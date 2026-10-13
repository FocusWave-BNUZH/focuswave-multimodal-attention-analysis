"""Compare a radar-only physical power-gated candidate against frozen S1."""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "work"))
import evaluate_rs6240_phase_fusion_cross_session_v1 as cross  # noqa: E402
from rs6240_ecg_evaluator_v1 import evaluate_matched_beats  # noqa: E402


OUT = ROOT / "work" / "rs6240_power_gate_vs_frozen_s1_v1"
LO, HI = 5, 32
ALIAS = {"sub-97794_": "sub-97994_"}
MODELS = {"S1": None, "T0": [0, 1, 2, 3], "T1": [4, 5, 6, 7], "A4": [0, 1, 4, 5], "C8-PH": list(range(8))}


def power_bin(cube: np.ndarray, channels: list[int]) -> int:
    profile = np.mean(np.abs(cube[:, :, channels]) ** 2, axis=(0, 2))
    return int(LO + np.argmax(profile[LO : HI + 1]))


def construct(cube: np.ndarray, model: str):
    if model == "S1":
        return cross.choose_s1(cube)
    channels = MODELS[model]
    idx = power_bin(cube, channels)
    x, meta = cross.base.fuse_phase(cube, idx, channels)
    return x, meta


def evaluate(ref: dict, model: str) -> dict:
    session = ref["session_id"]
    data_session = ALIAS.get(session, session)
    onset = int(ref["onset_ms"])
    cube, a, b = cross.base.load_window(data_session, onset - 30000, onset)
    x, meta = construct(cube, model)
    radar = cross.base.analyze_signal(x, data_session)
    ecg = cross.base.ecg_clean_peaks(data_session, float(ref["onset_acq_s"]))
    matched = evaluate_matched_beats(ecg["peaks_s"], radar["peaks_s"], cross.OFFSET_S, cross.TOLERANCE_S)
    pred_hr = radar["result"]["heart_rate"].get("time_bpm")
    rsp = float(ref["rsp_br_bpm_goldclean"]) if ref.get("rsp_br_bpm_goldclean") else None
    raw = radar["raw_hr_bpm"]
    mislock = int(any(abs(raw - h * rsp) <= 5.0 for h in (2.0, 3.0))) if raw is not None and rsp else None
    return {"session_id": session, "onset_ms": onset, "model": model, "range_bin": meta["bin"], "channels": "|".join(map(str, meta["channels"])), "weights": json.dumps(meta["weights"]), "frame_start": a, "frame_end": b, "hr_abs_error_bpm": abs(float(pred_hr)-ecg["hr_bpm"]) if pred_hr is not None and ecg["hr_bpm"] is not None else None, "resp_harmonic_mislock": mislock, **matched}


def avg(rows, key):
    values = [float(r[key]) for r in rows if r.get(key) not in (None, "")]
    return float(np.mean(values)) if values else None


def write(path, rows):
    fields = list(rows[0]) if rows else ["session_id", "model", "error"]
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields); w.writeheader(); w.writerows(rows)


def main():
    refs = sorted([r for r in cross.base.read_csv(cross.REFERENCE) if r["session_id"] in cross.INDEPENDENT_SESSIONS], key=lambda r:(r["session_id"],int(r["onset_ms"])))
    rows=[]; failures=[]
    for ref in refs:
        for model in MODELS:
            try: rows.append(evaluate(ref, model))
            except Exception as exc: failures.append({"session_id":ref["session_id"],"onset_ms":ref["onset_ms"],"model":model,"error":f"{type(exc).__name__}: {exc}"})
    OUT.mkdir(parents=True,exist_ok=True); write(OUT/'window_metrics.csv',rows); write(OUT/'failures.csv',failures)
    summaries=[]
    for s in sorted(cross.INDEPENDENT_SESSIONS):
        for m in MODELS:
            z=[r for r in rows if r['session_id']==s and r['model']==m]; summaries.append({'session_id':s,'model':m,'n_windows':len(z),'hr_mae_bpm':avg(z,'hr_abs_error_bpm'),'ibi_mae_ms_matched':avg(z,'ibi_mae_ms_matched'),'rmssd_error_ms_matched':avg(z,'rmssd_abs_error_ms_matched'),'beat_recall':avg(z,'beat_recall'),'false_beat_rate':avg(z,'false_beat_rate'),'resp_harmonic_mislock':avg(z,'resp_harmonic_mislock')})
    write(OUT/'session_model_summary.csv',summaries)
    by={(r['session_id'],r['model']):r for r in summaries}; deltas=[]
    for s in sorted(cross.INDEPENDENT_SESSIONS):
        base_row=by[(s,'S1')]; out={'session_id':s,'delta_definition':'candidate - frozen S1; lower is better except beat_recall'}
        for m in ('T0','T1','A4','C8-PH'):
            for k in ('hr_mae_bpm','ibi_mae_ms_matched','rmssd_error_ms_matched','beat_recall','resp_harmonic_mislock'):
                x,y=by[(s,m)].get(k),base_row.get(k); out[f'{m}_delta_{k}']=float(x)-float(y) if x is not None and y is not None else None
        deltas.append(out)
    write(OUT/'session_deltas_vs_frozen_s1.csv',deltas)
    summary={'analysis':'physical power-gated candidate versus frozen S1','bin_gate':[LO,HI],'sessions':sorted(cross.INDEPENDENT_SESSIONS),'reference_windows':len(refs),'completed_model_rows':len(rows),'failed_model_rows':len(failures),'fixed_global_offset_s':cross.OFFSET_S,'matching_tolerance_ms':150.0,'notes':['S1 retains unconstrained frozen selection; only candidate models use radar-only power-gated bin 5-32.','Experimental only; no mainline change.']}
    (OUT/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8'); print(json.dumps(summary,ensure_ascii=False,indent=2))


if __name__=='__main__': main()
