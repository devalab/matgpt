import pandas as pd
from pymatgen.core.structure import Structure
import matplotlib.pyplot as plt
import seaborn as sns
import matgl
import hydra
from omegaconf import DictConfig, OmegaConf

@hydra.main(config_path="config", config_name="default", version_base=None)
def main(cfg: DictConfig):
    try:
        csv_path = cfg.proxy_model.csv_path
        model_name = cfg.proxy_model.model_eform
        plot_path = cfg.proxy_model.plot_path
        load_structures_predict_and_plot_kde(csv_path, model_name, plot_path, show_count=cfg.proxy_model.show_count)
    except Exception as e:
        print(f"An error occurred: {str(e)}")

def load_structures_predict_and_plot_kde(csv_path, model_name, plot_path, show_count=True):
    data = pd.read_csv(csv_path)
    data = data.dropna(subset=['CIF Path'])
    
    # Dynamically find the property column (first column that's not 'CIF Path' or 'SLICES')
    property_column = [col for col in data.columns if col not in ['CIF Path', 'SLICES']][0]
    
    model = matgl.load_model(model_name)
    property_eform_dict = {} 

    for index, row in data.iterrows():
        cif_path = row['CIF Path']
        property_value = row[property_column]  # Use the dynamically found property column
        try:
            structure = Structure.from_file(cif_path)
            eform = model.predict_structure(structure)
        except FileNotFoundError:
            continue
        
        if not pd.isnull(eform):
            if property_value not in property_eform_dict:
                property_eform_dict[property_value] = []
            property_eform_dict[property_value].append(float(eform))

    if not property_eform_dict:
        print("No predicted formation energies to plot.")
        return

    # Plot individual properties
    for property_value, eform_list in property_eform_dict.items():
        plt.figure(figsize=(12, 6))
        if len(eform_list) > 1:
            sns.kdeplot(eform_list, fill=True, label=f'{property_column} {property_value}')
        else:
            plt.axvline(eform_list[0], color='k', linestyle='dashed', linewidth=1, label=f'{property_column} {property_value}')
        plt.axvline(property_value, color='r', linestyle='dotted', linewidth=2, label=f'Target {property_column}')
        
        if show_count:
            plt.text(0.05, 0.95, f'Total reconstructions: {len(eform_list)}',
                     verticalalignment='top', horizontalalignment='left',
                     transform=plt.gca().transAxes, color='green', fontsize=12)
        
        plt.title(f'Predicted Formation Energies for {property_column} {property_value}')
        plt.xlabel('Formation Energy (eV/atom)')
        plt.ylabel('Density')
        plt.legend()
        plt.savefig(f"{plot_path}/Formation_Energy_{property_column}_{property_value}.png")
        plt.close()

    # Combined KDE plot
    plt.figure(figsize=(12, 6))
    for property_value, eform_list in property_eform_dict.items():
        sns.kdeplot(eform_list, fill=True, label=f'{property_column} {property_value}')
        plt.axvline(property_value, color='r', linestyle='dotted', linewidth=2)
    
    plt.title(f'Combined KDE of Predicted Formation Energies by {property_column}')
    plt.xlabel('Formation Energy (eV/atom)')
    plt.ylabel('Density')
    plt.legend()
    plt.savefig(f"{plot_path}/Combined_Predicted_Formation_Energies.png")
    plt.close()

if __name__ == "__main__":
    main()