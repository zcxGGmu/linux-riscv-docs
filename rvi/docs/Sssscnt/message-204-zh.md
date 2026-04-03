# 状态敏感计数器（Sssscnt）扩展提案（中文翻译）

- 原文链接：https://lists.riscv.org/g/sig-datacenter/message/204?p=%2C%2C%2C20%2C0%2C0%2C0%3A%3Arelevance%2C%2Cposterid%3A7911087%2C20%2C2%2C0%2C118091000
- 原文标题：Proposal of State sensitive Counter(Sssscnt) Extension

## 提案人

- 姓名：Fengxue(Esther) Zhang，Bohua Kou
- 组织：阿里巴巴达摩院（Alibaba Damo Academy）

## 引言

“负载（Load）”通常被定义为 CPU 实际执行工作负载的时间占比。
但如果不按运行频率进行归一化，这个指标在本质上是不完整的。
CPU 可能 100% 时间都在运行，但若其频率仅为最大频率的 50%，则它并不是真正的 100% 负载。
为此，内核负载跟踪会按 CPU 实际运行频率对观测负载进行缩放 [1]。

问题在于：

- 现代 CPU 可能并不知道自己当前运行在什么频率上；该决策由 PuC 或硬件直接做出。

State Sensitive Counters 通过引入状态敏感计数器来解决该问题：CPU 活跃周期计数器、系统活跃周期计数器，以及系统周期计数器。

## 定义

我们提议 State Sensitive Counters。
该扩展命名为 `Sssscnt`（`Ss` 表示特权架构与 Supervisor 级扩展，`sscnt` 表示状态敏感计数器）。
状态敏感计数器单元在每个 CPU 中实现，提供面向系统电源管理用途的状态敏感计数器。

状态敏感计数器包含一组 64 位事件计数器：

- **CPU active cycle counter**：以 CPU 运行频率统计 CPU 核心周期；在 CPU 空闲状态下暂停计数。
- **System active cycle counter**：以固定参考频率统计系统级周期；在 CPU 空闲状态下暂停计数。
- **System cycle counter**：以固定参考频率统计系统周期；持续递增（可视为 `mtime` 的 shadow）。

本文场景请参考后文“背景与目标”章节。

## 背景

动态电压频率调整（DVFS）是嵌入式系统和计算机处理器广泛采用的电源管理技术，可依据工作负载与处理需求动态调整运行时钟频率。

采用 DVFS 的主要动机包括：提升能效、优化系统性能、管理热状态。
在空闲或低负载阶段降低频率可减少功耗，从而延长移动设备续航并降低大型系统总能耗。
此外，DVFS 通过降低功率耗散来控制系统温度，缓解过热风险并提升可靠性。
这项技术已成为现代处理器与嵌入式系统的标准能力 [1]。

在该场景下，合理选择 CPU 频率非常关键。
频率设置过高会带来不必要功耗（无论在手机还是数据中心）；
频率设置过低又会损害系统性能 [2]。

对于类似 `schedutil` 的现代 CPU 频率调节器，要在跨 CPU、跨性能状态下做出准确预测，需要“频率不变（frequency-invariant）且 CPU 不变（CPU-invariant）”的 PELT（Per Entity Load Tracking）信号。

因为：在 1GHz 下使用 CPU 50% 与在 2GHz 下使用 CPU 50% 并不等价；在 LITTLE 核心上跑 50% 与在大核上跑 50% 也不等价。
因此架构允许用两个比率来缩放时间增量：一个 DVFS 比率和一个微架构比率。

![](https://alidocs.dingtalk.com/core/api/resources/img/5eecdaf48460cde5220dff77eff77c799399f43ed1ddf27f75b8339e1c4c2483d08509556868857aa156a98577f418d56ae1d5eeba82c21ed8ccd372804c0a102a3e6ca42731151b66db7f35d17d81cf6883e47f3058b297?tmpCode=2f34769f-3844-4ee7-ac58-5cd78402aa31)

对于简单 DVFS 架构（软件完全控制），该比率可直接计算为：

```text
          f_cur
r_dvfs := -----
          f_max
```

对于由硬件控制 DVFS 的更动态系统，可使用硬件计数器（Intel APERF/MPERF、ARMv8.4-AMU）提供该比率。
以 Intel 为例：

```text
         APERF
f_cur := ----- * P0
         MPERF

           4C-turbo;  if available and turbo enabled
f_max := { 1C-turbo;  if turbo enabled
           P0;        otherwise

                  f_cur
r_dvfs := min( 1, ----- )
                  f_max
```

结果是：上述 `running` 与 `runnable` 指标将不再依赖 DVFS 与 CPU 类型。
换言之，它们可以在不同 CPU 之间迁移并比较 [3]。

因此，实时可见 CPU 实际运行频率是不可妥协的。
但在现代 SoC 中，应用处理器（AP）核心存在关键约束：它通常只有“请求频率”的权限。
最终频率由硬件电源控制器（PuC）基于温度、功耗与策略约束自主决定，AP 无法直接读取。
要获得实际生效频率，AP 必须发起显式查询（如 mailbox、SMC 或寄存器轮询），这会引入延迟、软件开销和数据陈旧风险。
这种架构分离虽有助于硬件强制电源管理的稳健性，但会直接增加 DVFS 决策难度，并要求算法具备延迟感知能力。

## 目标

我们的目标是：为 AP 核心建立对硬件强制频率的低延迟、无陈旧可见性。
即把“高成本的同步查询”变为“近乎瞬时的读取能力”。
这既保留 PuC 的强制控制权，也为 DVFS 算法提供及时数据，以实现准确负载缩放与快速 governor 决策。

1. 处理器运行频率按如下公式计算：

![](https://lists.riscv.org/g/sig-datacenter/attachment/204/0)

1. 处理器归一化利用率按如下公式计算：

![](https://lists.riscv.org/g/sig-datacenter/attachment/204/1)

以上可通过架构定义的 `arch_sccale_cpu_capacity()` 回调获取。

## 为什么现有扩展不够

### 缺少会随 CPU 状态变化的周期计数器

现有标准 `time` 与 `cycle` 计数器会持续递增，不论 CPU 正在执行，还是处于 WFI（Wait For Interrupt）空闲状态。

`instret` 统计的是指令数而非周期数，因此不适合作为电源管理和基于时间的负载计算指标。

### 为什么不是 Zihpm？

- **特权级可见性（Privilege）**：`Zihpm` 计数器通常仅 M 模式可见，或需通过复杂委派（`mcounteren`）才能让 S 模式可见。电源管理往往需要 S 模式直接可见，避免大量 M 模式陷入。
- **复杂度（Complexity）**：`Zihpm` 需要配置（写 `mhpmevent`）。`sscnt` 提供固定功能 CSR，开箱即用。对高频运行的电源管理环路而言，降低配置开销是有价值的。
- **资源争用与隔离（Resource Contention & Isolation）**：`Zihpm` 下 HPM 计数器资源通常有限且共享，常被性能分析工具（如 `perf`）占用。若电源管理驱动也依赖 HPM 计数器，会产生资源冲突。

## 参考

- [1] https://www.sciencedirect.com/topics/computer-science/dynamic-voltage-and-frequency-scaling
- [2] https://lwn.net/Articles/816388/
- [3] https://docs.kernel.org/scheduler/schedutil.html

Cheers,  
Fengxue
