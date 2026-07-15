# 计划：riscv-contrib-scan 第三轮 —— 三路静态候选的深度甄别与成文

## Context（背景与动机）

这是「内核 → RISC-V 可移植性/贡献点」系列研究的**第三轮**。前两轮（`kvm-riscv/`、`riscv-arm-gap/`）都以**补丁邮件列表**为源挖掘在途补丁的可移植性，均已完成并提交。

第三轮 `riscv-contrib-scan/` **换了角度**：不看在途补丁，而用 `scripts/scan.py` 直接从**只读本地内核树** `/Users/zq/Desktop/patch-work/linux-riscv`（Linux v7.2.0-rc3）静态扫描，找「当前树的真实缺口」，与第二轮互补。三路信号（=用户说的「三个路径」）：
- **§1 官方特性矩阵 TODO**：`Documentation/features` 中 riscv 标 TODO 的 6 项（维护者标注，最可信）。
- **§2 Kconfig 能力差集**：arm64∪x86 有、riscv 未 select 的 247 个符号（arm64+x86 都有的 46 个=强信号 §2a；余 201 个=次强 §2b）。
- **§3 代码内 TODO/桩**：arch/riscv 及 riscv 驱动内 54 处 TODO/FIXME/桩（+2 处 DTS）。

**问题**：第三轮只跑完自动扫描（`scan.py` + 原始 `README.md`），产出的是**机器 grep 的原始候选，含大量误报**（README 自己两处标注"需人工判断"）。相比前两轮缺少逐候选**四态判定**、`analysis/` 明细、**Top 候选排名表**、去误报后的结论。`riscv-contrib-scan/` 尚未提交（git `??`）。

**目标**：复用前两轮（以 arm-gap 版为骨架）方法论，对三路候选做深度甄别与四态判定，剔除误报、核实 riscv 落点，补齐 `analysis/` 与 README 的 Top 候选表与结论，使第三轮达到与前两轮一致的完成度。**范围严格限制在 `riscv-contrib-scan/` 内**；内核树只读；不碰其他路径。

## 复用的方法论（arm-gap 版，`method-extract` 已提炼）

**四态 rubric**（本轮语义：判「该缺口是否值得且可行地在 riscv 补上」）：
- **ALREADY** —— riscv 其实已实现（scan 误报/假阳），引 `_baseline_riscv.md` 或源码为证。
- **PORTABLE** —— 可直接 `select`（符号已有通用实现）或补通用层钩子（`mm/ kernel/ lib/ include/linux/ 框架 Documentation/ tools/`），几乎直接适用。
- **PATTERN** —— 需在 `arch/riscv/*` 实现 arch 专属部分，**必须给出具体 riscv 落点文件 + 改写点**（可参照 arm64/x86 现成实现）。
- **N-A** —— riscv 无对应硬件/ISA 语义、不适用；须点名所依赖的专属硬件/ISA。

**analysis/*.md 单条候选 4 字段**：`候选：符号/特性/文件:行（来源）` / `现状：riscv 当前如何（源码核实）` / `落点：arch/riscv 目标文件 + 依据` / `判定：四态 + 一句理由`。深度候选 3–8 条/文件，其余靠分类表覆盖；每文件 <800 行（前两轮实测 214–293 行）。

**README 交付物骨架**：标题+目标 → **TL;DR**（三路规模/甄别后真候选计数/四态结论/最高价值方向）→ §1 方法论（数据源=内核树静态扫描、与 arm-gap 互补、四态 rubric）→ §2 三路总览（各路指标表+噪声抽样）→ §3 arm64/x86↔riscv 机制对应速查 → **§4 Top N 候选**（P1 旗舰/P2 高价值/P3 机会 分级）→ §5 三路四态计数汇总表 → §6 结论与贡献路线建议（近期低风险 select / 中期补 arch 钩子 / 明确不追）→ 附录（目录结构、复现、局限与口径）。
**Top 候选表列（5 列）**：`候选(特性/符号/TODO) | 缺口性质 | RISC-V 落点 | 判定 | 来源(features路径/Kconfig符号/文件:行)`。

## 候选甄别要点（`candidate-triage` 实地核实，只读抽样）

**§1（6 项 features TODO，全部确标 TODO）** 按"别家是否已做"三层排序：
- **最优先（arm64+x86 都 ok）**：`cmpxchg-local`（≡ §2a HAVE_CMPXCHG_LOCAL）、`virt-cpuacct`。
- **次优（仅 x86 ok，参照 x86 实现给 PATTERN）**：`kprobes-on-ftrace`、`optprobes`、`user-ret-profiler`。
- **剔除（三家都 TODO，遗留技术）**：`cBPF-JIT`。

**§2a（46 强信号）** 真候选约 **18–22（40–50%）**；判定前须逐一 grep 排「传递 select / config 假阳」：
- 已证**假阳性**：`PARAVIRT` —— riscv 有 `config PARAVIRT`(Kconfig:1127)+PARAVIRT_TIME_ACCOUNTING，扫描只看 `select` 漏判 → 实为 ALREADY。**教训：本轮 §2 所有符号判定前须查 config/def_bool，不止 select。**
- 真缺口簇：跟踪/NMI（NMI/PERF_EVENTS_NMI/HARDLOCKUP_DETECTOR_PERF/NMI_SAFE_THIS_CPU_OPS/TRACE_IRQFLAGS_NMI）、static_call/livepatch/reliable_stacktrace/KCSAN、SMT（SCHED_SMT/HOTPLUG_SMT/SCHED_CLUSTER）、MM（nonleaf_pmd_young/lazy_mmu_mode/memory_failure）、cmpxchg_local/double、hw_breakpoint、default_bpf_jit、cache_line_size。
- N-A/ISA 未就绪（~12–16）：mem-encrypt/CC 簇、resctrl、pkeys、ACPI 簇、legacy-compat（UID16/OLD_SIG*）、power_supply。

**§3（54 处代码 TODO）** 真缺口:噪声 ≈ **1:3**（噪声 ~36 = 正常运行时分支/常量/日志，批量标 N-A）。**8 个可动作真缺口**：
1. `drivers/iommu/riscv/iommu.c:1149` IOMMU Second-Stage（G-stage/嵌套翻译）— 高值
2. `arch/riscv/kvm/aia_imsic.c:773,864` KVM AIA IMSIC↔IOMMU 映射 — 高值
3. `drivers/irqchip/irq-riscv-imsic-platform.c:230` IMSIC Multi-MSI — 中值
4. `arch/riscv/net/bpf_jit_comp64.c:615`(+comp32:1277/1292) BPF-JIT 1/2 字节 RMW 原子 — 小而可移植
5. `drivers/perf/riscv_pmu_sbi.c:1132`(+kvm/vcpu_pmu.c:320/343) PMU 虚拟化计数器 — 中值
6. `arch/riscv/kernel/perf_callchain.c:32/43` perf guest-OS callchain — 中值
7. `arch/riscv/kernel/probes/decode-insn.c:29` kprobes REJECTED 指令改模拟 — 低中值
8. `arch/riscv/include/asm/spinlock.h:18` alternative 取代 static key — 低值（与 static_call 主题相关）

**与前两轮重叠（勿重复深挖，交叉引用即可）**：§2a 的 KCSAN/static_call/livepatch/COPY_MC/GENERIC_IRQ_ENTRY、§2b 的 haltpoll 均在 memory「真实缺口」清单已判；§3 的 KVM IOMMU/AIA、PMU 虚拟化与 **kvm 轮**重叠；cmpxchg-local ≡ HAVE_CMPXCHG_LOCAL（互为佐证）。

## 执行方案（阶段）

### 阶段 A：落地共享上下文（主代理写，`riscv-contrib-scan/analysis/` 下 3 文件）
- `_baseline_riscv.md` —— 复用/裁剪 arm-gap 版 riscv 能力基线 + memory 真实缺口清单 + 无对应 ISA→N-A 清单（MTE/PAC/SME/SPE、GIC/ITS/SMMU）。
- `_taxonomy.md` —— 本轮四态 rubric（源码静态信号语义版）+ arm64/x86↔riscv 机制速查 + **假阳排查纪律**（查 config/def_bool 不止 select）。
- `_agent_instructions.md` —— 分析子代理指令模板（复用 arm-gap 6 步骨架，改为"核实源码树静态候选"）。

### 阶段 B：派 4 个 `general-purpose` 分析子代理（1 波并行，四态判定）
每子代理：读 3 份共享上下文 → 到只读内核树核实（判 ALREADY/假阳前必查 config+def_bool）→ 逐条四态判定 → 写 `analysis/<name>.md`（<800 行）→ 回 ≤250 字摘要。**不再派生下级子代理**。

### 阶段 C：综合成文（主代理）
汇总各 analysis → 重写 `riscv-contrib-scan/README.md`（前置甄别后 TL;DR + §3 机制速查 + §4 Top 候选表 + §6 结论，保留原始扫描结果为附录并注明"只看 select"口径局限）。

## 子代理分片计划（定稿：4 个子代理，1 波并行）

1. **`feat_official`（§1 官方 TODO 6 项）**：按三层排序逐一判；深挖 cmpxchg-local / virt-cpuacct 的 riscv 落点，kprobes-on-ftrace/optprobes/user-ret-profiler 参照 x86 给 PATTERN 落点，cBPF-JIT 标最低价值剔除。→ `analysis/feat_official.md`
2. **`kconfig_trace_nmi`（§2a 跟踪/调试/NMI 硬化簇）**：KCSAN/static_call/livepatch/reliable_stacktrace（已判项交叉引用不重挖）、NMI 簇、hw_breakpoint、C_RECORDMCOUNT、hardlockup 等；逐一 grep 排假阳。→ `analysis/kconfig_trace_nmi.md`
3. **`kconfig_sched_mm_rest`（§2a 其余 + N-A 簇 + §2b 201 抽样）**：SMT 簇、MM 簇、cmpxchg/cache_line_size/default_bpf_jit/DMA 铺垫等能力类；mem-encrypt/resctrl/pkeys/ACPI/legacy/power_supply 批量归 N-A；§2b 201 个抽样批量归类（平台/时钟/SoC/x86-legacy→N-A）并捞漏网通用符号、排假阳（VMAP_STACK/JUMP_LABEL/PERF_EVENTS 等 riscv 已有）。→ `analysis/kconfig_sched_mm_rest.md`
4. **`code_todo`（§3 全部）**：8 个真缺口逐一深挖 riscv 落点与缺口性质（KVM/IOMMU/IRQ 与 kvm 轮交叉引用）；36 行噪声批量标 N-A 并说明理由。→ `analysis/code_todo.md`

## 验证（完成前自检）

- [ ] 每个 PORTABLE/PATTERN 候选可追溯到 features 路径 / Kconfig 符号 / `文件:行`，riscv 落点在本地树核实存在（带行号更佳）。
- [ ] **排假阳**：§2 每符号判定前查 config/def_bool（不止 select），杜绝 PARAVIRT 式误判。
- [ ] 不把 riscv **已有**能力误报为缺口（对照基线：combo-spinlock/Svnapot/Zabha/RVV/PARAVIRT 等）。
- [ ] 不把 riscv **无对应 ISA** 项（MTE/PAC/SME/GIC/ITS/SMMU 相关符号）误报为可移植。
- [ ] 与前两轮结论交叉一致（重叠真缺口 KCSAN/static_call/GENERIC_IRQ_ENTRY 判定不冲突）。
- [ ] README 段落齐全（TL;DR/Top 表/结论/附录口径），每文件 <800 行。

## 约束

- 只在 `riscv-contrib-scan/` 内新建/修改；不碰 `kvm-riscv/`、`riscv-arm-gap/`、内核树（只读）。
- 中文成文；不 commit/push（除非用户明确要求）。
- 子代理只读内核树，不再派生下级子代理。
- 本轮**不改 `scan.py`**（其"只看 select"口径缺陷在 README 附录注明即可，除非用户要求修脚本）。
