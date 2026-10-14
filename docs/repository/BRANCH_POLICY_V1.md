# Branch policy V1

The formal repository branch surface is `main` with `master` retained during the rollback window. External producer refs are recorded by exact commit, not mirrored as permanent branches. Task branches are ephemeral and are retired after merge/close and immutable preservation checks. Governance/review branches are retired only after their successor documents are present on `main`.

2026-10-13 当前分支用途、归档位置和实际收尾以 [V3执行记录](BRANCH_RETIREMENT_EXECUTION_V3.md) 为准；V1/V2旧矩阵与记录保留当时原文。

2026-10-14：用户已授权收尾旧候选、旧报告及旧基线。当前分支表与完整恢复位置以 [V4执行记录](BRANCH_RETIREMENT_EXECUTION_V4.md) 为准；master旧基线通过既有固定标签保留，q1旧报告通过完整新标签保留。本机未迁移现场不切换、不重置。
