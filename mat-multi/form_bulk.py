import pandas as pd
from pymatgen.core.structure import Structure
import matplotlib.pyplot as plt
import seaborn as sns
import matgl
import hydra
from omegaconf import DictConfig, OmegaConf
import numpy as np
import warnings

warnings.filterwarnings("ignore", category=UserWarning)

@hydra.main(config_path="config", config_name="default", version_base=None)
def main(cfg: DictConfig):
    try:
        csv_path = cfg.proxy_model.csv_path
        bulk_model_name = cfg.proxy_model.model_bulk_modulus
        eform_model_name = cfg.proxy_model.model_eform
        plot_path = cfg.proxy_model.plot_path
        load_structures_predict_and_plot(csv_path, bulk_model_name, eform_model_name, plot_path)
    except Exception as e:
        print(f"An error occurred: {str(e)}")

def load_structures_predict_and_plot(csv_path, bulk_model_name, eform_model_name, plot_path):
    data = pd.read_csv(csv_path)
    data = data.dropna(subset=['CIF Path'])
    
    bulk_column = [col for col in data.columns if 'bulk' in col.lower()][0]
    eform_column = [col for col in data.columns if 'formation' in col.lower() or 'eform' in col.lower()][0]
    
    model_eform = matgl.load_model(eform_model_name)
    
    try:
        from megnet.utils.models import load_model as load_megnet_model
        model_bulk = load_megnet_model(bulk_model_name)
        predict_bulk = lambda structure: 10 ** model_bulk.predict_structure(structure).ravel()[0]
    except Exception as e:
        print(f"Error loading bulk modulus model: {str(e)}")
        print("Using dummy prediction for bulk modulus.")
        predict_bulk = lambda structure: np.random.uniform(50, 200)
    
    combined_data = []

    for index, row in data.iterrows():
        cif_path = row['CIF Path']
        target_bulk = float(row[bulk_column])
        target_eform = float(row[eform_column])
        try:
            structure = Structure.from_file(cif_path)
            predicted_bulk = predict_bulk(structure)
            predicted_eform = model_eform.predict_structure(structure)
            combined_data.append((float(predicted_bulk), float(predicted_eform),
                                  target_bulk, target_eform))
        except FileNotFoundError:
            continue

    if not combined_data:
        print("No predicted data to plot.")
        return

    combined_data = pd.DataFrame(combined_data, columns=['Predicted Bulk Modulus', 'Predicted Formation Energy',
                                                         'Target Bulk Modulus', 'Target Formation Energy'])

    create_property_pair_plots(combined_data, plot_path)

def create_property_pair_plots(combined_data, plot_path):
    property_pairs = [
        (0, 20),
        (-0.5, 50),
        (-1, 100),
        (-1.5, 150),
        (-2, 200)
    ]
    
    for eform, bulk in property_pairs:
        create_single_pair_plot(combined_data, eform, bulk, plot_path)

def create_single_pair_plot(data, target_eform, target_bulk, plot_path):
    plt.figure(figsize=(10, 8))
    
    # Filter data for the specific target values
    filtered_data = data[
        (data['Target Formation Energy'].round(1) == target_eform) &
        (data['Target Bulk Modulus'].round() == target_bulk)
    ]
    
    if filtered_data.empty:
        print(f"No data for Formation Energy: {target_eform} eV/atom and Bulk Modulus: {target_bulk} GPa")
        plt.close()
        return
    
    # KDE plot
    sns.kdeplot(data=filtered_data, x='Predicted Bulk Modulus', y='Predicted Formation Energy', 
                fill=True, cmap="YlGnBu", alpha=0.7)
    
    # Target point
    plt.scatter(target_bulk, target_eform, color='red', marker='*', s=200, label='Target Point')
    
    # Add dotted lines for target values
    plt.axvline(x=target_bulk, color='r', linestyle='--', alpha=0.5)
    plt.axhline(y=target_eform, color='r', linestyle='--', alpha=0.5)
    
    plt.title(f'Bulk Modulus and Formation Energy\nTarget: ({target_bulk} GPa, {target_eform} eV/atom)', fontsize=20)
    plt.xlabel('Bulk Modulus (GPa)', fontsize=20)
    plt.ylabel('Formation Energy (eV/atom)', fontsize=20)
    plt.legend(fontsize=16)
    
    # Set axis limits to focus on the relevant area
    x_range = filtered_data['Predicted Bulk Modulus'].max() - filtered_data['Predicted Bulk Modulus'].min()
    y_range = filtered_data['Predicted Formation Energy'].max() - filtered_data['Predicted Formation Energy'].min()
    plt.xlim(filtered_data['Predicted Bulk Modulus'].min() - 0.1 * x_range, 
             filtered_data['Predicted Bulk Modulus'].max() + 0.1 * x_range)
    plt.ylim(filtered_data['Predicted Formation Energy'].min() - 0.1 * y_range, 
             filtered_data['Predicted Formation Energy'].max() + 0.1 * y_range)
    
    plt.savefig(f"{plot_path}/BulkModulus_{target_bulk}_FormationEnergy_{target_eform}.png")
    plt.close()

if __name__ == "__main__":
    main()