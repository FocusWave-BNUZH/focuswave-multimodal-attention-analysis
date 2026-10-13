# Branch policy V1

The formal repository branch surface is `main` with `master` retained during the rollback window. External producer refs are recorded by exact commit, not mirrored as permanent branches. Task branches are ephemeral and are retired after merge/close and immutable preservation checks. Governance/review branches are retired only after their successor documents are present on `main`.

2026-10-13 当前分支用途、归档位置和实际收尾以 [V3执行记录](BRANCH_RETIREMENT_EXECUTION_V3.md) 为准；V1/V2旧矩阵与记录保留当时原文。
