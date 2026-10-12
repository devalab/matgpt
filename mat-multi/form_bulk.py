import pandas as pd
from pymatgen.core.structure import Structure
import matplotlib.pyplot as plt
import seaborn as sns
import matgl
import matgl.utils.io
# matgl 1.1.3 downloads its pretrained models from the main branch of the matgl GitHub repository, where they no
# longer exist (removed in matgl 3.0). Load the same files from the v1.1.3 tag; models in ~/.cache/matgl are reused.
matgl.utils.io.PRETRAINED_MODELS_BASE_URL = "https://raw.githubusercontent.com/materialsvirtuallab/matgl/v1.1.3/pretrained_models/"
import hydra
from omegaconf import DictConfig
import numpy as np
import warnings
from tqdm import tqdm

warnings.filterwarnings("ignore", category=UserWarning)

@hydra.main(config_path="config", config_name="form_bulk", version_base=None)
def main(cfg: DictConfig):
    try:
        csv_path = cfg.proxy_model.csv_path
        bulk_model_name = cfg.proxy_model.model_bulk_modulus
        eform_model_name = cfg.proxy_model.model_eform
        plot_path = cfg.proxy_model.plot_path
        eform_column, bulk_column = cfg.training.selected_properties   # target columns, same order as sample.properties
        property_pairs = [tuple(p) for p in cfg.sample.properties]     # [formation energy, bulk modulus]
        load_structures_predict_and_plot(csv_path, bulk_model_name, eform_model_name, plot_path,
                                         eform_column, bulk_column, property_pairs)
    except Exception as e:
        print(f"An error occurred: {str(e)}")
        raise

def load_structures_predict_and_plot(csv_path, bulk_model_name, eform_model_name, plot_path,
                                     eform_column, bulk_column, property_pairs):
    data = pd.read_csv(csv_path)
    data = data.dropna(subset=['CIF Path'])

    model_eform = matgl.load_model(eform_model_name)

    from megnet.utils.models import load_model as load_megnet_model
    model_bulk = load_megnet_model(bulk_model_name)
    # The model predicts log10 of the bulk modulus in GPa
    predict_bulk = lambda structure: 10 ** model_bulk.predict_structure(structure).ravel()[0]

    # Predictions are written back into the CSV (read by metrics.py)
    data['Predicted_Formation_Energy'] = None
    data['Predicted_Bulk_Modulus'] = None
    combined_data = []

    for index, row in tqdm(data.iterrows(), total=len(data), desc="Predicting"):
        cif_path = row['CIF Path']
        target_bulk = float(row[bulk_column])
        target_eform = float(row[eform_column])
        try:
            structure = Structure.from_file(cif_path)
            predicted_bulk = float(predict_bulk(structure))
            predicted_eform = float(model_eform.predict_structure(structure))
        except Exception as e:
            print(f"Skipping {cif_path}: {e}")
            continue
        data.at[index, 'Predicted_Formation_Energy'] = predicted_eform
        data.at[index, 'Predicted_Bulk_Modulus'] = predicted_bulk
        combined_data.append((predicted_bulk, predicted_eform, target_bulk, target_eform))

    data.to_csv(csv_path, index=False)
    print(f"Updated CSV saved with predictions at: {csv_path}")

    if not combined_data:
        print("No predicted data to plot.")
        return

    combined_data = pd.DataFrame(combined_data, columns=['Predicted Bulk Modulus', 'Predicted Formation Energy',
                                                         'Target Bulk Modulus', 'Target Formation Energy'])

    for eform, bulk in property_pairs:
        create_single_pair_plot(combined_data, eform, bulk, plot_path)

def create_single_pair_plot(data, target_eform, target_bulk, plot_path):
    plt.figure(figsize=(10, 8))

    # Filter data for the specific target values
    filtered_data = data[
        np.isclose(data['Target Formation Energy'], target_eform) &
        np.isclose(data['Target Bulk Modulus'], target_bulk)
    ]

    if len(filtered_data) < 2:
        print(f"Not enough data for Formation Energy: {target_eform} eV/atom and Bulk Modulus: {target_bulk} GPa")
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

    # Set axis limits to focus on the relevant area (predictions and the target point)
    x_min = min(filtered_data['Predicted Bulk Modulus'].min(), target_bulk)
    x_max = max(filtered_data['Predicted Bulk Modulus'].max(), target_bulk)
    y_min = min(filtered_data['Predicted Formation Energy'].min(), target_eform)
    y_max = max(filtered_data['Predicted Formation Energy'].max(), target_eform)
    plt.xlim(x_min - 0.1 * (x_max - x_min), x_max + 0.1 * (x_max - x_min))
    plt.ylim(y_min - 0.1 * (y_max - y_min), y_max + 0.1 * (y_max - y_min))

    plt.savefig(f"{plot_path}/BulkModulus_{target_bulk}_FormationEnergy_{target_eform}.png")
    plt.close()

if __name__ == "__main__":
    main()
