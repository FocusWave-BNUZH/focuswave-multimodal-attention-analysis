# Fusion pipeline

Central-only exact common-cohort comparisons: C+B, C+B+NIR, C+B+RGB and C+B+NIR+RGB at predeclared 30 s.

## AI prototype

`run_quality_aware_fusion_prototype.py` is a small secondary predictive
prototype. It compares context-only logistic regression, regularized
concatenation, a small multilayer perceptron, and a quality-aware late-fusion
gate. The gate is not a causal attribution method and cannot validate
physiology or attention state.

The runner requires a formal central-readiness manifest before reading model
inputs. It rejects `preliminary_screening_only`, engineering-only, proxy,
unresolved-identity, non-global identity, non-matched, or unfrozen-fold inputs.
All imputation, scaling, model fitting and gate optimization occur inside each
frozen participant-disjoint outer fold. Missing-modality tests mask held-out
rows without changing the comparison cohort.

Example validation command:

```text
python pipelines/fusion/run_quality_aware_fusion_prototype.py --readiness <readiness.json> --output-dir <local-output> --preflight
```

The full run additionally requires `--features` and `--folds` conforming to
`schemas/multimodal/multimodal_ai_feature_matrix_v1.json`. Current local
formal readiness is still blocked by the NIR/RGB producer contracts, so this
prototype is not a final multimodal result.
