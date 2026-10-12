#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
run_mmwave_probe_criterion_models_20260831.py
版本：v1 (2026-08-31)
功能：毫米波特征与思维探针（Q1/Q2）及窗口行为结局的统计关联分析。
      支撑正式报告 5.4.3「毫米波特征与行为及思维探针的关系」。
      只读取已冻结的 merge-ready 表与 Behavior formal_v3 探针表，不读取原始雷达数据、
      不重跑 producer 信号链、不修改任何源表。
用法：python run_mmwave_probe_criterion_models_20260831.py
依赖：pandas、numpy、statsmodels>=0.14
输出：见 OUT_DIR（默认 11_数据/_FormalAnalysis/mmWave/mmwave_probe_criterion_models_20260831/）
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm

# ---------------------------------------------------------------------------
# 路径与参数集中声明
# ---------------------------------------------------------------------------
# 输入表（只读）
MW_J_TABLE = Path(r"D:\Project\厚粲杯\11_数据\_FormalAnalysis\mmWave\mmwave_probe_merge_ready.csv")          # J 盘 72 场 / 1440 窗
MW_E_TABLE = Path(r"D:\Project\厚粲杯\11_数据\_FormalAnalysis\mmWave\mmwave_probe_merge_ready_E.csv")        # E 盘 44 场 / 880 窗
BEHAVIOR_PROBE = Path(r"D:\Project\厚粲杯\11_数据\_FormalAnalysis\Behavior\formal_v3\probe_primary_30s.csv")  # 行为权威探针表（Q1/Q2 标签与正式身份）

# 输出目录（仓库外，行级结果不进入 Git）
OUT_DIR = Path(r"D:\Project\厚粲杯\11_数据\_FormalAnalysis\mmWave\mmwave_probe_criterion_models_20260831")

# 主预测变量（预先声明，SUPPORTING 层 + 运动代理；不按结果筛选）
# feature_layer 语义：
#   supporting_physiology : 心搏/呼吸估计（NOT_PRIMARY，作 supporting 特征）
#   motion_proxy          : 毫米波自身运动代理（体动敏感性核心对象）
PRIMARY_FEATURES: list[tuple[str, str]] = [
    ("mmwave_hr_fused_bpm_median", "supporting_physiology"),
    ("mmwave_hr_freq_bpm_median", "supporting_physiology"),
    ("mmwave_hr_time_bpm_median", "supporting_physiology"),
    ("mmwave_breath_rate_breaths_per_min_median", "supporting_physiology"),
    ("mmwave_motion_proxy_median", "motion_proxy"),
]

# 补充特征（质量/稳定性，作为敏感性特征单独报告，不并入主解释）
AUX_FEATURES: list[tuple[str, str]] = [
    ("mmwave_phase_stability_median", "quality_stability"),
    ("mmwave_hr_mean_confidence", "quality_confidence"),
    ("mmwave_timestamp_coverage_fraction", "quality_coverage"),
]

# 窗口行为结局（来自 Behavior formal_v3，覆盖速度、遗漏、误按、辨别力四个层面）
BEHAVIOR_OUTCOMES: list[str] = [
    "go_correct_rt_median_ms",
    "raw_go_omission_rate",
    "clean_go_omission_rate",
    "commission_rate",
    "dprime_loglinear",
]

# Q1 多项 logistic：类别 1 为参照类别；Q1 必须同时出现 1-4 四类
Q1_REFERENCE_CATEGORY = 1
# Q2 有序 GEE：至少出现三个有序等级
Q2_MIN_LEVELS = 3
# 模型最小样本门（行数与参与者组数）
MIN_MODEL_ROWS = 100
MIN_PARTICIPANT_GROUPS = 30
# 高体动排除敏感性：排除运动代理高于全样本该分位的窗口（固定准则，不调参）
HIGH_MOTION_EXCLUDE_QUANTILE = 0.90
# 置信区间用 1.96 * SE（与行为 science-v3 一致）
CI_Z = 1.96
# 随机种子（重采样类方法预留，本轮模型无重采样）
SEED = 20260831


# ---------------------------------------------------------------------------
# 数据装载与连接
# ---------------------------------------------------------------------------
def load_analysis_frame() -> pd.DataFrame:
    """装载毫米波 merge-ready 表与行为探针表，按 session+block+probe 序号一对一连接。

    返回：2320 行的宽表；身份采用行为表的 participant_group_id（权威），
    毫米波表只贡献 mmwave_* 特征列。
    """
    mw_j = pd.read_csv(MW_J_TABLE, encoding="utf-8-sig", low_memory=False)
    mw_e = pd.read_csv(MW_E_TABLE, encoding="utf-8-sig", low_memory=False)
    behavior = pd.read_csv(BEHAVIOR_PROBE, encoding="utf-8-sig", low_memory=False)

    # 连接键归一：毫米波 block-1/block-2 -> B1/B2；probe-01 -> 1
    mw = pd.concat([mw_j, mw_e], ignore_index=True)
    mw["_block_key"] = mw["block_id"].astype(str).str.replace("block-", "B", regex=False)
    mw["_probe_num"] = mw["probe_id"].astype(str).str.extract(r"probe-(\d+)").astype(int)
    behavior = behavior.copy()
    behavior["_probe_num"] = behavior["probe_event_id"].astype(str).str.extract(r"probe\|(\d+)$").astype(int)

    # 一对一连接；行为表提供 Q1/Q2 标签与正式身份键
    keep_be = ["session_id", "block_id", "_probe_num", "q1_nominal_4class", "q2_ordinal_4level",
               "participant_group_id", *BEHAVIOR_OUTCOMES]
    frame = mw.merge(behavior[keep_be],
                     left_on=["session_id", "_block_key", "_probe_num"],
                     right_on=["session_id", "block_id", "_probe_num"],
                     how="inner", suffixes=("", "_be"), validate="one_to_one")
    if len(frame) != 2320:
        raise RuntimeError(f"连接行数异常：期望 2320，实际 {len(frame)}")
    return frame


def _z_standardize(series: pd.Series) -> pd.Series:
    """总体 z 标准化（ddof=0），与行为 science-v3 的预测变量标准化一致。"""
    x = pd.to_numeric(series, errors="coerce")
    scale = float(x.std(ddof=0))
    if not np.isfinite(scale) or scale <= 0:
        return pd.Series(np.nan, index=x.index, dtype=float)
    return (x - float(x.mean())) / scale


def _model_gate(fit) -> str | None:
    """拟合结果门：收敛且参数/SE 全部有限才放行，否则返回失败原因。"""
    if fit is None:
        return "empty result"
    if getattr(fit, "converged", True) is False:
        return "model did not converge"
    try:
        params = np.asarray(fit.params, dtype=float)
        bse = np.asarray(fit.bse, dtype=float)
    except Exception as exc:
        return f"invalid result arrays: {type(exc).__name__}: {exc}"
    if params.size == 0 or not np.isfinite(params).all() or not np.isfinite(bse).all():
        return "non-finite or empty parameter/SE table"
    return None


# ---------------------------------------------------------------------------
# 模型族
# ---------------------------------------------------------------------------
def fit_q1_model(d: pd.DataFrame, predictor: str) -> tuple[list[dict], dict | None]:
    """Q1 四分类名义因变量的多项 logistic 回归（参与者聚类稳健协方差）。

    参数：d 至少含 q1_nominal_4class、predictor、participant_group_id、session_id。
    返回：(结果行列表, 失败记录或 None)。
    """
    work = d[["q1_nominal_4class", predictor, "participant_group_id", "session_id"]].copy()
    work["q1_nominal_4class"] = pd.to_numeric(work["q1_nominal_4class"], errors="coerce")
    work[predictor] = pd.to_numeric(work[predictor], errors="coerce")
    work = work.dropna()
    levels = sorted(set(work["q1_nominal_4class"].astype(int)))
    if len(work) < MIN_MODEL_ROWS or work["participant_group_id"].nunique() < MIN_PARTICIPANT_GROUPS:
        return [], {"reason": "insufficient rows or participant groups"}
    if set(levels) != {1, 2, 3, 4}:
        return [], {"reason": f"Q1 requires categories 1-4, observed {levels}"}
    ordered = [Q1_REFERENCE_CATEGORY] + [x for x in levels if x != Q1_REFERENCE_CATEGORY]
    mapping = {level: idx for idx, level in enumerate(ordered)}
    y = work["q1_nominal_4class"].astype(int).map(mapping).astype(int)
    x = work[[predictor]].astype(float)
    x[predictor] = _z_standardize(work[predictor])
    x = sm.add_constant(x, has_constant="add")
    try:
        model = sm.MNLogit(y, x)
        fit = model.fit(method="newton", maxiter=300, disp=False, cov_type="cluster",
                        cov_kwds={"groups": work["participant_group_id"].astype(str)})
    except Exception as exc:
        return [], {"reason": f"{type(exc).__name__}: {exc}"}
    reason = _model_gate(fit)
    if reason:
        return [], {"reason": reason}
    params = pd.DataFrame(fit.params)
    bse = pd.DataFrame(fit.bse)
    rows = []
    for equation_index, category in enumerate(ordered[1:]):
        if equation_index not in params.columns:
            continue
        estimate = float(params.loc[predictor, equation_index])
        se = float(bse.loc[predictor, equation_index])
        rows.append({"contrast_category": int(category), "reference_category": Q1_REFERENCE_CATEGORY,
                     "estimate_per_predictor_sd": estimate, "se": se,
                     "ci_low": estimate - CI_Z * se, "ci_high": estimate + CI_Z * se})
    return rows, None


def fit_q2_model(d: pd.DataFrame, predictor: str) -> tuple[dict | None, dict | None]:
    """Q2 四级有序因变量的有序 GEE（参与者聚类，GlobalOddsRatio ordinal）。

    返回：(结果行或 None, 失败记录或 None)。
    """
    work = d[["q2_ordinal_4level", predictor, "participant_group_id", "session_id"]].copy()
    work["q2_ordinal_4level"] = pd.to_numeric(work["q2_ordinal_4level"], errors="coerce")
    work[predictor] = pd.to_numeric(work[predictor], errors="coerce")
    work = work.dropna()
    if len(work) < MIN_MODEL_ROWS or work["participant_group_id"].nunique() < MIN_PARTICIPANT_GROUPS:
        return None, {"reason": "insufficient rows or participant groups"}
    if not set(work["q2_ordinal_4level"].astype(int).unique()).issubset({1, 2, 3, 4}) \
            or work["q2_ordinal_4level"].nunique() < Q2_MIN_LEVELS:
        return None, {"reason": "Q2 requires at least three ordered levels within 1-4"}
    x = work[[predictor]].astype(float)
    x[predictor] = _z_standardize(work[predictor])
    try:
        gor = sm.cov_struct.GlobalOddsRatio("ordinal")
        model = sm.OrdinalGEE(work["q2_ordinal_4level"].astype(int), x,
                              work["participant_group_id"].astype(str), cov_struct=gor)
        fit = model.fit(maxiter=100)
    except Exception as exc:
        return None, {"reason": f"{type(exc).__name__}: {exc}"}
    reason = _model_gate(fit)
    if reason:
        return None, {"reason": reason}
    estimate = float(pd.Series(fit.params)[predictor])
    se = float(pd.Series(fit.bse)[predictor])
    return {"estimate_per_predictor_sd": estimate, "se": se,
            "ci_low": estimate - CI_Z * se, "ci_high": estimate + CI_Z * se}, None


def fit_gaussian_gee(d: pd.DataFrame, outcome: str, predictors: list[str]) -> tuple[dict | None, dict | None]:
    """连续窗口结局的高斯 GEE（参与者聚类，exchangeable 相关结构）。

    参数：predictors 为已 z 标准化的预测变量列名列表。
    返回：(各预测变量结果行 dict 列表或 None, 失败记录或 None)。
    """
    work = d[[outcome, "participant_group_id", *predictors]].copy()
    work[outcome] = pd.to_numeric(work[outcome], errors="coerce")
    for p in predictors:
        work[p] = pd.to_numeric(work[p], errors="coerce")
    work = work.dropna()
    if len(work) < MIN_MODEL_ROWS or work["participant_group_id"].nunique() < MIN_PARTICIPANT_GROUPS:
        return None, {"reason": "insufficient rows or participant groups"}
    x = sm.add_constant(work[predictors].astype(float), has_constant="add")
    try:
        model = sm.GEE(work[outcome].astype(float), x, work["participant_group_id"].astype(str),
                       family=sm.families.Gaussian(), cov_struct=sm.cov_struct.Exchangeable())
        fit = model.fit(maxiter=100)
    except Exception as exc:
        return None, {"reason": f"{type(exc).__name__}: {exc}"}
    reason = _model_gate(fit)
    if reason:
        return None, {"reason": reason}
    rows = []
    for p in predictors:
        estimate = float(pd.Series(fit.params)[p])
        se = float(pd.Series(fit.bse)[p])
        rows.append({"estimate_per_predictor_sd": estimate, "se": se,
                     "ci_low": estimate - CI_Z * se, "ci_high": estimate + CI_Z * se})
    return rows, None


def fit_q2_multi(d: pd.DataFrame) -> tuple[list[dict] | None, dict | None]:
    """Q2 有序 GEE 的多预测变量版本（用于 between/within 同时进入）。"""
    work = d[["q2_ordinal_4level", "participant_group_id", "_between_z", "_within_z"]].copy()
    work["q2_ordinal_4level"] = pd.to_numeric(work["q2_ordinal_4level"], errors="coerce")
    work = work.dropna()
    if len(work) < MIN_MODEL_ROWS or work["participant_group_id"].nunique() < MIN_PARTICIPANT_GROUPS:
        return None, {"reason": "insufficient rows or participant groups"}
    x = work[["_between_z", "_within_z"]].astype(float)
    try:
        gor = sm.cov_struct.GlobalOddsRatio("ordinal")
        model = sm.OrdinalGEE(work["q2_ordinal_4level"].astype(int), x,
                              work["participant_group_id"].astype(str), cov_struct=gor)
        fit = model.fit(maxiter=100)
    except Exception as exc:
        return None, {"reason": f"{type(exc).__name__}: {exc}"}
    reason = _model_gate(fit)
    if reason:
        return None, {"reason": reason}
    rows = []
    for p in ["_between_z", "_within_z"]:
        estimate = float(pd.Series(fit.params)[p])
        se = float(pd.Series(fit.bse)[p])
        term = "between" if p == "_between_z" else "within"
        rows.append({"outcome": "q2_ordinal_4level", "term": term,
                     "estimate_per_predictor_sd": estimate, "se": se,
                     "ci_low": estimate - CI_Z * se, "ci_high": estimate + CI_Z * se})
    return rows, None


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------
def main() -> None:
    frame = load_analysis_frame()
    observed = frame[frame["mmwave_state"] == "OBSERVED"].copy()
    missing_sessions = sorted(frame.loc[frame["mmwave_state"] != "OBSERVED", "session_id"].unique())

    # ---- 描述统计（场次级）----
    desc_rows = []
    for feat, layer in [*PRIMARY_FEATURES, *AUX_FEATURES]:
        sess = observed.groupby("session_id")[feat].median().dropna()
        desc_rows.append({"feature": feat, "feature_layer": layer, "n_sessions": int(sess.count()),
                          "n_windows": int(observed[feat].notna().sum()),
                          "mean": float(sess.mean()), "sd": float(sess.std(ddof=1)),
                          "median": float(sess.median()), "min": float(sess.min()), "max": float(sess.max())})
    desc = pd.DataFrame(desc_rows)

    # Q1/Q2 分布（来自行为权威表，116 场全量）
    q1_dist = frame["q1_nominal_4class"].value_counts().sort_index()
    q2_dist = frame["q2_ordinal_4level"].value_counts().sort_index()
    dist_rows = []
    for var, s in [("Q1", q1_dist), ("Q2", q2_dist)]:
        for level, n in s.items():
            dist_rows.append({"probe_variable": var, "category_or_level": int(level),
                              "n": int(n), "proportion": float(n / len(frame))})
    dist = pd.DataFrame(dist_rows)

    # ---- 单变量主模型：8 特征 × Q1 / Q2 / 5 行为结局 ----
    q1_result_rows: list[dict] = []
    q2_result_rows: list[dict] = []
    beh_result_rows: list[dict] = []
    failure_rows: list[dict] = []

    def _base_counts(d: pd.DataFrame) -> dict:
        return {"participant_group_n": int(d["participant_group_id"].nunique()),
                "session_n": int(d["session_id"].nunique()), "n_rows": int(len(d))}

    all_features = [*PRIMARY_FEATURES, *AUX_FEATURES]
    for feat, layer in all_features:
        # 统一数值化
        d = observed.copy()
        d[feat] = pd.to_numeric(d[feat], errors="coerce")
        for col in [*BEHAVIOR_OUTCOMES, "q1_nominal_4class", "q2_ordinal_4level"]:
            d[col] = pd.to_numeric(d[col], errors="coerce")
        d = d.dropna(subset=[feat])

        # Q1
        rows, fail = fit_q1_model(d, feat)
        if fail:
            failure_rows.append({"model_family": "MNLogit_cluster_robust", "outcome": "q1_nominal_4class",
                                 "predictor": feat, "status": "not_estimable",
                                 "observation_unit": "probe", "reason": fail["reason"], **_base_counts(d)})
        for row in rows:
            q1_result_rows.append({"model_family": "MNLogit_cluster_robust", "outcome": "q1_nominal_4class",
                                   "predictor": feat, "feature_layer": layer, "status": "estimable",
                                   "observation_unit": "probe", **row, **_base_counts(d)})
        # Q2
        row, fail = fit_q2_model(d, feat)
        if fail:
            failure_rows.append({"model_family": "OrdinalGEE", "outcome": "q2_ordinal_4level",
                                 "predictor": feat, "status": "not_estimable",
                                 "observation_unit": "probe", "reason": fail["reason"], **_base_counts(d)})
        elif row:
            q2_result_rows.append({"model_family": "OrdinalGEE", "outcome": "q2_ordinal_4level",
                                   "predictor": feat, "feature_layer": layer, "status": "estimable",
                                   "observation_unit": "probe", **row, **_base_counts(d)})
        # 行为结局（高斯 GEE）
        for outcome in BEHAVIOR_OUTCOMES:
            d_out = d.dropna(subset=[outcome])
            rows, fail = fit_gaussian_gee(d_out, outcome, [feat])
            if fail:
                failure_rows.append({"model_family": "GaussianGEE_exchangeable", "outcome": outcome,
                                     "predictor": feat, "status": "not_estimable",
                                     "observation_unit": "probe", "reason": fail["reason"],
                                     **_base_counts(d_out)})
            else:
                for row in rows:
                    beh_result_rows.append({"model_family": "GaussianGEE_exchangeable", "outcome": outcome,
                                            "predictor": feat, "feature_layer": layer, "status": "estimable",
                                            "observation_unit": "probe", **row, **_base_counts(d_out)})

    # ---- 参与者间/内分解（5 个主特征）----
    wb_q2_rows: list[dict] = []
    wb_beh_rows: list[dict] = []
    for feat, layer in PRIMARY_FEATURES:
        d = observed.copy()
        d[feat] = pd.to_numeric(d[feat], errors="coerce")
        for col in [*BEHAVIOR_OUTCOMES, "q2_ordinal_4level"]:
            d[col] = pd.to_numeric(d[col], errors="coerce")
        d = d.dropna(subset=[feat])
        work = d.copy()
        group_mean = work.groupby("participant_group_id")[feat].transform("mean")
        work["_between_z"] = _z_standardize(group_mean)
        work["_within_z"] = _z_standardize(work[feat] - group_mean)
        counts = _base_counts(work.dropna(subset=["_between_z", "_within_z"]))
        q2_fit, q2_fail = fit_q2_multi(work)
        if q2_fail:
            failure_rows.append({"model_family": "OrdinalGEE_within_between", "outcome": "q2_ordinal_4level",
                                 "predictor": feat, "status": "not_estimable", "observation_unit": "probe",
                                 "reason": q2_fail["reason"], **counts})
        else:
            for row in q2_fit:
                wb_q2_rows.append({"predictor": feat, "feature_layer": layer, "status": "estimable",
                                   **row, **counts})
        for outcome in BEHAVIOR_OUTCOMES:
            d_out = work.dropna(subset=[outcome])
            rows, fail = fit_gaussian_gee(d_out, outcome, ["_between_z", "_within_z"])
            counts_o = _base_counts(d_out)
            if fail:
                failure_rows.append({"model_family": "GaussianGEE_within_between", "outcome": outcome,
                                     "predictor": feat, "status": "not_estimable", "observation_unit": "probe",
                                     "reason": fail["reason"], **counts_o})
            else:
                for term, row in zip(["between", "within"], rows):
                    wb_beh_rows.append({"predictor": feat, "feature_layer": layer, "outcome": outcome,
                                        "term": term, "status": "estimable", **row, **counts_o})

    # ---- 高体动排除敏感性（5 个主特征 × 3 族）----
    sens_rows: list[dict] = []
    motion = pd.to_numeric(observed["mmwave_motion_proxy_median"], errors="coerce")
    motion_cut = float(motion.quantile(HIGH_MOTION_EXCLUDE_QUANTILE))
    low_motion = observed[motion <= motion_cut].copy()
    for feat, layer in PRIMARY_FEATURES:
        d = low_motion.copy()
        d[feat] = pd.to_numeric(d[feat], errors="coerce")
        for col in [*BEHAVIOR_OUTCOMES, "q1_nominal_4class", "q2_ordinal_4level"]:
            d[col] = pd.to_numeric(d[col], errors="coerce")
        d = d.dropna(subset=[feat])
        rows, fail = fit_q1_model(d, feat)
        for row in (rows if not fail else []):
            sens_rows.append({"analysis": "high_motion_excluded", "model_family": "MNLogit_cluster_robust",
                              "outcome": "q1_nominal_4class", "predictor": feat, "status": "estimable",
                              **row, **_base_counts(d)})
        if fail:
            sens_rows.append({"analysis": "high_motion_excluded", "model_family": "MNLogit_cluster_robust",
                              "outcome": "q1_nominal_4class", "predictor": feat, "status": "not_estimable",
                              "reason": fail["reason"], **_base_counts(d)})
        row, fail = fit_q2_model(d, feat)
        if fail:
            sens_rows.append({"analysis": "high_motion_excluded", "model_family": "OrdinalGEE",
                              "outcome": "q2_ordinal_4level", "predictor": feat, "status": "not_estimable",
                              "reason": fail["reason"], **_base_counts(d)})
        elif row:
            sens_rows.append({"analysis": "high_motion_excluded", "model_family": "OrdinalGEE",
                              "outcome": "q2_ordinal_4level", "predictor": feat, "status": "estimable",
                              **row, **_base_counts(d)})
        for outcome in BEHAVIOR_OUTCOMES:
            d_out = d.dropna(subset=[outcome])
            rows, fail = fit_gaussian_gee(d_out, outcome, [feat])
            if fail:
                sens_rows.append({"analysis": "high_motion_excluded", "model_family": "GaussianGEE_exchangeable",
                                  "outcome": outcome, "predictor": feat, "status": "not_estimable",
                                  "reason": fail["reason"], **_base_counts(d_out)})
            else:
                for row in rows:
                    sens_rows.append({"analysis": "high_motion_excluded", "model_family": "GaussianGEE_exchangeable",
                                      "outcome": outcome, "predictor": feat, "status": "estimable",
                                      **row, **_base_counts(d_out)})

    # ---- 落盘 ----
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    q1 = pd.DataFrame(q1_result_rows)
    q2 = pd.DataFrame(q2_result_rows)
    beh = pd.DataFrame(beh_result_rows)
    wb_q2 = pd.DataFrame(wb_q2_rows)
    wb_beh = pd.DataFrame(wb_beh_rows)
    sens = pd.DataFrame(sens_rows)
    failures = pd.DataFrame(failure_rows)
    desc.to_csv(OUT_DIR / "mmwave_probe_descriptives.csv", index=False, encoding="utf-8-sig")
    dist.to_csv(OUT_DIR / "probe_q1_q2_distribution.csv", index=False, encoding="utf-8-sig")
    q1.to_csv(OUT_DIR / "mmwave_q1_nominal_models.csv", index=False, encoding="utf-8-sig")
    q2.to_csv(OUT_DIR / "mmwave_q2_ordinal_gee_models.csv", index=False, encoding="utf-8-sig")
    beh.to_csv(OUT_DIR / "mmwave_behavior_outcome_models.csv", index=False, encoding="utf-8-sig")
    wb_q2.to_csv(OUT_DIR / "mmwave_q2_within_between_models.csv", index=False, encoding="utf-8-sig")
    wb_beh.to_csv(OUT_DIR / "mmwave_behavior_within_between_models.csv", index=False, encoding="utf-8-sig")
    sens.to_csv(OUT_DIR / "mmwave_high_motion_excluded_sensitivity.csv", index=False, encoding="utf-8-sig")
    failures.to_csv(OUT_DIR / "model_failures.csv", index=False, encoding="utf-8-sig")

    manifest = {
        "run_date": "2026-08-31",
        "scope": "merge-ready tables only; no raw radar or producer signal-chain read",
        "cohort": {"participant_n": 61, "session_n": 116, "probe_n": 2320},
        "mmwave_observed": {"session_n": int(observed["session_id"].nunique()),
                            "window_n": int(len(observed))},
        "mmwave_missing_sessions": missing_sessions,
        "identity_source": "Behavior formal_v3 participant_group_id (authoritative); join by session+block+probe index",
        "predictors": {"primary": PRIMARY_FEATURES, "aux": AUX_FEATURES},
        "outcomes": {"q1": "q1_nominal_4class (MNLogit cluster robust, reference category 1)",
                     "q2": "q2_ordinal_4level (OrdinalGEE GlobalOddsRatio)",
                     "behavior": BEHAVIOR_OUTCOMES + [" (Gaussian GEE exchangeable)"]},
        "within_between": "participant mean (between) and deviation (within), both z-standardized",
        "high_motion_sensitivity": {"rule": f"exclude windows with motion_proxy > overall p{HIGH_MOTION_EXCLUDE_QUANTILE:.0f}",
                                    "cutoff": motion_cut},
        "rgb_covariate_sensitivity": "not run: RGB window-level motion aggregate table not yet materialized",
        "ci_method": "estimate +/- 1.96 * SE",
        "p_values": "not computed; inference by 95% CI contains zero or not",
        "seed": SEED,
    }
    (OUT_DIR / "run_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"done. q1={len(q1)} q2={len(q2)} behavior={len(beh)} wb_q2={len(wb_q2)} "
          f"wb_beh={len(wb_beh)} sensitivity={len(sens)} failures={len(failures)}")
    print(f"output: {OUT_DIR}")


if __name__ == "__main__":
    main()
