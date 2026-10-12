#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""建立 08_算法 的只读结构审计清单。

本工具不移动、不删除、不改写任何分析输出。它为后续受清单约束的迁移
生成一个可复查的 CSV：列出根目录与 output 顶层条目的文件数、体积、
建议归类、是否需要人工确认及默认 Git 边界。

示例：
    python scripts/maintenance/audit_repository_layout.py
    python scripts/maintenance/audit_repository_layout.py --output docs/00_治理/算法库结构审计_v1.csv
"""
from __future__ import annotations

import argparse
import csv
from datetime import date
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT = ROOT / "docs" / "00_治理" / "算法库结构审计_v1.csv"

OUTPUT_BUCKETS: dict[str, tuple[str, str]] = {
    "00_最新审计": ("00_索引与审计", "audit"),
    "J_Data_IDENTITY_SESSION_AUDIT": ("00_索引与审计", "audit"),
    "质量分析_行为裁剪_v1": ("10_质量控制", "audit"),
    "质量扫描": ("10_质量控制", "audit"),
    "ACQ_reference_20260821": ("20_生理金标准验证", "historical"),
    "ACQ_reference_20260824_reaudit": ("20_生理金标准验证", "audit"),
    "A2_rsp_gate": ("20_生理金标准验证", "exploratory"),
    "ACQ_mmwave_BP": ("20_生理金标准验证", "historical"),
    "ACQ_mmwave_FAST": ("20_生理金标准验证", "historical"),
    "ACQ-SART-SUB9779-FULL": ("20_生理金标准验证", "historical"),
    "ACQ-SART-SUB97792-FULL": ("20_生理金标准验证", "historical"),
    "ACQ-SART-SUB97793-FULL": ("20_生理金标准验证", "historical"),
    "External_AgeBalanced": ("20_生理金标准验证", "historical"),
    "外部数据集": ("20_生理金标准验证", "historical"),
    "预实验": ("30_预实验与原型", "historical"),
    "旧实验": ("30_预实验与原型", "historical"),
    "E_Data_20260821": ("30_预实验与原型", "review_required"),
    "E_Data_FAST": ("30_预实验与原型", "review_required"),
    "FAST_mmwave": ("30_预实验与原型", "historical"),
    "06_正式实验": ("40_正式实验", "historical"),
    "Formal_mmwave_FAST": ("40_正式实验", "historical"),
    "J_Data_ALERTNESS_EVENTS": ("40_正式实验", "exploratory"),
    "J_Data_GROUP_SUMMARY": ("40_正式实验", "audit"),
    "J_Data_M1_RAW_Q0_v1": ("40_正式实验", "exploratory"),
    "J_Data_MISSING_067_099_FAST": ("40_正式实验", "audit"),
    "J_Data_REPORT_RESULTS_SUMMARY": ("50_多模态与报告", "exploratory"),
    "J_Data_REPORT_FIGURES": ("50_多模态与报告", "exploratory"),
    "J_Data_MULTIMODAL_v1": ("50_多模态与报告", "exploratory"),
    "J_Data_MULTIMODAL_v1_logistic": ("50_多模态与报告", "exploratory"),
    "J_Data_MULTIMODAL_v1_forest_check": ("50_多模态与报告", "sensitivity"),
    "J_Data_NIR_V1": ("50_多模态与报告", "audit"),
    "J_Data_NIR_SAMPLED_BATCH": ("50_多模态与报告", "audit"),
    "J_Data_NIR_SAMPLED_PILOT": ("50_多模态与报告", "audit"),
    "J_Data_NIR_TEACHER_STAGE1": ("50_多模态与报告", "historical"),
    "归档_历史版本": ("90_历史归档", "historical"),
    "08_旧批次-SUB001-FULL": ("90_历史归档", "historical"),
    "08_SUB001-FULL": ("90_历史归档", "historical"),
    "07_REST-3min": ("90_历史归档", "historical"),
    "08_旧批次-REST-3min": ("90_历史归档", "historical"),
}

CANONICAL_OUTPUT_BUCKETS = {
    "00_索引与审计",
    "10_质量控制",
    "20_生理金标准验证",
    "30_预实验与原型",
    "40_正式实验",
    "50_多模态与报告",
    "90_历史归档",
    "99_运行临时",
}


def directory_stats(path: Path) -> tuple[int, int]:
    files = 0
    bytes_total = 0
    for item in path.rglob("*"):
        if item.is_file():
            files += 1
            bytes_total += item.stat().st_size
    return files, bytes_total


def classify_output(name: str) -> tuple[str, str, str]:
    if name in CANONICAL_OUTPUT_BUCKETS:
        return name, "mixed_child_assets", "canonical_container"
    if name in OUTPUT_BUCKETS:
        bucket, evidence = OUTPUT_BUCKETS[name]
        return bucket, evidence, "mapped"
    if name.startswith("J_Data_SUB"):
        return "40_正式实验", "exploratory", "group_subject_level_outputs_before_move"
    return "99_运行临时", "review_required", "unmapped_manual_review"


def row_for(path: Path, scope: str) -> dict[str, str | int]:
    files, size = directory_stats(path) if path.is_dir() else (1, path.stat().st_size)
    if scope == "output":
        bucket, evidence, status = classify_output(path.name)
    else:
        bucket, evidence, status = "repository_root", "n/a", "root_audit_only"
    return {
        "scope": scope,
        "source_name": path.name,
        "source_path": str(path),
        "suggested_bucket": bucket,
        "evidence_status": evidence,
        "migration_status": status,
        "file_count": files,
        "size_bytes": size,
        "git_policy": "ignored_reproducible_output" if scope == "output" else "check_gitignore_and_role",
        "audit_date": date.today().isoformat(),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="只读生成算法库结构审计 CSV")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    rows = []
    for entry in sorted(ROOT.iterdir(), key=lambda p: p.name.casefold()):
        if entry.name == ".git":
            continue
        rows.append(row_for(entry, "repository_root"))
    output = ROOT / "output"
    if output.exists():
        for entry in sorted(output.iterdir(), key=lambda p: p.name.casefold()):
            rows.append(row_for(entry, "output"))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    fields = list(rows[0]) if rows else ["scope", "source_name"]
    with args.output.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    print(f"wrote {len(rows)} rows: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
