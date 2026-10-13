"""Strict, small-sample multimodal fusion prototype.

This runner is intentionally a central-inference prototype.  It does not
produce a result from engineering/proxy inputs: a readiness manifest must
declare all four input blocks (context, mmWave, NIR and RGB) formally ready,
with a frozen matched cohort and frozen participant-level folds.

The runner compares a context logistic baseline, regularized concatenation,
a small concatenation MLP, and a quality-aware late-fusion gate.  Every model
is refit inside each participant-disjoint outer fold.  Missing-modality rows
are stress-tested by masking the held-out fold only; no rows are silently
dropped for an ablation.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd
from scipy.optimize import minimize
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import balanced_accuracy_score, f1_score, log_loss, roc_auc_score
from sklearn.neural_network import MLPClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler


SCHEMA_VERSION = "focuswave-multimodal-ai-prototype-v1"
MODALITIES = ("context", "mmwave", "nir", "rgb")
SENSOR_MODALITIES = ("mmwave", "nir", "rgb")
READY_STATUSES = {"formal_ready", "canonical_formal_ready"}
ABLATIONS = ("all_available", "missing_mmwave", "missing_nir", "missing_rgb")


class GateBlocked(RuntimeError):
    """Raised when a scientific or data-readiness gate is not satisfied."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise GateBlocked(message)


def readiness_errors(readiness: dict) -> list[str]:
    """Return all central-inference gate failures without reading raw data."""

    errors: list[str] = []
    if readiness.get("schema_version") != "focuswave-multimodal-readiness-v1":
        errors.append("readiness schema must be focuswave-multimodal-readiness-v1")
    if readiness.get("analysis_role") != "central_inference":
        errors.append("only central_inference readiness may run this prototype")
    if readiness.get("matched_cohort", {}).get("frozen") is not True:
        errors.append("matched cohort is not frozen")
    folds = readiness.get("folds", {})
    if folds.get("frozen") is not True:
        errors.append("participant-level folds are not frozen")
    if folds.get("group_key") != "repeat_participant_id":
        errors.append("fold group key must be repeat_participant_id")
    producers = readiness.get("producers", {})
    for modality in SENSOR_MODALITIES:
        spec = producers.get(modality, {})
        status = spec.get("status")
        if spec.get("formal_ready") is not True or status not in READY_STATUSES:
            errors.append(f"{modality} producer is not formal-ready (status={status!r})")
        if spec.get("quality_semantics_frozen") is not True:
            errors.append(f"{modality} quality semantics are not frozen")
        if not spec.get("feature_contract"):
            errors.append(f"{modality} feature contract is missing")
        status_text = " ".join(
            str(spec.get(field, "")).lower()
            for field in ("status", "role", "feature_status")
        )
        if "preliminary" in status_text or "engineering_only" in status_text or "proxy" in status_text:
            errors.append(f"{modality} readiness contains preliminary/engineering/proxy wording")
    return errors


def validate_readiness(readiness: dict) -> None:
    """Validate the central inference gate without inspecting private raw data."""

    errors = readiness_errors(readiness)
    _require(not errors, "; ".join(errors))


def feature_columns(frame: pd.DataFrame, modality: str) -> list[str]:
    return [column for column in frame.columns if column.startswith(f"{modality}__")]


def validate_feature_frame(frame: pd.DataFrame) -> dict[str, list[str]]:
    required = {
        "site", "session_id", "probe_id", "repeat_participant_id",
        "identity_status", "id_scope", "target",
        *(f"{modality}_available" for modality in SENSOR_MODALITIES),
        *(f"{modality}_quality" for modality in SENSOR_MODALITIES),
    }
    missing = sorted(required.difference(frame.columns))
    _require(not missing, f"feature matrix missing required columns: {missing}")
    key_columns = ["site", "session_id", "probe_id"]
    _require(
        not frame.duplicated(key_columns).any(),
        "duplicate site/session_id/probe_id rows would invalidate matched evaluation",
    )
    _require(
        frame["identity_status"].astype(str).eq("resolved").all(),
        "unresolved identity cannot enter participant-disjoint inference",
    )
    _require(
        frame["id_scope"].astype(str).eq("global_central").all(),
        "repeat_participant_id must be explicitly marked global_central",
    )
    target = pd.to_numeric(frame["target"], errors="coerce")
    _require(target.notna().all() and set(target.astype(int).unique()) <= {0, 1},
             "target must be a complete binary 0/1 column mapped upstream")
    _require(target.nunique() == 2, "matched matrix must contain both target classes")

    blocks: dict[str, list[str]] = {}
    for modality in MODALITIES:
        columns = feature_columns(frame, modality)
        _require(columns, f"{modality} feature block is empty")
        blocks[modality] = columns
    for modality in SENSOR_MODALITIES:
        available = pd.to_numeric(frame[f"{modality}_available"], errors="coerce")
        quality = pd.to_numeric(frame[f"{modality}_quality"], errors="coerce")
        _require(available.notna().all() and available.eq(1).all(),
                 f"primary matched cohort has unavailable {modality} rows")
        _require(quality.notna().all() and quality.between(0, 1).all(),
                 f"{modality}_quality must be finite and in [0, 1]")
        for column in blocks[modality]:
            _require(pd.api.types.is_numeric_dtype(frame[column]),
                     f"feature column must be numeric: {column}")
    for column in blocks["context"]:
        _require(pd.api.types.is_numeric_dtype(frame[column]),
                 f"feature column must be numeric: {column}")
    return blocks


def validate_folds(frame: pd.DataFrame, folds: pd.DataFrame) -> pd.DataFrame:
    required = {"repeat_participant_id", "fold"}
    _require(required <= set(folds.columns), "fold file must contain repeat_participant_id and fold")
    _require(not folds.duplicated("repeat_participant_id").any(),
             "fold file contains duplicate participant assignments")
    fold_map = folds.set_index("repeat_participant_id")["fold"]
    groups = frame["repeat_participant_id"].astype(str)
    _require(groups.isin(fold_map.index.astype(str)).all(),
             "every feature-matrix participant must have a frozen fold")
    assigned = groups.map({str(k): int(v) for k, v in fold_map.items()})
    _require(assigned.notna().all(), "fold assignment contains missing values")
    _require(set(assigned.astype(int).unique()) == set(range(int(assigned.max()) + 1)),
             "fold labels must be contiguous starting at zero")
    out = frame.copy()
    out["fold"] = assigned.astype(int).to_numpy()
    return out


def _imputer() -> SimpleImputer:
    return SimpleImputer(strategy="median", keep_empty_features=True)


def logistic_model() -> Pipeline:
    return Pipeline([
        ("imputer", _imputer()),
        ("scaler", StandardScaler()),
        ("model", LogisticRegression(C=1.0, max_iter=2000, solver="liblinear")),
    ])


def mlp_model(seed: int) -> Pipeline:
    return Pipeline([
        ("imputer", _imputer()),
        ("scaler", StandardScaler()),
        ("model", MLPClassifier(
            hidden_layer_sizes=(16,), activation="relu", alpha=1e-3,
            max_iter=1000, early_stopping=False, random_state=seed,
        )),
    ])


def _quality_matrix(frame: pd.DataFrame) -> np.ndarray:
    values = [np.ones(len(frame), dtype=float)]
    for modality in SENSOR_MODALITIES:
        available = pd.to_numeric(frame[f"{modality}_available"], errors="coerce").to_numpy(float)
        quality = pd.to_numeric(frame[f"{modality}_quality"], errors="coerce").to_numpy(float)
        values.append(np.clip(available * quality, 0.0, 1.0))
    return np.column_stack(values)


def _sigmoid(values: np.ndarray) -> np.ndarray:
    values = np.clip(values, -40.0, 40.0)
    return 1.0 / (1.0 + np.exp(-values))


class QualityAwareGatedFusion:
    """Four block experts plus a train-fold learned softmax quality gate."""

    def __init__(self, blocks: dict[str, list[str]], seed: int) -> None:
        self.blocks = blocks
        self.seed = seed
        self.experts: dict[str, Pipeline] = {}
        self.parameters: np.ndarray | None = None

    @staticmethod
    def _gate_weights(parameters: np.ndarray, quality: np.ndarray) -> np.ndarray:
        design = np.column_stack([np.ones(len(quality)), quality])
        scores = design @ parameters.reshape(4, 5).T
        scores -= scores.max(axis=1, keepdims=True)
        weights = np.exp(scores)
        return weights / weights.sum(axis=1, keepdims=True)

    def fit(self, train: pd.DataFrame, target: np.ndarray) -> "QualityAwareGatedFusion":
        expert_logits = []
        for index, modality in enumerate(MODALITIES):
            expert = logistic_model()
            expert.fit(train[self.blocks[modality]], target)
            self.experts[modality] = expert
            expert_logits.append(expert.decision_function(train[self.blocks[modality]]))
        logits = np.column_stack(expert_logits)
        quality = _quality_matrix(train)

        def objective(parameters: np.ndarray) -> float:
            weights = self._gate_weights(parameters, quality)
            fused = np.sum(weights * logits, axis=1)
            probabilities = _sigmoid(fused)
            loss = log_loss(target, probabilities, labels=[0, 1])
            return float(loss + 1e-3 * np.sum(parameters * parameters))

        result = minimize(objective, np.zeros(20, dtype=float), method="L-BFGS-B")
        _require(result.success, f"quality gate optimization failed: {result.message}")
        self.parameters = result.x
        return self

    def predict(self, frame: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
        _require(self.parameters is not None, "quality gate used before fit")
        logits = np.column_stack([
            self.experts[modality].decision_function(frame[self.blocks[modality]])
            for modality in MODALITIES
        ])
        weights = self._gate_weights(self.parameters, _quality_matrix(frame))
        return _sigmoid(np.sum(weights * logits, axis=1)), weights


def masked_frame(frame: pd.DataFrame, blocks: dict[str, list[str]], missing: str | None) -> pd.DataFrame:
    out = frame.copy()
    if missing is not None:
        for column in blocks[missing]:
            out[column] = np.nan
        out[f"{missing}_available"] = 0
        out[f"{missing}_quality"] = 0.0
    return out


def _metrics(target: np.ndarray, prediction: np.ndarray) -> dict[str, float | None]:
    labels = (prediction >= 0.5).astype(int)
    return {
        "n_probe": int(len(target)),
        "n_positive": int(target.sum()),
        "roc_auc": float(roc_auc_score(target, prediction)) if len(np.unique(target)) == 2 else None,
        "balanced_accuracy": float(balanced_accuracy_score(target, labels)),
        "macro_f1": float(f1_score(target, labels, average="macro", zero_division=0)),
        "brier": float(np.mean((prediction - target) ** 2)),
        "log_loss": float(log_loss(target, prediction, labels=[0, 1])),
    }


def _bootstrap_metrics(
    predictions: pd.DataFrame,
    group_key: str,
    reps: int,
    seed: int,
) -> dict[str, float | int | None]:
    groups = predictions[group_key].astype(str).unique()
    rng = np.random.default_rng(seed)
    values = {key: [] for key in ("roc_auc", "balanced_accuracy", "macro_f1", "brier", "log_loss")}
    for _ in range(reps):
        sampled = rng.choice(groups, size=len(groups), replace=True)
        parts = [predictions[predictions[group_key].astype(str).eq(group)] for group in sampled]
        sample = pd.concat(parts, ignore_index=True)
        result = _metrics(sample["target"].to_numpy(int), sample["prediction"].to_numpy(float))
        for key in values:
            if result[key] is not None:
                values[key].append(float(result[key]))
    output: dict[str, float | int | None] = {"bootstrap_reps": reps, "bootstrap_valid": len(values["brier"])}
    for key, samples in values.items():
        output[f"{key}_ci95_low"] = float(np.quantile(samples, 0.025)) if samples else None
        output[f"{key}_ci95_high"] = float(np.quantile(samples, 0.975)) if samples else None
    return output


def run_experiment(
    frame: pd.DataFrame,
    folds: pd.DataFrame,
    readiness: dict,
    output_dir: Path,
    bootstrap_reps: int = 200,
    seed: int = 20260830,
) -> dict:
    validate_readiness(readiness)
    blocks = validate_feature_frame(frame)
    frame = validate_folds(frame, folds)
    output_dir.mkdir(parents=True, exist_ok=True)
    all_predictions: list[dict] = []
    all_weights: list[dict] = []
    fold_values = sorted(frame["fold"].unique())
    for fold in fold_values:
        train = frame[frame["fold"] != fold].copy()
        test = frame[frame["fold"] == fold].copy()
        target_train = train["target"].astype(int).to_numpy()
        target_test = test["target"].astype(int).to_numpy()
        _require(len(np.unique(target_train)) == 2, f"fold {fold} training data is single-class")
        models: dict[str, object] = {
            "context_logistic": logistic_model(),
            "concat_logistic": logistic_model(),
            "concat_mlp": mlp_model(seed + int(fold)),
            "quality_gated_fusion": QualityAwareGatedFusion(blocks, seed + int(fold)),
        }
        models["context_logistic"].fit(train[blocks["context"]], target_train)
        all_columns = [column for modality in MODALITIES for column in blocks[modality]]
        models["concat_logistic"].fit(train[all_columns], target_train)
        models["concat_mlp"].fit(train[all_columns], target_train)
        models["quality_gated_fusion"].fit(train, target_train)

        for ablation in ABLATIONS:
            missing = None if ablation == "all_available" else ablation.removeprefix("missing_")
            test_masked = masked_frame(test, blocks, missing)
            condition_predictions: dict[str, np.ndarray] = {}
            condition_predictions["context_logistic"] = models["context_logistic"].predict_proba(
                test_masked[blocks["context"]]
            )[:, 1]
            condition_predictions["concat_logistic"] = models["concat_logistic"].predict_proba(
                test_masked[all_columns]
            )[:, 1]
            condition_predictions["concat_mlp"] = models["concat_mlp"].predict_proba(
                test_masked[all_columns]
            )[:, 1]
            gated_prediction, weights = models["quality_gated_fusion"].predict(test_masked)
            condition_predictions["quality_gated_fusion"] = gated_prediction
            for model_name, prediction in condition_predictions.items():
                for row, score in zip(test.itertuples(index=False), prediction):
                    all_predictions.append({
                        "site": row.site, "session_id": row.session_id, "probe_id": row.probe_id,
                        "repeat_participant_id": row.repeat_participant_id, "fold": int(fold),
                        "target": int(row.target), "model": model_name, "ablation": ablation,
                        "prediction": float(score),
                    })
            for row, weight in zip(test.itertuples(index=False), weights):
                all_weights.append({
                    "site": row.site, "session_id": row.session_id, "probe_id": row.probe_id,
                    "repeat_participant_id": row.repeat_participant_id, "fold": int(fold),
                    "ablation": ablation, "w_context": float(weight[0]),
                    "w_mmwave": float(weight[1]), "w_nir": float(weight[2]),
                    "w_rgb": float(weight[3]),
                })

    predictions = pd.DataFrame(all_predictions)
    weights = pd.DataFrame(all_weights)
    metrics_rows = []
    for (model, ablation), group in predictions.groupby(["model", "ablation"], sort=True):
        base = _metrics(group["target"].to_numpy(int), group["prediction"].to_numpy(float))
        base.update({"model": model, "ablation": ablation,
                     "n_session": int(group[["site", "session_id"]].drop_duplicates().shape[0]),
                     "n_participant": int(group["repeat_participant_id"].nunique())})
        base.update(_bootstrap_metrics(group, "repeat_participant_id", bootstrap_reps, seed))
        metrics_rows.append(base)
    metrics = pd.DataFrame(metrics_rows)
    predictions.to_csv(output_dir / "oof_predictions.csv", index=False)
    weights.to_csv(output_dir / "gating_weights.csv", index=False)
    metrics.to_csv(output_dir / "metrics.csv", index=False)
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "status": "PROTOTYPE_ONLY",
        "scientific_role": "secondary_predictive_fusion_prototype",
        "cohort": {
            "n_probe": int(len(frame)),
            "n_session": int(frame[["site", "session_id"]].drop_duplicates().shape[0]),
            "n_participant": int(frame["repeat_participant_id"].nunique()),
            "n_folds": int(len(fold_values)),
        },
        "target": "upstream binary target column; no label remapping in runner",
        "validation": "frozen participant-disjoint outer folds",
        "preprocessing": "median imputation and scaling fit inside each training fold",
        "models": ["context_logistic", "concat_logistic", "concat_mlp", "quality_gated_fusion"],
        "ablations": list(ABLATIONS),
        "blocked_interpretations": [
            "not causal modality attribution",
            "not physiology validation",
            "not a final attention-state claim",
        ],
    }
    (output_dir / "run_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return manifest


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--features", type=Path)
    parser.add_argument("--folds", type=Path)
    parser.add_argument("--readiness", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--bootstrap-reps", type=int, default=200)
    parser.add_argument("--seed", type=int, default=20260830)
    parser.add_argument("--preflight", action="store_true", help="validate readiness only")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        readiness = json.loads(args.readiness.read_text(encoding="utf-8"))
        validate_readiness(readiness)
        if args.preflight:
            payload = {"status": "PASS", "gate": "formal multimodal readiness", "schema_version": SCHEMA_VERSION}
            print(json.dumps(payload, ensure_ascii=False))
            return 0
        _require(args.features is not None and args.folds is not None,
                 "--features and --folds are required unless --preflight is used")
        frame = pd.read_csv(args.features)
        folds = pd.read_csv(args.folds)
        manifest = run_experiment(
            frame, folds, readiness, args.output_dir,
            bootstrap_reps=args.bootstrap_reps, seed=args.seed,
        )
        manifest["source_sha256"] = {
            "features": sha256_file(args.features),
            "folds": sha256_file(args.folds),
            "readiness": sha256_file(args.readiness),
        }
        (args.output_dir / "run_manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(json.dumps({"status": "PASS", **manifest["cohort"]}, ensure_ascii=False))
        return 0
    except GateBlocked as error:
        args.output_dir.mkdir(parents=True, exist_ok=True)
        report = {
            "status": "BLOCKED",
            "schema_version": SCHEMA_VERSION,
            "reason": str(error),
        }
        (args.output_dir / "gate_report.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(json.dumps(report, ensure_ascii=False))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
