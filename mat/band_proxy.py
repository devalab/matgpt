import pandas as pd
from pymatgen.core.structure import Structure
import matplotlib.pyplot as plt
import seaborn as sns
import matgl
import torch
import hydra
from omegaconf import DictConfig, OmegaConf

@hydra.main(config_path="config", config_name="default", version_base=None)
def main(cfg: DictConfig):
    try:
        csv_path = cfg.proxy_model.csv_path
        model_name = cfg.proxy_model.model_band
        plot_path = cfg.proxy_model.plot_path
        load_structures_predict_and_plot_kde(csv_path, model_name, plot_path, show_count=cfg.proxy_model.show_count)
    except Exception as e:
        print(f"An error occurred: {str(e)}")

def load_structures_predict_and_plot_kde(csv_path, model_name, plot_path, show_count=True):
    data = pd.read_csv(csv_path)
    data = data.dropna(subset=['CIF Path'])
    
    # Use 'band_gap' as the property column
    band_gap_column = 'band_gap'
    
    model = matgl.load_model(model_name)
    methods = ["PBE", "GLLB-SC", "HSE", "SCAN"]
    method_bandgap_data = {method: [] for method in methods}
    target_bandgap_data = {}

    for index, row in data.iterrows():
        cif_path = row['CIF Path']
        target_bandgap = float(row[band_gap_column])
        try:
            structure = Structure.from_file(cif_path)
            for i, method in enumerate(methods):
                graph_attrs = torch.tensor([i])
                predicted_bandgap = model.predict_structure(structure=structure, state_attr=graph_attrs)
                method_bandgap_data[method].append(float(predicted_bandgap))
                
                if target_bandgap not in target_bandgap_data:
                    target_bandgap_data[target_bandgap] = {}
                if method not in target_bandgap_data[target_bandgap]:
                    target_bandgap_data[target_bandgap][method] = []
                target_bandgap_data[target_bandgap][method].append(float(predicted_bandgap))
        except FileNotFoundError:
            print(f"File not found: {cif_path}")
            continue

    # Plot individual properties for each method and target
    for target_bandgap, methods_data in target_bandgap_data.items():
        palette = sns.color_palette("husl", n_colors=len(methods_data))
        for method, values in methods_data.items():
            plt.figure(figsize=(12, 6))
            color = palette.pop(0)
            sns.kdeplot(values, fill=True, color=color, label=f'{method} Band Gap')
            plt.axvline(target_bandgap, color=color, linestyle='dotted', linewidth=2, label='Target Band Gap')
            if show_count:
                plt.text(0.05, 0.95, f'Total reconstructions: {len(values)}',
                         verticalalignment='top', horizontalalignment='left',
                         transform=plt.gca().transAxes, color='green', fontsize=12)
            plt.title(f'Band Gap Distribution for {method} (Target {target_bandgap} eV)')
            plt.xlabel('Band Gap (eV)')
            plt.ylabel('Density')
            plt.legend()
            plt.savefig(f"{plot_path}/{method}_Band_Gap_Target_{target_bandgap}.png")
            plt.close()

    # Combined KDE plot for each method across all targets
    for method, values in method_bandgap_data.items():
        plt.figure(figsize=(12, 6))
        palette = sns.color_palette("husl", n_colors=len(target_bandgap_data))
        for target_bandgap, methods_data in target_bandgap_data.items():
            if method in methods_data:
                color = palette.pop(0)
                sns.kdeplot(methods_data[method], fill=True, color=color, label=f'Target {target_bandgap} eV')
                plt.axvline(target_bandgap, color=color, linestyle='dotted', linewidth=1, label=f'Target {target_bandgap} eV')
        plt.title(f'Combined Band Gap Distribution for {method}')
        plt.xlabel('Band Gap (eV)')
        plt.ylabel('Density')
        plt.legend()
        plt.savefig(f"{plot_path}/Combined_{method}_Band_Gaps.png")
        plt.close()

if __name__ == "__main__":
    main()