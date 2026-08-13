---
tags:
  - warranty
  - file-index
---

# File Structure Index

This document indexes all files in the project and their purposes.

## Root Level Files

| File | Purpose |
|------|---------|
| `config.yaml` | **Unified configuration** - All pipeline parameters in one YAML file |
| `requirements.txt` | **Dependencies** - All Python packages needed |
| `README.md` | **Main documentation** - Architecture, usage, API reference |
| `REFACTORING_SUMMARY.md` | **This refactoring** - What was created and why |

## `data/` Folder

| File | Purpose |
|------|---------|
| `AIDataset.csv` | Source data file — read-only input to the pipeline |
| `warranty_processed.csv` | Cleaned, preprocessed output from notebook 01 — input to notebooks 02–04 |
| `embeddings/` | All generated embedding artefacts, one timestamped subfolder per model |

> `config.yaml` → `data.csv_path` points to `data/AIDataset.csv`. Docker mounts this file read-only at `/app/data/AIDataset.csv`.
> `config.yaml` → `output.embeddings_root` points to `data/embeddings`.

## Documentation Files

| File                                | Purpose                                                                               |
| ----------------------------------- | ------------------------------------------------------------------------------------- |
| `QUICKSTART.md`                     | Installation, running the pipeline, troubleshooting                                   |
| `MIGRATION.md`                      | Side-by-side code comparison (old WCD.ipynb → new modules)                            |
| `warranty_embedding_eval_prompt.md` | Embedding evaluation pipeline spec — model roster, metrics, hybrid retrieval strategy |
| (index file)                        | You're reading it!                                                                    |

## `src/` Package (6 files)

### Root Level
```
src/
├── __init__.py                   # Package init, exports load_config
├── utils.py                      # 180+ lines utility functions
```

| File | Lines | Key Functions |
|------|-------|---|
| `__init__.py` | 5 | Package initialization |
| `utils.py` | 185 | I/O, validation, normalization, hashing, config loading |

### `src/data/` Subpackage
```
src/data/
├── __init__.py                   # DataLoader, DataCleaner, DataPreprocessor
└── stopwords.py                  # Hardcoded stopwords, required tokens
```

| File | Lines | Classes/Functions |
|------|-------|---|
| `__init__.py` | 200+ | `DataLoader`, `DataCleaner`, `DataPreprocessor` |
| `stopwords.py` | 150+ | `CUSTOM_STOPWORDS`, `REQUIRED_TOKENS` |

**Key Classes**:
- `DataLoader`: Load CSV files
- `DataCleaner`: Rename columns, normalize data types
- `DataPreprocessor`: Tokenize, clean text, concatenate features

### `src/embeddings/` Subpackage
```
src/embeddings/
└── __init__.py                   # 7 builder classes + factory function
```

| Builder Class | Purpose |
|---|---|
| `TFIDFBuilder` | TF-IDF sparse embeddings |
| `BM25Builder` | BM25 sparse embeddings |
| `OneHotBuilder` | One-hot encode categorical columns |
| `BertBuilder` | BERT [CLS] token embeddings |
| `SentenceTransformerBuilder` | MiniLM, MPNet, RoBERTa embeddings |
| `build_embeddings()` | Factory function for any embedding type |

**Features**:
- Unified interface (fit_transform, save, load)
- Automatic manifest creation
- Model versioning via timestamps

### `src/matching/` Subpackage
```
src/matching/
└── __init__.py                   # Similarity computation + summarization
```

| Class/Function | Purpose |
|---|---|
| `SimilarityMatcher` | Compute similarity matrices |
| `summarize_item_to_fm_matrix()` | Rank alternatives per item |
| `summarize_fm_to_fm_matrix()` | Find similar failure modes |

**Methods**:
- `compute_centroid_similarity()` - Item to group centroid
- `compute_intra_pairwise()` - Within-group item×item
- `compute_fm_item_to_centroids()` - Item×NewFM centroids
- `compute_inter_newfm()` - NewFM×NewFM centroids

### `src/classification/` Subpackage
```
src/classification/
└── __init__.py                   # Feature composition & training
```

| Class | Purpose |
|---|---|
| `FeatureComposer` | Combine embeddings with weights |
| `ClassificationTrainer` | Train models, grid search, evaluate |

**Methods**:
- `compose()` - Combine multi-embeddings with weights + normalize
- `cross_validate()` - K-fold CV with class filtering
- `grid_search_ohe_weights()` - Optimize embedding mixture
- `train_final_model()` - Train on full dataset

## `notebooks/` Folder (10 active workflow notebooks + 1 compatibility stub)

### Notebook 1: EDA & Data Exploration
```
01_eda_exploration.ipynb
```
**Purpose**: Load, clean, explore data. Outputs `data/warranty_processed.csv`.

### Notebook 2: Embedding Generation
```
02_embedding_generation.ipynb
```
**Purpose**: Generate full corpus embeddings for all SOTA models. Outputs one timestamped subfolder per model under `data/embeddings/`.

### Notebook 3: Similarity Matching
```
03_similarity_matching.ipynb
```
**Purpose**: Compute centroid, pairwise, and inter-FM similarities.

### Notebook 4: Embedding Evaluation
```
04_embedding_evaluation.ipynb
```
**Purpose**: Evaluate model quality on a 3 000-sample slice to identify the best model. Run before notebook 05.

**Models evaluated**: BM25, MiniLM-L6, MiniLM-L12, MPNet, BGE-M3, Qwen3-0.6B, Nomic-v1.5

**Metrics**: Recall@5/10, kNN Accuracy, kNN F1-macro, DTC sensitivity, hybrid alpha sweep

**Charts produced** (`results/charts/`): `01_model_recall5`, `02_model_all_metrics`, `03_dtc_sensitivity`, `04_hybrid_sweep`

**CSVs**: `embedding_eval_DATE.csv`, `hybrid_sweep_04_DATE.csv`

> Embeddings cached under `data/embeddings/eval/`. Result caching: delete CSV to recompute.

### Notebook 5: Feature Engineering & Hyperparameter Selection
```
05_feature_engineering.ipynb
```
**Purpose**: Answer *what is the best feature representation?* All expensive decisions made here; exports `results/best_features.json` for NB06 and NB07.

**Workflow**:
1. Rank all embedding models on full eval slice (confirms NB04 selection)
2. Compare four input composition strategies with best model
3. BM25 hybrid alpha sweep
4. OHE weight grid search — coarse then refined
5. Export `best_dense_key` and `best_weight` to `results/best_features.json`

**Charts produced** (`results/charts/`): `05_model_recall5`, `06_model_all_metrics`, `07_strategy_comparison`, `08_hybrid_sweep`, `16a/16b_ohe_grid`

**CSVs**: `model_ranking`, `strategy_comparison`, `hybrid_sweep`, `ohe_weight_coarse`, `ohe_weight_refined`

> Most expensive step: strategy comparison loads Qwen3 and re-encodes 4 strategies (~8 min). Cached — delete CSV to recompute.

### Notebook 6: LogReg Classification
```
06_logreg_classification.ipynb
```
**Purpose**: Answer *how well does LogisticRegression classify with the best features?* Loads `best_features.json` from NB05.

**Workflow**:
1. Load embeddings and best parameters from `results/best_features.json`
2. Train final LogisticRegression on full corpus
3. Part-constrained classification — per-GeneralPart FM constraint sets
4. Selective constraint — apply FM filter only for parts where it helps

**Charts produced** (`results/charts/`):
- `09_part_distribution`, `10_part_accuracy_comparison`, `11_part_accuracy_delta`
- `12_selective_constraint`, `13/14/15/16_top10_delta`

**CSVs**: `part_constrained_inference`, `part_selective_inference`

> Prerequisite: run NB05 first to generate `results/best_features.json`.

### Notebook 7: KNN Classification — Ablation Study
```
07_knn_classification.ipynb
```
**Purpose**: Answer *can KNN beat LogReg, and what do the FM constraint and randomisation each contribute independently?* Structured as a sequential ablation.

**Section structure** (each adds one component):
| Section | Content | What it isolates |
|---|---|---|
| 2 | PCA/UMAP sweep | Is dim reduction beneficial? |
| 3 | Prediction space analysis | Why constraint is useful (52 → ~7 FMs) |
| 4 | Global KNN k-sweep | Baseline, no constraint |
| 5 | Constrained KNN k-sweep | FM constraint effect alone |
| 6 | Per-part hold-out accuracy | Which parts benefit from constraint |
| 7 | Selective constraint | Smart constraint routing |
| 8 | Global RCkNN (no constraint) | Randomisation effect alone |
| 9 | Constrained RCkNN | Both randomisation + constraint |
| 10 | Final comparison vs LogReg | Best strategy overall |

**Charts produced** (`results/charts/`): `17_pca_umap_sweep`, `18_prediction_space`, `19/20_perpart_accuracy_delta`, `21_selective_constraint`, `22_rk_global_sweep`, `23_rk_knn_sweep`, `24_rk_knn_perpart`, `25_knn_vs_logreg`, `26_knn_k_sweep`

**CSVs**: `pca_umap_sweep`, `knn_global_sweep`, `knn_constrained_sweep`, `knn_perpart_accuracy`, `knn_selective_perpart`, `rk_global_sweep`, `rk_constrained_sweep`, `rk_knn_perpart`, `knn_vs_logreg`

> All sweeps cached — delete CSV to recompute. Prerequisite: run NB05 and NB06 first.

### Notebook 8: XGBoost Classification
```
08_xgboost_classification.ipynb
```
**Purpose**: Answer *does XGBoost improve fault-mode classification enough to become a routing-engine option?*

**Workflow**:
1. Load the same NB05-selected `X_final` features as NB06/NB07
2. Evaluate a cached global XGBoost sweep
3. Train per-`GeneralPart` XGBoost where enough data exists
4. Build selective `xgb_global` vs `xgb_per_part` evidence for NB09

**Results folder**: `results/nb08/`

**CSVs/JSON**: `xgb_global_sweep`, `xgb_perpart_training`, `xgb_selective_perpart`, `xgb_holdout_claims`, `xgb_vs_existing`, `xgb_params`

> Prerequisite: run NB05 first. Requires `xgboost`.

### Notebook 9: Routing Engine Training and Build
```
09_routing_engine_training.ipynb
```
**Purpose**: Build the final routing table and export serving artefacts using evidence from NB06 LogReg, NB07 KNN/RCkNN, and NB08 XGBoost.

**Routing options**: `logreg_global`, `logreg_per_part`, `xgb_global`, `xgb_per_part`, `knn_global`, `knn_fm`, `rk_global`, `rk_constrained`

**Results folder**: `results/nb09/`

**Model artefacts**: `models/nb09/`

**Evaluation handoff**: writes `results/nb09/evaluation_interface_DATE.json`, `evaluation_interface_latest.json`, raw comparison claim tables, initial/optimised hold-out claim tables, routing tables, and upgrade summary CSVs for notebook 10.

> Prerequisite: run NB05, NB06, NB07, and NB08 first.

### Notebook 10: Routing Engine Evaluation and Reporting
```
10_routing_engine_evaluation.ipynb
```
**Purpose**: Load the NB09 handoff files, apply confidence calibration, regenerate charts 31-38, and export audit/reporting CSVs without retraining models.

> Prerequisite: run `09_routing_engine_training.ipynb` through the evaluation handoff section first.

### Compatibility Stub
```
09_inference_engine.ipynb
```
**Purpose**: Points users to the split NB09/NB10 workflow. It no longer contains the full routing engine implementation.

## `tests/` Folder (3 files)

```
tests/
├── conftest.py                   # Pytest fixtures and setup
├── test_data.py                  # DataCleaner, DataPreprocessor tests
└── test_embeddings.py            # TFIDFBuilder, BM25Builder tests
```

| File | Tests |
|------|-------|
| `conftest.py` | Pytest configuration, fixtures |
| `test_data.py` | Column renaming, text cleaning, tokenization |
| `test_embeddings.py` | TFIDF/BM25 shape, sparsity |

**Run tests**:
```bash
pytest tests/ -v
```

## Total Code Summary

| Component | Files | Purpose |
|-----------|-------|---------|
| **Core Package** | 9 | Reusable modules |
| **Notebooks** | 10 active + 1 stub | Focused workflows (01-10) |
| **Tests** | 3 | Unit tests |
| **Documentation** | 4+ | Guides + index |
| **Config** | 1 | Unified parameters |
| **Dependencies** | 1 | Package list |

## File Dependencies

```
config.yaml
    ↓
01_eda  →  02_embedding  →  03_similarity
                ↓
          04_embedding_eval      (quick model selection — uses eval cache)
                ↓
          05_feature_engineering (full model ranking, OHE grid search)
                ↓                 writes results/best_features.json
          06_logreg_classification  (reads best_features.json, trains LogReg)
                ↓
          07_knn_classification     (reads best_features.json, KNN ablation)
                ↓
          08_xgboost_classification (reads best_features.json, XGBoost investigation)
                ↓
          09_routing_engine_training (reads 06/07/08 evidence, exports routing artefacts + evaluation handoff)
                |
          10_routing_engine_evaluation (reads NB09 handoff, exports charts/audit reports)

src/data           (used by 01)
src/embeddings     (used by 02, 04, 05)
src/matching       (used by 03)
src/classification (used by 05, 06)
src/utils          (used by all)
src/data/stopwords (used by embeddings)

results/best_features.json  (written by 05, read by 06, 07, and 08)
```

## Key Features by File

### `config.yaml`
- 11 configuration sections
- 50+ tunable parameters
- No hardcoded values needed

### `src/utils.py`
- Config loading (YAML)
- I/O helpers (save/load sparse/dense)
- Validation functions
- Normalization utilities
- Manifest creation
- Corpus hashing

### `src/data/__init__.py`
Features:
- Multi-step cleaning pipeline
- Regex-based tokenization
- Custom stopword filtering
- Required token enforcement
- Text concatenation

### `src/embeddings/__init__.py`
Features:
- 7 builder classes (consistent interface)
- Automatic model versioning
- Sparse & dense I/O
- Progress bars (tqdm)
- Reproducible manifests
- GPU/CPU device handling

### `src/matching/__init__.py`
Features:
- 4 similarity modes
- Centroid computation
- Pairwise similarity
- Summary generation
- Alternative ranking
- Top-k recommendations

### `src/classification/__init__.py`
Features:
- Feature composition
- Multi-embedding support
- Class filtering
- Cross-validation
- Grid search
- Progress tracking

## New vs Old Statistics

| Metric | Old `WCD.ipynb` | New Pipeline | Change |
|--------|---|---|---|
| Total Cells | 115+ | 39 | -66% |
| Total Lines | 2500+ | 2815 | +13% |
| File Organization | 1 monolithic | 22 modular | Better structure |
| Reusability | Low | High | Modular imports |
| Testability | None | Built-in | 80+ test lines |
| Documentation | Scattered | Comprehensive | 4 guide files |
| Config Management | Hardcoded | Unified YAML | Centralized |
| Duplicate Code | ~40% | <5% | -87% |

## `archive/` Folder

Contains files that predate or fall outside the refactored pipeline structure.

| File / Folder | Description |
|---|---|
| `AIDataset.csv` | Older copy of source data (Nov 2025). Active copy is now in `data/AIDataset.csv`. |
| `WCD.ipynb` | Original monolithic notebook (pre-refactor) |
| `WCD-21-11.ipynb` | Prior WCD notebook version |
| `WCD-jnl_pc.ipynb` | Prior WCD notebook version (jnl_pc variant) |
| `Logistic_regression.ipynb` | Standalone logistic regression experiment |
| `Model_load+embed.ipynb` | Standalone model loading/embedding experiment |
| `fm_item_summary_24010_B4010.csv` | Legacy output: FM item summary |
| `relabel_summaries_all_embeddings.csv` | Legacy output: relabelled embedding summaries |
| `relabel_summaries_all_embeddings-jnl_pc.csv` | Legacy output: relabelled summaries (jnl_pc variant) |
| `models/` | Saved model checkpoints (TF-IDF, MiniLM, BERT, BM25, MPNet, RoBERTa, timestamped) |
| `output_multiling/` | Legacy multilingual JSON outputs |
| `stop_words/` | Name CSV files used for stopword filtering (names data) |
| `grid search CV/` | Screenshots from early grid search experiments |

---

✅ **Status**: All structural improvements have been implemented.

Start with:
1. [QUICKSTART.md](QUICKSTART.md) - How to run
2. [README.md](README.md) - What things do
3. [MIGRATION.md](MIGRATION.md) - Where old code went
