# Multimodal AI fusion prototype implementation — 2026-08-30

Status: `IMPLEMENTED / FORMAL EXECUTION BLOCKED`

## What was implemented

The prototype is a small secondary predictive layer, not a replacement for the
frozen interpretable modality ladder. It contains four fixed comparisons:

1. context-only regularized logistic regression;
2. regularized feature concatenation;
3. a small concatenation multilayer perceptron;
4. four expert models combined by a train-fold learned softmax quality gate.

The gate receives producer-defined availability and quality values. Its weights
describe model behavior only; they are not causal modality contributions and
do not establish physiology validity.

## Safety and scientific gates

Before model input loading, the runner requires:

- a central-inference readiness manifest with all three sensor producers marked
  formal-ready;
- a frozen matched cohort and frozen participant-level folds;
- `resolved` identity with `id_scope=global_central`;
- complete binary target mapping performed upstream;
- one common `site/session_id/probe_id` row set with all sensor availability
  fields present.

The current local package does not pass this gate. The NIR evidence includes
identity/integration blockers and historical/recomputed packages; RGB has
engineering/raw-context and local motion/QC evidence but no completed formal
probe-level inference contract. Existing mmWave preliminary screening remains
preliminary screening only. No formal model was run on these assets.

## Verification contract

For each frozen outer fold, imputation, standardization, logistic fitting, MLP
fitting and gate optimization use training rows only. The held-out rows are
evaluated under the same fold for `all_available`, `missing_mmwave`,
`missing_nir`, and `missing_rgb`. The latter three are fixed missing-modality
stress tests, not a new cohort.

Implementation tests are in
`tests/test_multimodal_ai_prototype.py`. Local formal execution should only be
started after the producer readiness manifest, feature schema, identity mapping,
matched cohort and fold manifest are independently refreshed and pass the
runner's gate.
