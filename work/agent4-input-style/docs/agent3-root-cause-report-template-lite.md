---
title: Agent 3 Root Cause Diagnosis Report Lite
report_type: performance_root_cause
report_version: v1-lite
primary_consumers:
  - human_reviewer
  - agent4_optimizer
phase_compatibility:
  - phase_1
  - phase_2
  - phase_3
---

# Agent 3 性能异常根因诊断报告（精简版）

> 目标：只回答 5 个问题
> 1. 异常是什么
> 2. 最强证据是什么
> 3. 最可能根因是什么
> 4. 结论哪里还不稳
> 5. Agent 4 下一步做什么

## 1. 基本信息

| 字段 | 内容 |
| --- | --- |
| Diagnosis ID | `<diag-YYYYMMDD-XXX>` |
| Run ID | `<test-run-id>` |
| 当前阶段 | `<Phase 1 / Phase 2 / Phase 3>` |
| 代码版本 | `<commit / branch / tag>` |
| 基线版本 | `<baseline id>` |
| 总体状态 | `<confirmed / probable / insufficient_evidence / false_alarm>` |
| 总体置信度 | `<0.00 - 1.00>` |

## 2. 一句话摘要

- 异常结论：`<哪类性能异常，发生在什么场景>`
- 影响对象：`<RV / ARM / both + workload/testcase>`
- 最可能根因：`<一句话>`
- 是否建议交给 Agent 4：`<yes / no / conditional>`

## 3. 关键证据

### 3.1 指标证据

| 指标 | RV | ARM | Baseline | 异常点 |
| --- | --- | --- | --- | --- |
| Latency | `<...>` | `<...>` | `<...>` | `<...>` |
| IPC | `<...>` | `<...>` | `<...>` | `<...>` |
| Cache Miss Rate | `<...>` | `<...>` | `<...>` | `<...>` |

### 3.2 热点证据

| 热点函数 | 文件/模块 | RV Sample % | ARM Sample % | 说明 |
| --- | --- | --- | --- | --- |
| `<...>` | `<...>` | `<...>` | `<...>` | `<...>` |

### 3.3 代码 / 知识证据

- 相关代码位置：`<file:function or symbol>`
- 相关知识结论：`<历史案例 / 架构知识 / 已知模式>`
- 证据说明：`<为什么这些内容支撑当前根因>`

## 4. 根因判断

- 最可能根因：`<一句话>`
- 根因类型：`<code path / arch gap / config mismatch / infra noise / unknown>`
- 为什么这样判断：`<用 2-4 句把指标、热点、代码串起来>`
- 备选解释：`<如果有，写 1-2 个>`

## 5. 风险与缺口

- 当前缺口：`<缺哪些数据或哪些地方还不能完全解释>`
- 风险等级：`<high / medium / low>`
- 是否需要人工复核：`<yes / no>`
- 人工复核重点：`<最值得怀疑或最需要确认的点>`

## 6. 交给 Agent 4 的动作

| 字段 | 内容 |
| --- | --- |
| 是否进入优化 | `<yes / no / conditional>` |
| 优先处理位置 | `<module / file / function>` |
| 推荐第一动作 | `<优化 / 插桩 / 对比 patch / 补实验>` |
| 推荐验证方式 | `<如何验证优化是否成立>` |
| 变更风险 | `<high / medium / low>` |

## 7. 最终裁决

- 最终状态：`<confirmed_root_cause / probable_root_cause / insufficient_evidence / false_alarm>`
- 是否允许自动流转到 Agent 4：`<yes / no>`
- 若不允许，原因：`<证据不足 / 环境不一致 / 结论冲突 / 复现不稳定>`
