# Sssscnt 议题提问清单

- 关联文档：[message-204-en.md](/Users/zq/Desktop/ai-projs/posp/linux-riscv-docs/rvi/docs/Sssscnt/message-204-en.md)
- 用途：用于在评审会、SIG 讨论或提案澄清阶段提问

## 建议优先提的 10 个问题

1. 这个提案要解决的核心痛点，是否可以量化为具体的延迟预算和数据新鲜度目标？
   例如，PuC 频率查询现在的典型延迟是多少，`Sssscnt` 希望把它降低到什么量级。

2. `CPU active cycle counter` 中“CPU idle state” 的精确定义是什么？
   它只在 WFI 时停止，还是在 clock gating、retention、deep idle 等状态下也停止。

3. 当 CPU 频率动态变化时，`CPU active cycle counter` 是如何保证统计结果准确反映真实运行频率的？
   频点切换瞬间是否有误差窗口，硬件如何定义切换边界。

4. `System active cycle counter` 和 `System cycle counter` 使用的“fixed reference frequency” 是什么来源？
   它是全系统统一、每 cluster 一份，还是每 hart 局部实现；在异构多 cluster 系统里如何保证可比性。

5. 如果 `System cycle counter` 可以视为 `mtime` 的 shadow，那么它与 `mtime` 的关系是什么？
   是要求严格同步、允许偏差，还是只要求单调递增但不要求严格对齐。

6. 这三个计数器分别打算暴露为哪些 CSR，访问权限如何定义？
   在 M/S/VS/U 模式下是否都可见，还是只允许 S 模式读取。

7. 该提案如何支持虚拟化场景？
   Guest/Hypervisor 是否需要看到虚拟化后的状态敏感计数器，若需要，trap-and-emulate 的成本是否会抵消该提案的收益。

8. 为什么必须新增一个专用扩展，而不是在 `Zicntr`/`Zihpm`/SBI 接口上做增强？
   有没有做过对比，证明新扩展在实现复杂度、软件路径长度和性能上明显更优。

9. Linux 侧准备如何接入这些计数器？
   除了 `arch_scale_cpu_capacity()`，是否已经有针对 `schedutil`、PELT 或 cpufreq governor 的原型补丁或评估数据。

10. 该提案的收益如何验证？
    是否有计划提供 benchmark、频率跟踪精度对比、调频响应时间、能效收益或调度准确性改进的数据。

## 可继续追问的问题

11. 在 CPU hotplug、suspend/resume、cluster power down、system sleep 这些场景下，这些计数器的行为定义是什么？

12. 多核迁移场景下，调度器如何使用这些计数器来比较不同 hart 的负载，尤其是在异构系统中。

13. 这些计数器是否会引入新的 side channel 或功耗状态泄露问题？
    如果 S 模式可以直接读取，是否需要额外的访问控制或虚拟化隔离策略。

14. 如果硬件平台本身没有稳定的 reference clock，或者不同电源域之间存在时钟漂移，这个扩展还能否保持语义一致。

15. 提案里提到计数器是 64 位；在 RV32 系统上读取时，是否需要定义原子读取语义或高低位锁存机制。

16. 这个扩展是否只服务于 DVFS，也能支持 thermal governor、energy model、idle governor 或性能分析工具的统一使用。

17. 如果平台已经能通过 firmware mailbox 或 SCMI 类接口拿到实际频率，`Sssscnt` 相比这些方案的边际收益有多大。

18. 提案是否考虑过与 ARM AMU、Intel APERF/MPERF 做语义对齐，方便操作系统抽象出统一接口。

## 如果你想让讨论更有攻击性，可以优先问这 5 个

- 这个提案真正新增了什么不可替代的硬件能力，而不是把现有频率查询机制换了一种包装方式？
- “stale-free visibility” 在规范层面如何定义，如何测试，如何证明。
- 新增 CSR 和硬件计数路径的面积、功耗、验证成本是多少，是否值得为此引入一个新扩展。
- 如果 `Zihpm` 的主要问题只是权限和资源争用，为什么不能通过固定事件号和更直接的委派机制解决。
- 在最关键的 Linux 调度与 DVFS 路径上，是否已经证明它比现有方案有可观收益，而不只是理论上更优雅。

## 使用建议

- 开会时间短时，优先问“语义定义”“替代方案对比”“Linux 接入方式”“验证数据”这四类问题。
- 如果对方偏硬件实现，重点追问 idle state 边界、reference clock 来源和频点切换时的准确性。
- 如果对方偏软件生态，重点追问内核接入、虚拟化支持和与现有标准扩展的关系。
