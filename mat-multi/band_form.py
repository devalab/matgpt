import pandas as pd
from pymatgen.core.structure import Structure
import matplotlib.pyplot as plt
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
from tqdm import tqdm

# Fidelity index of the multi-fidelity MEGNet model; the paper uses PBE (Predicted_PBE)
METHODS = ["PBE", "GLLB-SC", "HSE", "SCAN"]

@hydra.main(config_path="config", config_name="form_band", version_base=None)
def main(cfg: DictConfig):
    try:
        csv_path = cfg.proxy_model.csv_path
        model_bandgap = cfg.proxy_model.model_band
        model_eform = cfg.proxy_model.model_eform
        plot_path = cfg.proxy_model.plot_path
        eform_column, band_gap_column = cfg.training.selected_properties   # target columns, same order as sample.properties
        property_pairs = [tuple(p) for p in cfg.sample.properties]        # [formation energy, band gap]
        load_structures_predict_and_plot_combined_kde(csv_path, model_bandgap, model_eform, plot_path,
                                                      eform_column, band_gap_column, property_pairs)
    except Exception as e:
        print(f"An error occurred: {str(e)}")
        raise

def load_structures_predict_and_plot_combined_kde(csv_path, model_bandgap, model_eform, plot_path,
                                                  eform_column, band_gap_column, property_pairs):
    data = pd.read_csv(csv_path)
    data = data.dropna(subset=['CIF Path'])

    model_band = matgl.load_model(model_bandgap)
    model_form = matgl.load_model(model_eform)

    # Predictions are written back into the CSV (read by metrics.py)
    data['Predicted_Formation_Energy'] = None
    for method in METHODS:
        data[f'Predicted_{method}'] = None

    method_data = {method: {'predicted_bandgaps': [], 'predicted_eforms': []} for method in METHODS}
    target_bandgaps = []
    target_eforms = []

    for index, row in tqdm(data.iterrows(), total=len(data), desc="Predicting"):
        cif_path = row['CIF Path']
        target_bandgap = float(row[band_gap_column])
        target_eform = float(row[eform_column])

        try:
            structure = Structure.from_file(cif_path)
            predicted_eform = float(model_form.predict_structure(structure))
            predicted = [float(model_band.predict_structure(structure=structure, state_attr=torch.tensor([i])))
                         for i in range(len(METHODS))]
        except Exception as e:
            print(f"Skipping {cif_path}: {e}")
            continue

        data.at[index, 'Predicted_Formation_Energy'] = predicted_eform
        for method, predicted_bandgap in zip(METHODS, predicted):
            data.at[index, f'Predicted_{method}'] = predicted_bandgap
            method_data[method]['predicted_bandgaps'].append(predicted_bandgap)
            method_data[method]['predicted_eforms'].append(predicted_eform)

        target_bandgaps.append(target_bandgap)
        target_eforms.append(target_eform)

    data.to_csv(csv_path, index=False)
    print(f"Updated CSV saved with predictions at: {csv_path}")

    if not target_bandgaps:
        print("No predicted data to plot.")
        return

    # Joint distribution for each target pair (PBE band gap, as in Fig. 10)
    pbe = pd.DataFrame({'Predicted Band Gap': method_data['PBE']['predicted_bandgaps'],
                        'Predicted Formation Energy': method_data['PBE']['predicted_eforms'],
                        'Target Band Gap': target_bandgaps,
                        'Target Formation Energy': target_eforms})
    for eform, band in property_pairs:
        create_single_pair_plot(pbe, eform, band, plot_path)

    # Create combined KDE plot for each method
    for method in METHODS:
        plt.figure(figsize=(12, 8))

        # Plot predicted values
        sns.kdeplot(x=method_data[method]['predicted_bandgaps'],
                    y=method_data[method]['predicted_eforms'],
                    cmap="YlGnBu", fill=True, cbar=True, label="Predicted")

        # Plot target values
        sns.scatterplot(x=target_bandgaps, y=target_eforms, color='red', alpha=0.6, label="Target")

        plt.title(f'Combined KDE Plot: Bandgap vs Formation Energy ({method})')
        plt.xlabel('Bandgap (eV)')
        plt.ylabel('Formation Energy (eV/atom)')
        plt.legend()

        plt.savefig(f"{plot_path}/Combined_KDE_Bandgap_vs_FormationEnergy_{method}.png")
        plt.close()

def create_single_pair_plot(data, target_eform, target_band, plot_path):
    filtered_data = data[
        np.isclose(data['Target Formation Energy'], target_eform) &
        np.isclose(data['Target Band Gap'], target_band)
    ]

    if len(filtered_data) < 2:
        print(f"Not enough data for Formation Energy: {target_eform} eV/atom and Band Gap: {target_band} eV")
        return

    plt.figure(figsize=(10, 8))
    sns.kdeplot(data=filtered_data, x='Predicted Band Gap', y='Predicted Formation Energy',
                fill=True, cmap="YlGnBu", alpha=0.7, cbar=True)

    # Target point
    plt.scatter(target_band, target_eform, color='red', marker='*', s=200, label='Target Point')
    plt.axvline(x=target_band, color='r', linestyle='--', alpha=0.5)
    plt.axhline(y=target_eform, color='r', linestyle='--', alpha=0.5)

    plt.title(f'Band Gap and Formation Energy\nTarget: ({target_band} eV, {target_eform} eV/atom)', fontsize=20)
    plt.xlabel('Band Gap (eV)', fontsize=20)
    plt.ylabel('Formation Energy (eV/atom)', fontsize=20)
    plt.legend(fontsize=16)

    plt.savefig(f"{plot_path}/BandGap_{target_band}_FormationEnergy_{target_eform}.png")
    plt.close()

if __name__ == "__main__":
    main()
