from __future__ import annotations

import csv
import json
import sys
from functools import lru_cache
from pathlib import Path

import bioread
import numpy as np
from scipy import signal


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from process_vital_signs_v3_1_1 import (  # noqa: E402
    FS,
    HR_HI_HZ,
    HR_LO_HZ,
    _analyze_displacement_v23,
    _sos_bandpass,
    select_bins_from_profile,
)


RAW = Path(r"D:\acq_mmwave_data")
REFERENCE = Path(r"D:\Project\厚粲杯\11_数据\derived\ecg_rsp_goldclean_reaudit_v1\goldclean_reference_windows.csv")
OUT = Path(__file__).resolve().parent / "rs6240_phase_fusion_ecg_v1"
MODELS = {
    "S1": [0],
    "T0": [0, 1, 2, 3],
    "T1": [4, 5, 6, 7],
    "A4": [0, 1, 4, 5],
    "C8-PH": list(range(8)),
}
CHANNEL_KEYS = [f"tx{tx}_rx{rx}" for tx in range(2) for rx in range(4)]


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def ordered_files(mmwave: Path) -> list[Path]:
    return sorted(mmwave.glob("*_mmwave_datacube.npz")) + sorted(mmwave.glob("*_mmwave_datacube_part*.npz"))


@lru_cache(maxsize=16)
def timestamps(session: str) -> np.ndarray:
    path = RAW / session / "mmwave" / f"{session.rstrip('_')}_mmwave_timestamps.csv"
    rows = []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        for row in csv.reader(handle):
            if len(row) >= 3:
                try:
                    rows.append((int(row[0]), int(row[2])))
                except ValueError:
                    pass
    return np.asarray(rows, dtype=np.int64)


@lru_cache(maxsize=16)
def npz_index(session: str) -> tuple[tuple[Path, int, int], ...]:
    records = []
    offset = 0
    for path in ordered_files(RAW / session / "mmwave"):
        with np.load(path, allow_pickle=False) as data:
            keys = sorted(k for k in data.files if k.startswith("tx"))
            if len(keys) != 8 or len({data[k].shape for k in keys}) != 1:
                continue
            n = int(data[keys[0]].shape[0])
        records.append((path, offset, offset + n))
        offset += n
    return tuple(records)


def load_window(session: str, start_ms: int, end_ms: int) -> tuple[np.ndarray, int, int]:
    ts = timestamps(session)
    i0 = int(np.searchsorted(ts[:, 1], start_ms, side="left"))
    i1 = int(np.searchsorted(ts[:, 1], end_ms, side="right"))
    chunks = []
    for path, a, b in npz_index(session):
        left, right = max(i0, a), min(i1, b)
        if left >= right:
            continue
        with np.load(path, allow_pickle=False) as data:
            keys = sorted(k for k in data.files if k.startswith("tx"))
            chunks.append(np.stack([data[k][left - a : right - a] for k in keys], axis=-1).astype(np.complex64))
    if not chunks:
        raise RuntimeError(f"No NPZ data for {session} [{start_ms}, {end_ms}]")
    cube = np.concatenate(chunks, axis=0)
    return cube, i0, i1


@lru_cache(maxsize=16)
def load_ecg(session: str):
    raw_dir = RAW / session
    acq = sorted(raw_dir.glob("*.acq"))
    if not acq:
        raise FileNotFoundError(f"No BIOPAC acq for {session}")
    data = bioread.read_file(str(acq[0]))
    channel = next((c for c in data.channels if "ECG" in str(c.name).upper()), None)
    if channel is None:
        raise RuntimeError(f"No ECG channel in {acq[0]}")
    return np.asarray(channel.data, dtype=float), float(channel.samples_per_second), str(acq[0])


def ecg_clean_peaks(session: str, onset_acq_s: float, window_s: float = 30.0):
    ecg, sr, acq_path = load_ecg(session)
    i0 = max(0, int(round((onset_acq_s - window_s) * sr)))
    i1 = min(len(ecg), int(round(onset_acq_s * sr)))
    seg = ecg[i0:i1] - np.median(ecg[i0:i1])
    sos = signal.butter(3, [0.5, 40.0], btype="band", fs=sr, output="sos")
    filtered = signal.sosfiltfilt(sos, seg)
    raw_peaks, _ = signal.find_peaks(filtered, distance=int(0.3 * sr), prominence=0.25)
    ibi_ms = np.diff(raw_peaks) / sr * 1000.0
    valid = (ibi_ms >= 300.0) & (ibi_ms <= 2000.0)
    if len(ibi_ms) >= 3:
        rel = np.abs(np.diff(ibi_ms)) / np.maximum(ibi_ms[:-1], 1.0)
        bad = np.zeros(len(ibi_ms), dtype=bool)
        for idx in np.where(rel > 0.20)[0]:
            bad[idx] = True
            bad[idx + 1] = True
        valid &= ~bad
    keep_peaks = raw_peaks[:-1][valid]
    if len(raw_peaks) and valid.size:
        keep_peaks = np.unique(np.concatenate([keep_peaks, raw_peaks[1:][valid]]))
    clean_ibi = np.diff(raw_peaks) / sr * 1000.0
    clean_ibi = clean_ibi[valid]
    return {
        "peaks_s": keep_peaks / sr,
        "ibi_ms": clean_ibi,
        "hr_bpm": 60000.0 / np.median(clean_ibi) if len(clean_ibi) else None,
        "rmssd_ms": float(np.sqrt(np.mean(np.diff(clean_ibi) ** 2))) if len(clean_ibi) >= 3 else None,
        "acq_path": acq_path,
        "sr": sr,
    }


def model_bin(cube: np.ndarray, channels: list[int]) -> int:
    power = np.mean(np.abs(cube) ** 2, axis=0)
    candidates: dict[int, list[float]] = {}
    for ch in channels:
        _, _, rows = select_bins_from_profile(power, ch, cube, len(cube))
        for bin_idx, _hr_snr, _br_snr, _br_score, _stability, heart_score in rows:
            candidates.setdefault(int(bin_idx), []).append(float(heart_score))
    if candidates:
        return max(candidates, key=lambda idx: float(np.mean(candidates[idx])))
    return int(np.argmax(np.mean(power[:, channels], axis=1)))


def phase_signal(cube: np.ndarray, bin_idx: int, ch: int) -> np.ndarray:
    return np.unwrap(np.angle(cube[:, bin_idx, ch])).astype(float)


def fuse_phase(cube: np.ndarray, bin_idx: int, channels: list[int]) -> tuple[np.ndarray, dict]:
    signals = []
    scores = []
    for ch in channels:
        phi = phase_signal(cube, bin_idx, ch)
        band = _sos_bandpass(phi, HR_LO_HZ, HR_HI_HZ)
        residual = phi - signal.sosfiltfilt(signal.butter(3, [0.5, 3.0], btype="band", fs=FS, output="sos"), phi)
        score = float(np.std(band) / max(np.std(residual), 1e-9))
        signals.append(band - np.mean(band))
        scores.append(max(score, 1e-6))
    weights = np.asarray(scores, dtype=float)
    weights /= np.sum(weights)
    return np.sum(np.asarray(signals) * weights[:, None], axis=0), {"weights": weights.tolist(), "channels": channels, "bin": bin_idx}


def analyze_signal(x: np.ndarray, session: str):
    result, (_t, _breath, _heartbeat, peaks, _bp) = _analyze_displacement_v23(x, x, len(x), method="bp_heart", session=session)
    ibi = np.diff(peaks) / FS * 1000.0 if len(peaks) >= 2 else np.asarray([], dtype=float)
    ibi = ibi[(ibi >= 300.0) & (ibi <= 2000.0)]
    raw_phase = signal.detrend(x, type="linear")
    freqs, pxx = signal.periodogram(raw_phase, fs=FS, window="hann")
    mask = (freqs >= HR_LO_HZ) & (freqs <= HR_HI_HZ)
    raw_bpm = float(freqs[mask][np.argmax(pxx[mask])] * 60.0) if np.any(mask) else None
    return {"result": result, "peaks_s": peaks / FS, "ibi_ms": ibi, "raw_hr_bpm": raw_bpm}


def match_peaks(ecg_s: np.ndarray, radar_s: np.ndarray) -> dict:
    if not len(ecg_s) or not len(radar_s):
        return {"recall": None, "false_beat_rate": None, "matched_count": 0, "timing_mae_ms": None}
    best = None
    for offset in np.arange(-1.0, 1.0001, 0.02):
        used = set()
        pairs = []
        for r_idx, r in enumerate(radar_s + offset):
            candidates = [(abs(float(r - e)), e_idx) for e_idx, e in enumerate(ecg_s) if e_idx not in used and abs(r - e) <= 0.15]
            if candidates:
                err, e_idx = min(candidates)
                used.add(e_idx)
                pairs.append((r_idx, e_idx, err))
        score = (len(pairs), -np.median([p[2] for p in pairs]) if pairs else -999.0)
        if best is None or score > best[0]:
            best = (score, offset, pairs)
    _, offset, pairs = best
    errors = np.asarray([p[2] * 1000.0 for p in pairs], dtype=float)
    return {"recall": len(pairs) / len(ecg_s), "false_beat_rate": max(0, len(radar_s) - len(pairs)) / len(radar_s), "matched_count": len(pairs), "timing_mae_ms": float(np.mean(np.abs(errors))) if len(errors) else None, "alignment_offset_s": float(offset)}


def main() -> None:
    reference = [row for row in read_csv(REFERENCE) if row["session_id"] == "sub-97793_"][:10]
    rows = []
    for ref in reference:
        session = ref["session_id"]
        onset_ms = int(ref["onset_ms"])
        onset_acq_s = float(ref["onset_acq_s"])
        cube, frame_start, frame_end = load_window(session, onset_ms - 30000, onset_ms)
        ecg = ecg_clean_peaks(session, onset_acq_s)
        for model, channels in MODELS.items():
            if model == "S1":
                all_channels = list(range(8))
                bin_idx = model_bin(cube, all_channels)
                # Choose the best single channel at the selected bin by band-limited phase quality.
                scores = []
                for ch in all_channels:
                    phi = phase_signal(cube, bin_idx, ch)
                    band = _sos_bandpass(phi, HR_LO_HZ, HR_HI_HZ)
                    scores.append(float(np.std(band)))
                ch = int(np.argmax(scores))
                x = _sos_bandpass(phase_signal(cube, bin_idx, ch), HR_LO_HZ, HR_HI_HZ)
                meta = {"channels": [ch], "bin": bin_idx, "weights": [1.0]}
            else:
                bin_idx = model_bin(cube, channels)
                x, meta = fuse_phase(cube, bin_idx, channels)
            analysis = analyze_signal(x, session)
            pred_peaks = analysis["peaks_s"]
            match = match_peaks(ecg["peaks_s"], pred_peaks)
            pred_ibi = analysis["ibi_ms"]
            ecg_ibi = ecg["ibi_ms"]
            n = min(len(pred_ibi), len(ecg_ibi))
            paired_ibi = pred_ibi[:n] - ecg_ibi[:n] if n else np.asarray([], dtype=float)
            pred_rmssd = float(np.sqrt(np.mean(np.diff(pred_ibi) ** 2))) if len(pred_ibi) >= 3 else None
            row = {
                "session": session,
                "onset_ms": onset_ms,
                "attention": ref["attention"],
                "frame_start": frame_start,
                "frame_end": frame_end,
                "model": model,
                "channels": "|".join(map(str, meta["channels"])),
                "range_bin": meta["bin"],
                "weights": json.dumps(meta["weights"]),
                "ecg_hr_bpm": ecg["hr_bpm"],
                "pred_hr_bpm": analysis["result"]["heart_rate"].get("time_bpm"),
                "pred_raw_spectral_hr_bpm": analysis["raw_hr_bpm"],
                "hr_abs_error_bpm": abs(float(analysis["result"]["heart_rate"]["time_bpm"]) - ecg["hr_bpm"]) if analysis["result"]["heart_rate"].get("time_bpm") is not None and ecg["hr_bpm"] is not None else None,
                "ecg_ibi_median_ms": float(np.median(ecg_ibi)) if len(ecg_ibi) else None,
                "pred_ibi_median_ms": float(np.median(pred_ibi)) if len(pred_ibi) else None,
                "ibi_mae_ms_truncated": float(np.mean(np.abs(paired_ibi))) if len(paired_ibi) else None,
                "ibi_rmse_ms_truncated": float(np.sqrt(np.mean(paired_ibi ** 2))) if len(paired_ibi) else None,
                "ecg_rmssd_ms": ecg["rmssd_ms"],
                "pred_rmssd_ms": pred_rmssd,
                "rmssd_abs_error_ms": abs(pred_rmssd - ecg["rmssd_ms"]) if pred_rmssd is not None and ecg["rmssd_ms"] is not None else None,
                "beat_recall": match["recall"],
                "false_beat_rate": match["false_beat_rate"],
                "matched_beat_count": match["matched_count"],
                "matched_timing_mae_ms": match["timing_mae_ms"],
                "alignment_offset_s_for_evaluation": match.get("alignment_offset_s"),
                "resp_harmonic_mislock": int(any(abs(float(analysis["raw_hr_bpm"]) - harmonic * float(ref["rsp_br_bpm_goldclean"])) <= 5.0 for harmonic in (2.0, 3.0))) if analysis["raw_hr_bpm"] is not None and ref.get("rsp_br_bpm_goldclean") else None,
            }
            rows.append(row)
        print(f"processed {session} onset={onset_ms} frames={frame_end-frame_start}")
    OUT.mkdir(parents=True, exist_ok=True)
    with (OUT / "fusion_ecg_window_metrics.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    summary = {"reference_windows": len(reference), "models": {}}
    for model in MODELS:
        model_rows = [r for r in rows if r["model"] == model]
        summary["models"][model] = {key: float(np.nanmean([r[key] for r in model_rows if r[key] is not None])) if any(r[key] is not None for r in model_rows) else None for key in ["hr_abs_error_bpm", "ibi_mae_ms_truncated", "ibi_rmse_ms_truncated", "rmssd_abs_error_ms", "beat_recall", "false_beat_rate", "matched_timing_mae_ms", "resp_harmonic_mislock"]}
    summary["notes"] = ["This first pass evaluates ten calibration windows from sub-97793_ only.", "Weights and range-bin choices use radar-only phase/power criteria; ECG is used after signal construction.", "IBI truncated metrics align arrays by order and are preliminary; matched beat timing uses a bounded evaluation-only offset search.", "No complex coherent fusion was run."]
    with (OUT / "fusion_ecg_summary.json").open("w", encoding="utf-8") as handle:
        json.dump(summary, handle, ensure_ascii=False, indent=2)
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    main()
