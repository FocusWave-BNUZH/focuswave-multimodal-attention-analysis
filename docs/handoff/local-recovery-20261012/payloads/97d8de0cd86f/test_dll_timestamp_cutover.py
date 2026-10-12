import importlib.util
from pathlib import Path

import numpy as np
import pytest


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "maintenance" / "run_mmwave_probe_merge_ready_20260831.py"


def load_adapter():
    spec = importlib.util.spec_from_file_location("dll_cutover_adapter", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def synthetic(python_delay_ms=0):
    dll = np.array([100, 110, 120, 130], dtype=np.int64)
    return np.column_stack([np.arange(len(dll)), dll, dll + 1000 + python_delay_ms])


def window_membership(adapter, values):
    timestamps = adapter.alignment_timestamps(values)
    lo, hi = np.searchsorted(timestamps, [100, 120], side="left")
    return lo, hi, timestamps[lo:hi].tolist()


def test_dll_column_controls_membership_and_exact_onset_is_excluded():
    adapter = load_adapter()
    assert window_membership(adapter, synthetic()) == (0, 2, [100, 110])


def test_python_processing_stall_does_not_change_membership():
    adapter = load_adapter()
    baseline = synthetic()
    stalled = synthetic(2000)
    assert window_membership(adapter, baseline) == window_membership(adapter, stalled)
    assert adapter.processing_delay_ms(baseline).tolist() == [1000] * 4
    assert adapter.processing_delay_ms(stalled).tolist() == [3000] * 4


def test_missing_dll_timestamp_fails_without_python_fallback():
    adapter = load_adapter()
    with pytest.raises(ValueError, match="DLL host receive"):
        adapter.alignment_timestamps(np.array([[0], [1]], dtype=np.int64))


def test_provenance_is_dll_host_receive_not_hardware_time():
    adapter = load_adapter()
    provenance = adapter.timestamp_provenance()
    assert provenance["timestamp_source"] == "dll_host_receive"
    assert provenance["timestamp_column"] == 1
    assert provenance["python_processing_timestamp_column"] == 2
    assert "not radar hardware" in provenance["timestamp_semantics"]
