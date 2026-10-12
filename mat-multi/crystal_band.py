import pandas as pd
from pymatgen.core.structure import Structure
from pymatgen.symmetry.analyzer import SpacegroupAnalyzer
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D  # noqa: F401  (registers the 3d projection)
from matplotlib.colors import Normalize
import seaborn as sns
import matgl
import matgl.utils.io
# matgl 1.1.3 downloads its pretrained models from the main branch of the matgl GitHub repository, where they no
# longer exist (removed in matgl 3.0). Load the same files from the v1.1.3 tag; models in ~/.cache/matgl are reused.
matgl.utils.io.PRETRAINED_MODELS_BASE_URL = "https://raw.githubusercontent.com/materialsvirtuallab/matgl/v1.1.3/pretrained_models/"
import torch
import hydra
from omegaconf import DictConfig
import numpy as np
import warnings
from tqdm import tqdm

warnings.filterwarnings("ignore", category=UserWarning)

# Mapping constants
CRYSTAL_SYSTEM_NAMES = {
    0: "Unknown",
    1: "Triclinic",
    2: "Monoclinic",
    3: "Orthorhombic",
    4: "Tetragonal",
    5: "Trigonal",
    6: "Hexagonal",
    7: "Cubic",
}

CRYSTAL_NAME_TO_ENCODED = {v.lower(): k for k, v in CRYSTAL_SYSTEM_NAMES.items() if k > 0}

# ==========================================
# Matplotlib settings
# ==========================================
plt.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans"],
    "font.size": 12,
    "axes.labelsize": 14,
    "axes.titlesize": 16,
    "axes.linewidth": 1.2,
    "legend.fontsize": 11,
    "legend.frameon": False,
    "xtick.labelsize": 11,
    "ytick.labelsize": 11,
    "xtick.major.width": 1.2,
    "ytick.major.width": 1.2,
    "figure.dpi": 300,
    "savefig.dpi": 300,
    "savefig.bbox": "tight",
})


@hydra.main(config_path="config", config_name="cs_band", version_base=None)
def main(cfg: DictConfig):
    try:
        csv_path = cfg.proxy_model.csv_path
        model_name = cfg.proxy_model.model_band
        plot_path = cfg.proxy_model.plot_path
        target_column = cfg.training.selected_properties[1]   # band gap target column
        load_structures_predict_and_plot(csv_path, model_name, plot_path, target_column)
    except Exception as e:
        print(f"An error occurred: {str(e)}")
        raise


def load_structures_predict_and_plot(csv_path, model_name, plot_path, target_column):
    data = pd.read_csv(csv_path)
    data = data.dropna(subset=["CIF Path"])

    print(f"Loading MatGL model: {model_name}...")
    model = matgl.load_model(model_name)

    # Initialize new columns to store the results
    data["Predicted_PBE"] = None
    data["Actual_Crystal_System"] = None

    results = []
    print(f"Processing {len(data)} structures for PBE Band Gap predictions...")
    for index, row in tqdm(data.iterrows(), total=len(data), desc="Predicting"):
        cif_path = row["CIF Path"]
        crystal_sys = int(row["crystal_system_encoded"])
        target_value = float(row[target_column])   # band gap target
        try:
            structure = Structure.from_file(cif_path)
            # state_attr [0] corresponds to the PBE method in MatGL bandgap models
            graph_attrs = torch.tensor([0])
            predicted_bandgap = float(model.predict_structure(structure=structure, state_attr=graph_attrs))
            
            actual_cs_name = SpacegroupAnalyzer(structure).get_crystal_system()
            actual_cs = CRYSTAL_NAME_TO_ENCODED.get(actual_cs_name, 0)

            # Save predictions directly into the DataFrame
            data.at[index, "Predicted_PBE"] = predicted_bandgap
            data.at[index, "Actual_Crystal_System"] = actual_cs
        except Exception as e:
            print(f"Skipping {cif_path}: {e}")
            continue
            
        results.append({
            "crystal_system": crystal_sys,
            "target_value": target_value,
            "predicted_bandgap": predicted_bandgap,
            "actual_crystal_system": actual_cs,
        })

    # Save the updated DataFrame back to the original CSV file
    data.to_csv(csv_path, index=False)
    print(f"\nPredictions saved to {csv_path}")

    if not results:
        print("No predicted band gaps to plot.")
        return

    df = pd.DataFrame(results)

    # 1. Generate the Summary Statistics Plot (Match Rate & Mean PBE Band Gap side-by-side)
    create_overall_summary_plot(df, plot_path)

    # 2. Generate 3D distribution plots
    condition_pairs = df[['target_value', 'crystal_system']].drop_duplicates()
    print(f"Generating {len(condition_pairs)} 3D distribution plots...")
    for _, row in tqdm(condition_pairs.iterrows(), total=len(condition_pairs), desc="Plotting 3D"):
        target_e = row['target_value']
        target_cs = int(row['crystal_system'])
        subset = df[(df["target_value"] == target_e) & (df["crystal_system"] == target_cs)]
        
        if len(subset) >= 2:
            create_3d_bar(subset, target_e, target_cs, plot_path)


def create_overall_summary_plot(df, plot_path):
    """Generates side-by-side bar plots for Match Rate and Mean PBE Band Gap."""
    stats = []
    target_cs_vals = sorted(df["crystal_system"].unique())
    
    print("\n--- Individual Statistics ---")
    for cs in target_cs_vals:
        cs_name = CRYSTAL_SYSTEM_NAMES.get(cs, str(cs))
        subset = df[df["crystal_system"] == cs]
        
        matched = (subset["actual_crystal_system"] == cs).sum()
        total = len(subset)
        match_rate = (matched / total * 100) if total > 0 else 0
        
        # Calculate Mean PBE Band Gap for this crystal system
        if total > 0:
            mean_bg = subset["predicted_bandgap"].mean()
        else:
            mean_bg = 0
            
        print(f"{cs_name}: Match Rate {match_rate:.1f}%, Mean PBE Band Gap {mean_bg:.4f} eV")
        
        stats.append({
            "System": cs_name, 
            "Match Rate (%)": match_rate,
            "Mean Band Gap (eV)": mean_bg,
            "Count_Label": f"{matched}/{total}"
        })
    
    stat_df = pd.DataFrame(stats)
    overall_mean_bg = df["predicted_bandgap"].mean()

    # Create a figure with 2 side-by-side subplots
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 7))

    # --- Plot 1: Match Rate ---
    sns.barplot(data=stat_df, x="System", y="Match Rate (%)", palette="viridis", ax=ax1)
    ax1.set_title("Structural Match Rate by Crystal System", pad=15, fontweight='bold')
    ax1.set_ylabel("Match Rate (%)")
    ax1.set_ylim(0, 115) 
    
    for i, p in enumerate(ax1.patches):
        ax1.annotate(f'{stat_df["Count_Label"].iloc[i]}\n({p.get_height():.1f}%)', 
                    (p.get_x() + p.get_width() / 2., p.get_height()),
                    ha='center', va='center', xytext=(0, 15), 
                    textcoords='offset points', fontweight='bold', fontsize=11)

    # --- Plot 2: Mean PBE Band Gap ---
    sns.barplot(data=stat_df, x="System", y="Mean Band Gap (eV)", palette="magma", ax=ax2)
    ax2.set_title("Predicted PBE Band Gap by System", pad=15, fontweight='bold')
    ax2.set_ylabel("Mean Band Gap (eV)")
    
    max_bg = stat_df["Mean Band Gap (eV)"].max()
    ax2.set_ylim(0, max_bg * 1.25 if max_bg > 0 else 1.0)

    for p in ax2.patches:
        ax2.annotate(f'{p.get_height():.3f}', 
                    (p.get_x() + p.get_width() / 2., p.get_height()),
                    ha='center', va='center', xytext=(0, 10), 
                    textcoords='offset points', fontweight='bold', fontsize=11)
        
    props = dict(boxstyle='round', facecolor='white', alpha=0.9, edgecolor='grey')
    ax2.text(0.05, 0.95, f"Overall Mean: {overall_mean_bg:.4f} eV", 
             transform=ax2.transAxes, fontsize=12, verticalalignment='top', 
             bbox=props, family='monospace')

    sns.despine()
    plt.tight_layout()
    fig.savefig(f"{plot_path}/Summary_Statistics_PBE_BandGap.png")
    plt.close(fig)
    print(f"Summary plot saved to {plot_path}/Summary_Statistics_PBE_BandGap.png")


def create_3d_bar(data, target_value, target_cs, plot_path):
    all_cs = list(range(1, 8))
    target_cs_name = CRYSTAL_SYSTEM_NAMES.get(target_cs, "Unknown")
    bg_min, bg_max = data["predicted_bandgap"].min(), data["predicted_bandgap"].max()
    
    if bg_min == bg_max:
        bg_min -= 0.1
        bg_max += 0.1
        
    n_bins = 40  
    bins = np.linspace(bg_min - 0.1, bg_max + 0.1, n_bins + 1)
    bin_centers = 0.5 * (bins[:-1] + bins[1:])
    bin_width = bins[1] - bins[0]

    fig = plt.figure(figsize=(12, 10))
    ax = fig.add_subplot(111, projection="3d")

    ax.xaxis.set_pane_color((1.0, 1.0, 1.0, 1.0))
    ax.yaxis.set_pane_color((1.0, 1.0, 1.0, 1.0))
    ax.zaxis.set_pane_color((1.0, 1.0, 1.0, 1.0))
    ax.grid(color='grey', linestyle='-', linewidth=0.5, alpha=0.3)

    max_count = 0
    bar_data = []
    for yi, cs in enumerate(all_cs):
        subset = data[data["actual_crystal_system"] == cs]["predicted_bandgap"]
        counts, _ = np.histogram(subset, bins=bins)
        max_count = max(max_count, counts.max()) if len(subset) > 0 else max_count
        bar_data.append((yi, cs, counts))

    if max_count == 0: max_count = 1
    norm = Normalize(vmin=0, vmax=max_count)
    cmap_obj = plt.get_cmap("plasma") 

    for yi in range(len(all_cs)):
        ax.plot([bg_min, bg_max], [yi, yi], [0, 0], 
                color="olive", linestyle="--", linewidth=1.2, alpha=0.4)

    dx_width = bin_width * 0.4
    dy_width = 0.15 
    n_segments = 50  
    dz_step = max_count / n_segments

    _x, _y, _z, _dx, _dy, _dz, _colors = [], [], [], [], [], [], []
    _ox, _oy, _oz, _odx, _ody, _odz = [], [], [], [], [], []

    for yi, cs, counts in reversed(bar_data):
        for xi, count in enumerate(counts):
            if count == 0: continue
            _ox.append(bin_centers[xi] - dx_width / 2)
            _oy.append(yi - dy_width / 2)
            _oz.append(0)
            _odx.append(dx_width)
            _ody.append(dy_width)
            _odz.append(count)
            current_z = 0
            while current_z < count:
                segment_height = min(dz_step, count - current_z)
                _x.append(bin_centers[xi] - dx_width / 2)
                _y.append(yi - dy_width / 2)
                _z.append(current_z)
                _dx.append(dx_width)
                _dy.append(dy_width)
                _dz.append(segment_height)
                _colors.append(cmap_obj(norm(current_z + segment_height/2)))
                current_z += dz_step

    ax.bar3d(_x, _y, _z, _dx, _dy, _dz, color=_colors, alpha=1.0, shade=True, edgecolor='none')
    ax.bar3d(_ox, _oy, _oz, _odx, _ody, _odz, color=(0,0,0,0), edgecolor='black', linewidth=0.3, shade=False)

    # Axis labels
    ax.set_xlabel("Predicted PBE Band Gap (eV)", labelpad=15, fontstyle='italic')
    ax.set_ylabel("Actual Crystal System", labelpad=15, fontstyle='italic')
    ax.set_zlabel("Count", labelpad=12, fontstyle='italic')

    ax.set_yticks(range(len(all_cs)))
    ax.set_yticklabels([str(c) for c in all_cs], rotation=-15, ha='left')
    ax.set_title(f"Target band gap: {target_value} eV | Target CS: {target_cs_name} ({target_cs})", 
                 pad=20, fontweight='bold')
    ax.view_init(elev=20, azim=-55)
    
    # Save the 3D plots with the band gap naming convention
    fig.savefig(f"{plot_path}/Origin3D_PBE_BandGap_{target_value}_CS_{target_cs}.png")
    plt.close(fig)

if __name__ == "__main__":
    main()
