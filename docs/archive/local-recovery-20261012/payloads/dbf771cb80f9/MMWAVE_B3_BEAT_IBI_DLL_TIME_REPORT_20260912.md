# mmWave 逐搏级验证扩样报告：5 场次 16 blocks（2026-08-31）

Status: `PARTIAL / HRV_BLOCKED`（扩样复核后维持）；这是 beat-timing 有效性审计，不是正式 HRV 结果。

## 1. 直接结论

- 08-30 的 3 场次 8 blocks 逐搏验证按同一固定评估契约扩充到 5 场次 16 blocks（新增 97796/97794 各 4 blocks；97792 判 not_estimable 跳过，见第 2 节清点）。
- 主容差 ±75 ms 一对一最近邻匹配：pooled `297/1364` ECG R 峰 vs `1193` 雷达峰；灵敏度 `0.217742`，精确率 `0.248952`。
- 旧 3 场次 8 窗在新运行中的数值：结构/匹配字段存在不一致：97793/block1.beat_derived_mean_hr_bpm: old=18.569144271934803 new=23.719898932604547；97793/block1.beat_precision: old=0.2638888888888889 new=0.3333333333333333；97793/block1.beat_sensitivity: old=0.2375 new=0.3；97793/block1.beat_vs_spectral_hr_delta_bpm: old=-33.02417894506064 new=-27.856032299487143；97793/block1.existing_spectral_hr_bpm: old=51.593323216995444 new=51.57593123209169；97793/block1.extra_radar_beats_n: old=53.0 new=48
- 旧 3 场次 pooled 灵敏度/精确率（从旧 CSV 复算）= `0.170243` / `0.210619`；新增 2 场次 8 窗 pooled = `0.236090` / `0.262542`。
- 结论：`HRV_BLOCKED` 在扩样后**加强**（新增场次匹配率更低，pooled 灵敏度 0.170 → 0.218，精确率 0.211 → 0.249；数字依据见第 4/5 节）。
- 本运行不计算任何正式 RMSSD/SDNN/LF/HF，不授权新检测器、调参或 HRV 指标晋升。

## 2. 5 场次 NPZ / marker 只读清点

- v3.1.1 NPZ 根：`08_算法/output/20_生理金标准验证/06_HR_COURSE_99_CORRECTED_GATE`（旧 3 场次 NPZ sha256 与 08-30 MANIFEST 逐位一致，确认同源）。

| 场次 | NPZ/JSON | 帧数 | heart_peaks | timestamps 行数一致 | 命名坑 | complete blocks |
|---|---:|---:|---:|---:|---|---:|
| 97793 | 有 | 162924 | 1991 | 是 | 无 | block1/2 |
| 9779 | 有 | 155557 | 1967 | 是 | 无 | block1/2 |
| 97795 | 有 | 140648 | 1811 | 是 | acq 误写 97995.acq | block1-4 |
| 97796 | 有 | 141395 | 1793 | 是 | 无 | block1-4 |
| 97794 | 有（文件名前缀 97994） | 133139 | 1629 | 是 | 目录/beh/mmwave 前缀 97994 | block1-4 |
| 97792 | **无 NPZ** | — | — | — | 仅 baseline+practice | 4 block 全 not_recorded |

- 97792 判定：`not_estimable + reason=仅采集 baseline+practice（events.csv 无 block1-4 段事件、无 v3.1.1 NPZ 输出）`，如实跳过。
- marker 对齐：16 个 complete block 中 15 个 marker 序列 exact；唯一非 exact 为 97793/block1（index 73 event 103 vs physical 102，与 08-30 口径一致），其 ECG affine fit p95 2.67 ms 仍可用。新增 97796/97794 的 8 个 block 全部 exact（fit p95 2.07–3.40 ms）。

## 3. 固定评估契约（与 08-30 一致，未改）

- 雷达侧：现有全记录 v3.1.1 NPZ `heart_peaks`，经权威 DLL 时间行映射；不改任何检测器参数。
- ECG 侧：block-local affine event-marker 映射 + 固定 `gold_standard_qa.py` 参数（0.5–40 Hz / 0.30 s / prominence 0.25）；保留原始 R 峰做匹配审计。
- 匹配：一对一最近邻，无逐窗 lag 搜索；主容差 ±75 ms，敏感性 ±50/100/150 ms。
- 窗口：每 block 一个确定性 60 s 区间（block 开始 +30 s 起、结束 -30 s 前），与 08-30 相同。
- IBI：仅匹配对内相邻间隔；常数偏移抵消且不用于选峰。
- 复现方式：扩展脚本直接 import 08-30 模块并调用其 `evaluate_window`（同一段代码），契约常量同源。

## 4. 每 block 匹配表（16 blocks，±75 ms）

| subject | block | ECG R 峰 | 雷达峰 | matched | sensitivity | precision | paired-IBI MAE (ms) | timing MAE (ms) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 97793 | block1 | 80 | 72 | 24 | 0.3000 | 0.3333 | 51.4 | 35.6 |
| 97793 | block2 | 82 | 75 | 5 | 0.0610 | 0.0667 | 47.7 | 28.3 |
| 9779 | block1 | 83 | 68 | 17 | 0.2048 | 0.2500 | 54.5 | 33.6 |
| 9779 | block2 | 90 | 73 | 19 | 0.2111 | 0.2603 | 61.4 | 33.0 |
| 97795 | block1 | 88 | 74 | 17 | 0.1932 | 0.2297 | 39.9 | 34.8 |
| 97795 | block2 | 90 | 77 | 22 | 0.2444 | 0.2857 | 49.6 | 34.4 |
| 97795 | block3 | 93 | 78 | 21 | 0.2258 | 0.2692 | 54.0 | 31.0 |
| 97795 | block4 | 93 | 78 | 15 | 0.1613 | 0.1923 | 40.4 | 31.9 |
| 97796 | block1 | 93 | 75 | 7 | 0.0753 | 0.0933 | 102.5 | 46.5 |
| 97796 | block2 | 89 | 73 | 25 | 0.2809 | 0.3425 | 55.1 | 43.0 |
| 97796 | block3 | 87 | 76 | 40 | 0.4598 | 0.5263 | 42.0 | 32.3 |
| 97796 | block4 | 84 | 75 | 30 | 0.3571 | 0.4000 | 40.9 | 36.7 |
| 97794 | block1 | 81 | 78 | 12 | 0.1481 | 0.1538 | 32.3 | 34.4 |
| 97794 | block2 | 77 | 73 | 14 | 0.1818 | 0.1918 | 38.3 | 39.2 |
| 97794 | block3 | 80 | 76 | 16 | 0.2000 | 0.2105 | 43.3 | 39.1 |
| 97794 | block4 | 74 | 72 | 13 | 0.1757 | 0.1806 | 52.8 | 37.1 |

## 5. 分场次 pooled 汇总

| subject | 窗数 | ECG R 峰 | 雷达峰 | matched | sensitivity | precision | paired-IBI MAE 中位 (ms) | timing MAE 中位 (ms) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 97793 | 2 | 162 | 147 | 29 | 0.1790 | 0.1973 | 49.6 | 32.0 |
| 9779 | 2 | 173 | 141 | 36 | 0.2081 | 0.2553 | 57.9 | 33.3 |
| 97795 | 4 | 364 | 307 | 75 | 0.2060 | 0.2443 | 45.0 | 33.1 |
| 97796 | 4 | 353 | 299 | 102 | 0.2890 | 0.3411 | 48.5 | 39.8 |
| 97794 | 4 | 312 | 299 | 55 | 0.1763 | 0.1839 | 40.8 | 38.1 |
| **5 场次 pooled** | **16** | **1364** | **1193** | **297** | **0.2177** | **0.2490** | **48.7** | **34.6** |

5 场次 vs 3 场次对比：

| 指标 | 旧 3 场次 8 窗（08-30） | 扩样 5 场次 16 窗 | 方向 |
|---|---:|---:|---|
| pooled matched | 119 | 297 | 窗数翻倍、matched 未同倍增长 |
| pooled sensitivity | 0.170243 | 0.217742 | 下降（--4.7 百分点） |
| pooled precision | 0.210619 | 0.248952 | 下降（--3.8 百分点） |
| per-window 中位 sensitivity | 0.156091 | 0.202410 | 下降 |
| per-window 中位 precision | 0.188922 | 0.239865 | 下降 |
| paired-IBI MAE 中位 (ms) | 46.258 | 48.652 | 稳定 |
| 配对子集 timing MAE 中位 (ms) | 35.615 | 34.608 | 稳定 |

## 6. 容差敏感性（5 场次 pooled）

| tolerance | pooled matched | ECG R-peaks | radar peaks | sensitivity | precision |
|---:|---:|---:|---:|---:|---:|
| 50 ms | 208 | 1364 | 1193 | 0.152493 | 0.174350 |
| 75 ms | 297 | 1364 | 1193 | 0.217742 | 0.248952 |
| 100 ms | 397 | 1364 | 1193 | 0.291056 | 0.332775 |
| 150 ms | 578 | 1364 | 1193 | 0.423754 | 0.484493 |

## 7. 结论

`HRV_BLOCKED` **维持且加强**。理由（数字）：

- 扩样后 ±75 ms pooled 灵敏度 0.170 → 0.218、精确率 0.211 → 0.249，新增 97796/97794 场次的匹配质量比旧 3 场次更低（新增 8 窗 pooled 灵敏度 0.236 / 精确率 0.263），说明低匹配率不是旧场次的个例，而是该 beat 证据链的系统性现象。
- 配对子集 timing MAE 中位 34.6 ms 与 paired-IBI MAE 中位 48.7 ms 与旧结果同量级，但这是"匹配成功子集"上的条件值，不能补偿 0.78 的漏检率。
- 逐搏级证据仍不足以支持任何 HRV 指标晋升；本报告不计算 RMSSD/SDNN/LF/HF，不授权新检测器、HRV 窗口调参或正式 HRV 指标计算。

## 8. 资产与溯源

- 脚本（Git-safe）：`scripts/maintenance/run_mmwave_beat_level_validation_20260831_expanded.py`
- 逐窗明细（local-only，不进 Git）：`11_数据/derived/mmwave_beat_level_validation_20260831_5subjects_expanded/MMWAVE_B3_BEAT_IBI_DLL_TIME_PER_BLOCK_LOCAL_ONLY.csv`
- 汇总/容差/manifest：`docs/results/2026-08-30_MMWAVE_HRV_BEAT_LEVEL_GATE/` 下 EXPANDED 三件套（旧 08-30 四件套保留未覆盖）
- Manifest：`MMWAVE_B3_BEAT_IBI_DLL_TIME_MANIFEST_20260912.json`（含 NPZ sha256、源码 hash、契约与边界）
