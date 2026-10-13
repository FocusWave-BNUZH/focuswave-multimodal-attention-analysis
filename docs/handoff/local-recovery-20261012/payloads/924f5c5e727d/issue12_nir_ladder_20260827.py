from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import balanced_accuracy_score, roc_auc_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

NIR = Path(r"D:\Project\厚粲杯\11_数据\derived\nir_69session_final_probe_analysis_v1\analysis_probe_matrix_30s.csv")
C2B = Path(r"D:\Project\厚粲杯\11_数据\derived\c2b_v2_canonical_baselines_20260826\window_30s\canonical_feature_matrix_local.csv")
OUT = Path(__file__).with_name("issue12_nir_ladder_20260827")
SEED = 20260827
BOOT = 1000
CONTEXT = ["block_num", "block_probe_fraction", "onset_rel_s"]
BEHAVIOR = ["pre10_error_rate", "pre10_rt_median_ms", "pre10_rt_sd_ms", "pre10_n_trials"]
NIR_FEATURES = [
    "nir_pir_median", "nir_pir_mean", "nir_pir_mad", "nir_pir_iqr", "nir_pir_sd",
    "nir_pir_p10", "nir_pir_p90", "nir_pir_slope_per_sec", "nir_pir_diff_mad",
    "nir_pir_diff_rate_mad_per_sec", "nir_oar_median", "nir_oar_mean", "nir_oar_mad",
    "nir_oar_iqr", "nir_oar_sd", "nir_oar_p10", "nir_oar_p90", "nir_oar_slope_per_sec",
    "nir_oar_diff_mad", "nir_oar_diff_rate_mad_per_sec",
]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1_048_576), b""):
            h.update(chunk)
    return h.hexdigest()


def model(seed: int):
    return make_pipeline(
        SimpleImputer(strategy="median", add_indicator=True),
        StandardScaler(),
        LogisticRegression(C=1.0, max_iter=3000, class_weight="balanced", random_state=seed),
    )


def fit_oof(data: pd.DataFrame, features: list[str], name: str) -> pd.DataFrame:
    rows = []
    for fold in range(5):
        train, test = data[data.fold != fold], data[data.fold == fold]
        if train.target.nunique() != 2:
            raise RuntimeError(f"one-class training fold: {fold}")
        m = model(SEED + fold)
        m.fit(train[features], train.target)
        out = test[["subject_id", "session_id", "session_probe_index", "repeat_participant_id", "target", "fold"]].copy()
        out["model"] = name
        out["score"] = m.predict_proba(test[features])[:, 1]
        rows.append(out)
    return pd.concat(rows, ignore_index=True)


def auc(y, s):
    return float(roc_auc_score(y, s))


def main():
    OUT.mkdir(exist_ok=True)
    nir = pd.read_csv(NIR)
    c2b = pd.read_csv(C2B)
    nir["subject_key"] = nir.subject_id.astype(float).astype(int).map(lambda x: f"{x:03d}")
    c2b["subject_key"] = c2b.subject_id.astype(float).astype(int).map(lambda x: f"{x:03d}")
    nir["probe_key"] = nir.session_probe_index.astype(float).astype(int)
    c2b["probe_key"] = c2b.probe_seq.astype(float).astype(int)
    nir["onset_key"] = nir.probe_onset_ms.round().astype("int64")
    c2b["onset_key"] = c2b.probe_onset_ms.round().astype("int64")
    key = ["subject_key", "probe_key", "onset_key"]
    merged = nir.merge(c2b, on=key, suffixes=("_nir", "_c2b"), validate="one_to_one", how="inner")
    if len(merged) != len(nir) or len(merged) != 1360:
        raise RuntimeError(f"exact ready join failed: nir={len(nir)}, merged={len(merged)}")
    if not np.allclose(merged.onset_abs_diff_ms, 0.0):
        raise RuntimeError("NIR onset alignment contains non-zero differences")
    merged["target"] = merged.label_nir.ne(1).astype(int)
    merged["fold"] = merged.fold.astype(int)
    merged["repeat_participant_id"] = merged.repeat_participant_id.astype(str)
    merged["subject_id"] = merged.subject_id_nir
    merged["session_id"] = merged.session_id
    merged["session_probe_index"] = merged.session_probe_index
    merged["block_num"] = merged.block_num_nir
    merged["block_probe_fraction"] = merged.block_probe_fraction_nir
    merged["onset_rel_s"] = merged.onset_rel_s_nir
    required = CONTEXT + BEHAVIOR + NIR_FEATURES
    missing = [c for c in required if c not in merged]
    if missing:
        raise RuntimeError(f"missing feature columns: {missing}")
    merged[["subject_id", "session_id", "session_probe_index", "repeat_participant_id", "target", "fold", "onset_key"] + required].to_csv(OUT / "joined_probe_matrix.csv", index=False)
    sets = {
        "nir_only": NIR_FEATURES,
        "C_plus_B": CONTEXT + BEHAVIOR,
        "C_plus_B_plus_NIR": CONTEXT + BEHAVIOR + NIR_FEATURES,
    }
    preds = pd.concat([fit_oof(merged, f, n) for n, f in sets.items()], ignore_index=True)
    rows = []
    rng = np.random.default_rng(SEED)
    groups = np.array(sorted(merged.repeat_participant_id.unique()))
    for name, features in sets.items():
        p = preds[preds.model == name].sort_values(["subject_id", "session_probe_index"])
        rows.append({"model": name, "n_probe": len(p), "n_session": p.session_id.nunique(), "n_participant": p.repeat_participant_id.nunique(), "n_features": len(features), "roc_auc": auc(p.target, p.score), "balanced_accuracy_0_5": balanced_accuracy_score(p.target, p.score >= 0.5)})
    metrics = pd.DataFrame(rows)
    metrics.to_csv(OUT / "metrics.csv", index=False)
    preds.to_csv(OUT / "oof_predictions.csv", index=False)
    comparisons = []
    for candidate, reference in [("C_plus_B_plus_NIR", "C_plus_B"), ("nir_only", "C_plus_B")]:
        a = preds[preds.model == candidate].set_index(["subject_id", "session_probe_index"])
        b = preds[preds.model == reference].set_index(["subject_id", "session_probe_index"])
        joined = a[["score", "target", "repeat_participant_id"]].join(b[["score"]], lsuffix="_a", rsuffix="_b")
        values = []
        for _ in range(BOOT):
            sampled = rng.choice(groups, len(groups), replace=True)
            idx = np.concatenate([np.flatnonzero(joined.repeat_participant_id.to_numpy() == g) for g in sampled])
            values.append(auc(joined.target.to_numpy()[idx], joined.score_a.to_numpy()[idx]) - auc(joined.target.to_numpy()[idx], joined.score_b.to_numpy()[idx]))
        delta = auc(joined.target, joined.score_a) - auc(joined.target, joined.score_b)
        comparisons.append({"candidate": candidate, "reference": reference, "n_probe": len(joined), "n_participant": joined.repeat_participant_id.nunique(), "delta_auc": delta, "ci95_low": float(np.quantile(values, .025)), "ci95_high": float(np.quantile(values, .975)), "bootstrap": BOOT})
    pd.DataFrame(comparisons).to_csv(OUT / "paired_bootstrap.csv", index=False)
    manifest = {
        "run_id": "ISSUE12_NIR_LADDER_20260827",
        "status": "PASS_WITH_RGB_BLOCKED",
        "entrypoint": str(Path(__file__)),
        "inputs": {"nir_ready_matrix": {"path": str(NIR), "sha256": sha256(NIR)}, "c2b_feature_matrix_reused_for_behavior_context_join": {"path": str(C2B), "sha256": sha256(C2B)}},
        "join": {"key": key, "rows_nir": len(nir), "rows_c2b": len(c2b), "rows_exact_join": len(merged), "onset_abs_diff_ms_max": float(merged.onset_abs_diff_ms.abs().max())},
        "cohort": {"probes": len(merged), "sessions": merged.session_id.nunique(), "repeat_participants": merged.repeat_participant_id.nunique(), "target_1_other_states": int(merged.target.sum()), "target_0_focused": int((merged.target == 0).sum())},
        "folds": {"source": "NIR ready matrix pre-existing fold and group_subject_id", "validation": "fixed 5-fold repeat-participant-disjoint", "fold_counts": {str(k): int(v) for k, v in merged.fold.value_counts().sort_index().items()}},
        "model": {"family": "L2 logistic C=1.0", "preprocessing": "median imputation with indicators and scaling fit inside each training fold", "features": sets},
        "prohibitions": {"c2b_rerun": True, "c2c_rerun": True, "rgb_consumed": False, "raw_video_or_inference": False},
    }
    (OUT / "run_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"manifest": str(OUT / 'run_manifest.json'), "metrics": metrics.to_dict(orient='records'), "comparisons": comparisons}, ensure_ascii=False))


if __name__ == "__main__":
    main()
