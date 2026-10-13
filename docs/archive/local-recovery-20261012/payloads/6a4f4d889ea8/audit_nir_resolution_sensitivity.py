from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

import cv2
import numpy as np
from scipy import stats


RUNTIME = Path(r"D:\Project\厚粲杯\08_算法\01_Attention-Analysis_nvidia-cuda\runtime\nir-formal")
DEFAULT_INPUT = Path(r"D:\Project\厚粲杯\11_数据\01_Attention-Analysis_nvidia-cuda_formal_NIR")
DEFAULT_OUTPUT = Path(r"D:\Project\厚粲杯\08_算法\work\nir_resolution_sensitivity_audit_2026-08-27")
PALETTE_TO_CLASS = {(0, 0, 0): 0, (255, 0, 0): 1, (0, 255, 0): 2, (0, 0, 255): 3}
GEOM_METRICS = ["center_x", "center_y", "axis_a", "axis_b", "short_axis", "long_axis", "ellipse_area", "contour_area", "geom_mean_diameter"]
METRICS = [
    "pupil_center_x", "pupil_center_y", "pupil_axis_a", "pupil_axis_b", "pupil_short_axis", "pupil_long_axis", "pupil_ellipse_area", "pupil_contour_area", "pupil_geom_mean_diameter",
    "iris_outer_center_x", "iris_outer_center_y", "iris_outer_axis_a", "iris_outer_axis_b", "iris_outer_short_axis", "iris_outer_long_axis", "iris_outer_ellipse_area", "iris_outer_contour_area", "iris_outer_geom_mean_diameter",
    "pupil_to_iris_diameter_ratio", "pupil_to_iris_ellipse_area_ratio", "pupil_pixels", "iris_outer_pixels",
]


def load_runtime():
    sys.path.insert(0, str(RUNTIME))
    from ritnet_fullclass_metrics import summarize_fullclass
    from ritnet_fullclass_contract import QC_PALETTE_BGR
    return summarize_fullclass, QC_PALETTE_BGR


def read_label(path: Path) -> tuple[np.ndarray, int]:
    raw = np.fromfile(path, dtype=np.uint8)
    image = cv2.imdecode(raw, cv2.IMREAD_COLOR)
    if image is None or image.ndim != 3 or image.shape[2] != 3:
        raise ValueError(f"cannot decode color PNG: {path}")
    out = np.full(image.shape[:2], 255, dtype=np.uint8)
    for color, class_id in PALETTE_TO_CLASS.items():
        out[np.all(image == np.asarray(color, dtype=np.uint8), axis=2)] = class_id
    unknown = int(np.sum(out == 255))
    if unknown:
        raise ValueError(f"unknown palette pixels={unknown}: {path}")
    return out, int(image.shape[1] * image.shape[0])


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def f(value: Any) -> float | None:
    try:
        if value in (None, ""):
            return None
        value = float(value)
        return value if math.isfinite(value) else None
    except (TypeError, ValueError):
        return None


def b(value: Any) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def get_qc_rows(input_root: Path) -> tuple[list[Path], dict[str, dict[str, str]], list[dict[str, Any]]]:
    files = sorted(input_root.rglob("*_labels.png"))
    rows: dict[str, dict[str, str]] = {}
    inventories = []
    for run_dir in sorted({p.parent.parent for p in files}):
        index_files = sorted(run_dir.glob("*_qc_index.csv"))
        if not index_files:
            continue
        index = index_files[0]
        run_files = sorted(run_dir.rglob("*_labels.png"))
        with index.open("r", encoding="utf-8-sig", newline="") as fh:
            for row in csv.DictReader(fh):
                label = row.get("labels_file", "")
                if label:
                    rows[str(run_dir / label)] = row
        inventories.append({"run_dir": str(run_dir), "qc_index": str(index), "n_labels": len(run_files)})
    return files, rows, inventories


def safe_name(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", value)


def enrich(result: dict[str, Any], prefix: str, scale_x: float, scale_y: float) -> dict[str, Any]:
    out = {}
    for geom in ("pupil", "iris_outer"):
        for metric in GEOM_METRICS:
            key = f"{prefix}_{geom}_{metric}"
            value = result.get(f"{geom}_{metric}")
            if value is None:
                out[key] = None
            elif metric == "center_x":
                out[key] = float(value) * scale_x
            elif metric == "center_y":
                out[key] = float(value) * scale_y
            elif metric in {"axis_a", "axis_b", "short_axis", "long_axis"}:
                out[key] = float(value) * scale_x
            elif metric in {"ellipse_area", "contour_area"}:
                out[key] = float(value) * scale_x * scale_y
            else:
                out[key] = float(value)
        out[f"{prefix}_{geom}_fit_valid"] = bool(result.get(f"{geom}_fit_valid"))
        out[f"{prefix}_{geom}_edge"] = bool(result.get(f"{geom}_touches_roi_edge"))
    for metric in ("pupil_to_iris_diameter_ratio", "pupil_to_iris_ellipse_area_ratio", "pupil_to_iris_contour_area_ratio", "pupil_pixels", "iris_outer_pixels"):
        value = result.get(metric)
        out[f"{prefix}_{metric}"] = None if value is None else float(value) * (scale_x * scale_y if metric in {"pupil_pixels", "iris_outer_pixels"} else 1.0)
    out[f"{prefix}_normalization_valid"] = bool(result.get("normalization_valid"))
    return out


def quantile_bin(value: float | None, q1: float, q2: float) -> str:
    if value is None:
        return "missing"
    if value <= q1:
        return "pupil_size_Q1_small"
    if value <= q2:
        return "pupil_size_Q2_Q3_mid"
    return "pupil_size_Q4_large"


def paired_stats(rows: list[dict[str, Any]], metric: str, group: str) -> dict[str, Any]:
    pairs = [(f(r.get(f"a_{metric}")), f(r.get(f"b640_{metric}"))) for r in rows if f(r.get(f"a_{metric}")) is not None and f(r.get(f"b640_{metric}")) is not None]
    if not pairs:
        return {"group": group, "metric": metric, "n": 0}
    a = np.asarray([x[0] for x in pairs], dtype=float)
    z = np.asarray([x[1] for x in pairs], dtype=float)
    diff = z - a
    denom = np.abs(a)
    rel = np.where(denom > 0, np.abs(diff) / denom, np.nan)
    result: dict[str, Any] = {
        "group": group, "metric": metric, "n": int(len(a)),
        "mean_a": float(np.mean(a)), "mean_b640": float(np.mean(z)),
        "mean_signed_bias_b640_minus_a": float(np.mean(diff)),
        "median_signed_bias_b640_minus_a": float(np.median(diff)),
        "sd_signed_bias": float(np.std(diff, ddof=1)) if len(diff) > 1 else None,
        "mae": float(np.mean(np.abs(diff))),
        "median_ae": float(np.median(np.abs(diff))),
        "mean_relative_abs_error": float(np.nanmean(rel)) if np.isfinite(rel).any() else None,
        "p95_relative_abs_error": float(np.nanpercentile(rel, 95)) if np.isfinite(rel).any() else None,
        "pearson_r": None, "spearman_rho": None,
    }
    if len(a) >= 2 and np.ptp(a) > 0 and np.ptp(z) > 0:
        result["pearson_r"] = float(stats.pearsonr(a, z).statistic)
        result["spearman_rho"] = float(stats.spearmanr(a, z).statistic)
    return result


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = ap.parse_args()
    out = args.output
    out.mkdir(parents=True, exist_ok=True)
    summarize_fullclass, palette = load_runtime()
    files, qc_rows, inventories = get_qc_rows(args.input)
    frame_rows: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []
    for idx, path in enumerate(files, 1):
        run_dir = path.parent.parent
        meta = qc_rows.get(str(path), {})
        base = {"source_label_path": str(path), "subject": meta.get("subject", run_dir.name.split("_")[0]), "phase": meta.get("phase"), "phase_segment": meta.get("phase_segment"), "frame_idx": meta.get("frame_idx"), "eye": meta.get("eye"), "reason": meta.get("reason"), "roi_clipped": b(meta.get("roi_clipped")), "source_normalization_valid": b(meta.get("normalization_valid"))}
        try:
            labels, native_pixels = read_label(path)
            a = summarize_fullclass(labels, None, (640, 400))
            bb = summarize_fullclass(labels, None, (320, 160))
            row = dict(base)
            row.update(enrich(a, "a", 1.0, 1.0))
            row.update(enrich(bb, "b_raw", 1.0, 1.0))
            # B is the formal 320x160 coordinate system; map it back to native coordinates.
            for metric in METRICS:
                value = row.get(f"b_raw_{metric}")
                if value is None:
                    row[f"b640_{metric}"] = None
                elif metric.endswith("_center_x") or metric.endswith("_axis_a") or metric.endswith("_axis_b") or metric.endswith("_short_axis") or metric.endswith("_long_axis"):
                    row[f"b640_{metric}"] = float(value) * 2.0
                elif metric.endswith("_center_y"):
                    row[f"b640_{metric}"] = float(value) * 2.5
                elif metric.endswith("_ellipse_area") or metric.endswith("_contour_area") or metric in {"pupil_pixels", "iris_outer_pixels"}:
                    row[f"b640_{metric}"] = float(value) * 5.0
                elif metric.endswith("_geom_mean_diameter"):
                    row[f"b640_{metric}"] = float(value) * math.sqrt(5.0)
                else:
                    row[f"b640_{metric}"] = float(value)
            row["native_width"] = 640
            row["native_height"] = 400
            row["b_width"] = 320
            row["b_height"] = 160
            row["edge_frame"] = bool(row["roi_clipped"] or "roi_clipped" in str(row["reason"]).lower() or row["a_pupil_edge"] or row["a_iris_outer_edge"] or row["b_raw_pupil_edge"] or row["b_raw_iris_outer_edge"])
            row["native_palette_pixels"] = native_pixels
            frame_rows.append(row)
        except Exception as exc:
            errors.append({"path": str(path), "error": repr(exc)})
    if not frame_rows:
        raise RuntimeError("No frame rows were produced")
    # Pupil-size strata are defined from A native geom-mean diameter, without using B.
    vals = np.asarray([f(r.get("a_pupil_geom_mean_diameter")) for r in frame_rows if f(r.get("a_pupil_geom_mean_diameter")) is not None], dtype=float)
    q1, q2 = np.quantile(vals, [1 / 3, 2 / 3]) if len(vals) else (float("nan"), float("nan"))
    for row in frame_rows:
        row["pupil_size_stratum"] = quantile_bin(f(row.get("a_pupil_geom_mean_diameter")), float(q1), float(q2))
        row["edge_stratum"] = "edge_frame" if row["edge_frame"] else "non_edge_frame"
        row["source_gate_stratum"] = "source_roi_clipped" if row["roi_clipped"] else "source_roi_not_clipped"
    frame_path = out / "frame_level_comparison.csv"
    fields = list(frame_rows[0])
    with frame_path.open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        writer.writeheader(); writer.writerows(frame_rows)
    groups = {"all": frame_rows}
    for key in ("pupil_size_stratum", "edge_stratum", "source_gate_stratum"):
        for value in sorted({str(r[key]) for r in frame_rows}):
            groups[f"{key}={value}"] = [r for r in frame_rows if str(r[key]) == value]
    summary_rows = []
    for group, rows in groups.items():
        for metric in METRICS:
            summary_rows.append(paired_stats(rows, metric, group))
        for method in ("a", "b_raw"):
            for geom in ("pupil", "iris_outer"):
                summary_rows.append({"group": group, "metric": f"{method}_{geom}_fit_rate", "n": len(rows), "fit_rate": float(np.mean([bool(r[f"{method}_{geom}_fit_valid"]) for r in rows]))})
    summary_path = out / "summary_statistics.csv"
    fields2 = sorted({k for r in summary_rows for k in r})
    with summary_path.open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields2); writer.writeheader(); writer.writerows(summary_rows)
    manifest = {
        "status": "complete" if not errors else "partial",
        "input_root": str(args.input), "output_root": str(out), "n_labels_found": len(files), "n_frames_audited": len(frame_rows), "n_errors": len(errors),
        "errors": errors, "inventories": inventories, "native_expected_shape": [400, 640], "formal_expected_shape": [160, 320],
        "palette_bgr_to_class": {str(k): v for k, v in PALETTE_TO_CLASS.items()}, "pupil_size_cutpoints_native_geom_mean_diameter": [float(q1), float(q2)],
        "pir_definition": "pupil_to_iris_diameter_ratio = sqrt(pupil_axis_a*pupil_axis_b)/sqrt(iris_axis_a*iris_axis_b), matching RITNET_FULLCLASS_EXTENSION.md",
        "comparison": "A native 640x400; B summarize_fullclass(labels, analysis_size=(320,160)); b640 maps B geometry back by x=2, y=2.5, area=5",
        "runtime_files": {name: {"path": str(RUNTIME / name), "sha256": sha256(RUNTIME / name)} for name in ["ritnet_runtime.py", "ritnet_fullclass_metrics.py", "ritnet_fullclass_contract.py"]},
    }
    (out / "audit_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    if errors:
        (out / "errors.json").write_text(json.dumps(errors, ensure_ascii=False, indent=2), encoding="utf-8")
    # Compact report with decisions based on pre-declared practical thresholds.
    pir = [r for r in summary_rows if r["group"] == "all" and r["metric"] == "pupil_to_iris_diameter_ratio"]
    p = pir[0] if pir else {}
    report = ["# NIR 640x400 vs 320x160 sensitivity audit", "", f"- Input labels found: {len(files)}; audited: {len(frame_rows)}; errors: {len(errors)}", f"- A: native 640x400; B: current formal INTER_NEAREST resize to 320x160; B640: B geometry mapped back to native coordinates.", f"- Pupil size cutpoints (A geom-mean diameter): {q1:.4f}, {q2:.4f}.", "", "## Primary PIR result", "", f"- PIR pairs: n={p.get('n')}; Pearson r={p.get('pearson_r')}; Spearman rho={p.get('spearman_rho')}; MAE={p.get('mae')}; mean signed bias (B640-A)={p.get('mean_signed_bias_b640_minus_a')}; mean relative absolute error={p.get('mean_relative_abs_error')}.", "", "## Decision", "", "Decision thresholds used for this audit: PASS if primary PIR r >= .995 and mean relative absolute error < 1%; CAUTION if r >= .98 and mean relative absolute error < 3%; otherwise FAIL. These are audit decision rules, not validation against an external ground truth."]
    (out / "audit_report.md").write_text("\n".join(report) + "\n", encoding="utf-8")
    print(json.dumps({"labels_found": len(files), "audited": len(frame_rows), "errors": len(errors), "output": str(out)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
