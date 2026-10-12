# utils/novelty.py
# Novelty check against the training CSV, same procedure as form_proxy.py / bulk_proxy.py
# in ../mat: primitive standard cells, same reduced formula, StructureMatcher
# (ltol=0.2, stol=0.3, angle_tol=5).
import os
import pandas as pd
from tqdm import tqdm
from pymatgen.core.structure import Structure
from pymatgen.symmetry.analyzer import SpacegroupAnalyzer
from pymatgen.analysis.structure_matcher import StructureMatcher, ElementComparator


def make_matcher():
    return StructureMatcher(ltol=0.2, stol=0.3, angle_tol=5, primitive_cell=True, scale=True,
                            attempt_supercell=False, comparator=ElementComparator())


def build_training_db(training_cifs_path, cif_column="cif"):
    training_db = {}
    if not os.path.exists(training_cifs_path):
        print(f"Warning: Training CIF file '{training_cifs_path}' not found. Novelty checking will be skipped.")
        return training_db
    train_data = pd.read_csv(training_cifs_path)
    if cif_column not in train_data.columns:
        print(f"Column '{cif_column}' not found in {training_cifs_path}. Columns: {list(train_data.columns)}")
        return training_db
    if 'status' in train_data.columns:
        train_data = train_data[train_data['status'] == 'success']
    for _, row in tqdm(train_data.iterrows(), total=len(train_data), desc="Building Training DB"):
        try:
            if pd.isna(row[cif_column]):
                continue
            prim = SpacegroupAnalyzer(Structure.from_str(row[cif_column], fmt="cif")).get_primitive_standard_structure()
            training_db.setdefault(prim.composition.reduced_formula, []).append(prim)
        except Exception:
            continue
    print(f"Loaded {len(training_db)} unique chemical compositions from the training set.")
    return training_db


def is_novel(structure, training_db, sm):
    eval_struc = structure
    try:
        eval_struc = SpacegroupAnalyzer(structure).get_primitive_standard_structure()
    except Exception:
        pass
    for candidate in training_db.get(eval_struc.composition.reduced_formula, []):
        try:
            if sm.fit(candidate, eval_struc):
                return 0
        except Exception:
            pass
    return 1
