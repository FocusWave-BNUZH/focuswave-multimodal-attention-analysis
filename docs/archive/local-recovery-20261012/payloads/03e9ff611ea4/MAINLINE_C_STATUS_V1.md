# Mainline C v1 status

Audit date: 2026-08-27

Overall: `PARTIAL`

## Producer truth

The workspace registry resolves the producer to `kyandi233-dev/Attention-Analysis`. The central repository is `greenboo26/focuswave-multimodal-attention-analysis`. The inspected NVIDIA producer checkout is `nvidia-cuda`; its local worktree has pre-existing untracked files and was not modified. The RGB checkout is a local view of the same producer repository and also has pre-existing untracked files; it was not modified.

The central contract requires local producers to emit timestamps, gaps, coverage, QC, linkage evidence and provenance, while central integration owns identity reconciliation, global cohort and participant-disjoint inference.

## NIR audit

| layer | observed evidence | result |
|---|---|---|
| raw/producer output | 71 completed fullclass subject directories; 71 usable `eyes.csv`/`frames.csv`/`run_manifest.json` sets | `SUPPORTING` |
| derived features | `nir_69session_final_probe_analysis_v1/analysis_probe_matrix_30s.csv` | `READY_FOR_CENTRAL_MERGE` |
| QC | 1,360 rows retain PIR/OAR coverage, internal coverage, temporal gap, ROI clipping and RITnet-found fields | `READY_WITH_ROW_QC` |
| probe alignment | 1,360/1,360 exact canonical behavior rows; `onset_abs_diff_ms=0.0` | `PASS` |
| cohort | 68 sessions / 44 repeat participants / 1,360 probes; 30 s primary | `PASS_FOR_CURRENT_MATCHED_COHORT` |

The usable handoff is the existing matrix, not the newer-looking `nir_v1_scientific_fix_v1` table. The latter has 4,260 rows across 71 sessions, but its 30 s keys did not exact-join the canonical behavior table in this audit; the direct logical-probe comparison exposed an approximately 1.15 s onset mismatch for block 1 and block-index mismatch for block 2. It is retained as misaligned/stale evidence and is not consumed by #12.

NIR producer run manifest records `gpu_inference_started=false`; no new NIR/RITnet/YOLO inference was started in this task.

## RGB audit

| layer | observed evidence | result |
|---|---|---|
| raw extraction | 71/71 selected subjects have full-span face frame manifests and RGB raw face parquet manifests; 71/71 motion manifests; 71/71 pose manifests | `ENGINEERING_COMPLETE` |
| derived features | face raw, motion raw and pose landmarks exist; pose manifests explicitly say `derived_features_deferred=true` | `PARTIAL` |
| QC | inventory and timestamp-gap audit exist; per-probe QC/feature aggregate is absent from the inspected root | `NOT_READY` |
| probe alignment | no canonical RGB probe-level table or alignment manifest was found in the inspected root | `BLOCKED_PENDING_DERIVATION` |
| formal inference | central RGB contract remains engineering/parity first; no formal RGB inference authorized | `NOT_AUTHORIZED` |

Observed RGB cohort manifest: 71 selected, 71 complete/skipped, 0 failed. This is producer completion, not central probe readiness. The RGB inventory contains 72 source rows, while the completed cohort contains 71 sessions; the difference must remain visible until the exclusion/selection mapping is reconciled.

## Handoff to #12

Consume only the local NIR matrix named in `MAINLINE_C_MANIFEST_V1.json`, with its recorded SHA-256 and 30 s window. Preserve the row-level QC fields and do not treat NIR as label truth. Use the existing canonical behavior label semantics: label 1 is fully task-focused; labels 2/3/4 are other non-fully-task-focused states.

Do not consume the 4,260-row scientific-fix table, the older 69-session diagnostic table, RGB raw parquet, or RGB local subject outputs as formal probe features.

## Minimal continuation

RGB: reuse the producer's existing raw face/motion/pose outputs to derive the smallest versioned probe-window feature/QC package, then emit a canonical absolute-Unix-ms alignment table and manifest. Do not rerun raw extraction or full inference unless a producer continuation proves an output is missing.

NIR: no continuation is needed for the current matched 68-session handoff. Separately resolve the cohort/recovery status for `sub-100`, `sub-178`, and `sub-099` before any cohort expansion; do not merge them by subject name or approximate time.
