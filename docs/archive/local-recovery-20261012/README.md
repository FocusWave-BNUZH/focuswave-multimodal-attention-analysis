# 本机历史源码与过程证据补录

任务日期：2026-10-12至13。仓库：`greenboo26/focuswave-multimodal-attention-analysis`。本补录共252个不同内容的历史原文快照。

逐项与远端当前分支及历史内容比较后，保留尚未发布且有复现价值的源码、测试、方法/失败/运行记录。目录名work或临时脚本名称不决定其价值；真实研发脚本与复核过程按内容保留，测试生成物与无用诊断不纳入。

本目录用于历史追溯，不改变当前正式入口、参数、样本、统计分折或冻结结论。原始/行级数据、身份财务信息、凭据、模型二进制与运行缓存仍留在本机，未在此发布。原文保留当时上下文和相对路径；恢复需按原位置、版本与输入/模型契约重建，孤立快照不等于完整可执行管线。

manifest.json记录原位置、来源提交及安全散列算法256位（Secure Hash Algorithm 256-bit [SHA-256]）；verification.json记录字节、源码语法及结构检查。没有重跑真实研究数据，也没有重新验证心理/生理构念或性能。

## 2026-10-13 默认分支归档与分支收尾

2026-10-13；任务 `FW-GIT-REMOTE-TIDY-20261013`。默认分支仍为 `main`。
本轮只整合历史归档与管理引用，不修改现行代码、配置、科学方法、结果或图表。分支数按远端实际引用核验。

### 整理后保留的分支

| 分支 | 用途 |
|---|---|
| `codex/behavior-formal-v3-rejected-baseline-fix` | 未完成代码审阅所需的分支/基线 |
| `codex/behavior-science-v3-baseline` | 未完成代码审阅所需的分支/基线 |
| `codex/formal-bb-behavior-v1` | 未完成代码审阅所需的分支/基线 |
| `codex/formal-bb-probe-window-fix` | 未完成代码审阅所需的分支/基线 |
| `codex/q1-questionnaire-criterion-validity-20260826` | 本地在用历史报告工作线，独有版本仍需保留 |
| `fix/issue33-probe-contract` | 未关闭问题33关联分支，保留独有修复证据 |
| `main` | 当前主线 |
| `master` | 已有回退政策保留的历史基线 |

### 收尾分支与完整恢复位置

| 原分支 | 原提交 | 恢复位置 |
|---|---|---|
| `codex/local-process-recovery-20261012` | `b42f137998aa3e7dfe4097f101da6ba6785819f5` | 当前默认分支的合并提交历史 |
| `codex/mmwave-estimator-improvement-v1-20260912` | `da84260c87ac581d2a806b06878a33472e0160fc` | 当前默认分支完整提交历史 |
| `codex/mmwave-formal-reanalysis-v2` | `d87229afe071f23450728a6d617ec82317e6c9df` | [固定历史版本标签](https://github.com/greenboo26/focuswave-multimodal-attention-analysis/tree/archive/20261013/mmwave-formal-reanalysis-v2) |
| `codex/mmwave-pre30s-selector-hr-20260831` | `2f606cb9332c319993264789061731dd67be064b` | 当前默认分支完整提交历史 |
| `codex/mmwave-producer-contract-provenance-m1-20260913` | `37f5d8e32fbc63fa3ba8bca05221b534089bcec9` | 当前默认分支完整提交历史 |
| `codex/mmwave-production-contract-hardening` | `fc682b491fcbeeb9bd1b030c8af9da33282d2846` | [固定历史版本标签](https://github.com/greenboo26/focuswave-multimodal-attention-analysis/tree/archive/20261013/mmwave-production-contract-hardening) |
| `codex/project-state-map-20260829` | `efb385fccdb8f0bd7c4c9c8b07bf1f242c6da047` | [固定历史版本标签](https://github.com/greenboo26/focuswave-multimodal-attention-analysis/tree/archive/20261013/project-state-map-20260829) |
| `codex/t0-vmd-fix` | `018d6f79ec410552ee6f59d6f9f5fb6e8151ce42` | 当前默认分支完整提交历史 |

整理策略：只有正在使用的主线、生产线和未完成审阅保留活动分支；已完成工作收进已有目录，旧实现以固定版本或提交历史追溯。一般文件整理不自动创建新分支，不强制推送、重写历史或切换本地工作副本。

历史文档中的原分支名保留当时上下文，当前定位以本节的固定版本链接和根目录当前入口为准。后续科学/生产使用仍须核对所属仓库、明确版本和现行契约。
