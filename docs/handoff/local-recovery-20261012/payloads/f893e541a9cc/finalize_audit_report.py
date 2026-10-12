from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats


OUT = Path(__file__).parent
FRAME = pd.read_csv(OUT / "frame_level_comparison.csv")
SUMMARY = pd.read_csv(OUT / "summary_statistics.csv")


def paired(metric: str, data: pd.DataFrame = FRAME) -> dict[str, float | int | None]:
    d = data[[f"a_{metric}", f"b640_{metric}"]].dropna()
    if len(d) < 2:
        return {"n": int(len(d))}
    a = d.iloc[:, 0].to_numpy(float)
    b = d.iloc[:, 1].to_numpy(float)
    diff = b - a
    rel = np.abs(diff) / np.where(np.abs(a) > 0, np.abs(a), np.nan)
    slope = float(np.polyfit(a, b, 1)[0]) if np.ptp(a) > 0 else None
    return {"n": int(len(d)), "mean_bias": float(diff.mean()), "mae": float(np.abs(diff).mean()), "mean_rel_abs_error": float(np.nanmean(rel)), "p95_rel_abs_error": float(np.nanpercentile(rel, 95)), "pearson_r": float(stats.pearsonr(a, b).statistic) if np.ptp(b) > 0 else None, "spearman_rho": float(stats.spearmanr(a, b).statistic) if np.ptp(b) > 0 else None, "slope_b640_on_a": slope, "sd_ratio_b640_over_a": float(np.std(b, ddof=1) / np.std(a, ddof=1)) if np.std(a, ddof=1) > 0 else None}


def fit_rate(method: str, geom: str, data: pd.DataFrame = FRAME) -> float:
    return float(data[f"{method}_{geom}_fit_valid"].mean())


pir_all = paired("pupil_to_iris_diameter_ratio")
area_all = paired("pupil_ellipse_area")
axis_a = paired("pupil_axis_a")
axis_b = paired("pupil_axis_b")
geom_d = paired("pupil_geom_mean_diameter")

groups = ["pupil_size_Q1_small", "pupil_size_Q2_Q3_mid", "pupil_size_Q4_large"]
size_rows = []
for g in groups:
    d = FRAME[FRAME.pupil_size_stratum == g]
    x = paired("pupil_to_iris_diameter_ratio", d)
    x["group"] = g
    x["n_frames"] = len(d)
    size_rows.append(x)

edge_rows = []
for g in ["edge_frame", "non_edge_frame"]:
    d = FRAME[FRAME.edge_stratum == g]
    x = paired("pupil_to_iris_diameter_ratio", d)
    x["group"] = g
    x["n_frames"] = len(d)
    edge_rows.append(x)

source_rows = []
for g in ["source_roi_clipped", "source_roi_not_clipped"]:
    d = FRAME[FRAME.source_gate_stratum == g]
    x = paired("pupil_to_iris_diameter_ratio", d)
    x["group"] = g
    x["n_frames"] = len(d)
    source_rows.append(x)

verdict = "FAIL" if (pir_all.get("pearson_r", 0) or 0) < 0.98 or (pir_all.get("mean_rel_abs_error", 1) or 1) >= 0.03 else ("CAUTION" if (pir_all.get("pearson_r", 0) or 0) < 0.995 or (pir_all.get("mean_rel_abs_error", 1) or 1) >= 0.01 else "PASS")
report = f"""# NIR 640×400 vs 320×160 几何敏感性审计

## 结论

**{verdict}：不建议直接把现有 320×160 几何当作 640×400 几何的等价替代；建议先对全量已保存的 640×400 label 做 640×400 几何重算。** 这不需要重新跑 YOLO 或 RITnet。是否重跑 44 人的模型推理不是本审计的必要步骤，只有在 640×400 label 未覆盖全量帧时才需要考虑。

本审计使用 5,347/5,347 张 sparse QC 彩色 label，全部成功解码，错误 0。A 为原生 640×400；B 为当前正式 `INTER_NEAREST` 缩放到 320×160 后的同一几何函数；`B640` 是将 B 的坐标、轴和面积映射回原生坐标后的可比结果。PIR 按当前 runtime 定义为 pupil/iris 几何平均直径比。

判定规则是审计预注册式工程门槛：PASS：PIR Pearson ≥ .995 且平均相对绝对误差 <1%；CAUTION：Pearson ≥ .98 且误差 <3%；否则 FAIL。该规则不是外部真值验证。

## 主要结果

| 指标 | 配对 n | B640−A 平均偏差 | MAE | 平均相对绝对误差 | Pearson | Spearman | B640/A 斜率 | SD 比 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| pupil center x | {paired('pupil_center_x')['n']} | {paired('pupil_center_x')['mean_bias']:.4f} | {paired('pupil_center_x')['mae']:.4f} | {paired('pupil_center_x')['mean_rel_abs_error']:.4%} | {paired('pupil_center_x')['pearson_r']:.4f} | {paired('pupil_center_x')['spearman_rho']:.4f} | {paired('pupil_center_x')['slope_b640_on_a']:.4f} | {paired('pupil_center_x')['sd_ratio_b640_over_a']:.4f} |
| pupil center y | {paired('pupil_center_y')['n']} | {paired('pupil_center_y')['mean_bias']:.4f} | {paired('pupil_center_y')['mae']:.4f} | {paired('pupil_center_y')['mean_rel_abs_error']:.4%} | {paired('pupil_center_y')['pearson_r']:.4f} | {paired('pupil_center_y')['spearman_rho']:.4f} | {paired('pupil_center_y')['slope_b640_on_a']:.4f} | {paired('pupil_center_y')['sd_ratio_b640_over_a']:.4f} |
| pupil axis a | {axis_a['n']} | {axis_a['mean_bias']:.4f} | {axis_a['mae']:.4f} | {axis_a['mean_rel_abs_error']:.4%} | {axis_a['pearson_r']:.4f} | {axis_a['spearman_rho']:.4f} | {axis_a['slope_b640_on_a']:.4f} | {axis_a['sd_ratio_b640_over_a']:.4f} |
| pupil axis b | {axis_b['n']} | {axis_b['mean_bias']:.4f} | {axis_b['mae']:.4f} | {axis_b['mean_rel_abs_error']:.4%} | {axis_b['pearson_r']:.4f} | {axis_b['spearman_rho']:.4f} | {axis_b['slope_b640_on_a']:.4f} | {axis_b['sd_ratio_b640_over_a']:.4f} |
| pupil ellipse area | {area_all['n']} | {area_all['mean_bias']:.4f} | {area_all['mae']:.4f} | {area_all['mean_rel_abs_error']:.4%} | {area_all['pearson_r']:.4f} | {area_all['spearman_rho']:.4f} | {area_all['slope_b640_on_a']:.4f} | {area_all['sd_ratio_b640_over_a']:.4f} |
| PIR diameter ratio | {pir_all['n']} | {pir_all['mean_bias']:.6f} | {pir_all['mae']:.6f} | {pir_all['mean_rel_abs_error']:.4%} | {pir_all['pearson_r']:.4f} | {pir_all['spearman_rho']:.4f} | {pir_all['slope_b640_on_a']:.4f} | {pir_all['sd_ratio_b640_over_a']:.4f} |

## 三个重点判断

1. **不是单纯尺度变化。** 映射回 640×400 后，中心位置误差较小，但 pupil axis a 平均相对误差约 {axis_a['mean_rel_abs_error']:.2%}，axis b 约 {axis_b['mean_rel_abs_error']:.2%}，pupil ellipse area 约 {area_all['mean_rel_abs_error']:.2%}；说明轮廓量化和最大轮廓/椭圆拟合本身发生了改变。
2. **对细微帧间变化存在压平风险。** pupil 几何平均直径的 B640/A 斜率为 {geom_d['slope_b640_on_a']:.4f}、SD 比为 {geom_d['sd_ratio_b640_over_a']:.4f}；这表示尺寸动态被明显压缩。PIR 的 SD 比为 {pir_all['sd_ratio_b640_over_a']:.4f}，不能仅用整体相关替代动态等价性。
3. **小瞳孔和 edge-gate 帧更敏感。** 小瞳孔 Q1 的 PIR 平均相对绝对误差为 {size_rows[0]['mean_rel_abs_error']:.2%}，Pearson={size_rows[0]['pearson_r']:.4f}；中间层为 {size_rows[1]['mean_rel_abs_error']:.2%}，Pearson={size_rows[1]['pearson_r']:.4f}；大瞳孔 Q4 为 {size_rows[2]['mean_rel_abs_error']:.2%}，Pearson={size_rows[2]['pearson_r']:.4f}。按几何或 QC 任一边缘定义的 edge-frame 误差为 {edge_rows[0]['mean_rel_abs_error']:.2%}，非 edge-frame 为 {edge_rows[1]['mean_rel_abs_error']:.2%}；这个合并 edge 分层并未显示 edge 更差，不能据此声称边缘效应更强。更直接的源 gate `roi_clipped` 分层中，clipped 误差为 {source_rows[0]['mean_rel_abs_error']:.2%}（n={source_rows[0]['n']}），未 clipped 为 {source_rows[1]['mean_rel_abs_error']:.2%}（n={source_rows[1]['n']}），提示 ROI 裁剪帧存在小幅系统风险。

## 有效拟合率

| 方法 | pupil fit | iris_outer fit |
|---|---:|---:|
| A，640×400 | {fit_rate('a','pupil'):.2%} | {fit_rate('a','iris_outer'):.2%} |
| B，320×160 | {fit_rate('b_raw','pupil'):.2%} | {fit_rate('b_raw','iris_outer'):.2%} |

B 相比 A 的有效拟合率下降约 {(fit_rate('a','pupil')-fit_rate('b_raw','pupil')):.2%} 个百分点（pupil），iris_outer 下降约 {(fit_rate('a','iris_outer')-fit_rate('b_raw','iris_outer')):.2%} 个百分点。

## 产物与限制

- 帧级对照：[frame_level_comparison.csv](frame_level_comparison.csv)
- 汇总统计：[summary_statistics.csv](summary_statistics.csv)
- 审计清单与 runtime 哈希：[audit_manifest.json](audit_manifest.json)
- 可复现脚本：[audit_nir_resolution_sensitivity.py](audit_nir_resolution_sensitivity.py)
- 输入是 sparse QC，不是全量帧；因此本结果证明 QC 样本上的分辨率敏感性，不能直接宣称 44 人全量帧的效应完全相同。
- QC 图是按 runtime 调色板保存的彩色 label，审计已按 BGR 调色板无损恢复四类，而不是把 RGB 强度当类别编号。
- 当前 audit 只涉及几何后处理，没有重跑 YOLO/RITnet，没有覆盖正式 CSV/QC，也没有修改正式 runtime。
"""
(OUT / "audit_report.md").write_text(report, encoding="utf-8")
print(json.dumps({"verdict": verdict, "pir": pir_all, "pupil_geom": geom_d, "size": size_rows, "edge": edge_rows}, ensure_ascii=False, indent=2))
