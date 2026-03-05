# VMID Allocator 优化任务清单（RISC-V）

- [x] 复习现有资料与约束（当前仓库文档、目标代码路径、参考补丁）
- [x] 并行提取 ARM 参考补丁（5 个链接）的关键机制变化
- [x] 对比 ARM/RISC-V VMID 硬件机制（位宽、TLB 语义、失效策略、代际机制）
- [x] 对比 Linux ARM/RISC-V VMID allocator 当前实现（数据结构、并发模型、flush 策略）
- [x] 评估 ARM 方案迁移到 RISC-V 的可行性与风险
- [x] 制定 RISC-V VMID allocator 优化方案（分阶段、接口变化、验证策略）
- [x] 生成 `riscv-vmid-allocator-improve.md`
- [x] 在本文档末尾补充 review 结论

## review
- 已完成 3 个并行 Agent 调研（ARM 补丁系列、ARM64 现状、RISC-V 现状），并与主线程源码核对结果交叉验证。
- 已在当前目录生成 `riscv-vmid-allocator-improve.md`，覆盖硬件机制对比、内核实现对比、迁移可行性分析与分阶段优化方案。
- 已在文档中补充 ARM 补丁 `-1~-5` 的逐项提炼、迁移分类、风险与验证计划。

---

# 2026-03-05 VMID allocator 现状分析任务清单

- [x] 阅读 `arch/riscv/kvm/vmid.c` 与相关头文件，提取硬件约束
- [x] 梳理当前 Linux RISC-V VMID allocator 实现（结构、并发、快慢路径、代际机制）
- [x] 对照 ARM64 实现识别差距（性能/扩展性/正确性）
- [x] 形成中文输出（文件路径 + 函数级分析 + >=3 条优化建议及风险）
- [x] 回填 review 结论

## review (2026-03-05)
- 已完成函数级分析：`vmid.c`、`vcpu.c`、`mmu.c`、`tlb.c`、`gstage.c`、`csr.h`、`kvm_vmid.h`。
- 已补充 RISC-V H 扩展规范要点（VMIDLEN/VMIDMAX、HFENCE 语义、VMID+VSASID 标签关系、跨 hart 要求）。
- 已完成 ARM64 `arch/arm64/kvm/vmid.c` 对照并提炼性能/扩展性/正确性差距与优化点风险分级。

---

# 2026-03-05 ARM KVM VMID allocator 补丁系列迁移分析

- [x] 逐个读取 5 个 lore 链接原文（含 diff）
- [x] 按补丁提炼：问题、改动、并发/内存序、性能影响
- [x] 归纳系列设计主线：per-CPU reserved VMID / generation rollover / TLB flush 触发条件
- [x] 输出迁移三分类：可直接迁移 / 需要改造后迁移 / 不建议迁移
- [x] 给出关键代码路径与不确定点
- [x] 在本节末尾补充 review

## review (2026-03-05 ARM VMID 系列)
- 已逐个读取 5 个 lore 链接（2021-11-22，v4 0/4 + 1/4~4/4），并抽取到 `tasks/lore/patch1..5.txt`。
- 已按补丁输出问题/改动/并发与内存序/性能影响，并归纳了 per-CPU reserved VMID、generation rollover 与 TLB flush 触发条件。
- 已形成 RISC-V 迁移三分类，明确列出可直接迁移项、需改造项与不建议直接迁移项，并标注不确定点。

---

# 2026-03-05 ARM64 KVM VMID allocator 实现与硬件约束分析

- [x] 定位 ARM64 KVM VMID 相关源码文件与关键函数
- [x] 提取 ARM64 VMID 硬件机制（位宽来源、TLB 标记/失效语义、全局 flush 条件）
- [x] 梳理 Linux ARM64 VMID allocator 实现（数据结构、锁/原子、per-CPU 预留、generation、slowpath）
- [x] 核对 2021 补丁系列在当前代码中的状态及后续演进
- [x] 形成中文分析输出（含关键并发保证与内存序点）
- [x] 回填 review 结论

## review (2026-03-05 ARM64)
- 已完成：基于 `/home/zq/work-space/repo/patch-work/linux` 源码与 `git log/blame/show`，确认 2021 VMID allocator 系列核心机制仍在。
- 已识别后续关键演进：2022 EL2 侧 VMID bits 副本、2023 VHE VMID 变更触发 stage-2 reload、2025 VMID 分配前移到 `kvm_arch_vcpu_load()`、2024 nVHE TLBI 的 ISB/上下文同步修复。

---

# 2026-03-05 基于 Chapter 21 规范的文档优化

- [x] 读取 `/home/zq/Downloads/arch-spec/riscv/riscv-privileged.pdf` 并定位 Chapter 21 VMID 相关条款
- [x] 抽取 `hgatp` VMIDLEN/VMIDMAX、`HFENCE.GVMA` 语义与 MODE 切换约束
- [x] 将规范约束映射到 `riscv-vmid-allocator-improve.md` 的设计与验证章节
- [x] 回填 review 结论

## review (2026-03-05 Chapter 21)
- 已新增 Chapter 21 约束小节（21.2.10/21.3.2），补充 VMIDLEN 可为 0、写 HGATP 无隐式排序、HFENCE.GVMA 本 hart 语义与 MODE 变更 fence 规则。
- 已同步强化优化方案：新增必须时序约束、正确性不变式与验证项，避免“仅写 HGATP 不发 HFENCE”的潜在错误路径。
