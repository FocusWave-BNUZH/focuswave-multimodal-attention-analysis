# Issue #13 Mainline B：心理测量信效度 evidence matrix v1

状态：`PARTIAL`。已有 behavior/Probe/questionnaire/repeated-participant 资产已实际复用；没有等待 NIR/RGB/mmWave，也未重复运行 Behavior + mmWave 增量分析。

## 口径

- 状态指标：Probe label/vigilance、场次级事后走神比例及其行为效标；结果单位是 probe 或 session，不能直接解释为稳定个体能力。
- 稳定个体指标：当前没有足够的重复测量信度或成熟多题量表证据；trait-like 单题只保留为候选背景指标。
- `PARTIAL` 表示方向/效标支持存在，但仍受回顾性单题、时间结构、重复 session 或未完成结构效度限制；`BLOCKED` 表示不具备正式包装所需证据，不表示“无效”。

## 结论

1. 最适合正式产品报告的状态层候选是：Probe label 1/2/3/4 的时间敏感轨迹、Probe vigilance、以及经过时间/阶段校正的行为关联；它们是状态/过程指标。
2. 场次级事后走神比例与 label 1、label 2/3/4 和 commission error 具有方向性关联，属于外部效标/收敛支持，不是标准化量表效度。
3. 没有足够证据支持“稳定专注能力/特质分数”：没有成熟多题量表、内部一致性、因子结构或正式 test–retest ICC。
4. 重复参与者 grouped LOSO 只说明泛化边界；B0 behavior/context 不应被 mmWave M1 增量替代，不能把它当作心理测验信度。

## 证据明细

完整字段见同目录 CSV；每行保留 n、分析单位、方向、效应、95% CI、p/q、状态和产品含义。

| ID | 构念 | n(session/obs/participant) | 单位 | 效应 | 95% CI | p/q | 状态 | 产品含义 |
|---|---|---:|---|---|---|---|---|---|
| Q1-PROBE-L1 | 问卷走神比例 vs Probe label 1 完全任务聚焦比例 | 67/67/46 | session | Spearman rho=-0.581 | [-0.735, -0.409] | 2.494e-07/1.746e-06 | PARTIAL | 可作为场次级外部效标；不能作为实时状态验证 |
| Q1-PROBE-L2 | 问卷走神比例 vs Probe label 2 任务相关干扰比例 | 67/67/46 | session | Spearman rho=0.534 | [0.352, 0.690] | 3.204e-06/1.121e-05 | PARTIAL | 支持状态构念的收敛方向，但不升级为量表效度 |
| Q1-PROBE-L3 | 问卷走神比例 vs Probe label 3 大脑空白比例 | 67/67/46 | session | Spearman rho=0.362 | [0.133, 0.567] | 0.002587/0.006035 | PARTIAL | 支持相关状态证据；保持四类语义，不并入 mind-wandering 总类 |
| Q1-PROBE-L4 | 问卷走神比例 vs Probe label 4 走神比例 | 67/67/46 | session | Spearman rho=0.330 | [0.126, 0.514] | 0.006345/0.0111 | PARTIAL | 支持状态构念的方向性关联；不替代 Probe 事件测量 |
| Q1-BEH-COMMISSION | 问卷走神比例 vs commission error rate | 67/67/46 | session | Spearman rho=0.260 | [0.014, 0.494] | 0.03394/0.04751 | PARTIAL | 可进入产品报告的外部效标桥接；效应较小，不能单独作稳定能力结论 |
| Q1-BEH-PREEMPT | 问卷走神比例 vs preempt rate | 67/67/46 | session | Spearman rho=0.154 | [-0.161, 0.462] | 0.213/0.2485 | PARTIAL | 不作为主产品指标；仅保留为弱/不精确辅助证据 |
| Q1-BEH-RT | 问卷走神比例 vs Go-trial median RT | 67/67/46 | session | Spearman rho=-0.068 | [-0.351, 0.196] | 0.5819/0.5819 | PARTIAL | 当前不支持方向性产品结论；场次级 RT variability 尚未有既有字段 |
| Q1-ORD-PROBE | 有序模型：非完全任务聚焦比例 vs 问卷走神等级 | 67/67/46 | session; participant-cluster robust SE | OR per 1 SD=4.01 | [2.10, 7.66] | 2.552e-05/7.657e-05 | PARTIAL | 可作为收敛/效标支持；不能解释为逐 Probe 状态准确率 |
| Q1-ORD-ERROR | 联合有序模型：commission error vs 问卷走神等级 | 67/67/46 | session; participant-cluster robust SE | OR per 1 SD=1.79 | [1.12, 2.85] | 0.01401/0.01401 | PARTIAL | 保留为模型依赖的辅助效标证据 |
| Q1-ORD-RT | 联合有序模型：median RT vs 问卷走神等级 | 67/67/46 | session; participant-cluster robust SE | OR per 1 SD=1.74 | [1.27, 2.39] | 0.0005424/0.0008136 | PARTIAL | 仅作为探索性条件关联；不单独进入产品主结论 |
| BEHAV-LABEL1-TIME | Probe label 1 随 block 内 progress 的变化 | 70/1400/46 | probe; participant-clustered GEE | OR=0.43 | [0.25, 0.74] | 0.002527/0.00722 | PARTIAL | 支持状态测量对任务进程敏感；产品应报告时间/阶段校正后的状态指标 |
| BEHAV-VIG-TIME | Probe vigilance 随 task progress 的变化 | 70/1400/46 | probe; participant-clustered GEE | OR=0.26 | [0.14, 0.47] | 9.623e-06/6.415e-05 | PARTIAL | 支持警觉状态的时间敏感性；不是稳定个体能力信度 |
| BEHAV-VIG-ERROR | vigilance 与 Probe 前 10 s error rate | 70/1400/46 | probe; participant-clustered GEE | OR=0.68 | [0.56, 0.83] | 9.875e-05/0.0003646 | PARTIAL | 是行为外部效标支持；适合状态层，不适合 trait 包装 |
| REPEAT-STATE-ORDER | 重复 session：label 1 的 session-order 主效应 | 70/1400/46 | probe; participant random-intercept mixed model | primary OR=0.71; sensitivity=0.95 | primary [0.66, 0.77]; sensitivity [0.88, 1.03] | primary 4.143e-19; sensitivity 0.1937/primary 3.314e-18; sensitivity 0.2634 | PARTIAL | 不能作为稳定 trait 信度；至少需要 session-order/进度校正 |
| REPEAT-STATE-INTERACTION | 重复 session：label 1 的 progress × session-order | 70/1400/46 | probe; participant random-intercept mixed model | primary OR=1.57; sensitivity=1.69 | primary [1.39, 1.77]; sensitivity [1.48, 1.92] | primary 6.34e-13; sensitivity 8.112e-15/primary 2.536e-12; sensitivity 6.489e-14 | PARTIAL | 状态指标对任务进程的变化在重复 session 中方向一致；仍不是 test-retest ICC |
| REPEAT-ERROR-ORDER | 重复 session：pre10 error 的 session-order | 70/1400/46 | probe; participant random-intercept mixed model | primary OR=1.16; sensitivity=1.13 | primary [1.11, 1.21]; sensitivity [1.08, 1.18] | primary 7.233e-11; sensitivity 5.126e-07/primary 1.929e-10; sensitivity 1.367e-06 | PARTIAL | 行为表现存在练习/场次结构；产品报告应避免把跨场次绝对分数当个人能力 |
| REPEAT-GROUPED-LOSO | participant-disjoint repeated-participant LOSO：behavior baseline vs mmWave M1 | 71/1317/46 | probe; held-out repeat_participant_id | B0 AUC=0.656; M1 AUC=0.609 | B0 [0.609, 0.706]; M1 [0.548, 0.673] | NA (bootstrap CI only)/NA | PARTIAL | 重复被试外推仍应以 behavior/context 为锚；不把 mmWave 增量包装成心理测验信度证据 |
| MEASURE-STRUCTURE | 正式问卷多题量表、反向计分、alpha/omega、因子结构 | 134 formal questionnaire rows/212 item/design records/未确定 | item inventory / respondent source | NA | NA | NA/NA | BLOCKED | 不得把单题组合成标准化量表；不得宣称内部一致性或结构效度 |
| TRAIT-SINGLE-ITEM | 自评专注力、平时持续专注时长单题 | 未形成可分析桥接/未形成可分析桥接/未形成可分析桥接 | session-level retrospective single item | NA | NA | NA/NA | BLOCKED | 只能作为描述性背景/候选稳定个体指标；当前不得包装为能力/特质分数 |
| STATE-ITEM-BRIDGE | 正式版第4题总体走神比例单题 | 67/67/46 | session-level retrospective single item | 见 Q1-PROBE/Q1-BEH 行 | 见 Q1-PROBE/Q1-BEH 行 | 见 Q1-PROBE/Q1-BEH 行/见 Q1-PROBE/Q1-BEH 行 | PARTIAL | 可作为场次级主观外部效标/报告字段；不能复制到实时 probe/window 状态 |
