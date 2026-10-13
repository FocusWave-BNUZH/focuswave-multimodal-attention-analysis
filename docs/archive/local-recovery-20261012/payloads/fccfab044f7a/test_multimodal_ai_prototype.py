from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "pipelines/fusion/run_quality_aware_fusion_prototype.py"


def load_module():
    spec = importlib.util.spec_from_file_location("multimodal_ai_prototype", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def readiness(status: str = "formal_ready") -> dict:
    return {
        "schema_version": "focuswave-multimodal-readiness-v1",
        "analysis_role": "central_inference",
        "matched_cohort": {"frozen": True, "cohort_id": "synthetic-test"},
        "folds": {"frozen": True, "group_key": "repeat_participant_id"},
        "producers": {
            modality: {
                "status": status,
                "formal_ready": status == "formal_ready",
                "quality_semantics_frozen": True,
                "feature_contract": f"{modality}-v1",
            }
            for modality in ("mmwave", "nir", "rgb")
        },
    }


def fixture() -> tuple[pd.DataFrame, pd.DataFrame]:
    rng = np.random.default_rng(7)
    rows = []
    fold_rows = []
    for participant in range(8):
        group = f"R{participant:03d}"
        fold_rows.append({"repeat_participant_id": group, "fold": participant % 4})
        for probe in range(4):
            target = int((participant + probe) % 3 == 0)
            row = {
                "site": "test",
                "session_id": f"s{participant:03d}",
                "probe_id": probe + 1,
                "repeat_participant_id": group,
                "identity_status": "resolved",
                "id_scope": "global_central",
                "target": target,
            }
            for modality in ("context", "mmwave", "nir", "rgb"):
                row[f"{modality}__x1"] = float(rng.normal(loc=target, scale=0.5))
                row[f"{modality}__x2"] = float(rng.normal(loc=target, scale=0.5))
            for modality in ("mmwave", "nir", "rgb"):
                row[f"{modality}_available"] = 1
                row[f"{modality}_quality"] = 0.8
            rows.append(row)
    return pd.DataFrame(rows), pd.DataFrame(fold_rows)


def test_preliminary_producer_is_rejected():
    module = load_module()
    with pytest.raises(module.GateBlocked, match="not formal-ready"):
        module.validate_readiness(readiness("preliminary_screening_only"))


def test_prototype_uses_same_rows_and_frozen_groups(tmp_path):
    module = load_module()
    frame, folds = fixture()
    manifest = module.run_experiment(frame, folds, readiness(), tmp_path, bootstrap_reps=20)
    assert manifest["status"] == "PROTOTYPE_ONLY"
    predictions = pd.read_csv(tmp_path / "oof_predictions.csv")
    assert len(predictions) == len(frame) * 4 * 4
    assignments = predictions[["repeat_participant_id", "fold"]].drop_duplicates()
    assert not assignments.duplicated("repeat_participant_id").any()
    metrics = pd.read_csv(tmp_path / "metrics.csv")
    assert set(metrics["model"]) == {
        "context_logistic", "concat_logistic", "concat_mlp", "quality_gated_fusion"
    }
    assert set(metrics["ablation"]) == {
        "all_available", "missing_mmwave", "missing_nir", "missing_rgb"
    }
    weights = pd.read_csv(tmp_path / "gating_weights.csv")
    assert np.allclose(weights[["w_context", "w_mmwave", "w_nir", "w_rgb"]].sum(axis=1), 1.0)


def test_unresolved_identity_is_rejected():
    module = load_module()
    frame, _ = fixture()
    frame.loc[0, "identity_status"] = "unresolved"
    with pytest.raises(module.GateBlocked, match="unresolved identity"):
        module.validate_feature_frame(frame)
