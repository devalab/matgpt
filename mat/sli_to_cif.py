from slices.core import SLICES
from pymatgen.core.structure import Structure
import pandas as pd
from tqdm import tqdm
import os
import matplotlib.pyplot as plt
import numpy as np
import hydra
from omegaconf import DictConfig, OmegaConf

@hydra.main(config_path="config", config_name="default", version_base=None)
def main(cfg: DictConfig):
    try:
        data_path = cfg.back_to_cif.file_path
        output_folder = cfg.back_to_cif.output_folder
        plot_targeted_reconstructions(data_path, output_folder, cfg)
    except Exception as e:
        print(f"An error occurred: {str(e)}")

def convert_and_save_structures(data_path, output_folder, cfg):
    data = pd.read_csv(data_path)
    backend = SLICES()
    reconstructed_data = []
    property_reconstructions = {}
    cif_folder = os.path.join(output_folder, "cif_files")
    if not os.path.exists(cif_folder):
        os.makedirs(cif_folder)

    # Get the property column names (all columns that aren't 'Sequence')
    property_columns = [col for col in data.columns if col != 'Sequence']

    for index, row in tqdm(data.iterrows(), total=data.shape[0], desc="Processing sequences"):
        property_values = tuple(row[col] for col in property_columns)
        sequence = row['Sequence']
        try:
            structure, final_energy_per_atom_IAP = backend.SLICES2structure(sequence)
            if final_energy_per_atom_IAP != 0:
                # Save structure to CIF in the specified subfolder
                file_path = os.path.join(cif_folder, f"{index}.cif")
                structure.to(fmt="cif", filename=file_path)
                # Record data for plotting and saving
                reconstructed_data.append({**{col: val for col, val in zip(property_columns, property_values)}, 
                                           'SLICES': sequence, 'CIF Path': file_path})
                property_reconstructions[property_values] = property_reconstructions.get(property_values, 0) + 1
        except Exception as e:
            print(f"An error occurred with sequence: {sequence} - {e}")

    # Save the successful reconstructions to a CSV file
    reconstructed_df = pd.DataFrame(reconstructed_data)
    reconstructed_df.to_csv(os.path.join(output_folder, cfg.back_to_cif.reconstructed), index=False)
    
    return property_reconstructions, reconstructed_df, property_columns

def plot_targeted_reconstructions(data_path, output_folder, cfg):
    data = pd.read_csv(data_path)
    property_reconstructions, _, property_columns = convert_and_save_structures(data_path, output_folder, cfg)
    
    target_properties = sorted(property_reconstructions.keys())
    
    # Create a figure with subplots for each property
    fig, axes = plt.subplots(len(property_columns), 1, figsize=(12, 6*len(property_columns)), squeeze=False)
    
    for i, property_column in enumerate(property_columns):
        ax = axes[i, 0]
        
        # Extract the i-th element from each tuple for the current property
        property_values = [prop[i] for prop in target_properties]
        reconstruction_counts = [property_reconstructions[prop] for prop in target_properties]
        
        bar_width = 0.8
        colors = plt.cm.viridis(np.linspace(0, 1, len(property_values)))
        
        bars = ax.bar(range(len(property_values)), reconstruction_counts, color=colors, width=bar_width)
        
        # Add the counts above the bars
        for j, bar in enumerate(bars):
            height = bar.get_height()
            ax.annotate(f'{height}',
                        xy=(bar.get_x() + bar.get_width() / 2, height),
                        xytext=(0, 3),  # 3 points vertical offset
                        textcoords="offset points",
                        ha='center', va='bottom')
        
        ax.set_xlabel(property_column)
        ax.set_ylabel('Number of Successful Conversions')
        ax.set_title(f'Successful Structure Conversions by {property_column}')
        ax.set_xticks(range(len(property_values)))
        ax.set_xticklabels([f'{prop:.2f}' for prop in property_values], rotation=45)
    
    plt.tight_layout()
    plt.savefig(os.path.join(output_folder, cfg.back_to_cif.plot_name))
    plt.close()

if __name__ == "__main__":
    main()