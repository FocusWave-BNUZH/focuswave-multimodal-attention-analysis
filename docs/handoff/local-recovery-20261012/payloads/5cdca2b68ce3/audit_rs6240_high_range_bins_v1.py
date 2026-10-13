"""Read-only diagnostic for high-index range-bin selections."""

from __future__ import annotations

import csv
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "work"))
import evaluate_rs6240_phase_fusion as base  # noqa: E402


ALIASES = {"sub-97794_": "sub-97994_"}
METRICS = ROOT / "work" / "rs6240_phase_fusion_cross_session_v1" / "window_metrics.csv"


def main() -> None:
    rows = list(csv.DictReader(METRICS.open(encoding="utf-8-sig")))
    seen: set[tuple[str, str]] = set()
    selected = []
    for row in rows:
        key = (row["session_id"], row["onset_ms"])
        if int(row["range_bin"]) >= 128 and key not in seen:
            seen.add(key)
            selected.append(row)
    print(f"high_bin_unique_windows={len(selected)}")
    print("session_id,onset_ms,selected_bin,top_power_bins,selected_power_ratio,physical_band_max_bin")
    for row in selected:
        session = ALIASES.get(row["session_id"], row["session_id"])
        cube, _, _ = base.load_window(session, int(row["onset_ms"]) - 30000, int(row["onset_ms"]))
        profile = np.mean(np.abs(cube) ** 2, axis=(0, 2))
        top = np.argsort(profile)[-8:][::-1].tolist()
        ratio = float(profile[int(row["range_bin"])] / max(np.max(profile), 1e-12))
        local = int(np.argmax(profile[5:33]) + 5)
        print(f"{row['session_id']},{row['onset_ms']},{row['range_bin']},{'|'.join(map(str, top))},{ratio:.5f},{local}")


if __name__ == "__main__":
    main()
