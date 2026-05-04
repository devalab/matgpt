import pandas as pd
from pymatgen.core.structure import Structure
import matplotlib.pyplot as plt
import seaborn as sns
import matgl
import torch
import hydra
from omegaconf import DictConfig, OmegaConf
import numpy as np

@hydra.main(config_path="config", config_name="default", version_base=None)
def main(cfg: DictConfig):
    try:
        csv_path = cfg.proxy_model.csv_path
        model_bandgap = cfg.proxy_model.model_band
        model_eform = cfg.proxy_model.model_eform
        plot_path = cfg.proxy_model.plot_path
        load_structures_predict_and_plot_combined_kde(csv_path, model_bandgap, model_eform, plot_path)
    except Exception as e:
        print(f"An error occurred: {str(e)}")

def load_structures_predict_and_plot_combined_kde(csv_path, model_bandgap, model_eform, plot_path):
    data = pd.read_csv(csv_path)
    data = data.dropna(subset=['CIF Path'])
    
    band_gap_column = 'band_gap'
    eform_column = [col for col in data.columns if col not in ['CIF Path', 'SLICES', band_gap_column]][0]
    
    model_band = matgl.load_model(model_bandgap)
    model_form = matgl.load_model(model_eform)
    
    methods = ["PBE", "GLLB-SC", "HSE", "SCAN"]
    method_data = {method: {'predicted_bandgaps': [], 'predicted_eforms': []} for method in methods}
    target_bandgaps = []
    target_eforms = []

    for index, row in data.iterrows():
        cif_path = row['CIF Path']
        target_bandgap = float(row[band_gap_column])
        target_eform = float(row[eform_column])
        
        try:
            structure = Structure.from_file(cif_path)
            
            for i, method in enumerate(methods):
                graph_attrs = torch.tensor([i])
                predicted_bandgap = model_band.predict_structure(structure=structure, state_attr=graph_attrs)
                predicted_eform = model_form.predict_structure(structure)
                
                method_data[method]['predicted_bandgaps'].append(float(predicted_bandgap))
                method_data[method]['predicted_eforms'].append(float(predicted_eform))
            
            target_bandgaps.append(target_bandgap)
            target_eforms.append(target_eform)
            
        except FileNotFoundError:
            print(f"File not found: {cif_path}")
            continue

    # Create combined KDE plot for each method
    for method in methods:
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

    # Create a single plot with all methods
    plt.figure(figsize=(15, 10))
    
    for method in methods:
        sns.kdeplot(x=method_data[method]['predicted_bandgaps'], 
                    y=method_data[method]['predicted_eforms'], 
                    cmap="YlGnBu",fill=True, alpha=0.5, label=method)
    
    sns.scatterplot(x=target_bandgaps, y=target_eforms, color='red', alpha=0.6, label="Target")
    
    plt.title('Combined KDE Plot: Bandgap vs Formation Energy (All Methods)')
    plt.xlabel('Bandgap (eV)')
    plt.ylabel('Formation Energy (eV/atom)')
    plt.legend()
    
    plt.savefig(f"{plot_path}/Combined_KDE_Bandgap_vs_FormationEnergy_All_Methods.png")
    plt.close()

if __name__ == "__main__":
    main()