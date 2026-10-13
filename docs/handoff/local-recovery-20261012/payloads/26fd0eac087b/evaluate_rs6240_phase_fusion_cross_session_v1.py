"""Experimental cross-session RS6240 phase-fusion evaluation.

This script is deliberately separate from the S1 mainline.  It reuses the
radar-only signal construction from the first-pass experiment, but evaluates
four independent sessions with the fixed +0.365 s ECG alignment and the
monotonic one-to-one ECG evaluator.  ECG is never used to choose a channel,
range bin, or fusion weight.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "work"))

import evaluate_rs6240_phase_fusion as base  # noqa: E402
from rs6240_ecg_evaluator_v1 import evaluate_matched_beats  # noqa: E402


REFERENCE = base.REFERENCE
DEFAULT_OUTPUT = Path(__file__).resolve().parent / "rs6240_phase_fusion_cross_session_v1"
EXCLUDED_DEVELOPMENT_SESSION = "sub-97793_"
INDEPENDENT_SESSIONS = {"sub-97794_", "sub-97795_", "sub-97796_", "sub-9779_"}
DATA_SESSION_ALIASES = {"sub-97794_": "sub-97994_"}
OFFSET_S = 0.365
TOLERANCE_S = 0.150
MODELS = {
    "S1": list(range(8)),
    "T0": [0, 1, 2, 3],
    "T1": [4, 5, 6, 7],
    "A4": [0, 1, 4, 5],
    "C8-PH": list(range(8)),
}


def _float(value):
    return float(value) if value not in (None, "", "nan") else None


def choose_s1(cube: np.ndarray) -> tuple[np.ndarray, dict]:
    """Select one channel using radar-only phase quality at a radar-only bin."""

    bin_idx = base.model_bin(cube, list(range(8)))
    scores = []
    for channel in range(8):
        phi = base.phase_signal(cube, bin_idx, channel)
        band = base._sos_bandpass(phi, base.HR_LO_HZ, base.HR_HI_HZ)
        scores.append(float(np.std(band)))
    channel = int(np.argmax(scores))
    signal = base._sos_bandpass(
        base.phase_signal(cube, bin_idx, channel), base.HR_LO_HZ, base.HR_HI_HZ
    )
    return signal, {"channels": [channel], "weights": [1.0], "bin": bin_idx}


def construct_signal(cube: np.ndarray, model: str) -> tuple[np.ndarray, dict]:
    if model == "S1":
        return choose_s1(cube)
    channels = MODELS[model]
    bin_idx = base.model_bin(cube, channels)
    signal, meta = base.fuse_phase(cube, bin_idx, channels)
    return signal, meta


def evaluate_window(row: dict[str, str], model: str) -> dict:
    session = row["session_id"]
    data_session = DATA_SESSION_ALIASES.get(session, session)
    onset_ms = int(row["onset_ms"])
    onset_acq_s = float(row["onset_acq_s"])
    cube, frame_start, frame_end = base.load_window(data_session, onset_ms - 30000, onset_ms)
    signal, meta = construct_signal(cube, model)
    radar = base.analyze_signal(signal, data_session)
    ecg = base.ecg_clean_peaks(data_session, onset_acq_s)
    matched = evaluate_matched_beats(
        ecg["peaks_s"], radar["peaks_s"], offset_s=OFFSET_S, tolerance_s=TOLERANCE_S
    )
    raw_hr = radar["raw_hr_bpm"]
    rsp_br = _float(row.get("rsp_br_bpm_goldclean"))
    harmonic_mislock = None
    if raw_hr is not None and rsp_br is not None:
        harmonic_mislock = int(any(abs(raw_hr - h * rsp_br) <= 5.0 for h in (2.0, 3.0)))
    pred_hr = radar["result"]["heart_rate"].get("time_bpm")
    return {
        "session_id": session,
        "onset_ms": onset_ms,
        "attention": row.get("attention"),
        "frame_start": frame_start,
        "frame_end": frame_end,
        "model": model,
        "channels": "|".join(str(x) for x in meta["channels"]),
        "range_bin": meta["bin"],
        "weights": json.dumps(meta["weights"]),
        "ecg_hr_bpm": ecg["hr_bpm"],
        "pred_hr_bpm": pred_hr,
        "hr_abs_error_bpm": abs(float(pred_hr) - ecg["hr_bpm"])
        if pred_hr is not None and ecg["hr_bpm"] is not None
        else None,
        "ecg_ibi_count": len(ecg["ibi_ms"]),
        "pred_beat_count": len(radar["peaks_s"]),
        "resp_harmonic_mislock": harmonic_mislock,
        **matched,
    }


def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = list(rows[0]) if rows else ["session_id", "model", "error"]
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def mean(rows: list[dict], key: str):
    values = [float(row[key]) for row in rows if row.get(key) not in (None, "")]
    return float(np.mean(values)) if values else None


def run(output: Path) -> dict:
    all_rows = base.read_csv(REFERENCE)
    rows = [
        row
        for row in all_rows
        if row["session_id"] in INDEPENDENT_SESSIONS and row["session_id"] != EXCLUDED_DEVELOPMENT_SESSION
    ]
    rows.sort(key=lambda row: (row["session_id"], int(row["onset_ms"])))
    failures = []
    metrics = []
    for row in rows:
        for model in MODELS:
            try:
                metrics.append(evaluate_window(row, model))
            except Exception as exc:  # retain failure provenance and continue
                failures.append({
                    "session_id": row.get("session_id"),
                    "onset_ms": row.get("onset_ms"),
                    "model": model,
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                })

    output.mkdir(parents=True, exist_ok=True)
    write_csv(output / "window_metrics.csv", metrics)
    write_csv(output / "failures.csv", failures)

    summary_rows = []
    for session in sorted(INDEPENDENT_SESSIONS):
        for model in MODELS:
            subset = [r for r in metrics if r["session_id"] == session and r["model"] == model]
            summary_rows.append({
                "session_id": session,
                "model": model,
                "n_windows": len(subset),
                "n_failures": sum(1 for f in failures if f["session_id"] == session and f["model"] == model),
                "hr_mae_bpm": mean(subset, "hr_abs_error_bpm"),
                "ibi_mae_ms_matched": mean(subset, "ibi_mae_ms_matched"),
                "ibi_rmse_ms_matched": mean(subset, "ibi_rmse_ms_matched"),
                "rmssd_error_ms_matched": mean(subset, "rmssd_abs_error_ms_matched"),
                "beat_recall": mean(subset, "beat_recall"),
                "false_beat_rate": mean(subset, "false_beat_rate"),
                "resp_harmonic_mislock": mean(subset, "resp_harmonic_mislock"),
                "matched_ibi_usable_windows": sum(r.get("ibi_mae_ms_matched") is not None for r in subset),
                "matched_rmssd_usable_windows": sum(r.get("rmssd_abs_error_ms_matched") is not None for r in subset),
            })
    write_csv(output / "session_model_summary.csv", summary_rows)

    delta_rows = []
    metrics_to_delta = [
        "hr_mae_bpm", "ibi_mae_ms_matched", "ibi_rmse_ms_matched",
        "rmssd_error_ms_matched", "beat_recall", "false_beat_rate", "resp_harmonic_mislock",
    ]
    by_key = {(r["session_id"], r["model"]): r for r in summary_rows}
    for session in sorted(INDEPENDENT_SESSIONS):
        s1 = by_key[(session, "S1")]
        row = {"session_id": session, "n_windows_s1": s1["n_windows"], "delta_definition": "model - S1; lower is better except beat_recall"}
        for model in ("T0", "T1", "A4", "C8-PH"):
            candidate = by_key[(session, model)]
            for key in metrics_to_delta:
                left, right = candidate[key], s1[key]
                row[f"{model}_delta_{key}"] = float(left - right) if left is not None and right is not None else None
        delta_rows.append(row)
    write_csv(output / "session_deltas_T0_minus_S1.csv", delta_rows)

    result = {
        "evaluator_version": "ECG evaluator v1",
        "sessions": sorted(INDEPENDENT_SESSIONS),
        "excluded_development_session": EXCLUDED_DEVELOPMENT_SESSION,
        "reference_windows": len(rows),
        "completed_model_rows": len(metrics),
        "failed_model_rows": len(failures),
        "models": list(MODELS),
        "fixed_global_offset_s": OFFSET_S,
        "matching_tolerance_ms": TOLERANCE_S * 1000.0,
        "weight_source": "radar-only phase/power QC; no ECG labels used for selection",
        "notes": [
            "Experimental cross-session phase-domain ablation; does not modify S1 mainline.",
            "The development session sub-97793_ is excluded from this independent summary.",
            "IBI and RMSSD are computed only from adjacent matched beats by the fixed evaluator.",
            "No complex coherent fusion was run; C8-PH means eight-channel phase-domain fusion.",
            "No candidate may enter the formal baseline without session-level ECG review and confirmation.",
        ],
    }
    (output / "summary.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    print(json.dumps(run(args.output), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
