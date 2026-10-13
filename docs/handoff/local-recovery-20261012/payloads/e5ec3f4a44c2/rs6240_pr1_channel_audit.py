from __future__ import annotations

import csv
import json
import math
import re
from pathlib import Path

import numpy as np
from scipy import signal


OUT = Path(__file__).resolve().parent / "rs6240_pr1_channel_audit_v1"
FS = 100.0
BR_BAND = (0.1, 0.5)
HR_BAND = (0.8, 2.0)
CHANNELS = [f"tx{tx}_rx{rx}" for tx in range(2) for rx in range(4)]
GROUPS = {
    "TX0": [0, 1, 2, 3],
    "TX1": [4, 5, 6, 7],
    "A4_vertical_azimuth": [0, 1, 4, 5],
    "A4_vertical_elevation": [3, 2, 1],
    "C8": list(range(8)),
}


def csv_rows(path: Path):
    with path.open("r", encoding="utf-8", errors="replace", newline="") as handle:
        for row in csv.reader(handle):
            if len(row) < 3:
                continue
            try:
                yield int(row[0]), int(row[1]), int(row[2])
            except ValueError:
                continue


def ordered_npz_files(mmwave_dir: Path) -> list[Path]:
    base = sorted(mmwave_dir.glob("*_mmwave_datacube.npz"))
    parts = sorted(mmwave_dir.glob("*_mmwave_datacube_part*.npz"))
    return base + parts


def inspect_files(files: list[Path], max_frames: int):
    expected = None
    key_rows = []
    total = 0
    loaded = []
    for path in files:
        with np.load(path, allow_pickle=False) as data:
            keys = sorted(k for k in data.files if k.startswith("tx"))
            shapes = {k: tuple(data[k].shape) for k in keys}
            dtypes = {k: str(data[k].dtype) for k in keys}
            consistent = len(keys) == 8 and len(set(shapes.values())) == 1
            if expected is None:
                expected = {"keys": keys, "shape": shapes.get(keys[0]) if keys else None}
            if total < max_frames and consistent:
                take = min(max_frames - total, shapes[keys[0]][0])
                chunk = np.stack([data[k][:take] for k in keys], axis=-1).astype(np.complex64)
                loaded.append(chunk)
                total += take
            key_rows.append(
                {
                    "file": str(path),
                    "keys": "|".join(keys),
                    "n_keys": len(keys),
                    "shape_set": "|".join(sorted(map(str, set(shapes.values())))),
                    "dtype_set": "|".join(sorted(set(dtypes.values()))),
                    "consistent_8ch": consistent,
                    "frame_count": shapes[keys[0]][0] if keys and consistent else 0,
                }
            )
    if not loaded:
        raise RuntimeError(f"No readable 8-channel data in {files[0].parent}")
    return np.concatenate(loaded, axis=0), key_rows, expected


def timestamp_stats(path: Path, n_data: int) -> dict:
    rows = np.asarray(list(csv_rows(path)), dtype=np.int64)
    out = {"timestamp_file": str(path), "timestamp_rows": int(len(rows)), "npz_audit_frames": int(n_data)}
    if len(rows) < 2:
        return out
    for idx, label in ((1, "device"), (2, "host")):
        delta = np.diff(rows[:, idx]).astype(float)
        duration = (rows[-1, idx] - rows[0, idx]) / 1000.0
        out[f"{label}_duration_s"] = float(duration)
        out[f"{label}_effective_hz"] = float((len(rows) - 1) / duration) if duration > 0 else None
        out[f"{label}_delta_ms_median"] = float(np.median(delta))
        out[f"{label}_delta_ms_p95"] = float(np.percentile(delta, 95))
        out[f"{label}_delta_ms_max"] = float(np.max(delta))
        out[f"{label}_gaps_gt_15ms"] = int(np.sum(delta > 15))
        out[f"{label}_zero_or_negative_deltas"] = int(np.sum(delta <= 0))
    out["frame_id_step_unique"] = "|".join(map(str, np.unique(np.diff(rows[:, 0]))[:20]))
    out["timestamp_rows_match_audit_frames"] = bool(len(rows) == n_data)
    return out


def choose_bins(cube: np.ndarray, n_bins: int = 5) -> list[int]:
    profile = np.mean(np.abs(cube) ** 2, axis=(0, 2))
    valid = np.arange(len(profile))
    valid = valid[(valid >= 4) & (valid < len(profile) - 2)]
    order = valid[np.argsort(profile[valid])[::-1]]
    selected = []
    for idx in order:
        if all(abs(int(idx) - old) >= 3 for old in selected):
            selected.append(int(idx))
        if len(selected) >= n_bins:
            break
    return selected


def safe_corr(x: np.ndarray, y: np.ndarray) -> float:
    if np.std(x) == 0 or np.std(y) == 0:
        return float("nan")
    return float(np.corrcoef(x, y)[0, 1])


def band_coherence(x: np.ndarray, y: np.ndarray, band: tuple[float, float]) -> float:
    nperseg = min(1024, len(x))
    if nperseg < 128:
        return float("nan")
    freqs, coh = signal.coherence(x, y, fs=FS, nperseg=nperseg, noverlap=nperseg // 2)
    mask = (freqs >= band[0]) & (freqs <= band[1])
    return float(np.nanmean(coh[mask])) if np.any(mask) else float("nan")


def circular_sd(x: np.ndarray) -> float:
    r = float(np.abs(np.mean(np.exp(1j * x))))
    return float(math.sqrt(max(0.0, -2.0 * math.log(max(r, 1e-12)))))


def analyze_session(session: str, root: Path, max_frames: int) -> tuple[list[dict], list[dict], list[dict], list[dict], dict, list[dict]]:
    mmwave = root / session / "mmwave"
    timestamp_path = mmwave / f"{session.rstrip('_')}_mmwave_timestamps.csv"
    files = ordered_npz_files(mmwave)
    if not files:
        raise FileNotFoundError(f"No npz files for {session}")
    cube, file_rows, expected = inspect_files(files, max_frames)
    bins = choose_bins(cube)
    timestamp = timestamp_stats(timestamp_path, sum(row["frame_count"] for row in file_rows))
    timestamp["session"] = session
    timestamp["files"] = len(files)
    timestamp["audit_window_frames"] = int(len(cube))
    timestamp["selected_range_bins"] = "|".join(map(str, bins))
    timestamp["keys"] = "|".join(expected["keys"])
    timestamp["shape_first_chunk"] = str(expected["shape"])

    pair_corr = []
    coh_br = []
    coh_hr = []
    relative = []
    for bin_idx in bins:
        phase = np.unwrap(np.angle(cube[:, bin_idx, :]), axis=0)
        phase_inc = np.angle(cube[1:, bin_idx, :] * np.conj(cube[:-1, bin_idx, :]))
        for i in range(8):
            for j in range(i + 1, 8):
                pair = f"{CHANNELS[i]}__{CHANNELS[j]}"
                same_tx = (i // 4) == (j // 4)
                pair_corr.append({"session": session, "range_bin": bin_idx, "ch_i": CHANNELS[i], "ch_j": CHANNELS[j], "pair": pair, "same_tx": same_tx, "phase_increment_corr": safe_corr(phase_inc[:, i], phase_inc[:, j])})
                coh_br.append({"session": session, "range_bin": bin_idx, "pair": pair, "same_tx": same_tx, "coherence_br_mean": band_coherence(phase[:, i], phase[:, j], BR_BAND)})
                coh_hr.append({"session": session, "range_bin": bin_idx, "pair": pair, "same_tx": same_tx, "coherence_hr_mean": band_coherence(phase[:, i], phase[:, j], HR_BAND)})
                relative.append({"session": session, "range_bin": bin_idx, "pair": pair, "same_tx": same_tx, "relative_phase_circular_sd_rad": circular_sd(np.angle(cube[:, bin_idx, i] * np.conj(cube[:, bin_idx, j]))), "relative_phase_mean_rad": float(np.angle(np.mean(cube[:, bin_idx, i] * np.conj(cube[:, bin_idx, j]))))})

    summary = {"session": session, "audit_frames": int(len(cube)), "selected_range_bins": bins, "groups": {}}
    for group, indices in GROUPS.items():
        pairs = [(i, j) for pos, i in enumerate(indices) for j in indices[pos + 1 :]]
        rows = [r for r in pair_corr if r["range_bin"] in bins and r["ch_i"] in {CHANNELS[i] for i, _ in pairs}]
        selected_pairs = {f"{CHANNELS[i]}__{CHANNELS[j]}" for i, j in pairs}
        rows = [r for r in pair_corr if r["pair"] in selected_pairs]
        br = [r["coherence_br_mean"] for r in coh_br if r["pair"] in selected_pairs and np.isfinite(r["coherence_br_mean"])]
        hr = [r["coherence_hr_mean"] for r in coh_hr if r["pair"] in selected_pairs and np.isfinite(r["coherence_hr_mean"])]
        corr = [r["phase_increment_corr"] for r in rows if np.isfinite(r["phase_increment_corr"])]
        rel = [r["relative_phase_circular_sd_rad"] for r in relative if r["pair"] in selected_pairs and np.isfinite(r["relative_phase_circular_sd_rad"])]
        summary["groups"][group] = {"n_pairs": len(pairs), "phase_increment_corr_mean": float(np.mean(corr)) if corr else None, "coherence_br_mean": float(np.mean(br)) if br else None, "coherence_hr_mean": float(np.mean(hr)) if hr else None, "relative_phase_circular_sd_mean_rad": float(np.mean(rel)) if rel else None}
    return pair_corr, coh_br, coh_hr, relative, timestamp, file_rows


def write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    root = Path(r"D:\acq_mmwave_data")
    sessions = ["sub-3_", "sub-4_", "sub-97793_"]
    max_frames = 6000
    all_pair_corr, all_br, all_hr, all_relative, timestamps, file_rows = [], [], [], [], [], []
    summaries = []
    for session in sessions:
        pair_corr, coh_br, coh_hr, relative, timestamp, files = analyze_session(session, root, max_frames)
        all_pair_corr.extend(pair_corr)
        all_br.extend(coh_br)
        all_hr.extend(coh_hr)
        all_relative.extend(relative)
        timestamps.append(timestamp)
        file_rows.extend(files)
        summaries.append({"session": session, "timestamp": timestamp, "selected_range_bins": timestamp["selected_range_bins"], "groups": {}})
    write_csv(OUT / "pairwise_corr.csv", all_pair_corr)
    write_csv(OUT / "pairwise_coherence_br.csv", all_br)
    write_csv(OUT / "pairwise_coherence_hr.csv", all_hr)
    write_csv(OUT / "relative_phase_stability.csv", all_relative)
    write_csv(OUT / "timestamp_quality.csv", timestamps)
    write_csv(OUT / "channel_mapping.csv", [{"channel_index": i, "key": key, "tx": i // 4, "rx": i % 4} for i, key in enumerate(CHANNELS)])
    write_csv(OUT / "file_integrity.csv", file_rows)
    # Recompute compact group summaries from the emitted pairwise tables.
    summary = {"sessions": sessions, "max_frames_per_session": max_frames, "fs_assumed_hz": FS, "bands_hz": {"br": BR_BAND, "hr": HR_BAND}, "channel_order": CHANNELS, "groups": GROUPS, "notes": ["This is a read-only 3-session, 60-second-per-session audit window.", "Coherence is computed on unwrapped slow-time phase; it is not an ECG validation result.", "Range bins are selected by mean complex magnitude power with bins 0-3 excluded and a 3-bin separation heuristic."]}
    with (OUT / "audit_summary.json").open("w", encoding="utf-8") as handle:
        json.dump(summary, handle, ensure_ascii=False, indent=2)
    print(json.dumps({"output": str(OUT), "sessions": sessions, "max_frames": max_frames, "timestamp_rows": {row["session"]: row["timestamp_rows"] for row in timestamps}}, ensure_ascii=False))


if __name__ == "__main__":
    main()
