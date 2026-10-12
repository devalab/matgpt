"""Table metrics for multi-property generation (Tables 4-7).

Run after sli_to_cif.py and the proxy script for the same config, e.g.
    python metrics.py --config-name form_bulk

Reads the reconstructed CSV (with the Predicted_* / Actual_Crystal_System columns added by
the proxy script) and reports the following for each target pair in sample.properties. As in
the paper's tables, the counts use the reconstructed structures that the proxy script could
evaluate:
  Validity    evaluated structures / requested sequences (sample.number_sequences)
  Uniqueness  distinct SLICES strings (whitespace-normalized) / requested sequences
  Novelty     no StructureMatcher match in the training set (utils/novelty.py), relative to
              the requested sequences or the evaluated structures (metrics.novelty_relative_to)
  Errors      per property: MAE, median absolute error, RMSE, mean signed error
              (prediction - target), MAPE and the hit rate within +/- metrics.hit_tolerances
              (null skips it); joint_hit_rate_percent when two tolerances are set
  Match rate  crystal system targets only: Actual_Crystal_System == target, over the
              evaluated structures that SpacegroupAnalyzer could classify
"""
import math
import os
from statistics import median

import numpy as np
import pandas as pd
import hydra
from omegaconf import DictConfig
from pymatgen.core.structure import Structure
from tqdm import tqdm

from utils.novelty import build_training_db, is_novel, make_matcher

CRYSTAL_SYSTEM_COLUMN = "crystal_system_encoded"


def add_novelty(data, training_cifs, cif_column):
    """Is_Novel = 1/0 per reconstructed structure (empty if it cannot be read or no training data)."""
    training_db = build_training_db(training_cifs, cif_column)
    sm = make_matcher()
    flags = []
    for cif_path in tqdm(data["CIF Path"], desc="Checking novelty"):
        try:
            flags.append(is_novel(Structure.from_file(cif_path), training_db, sm) if training_db else None)
        except Exception:
            flags.append(None)
    data["Is_Novel"] = flags
    return data


def error_metrics(name, predictions, target, tolerance=None):
    predictions = [p for p in pd.to_numeric(predictions, errors="coerce") if math.isfinite(p)]
    errors = [p - target for p in predictions]
    n = len(errors)
    return {
        f"{name}_finite_predictions": n,
        f"{name}_mae": sum(abs(e) for e in errors) / n if n else math.nan,
        f"{name}_median_absolute_error": median(abs(e) for e in errors) if n else math.nan,
        f"{name}_rmse": math.sqrt(sum(e * e for e in errors) / n) if n else math.nan,
        f"{name}_mean_signed_error": sum(errors) / n if n else math.nan,
        f"{name}_mape_percent": 100.0 * sum(abs(e) for e in errors) / n / abs(target) if n and target != 0 else math.nan,
        # the small margin keeps errors that equal the tolerance (up to float rounding) inside it
        f"{name}_hit_rate_percent": 100.0 * sum(abs(e) <= tolerance + 1e-9 for e in errors) / n if n and tolerance is not None else math.nan,
    }


@hydra.main(config_path="config", config_name="form_band", version_base=None)
def main(cfg: DictConfig):
    csv_path = cfg.proxy_model.csv_path
    data = pd.read_csv(csv_path)
    data = data.dropna(subset=["CIF Path"])
    target_cols = list(cfg.training.selected_properties)
    pred_cols = list(cfg.metrics.prediction_columns)     # same order as selected_properties
    tolerances = list(cfg.metrics.hit_tolerances)        # same order; null = no hit rate
    requested = int(cfg.sample.number_sequences)
    relative_to = cfg.metrics.novelty_relative_to
    if relative_to not in ("reconstructed", "requested"):
        raise ValueError(f"metrics.novelty_relative_to must be 'reconstructed' or 'requested', not {relative_to!r}")
    missing = [c for c in pred_cols if c not in data.columns]
    if missing:
        raise SystemExit(f"Columns {missing} not found in {csv_path}; run the proxy script for this config first.")

    # Novelty is checked against the training set itself; saved so it is computed only once
    if "Is_Novel" not in data.columns or data["Is_Novel"].isna().all():
        data = add_novelty(data, cfg.proxy_model.training_cifs, cfg.proxy_model.training_cif_column)
        data.to_csv(csv_path, index=False)
    has_novelty = pd.to_numeric(data["Is_Novel"], errors="coerce").notna().any()

    results = []
    for pair in cfg.sample.properties:
        mask = np.ones(len(data), dtype=bool)
        for col, value in zip(target_cols, pair):
            mask &= np.isclose(pd.to_numeric(data[col], errors="coerce"), float(value))
        rows = data[mask]
        evaluated = rows[rows[pred_cols].apply(pd.to_numeric, errors="coerce").notna().all(axis=1)]
        if len(rows) == 0:
            print(f"Warning: no reconstructed structures for target pair {list(pair)}")

        n_unique = len({" ".join(str(s).split()) for s in evaluated["SLICES"].dropna()})
        novel = pd.to_numeric(evaluated["Is_Novel"], errors="coerce")
        n_novel = int(novel.sum()) if has_novelty else None
        novelty_base = len(evaluated) if relative_to == "reconstructed" else requested

        result = {col: value for col, value in zip(target_cols, pair)}
        result.update({
            "requested": requested,
            "reconstructed": len(rows),
            "evaluated": len(evaluated),
            "validity_percent": 100.0 * len(evaluated) / requested,
            "unique_slices": n_unique,
            "uniqueness_percent": 100.0 * n_unique / requested,
            "novel": n_novel,
            "novelty_percent": 100.0 * n_novel / novelty_base if n_novel is not None and novelty_base else math.nan,
        })

        hits = []
        for col, value, pred_col, tolerance in zip(target_cols, pair, pred_cols, tolerances):
            if col == CRYSTAL_SYSTEM_COLUMN:
                actual = pd.to_numeric(evaluated[pred_col], errors="coerce")
                classified = actual[actual > 0]
                matched = int((classified == int(value)).sum())
                result.update({
                    "crystal_system_classified": len(classified),
                    "crystal_system_matched": matched,
                    "match_rate_percent": 100.0 * matched / len(classified) if len(classified) else math.nan,
                })
            else:
                name = pred_col.replace("Predicted_", "").lower()   # e.g. formation_energy_mae, pbe_mae
                result.update(error_metrics(name, evaluated[pred_col], float(value), tolerance))
                if tolerance is not None:
                    predicted = pd.to_numeric(evaluated[pred_col], errors="coerce")
                    hits.append((predicted.notna(), (predicted - float(value)).abs() <= tolerance + 1e-9))
        if len(hits) == 2:
            (finite_a, hit_a), (finite_b, hit_b) = hits
            n_both = int((finite_a & finite_b).sum())
            result["joint_hit_rate_percent"] = 100.0 * (hit_a & hit_b).sum() / n_both if n_both else math.nan
        results.append(result)

    table = pd.DataFrame(results)
    os.makedirs(os.path.dirname(cfg.metrics.output_csv) or ".", exist_ok=True)
    table.to_csv(cfg.metrics.output_csv, index=False)
    print(table.round(4).to_string(index=False))
    print(f"\nNovelty is relative to the {relative_to} structures. Saved to {cfg.metrics.output_csv}")


if __name__ == "__main__":
    main()
