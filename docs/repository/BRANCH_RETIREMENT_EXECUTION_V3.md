# 2026-10-13 分支生命周期收尾记录（V3）

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

执行状态：归档已合入后，按逐分支实时引用与完整恢复核验收尾；最终现场核验记录追加于本文件。

## 执行后核验（2026-10-13）

归档整合提交 `8ca0ed7d04d92c7511ca3f5d8c49f309bdfee7c1` 已推送。远端分支已按上表收尾，当前保留 8 个分支；本仓库补录分支已不存在。需保留的历史标签已回读为原精确提交，已合并分支全部由默认分支历史保存。载荷 252 份内容校验通过，本地工作副本、索引和HEAD（当前检出提交）保持不变。当前代码、配置、结果和图表未改；不重跑研究数据。
