# misc-arch（第 3 片）可移植性分析（linux-arm-kernel → RISC-V）

> 输入：`data/by_category/misc-arch.2.jsonl`（201 系列，arm64/ARM 架构杂项 catch-all）。
> 判定依据：`_baseline_riscv.md` + 本地内核树 `/Users/zq/Desktop/patch-work/linux-riscv`（v7.2.0-rc3）核对。
> 深挖：curl 2 条（#68 livepatch、#49 cacheinfo）+ 本地 grep 核对 ~12 处 riscv 落点。

## 摘要

- **系列总数**：201
- **四态计数（近似）**：ALREADY ≈ 8 / PORTABLE ≈ 14 / PATTERN ≈ 16 / N-A ≈ 163
- 本片主体是 **KVM:arm64 NV/pKVM/hyp**（~55 条，均 N-A）、**ARM SoC/mach + DTS/defconfig/pull noise**（~70 条，N-A）、**arm64 专属 ISA/HW**（MPAM/MTE/POE/MOPS/AMU/BRBE/SPE/boot-wrapper，~20 条，N-A）。真候选集中在 **通用底座（drivers/base、lib/、kernel/、scripts/）** 与 **arch 通用机制（livepatch、cacheinfo、mmap 随机化）**。

### 本类 Top 候选（按价值排序）
1. **#68 arm64: Implement HAVE_LIVEPATCH** — PATTERN，riscv 缺 livepatch + reliable-stacktrace（有 ftrace 底座）
2. **#49 cacheinfo: Set cache 'id' based on DT data** — PORTABLE（`drivers/base/cacheinfo.c` 通用）+ 可选 arch hook
3. **#193 kcov: New Unique PC|EDGE|CMP Modes** — PORTABLE，通用 `kernel/kcov.c`，riscv 有 `ARCH_HAS_KCOV`
4. **#86 lib/crc: improve how arch-optimized code is integrated** — PORTABLE，通用 `lib/crc/` 框架 + 为 riscv 建 arch 槽位
5. **#190 arm64: cacheinfo: Avoid OOB write when DT info incorrect** — PATTERN（bug 平价），riscv 同用 DT cacheinfo
6. **#119 arm64: Support VA_BITS=52 for ARCH_MMAP_RND_BITS_MAX** — PATTERN，riscv 动态 Sv39/48/57 同类问题
7. **#5 / #85 / #145 / #196 sched/module 通用整合** — PORTABLE，riscv 自动受益或同一 tree-wide 系列覆盖

---

## Top 可移植候选（深度）

### 1. #68 arm64: Implement HAVE_LIVEPATCH —— PATTERN（强）
- **原补丁**：`[v5] arm64: Implement HAVE_LIVEPATCH`（https://patchwork.kernel.org/project/linux-arm-kernel/patch/20250630174502.842486-1-song@kernel.org/）状态=new
- **可移植点**（curl 核对 diff）：`select HAVE_LIVEPATCH`（依赖 `HAVE_RELIABLE_STACKTRACE`）+ `TIF_PATCH_PENDING`（thread_info）+ 退出用户态时 `klp_update_patch_state()`（entry-common）+ 重写 `arch_stack_walk_reliable()`。
- **riscv 落点**：`arch/riscv/Kconfig`（select HAVE_LIVEPATCH + HAVE_RELIABLE_STACKTRACE）、`arch/riscv/include/asm/thread_info.h`（加 TIF_PATCH_PENDING）、`arch/riscv/kernel/entry.S`+`traps.c`（exit-to-user 钩 klp_update_patch_state）、`arch/riscv/kernel/stacktrace.c`（arch_stack_walk_reliable）。
- **依据**：本地 grep 确认 riscv **无** `HAVE_LIVEPATCH`/`livepatch.h`、**无** `HAVE_RELIABLE_STACKTRACE`；但 **已有** `HAVE_DYNAMIC_FTRACE_WITH_CALL_OPS`/`WITH_ARGS`（Kconfig:161-163）——livepatch 的 ftrace 底座已就绪。
- **判定**：PATTERN。机制与 arm64 逐点对应，唯一前置是 riscv 先实现 reliable-stacktrace（同一补丁内一并做）。

### 2. #49 cacheinfo: Set cache 'id' based on DT data —— PORTABLE + PATTERN
- **原补丁**：`cacheinfo: Set cache 'id' based on DT data`（https://patchwork.kernel.org/project/linux-arm-kernel/patch/20250711182743.30141-2-james.morse@arm.com/）状态=new
- **可移植点**（curl 核对）：[1/3] 改 `drivers/base/cacheinfo.c`——**通用框架**，为所有 DT 架构从 DT 生成 cache `id`；[2/3] 加通用 arch hook 把 CPU 硬件 id 压成 32 位；[3/3] arm64 用 MPIDR 实现该 hook。
- **riscv 落点**：`drivers/base/cacheinfo.c` 改动 **自动适用** riscv（PORTABLE）；`arch/riscv/kernel/cacheinfo.c` 可按需提供压缩 hook（PATTERN，riscv hart-id 通常 ≤32 位，多半无需）。
- **依据**：本地确认 riscv `cacheinfo.c` 用 DT（`of_node`/`ci_leaf_init`）且 **未设** `this_leaf->id`——正是本补丁补齐的能力。
- **判定**：PORTABLE（核心）。

### 3. #193 kcov: Introduce New Unique PC|EDGE|CMP Modes —— PORTABLE
- **原补丁**：`kcov: Introduce New Unique PC|EDGE|CMP Modes`（https://patchwork.kernel.org/project/linux-arm-kernel/patch/20250114-kcov-v1-5-004294b931a2@quicinc.com/）状态=new
- **可移植点**：新增 kcov 去重覆盖模式，全部落在通用 `kernel/kcov.c` + 示例/文档；无 arch 依赖。
- **riscv 落点**：无需 arch 改动，riscv `select ARCH_HAS_KCOV`（Kconfig:38）即自动获得。
- **判定**：PORTABLE（通用 sanitizer/coverage 框架）。

### 4. #86 lib/crc: improve how arch-optimized code is integrated —— PORTABLE
- **原补丁**：`lib/crc: improve how arch-optimized code is integrated`（https://patchwork.kernel.org/project/linux-arm-kernel/patch/20250607200454.73587-2-ebiggers@kernel.org/）状态=new
- **可移植点**：把各 arch CRC 优化代码迁入 `lib/crc/<arch>/` 并统一集成方式——通用 `lib/crc/` 框架重构，为每架构建标准槽位。
- **riscv 落点**：`lib/crc/riscv/`（riscv CRC 优化按同一模式接入）；框架本身 PORTABLE。
- **判定**：PORTABLE。同族 #114（drop "glue" 文件名）为纯机械重命名，PORTABLE-low。

### 5. #190 arm64: cacheinfo: Avoid out-of-bounds write when DT info is incorrect —— PATTERN
- **原补丁**：（https://patchwork.kernel.org/project/linux-arm-kernel/patch/20250116185458.3272683-2-rrendec@redhat.com/）状态=new
- **可移植点**：DT cacheinfo 层级/leaf 数不一致时防越界写。
- **riscv 落点**：`arch/riscv/kernel/cacheinfo.c`（`ci_leaf_init` 循环）/ `drivers/base/cacheinfo.c`——riscv 同样从 DT 填 cacheinfo，同类越界风险存在。
- **判定**：PATTERN（bug 平价）。同族 #180/#104/#191 多为 arm64/arm32 本地实现，价值低。

### 6. #119 arm64: Support ARM64_VA_BITS=52 when setting ARCH_MMAP_RND_BITS_MAX —— PATTERN
- **原补丁**：（https://patchwork.kernel.org/project/linux-arm-kernel/patch/20250417114754.3238273-1-korneld@google.com/）状态=new
- **可移植点**：VA 位宽变化时正确设定 mmap 随机化位数上限。
- **riscv 落点**：`arch/riscv/Kconfig`（`ARCH_MMAP_RND_BITS_MAX`，本地确认存在于 :270）——riscv 运行时动态 Sv39/48/57，VA 位宽可变，同类需按 VA 宽度调整 rnd bits。
- **判定**：PATTERN。

### 通用整合类（PORTABLE，riscv 自动受益 / 同系列已覆盖）
- **#5** `sched: Switch fallback task allowed cpumask to HK_TYPE_DOMAIN`：核心 [25/33] 在通用 `kernel/sched`，[27/33] 仅 arm64 薄适配 → PORTABLE。
- **#85** `sched: preempt: Move dynamic keys into kernel/sched`：通用整合，riscv **已有** `HAVE_PREEMPT_DYNAMIC_KEY`（Kconfig:196）→ PORTABLE（去重受益）。
- **#145** `arm/arm64: Rely on generic printing of preemption model`：改用通用 preempt 打印 → riscv 可同样丢弃自定义代码，PORTABLE/PATTERN-low。
- **#196** `ARM/arm64: module: Use RCU in all users of __module_text_address()`：tree-wide 通用系列（`kernel/module`），riscv 由同系列其它补丁覆盖 → PORTABLE。
- **#130** `Make gcc-8.1 and binutils-2.30 the minimum`、**#13** `Bump min LLVM to 15.0.0`：通用 kbuild 版本门槛 → PORTABLE。
- **#109 [2/4]** `ubsan: Remove regs from report_ubsan_failure()`（通用 `lib/ubsan.c`）、**#53 [2/2]** `bitfield: Ensure return values checked`（通用 `include/linux/bitfield.h`）→ 通用部分 PORTABLE，其余 KVM/EL2 部分 N-A。
- **#102 / #127 / #107**：`KVM lock_all_vcpus` / `KVM extract lock_all_vcpus` / `rust: Add bug/warn abstractions` —— 系列内 **已含显式 RISC-V 补丁**（`RISC-V: KVM: ...` / `riscv/bug: ARCH_WARN_ASM`）→ **ALREADY / 已在途**，riscv 落点 `arch/riscv/kvm/`、`arch/riscv/include/asm/bug.h`。

---

## 关键 ALREADY（避免误报为「新可移植」）
| 系列 | 依据（本地核对） |
|---|---|
| **#124** arm64: enable PREEMPT_LAZY | riscv 已 `select ARCH_HAS_PREEMPT_LAZY` + `HAVE_TIF_NEED_RESCHED_LAZY`（thread_info.h:117）|
| **#15** arm64/dma-mapping: respect dir parameter | riscv `arch_sync_dma_for_device` 已按 `dir` switch 正确处理（dma-noncoherent.c:69）|
| **#123** fdt: Delete rng-seed after use | riscv 已把 `kaslr-seed` 读后清零 `*prop=0`（pi/fdt_early.c:24）；`rng-seed` 为 arm64 FDT 专属路径 |
| **#181** arm64: Handle .ARM.attributes in linker | riscv 已在 `vmlinux.lds.S:171` 处理 `.riscv.attributes` |
| **#174 / #197** arm64 sorttable mcount_loc | riscv 已 `select HAVE_BUILDTIME_MCOUNT_SORT`（Kconfig:155）|
| **#84** arm64: Unconditionally select JUMP_LABEL | riscv 已 `HAVE_ARCH_JUMP_LABEL(_RELATIVE)`（基线 §11），策略性差异 |

---

## 次级 PATTERN（低-中，arch 专属但机制可复用；落点已注）
- **#76** arm64: move smp_send_stop() cpu mask off stack → `arch/riscv/kernel/smp.c`（大 cpumask 移出栈）
- **#94** arm64/trap: fix ct->nmi_nesting when die() in kthread → `arch/riscv/kernel/traps.c`（context-tracking nmi 交互，通用性中）
- **#16** arm64/ptdump: Add ARM64_PTDUMP_CONSOLE → `arch/riscv/mm/ptdump.c`（ptdump 控制台输出）
- **#105** arm64/boot: Forbid BSS symbols in startup code → `arch/riscv/kernel/pi/`（riscv 已有 `__pi_` 前缀纪律，可进一步禁 BSS）
- **#26** arm64/module: runtime patching、**#96** pagetable teardown warning、**#112** traps show fault addr、**#28/#132** 经 sysfs 暴露 CPU 寄存器（CPUECTLR/AIDR_EL1；riscv 已经 sysfs 暴露 mvendorid/marchid，部分 ALREADY）、**#144** perf data-type profiling（tools/perf，需 riscv 指令解码）、**#36/#37** NR_CPUS=1（Kconfig 调参）、**#39** tracing hide ipi events（通用 tracepoint，倾向 PORTABLE）
- **#14** KVM: arm64: Add "struct kvm_page_fault"：KVM MMU 抽象重构（借鉴 x86），riscv 落点 `arch/riscv/kvm/mmu.c`，KVM-内部，价值中低。

---

## N-A 合并组（同质，逐条无 riscv 价值）
| 组 | 代表行/系列 | 计数 | 依据 |
|---|---|---|---|
| KVM:arm64 NV/nested（VNCR/AT/ESR_EL2/FAR_EL2/HCR(X)/TGRAN/GTG/S1POE/PAR）| #1,2,4,12,17,22,24,25,29,30,33,41,48,50,66,67,74,92,103,111,117,121,125,140,143,151,168,172,183,192,194 | ~33 | arm64 EL2/hyp + GIC/系统寄存器专属 |
| pKVM / stage-2 huge / memcache（#98 及拆分 #40,72,106,108,146,148,152,154-158,169,179,189,#110 GCS）| #40,54,71,72,98,106,108,110,146,148,152,154,155,156,157,158,164,169,179,189 | ~20 | pKVM/EL2 hyp + stage-2 CMO，arm64 专属 |
| ARM SoC/mach 平台（OMAP/at91/imx/tegra/rockchip/shmobile/davinci/samsung/zynq(mp)/hpe/sa1100/orion/s3c/versatile/spitz）| #3,6,7,9,18,21,26?,32,46,51,56,73,75,79,81,97,129,131,135,141,150,153,161,162,177,182,184,187,191,198,201 | ~30 | 厂商 SoC/mach，无 riscv 对应 |
| DTS/defconfig/pull-request/bindings noise | #31,38,42,47,57-65,69,82,113,142,153,170,171,188,199 | ~28 | 分类器批量 N-A（含 SPDX 许可注释替换 #57-65,69 共 10 条）|
| string-choices helper 纯清理 | #43,44,45,55,79,81 | 6 | arch/arm 琐碎 idiom |
| arm64 专属 ISA/HW（MPAM/MTE/POE/MOPS/AMU/BRBE/SPE/hwcaps-DPISA）| #11,77,87,91,133,139,164,173,175,185,194 | ~11 | 无 riscv 对应扩展 |
| boot-wrapper（arm 测试固件）| #23,88,89,159 | 4 | arm 固件测试工具，非内核 |
| perf vendor events（arm JSON 数据）| #170,171,188 | 3 | arm 厂商 PMU 事件表 |
| arm64/arm crypto asm bug | #83,138 | 2 | arch 汇编专属 |
| toolchain/linker workaround（LLD/binutils）| #93,95,122 | 3 | arm64 特定工具链 |
| arm 汇编/链接/fixmap/vectors 本地实现 | #75,90,100,101,115,116,118,120,134,136,137,147,149,160,163,166,167,176,186,200 | ~20 | arm(64) 本地 boot/link，PATTERN-low 到 N-A |
| 琐碎清理（whitespace/typo/BUG()/dup header/str_on_off）| #17,27,34,35,52,74,121,126,165,195 | ~10 | trivial |
| arch=other（mips/hyperv）| #80,178 | 2 | 非 riscv（hyperv 无 riscv 端）|

---

## 全量判定表（覆盖 201 条；同质 N-A 见上组，候选逐条）
| # | 系列（简） | arch | 判定 | 可移植点 / riscv 落点 |
|---|---|---|---|---|
| 5 | sched fallback cpumask HK_TYPE_DOMAIN | arm | PORTABLE | 通用 kernel/sched；riscv 自动 |
| 13 | Bump min LLVM 15.0.0 | arm | PORTABLE | 通用 kbuild |
| 14 | KVM: arm64 struct kvm_page_fault | arm | PATTERN-low | arch/riscv/kvm/mmu.c（KVM 内部）|
| 15 | dma-mapping respect dir | arm | ALREADY | dma-noncoherent.c 已按 dir |
| 16 | arm64/ptdump CONSOLE | arm | PATTERN | arch/riscv/mm/ptdump.c |
| 39 | tracing hide ipi events | arm | PORTABLE | 通用 tracepoint |
| 49 | cacheinfo cache id from DT | arm | **PORTABLE**+PATTERN | drivers/base/cacheinfo.c（自动）+ arch hook |
| 53 | bitfield ensure return checked([2/2]) | arm | PORTABLE(部分) | include/linux/bitfield.h；[1/2] KVM N-A |
| 68 | arm64 Implement HAVE_LIVEPATCH | arm | **PATTERN** | Kconfig/thread_info/entry/stacktrace（需先做 reliable-stacktrace）|
| 76 | smp_send_stop cpumask off stack | arm | PATTERN-low | arch/riscv/kernel/smp.c |
| 84 | Unconditionally select JUMP_LABEL | arm | ALREADY | 已 HAVE_ARCH_JUMP_LABEL |
| 85 | preempt: move dynamic keys → kernel/sched | arm | PORTABLE | 通用；riscv 有 HAVE_PREEMPT_DYNAMIC_KEY |
| 86 | lib/crc arch-optimized integration | arm | **PORTABLE** | lib/crc/ 框架 + lib/crc/riscv/ |
| 94 | trap nmi_nesting in kthread | arm | PATTERN-low | arch/riscv/kernel/traps.c |
| 96 | pagetable teardown false warning | arm | PATTERN-low | arch/riscv/mm |
| 102 | KVM lock_all_vcpus（含 RISC-V 补丁）| arm | ALREADY | 系列内已含 arch/riscv/kvm |
| 105 | boot: forbid BSS in startup | arm | PATTERN | arch/riscv/kernel/pi/（已有 __pi_ 前缀）|
| 107 | rust bug/warn（含 riscv 补丁）| arm | ALREADY | arch/riscv/include/asm/bug.h |
| 109 | UBSAN at EL2（[2/4] ubsan 通用）| arm | PORTABLE(部分) | lib/ubsan.c；EL2 部分 N-A |
| 112 | traps show fault addr | arm | PATTERN-low | arch/riscv/kernel/traps.c |
| 114 | lib/crc drop "glue" 文件名 | arm | PORTABLE-low | lib/crc/（机械重命名）|
| 119 | VA_BITS=52 ARCH_MMAP_RND_BITS_MAX | arm | **PATTERN** | arch/riscv/Kconfig（动态 Sv39/48/57）|
| 123 | fdt delete rng-seed after use | arm | ALREADY | 已清零 kaslr-seed（pi/fdt_early.c:24）|
| 124 | arm64 enable PREEMPT_LAZY | arm | ALREADY | 已 ARCH_HAS_PREEMPT_LAZY |
| 127 | KVM extract lock_all_vcpus（含 riscv）| arm | ALREADY | arch/riscv/kvm |
| 128 | dax devmap check pmd_trans_huge | arm | PATTERN-low | pgtable.h（riscv 未见 pmd_devmap，多半不适用）|
| 130 | gcc-8.1/binutils-2.30 minimum | arm | PORTABLE | 通用 kbuild |
| 132 | expose AIDR_EL1 via sysfs | arm | PATTERN-low | riscv 已 sysfs 暴露 mvendorid 等（部分 ALREADY）|
| 144 | perf data-type profiling arm64 | arm | PATTERN-low | tools/perf（需 riscv 指令解码）|
| 145 | generic printing of preemption model | arm | PORTABLE | 通用；riscv 可弃自定义 |
| 174/197 | sorttable mcount_loc（arm64 boot/build）| arm | ALREADY | 已 HAVE_BUILDTIME_MCOUNT_SORT |
| 181 | Handle .ARM.attributes in linker | arm | ALREADY | 已处理 .riscv.attributes（lds:171）|
| 190 | cacheinfo OOB write on bad DT | arm | **PATTERN** | arch/riscv/kernel/cacheinfo.c |
| 193 | kcov new uniq PC/EDGE/CMP modes | arm | **PORTABLE** | 通用 kernel/kcov.c；riscv 有 ARCH_HAS_KCOV |
| 196 | module RCU __module_text_address | arm | PORTABLE | tree-wide 通用 kernel/module |
| 其余 ~163 条 | KVM:arm64 NV/pKVM/hyp、ARM SoC/mach、DTS/defconfig/pull noise、arm64 ISA/HW（MPAM/MTE/POE/MOPS/AMU/BRBE/SPE）、boot-wrapper、perf-vendor、crypto-asm、toolchain workaround、trivial | arm/other | **N-A** | 见上「N-A 合并组」表；依赖 ARM 专有 HW/ISA 或厂商平台，无 riscv 对应，不扩展通用底座 |
