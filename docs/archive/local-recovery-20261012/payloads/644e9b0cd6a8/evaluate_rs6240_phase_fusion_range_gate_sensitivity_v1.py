"""Range-bin candidate gate sensitivity for the RS6240 phase-fusion experiment.

This is a sensitivity analysis only.  It keeps all signal construction and ECG
evaluation rules fixed, but restricts radar-only range-bin selection to a
plausible candidate region.  It must not be used to replace the unconstrained
analysis or the S1 formal baseline without independent review.
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
SESSIONS = {"sub-97794_", "sub-97795_", "sub-97796_", "sub-9779_"}
ALIAS = {"sub-97794_": "sub-97994_"}
MODELS = {"S1": list(range(8)), "T0": [0, 1, 2, 3], "T1": [4, 5, 6, 7], "A4": [0, 1, 4, 5], "C8-PH": list(range(8))}
OFFSET_S = 0.365
TOLERANCE_S = 0.150


def gated_bin(cube: np.ndarray, channels: list[int], lo: int, hi: int) -> int:
    power = np.mean(np.abs(cube) ** 2, axis=0)
    candidates: dict[int, list[float]] = {}
    for ch in channels:
        _, _, rows = base.select_bins_from_profile(power, ch, cube, len(cube))
        for bin_idx, _hr, _br, _score, _stability, heart_score in rows:
            if lo <= int(bin_idx) <= hi:
                candidates.setdefault(int(bin_idx), []).append(float(heart_score))
    if candidates:
        return max(candidates, key=lambda idx: float(np.mean(candidates[idx])))
    window = power[lo : hi + 1, channels]
    return int(lo + np.argmax(np.mean(window, axis=1)))


def signal_for(cube: np.ndarray, model: str, lo: int, hi: int):
    channels = MODELS[model]
    bin_idx = gated_bin(cube, channels, lo, hi)
    if model == "S1":
        scores = []
        for ch in range(8):
            phi = base.phase_signal(cube, bin_idx, ch)
            scores.append(float(np.std(base._sos_bandpass(phi, base.HR_LO_HZ, base.HR_HI_HZ))))
        ch = int(np.argmax(scores))
        x = base._sos_bandpass(base.phase_signal(cube, bin_idx, ch), base.HR_LO_HZ, base.HR_HI_HZ)
        return x, {"channels": [ch], "weights": [1.0], "bin": bin_idx}
    x, meta = base.fuse_phase(cube, bin_idx, channels)
    return x, meta


def row_for(ref: dict[str, str], model: str, lo: int, hi: int) -> dict:
    session = ref["session_id"]
    data_session = ALIAS.get(session, session)
    onset = int(ref["onset_ms"])
    cube, a, b = base.load_window(data_session, onset - 30000, onset)
    x, meta = signal_for(cube, model, lo, hi)
    radar = base.analyze_signal(x, data_session)
    ecg = base.ecg_clean_peaks(data_session, float(ref["onset_acq_s"]))
    matched = evaluate_matched_beats(ecg["peaks_s"], radar["peaks_s"], OFFSET_S, TOLERANCE_S)
    pred_hr = radar["result"]["heart_rate"].get("time_bpm")
    rsp = float(ref["rsp_br_bpm_goldclean"]) if ref.get("rsp_br_bpm_goldclean") else None
    raw = radar["raw_hr_bpm"]
    mislock = int(any(abs(raw - h * rsp) <= 5.0 for h in (2.0, 3.0))) if raw is not None and rsp else None
    return {
        "session_id": session, "onset_ms": onset, "model": model, "range_bin": meta["bin"],
        "channels": "|".join(str(c) for c in meta["channels"]), "weights": json.dumps(meta["weights"]),
        "frame_start": a, "frame_end": b, "ecg_hr_bpm": ecg["hr_bpm"], "pred_hr_bpm": pred_hr,
        "hr_abs_error_bpm": abs(float(pred_hr) - ecg["hr_bpm"]) if pred_hr is not None and ecg["hr_bpm"] is not None else None,
        "resp_harmonic_mislock": mislock, **matched,
    }


def write_csv(path: Path, rows: list[dict]) -> None:
    fields = list(rows[0]) if rows else ["session_id", "model", "error"]
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields); w.writeheader(); w.writerows(rows)


def avg(rows, key):
    v = [float(r[key]) for r in rows if r.get(key) not in (None, "")]
    return float(np.mean(v)) if v else None


def main() -> None:
    ap = argparse.ArgumentParser(); ap.add_argument("--bin-lo", type=int, default=5); ap.add_argument("--bin-hi", type=int, default=32); ap.add_argument("--output", type=Path, required=True); args = ap.parse_args()
    refs = sorted([r for r in base.read_csv(REFERENCE) if r["session_id"] in SESSIONS], key=lambda r: (r["session_id"], int(r["onset_ms"])))
    rows, failures = [], []
    for ref in refs:
        for model in MODELS:
            try: rows.append(row_for(ref, model, args.bin_lo, args.bin_hi))
            except Exception as exc: failures.append({"session_id": ref["session_id"], "onset_ms": ref["onset_ms"], "model": model, "error": f"{type(exc).__name__}: {exc}"})
    args.output.mkdir(parents=True, exist_ok=True); write_csv(args.output / "window_metrics.csv", rows); write_csv(args.output / "failures.csv", failures)
    summaries=[]
    for s in sorted(SESSIONS):
        for m in MODELS:
            z=[r for r in rows if r["session_id"]==s and r["model"]==m]; summaries.append({"session_id":s,"model":m,"n_windows":len(z),"hr_mae_bpm":avg(z,"hr_abs_error_bpm"),"ibi_mae_ms_matched":avg(z,"ibi_mae_ms_matched"),"rmssd_error_ms_matched":avg(z,"rmssd_abs_error_ms_matched"),"beat_recall":avg(z,"beat_recall"),"false_beat_rate":avg(z,"false_beat_rate"),"resp_harmonic_mislock":avg(z,"resp_harmonic_mislock")})
    write_csv(args.output / "session_model_summary.csv", summaries)
    summary={"analysis":"range-bin gate sensitivity","bin_lo":args.bin_lo,"bin_hi":args.bin_hi,"sessions":sorted(SESSIONS),"reference_windows":len(refs),"completed_model_rows":len(rows),"failed_model_rows":len(failures),"fixed_global_offset_s":OFFSET_S,"matching_tolerance_ms":150.0,"notes":["Radar-only range selection gate; ECG not used for bin or weight selection.","Sensitivity only; do not replace unconstrained analysis or S1 baseline."]}
    (args.output / "summary.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps(summary,ensure_ascii=False,indent=2))


if __name__ == "__main__": main()
