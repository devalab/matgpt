# import smact
# from smact.screening import pauling_test
# from pymatgen.core import Structure
# import pandas as pd
# import matplotlib.pyplot as plt
# from collections import Counter
# import numpy as np
# import itertools
# from invcryrep.invcryrep import InvCryRep
# from tqdm import tqdm
# import hydra
# from omegaconf import DictConfig, OmegaConf
# import os

# @hydra.main(config_path="config", config_name="default", version_base=None)
# def main(cfg: DictConfig):
#     # SMACT Validity Functions
#     def smact_validity(comp, count, use_pauling_test=True, include_alloys=True):
#         elem_symbols = tuple(comp)
#         space = smact.element_dictionary(elem_symbols)
#         smact_elems = [e[1] for e in space.items()]
#         electronegs = [e.pauling_eneg for e in smact_elems]
#         ox_combos = [e.oxidation_states for e in smact_elems]
#         if len(set(elem_symbols)) == 1:
#             return True
#         if include_alloys:
#             is_metal_list = [elem_s in smact.metals for elem_s in elem_symbols]
#             if all(is_metal_list):
#                 return True
#         threshold = np.max(count)
#         oxn = 1
#         for oxc in ox_combos:
#             oxn *= len(oxc)
#         if oxn > 1e7:
#             return False
#         for ox_states in itertools.product(*ox_combos):
#             stoichs = [(c,) for c in count]
#             cn_e, cn_r = smact.neutral_ratios(
#                 ox_states, stoichs=stoichs, threshold=threshold)
#             if cn_e:
#                 if use_pauling_test:
#                     try:
#                         electroneg_OK = pauling_test(ox_states, electronegs)
#                     except TypeError:
#                         electroneg_OK = True
#                 else:
#                     electroneg_OK = True
#                 if electroneg_OK:
#                     return True
#         return False

#     def structure_validity(crystal, cutoff=0.5):
#         dist_mat = crystal.distance_matrix
#         dist_mat = dist_mat + np.diag(np.ones(dist_mat.shape[0]) * (cutoff + 10.))
#         if dist_mat.min() < cutoff or crystal.volume < 0.1:
#             return False
#         else:
#             return True

#     def is_valid(struct):
#         atom_types = [str(specie) for specie in struct.species]
#         elem_counter = Counter(atom_types)
#         composition = [(elem, elem_counter[elem]) for elem in sorted(elem_counter.keys())]
#         elems, counts = list(zip(*composition))
#         counts = np.array(counts)
#         counts = counts / np.gcd.reduce(counts)
#         comps = tuple(counts.astype("int").tolist())

#         comp_valid = smact_validity(elems, comps)
#         struct_valid = structure_validity(struct)
#         return comp_valid and struct_valid

#     # Uniqueness Check Functions
#     def read_slices_from_df(df, column_name):
#         return df[column_name].tolist()

#     def canonicalize_slices(slices_strings, backend):
#         canonical_slices = []
#         for s in tqdm(slices_strings, desc="Canonicalizing SLICES"):
#             try:
#                 canonical_slice = backend.get_canonical_SLICES(s)
#                 canonical_slices.append(canonical_slice)
#             except Exception as e:
#                 print(f"Skipping SLICES string due to error: {e}")
#         return canonical_slices

#     def check_uniqueness(canonical_generated_slices, canonical_true_slices):
#         unique_generated_slices = set(canonical_generated_slices)
#         unique_true_slices = set(canonical_true_slices)
#         unique_new_slices = unique_generated_slices - unique_true_slices
#         return len(unique_new_slices), unique_new_slices

#     # Read the CSV files
#     try:
#         df_gen = pd.read_csv(os.path.join("sample/output_structures", cfg.back_to_cif.reconstructed))
#         df_true = pd.read_csv(cfg.data_path.fname)
#     except FileNotFoundError as e:
#         print(f"Error: Unable to read CSV file. {e}")
#         return

#     # SMACT Validity Check
#     properties = cfg.sample.properties
#     num_structures_per_property = cfg.sample.number_sequences
#     structures_dict = {}

#     # Convert properties to a list of lists if it's a single list
#     if not any(isinstance(prop, list) for prop in properties):
#         properties = [[prop] for prop in properties]

#     if 'CIF Path' not in df_gen.columns:
#         print("Warning: 'CIF Path' column not found in the generated data CSV.")
#         print("Available columns:", df_gen.columns.tolist())
#         print("Skipping SMACT validity check.")
#     else:
#         for i, prop in enumerate(properties):
#             cif_paths = df_gen['CIF Path'].iloc[i*num_structures_per_property:(i+1)*num_structures_per_property].tolist()
#             structures_dict[tuple(prop)] = []
#             for cif_path in cif_paths:
#                 try:
#                     structures_dict[tuple(prop)].append(Structure.from_file(cif_path))
#                 except Exception as e:
#                     print(f"Error loading structure from {cif_path}: {e}")

#         validity_results = {tuple(prop): [] for prop in properties}

#         for prop, structures in structures_dict.items():
#             for struct in structures:
#                 try:
#                     is_valid_structure = is_valid(struct)
#                     validity_results[prop].append(is_valid_structure)
#                 except Exception as e:
#                     print(f"Error checking validity for structure: {e}")

#         # Print validity results
#         for prop, results in validity_results.items():
#             if results:
#                 print(f"Property: {prop}, Valid Structures: {sum(results)}/{len(results)}")
#             else:
#                 print(f"Property: {prop}, No valid structures found")

#         # Extract validity percentages for plotting
#         validity_percentages = {prop: sum(results)/len(results) if results else 0 for prop, results in validity_results.items()}

#         # Plotting the validity percentages as a bar histogram
#         plt.figure(figsize=(12, 8))
#         properties_str = [str(prop).replace('[', '(').replace(']', ')') for prop in properties]
#         percentages = [validity_percentages[tuple(prop)] for prop in properties]

#         x = np.arange(len(properties))
#         width = 0.4

#         bars = plt.bar(x, percentages, width, color='blue')

#         # Adding numbers on top of bars
#         for i, bar in enumerate(bars):
#             yval = bar.get_height()
#             plt.text(bar.get_x() + bar.get_width()/2, yval + 0.01, f'{yval:.2%}', va='bottom', ha='center', fontsize=12)

#         # Formatting plot
#         plt.xlabel('Property', fontsize=14)
#         plt.ylabel('Validity Percentage', fontsize=14)
#         plt.title('Validity Metrics for Different Properties', fontsize=16)
#         plt.xticks(x, properties_str, fontsize=12, rotation=45, ha='right')
#         plt.yticks(fontsize=12)

#         plt.tight_layout()
#         os.makedirs(os.path.dirname(cfg.proxy_model.plot_path), exist_ok=True)
#         plt.savefig(f"{cfg.proxy_model.plot_path}/validity_metrics.png")
#         plt.close()

#     # Uniqueness Check
#     try:
#         backend = InvCryRep(graph_method='econnn')

#         # Use "SLICES" for generated data and cfg.training.slices for true data
#         generated_slices_strings = read_slices_from_df(df_gen, "SLICES")
#         true_slices_strings = read_slices_from_df(df_true, cfg.training.slices)

#         canonical_generated_slices = canonicalize_slices(generated_slices_strings, backend)
#         canonical_true_slices = canonicalize_slices(true_slices_strings, backend)

#         num_unique_new, unique_new_slices = check_uniqueness(canonical_generated_slices, canonical_true_slices)

#         print(f"Total Generated Slices: {len(canonical_generated_slices)}")
#         print(f"Unique New Slices (not in training data): {num_unique_new}")

#         # Plotting the uniqueness results
#         labels = ['Total Generated', 'Unique New']
#         counts = [len(canonical_generated_slices), num_unique_new]
#         plt.figure(figsize=(12, 8))
#         bars = plt.bar(labels, counts, color='blue', width=0.4)

#         # Adding numbers on top of bars
#         for bar in bars:
#             yval = bar.get_height()
#             plt.text(bar.get_x() + bar.get_width()/2, yval + 0.01, int(yval), va='bottom', ha='center', fontsize=12)

#         # Formatting plot
#         plt.xlabel('Categories', fontsize=14)
#         plt.ylabel('Counts', fontsize=14)
#         plt.title('Uniqueness of Generated Slices', fontsize=16)
#         plt.tight_layout()
#         plt.savefig(f"{cfg.proxy_model.plot_path}/uniqueness_metrics.png")
#         plt.close()
#     except Exception as e:
#         print(f"Error during uniqueness check: {e}")

# if __name__ == "__main__":
#     main()