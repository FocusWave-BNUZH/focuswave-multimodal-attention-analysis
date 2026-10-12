from __future__ import annotations

import csv
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/maintenance/build_mmwave_probe_adapter_v1.py"
SCHEMA = ROOT / "schemas/mmwave/mmwave_probe_merge_ready_v1.schema.json"
AVAILABILITY_SCHEMA = ROOT / "schemas/mmwave/mmwave_probe_availability_v1.schema.json"
FEATURE_SCHEMA = ROOT / "schemas/mmwave/mmwave_probe_feature_lane_v1.schema.json"


def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def timeline_row(probe: str) -> dict[str, str]:
    return {
        "repeat_participant_id": "R001", "session_id": "sub-001", "block_id": "block-1",
        "probe_id": probe, "window_name": "pre_30s", "probe_onset_unix_ms": "100000",
        "window_effective_start_unix_ms": "70000", "window_end_unix_ms": "100000",
    }


def test_schema_requires_explicit_eligibility_and_provenance_fields():
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    assert {"mmwave_failure_reason", "mmwave_eligibility_label", "mmwave_estimator_version", "mmwave_adapter_source_commit"} <= set(schema["required"])


def test_two_input_lanes_share_key_and_keep_hrv_null():
    availability = json.loads(AVAILABILITY_SCHEMA.read_text(encoding="utf-8"))
    feature = json.loads(FEATURE_SCHEMA.read_text(encoding="utf-8"))
    assert availability["required"][:5] == feature["required"][:5]
    assert feature["properties"]["mmwave_eligibility_label"]["const"] == "EXCLUDE_FROM_FINAL_MULTIMODAL_CONTRIBUTION"
    for field in ("mmwave_ibi_median_ms", "mmwave_rmssd_ms", "mmwave_sdnn_ms"):
        assert feature["properties"][field]["type"] == "null"


def test_adapter_preserves_rows_and_withholds_physiology_without_source(tmp_path):
    timeline = tmp_path / "timeline.csv"
    write_csv(timeline, list(timeline_row("probe-01")), [timeline_row("probe-01"), timeline_row("probe-02")])
    out_dir = tmp_path / "formal_multimodal_v2" / "mmwave"
    subprocess.run([sys.executable, str(SCRIPT), "--timeline", str(timeline), "--out-dir", str(out_dir)], check=True)
    with (out_dir / "mmwave_probe_merge_ready.csv").open(encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    assert len(rows) == 2
    assert {row["mmwave_state"] for row in rows} == {"STRUCTURAL_MISSING"}
    assert {row["mmwave_eligibility_label"] for row in rows} == {"EXCLUDE_FROM_FINAL_MULTIMODAL_CONTRIBUTION"}
    assert {row["mmwave_hr_fused_bpm_median"] for row in rows} == {""}
    manifest = json.loads((out_dir / "mmwave_probe_merge_ready_manifest.json").read_text(encoding="utf-8"))
    assert manifest["join"]["timeline_rows"] == 2
    assert manifest["join"]["unmatched_timeline_rows"] == 2


def test_adapter_marks_observed_source_not_eligible_and_does_not_copy_hr(tmp_path):
    timeline = tmp_path / "timeline.csv"
    write_csv(timeline, list(timeline_row("probe-01")), [timeline_row("probe-01")])
    source = tmp_path / "availability.csv"
    source_row = timeline_row("probe-01") | {
        "mmwave_observed": "true", "mmwave_source_run_id": "run-7", "mmwave_source_commit": "abc123",
        "mmwave_estimator_version": "v3.1.1", "mmwave_hr_fused_bpm_median": "75.0",
        "mmwave_timestamp_coverage_fraction": "1.0", "mmwave_hr_mean_confidence": "0.82",
    }
    write_csv(source, list(source_row), [source_row])
    out_dir = tmp_path / "out"
    subprocess.run([sys.executable, str(SCRIPT), "--timeline", str(timeline), "--out-dir", str(out_dir), "--source-index", str(source)], check=True)
    with (out_dir / "mmwave_probe_merge_ready.csv").open(encoding="utf-8") as stream:
        row = next(csv.DictReader(stream))
    assert row["mmwave_state"] == "NOT_ELIGIBLE"
    assert row["mmwave_observed"] == "true"
    assert row["mmwave_estimator_version"] == "v3.1.1"
    assert row["mmwave_hr_mean_confidence"] == "0.82"
    assert row["mmwave_hr_fused_bpm_median"] == ""
