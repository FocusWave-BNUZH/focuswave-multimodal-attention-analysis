# mmWave coarse physical ROI contract — 2026-08-30

Status: **PASS / COARSE_ROI_UNRESOLVED / HARD_EXTERNAL_BLOCKER**

## Decision

No numeric coarse physical ROI is frozen for the existing formal recordings, and no selector or estimator is changed. The exact current rule is:

> **Do not exclude a selected range bin as physically impossible for formal-session processing unless a session-bound geometry record independently maps that bin to space outside the participant envelope.**

This is deliberately not a physiology-validity rule. It says that the repository has not recovered enough placement geometry to identify any in-data range interval as definitely outside the formal participant envelope. It also does not authorise arbitrary-range target selection: existing data-shape bounds and every existing algorithm contract remain unchanged.

Historical `0.30–1.50 m` (bins 9–40 under the corrected axis) remains `HISTORICAL_GATE_SENSITIVITY` only. It is neither restored as this contract nor relabelled as a physiology-valid gate.

## Independent evidence table

| physical fact needed for a coarse ROI | recovered evidence | status and permitted use |
|---|---|---|
| formal range coordinate | `ReportDataCube1D` has 256 reported range elements; formal mapping is `range_m = bin × 0.037` | `CONFIRMED_AXIS_SEMANTICS`; a selected-bin distance is a radar coordinate/proxy, not a measured chest distance |
| range bias / absolute calibration | no formal-session range-bias measurement, target receipt, or device readback was recovered; the prior audit reports no verified additional bias | `UNRESOLVED`; no offset or tolerance may be invented |
| radar mounting position, height, yaw/pitch/roll | no session-bound installation record | `MISSING_REQUIRED_GEOMETRY` |
| chair and chest envelope | protocol says face the upper sternum at 0.4 m, but has no per-session measurement or confirmation | `PROTOCOL_INSTRUCTION_ONLY`; cannot set a bound |
| posture, slouch and reposition tolerance | no recorded tolerance or session-linked placement trace | `MISSING_REQUIRED_GEOMETRY` |
| room, wall and adjacent-room geometry | no dimensions, scale-bearing setup media, or occlusion map linked to the formal sessions | `MISSING_REQUIRED_GEOMETRY`; cannot call bins behind a wall/another room |
| useful range and FOV | no formal-session FOV, boresight, antenna-coordinate, or angle-calibration record | `MISSING_REQUIRED_GEOMETRY`; 1-D range alone cannot distinguish azimuth/elevation locations |
| 0.8 m range-verification utility | engineering check that the radar can observe a person near an expected target | `ENGINEERING_REFERENCE_ONLY`; not formal-session placement truth |
| B2 near-side bright structure | observed in the locked structural audit; physical cause and target identity unresolved | `OBSERVED_SUPPORTING`; no hard exclusion follows |

The coordinate axis itself spans bins 0–255. Its nominal `256 × 0.037 = 9.472 m` data-domain extent is **not** a room map or a device-useful-range claim, so it supplies no scene-specific hard-exclude boundary.

## Contracted classifications

| category | current formal status | exact action |
|---|---|---|
| data-impossible | a bin outside the stored 0–255 range axis | invalid input/index; this is a representation check, not an ROI inference |
| scene-hard-exclude | no interval currently provable from formal-session geometry | none frozen |
| uncertain boundary / soft-prior candidate | all in-axis distances, including near-side structures | retain as unresolved; do not introduce a soft prior without a separately approved geometry contract |
| physiology-valid range | unresolved | never infer from this contract; HR/BR remain `HOLD`, HRV remains `BLOCKED` |

## Evidence boundary and reopening condition

`REUSE_REJECTION_REASON`: the existing #26 distance/structure audit, protocol instruction, engineering range verifier, corrected 0.037 m/bin axis, and B2 labels already cover available repository evidence. None identifies where a particular formal-session radar ray intersected the participant, chair, wall, or another room. An error-derived threshold, selected-bin distribution, or a new selector cannot supply that missing external fact.

The smallest adequate reopening package is a session-bound record containing all of the following:

1. Radar reference point, height, position and yaw/pitch/roll relative to a room coordinate system.
2. Chair and chest-reference envelope, with permitted fore/aft and lateral posture movement.
3. Room/wall/adjacent-space geometry and a scale-bearing setup photo, diagram, laser measurement, or equivalent.
4. Acquisition-time linkage between that setup record and each covered session/block.
5. Range-bias/calibration target evidence. Spatial use beyond 1-D range additionally needs antenna coordinates, calibration and angle convention.

Only then may a separate, pre-specified geometry calculation divide bins into scene-hard-exclude and boundary-uncertain sets. ECG/HR/BR/RSP errors must not be used to choose those bounds.

## Provenance and non-actions

- Source baseline: canonical `main` `9eb624ebfa58c0ef58a19de04266fe8d0da7aec3`.
- Reused evidence: `MMWAVE_PHYSICAL_TRUTH_RECOVERY_CHECK_20260830.md`, Issue #26, `MMWAVE_DISTANCE_ERROR_PHYSICAL_GATE_REPORT_2026-08-30.md`, `MMWAVE_PHYSICAL_EVIDENCE.csv`, and the formal firmware/range mapping audits cited in the evidence table.
- No raw data, photos, participant-level table, estimator, selector, gate, QC threshold, C2B/C2C run, or physiology result was created or changed.
