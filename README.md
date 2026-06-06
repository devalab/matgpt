![MatGPT banner](assets/matgpt-banner.png)

# MatGPT

MatGPT is a transformer-based framework for property-conditioned generation of inorganic crystal structures. It represents crystals as SLICES strings, trains GPT-style decoder models on structure-property data, samples new SLICES strings for target property values, reconstructs generated structures, and evaluates them with proxy property models.

This repository contains the reusable code. Datasets, trained weights, checkpoints, logs, generated samples, reconstructed CIF files, and plots are kept outside Git and should be supplied separately for reproduction.

## Repository Layout

```text
MatGPT/
  mat/                  # single-property conditioning
    train.py
    sample_property.py
    sli_to_cif.py
    form_proxy.py
    band_proxy.py
    bulk_proxy.py
    metrics.py
    config/default.yaml
    utils/
    dataset/
    weights/

  mat-multi/            # multi-property conditioning
    train.py
    sample_property.py
    sli_to_cif.py
    band_form.py
    form_bulk.py
    crystal_form.py
    crystal_band.py
    crystal_bulk.py
    form_proxy.py
    band_proxy.py
    metrics.py
    config/default.yaml
    utils/
    dataset/
    weights/
```

Use `mat/` when conditioning on one property. Use `mat-multi/` when conditioning on more than one value, including cases where one value is an encoded crystal system.

## Data and Weights

Processed datasets and trained weights are distributed separately from this code repository. Place them in the following folders before running the scripts:

```text
mat/dataset/
mat/weights/
mat-multi/dataset/
mat-multi/weights/
```

The source databases used to prepare materials data can be accessed here:

- [Materials Project](https://www.materialsproject.org/)
- [Alexandria Materials Database](https://alexandria.icams.rub.de/)

Processed datasets and trained weights are available on Hugging Face: [harshasatyavardhan/matgpt_datasets](https://huggingface.co/datasets/harshasatyavardhan/matgpt_datasets).

Each training CSV must include:

- a SLICES column, configured with `training.slices`
- one or more numeric property columns, configured with `training.selected_properties`
- any metadata columns required by the evaluation scripts

Trained model artifacts are expected in this format:

```text
weights/transformer_property_<N>.pth
weights/model_info_property_<N>.json
```

`<N>` is the number of conditioning values used by the model.

## Crystal-System Encoding

For runs that use `crystal_system_encoded`, the encoding used by the evaluation scripts is:

| Code | Crystal system |
| --- | --- |
| 1 | Triclinic |
| 2 | Monoclinic |
| 3 | Orthorhombic |
| 4 | Tetragonal |
| 5 | Trigonal |
| 6 | Hexagonal |
| 7 | Cubic |

Code `0` is reserved for `Unknown` in the plotting/evaluation utilities.

## Environment

Create a Python environment with the required scientific and deep-learning packages. A typical installation is:

```bash
pip install torch pytorch-lightning hydra-core omegaconf pandas numpy matplotlib seaborn tqdm einops tensorboard pymatgen matgl m3gnet megnet tensorflow
```

The materials-science stack can be sensitive to Python, CUDA, TensorFlow, and operating-system versions, so a dedicated environment is recommended.

## Configuration

Both code paths use Hydra:

```text
mat/config/default.yaml
mat-multi/config/default.yaml
```

Important fields:

| Field | Description |
| --- | --- |
| `data_path.fname` | path to the training CSV |
| `training.selected_properties` | property columns used for conditioning |
| `training.num_properties` | number of conditioning values |
| `training.special_tokens` | property tokens prepended to the generated sequence |
| `training.slices` | SLICES column name |
| `paths.checkpoint_path` | exported model weights used for sampling |
| `paths.vocab_and_model` | vocabulary and model metadata JSON |
| `sample.properties` | target property values used during generation |
| `sample.save_path` | output CSV for generated SLICES strings |
| `back_to_cif.output_folder` | reconstructed CIF files and conversion plots |
| `proxy_model.*` | proxy model names and output paths |

Run scripts from inside `mat/` or `mat-multi/` so the relative paths in the config resolve correctly.

## Training

Single-property model:

```bash
cd mat
python train.py \
  data_path.fname=./dataset/data.csv \
  training.selected_properties='["PROPERTY_COLUMN"]' \
  training.num_properties=1 \
  training.special_tokens='["<PROPERTY_TOKEN>"]' \
  training.slices=SLICES
```

Multi-property model:

```bash
cd mat-multi
python train.py \
  data_path.fname=./dataset/data.csv \
  training.selected_properties='["PROPERTY_COLUMN_1","PROPERTY_COLUMN_2"]' \
  training.num_properties=2 \
  training.special_tokens='["<PROPERTY_TOKEN_1>","<PROPERTY_TOKEN_2>"]' \
  training.slices=SLICES
```

Training writes logs, PyTorch Lightning checkpoints, exported weights, and vocabulary metadata to the configured paths.

## Sampling

Generate SLICES strings from a trained model:

```bash
cd mat
python sample_property.py \
  sample.properties='[TARGET_VALUE]' \
  sample.number_sequences=500
```

For multi-property conditioning:

```bash
cd mat-multi
python sample_property.py \
  sample.properties='[[TARGET_VALUE_1,TARGET_VALUE_2]]' \
  sample.number_sequences=500
```

The sampler loads the configured model weights and metadata, validates generated SLICES strings, and writes the accepted samples to `sample.save_path`.

## Reconstruction

Convert generated SLICES strings to CIF structures:

```bash
cd mat
python sli_to_cif.py
```

or:

```bash
cd mat-multi
python sli_to_cif.py
```

Outputs are written under the configured `sample/output_structures/` folder.

## Evaluation

Single-property evaluation utilities:

```bash
cd mat
python form_proxy.py
python band_proxy.py
python bulk_proxy.py
python metrics.py
```

Multi-property evaluation utilities:

```bash
cd mat-multi
python band_form.py
python form_bulk.py
python crystal_form.py
python crystal_band.py
python crystal_bulk.py
python metrics.py
```

The proxy model names and reconstructed CSV path are configured under `proxy_model` in the corresponding Hydra config.

## Reproducibility Notes

- This repository tracks code and configuration only.
- Use the same processed dataset, property columns, target values, weights, and proxy model versions to reproduce a specific result.
- `train.py` uses the first 90% of rows for training and the remaining 10% for validation.
- Sampling uses nucleus sampling with default `temperature=1.2` and `top_p=0.9`.
- `model_info_property_<N>.json` stores the vocabulary and block size required for sampling.

## Git Ignore Policy

The repository does not track datasets, weights, checkpoints, logs, generated samples, CIF files, plots, Python caches, or local OS files such as `.DS_Store`.

## Citation

If you use this repository, please cite the associated manuscript:

```text
Transformer-Based Generation of Inorganic Materials with Targeted Properties.
Manuscript submitted for journal review.
```
