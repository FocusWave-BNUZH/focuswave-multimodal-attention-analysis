import importlib.util
from pathlib import Path

import numpy as np
import pytest


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "maintenance" / "run_mmwave_pre30s_selector_hr_20260831.py"


def load_module():
    spec = importlib.util.spec_from_file_location("pre30s_dll_cutover", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_dll_host_receive_clock_is_selected_without_python_fallback():
    module = load_module()
    values = np.array([[0, 100, 500], [1, 110, 9_000], [2, 120, 10_000]])
    assert module.alignment_timestamps(values).tolist() == [100, 110, 120]
    lo, hi = np.searchsorted(module.alignment_timestamps(values), [100, 120], side="left")
    assert (lo, hi) == (0, 2)


def test_missing_or_invalid_dll_clock_fails_closed():
    module = load_module()
    with pytest.raises(ValueError, match="DLL host receive"):
        module.alignment_timestamps(np.array([[0], [1]]))
    with pytest.raises(ValueError, match="invalid or nonmonotonic"):
        module.alignment_timestamps(np.array([[0, 110, 1], [1, 100, 2]]))
