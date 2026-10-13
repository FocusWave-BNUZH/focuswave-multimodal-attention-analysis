"""Run the same range-gated sensitivity with a radar-only power selector.

This wrapper intentionally reuses the fixed evaluator and all signal
construction code from the range-gate sensitivity script; only the bin score
inside the candidate region is changed to mean complex power.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "work"))
import evaluate_rs6240_phase_fusion_range_gate_sensitivity_v1 as gate  # noqa: E402


def power_bin(cube: np.ndarray, channels: list[int], lo: int, hi: int) -> int:
    profile = np.mean(np.abs(cube[:, :, channels]) ** 2, axis=(0, 2))
    return int(lo + np.argmax(profile[lo : hi + 1]))


gate.gated_bin = power_bin


if __name__ == "__main__":
    gate.main()
