import importlib.util
from pathlib import Path

import numpy as np
import pytest


ROOT = Path(__file__).resolve().parents[1]
ADAPTER = ROOT / "scripts" / "maintenance" / "run_mmwave_probe_merge_ready_20260831.py"
PRODUCER = ROOT / "scripts" / "process_vital_signs_v3_1_1.py"


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def timestamps(python_offset_ms: int = 0) -> np.ndarray:
    # col0 frame index, col1 DLL host receive, col2 delayed Python processing.
    dll = np.array([100, 110, 120, 130], dtype=np.int64)
    return np.column_stack((np.arange(len(dll)), dll, dll + 1_000 + python_offset_ms))


def test_formal_slicing_uses_dll_column_and_excludes_exact_probe_onset():
    module = load_module(ADAPTER, "dll_adapter_t1")
    first = module.select_formal_window_indices(timestamps(), 100, 120)
    changed_python = timestamps(python_offset_ms=2_000)
    second = module.select_formal_window_indices(changed_python, 100, 120)
    assert first == second == (0, 2)
    assert module.alignment_timestamps(changed_python).tolist() == [100, 110, 120, 130]
    # The exact 120-ms probe-onset frame is index 2 and is outside [100, 120).
    assert module.alignment_timestamps(changed_python)[first[0]:first[1]].tolist() == [100, 110]


def test_python_processing_stall_is_qc_only_and_processing_delay_is_explicit():
    module = load_module(ADAPTER, "dll_adapter_t3")
    baseline = timestamps()
    stalled = timestamps(python_offset_ms=2_000)
    assert module.select_formal_window_indices(baseline, 105, 130) == (1, 3)
    assert module.select_formal_window_indices(stalled, 105, 130) == (1, 3)
    assert module.processing_delay_ms(baseline).tolist() == [1_000] * 4
    assert module.processing_delay_ms(stalled).tolist() == [3_000] * 4


def test_block_clipped_start_and_end_exclusive_contract_are_preserved():
    module = load_module(ADAPTER, "dll_adapter_t7")
    row = {
        "window_start_unix_ms": "90",
        "window_effective_start_unix_ms": "100",
        "window_end_unix_ms": "120",
    }
    assert module.formal_window_bounds(row) == (100, 120)
    assert module.select_formal_window_indices(timestamps(), *module.formal_window_bounds(row)) == (0, 2)


def test_missing_dll_column_never_falls_back_to_python_processing_time(tmp_path):
    module = load_module(ADAPTER, "dll_adapter_t5")
    with pytest.raises(ValueError, match="DLL host receive"):
        module.select_formal_window_indices(np.array([[0], [1]], dtype=np.int64), 0, 1)
    timestamp_file = tmp_path / "timestamps.csv"
    timestamp_file.write_text("0,,1000\\n", encoding="utf-8")
    producer = load_module(PRODUCER, "dll_producer_t5")
    with pytest.raises(ValueError, match="No valid radar timestamps"):
        producer.load_radar_timestamps(timestamp_file)


def test_timestamp_provenance_is_not_hardware_time():
    module = load_module(ADAPTER, "dll_adapter_t4")
    provenance = module.alignment_provenance()
    assert provenance["alignment_timestamp_source"] == "dll_host_receive"
    assert provenance["alignment_timestamp_column"] == 1
    assert provenance["python_processing_timestamp_column"] == 2
    assert "hardware" not in provenance["alignment_timestamp_source"]
    assert "not radar hardware" in provenance["alignment_timestamp_semantics"]


def test_active_formal_and_supporting_window_paths_do_not_slice_on_python_column():
    paths = [
        ROOT / "scripts" / "maintenance" / "run_mmwave_probe_merge_ready_20260831.py",
        ROOT / "scripts" / "maintenance" / "run_mmwave_probe_merge_ready_E_20260831.py",
        ROOT / "scripts" / "maintenance" / "run_mmwave_pre30s_selector_hr_20260831.py",
        ROOT / "scripts" / "maintenance" / "plot_mmwave_method_3panel_20260831.py",
        ROOT / "scripts" / "maintenance" / "run_mmwave_targeted_validation_20260830.py",
        ROOT / "scripts" / "maintenance" / "run_mmwave_window_length_comparison_20260830.py",
        ROOT / "scripts" / "maintenance" / "run_mmwave_beat_level_validation_20260830.py",
        ROOT / "scripts" / "maintenance" / "run_mmwave_estimator_same_window_audit_20260830.py",
        ROOT / "scripts" / "maintenance" / "run_mmwave_gate_target_ablation_20260830.py",
    ]
    for path in paths:
        assert "timestamps[:, 2]" not in path.read_text(encoding="utf-8"), path


def test_beat_validation_uses_dll_time_for_peak_matching():
    beat = load_module(
        ROOT / "scripts" / "maintenance" / "run_mmwave_beat_level_validation_20260830.py",
        "dll_beat_validation",
    )
    source = (ROOT / "scripts" / "maintenance" / "run_mmwave_beat_level_validation_20260830.py").read_text(
        encoding="utf-8"
    )
    assert "radar_ms = timestamps[selected, 1].astype(float)" in source
    assert "radar_ms = timestamps[selected, 2].astype(float)" not in source
