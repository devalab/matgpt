# import pandas as pd
# from pymatgen.core.structure import Structure
# from pymatgen.symmetry.analyzer import SpacegroupAnalyzer
# import matplotlib.pyplot as plt
# import seaborn as sns
# import matgl
# import hydra
# from omegaconf import DictConfig
# import numpy as np
# import warnings

# warnings.filterwarnings("ignore", category=UserWarning)

# CRYSTAL_SYSTEM_NAMES = {
#     0: "Unknown",
#     1: "Triclinic",
#     2: "Monoclinic",
#     3: "Orthorhombic",
#     4: "Tetragonal",
#     5: "Trigonal",
#     6: "Hexagonal",
#     7: "Cubic",
# }

# CRYSTAL_NAME_TO_ENCODED = {v.lower(): k for k, v in CRYSTAL_SYSTEM_NAMES.items() if k > 0}

# plt.rcParams.update({
#     "font.size": 14,
#     "axes.labelsize": 16,
#     "axes.titlesize": 18,
#     "legend.fontsize": 12,
#     "xtick.labelsize": 12,
#     "ytick.labelsize": 12,
#     "figure.dpi": 300,
#     "savefig.dpi": 300,
#     "savefig.bbox": "tight",
# })


# @hydra.main(config_path="config", config_name="default", version_base=None)
# def main(cfg: DictConfig):
#     try:
#         csv_path = cfg.proxy_model.csv_path
#         bulk_model_name = cfg.proxy_model.model_bulk_modulus
#         plot_path = cfg.proxy_model.plot_path
#         load_structures_predict_and_plot(csv_path, bulk_model_name, plot_path)
#     except Exception as e:
#         print(f"An error occurred: {str(e)}")


# def load_structures_predict_and_plot(csv_path, bulk_model_name, plot_path):
#     data = pd.read_csv(csv_path)
#     data = data.dropna(subset=["CIF Path"])

#     try:
#         from megnet.utils.models import load_model as load_megnet_model
#         model_bulk = load_megnet_model(bulk_model_name)
#         predict_bulk = lambda structure: 10 ** model_bulk.predict_structure(structure).ravel()[0]
#     except Exception as e:
#         print(f"Error loading bulk modulus model: {str(e)}")
#         print("Using dummy prediction for bulk modulus.")
#         predict_bulk = lambda structure: np.random.uniform(50, 200)

#     results = []
#     for _, row in data.iterrows():
#         cif_path = row["CIF Path"]
#         crystal_sys = int(row["crystal_system_encoded"])
#         target_eform = float(row["e_form"])
#         try:
#             structure = Structure.from_file(cif_path)
#             predicted_bulk = float(predict_bulk(structure))
#             actual_cs_name = SpacegroupAnalyzer(structure).get_crystal_system()
#             actual_cs = CRYSTAL_NAME_TO_ENCODED.get(actual_cs_name, 0)
#         except Exception:
#             continue
#         results.append({
#             "crystal_system": crystal_sys,
#             "target_eform": target_eform,
#             "predicted_bulk": predicted_bulk,
#             "actual_crystal_system": actual_cs,
#         })

#     if not results:
#         print("No predicted bulk moduli to plot.")
#         return

#     df = pd.DataFrame(results)
#     targets = sorted(df["target_eform"].unique())

#     for target in targets:
#         subset = df[df["target_eform"] == target]
#         if len(subset) < 5:
#             continue
#         create_2d_kde(subset, target, plot_path)

#     # Combined KDE: predicted bulk modulus grouped by target e_form
#     plt.figure(figsize=(12, 6))
#     for target in targets:
#         subset = df[df["target_eform"] == target]
#         if len(subset) > 1:
#             sns.kdeplot(subset["predicted_bulk"], fill=True,
#                         label=f"Target {target} eV/atom", alpha=0.4)
#     plt.xlabel("Predicted Bulk Modulus (GPa)")
#     plt.ylabel("Density")
#     plt.title("Combined Predicted Bulk Modulus Distribution")
#     plt.legend()
#     plt.tight_layout()
#     plt.savefig(f"{plot_path}/Combined_BulkModulus_by_target.png")
#     plt.close()

#     # Combined crystal system: target vs actual (grouped bar chart)
#     all_cs = list(range(1, 8))

#     fig, ax = plt.subplots(figsize=(14, 7))
#     x = np.arange(len(all_cs))
#     width = 0.35

#     target_counts = df["crystal_system"].value_counts().reindex(all_cs, fill_value=0)
#     actual_counts = df["actual_crystal_system"].value_counts().reindex(all_cs, fill_value=0)

#     bars1 = ax.bar(x - width / 2, target_counts.values, width, label="Target (Conditioned)", alpha=0.8, color="#2c7fb8")
#     bars2 = ax.bar(x + width / 2, actual_counts.values, width, label="Actual (From Structure)", alpha=0.8, color="#d95f02")

#     ax.set_xticks(x)
#     ax.set_xticklabels([f"{CRYSTAL_SYSTEM_NAMES[c]}\n({c})" for c in all_cs], rotation=0, ha="center")
#     ax.set_xlabel("Crystal System")
#     ax.set_ylabel("Count")
#     ax.set_title("Crystal System: Target vs Actual")
#     ax.legend(fontsize=13)

#     for bar in bars1:
#         h = bar.get_height()
#         if h > 0:
#             ax.text(bar.get_x() + bar.get_width() / 2, h, f"{int(h)}", ha="center", va="bottom", fontsize=10, fontweight="bold")
#     for bar in bars2:
#         h = bar.get_height()
#         if h > 0:
#             ax.text(bar.get_x() + bar.get_width() / 2, h, f"{int(h)}", ha="center", va="bottom", fontsize=10, fontweight="bold")

#     fig.tight_layout()
#     fig.savefig(f"{plot_path}/Combined_CrystalSystem_BulkModulus.png")
#     plt.close(fig)

#     target_cs_vals = sorted(df["crystal_system"].unique())
#     for cs in target_cs_vals:
#         cs_name = CRYSTAL_SYSTEM_NAMES.get(cs, str(cs))
#         subset = df[df["crystal_system"] == cs]
#         matched = (subset["actual_crystal_system"] == cs).sum()
#         total = len(subset)
#         print(f"Crystal System {cs_name}: {matched}/{total} matched ({100 * matched / total:.1f}%)")

#     print(f"Bulk Modulus -- Mean: {df['predicted_bulk'].mean():.2f} GPa | Std: {df['predicted_bulk'].std():.2f} GPa")


# def create_2d_kde(data, target_eform, plot_path):
#     fig = plt.figure(figsize=(10, 8))
#     gs = fig.add_gridspec(2, 2, width_ratios=[4, 1], height_ratios=[1, 4],
#                           hspace=0.05, wspace=0.05)

#     ax_main = fig.add_subplot(gs[1, 0])
#     ax_top = fig.add_subplot(gs[0, 0], sharex=ax_main)
#     ax_right = fig.add_subplot(gs[1, 1], sharey=ax_main)

#     # Main 2D KDE
#     sns.kdeplot(
#         data=data, x="predicted_bulk", y="crystal_system",
#         fill=True, cmap="YlGnBu", alpha=0.7, ax=ax_main,
#     )

#     cs_vals = sorted(data["crystal_system"].unique())
#     ax_main.set_yticks(cs_vals)
#     ax_main.set_yticklabels([CRYSTAL_SYSTEM_NAMES.get(c, str(c)) for c in cs_vals])
#     ax_main.set_xlabel("Predicted Bulk Modulus (GPa)")
#     ax_main.set_ylabel("Crystal System")

#     # Top marginal: KDE of predicted bulk modulus
#     sns.kdeplot(data["predicted_bulk"], fill=True, color="#2c7fb8", alpha=0.5, ax=ax_top)
#     ax_top.set_ylabel("Density")
#     ax_top.tick_params(labelbottom=False)
#     ax_top.set_xlabel("")

#     # Right marginal: KDE of crystal system distribution
#     sns.kdeplot(y=data["crystal_system"], fill=True, color="#2c7fb8", alpha=0.5, ax=ax_right)
#     ax_right.set_xlabel("Density")
#     ax_right.tick_params(labelleft=False)
#     ax_right.set_ylabel("")

#     fig.suptitle(
#         f"Crystal System vs Bulk Modulus | Target E_form = {target_eform} eV/atom",
#         fontsize=16, y=0.98,
#     )
#     fig.savefig(f"{plot_path}/Crystal_BulkModulus_{target_eform}.png")
#     plt.close(fig)


# if __name__ == "__main__":
#     main()


import pandas as pd
from pymatgen.core.structure import Structure
from pymatgen.symmetry.analyzer import SpacegroupAnalyzer
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
import matplotlib.cm as cm
from matplotlib.colors import Normalize
import seaborn as sns
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
# Publication Quality Matplotlib Settings
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


@hydra.main(config_path="config", config_name="default", version_base=None)
def main(cfg: DictConfig):
    try:
        csv_path = cfg.proxy_model.csv_path
        bulk_model_name = cfg.proxy_model.model_bulk_modulus
        plot_path = cfg.proxy_model.plot_path
        load_structures_predict_and_plot(csv_path, bulk_model_name, plot_path)
    except Exception as e:
        print(f"An error occurred: {str(e)}")


def load_structures_predict_and_plot(csv_path, bulk_model_name, plot_path):
    data = pd.read_csv(csv_path)
    data = data.dropna(subset=["CIF Path"])

    try:
        from megnet.utils.models import load_model as load_megnet_model
        print(f"Loading MEGNet model: {bulk_model_name}...")
        model_bulk = load_megnet_model(bulk_model_name)
        predict_bulk = lambda structure: 10 ** model_bulk.predict_structure(structure).ravel()[0]
    except Exception as e:
        print(f"Error loading bulk modulus model: {str(e)}")
        print("Using dummy prediction for bulk modulus.")
        predict_bulk = lambda structure: np.random.uniform(50, 200)

    results = []
    print(f"Processing {len(data)} structures for Bulk Modulus predictions...")
    for _, row in tqdm(data.iterrows(), total=len(data), desc="Predicting"):
        cif_path = row["CIF Path"]
        crystal_sys = int(row["crystal_system_encoded"])
        target_eform = float(row["e_form"])
        try:
            structure = Structure.from_file(cif_path)
            predicted_bulk = float(predict_bulk(structure))
            actual_cs_name = SpacegroupAnalyzer(structure).get_crystal_system()
            actual_cs = CRYSTAL_NAME_TO_ENCODED.get(actual_cs_name, 0)
        except Exception:
            continue
            
        results.append({
            "crystal_system": crystal_sys,
            "target_eform": target_eform,
            "predicted_bulk": predicted_bulk,
            "actual_crystal_system": actual_cs,
        })

    if not results:
        print("No predicted bulk moduli to plot.")
        return

    df = pd.DataFrame(results)

    # 1. Generate the Summary Statistics Plot (Match Rate & Mean Bulk Modulus side-by-side)
    create_overall_summary_plot(df, plot_path)

    # 2. Generate 3D distribution plots
    condition_pairs = df[['target_eform', 'crystal_system']].drop_duplicates()
    print(f"Generating {len(condition_pairs)} 3D distribution plots...")
    for _, row in tqdm(condition_pairs.iterrows(), total=len(condition_pairs), desc="Plotting 3D"):
        target_e = row['target_eform']
        target_cs = int(row['crystal_system'])
        subset = df[(df["target_eform"] == target_e) & (df["crystal_system"] == target_cs)]
        
        if len(subset) >= 2:
            create_3d_bar(subset, target_e, target_cs, plot_path)


def create_overall_summary_plot(df, plot_path):
    """Generates side-by-side bar plots for Match Rate and Mean Bulk Modulus."""
    stats = []
    target_cs_vals = sorted(df["crystal_system"].unique())
    
    print("\n--- Individual Statistics ---")
    for cs in target_cs_vals:
        cs_name = CRYSTAL_SYSTEM_NAMES.get(cs, str(cs))
        subset = df[df["crystal_system"] == cs]
        
        matched = (subset["actual_crystal_system"] == cs).sum()
        total = len(subset)
        match_rate = (matched / total * 100) if total > 0 else 0
        
        # Calculate Mean Bulk Modulus for this crystal system
        if total > 0:
            mean_bulk = subset["predicted_bulk"].mean()
        else:
            mean_bulk = 0
            
        print(f"{cs_name}: Match Rate {match_rate:.1f}%, Mean Bulk Modulus {mean_bulk:.2f} GPa")
        
        stats.append({
            "System": cs_name, 
            "Match Rate (%)": match_rate,
            "Mean Bulk Modulus (GPa)": mean_bulk,
            "Count_Label": f"{matched}/{total}"
        })
    
    stat_df = pd.DataFrame(stats)
    overall_mean_bulk = df["predicted_bulk"].mean()

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

    # --- Plot 2: Mean Bulk Modulus ---
    sns.barplot(data=stat_df, x="System", y="Mean Bulk Modulus (GPa)", palette="mako", ax=ax2)
    ax2.set_title("Predicted Bulk Modulus by System", pad=15, fontweight='bold')
    ax2.set_ylabel("Mean Bulk Modulus (GPa)")
    
    max_bulk = stat_df["Mean Bulk Modulus (GPa)"].max()
    ax2.set_ylim(0, max_bulk * 1.25 if max_bulk > 0 else 100.0)

    for p in ax2.patches:
        ax2.annotate(f'{p.get_height():.2f}', 
                    (p.get_x() + p.get_width() / 2., p.get_height()),
                    ha='center', va='center', xytext=(0, 10), 
                    textcoords='offset points', fontweight='bold', fontsize=11)
        
    props = dict(boxstyle='round', facecolor='white', alpha=0.9, edgecolor='grey')
    ax2.text(0.05, 0.95, f"Overall Mean: {overall_mean_bulk:.2f} GPa", 
             transform=ax2.transAxes, fontsize=12, verticalalignment='top', 
             bbox=props, family='monospace')

    sns.despine()
    plt.tight_layout()
    fig.savefig(f"{plot_path}/Summary_Statistics_BulkModulus.png")
    plt.close(fig)
    print(f"Summary plot saved to {plot_path}/Summary_Statistics_BulkModulus.png")


def create_3d_bar(data, target_eform, target_cs, plot_path):
    all_cs = list(range(1, 8))
    target_cs_name = CRYSTAL_SYSTEM_NAMES.get(target_cs, "Unknown")
    bulk_min, bulk_max = data["predicted_bulk"].min(), data["predicted_bulk"].max()
    
    if bulk_min == bulk_max:
        bulk_min -= 10.0
        bulk_max += 10.0
        
    n_bins = 40  
    bins = np.linspace(bulk_min - 5.0, bulk_max + 5.0, n_bins + 1)
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
        subset = data[data["actual_crystal_system"] == cs]["predicted_bulk"]
        counts, _ = np.histogram(subset, bins=bins)
        max_count = max(max_count, counts.max()) if len(subset) > 0 else max_count
        bar_data.append((yi, cs, counts))

    if max_count == 0: max_count = 1
    norm = Normalize(vmin=0, vmax=max_count)
    cmap_obj = plt.get_cmap("plasma") 

    for yi in range(len(all_cs)):
        ax.plot([bulk_min, bulk_max], [yi, yi], [0, 0], 
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

    # Updated labels for Bulk Modulus
    ax.set_xlabel("Predicted Bulk Modulus (GPa)", labelpad=15, fontstyle='italic')
    ax.set_ylabel("Actual Crystal System", labelpad=15, fontstyle='italic')
    ax.set_zlabel("Count", labelpad=12, fontstyle='italic')

    ax.set_yticks(range(len(all_cs)))
    ax.set_yticklabels([str(c) for c in all_cs], rotation=-15, ha='left')
    ax.set_title(f"Target $E_{{form}}$: {target_eform} | Target CS: {target_cs_name} ({target_cs})", 
                 pad=20, fontweight='bold')
    ax.view_init(elev=20, azim=-55)
    
    # Save the 3D plots with the bulk modulus naming convention
    fig.savefig(f"{plot_path}/Origin3D_BulkModulus_{target_eform}_CS_{target_cs}.png")
    plt.close(fig)

if __name__ == "__main__":
    main()