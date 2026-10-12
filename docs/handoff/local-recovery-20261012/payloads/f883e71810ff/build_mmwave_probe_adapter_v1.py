"""Build the local-only mmWave reserve interface on the canonical probe timeline.

This adapter never creates physiology estimates. It only attaches a producer
availability index already keyed to the canonical five-column probe key. Until
the formal mmWave gate changes, physiology values remain null and every row is
excluded from final multimodal contribution analysis.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import subprocess
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[2]
KEY = ("repeat_participant_id", "session_id", "block_id", "probe_id", "window_name")
WINDOW_COLUMNS = ("probe_onset_unix_ms", "window_effective_start_unix_ms", "window_end_unix_ms")
OUTPUT_FIELDS = [
    *KEY, *WINDOW_COLUMNS,
    "mmwave_state", "mmwave_observed", "mmwave_missing_reason", "mmwave_failure_reason",
    "mmwave_eligibility_label", "mmwave_source_run_id", "mmwave_source_commit",
    "mmwave_estimator_version", "mmwave_adapter_source_commit", "mmwave_loadable",
    "mmwave_timestamp_coverage_fraction", "mmwave_hr_freq_bpm_median",
    "mmwave_hr_time_bpm_median", "mmwave_hr_fused_bpm_median",
    "mmwave_breath_rate_breaths_per_min_median", "mmwave_hr_usable_window_fraction",
    "mmwave_hr_mean_confidence", "mmwave_selected_bin_mode", "mmwave_selected_channel_mode",
    "mmwave_selected_bin_distance_proxy_m", "mmwave_target_switch_rate",
    "mmwave_phase_stability_median", "mmwave_motion_proxy_median", "mmwave_ibi_median_ms",
    "mmwave_rmssd_ms", "mmwave_sdnn_ms",
]
WITHHELD_FIELDS = {
    "mmwave_hr_freq_bpm_median", "mmwave_hr_time_bpm_median", "mmwave_hr_fused_bpm_median",
    "mmwave_breath_rate_breaths_per_min_median", "mmwave_ibi_median_ms", "mmwave_rmssd_ms",
    "mmwave_sdnn_ms", "mmwave_selected_bin_mode", "mmwave_selected_channel_mode",
    "mmwave_selected_bin_distance_proxy_m", "mmwave_target_switch_rate",
    "mmwave_phase_stability_median", "mmwave_motion_proxy_median",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git_head() -> str | None:
    try:
        return subprocess.check_output(["git", "-C", str(REPO), "rev-parse", "HEAD"], text=True).strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def read_csv(path: Path) -> tuple[list[dict[str, str]], list[str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        if not reader.fieldnames:
            raise ValueError(f"CSV has no header: {path}")
        return list(reader), list(reader.fieldnames)


def key_of(row: dict[str, str]) -> tuple[str, ...]:
    return tuple((row.get(column) or "").strip() for column in KEY)


def nullable(value: str | None) -> str | None:
    return (value or "").strip() or None


def parse_bool(value: str | None, *, field: str) -> bool:
    normalized = (value or "").strip().lower()
    if normalized in {"true", "1", "yes"}:
        return True
    if normalized in {"false", "0", "no"}:
        return False
    raise ValueError(f"{field} must be boolean, got {value!r}")


def fraction(value: str | None, *, field: str) -> float | None:
    text = nullable(value)
    if text is None:
        return None
    number = float(text)
    if not 0 <= number <= 1:
        raise ValueError(f"{field} must be within [0, 1], got {number}")
    return number


def number(value: str | None, *, field: str) -> float | None:
    text = nullable(value)
    if text is None:
        return None
    try:
        return float(text)
    except ValueError as exc:
        raise ValueError(f"{field} must be numeric, got {text!r}") from exc


def validate_timeline(rows: list[dict[str, str]], fields: list[str]) -> None:
    required = {*KEY, *WINDOW_COLUMNS}
    if missing := required - set(fields):
        raise ValueError(f"timeline missing required columns: {sorted(missing)}")
    keys = [key_of(row) for row in rows]
    if not rows or any(not all(key) for key in keys) or len(keys) != len(set(keys)):
        raise ValueError("timeline canonical key must be non-null and unique")
    if any(row["window_name"] != "pre_30s" for row in rows):
        raise ValueError("timeline contains a non-pre_30s window")
    for row in rows:
        for column in WINDOW_COLUMNS:
            int(row[column])


def load_source_index(path: Path | None, keys: set[tuple[str, ...]]) -> tuple[dict[tuple[str, ...], dict[str, str]], dict[str, Any]]:
    if path is None:
        return {}, {"provided": False, "rows": 0, "sha256": None}
    rows, fields = read_csv(path)
    if missing := ({*KEY, "mmwave_observed"} - set(fields)):
        raise ValueError(f"source index missing required columns: {sorted(missing)}")
    index: dict[tuple[str, ...], dict[str, str]] = {}
    for row in rows:
        key = key_of(row)
        if not all(key) or key in index:
            raise ValueError("source index canonical key must be non-null and unique")
        if key not in keys:
            raise ValueError(f"source index key is absent from canonical timeline: {key}")
        parse_bool(row.get("mmwave_observed"), field="mmwave_observed")
        index[key] = row
    return index, {"provided": True, "rows": len(rows), "sha256": sha256(path)}


def build_row(timeline: dict[str, str], source: dict[str, str] | None, adapter_commit: str | None) -> dict[str, Any]:
    row: dict[str, Any] = {column: timeline[column] for column in (*KEY, *WINDOW_COLUMNS)}
    for column in WINDOW_COLUMNS:
        row[column] = int(row[column])
    row.update({column: None for column in OUTPUT_FIELDS if column not in row})
    row["mmwave_eligibility_label"] = "EXCLUDE_FROM_FINAL_MULTIMODAL_CONTRIBUTION"
    row["mmwave_adapter_source_commit"] = adapter_commit
    if source is None:
        row.update({
            "mmwave_state": "STRUCTURAL_MISSING", "mmwave_observed": False,
            "mmwave_missing_reason": "NO_CANONICAL_MMWAVE_PROBE_SOURCE",
            "mmwave_failure_reason": "NO_EXACT_FIVE_COLUMN_KEYED_MMWAVE_OUTPUT",
        })
    else:
        observed = parse_bool(source.get("mmwave_observed"), field="mmwave_observed")
        row.update({
            "mmwave_observed": observed,
            "mmwave_source_run_id": nullable(source.get("mmwave_source_run_id")),
            "mmwave_source_commit": nullable(source.get("mmwave_source_commit")),
            "mmwave_estimator_version": nullable(source.get("mmwave_estimator_version")),
            "mmwave_loadable": parse_bool(source["mmwave_loadable"], field="mmwave_loadable") if nullable(source.get("mmwave_loadable")) else None,
            "mmwave_timestamp_coverage_fraction": fraction(source.get("mmwave_timestamp_coverage_fraction"), field="mmwave_timestamp_coverage_fraction"),
            "mmwave_hr_usable_window_fraction": fraction(source.get("mmwave_hr_usable_window_fraction"), field="mmwave_hr_usable_window_fraction"),
            "mmwave_hr_mean_confidence": number(source.get("mmwave_hr_mean_confidence"), field="mmwave_hr_mean_confidence"),
        })
        if observed:
            row.update({
                "mmwave_state": "NOT_ELIGIBLE", "mmwave_missing_reason": "FORMAL_MMWAVE_PHYSIOLOGY_HOLD",
                "mmwave_failure_reason": nullable(source.get("mmwave_failure_reason")) or "T5_HR_BR_NOT_PASS__T6_HRV_EXCLUDE",
            })
        else:
            state = nullable(source.get("mmwave_state")) or "OBSERVATION_MISSING"
            if state not in {"STRUCTURAL_MISSING", "OBSERVATION_MISSING", "UNRESOLVED"}:
                raise ValueError(f"unobserved source row has invalid state {state!r}")
            row.update({
                "mmwave_state": state,
                "mmwave_missing_reason": nullable(source.get("mmwave_missing_reason")) or "UPSTREAM_MMWAVE_OBSERVATION_MISSING",
                "mmwave_failure_reason": nullable(source.get("mmwave_failure_reason")),
            })
    for column in WITHHELD_FIELDS:
        row[column] = None
    return row


def validate_rows(rows: list[dict[str, Any]]) -> None:
    keys = [tuple(str(row[column]) for column in KEY) for row in rows]
    if len(keys) != len(set(keys)) or any(not all(key) for key in keys):
        raise ValueError("output canonical keys are null or non-unique")
    for row in rows:
        if row["mmwave_observed"] and row["mmwave_state"] not in {"OBSERVED", "QC_FAIL", "NOT_ELIGIBLE"}:
            raise ValueError("observed output row has incompatible state")
        if not row["mmwave_observed"] and row["mmwave_state"] not in {"STRUCTURAL_MISSING", "OBSERVATION_MISSING", "UNRESOLVED"}:
            raise ValueError("unobserved output row has incompatible state")
        if row["window_name"] != "pre_30s" or row["mmwave_eligibility_label"] != "EXCLUDE_FROM_FINAL_MULTIMODAL_CONTRIBUTION":
            raise ValueError("adapter may not alter the frozen window or contribution eligibility")
        if any(row[column] is not None for column in WITHHELD_FIELDS):
            raise ValueError("held physiology/diagnostic fields must remain null")


def csv_value(value: Any) -> str:
    if value is None:
        return ""
    return ("true" if value else "false") if isinstance(value, bool) else str(value)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--timeline", type=Path, required=True, help="canonical_probe_timeline.csv")
    parser.add_argument("--out-dir", type=Path, required=True, help="local-only formal_multimodal_v2/mmwave directory")
    parser.add_argument("--source-index", type=Path, help="optional exact-keyed mmWave availability index")
    args = parser.parse_args()
    timeline_rows, timeline_fields = read_csv(args.timeline)
    validate_timeline(timeline_rows, timeline_fields)
    source_index, source_meta = load_source_index(args.source_index, {key_of(row) for row in timeline_rows})
    adapter_commit = git_head()
    rows = [build_row(row, source_index.get(key_of(row)), adapter_commit) for row in timeline_rows]
    validate_rows(rows)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    output_csv = args.out_dir / "mmwave_probe_merge_ready.csv"
    with output_csv.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=OUTPUT_FIELDS)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: csv_value(row[key]) for key in OUTPUT_FIELDS})
    state_counts = Counter(row["mmwave_state"] for row in rows)
    reason_counts = Counter(row["mmwave_missing_reason"] for row in rows)
    eligibility_counts = Counter(row["mmwave_eligibility_label"] for row in rows)
    audit_rows = ([{"category": "mmwave_state", "value": key, "rows": value} for key, value in sorted(state_counts.items())] +
                  [{"category": "mmwave_missing_reason", "value": key or "<null>", "rows": value} for key, value in sorted(reason_counts.items(), key=lambda pair: str(pair[0]))] +
                  [{"category": "mmwave_eligibility_label", "value": key, "rows": value} for key, value in sorted(eligibility_counts.items())])
    audit_path = args.out_dir / "mmwave_probe_merge_ready_audit.csv"
    with audit_path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=["category", "value", "rows"])
        writer.writeheader(); writer.writerows(audit_rows)
    matched = sum(key_of(row) in source_index for row in timeline_rows)
    manifest = {
        "schema_version": "focuswave-mmwave-probe-adapter-v1",
        "adapter_status": "PARTIAL" if not source_index else "STRUCTURAL_PASS__FORMAL_CONTRIBUTION_BLOCKED",
        "canonical_probe_key": list(KEY), "window": "pre_30s",
        "timeline": {"path": str(args.timeline), "sha256": sha256(args.timeline), "rows": len(rows)},
        "source_index": source_meta, "adapter_source_commit": adapter_commit,
        "output": {"csv": output_csv.name, "sha256": sha256(output_csv), "rows": len(rows)},
        "join": {"timeline_rows": len(rows), "source_index_rows": len(source_index), "matched_source_rows": matched, "unmatched_timeline_rows": len(rows) - matched, "unique_nonnull_key": True},
        "state_counts": dict(sorted(state_counts.items())),
        "missing_reason_counts": dict(sorted(reason_counts.items(), key=lambda pair: str(pair[0]))),
        "eligibility_counts": dict(sorted(eligibility_counts.items())),
        "scientific_boundary": "T5 HR/BR formal validity is not PASS and T6 HRV remains EXCLUDE; no physiology or diagnostic field may enter final multimodal contribution analysis.",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
    }
    (args.out_dir / "mmwave_probe_merge_ready_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"status": manifest["adapter_status"], "out_dir": str(args.out_dir), "rows": len(rows), "state_counts": manifest["state_counts"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
