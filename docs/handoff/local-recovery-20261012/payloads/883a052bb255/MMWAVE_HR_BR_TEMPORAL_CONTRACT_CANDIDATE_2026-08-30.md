# mmWave HR/BR temporal contract candidate — 2026-08-30

Status: `PARTIAL / FORMAL_HR_BR_WINDOW_NOT_FROZEN / ISSUE25_WAIT_ON_SELECTOR_VALIDITY`

Purpose: freeze the vocabulary, evidence boundary, and acceptance checklist needed before a formal heart-rate (HR) or breathing-rate (BR) temporal contract can be declared. This is a decision-preparation record. It neither promotes a window nor changes the producer, raw data, selector, ECG reference, physical gate, or multimodal feature set.

## 1. Decision at this revision

No formal HR or BR analysis window is frozen. `20 s` remains a bounded engineering/continuity diagnostic; `25 s` is an internal HR-course calculation interval; `40 s / 20 s step` is a variational mode decomposition (VMD) overlap setting; and `60 s` is a historical trailing aggregation/probe semantic. They are not interchangeable.

The existing Issue #25 contrast is useful conditional evidence, but it cannot select a formal duration: on a predeclared 303-endpoint grid with 283 paired ECG-valid endpoints, the historical fixed-target path reported 20-s versus trailing-60-s mean absolute error (MAE) of `14.703129` versus `5.608574 bpm`. The contrast is conditional on that historical target/path and targeted subset. It is not identifiable as a window-length-only effect while the current selector/path contract remains unresolved.

`pre_30s = [probe_onset_unix_ms - 30000, probe_onset_unix_ms)` remains the frozen Behavior/NIR/RGB multimodal alignment window. It is an outcome-feature alignment convention, not an HR/BR estimator or validation window. mmWave stays excluded from that formal three-modal package while HR/BR are `HOLD`.

## 2. Frozen terminology

| Term | Exact semantics and existing source | Authorized use | Not evidence for |
|---|---|---|---|
| `20 s engineering diagnostic` | `run_mmwave_targeted_validation_20260830.py` at `472735b6`; block-local interval with 10-s step and 5-s boundary guard, originally for target/bin/channel continuity and ECG-aligned bounded diagnostics | Diagnostics, coverage/QC and selector/path troubleshooting | Canonical physiological HR/BR duration or HRV duration |
| `25 s internal HR course` | `process_vital_signs_v3_1_1.py`; local time/frequency HR course window with 5-s step | Existing historical-course implementation only | A standalone formal window or a substitute for the 20-s diagnostic |
| `40 s VMD / 20 s step` | `separate_vmd_heart_windowed()` in `process_vital_signs_v3_1_1.py` | Internal cardiac-separation overlap setting | Output HR/BR aggregation duration or probe alignment window |
| `60 s historical trailing aggregation` | `run_hr_course_99_corrected.py` and `build_hr_course_99_audit.py` at `64634159d`; a 60-s trailing probe interval summarizes existing 25-s/5-s course points by `(t > onset - 60) & (t <= onset)` | Historical reference reproduction and a predeclared comparison arm | Direct reuse of `_selection_60s` raw-frame-0 output, or automatic formal promotion |
| `pre_30s multimodal probe alignment` | Formal model-ready/attach package; real Unix milliseconds before the probe onset | Behavior/NIR/RGB feature attachment key | mmWave HR/BR duration, ECG validity gate, or HRV duration |

## 3. Current evidence and its valid boundary

1. Issue #25 reused the existing v3.1.1 bandpass, periodogram, peak, segment-correction/consensus and course chain; it fixed the historical corrected-gate target before observing comparison results, used DLL time plus block-local ECG affine mapping, and applied the Issue #24 ECG-quality adapter independently to both durations. It did not construct a new estimator.
2. The comparison held fixed the targeted three-session/complete-block subset, endpoint grid, target source, estimator family, timing contract and ECG rule. Its nominal frequency-bin spacing is 3 bpm at 20 s and 1 bpm at 60 s; observed frame counts and coverage are still DLL-time dependent.
3. It did **not** hold fixed the scientific target/selector/path state now required for a formal producer: the comparison uses a historical fixed-target route, whereas the current independent selector/path has unresolved target/bin/channel and continuity provenance. Therefore the 9.094555-bpm paired MAE difference cannot be attributed to duration alone.
4. The `0.30–1.50 m` historical range gate is `HISTORICAL_GATE_SENSITIVITY`, not a current physical ROI: current session-level distance, orientation and target-identity evidence is absent. No interval may be selected from ECG error.
5. For HRV, the more basic beat-to-ECG validation gate has failed; neither 20 s nor 60 s is authorized for HRV promotion. A future HRV contract requires a separately predeclared longer metric-specific window after beat-level validation.

## 4. Formal-window acceptance checklist

A formal HR/BR duration may be considered only when all applicable items are evidenced in a committed aggregate report/manifest and row-level data remain local-only.

| Gate | Required evidence | Current state |
|---|---|---|
| T2 physical ROI | Independent session/block placement or geometry receipt establishing target identity and any ROI independently of ECG outcome; otherwise use only an externally justified broad ROI | `BLOCKED / PHYSICAL_GATE_UNRESOLVED` |
| T3 selector/path | One deterministic target/bin/channel and downstream path, version-pinned and reproducible in every compared duration; no ECG-informed selector tuning | `PARTIAL / WAIT_ON_SELECTOR_VALIDITY` |
| Time and coverage | DLL-time interval construction, same-block boundary guards, frame-coverage accounting, incomplete-tail exclusion without repair, and block-local ECG alignment audit | Available for targeted diagnostic; needs reuse under the frozen T2/T3 contract |
| Reference quality | Predeclared ECG quality adapter separately applied per duration; retain invalid reasons and warnings; paired denominator, missingness and coverage reported | Available (`335 = 325 valid + 10 invalid + 0 unresolved`); must be rerun for the formal grid |
| Comparison protocol | Durations, endpoint grid, overlap/step, target/path, QC, metrics and decision rule fixed before result review; no duration chosen by MAE | Not authorized until T2/T3 pass |
| Statistical boundary | Report MAE, median absolute error, bias, correlation, frequency resolution, coverage, valid-window count and overlap dependence; do not call overlapping endpoints independent superiority evidence | Template ready; formal run pending |
| Multimodal interface | Map only a validated mmWave producer to `pre_30s` by real Unix milliseconds and the frozen mother-table key; rerun matched cohort/LOSO/leakage checks | `BLOCKED` because HR/BR remain `HOLD` |

## 5. Reusable implementation assets

| Asset | Reuse role | Restriction |
|---|---|---|
| `scripts/maintenance/run_mmwave_window_length_comparison_20260830.py` | Minimal wrapper for the existing paired 20-s/trailing-60-s diagnostic and manifest checks | Reuse only after replacing inputs with a frozen T2/T3 contract; do not add a length sweep |
| `scripts/maintenance/run_hr_course_99_corrected.py` and `build_hr_course_99_audit.py` | Historical 60-s trailing-course semantics | Preserve fixed-target and 25-s/5-s internal-course semantics; do not rebrand it as a 60-s point estimator |
| `scripts/process_vital_signs_v3_1_1.py` | Existing target, phase, cardiac, VMD, peak, spectral and course functions | No new algorithm family, silent estimator rewrite, or ECG-informed tuning |
| `scripts/gold_standard_qa.py::ecg_qa` | Issue #24 reference-quality adapter | Apply separately to every duration and preserve warnings distinct from invalidity |
| `scripts/maintenance/run_mmwave_dll_window_coverage_audit_20260830.py` | DLL-time completeness and tail accounting | Exclude severe incompleteness; never pad/backfill historical tail |
| `scripts/maintenance/run_mmwave_selector_path_reconciliation_20260830.py` and its result package | Selector/path evidence and controlled-stage provenance | Its current result is supporting-only; it does not close T3 |

## 6. Required next execution order

1. Obtain independent T2 physical placement/ROI evidence, or explicitly freeze a broad externally justified ROI without using ECG outcomes.
2. Freeze and reproduce T3 target/bin/channel/selector/path identity across comparison durations; document all non-identifiable stages rather than substituting a new selector.
3. Predeclare the duration comparison grid and decision rule before seeing new metrics. Reuse the Issue #24 ECG adapter and DLL-time/boundary contract; compare the same valid endpoints under the same selector/path and target identity.
4. If HR/BR validity passes separately, map the validated aggregate to `pre_30s` and rerun multimodal cohort, repeated-participant and leakage gates. A change in alignment scope is not a window-validation result.

## 7. Evidence pointers

- Issue #25 report and manifest: `docs/results/2026-08-30_MMWAVE_TARGETED_VALIDATION/MMWAVE_WINDOW_LENGTH_COMPARISON_REPORT_2026-08-30.md` and `MMWAVE_WINDOW_LENGTH_COMPARISON_MANIFEST.json`.
- Selector/window confound reconciliation: `docs/results/2026-08-30_MMWAVE_SELECTOR_PATH_RECONCILIATION/MMWAVE_SELECTOR_WINDOW_CONFOUND_RECONCILIATION_REPORT_2026-08-30.md`.
- Current canonical boundary: `docs/canonical/MMWAVE_CANONICAL_STATE_AND_INTERFACE_V1.md` and `docs/research/MMWAVE_HR_BR_HRV_PROJECT_PIPELINE_MAP_2026-08-30.md`.
- Frame-time and formal validity contracts: `docs/research/MMWAVE_FRAME_TIME_CONTRACT_2026-08-30.md` and `docs/research/MMWAVE_VALIDITY_BLOCKERS_AND_RESOLUTION_CONTRACT_2026-08-30.md`.
- Formal non-mmWave alignment: `docs/results/2026-08-30_FORMAL_MODEL_READY_V1/README.md` and `docs/results/2026-08-30_FORMAL_MULTIMODAL_ATTACH/README.md`.

## 8. Final status

`PASS` for temporal-term lineage, evidence separation and reusable-asset identification. `PARTIAL` for the existing conditional 20-s versus 60-s diagnostic. `BLOCKED` for a formal HR/BR temporal contract pending T2 physical ROI evidence and T3 selector/path validity. HR/BR remain `HOLD`; HRV remains `BLOCKED`.
