# 计划：linux-arm-kernel 补丁 → RISC-V 可移植性汇总

## Context（背景与目标）

用户要求：以 **linux-arm-kernel 邮件列表**（`https://lists.infradead.org/pipermail/linux-arm-kernel/`）为源，探索
**2025-01-01 ~ 2026-07-10** 区间内的全部补丁，收集汇总，逐一分析其移植到 **RISC-V** 架构的可能性，列举潜在可移植补丁。
产出一篇汇总文档放在 **`riscv-arm-gap/`** 路径下，标注「原补丁 ↔ 可移植点 ↔ RISC-V 落点」的对应关系。

**辅助资源**：本地内核源码 `/Users/zq/Desktop/patch-work/linux-riscv`（只读，用于核对 riscv 现状与落点）。
**范围约束**：只在当前路径（`.../claude-4-8/`）下新建 `riscv-arm-gap/`；不触碰 `kvm-riscv/` 或其他路径；不修改内核源码。

这是上一轮 KVM 可移植性研究的姊妹任务，方法论沿用「全量自动分类索引 + 候选深度分析」的分层策略，但**数据源、分类法与 RISC-V 基线全部重构**——linux-arm-kernel 覆盖整个 ARM/ARM64 架构（mm/perf/cpufeature/entry/vdso/DTS/SoC 驱动/MTE/BTI/SVE…），而非仅 KVM 子系统。

## 关键侦察结论（已确认）

1. **数据源决策（重要，见下方「关键决策」）**：`patchwork.kernel.org` 存在 **`linux-arm-kernel` 项目**，提供与 KVM 任务相同的 REST API，且是**同一条邮件列表的结构化补丁视图**（自动从邮件抽取 patch，正好等于用户要的「所有补丁」）。区间内 **668 页 × 100 ≈ 66,800 个补丁**（约 KVM 的 3 倍）。pipermail 是同列表的原始 mbox 归档（2025-Jan~2026-Jul 逐月 `.txt.gz`），需自行重建线程/系列并从讨论噪声中抽取补丁——patchwork 已完成这项工作。**决定采用 patchwork 作为结构化索引，并在文档中显式说明此等价关系。**
2. **信噪比低**：抽样确认 linux-arm-kernel ~85% 是对 RISC-V 而言的「硬件噪声」——DTS/dt-bindings 板级描述、SoC/厂商驱动（clk/pinctrl/soc/iommu-smmu/phy/reset）、defconfig、`[GIT,PULL]`、被抄送的无关子系统（net/media）。仅 ~10-15% 是**架构核心信号**（arch/arm64 的 mm、cpufeature、perf、entry、vdso、bpf、atomics、kexec…）才真正涉及可移植性。分类器必须**激进地批量归入噪声桶**，只把架构核心信号送子代理。
3. **存在真实的特性对应关系**（使分析有价值）：arm64 contpte ↔ riscv **Svnapot**；LSE atomics ↔ **Zabha/Zacas/Zawrs**；BTI ↔ **Zicfilp**；GCS 影子栈 ↔ **Zicfiss**；SVE/SME ↔ **RVV**；TBI 指针掩码 ↔ **Zjpm/Supm**；MTE/PAC ↔ 暂无 riscv 对应。

## 数据源与接口

- Patchwork REST API（已验证 200 OK，无需鉴权）：
  `https://patchwork.kernel.org/api/1.2/patches/?project=linux-arm-kernel&since=2025-01-01T00:00:00&before=2026-07-10T00:00:00&per_page=100&page=N&order=date`
- 每条记录字段：`id, name, date, submitter, series[id/name/version], state, web_url, msgid, mbox`。
- 深挖候选时用 `mbox` 取补丁全文（含 diff）确认落点。

## RISC-V 能力基线（arch/riscv 全树，2 个 Explore 子代理已盘点，全部核对文件存在）

内核树 = Linux v7.2.0-rc3。**已成熟实现（判 ALREADY 的依据，勿误报为可移植）：**
- **MM/页表**：Sv39/48/57（运行时动态）、hugetlb/THP（含 PUD-THP）、**Svnapot**（=arm64 contpte 连续 PTE）、
  线性映射拆分 `__split_linear_mapping_*`（`mm/pageattr.c`）、vmemmap、TLB range flush + **Svinval** + SBI rfence + 批量 unmap、
  STRICT_KERNEL_RWX、**Svvptc**、Svade/Svadu（=HW A/D）、Svpbmt（=MAIR）。
- **cpufeature**：`elf_hwcap`/hwprobe/`riscv_isa_ext[]`(~105 扩展)/alternatives/四厂商 errata(andes/mips/sifive/thead)/vendor_extensions。
- **原子/锁**：**Zabha**(子字 AMO=LSE)、**Zacas**(CAS，缺则退回 LR/SC)、**Zawrs**(=WFE)、combo spinlock(ticket↔qspinlock 运行时切换)。
- **entry/boot**：手写 entry（非 GENERIC_ENTRY，同 arm64）、compat、head.S、EFI-stub、KASLR(`RANDOMIZE_BASE`)、XIP。
- **vector/CFI/指针掩码**：完整 RVV 1.0 + kernel-mode vector + Vector-Crypto；**Zicfilp**(=BTI 落地页)、**Zicfiss**(=GCS 影子栈)、kCFI；**Supm**(=TBI/tagged-addr ABI，`prctl PR_PMLEN`)。
- **perf/trace/kexec/acpi/debug**：SBI-PMU + **sscofpmf**(溢出采样)+snapshot；dynamic ftrace(WITH_ARGS/CALL_OPS/DIRECT_CALLS/FUNCTION_GRAPH)、kprobes/kretprobes/uprobes、BPF-JIT(64+32,kfunc/arena/percpu)、jump_label、kgdb；完整 kexec/kexec_file/purgatory/kdump；ACPI(RINTC/RHCT/RIMT/SRAT，64bit)；KASAN-generic + KFENCE + stackprotector + VMAP_STACK。

**明确缺口（arm64 有、riscv 无/部分）——即移植候选来源：**
1. **KCSAN / KMSAN / KASAN SW_TAGS** —— riscv 缺（仅 KASAN-generic + KFENCE）；均为**通用 sanitizer** → 多为 PORTABLE（可 select/补 arch 钩子）。
2. **`rodata=full`** —— riscv 无真正等价（仅 STRICT_RWX + 按需拆分）→ PATTERN（`mm/pageattr.c`/`mm/init.c`）。
3. **BBML2 大块映射 / contpte 优化**（arm64 `mm/mmu.c`+`cpufeature`）—— riscv 有 Svnapot 但优化点不同 → PATTERN（`mm/`）。
4. **MTE(内存标签) / PAC(指针认证) / SME(矩阵) / SPE(统计采样)** —— riscv **无对应 ISA/HW** → N-A（除非补丁扩展了通用底座）。
   emerging 类比已落地：BTI→Zicfilp、GCS→Zicfiss、SVE→RVV、TBI→Supm、LSE→Zabha/Zacas —— 这些 arm64 补丁多判 ALREADY/PATTERN。
5. 其余高价值来源：mm 通用优化、cpufeature/alternatives 重构、ftrace/bpf-jit 改进、vdso、entry 硬化、perf core、通用 selftests/docs。

## 分类法（linux-arm-kernel 专用，20+ 类 / 3 层级 + 噪声桶）

**噪声桶（分类器批量判 N-A，仅计数+抽样，不送子代理）：**
- `dts-board`（arm64/ARM dts、板级 dt-bindings）
- `soc-driver`（clk/pinctrl/soc/reset/phy/memory-ctrl/厂商驱动）
- `pull-request`（`[GIT,PULL]`）
- `defconfig`
- `unrelated-cc`（被抄送的 net/media/usb 等无关子系统）
- `firmware-abi`（SCMI/SCPI/PSCI/SMCCC/FF-A/OP-TEE —— ARM 固件 ABI，多 N-A，仅注 SBI 类比）

**可移植相关桶（送子代理做四态判定）：**
- `mm-pgtable`（页表/TLB/hugetlb/THP/contpte/vmemmap/ioremap/rodata=full/BBML）
- `cpufeature-alt`（特性检测/alternatives/errata/hwcaps/ELF-hwcap）
- `perf-pmu`（arm_pmu/perf events/SPE；CoreSight 归 HW）
- `entry-exception`（entry.S/syscall/异常/中断入口/context-tracking）
- `vdso`（vDSO/gettimeofday/clock_gettime）
- `trace-probe`（ftrace/kprobes/uprobes/bpf-jit/jump_label/kgdb）
- `atomics-locking`（LSE/cmpxchg/qspinlock/barriers）
- `vector-fp`（SVE/SME/FP-SIMD 上下文/ptrace/signal —— 对 RVV）
- `security-hw`（MTE/BTI/PAC/GCS/CFI/影子栈/pointer-masking/KASLR —— 混合，逐条判）
- `signal-ptrace-elf`（信号/ptrace/ELF/coredump/进程）
- `kexec-crash`（kexec/kdump/crash/purgatory）
- `acpi-arch`（arm64 ACPI 中架构无关部分）
- `boot-head`（head.S/boot/EFI-stub/relocation）
- `irqchip`（GICv3/v4/ITS —— 多 HW N-A；通用 irqchip 基础设施 PORTABLE）
- `generic-cross`（经 arm 列表但落在 mm//kernel//lib//include/linux 的**架构无关**改动 → PORTABLE/自动适用）
- `docs-tooling`（Documentation/selftests/tools/kselftest → PORTABLE）
- `misc-arch`（其余 arch/arm64 catch-all，送子代理三分类）

## 四态判定 rubric（沿用 KVM 任务）

- **ALREADY** —— riscv 已实现等价能力（引基线/源码为证）。
- **PORTABLE** —— 通用/架构无关代码，改动应直接/几乎直接适用于 riscv。
- **PATTERN** —— arch 专属实现，但机制可复用，需在 riscv 侧重写；给出具体 riscv 落点文件。
- **N-A** —— 依赖 ARM 专有硬件/ISA（GIC/ITS/SMMU/PAC/MTE/板级 DTS/厂商 SoC）且无 riscv 对应、不扩展通用底座 → 不可移植。

## 实施步骤

### 阶段 0：数据采集（`riscv-arm-gap/scripts/fetch_patches.py`，改自 KVM 版）
- 改 `project=linux-arm-kernel`、输出目录 `riscv-arm-gap/data/`；保留断点续抓/重试/礼貌延时。
- 抓全部 ~668 页元数据 → `all_patches.jsonl`（~66,800 条）。仅元数据不取全文。

### 阶段 1：分类与去重（`riscv-arm-gap/scripts/classify.py`，重写分类法）
- **重写** arch 分类器与 CATEGORY_RULES 为上面的 linux-arm-kernel 分类法（噪声桶优先批量吸收，架构核心桶精准命中）。
- 按 series 归一化去重（复用 KVM 版 `norm_name`），保留最新版本。
- 产出：`arm_series.csv`（每系列一行：类别/层级/arch/状态/日期/系列名/web_url）、`category_counts.md`（统计）、`by_category/<cat>.jsonl`（供子代理输入）。
- 校验打印：总条数≈66,800；噪声桶 vs 信号桶占比；各类别计数自洽。

### 阶段 2：可移植性分析（并行子代理，改自 KVM `_agent_instructions.md`）
- 先落地共享上下文：`riscv-arm-gap/analysis/{_baseline_riscv.md,_taxonomy.md,_agent_instructions.md}`。
- 分派：每个**信号桶**一个子代理（约 12-15 个，分批并行）；噪声桶不派代理（分类器已批量判 N-A，README 汇总计数+抽样示例）。
- 每子代理：读共享上下文 + 分到的 `by_category/*.jsonl`；对每条系列判四态；对本批最强 3-6 候选 `curl -sL <mbox>` 取全文核实 diff 与 riscv 落点；写 `analysis/<cat>.md`；返回 ≤250 字摘要。

### 阶段 3：综合与成文（主代理 → `riscv-arm-gap/`）
- `README.md`：数据出处与 patchwork↔pipermail 等价说明、总体统计（噪声/信号占比）、三层级+特性对应关系概览、
  **Top 40-60 可移植候选排名表**（原补丁 → 可移植点 → riscv 落点 → 依据/web_url）、按类别计数、结论与移植路线建议、附录。
- `analysis/`：按类别拆分明细（「多而小」，每文件 <800 行）。
- `data/`：`all_patches.jsonl` + `arm_series.csv` + `category_counts.md` + `by_category/` 作为可追溯证据。
- `scripts/`：抓取与分类脚本（可复现）。

## 关键决策（已采用合理默认，审批时可否决）

1. **数据源用 patchwork.kernel.org/project/linux-arm-kernel（用户已确认）**：二者是**同一条 linux-arm-kernel 列表**，patchwork 已把邮件中的补丁结构化抽取（正好=用户要的「所有补丁」），可复用 KVM 管线、按日期/系列/状态过滤；直接解析 pipermail 需重建线程与系列、从讨论中抽补丁，成本高且更易错。README 中会显式说明此 patchwork↔pipermail 等价关系。
2. **深度**：全量自动分类索引（覆盖全部去重系列，每条带四态判定）+ Top 40-60 候选深度分析；噪声桶批量判 N-A 只计数+抽样，不逐条散文。
3. **结构**：`riscv-arm-gap/` 下多文件（README + analysis/ + data/ + scripts/），中文成文与项目一致。
4. **不做**：不碰其他路径（含 kvm-riscv/）；不改内核源码；不为 DTS/厂商驱动逐条写散文。

## 验证方式

- 数据完整性：`all_patches.jsonl` 行数 ≈ 66,800（patchwork Link rel=last 页数×100 校对）；去重系列数、各类别计数脚本打印自洽。
- 抽查：随机抽 10 个「PORTABLE/PATTERN」结论，核对 mbox 全文 diff 与 riscv 源码落点成立；抽查噪声桶样本确属 N-A（非误杀架构核心补丁）。
- 交叉核对：结论与 riscv 基线一致——不把 riscv **已有**特性（如 Svnapot/RVV/Zbb）误报为「可移植」，不把**纯 ARM 硬件/ISA**特性（GIC/PAC/MTE）误报为可移植。
- 可追溯：每个候选带 patchwork `web_url` 与 riscv 目标文件路径。

## 预期规模与成本提示

- 网络：~668 次 API 分页请求（元数据）+ 数十次 mbox 全文抓取（仅候选）。较 KVM 任务大 ~3 倍。
- 算力：约 12-15 个分析子代理分批并行。属研究型任务的合理开销，规模大于 KVM 任务。
