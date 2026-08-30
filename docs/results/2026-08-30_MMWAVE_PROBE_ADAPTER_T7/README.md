# mmWave probe adapter T7 — 2026-08-30

Status: **PARTIAL — structural adapter passes; final multimodal contribution remains blocked**.

## Scope

This package implements the narrow T7 adapter required by the frozen mmWave
interface. It consumes the pre-existing canonical probe timeline and, only if
provided, an already five-column-keyed mmWave availability index. It does not
run a mmWave producer, estimate HR/BR/HRV, infer identity from folders, alter
the `pre_30s` window, fill values, or retrain a multimodal model.

The local-only output is written beneath the supplied derived root as
`formal_multimodal_v2/mmwave/`:

- `mmwave_probe_merge_ready.csv`
- `mmwave_probe_merge_ready_manifest.json`
- `mmwave_probe_merge_ready_audit.csv`

## Actual local run

The existing 1,440-row canonical timeline was used. No exact five-column-keyed
formal mmWave availability index currently exists for these rows, so the output
preserves all 1,440 rows as `STRUCTURAL_MISSING` with
`NO_CANONICAL_MMWAVE_PROBE_SOURCE`. The canonical keys are non-null, unique and
equal to the timeline key set; JSON-schema validation passed for all 1,440 rows.

All rows carry `EXCLUDE_FROM_FINAL_MULTIMODAL_CONTRIBUTION`. T5 has not passed a
formal HR/BR validity gate and T6 retains HRV exclusion, therefore held
physiology and diagnostic fields are null even if a future source index reports
observations. This is a truthful merge interface, not a formal mmWave predictor
attachment.

## Reuse and next input requirement

`REUSE_GATE=PASS`: the adapter reuses the frozen mother-table timeline,
five-column key, `pre_30s` semantics and existing mmWave field contract. The
closest historic mmWave windows use different subjects/window semantics and are
not silently mapped into the formal timeline.

To advance from the present `PARTIAL` result, a producer must emit an exact
five-column-keyed availability index with real session/block/probe provenance,
source run/commit and estimator version. That alone does not authorize final
contribution analysis: T5 HR/BR validity and T6 HRV eligibility remain separate
scientific gates.
