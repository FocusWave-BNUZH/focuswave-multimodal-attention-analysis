# 2026-10-14 剩余分支收敛执行记录

任务 `FW-GIT-BRANCH-CONSOLIDATE-20261014`；用户明确授权执行上轮逐分支结论。完整旧版本已核验到原精确提交和整棵文件树，接下来关闭旧审阅与移除远端分支标签。历史科学实现不合入当前主线。

## 执行后保留的活动分支

| 保留分支 | 用途 |
|---|---|
| `main` | 中央当前主线 |
| `fix/issue33-probe-contract` | 尚未关闭的问题33修复与证据 |

## 已固定的完整历史版本

| 原分支 | 完整历史版本 | 精确提交 |
|---|---|---|
| `codex/behavior-formal-v3-rejected-baseline-fix` | [固定版本](https://github.com/greenboo26/focuswave-multimodal-attention-analysis/tree/archive/20261014/behavior-formal-v3-rejected-baseline-fix) | `8a23f6a27cae643eda366696672da64d3ce479a4` |
| `codex/behavior-science-v3-baseline` | [固定版本](https://github.com/greenboo26/focuswave-multimodal-attention-analysis/tree/archive/20261014/behavior-science-v3-baseline) | `64b7394e7aa621242c62684ff5a04b14261e2c76` |
| `codex/formal-bb-behavior-v1` | [固定版本](https://github.com/greenboo26/focuswave-multimodal-attention-analysis/tree/archive/20261014/formal-bb-behavior-v1) | `0423beba1813bf81b16d4d7d7e9c7ac4763920e6` |
| `codex/formal-bb-probe-window-fix` | [固定版本](https://github.com/greenboo26/focuswave-multimodal-attention-analysis/tree/archive/20261014/formal-bb-probe-window-fix) | `9e2dea90306552d38377a6bf9cbe6c3561afa4b3` |
| `codex/q1-questionnaire-criterion-validity-20260826` | [固定版本](https://github.com/greenboo26/focuswave-multimodal-attention-analysis/tree/archive/20261014/q1-questionnaire-criterion-validity-20260826) | `d8a2870766b011da3d62b85d33dd10652d2db4b4` |
| `master` | [固定版本](https://github.com/greenboo26/focuswave-multimodal-attention-analysis/tree/legacy/mmwave-hrv-master-pre-focuswave-20260826) | `96525b19422b34291e4d87747fef214d1fec60d7` |

本机旧q1/生产分支和未提交迁移内容保持原状；远端收尾不代表本地工作副本已迁移。旧分支不再作为推送目标，恢复使用上表完整固定版本。

执行状态：完整版本保护已核验，实际关闭/删除及最终回读将在本记录追加。
