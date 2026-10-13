# Mainline C v1 — NIR/RGB producer handoff

Status: `PARTIAL`

This is the Git-safe handoff surface for issue #14. It records the verified producer outputs and the local-only row-level input for #12. No raw video, participant-level rows, parquet payloads, model weights, credentials, or machine-private runtime files are copied into this repository.

## Ready input

NIR 30 s probe-level input for #12:

`D:\Project\厚粲杯\11_数据\derived\nir_69session_final_probe_analysis_v1\analysis_probe_matrix_30s.csv`

Verified scope: 1,360 probes, 68 sessions, 44 repeat participants, exact `onset_abs_diff_ms=0.0` for all rows. The table already contains canonical behavior fields, NIR features, NIR QC fields, and frozen fold/group fields. It remains local-only because it is row-level data.

## Not ready

RGB has completed raw/derived engineering extraction for 71 selected sessions, but probe-level feature derivation, QC aggregation, and canonical probe alignment are not present in the inspected output root. RGB is therefore `ENGINEERING_COMPLETE / CENTRAL_PROBE_NOT_READY`, not a formal RGB model input.

The 71-session NIR fullclass source output is also not itself the central-ready cohort: `sub-067` is outside the 70-session report cohort, while `sub-100` and `sub-178` are absent from the exact 68-session NIR matrix. The cohort restriction is recorded rather than silently repaired.

## Files

- `MAINLINE_C_MANIFEST_V1.json`: counts, paths, hashes, producer refs, status and blockers.
- `NIR_PROBE_LEVEL_SCHEMA_V1.csv`: central field mapping and QC/provenance semantics for the ready NIR table.
- `MAINLINE_C_STATUS_V1.md`: concise audit report and minimal continuation plan.
