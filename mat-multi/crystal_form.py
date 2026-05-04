# import pandas as pd
# from pymatgen.core.structure import Structure
# from pymatgen.symmetry.analyzer import SpacegroupAnalyzer
# import matplotlib.pyplot as plt
# from mpl_toolkits.mplot3d import Axes3D
# import matplotlib.cm as cm
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
#         model_name = cfg.proxy_model.model_eform
#         plot_path = cfg.proxy_model.plot_path
#         load_structures_predict_and_plot(csv_path, model_name, plot_path)
#     except Exception as e:
#         print(f"An error occurred: {str(e)}")


# def load_structures_predict_and_plot(csv_path, model_name, plot_path):
#     data = pd.read_csv(csv_path)
#     data = data.dropna(subset=["CIF Path"])

#     model = matgl.load_model(model_name)

#     results = []
#     for _, row in data.iterrows():
#         cif_path = row["CIF Path"]
#         crystal_sys = int(row["crystal_system_encoded"])
#         target_eform = float(row["e_form"])
#         try:
#             structure = Structure.from_file(cif_path)
#             predicted_eform = float(model.predict_structure(structure))
#             actual_cs_name = SpacegroupAnalyzer(structure).get_crystal_system()
#             actual_cs = CRYSTAL_NAME_TO_ENCODED.get(actual_cs_name, 0)
#         except Exception:
#             continue
#         results.append({
#             "crystal_system": crystal_sys,
#             "target_eform": target_eform,
#             "predicted_eform": predicted_eform,
#             "actual_crystal_system": actual_cs,
#         })

#     if not results:
#         print("No predicted formation energies to plot.")
#         return

#     df = pd.DataFrame(results)
#     targets = sorted(df["target_eform"].unique())

#     for target in targets:
#         subset = df[df["target_eform"] == target]
#         if len(subset) < 5:
#             continue
#         create_3d_bar(subset, target, plot_path)

#     # Combined 3D bar plot across all targets
#     create_3d_bar_combined(df, plot_path)

#     # Combined KDE: predicted formation energy grouped by target e_form
#     plt.figure(figsize=(12, 6))
#     for target in targets:
#         subset = df[df["target_eform"] == target]
#         if len(subset) > 1:
#             sns.kdeplot(subset["predicted_eform"], fill=True,
#                         label=f"Target {target} eV/atom", alpha=0.4)
#         plt.axvline(target, color="r", linestyle="--", linewidth=1.5, alpha=0.7)
#     plt.xlabel("Predicted Formation Energy (eV/atom)")
#     plt.ylabel("Density")
#     plt.title("Combined Predicted Formation Energy Distribution")
#     plt.legend()
#     plt.tight_layout()
#     plt.savefig(f"{plot_path}/Combined_FormEnergy_by_target.png")
#     plt.close()

#     # Combined crystal system: target vs actual (grouped bar chart)
#     # Always show all 7 crystal systems (1-7)
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
#     fig.savefig(f"{plot_path}/Combined_CrystalSystem_FormEnergy.png")
#     plt.close(fig)

#     # Per target crystal system: match rate
#     target_cs_vals = sorted(df["crystal_system"].unique())
#     for cs in target_cs_vals:
#         cs_name = CRYSTAL_SYSTEM_NAMES.get(cs, str(cs))
#         subset = df[df["crystal_system"] == cs]
#         matched = (subset["actual_crystal_system"] == cs).sum()
#         total = len(subset)
#         print(f"Crystal System {cs_name}: {matched}/{total} matched ({100 * matched / total:.1f}%)")

#     mae = np.mean(np.abs(df["predicted_eform"] - df["target_eform"]))
#     rmse = np.sqrt(np.mean((df["predicted_eform"] - df["target_eform"]) ** 2))
#     print(f"Formation Energy -- MAE: {mae:.4f} eV/atom | RMSE: {rmse:.4f} eV/atom")


# def create_3d_bar(data, target_eform, plot_path):
#     # Always show all 7 crystal systems (1-7) on Y axis
#     all_cs = list(range(1, 8))

#     # Bin the predicted formation energy
#     eform_min = data["predicted_eform"].min()
#     eform_max = data["predicted_eform"].max()
#     n_bins = 25
#     bins = np.linspace(eform_min - 0.1, eform_max + 0.1, n_bins + 1)
#     bin_centers = 0.5 * (bins[:-1] + bins[1:])
#     bin_width = bins[1] - bins[0]

#     fig = plt.figure(figsize=(14, 10))
#     ax = fig.add_subplot(111, projection="3d")

#     max_count = 0
#     bar_data = []
#     for yi, cs in enumerate(all_cs):
#         subset = data[data["actual_crystal_system"] == cs]["predicted_eform"]
#         counts, _ = np.histogram(subset, bins=bins)
#         max_count = max(max_count, counts.max()) if len(subset) > 0 else max_count
#         bar_data.append((yi, cs, counts))

#     if max_count == 0:
#         max_count = 1
#     norm = plt.Normalize(0, max_count)
#     cmap_obj = cm.get_cmap("plasma")

#     # Plot from back to front (high yi first) to avoid occlusion
#     for yi, cs, counts in reversed(bar_data):
#         for xi, count in enumerate(counts):
#             if count == 0:
#                 continue
#             color = cmap_obj(norm(count))
#             ax.bar3d(bin_centers[xi] - bin_width / 2, yi - 0.35, 0,
#                      bin_width * 0.85, 0.7, count,
#                      color=color, alpha=0.85, edgecolor="k", linewidth=0.3)

#     ax.set_xlabel("Formation Energy (eV/atom)", fontsize=13, labelpad=12)
#     ax.set_ylabel("Crystal System", fontsize=13, labelpad=12)
#     ax.set_zlabel("Count", fontsize=13, labelpad=10)

#     ax.set_yticks(range(len(all_cs)))
#     ax.set_yticklabels([CRYSTAL_SYSTEM_NAMES[c] for c in all_cs], fontsize=9)

#     ax.set_title(
#         f"Actual Crystal System Distribution\nTarget E_form = {target_eform} eV/atom",
#         fontsize=15, pad=20,
#     )

#     ax.view_init(elev=30, azim=225)

#     fig.tight_layout()
#     fig.savefig(f"{plot_path}/Crystal_FormEnergy_3D_{target_eform}.png")
#     plt.close(fig)


# def create_3d_bar_combined(df, plot_path):
#     all_cs = list(range(1, 8))

#     eform_min = df["predicted_eform"].min()
#     eform_max = df["predicted_eform"].max()
#     n_bins = 30
#     bins = np.linspace(eform_min - 0.1, eform_max + 0.1, n_bins + 1)
#     bin_centers = 0.5 * (bins[:-1] + bins[1:])
#     bin_width = bins[1] - bins[0]

#     fig = plt.figure(figsize=(14, 10))
#     ax = fig.add_subplot(111, projection="3d")

#     max_count = 0
#     bar_data = []
#     for yi, cs in enumerate(all_cs):
#         subset = df[df["actual_crystal_system"] == cs]["predicted_eform"]
#         counts, _ = np.histogram(subset, bins=bins)
#         max_count = max(max_count, counts.max()) if len(subset) > 0 else max_count
#         bar_data.append((yi, cs, counts))

#     if max_count == 0:
#         max_count = 1
#     norm = plt.Normalize(0, max_count)
#     cmap_obj = cm.get_cmap("plasma")

#     for yi, cs, counts in reversed(bar_data):
#         for xi, count in enumerate(counts):
#             if count == 0:
#                 continue
#             color = cmap_obj(norm(count))
#             ax.bar3d(bin_centers[xi] - bin_width / 2, yi - 0.35, 0,
#                      bin_width * 0.85, 0.7, count,
#                      color=color, alpha=0.85, edgecolor="k", linewidth=0.3)

#     ax.set_xlabel("Formation Energy (eV/atom)", fontsize=13, labelpad=12)
#     ax.set_ylabel("Crystal System", fontsize=13, labelpad=12)
#     ax.set_zlabel("Count", fontsize=13, labelpad=10)

#     ax.set_yticks(range(len(all_cs)))
#     ax.set_yticklabels([CRYSTAL_SYSTEM_NAMES[c] for c in all_cs], fontsize=9)

#     ax.set_title("Actual Crystal System vs Predicted Formation Energy", fontsize=15, pad=20)

#     ax.view_init(elev=30, azim=225)

#     fig.tight_layout()
#     fig.savefig(f"{plot_path}/Crystal_FormEnergy_3D_Combined.png")
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
import matgl
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
        model_name = cfg.proxy_model.model_eform
        plot_path = cfg.proxy_model.plot_path
        load_structures_predict_and_plot(csv_path, model_name, plot_path)
    except Exception as e:
        print(f"An error occurred: {str(e)}")

def load_structures_predict_and_plot(csv_path, model_name, plot_path):
    data = pd.read_csv(csv_path)
    data = data.dropna(subset=["CIF Path"])

    print(f"Loading MatGL model: {model_name}...")
    model = matgl.load_model(model_name)

    # Initialize new columns to store the results
    data["Predicted_Eform"] = None
    data["Actual_Crystal_System"] = None

    results = []
    print(f"Processing {len(data)} structures...")
    
    for index, row in tqdm(data.iterrows(), total=len(data), desc="Predicting"):
        cif_path = row["CIF Path"]
        crystal_sys = int(row["crystal_system_encoded"])
        target_eform = float(row["e_form"])
        try:
            structure = Structure.from_file(cif_path)
            predicted_eform = float(model.predict_structure(structure))
            actual_cs_name = SpacegroupAnalyzer(structure).get_crystal_system()
            actual_cs = CRYSTAL_NAME_TO_ENCODED.get(actual_cs_name, 0)
            
            # Save predictions directly into the DataFrame
            data.at[index, "Predicted_Eform"] = predicted_eform
            data.at[index, "Actual_Crystal_System"] = actual_cs
            
        except Exception:
            # Skip rows where parsing or prediction fails
            continue
            
        results.append({
            "crystal_system": crystal_sys,
            "target_eform": target_eform,
            "predicted_eform": predicted_eform,
            "actual_crystal_system": actual_cs,
        })

    # Save the updated DataFrame back to the original CSV file
    data.to_csv(csv_path, index=False)
    print(f"\nPredictions and structures saved successfully to {csv_path}")

    if not results:
        print("No results to process.")
        return

    df = pd.DataFrame(results)

    # 1. Generate the Summary Statistics Plot (Match Rate & Individual MAE side-by-side)
    create_overall_summary_plot(df, plot_path)

    # 2. Generate 3D distribution plots
    condition_pairs = df[['target_eform', 'crystal_system']].drop_duplicates()
    print(f"Generating {len(condition_pairs)} 3D distribution plots...")
    for _, row in tqdm(condition_pairs.iterrows(), total=len(condition_pairs), desc="Plotting 3D"):
        target_e, target_cs = row['target_eform'], int(row['crystal_system'])
        subset = df[(df["target_eform"] == target_e) & (df["crystal_system"] == target_cs)]
        if len(subset) >= 2:
            create_3d_bar(subset, target_e, target_cs, plot_path)

def create_overall_summary_plot(df, plot_path):
    """Generates side-by-side bar plots for Match Rate and Individual MAE."""
    stats = []
    target_cs_vals = sorted(df["crystal_system"].unique())
    
    print("\n--- Individual Statistics ---")
    for cs in target_cs_vals:
        cs_name = CRYSTAL_SYSTEM_NAMES.get(cs, str(cs))
        subset = df[df["crystal_system"] == cs]
        
        matched = (subset["actual_crystal_system"] == cs).sum()
        total = len(subset)
        match_rate = (matched / total * 100) if total > 0 else 0
        
        # Calculate Individual MAE for this crystal system
        if total > 0:
            indiv_mae = np.mean(np.abs(subset["predicted_eform"] - subset["target_eform"]))
        else:
            indiv_mae = 0
            
        print(f"{cs_name}: Match Rate {match_rate:.1f}%, MAE {indiv_mae:.4f} eV/atom")
        
        stats.append({
            "System": cs_name, 
            "Match Rate (%)": match_rate,
            "MAE (eV/atom)": indiv_mae,
            "Count_Label": f"{matched}/{total}"
        })
    
    stat_df = pd.DataFrame(stats)
    overall_mae = np.mean(np.abs(df["predicted_eform"] - df["target_eform"]))

    # Create a figure with 2 side-by-side subplots
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 7))

    # --- Plot 1: Match Rate ---
    sns.barplot(data=stat_df, x="System", y="Match Rate (%)", palette="viridis", ax=ax1)
    ax1.set_title("Structural Match Rate by Crystal System", pad=15, fontweight='bold')
    ax1.set_ylabel("Match Rate (%)")
    ax1.set_ylim(0, 115)  # Extra space for labels
    
    # Annotate Match Rate counts on top of bars
    for i, p in enumerate(ax1.patches):
        ax1.annotate(f'{stat_df["Count_Label"].iloc[i]}\n({p.get_height():.1f}%)', 
                    (p.get_x() + p.get_width() / 2., p.get_height()),
                    ha='center', va='center', xytext=(0, 15), 
                    textcoords='offset points', fontweight='bold', fontsize=11)

    # --- Plot 2: Individual MAE ---
    sns.barplot(data=stat_df, x="System", y="MAE (eV/atom)", palette="magma", ax=ax2)
    ax2.set_title("Energy Prediction Error (Individual MAE)", pad=15, fontweight='bold')
    ax2.set_ylabel("Mean Absolute Error (eV/atom)")
    
    # Dynamically set y-limit to leave room for text
    max_mae = stat_df["MAE (eV/atom)"].max()
    ax2.set_ylim(0, max_mae * 1.25 if max_mae > 0 else 0.1)

    # Annotate MAE values on top of bars
    for p in ax2.patches:
        ax2.annotate(f'{p.get_height():.4f}', 
                    (p.get_x() + p.get_width() / 2., p.get_height()),
                    ha='center', va='center', xytext=(0, 10), 
                    textcoords='offset points', fontweight='bold', fontsize=11)
        
    # Add Overall MAE text box to the second plot
    props = dict(boxstyle='round', facecolor='white', alpha=0.9, edgecolor='grey')
    ax2.text(0.05, 0.95, f"Overall MAE: {overall_mae:.4f} eV/atom", 
             transform=ax2.transAxes, fontsize=12, verticalalignment='top', 
             bbox=props, family='monospace')

    sns.despine()
    plt.tight_layout()
    fig.savefig(f"{plot_path}/Summary_Statistics_with_Individual_MAE.png")
    plt.close(fig)
    print(f"Summary plot saved to {plot_path}/Summary_Statistics_with_Individual_MAE.png")

def create_3d_bar(data, target_eform, target_cs, plot_path):
    all_cs = list(range(1, 8))
    target_cs_name = CRYSTAL_SYSTEM_NAMES.get(target_cs, "Unknown")
    eform_min, eform_max = data["predicted_eform"].min(), data["predicted_eform"].max()
    
    if eform_min == eform_max:
        eform_min -= 0.1
        eform_max += 0.1
        
    n_bins = 40  
    bins = np.linspace(eform_min - 0.1, eform_max + 0.1, n_bins + 1)
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
        subset = data[data["actual_crystal_system"] == cs]["predicted_eform"]
        counts, _ = np.histogram(subset, bins=bins)
        max_count = max(max_count, counts.max()) if len(subset) > 0 else max_count
        bar_data.append((yi, cs, counts))

    if max_count == 0: max_count = 1
    norm = Normalize(vmin=0, vmax=max_count)
    cmap_obj = plt.get_cmap("plasma") 

    for yi in range(len(all_cs)):
        ax.plot([eform_min, eform_max], [yi, yi], [0, 0], 
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

    ax.set_xlabel("Formation Energy (eV/atom)", labelpad=15, fontstyle='italic')
    ax.set_ylabel("Actual Crystal System", labelpad=15, fontstyle='italic')
    ax.set_zlabel("Count", labelpad=12, fontstyle='italic')

    ax.set_yticks(range(len(all_cs)))
    ax.set_yticklabels([str(c) for c in all_cs], rotation=-15, ha='left')
    ax.set_title(f"Target $E_{{form}}$: {target_eform} | Target CS: {target_cs_name} ({target_cs})", 
                 pad=20, fontweight='bold')
    ax.view_init(elev=20, azim=-55)
    fig.savefig(f"{plot_path}/Origin3D_Eform_{target_eform}_CS_{target_cs}.png")
    plt.close(fig)

if __name__ == "__main__":
    main()