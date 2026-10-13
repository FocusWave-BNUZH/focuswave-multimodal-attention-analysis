# 厚粲杯科研工作区总账

更新时间：2026-08-26

## 当前仓库

| 资产 | 本地路径 | 当前分支 | 当前 HEAD | 远程 |
|---|---|---|---|---|
| mmwave-hrv-analysis | `D:\Project\厚粲杯\08_算法` | `codex/audit-j-target-lock-gate` | 以提交时实际 `git rev-parse HEAD` 为准 | `git@github.com:greenboo26/mmwave-hrv-analysis.git` |
| FocusWave | `D:\Project\厚粲杯\05_实验\FocusWave` | 本轮未修改 | 本轮未修改 | 本轮未同步 |

## C1 封存状态

`C1D_NO_MATERIAL_IMPROVEMENT_STOP_HRV`

含义：在当前比赛周期内停止继续投入毫米波逐搏 IBI/HRV 算法开发。不得解释为“RS6240 无法测 HRV”。C1c 确定性重放已通过，C1d 后端 pilot 未达到冻结成功门槛。

### C1 代码

- `scripts/run_c1c_mmhrv_pilot.py`
- `scripts/replay_c1c_assets.py`
- `scripts/run_c1d_radarbeat_backend_pilot.py`

### C1 公开交接资产

仓库内 `docs/results/c1_pilot/` 只保存代码审计所需的紧凑报告、CSV/JSON 结果和运行 manifest：

- `C1C_PILOT_REPORT.md`
- `C1D_PILOT_REPORT.md`
- `c1c_metrics_primary.csv`
- `c1c_metrics_long.csv`
- `c1d_metrics_primary.csv`
- `c1d_metrics_long.csv`
- `c1d_decision.json`
- `c1c_run_manifest.json`

### C1 本地大资产，不上传 GitHub

- `D:\Project\厚粲杯\11_数据\derived\c1c_mmhrv_pilot_v1\97793\c1c_waveforms_replayed.npz`
- `D:\Project\厚粲杯\11_数据\derived\c1c_mmhrv_pilot_v1\9779\c1c_waveforms_replayed.npz`
- `D:\Project\厚粲杯\11_数据\derived\c1c_mmhrv_pilot_v1\97795\c1c_waveforms_replayed.npz`
- J 盘 raw ADC、ECG 原始文件、完整 derived 目录和各场诊断图

这些路径用于本地复核，不构成 GitHub 可获取资产。

## C2a 状态

目标：只读审计正式心理状态标签、probe-centered 样本单位、重复被试分组、窗口覆盖和模态 coverage。不训练模型、不提取大规模 RGB/NIR 特征、不重做 HRV。

状态：`PENDING_C2A_AUDIT`

C2a 完成后必须登记以下本地产物的具体路径，并将匿名汇总/方法报告复制到仓库；行级 manifest、被试映射和任何敏感数据只能保留在本地 derived 目录。

