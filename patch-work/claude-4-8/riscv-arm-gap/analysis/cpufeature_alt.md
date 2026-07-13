# cpufeature-alt 可移植性分析（linux-arm-kernel → RISC-V）

> 类别：特性检测 / alternatives / errata / hwcap / sysreg（Tier B）。
> 判定纪律：riscv 有对应框架（`cpufeature.c` / `sys_hwprobe.c` / `alternative.c` / 四厂商 errata）但更年轻；
> arm64 **框架级改进**多判 PATTERN，依赖 arm64 sysreg/MIDR/EL2 编码的**具体项**判 N-A，**通用 cpu/hotplug/cpufreq/lib** 基础设施判 PORTABLE。
> 本文所有 riscv 落点均已在本地树 `/Users/zq/Desktop/patch-work/linux-riscv`（v7.2.0-rc3）核对存在。

## 摘要

- **系列总数**：144
- **四态计数**：ALREADY = 2 ｜ PORTABLE = 9 ｜ PATTERN = 10 ｜ N-A = 123

本类是全数据集里最"ARM 私有"的一桶：约 85% 是 KVM/arm64 的 **sysreg 编码、EL2/VHE、vGIC(v3/v5)、SME、SPE/BRBE/coresight、MTE、MPAM、厂商 MIDR errata、NV(嵌套虚拟化)**，均无 riscv 对应 → N-A。真正有价值的可移植点集中在**通用内核底座**（cpu/hotplug、cpufreq core、lib/crc）与**少数 arch 机制**（cmdline ISA 覆盖、module alternatives 校验、cpuinfo）。

### 本类 Top 候选（按价值排序）

| # | 系列 | 判定 | 一句话 |
|---|---|---|---|
| 1 | arm64: cmdline override for ID_AA64ISAR0_EL1.ATOMIC (#81) | **PATTERN** | riscv 缺"按扩展的 cmdline 关闭/覆盖"机制，真实缺口 |
| 2 | AArch64 AMUv1 average freq (#134) | **PORTABLE**+PATTERN | `drivers/cpufreq` core 的 `cpuinfo_avg_freq` sysfs + `arch_freq_get_on_cpu` 错误返回是通用 |
| 3 | arm64: modules: Reject malformed modules (#73) | **PATTERN** | "拒绝含内部 alternative 回调的模块" 可移植到 riscv `module.c` |
| 4 | lib/crc: CPU-feature static keys `__ro_after_init` (#121) | **PORTABLE** | 纯 `lib/`，riscv 自动受益 |
| 5 | arm64: HOTPLUG_PARALLEL for secondary CPUs (#9) | **ALREADY** | riscv 已 `select HOTPLUG_PARALLEL`（负向发现）；新增通用 `HOTPLUG_PARALLEL_SMT` 旋钮 PORTABLE |
| 6 | KVM: arm64: Errata mgmt for VM Live migration (#126) | **PATTERN(弱)** | 迁移感知的 errata 目标实现协商；riscv 已有 vendor-based errata |

---

## Top 可移植候选（深度）

### 1. arm64: Add command-line override for ID_AA64ISAR0_EL1.ATOMIC（#81）— PATTERN
- **原补丁**：<https://patchwork.kernel.org/project/linux-arm-kernel/patch/20250902-topic-arm64-pi-aa64isar0-atomic-v1-1-125f9538a230@linaro.org/> 状态=new
- **diff 核对**：改 `arch/arm64/kernel/pi/idreg-override.c` + `cpufeature.c` + `image-vars.h`。arm64 早期 PI 阶段用 `idreg-override` 框架，让 `arm64.nolse` 之类 cmdline 参数在检测前**屏蔽单个 ISA 特性**。
- **可移植点**：按扩展粒度的 cmdline 覆盖/禁用 ISA 特性。riscv 目前只能整体降级 satp（`pi/cmdline_early.c` 的 `no4lvl/no5lvl`），**无法**像 arm64 那样在 cmdline 关闭单个扩展（如临时禁用 Zabha/Svnapot 做排障或对齐异构核）。
- **riscv 落点**：`arch/riscv/kernel/cpufeature.c`（`riscv_fill_hwcap`/ISA 串解析处新增 override 过滤，已验证文件存在 `cpufeature.c:57+`）；早期可挂 `arch/riscv/kernel/pi/cmdline_early.c`（已存在）。
- **判定**：PATTERN——机制清晰、riscv 有 cmdline+ISA 解析底座，属真实功能缺口，需在 riscv 侧新写 override 表。

### 2. Add support for AArch64 AMUv1-based average freq（#134）— PORTABLE（core）+ PATTERN（arch）
- **原补丁**：<https://patchwork.kernel.org/project/linux-arm-kernel/patch/20250131162439.3843071-2-beata.michalska@arm.com/> 状态=new
- **diff 核对**：patch 1-2 改 `drivers/cpufreq/cpufreq.c`、`include/linux/cpufreq.h`（+ x86 `aperfmperf.c`/`proc.c`、arm64）——即 `arch_freq_get_on_cpu()` 允许返回错误 + 新增可选 `cpuinfo_avg_freq` sysfs 项，**均为架构无关核心**。patch 3-4 才是 arm64 AMU 实现。
- **可移植点**：cpufreq core 的 sysfs/hook 改动（PORTABLE，自动适用 riscv）；riscv 可选实现自己的 `arch_freq_get_on_cpu`（PATTERN）。
- **riscv 落点**：core 部分无需 riscv 改动即生效；arch 实现落 `arch/riscv/kernel/`（**已验证 riscv 当前无 `arch_freq_get_on_cpu`/`cpuinfo_avg_freq`**，riscv 无 AMU，实现价值有限）。
- **判定**：以 PORTABLE 记（主体是通用 cpufreq core）；arch 侧 PATTERN，价值低（无 AMU 硬件）。

### 3. arm64: modules: Reject loading of malformed modules（#73）— PATTERN
- **原补丁**：<https://patchwork.kernel.org/project/linux-arm-kernel/patch/20250922130427.2904977-2-abarnas@google.com/> 状态=new
- **diff 核对**：patch 1「Fail module loading if dynamic SCS patching fails」改 `arch/arm64/kernel/module.c`+`pi/patch-scs.c`——**arm64 专属**（动态影子调用栈 patching）。patch 2「Reject modules with internal alternative callbacks」才是可移植思想：拒绝 `.alternative` 段里引用**模块内部回调函数**的模块（加载后地址失效）。
- **可移植点**：module_finalize 阶段对 alternative 段做合法性校验（拒绝内部回调）。
- **riscv 落点**：`arch/riscv/kernel/module.c`（**已验证** `module_finalize` 在 `module.c:895`，`apply_module_alternatives` 在 `:903`）——riscv 同样应用 `.alternative` 段，可加同类校验硬化。
- **判定**：PATTERN——patch 2 机制适用 riscv；patch 1（SCS）arm64 专属不移植。

### 4. lib/crc: make the CPU feature static keys `__ro_after_init`（#121）— PORTABLE
- **原补丁**：<https://patchwork.kernel.org/project/linux-arm-kernel/patch/20250413154350.10819-1-ebiggers@kernel.org/> 状态=new（arch=generic）
- **可移植点**：把 CRC 用到的 CPU-feature static key 标 `__ro_after_init`（boot 后只读，防篡改硬化）。纯 `lib/crc`，架构无关。
- **riscv 落点**：无需 riscv 改动；riscv 的 Zbc-加速 CRC 路径自动受益。
- **判定**：PORTABLE（通用 lib，自动适用）。

### 5. arm64: Add HOTPLUG_PARALLEL support for secondary CPUs（#9）— ALREADY（负向发现）
- **原补丁**：<https://patchwork.kernel.org/project/linux-arm-kernel/patch/20260624092537.2916971-4-ruanjinjie@huawei.com/> 状态=new
- **核对**：series 含通用 patch「cpu/hotplug: Introduce CONFIG_HOTPLUG_PARALLEL_SMT」「Propagate bring-up status to arch_cpuhp_cleanup_kick_cpu()」+ arm64 `smp.c` 改造使用通用 split-startup。
- **riscv 现状**：**已验证 riscv `arch/riscv/Kconfig:205` 已 `select HOTPLUG_PARALLEL if HOTPLUG_CPU`**，`smpboot.c:184/236` 已实现 `arch_cpuhp_kick_ap_alive`/`cpuhp_ap_sync_alive` 走通用并行 bringup。故 arm64 本 series 的**主体价值 riscv 早已具备 → ALREADY**。
- **判定**：ALREADY（并行 bringup 主体）；仅新增的通用 `HOTPLUG_PARALLEL_SMT` 旋钮落 `kernel/cpu.c` 属 PORTABLE，riscv 合入后自动可用（riscv SMT 语义有限，收益低）。

### 6. KVM: arm64: Errata management for VM Live migration（#126）— PATTERN（弱）
- **原补丁**：<https://patchwork.kernel.org/project/linux-arm-kernel/patch/20250221140229.12588-4-shameerali.kolothum.thodi@huawei.com/> 状态=new
- **可移植点**：向 guest 暴露"目标实现 CPU 列表"（hypercall），使 guest 能按实现启用 errata，支持跨异构主机迁移。
- **riscv 落点**：`arch/riscv/kvm/`（**已验证** riscv KVM 已按 `riscv_cached_mvendorid/marchid` 启用 errata，`kvm/main.c:23`；且 `mvendorid/marchid/mimpid` 可经 ONE_REG 写入 `vcpu_onereg.c:164`）。迁移感知的目标实现协商可类比重写，但 arm64 侧强依赖 SMCCC/MIDR 语义。
- **判定**：PATTERN（弱）——概念可借鉴；riscv 已有 vendor-based errata 与可写 vendor id 底座（后者见 #129 ALREADY）。

---

## 全量判定表（覆盖每一条系列；同质 N-A 简述）

| # | 系列 | arch | 判定 | 可移植点 / riscv 落点（若有） |
|---|---|---|---|---|
| 1 | arm64: KVM: Backport VHE-only boot fixes | arm | N-A | VHE/E2H0/HCR_EL2 + ID_AA64MMFR4 编码，arm64 EL2 专属 |
| 2 | KVM: arm64: Implement support for SME | arm | N-A | SME(矩阵)无 riscv 对应（RVV≠SME）|
| 3 | KVM: arm64: Add GICv5 IRS support | arm | N-A | GICv5 中断控制器 HW |
| 4 | arm64: cpuinfo: Fix sysfs cleanup on failure | arm | **PATTERN** | cpuinfo sysfs 失败清理 → `arch/riscv/kernel/cpu.c`（低价值 bugfix 模式）|
| 5 | KVM: arm64: FEAT_NV2p1/NV3 | arm | N-A | 嵌套虚拟化 arm64 专属 |
| 6 | Backport ARM64 VHE boot fixes to 6.6.y | arm | N-A | 同 #1 |
| 7 | arm64/sysreg: Fix BWE field encoding ID_AA64DFR2 | arm | N-A | sysreg 编码 |
| 8 | arm64: errata: NVIDIA Olympus store/load ordering | arm | N-A | 厂商 MIDR errata（riscv errata 框架已 ALREADY）|
| 9 | arm64: Add HOTPLUG_PARALLEL support | arm | **ALREADY** | riscv 已 `select HOTPLUG_PARALLEL`（Kconfig:205）；通用 SMT 旋钮 PORTABLE |
| 10 | KVM: arm64: Add missing hyp_enter when trapping sysreg | arm | N-A | KVM hyp bugfix |
| 11 | arm64: errata: Handle Apple WFI State Loss | arm | N-A | Apple MIDR errata |
| 12 | ARM64 PMU Partitioning | arm | N-A | arm_pmuv3 HPMN 分区，属 perf-pmu；MDCR_EL2 专属 |
| 13 | arm64: errata: NVIDIA Olympus (v3) | arm | N-A | 同 #8 |
| 14 | arm64/cpufeature: Simplify c_show() | arm | **PATTERN** | cpuinfo 输出简化 → `arch/riscv/kernel/cpu.c:329`（低）|
| 15 | arm64: cpufeature: WORKAROUND_DISABLE_CNP | arm | N-A | CNP(TLB) + HiSilicon MIDR |
| 16 | KVM: arm64: FEAT_{S1POE,ATS1A} fixes | arm | N-A | sysreg 专属 |
| 17 | KVM: arm64 on s390 System Register Handling | arm | N-A | 跨 arch 泛化 KVM feature reg，arm64 sysreg 语义 |
| 18 | arm64: cpucaps: Keep entries sorted | arm | N-A | cpucaps 生成文件排序（arm64 工具链）|
| 19 | arm64: 2025 dpISA extensions | arm | N-A | arm64 hwcap/ISA 专属 |
| 20 | arm_mpam: MPAM v0.1 arch version | arm | N-A | MPAM 资源分区 HW |
| 21 | arm64: arch_timer: Improve errata handling | arm | N-A | arm_arch_timer（属 timer-pv）|
| 22 | arm64: errata: Reformat table for IDs | arm | N-A | errata 表排版 |
| 23 | KVM: s390: Introduce arm64 KVM - symlinks | arm | N-A | 跨 arch 符号链接 |
| 24 | coco/TSM: Host-side Arm CCA IDE setup | arm | N-A | Arm CCA/RME 机密计算（X.509/coco 通用部分已上游 generic）|
| 25 | KVM: arm64: pKVM init & feature detection fixes | arm | N-A | pKVM 专属 |
| 26 | KVM: arm64: PMUVer as unsigned | arm | N-A | sysreg 符号处理 |
| 27 | arm64: cpufeature: Fix GCIE field ordering | arm | N-A | GICv5 字段排序 |
| 28 | perf arm_spe: Dump IMPDEF events | arm | N-A | SPE 采样 + tools/perf |
| 29 | arm64/hwcap: Include kernel-hwcap.h in gen files | arm | N-A | 生成文件 Makefile 卫生 |
| 30 | arm64: FEAT_Debugv8p9 | arm | N-A | arm64 debug 特性（通用 hw_breakpoint 硬化点可 PATTERN，价值低）|
| 31 | KVM: arm64: Advertise ID_AA64PFR2.GCIE | arm | N-A | GICv5 CPU 接口 |
| 32 | KVM: arm64: First batch of vgic-v5 fixes | arm | N-A | vGIC |
| 33 | KVM: arm64: vGIC-v5 with PPI support | arm | N-A | vGIC |
| 34 | iommu/arm-smmu-v3: Update Arm errata | arm | N-A | SMMU HW |
| 35 | arm64: errata: CME DVMSync (mm_cpumask) | arm | N-A | CME DVMSync HW errata |
| 36 | support FEAT_LSUI | arm | N-A | arm64 非特权原子 ISA |
| 37 | arm_mpam: KVM/arm64 + resctrl glue | arm | N-A | MPAM |
| 38 | KVM: arm64: Read PMUVer as unsigned | arm | N-A | sysreg 符号 |
| 39 | selftests/arm64: sve2p1/cmpbr sigill hwcap | arm | N-A | arm64 ISA sigill 测试 |
| 40 | arm64: errata: Fix missing space + style | arm | N-A | 排版/风格（const 卫生 trivial）|
| 41 | selftests/arm64: cmpbr/sve2p1 sigill | arm | N-A | 同 #39 |
| 42 | Arm SMMU errata updates | arm | N-A | SMMU |
| 43 | KVM: arm64: Generalise RESx handling | arm | N-A | sysreg RESx 框架 |
| 44 | KVM: arm64: Enforce MTE disablement at EL2 | arm | N-A | MTE |
| 45 | Add support for FEAT_{LS64,LS64_V} | arm | N-A | 64B 原子 load/store ISA |
| 46 | arm64: errata: SI L1 downstream coherency | arm | N-A | 厂商 errata |
| 47 | clk: samsung: auto clock gating PM | arm | N-A | Samsung SoC clk 驱动 |
| 48 | KVM: arm64: FEAT_IDST | arm | N-A | sysreg 陷入 |
| 49 | arm64: cpufeature: MPAM v0.1 | arm | N-A | MPAM |
| 50 | arm: npcm: drop unused Kconfig ERRATA | arm | N-A | arm32 SoC Kconfig |
| 51 | KVM: arm64: guest feature trapping fixes | arm | N-A | Trace Buffer/MTE 陷入 |
| 52 | KVM: arm64: VTCR_EL2 → feature dependency | arm | N-A | sysreg 框架 |
| 53 | KVM: arm64: sys_regs: disable warning | arm | N-A | 编译器告警(stable) |
| 54 | coresight: trbe: trigger/circle buffer | generic | N-A | CoreSight TRBE 追踪 HW（arch=generic 但 arm HW）|
| 55 | arm64/sysreg: Remove ARM64_FEATURE_FIELD_BITS | arm | N-A | 删无用宏 |
| 56 | arm64: cpufeature: Unrestrict ID_AA64MMFR1 bits | arm | N-A | sysreg 位分配 |
| 57 | KVM: arm64: LR overflow infra (final) | arm | N-A | vGIC LR |
| 58 | KVM: arm64: SPE support | arm | N-A | 统计采样 HW |
| 59 | KVM: arm64: drop sysreg init error log | arm | N-A | 日志 trivial |
| 60 | KVM: arm64: add newline to sysreg init log | arm | N-A | 日志 trivial |
| 61 | KVM: arm64: LR overflow infrastructure | arm | N-A | vGIC LR |
| 62 | arm64: topology: Improve cpuinfo_avg_freq | arm | **PATTERN** | 配合 #134；AMU 无 riscv 对应，`arch_freq_get_on_cpu` 可选实现（价值低）|
| 63 | KVM: arm64: Prevent sysreg helper transposition | arm | **PATTERN** | 编译期类型检查 KVM sysreg 访问器 → riscv KVM 访问器防御（低）|
| 64 | arm64/sysreg: Prefix descriptor + ICH_VMCR_EL2 | arm | N-A | sysreg 生成工具 + vGIC |
| 65 | Enable new Arm architecture features (boot-wrapper) | arm | N-A | 固件 boot-wrapper |
| 66 | arm64: errata: Neoverse-V3AE | arm | N-A | cputype + errata |
| 67 | arm64/sysreg: Clean up TCR_EL1 macros | arm | N-A | sysreg 宏 |
| 68 | KVM: arm64: selftests: Sync ID_AA64PFR1/MPIDR/CLIDR | arm | N-A | selftests |
| 69 | arm64: cpufeature: Don't cpu_enable_mte() w/ KASAN_GENERIC | arm | N-A | MTE×KASAN 交互（riscv 无 MTE）|
| 70 | arm64/sysreg: Feat descriptor + ICH_VMCR_EL2 | arm | N-A | sysreg 工具 + vGIC |
| 71 | arm64/sysreg: Fix GIC CDEOI encoding | arm | N-A | GIC 指令编码 |
| 72 | KVM: arm64: De-specialise the timer UAPI | arm | N-A | KVM arm64 timer sysreg（属 timer-pv）|
| 73 | arm64: modules: Reject malformed modules | arm | **PATTERN** | 拒绝含内部 alternative 回调的模块 → `arch/riscv/kernel/module.c:895/903`（SCS patch 不移植）|
| 74 | support FEAT_LSUI + futex | arm | N-A | 同 #36 |
| 75 | KVM: arm64: selftests: ID_AA64ISAR3 | arm | N-A | selftests |
| 76 | KVM: arm64: RES0 of undefined registers | arm | N-A | sysreg RES0 |
| 77 | KVM: arm64: EL2 fields writable ID_AA64MMFR1 | arm | N-A | sysreg 可写 |
| 78 | gpio/pinctrl/mfd: compound literals syntax | arm | **PORTABLE** | 通用驱动 C 清理（无 riscv-arch 价值）|
| 79 | gpio: modernize bgpio_init - part 4 | generic | **PORTABLE** | `drivers/gpio` 通用框架重构（无 riscv-arch 价值）|
| 80 | gpio: modernize bgpio_init - part 3 | generic | **PORTABLE** | 同上 |
| 81 | arm64: cmdline override ID_AA64ISAR0.ATOMIC | arm | **PATTERN** | 按扩展 cmdline 覆盖 ISA → `arch/riscv/kernel/cpufeature.c` + `pi/cmdline_early.c`（真实缺口）|
| 82 | arm64: sysreg: Fix field defs + gen script | arm | N-A | sysreg 工具 |
| 83 | KVM: arm64: GICv5 legacy (GCIE_LEGACY) NV | arm | N-A | GIC + NV |
| 84 | gpio: modernize bgpio_init - part 2 | generic | **PORTABLE** | 同 #79 |
| 85 | gpio: modernize bgpio_init - part 1 | generic | **PORTABLE** | 同 #79 |
| 86 | Add workaround HIP10/HIP10C erratum 162200802 | arm | N-A | KVM GICD + 厂商 errata |
| 87 | KVM: arm64: selftests: Sync ID_AA64MMFR3 | arm | N-A | selftests |
| 88 | arm64/sysreg: Clean up TCR_XXX macros | arm | N-A | sysreg 宏 |
| 89 | KVM: arm64: FEAT_RASv1p1 + RAS selection | arm | N-A | RAS |
| 90 | KVM: arm64: Live system register access fixes | arm | N-A | KVM sysreg |
| 91 | arm64: cpufeature: __always_inline for GCS checks | arm | **PATTERN** | GCS(=Zicfiss) 特性检查强制内联 → `arch/riscv/kernel/usercfi.c`（低）|
| 92 | pinctrl: modernize bgpio_init | generic | **PORTABLE** | `drivers/pinctrl` 通用重构（无 riscv-arch 价值）|
| 93 | mfd: vexpress: new GPIO chip API | arm | N-A | vexpress(arm) 驱动 |
| 94 | arm64: sysreg: Fix and tidyup field defs | arm | N-A | sysreg |
| 95 | support SCTLR2_ELx | arm | N-A | arm64 新控制寄存器 |
| 96 | KVM: arm64: Check SYSREGS_ON_CPU | arm | N-A | KVM sysreg |
| 97 | KVM: arm64: Userspace GICv3 sysreg access | arm | N-A | GIC |
| 98 | arm64: kvm: sys_regs: string choices helper | arm | N-A | 清理 trivial |
| 99 | KVM: arm64: Config-driven deps TCR2/SCTLR/MDCR | arm | N-A | sysreg 框架 |
| 100 | phy: exynos-mipi-video: cam0 sysreg property | arm | N-A | Exynos PHY DT |
| 101 | arm64: errata: Ampere AC03_CPU_50 | arm | N-A | 厂商 errata |
| 102 | gpio: mmio: remove struct bgpio_pdata | arm | **PORTABLE** | `drivers/gpio` 通用重构（无 riscv-arch 价值）|
| 103 | KVM: arm64: GICv3 guests on GICv5 hosts | arm | N-A | GIC |
| 104 | Fixes for Exynos7870 MIPI PHY | arm | N-A | Exynos PHY |
| 105 | ARM64: errata: HIP10/HIP10C 162200803 | arm | N-A | 厂商 errata |
| 106 | support FEAT_MTE_STORE_ONLY | arm | N-A | MTE（PR_ prctl 通用但语义 MTE）|
| 107 | support FEAT_MTE_TAGGED_FAR | arm | N-A | MTE |
| 108 | arm64/perf: BRBE branch stack sampling | arm | N-A | BRBE 分支采样 HW（属 perf-pmu）|
| 109 | arm64: Drop workarounds after binutils bump | arm | N-A | arm64 汇编工具链 |
| 110 | KVM: arm64: vcpu sysreg accessor rework | arm | N-A | KVM sysreg |
| 111 | arm64: sysreg: Drag kconfig.h for vdso build | arm | N-A | 构建修复 |
| 112 | arm64: MIDR-based check for FEAT_ECBHB | arm | N-A | MIDR + Spectre |
| 113 | arm64: errata: AmpereOne AC04_CPU_23 | arm | N-A | 厂商 errata |
| 114 | KVM: arm64: Don't claim MTE_ASYNC | arm | N-A | MTE |
| 115 | Enable use of FPMR and ZT0 (boot-wrapper) | arm | N-A | SME 相关固件 |
| 116 | KVM: arm64: Revamp Fine Grained Trap handling | arm | N-A | FGT sysreg |
| 117 | arm64/cpufeature: ng_mappings `ro_after_init` | arm | **PATTERN** | boot 期特性标志 ro_after_init 硬化 → riscv boot flags（弱；ng/KPTI arm64 专属）|
| 118 | arm64: errata: Spectre-BHB MIDR sentinels | arm | N-A | MIDR 数组 bugfix |
| 119 | arm64/cpuinfo: only show one cpu in c_show() | arm | **PATTERN** | /proc/cpuinfo 语义 → `arch/riscv/kernel/cpu.c:329`（低）|
| 120 | arm64: errata: AmpereOne AC03_CPU_36 | arm | N-A | 厂商 errata |
| 121 | lib/crc: CPU feature static keys `__ro_after_init` | generic | **PORTABLE** | 纯 `lib/crc` 硬化，riscv 自动受益 |
| 122 | iommu/arm-smmu-v3: S2FWB feature detection | arm | N-A | SMMU |
| 123 | Two minor fixups around FEAT_E2H0 | arm | N-A | E2H0/VHE cpufeature |
| 124 | perf vendor events arm64: AmpereOne errata | arm | N-A | perf 厂商 JSON 事件 |
| 125 | KVM: arm64: Add NV GICv3 support | arm | N-A | NV + GIC |
| 126 | KVM: arm64: Errata mgmt for VM Live migration | arm | **PATTERN(弱)** | 迁移感知 errata 目标实现协商 → `arch/riscv/kvm/`（riscv 已有 vendor errata）|
| 127 | KVM: arm64: NV userspace ABI | arm | N-A | NV |
| 128 | Minor improvements for PIE/POE helpers | arm | N-A | 权限间接/覆盖 sysreg |
| 129 | KVM: arm64: writable MIDR/REVIDR | arm | **ALREADY** | riscv KVM 已可写 mvendorid/marchid/mimpid（`vcpu_onereg.c:164`）|
| 130 | KVM: arm64: SME in non-protected guests | arm | N-A | SME |
| 131 | PMU partitioning driver support | arm | N-A | 同 #12 |
| 132 | KVM: arm64: symbolic name ID_AA64PFR0.RME | arm | N-A | RME 清理 |
| 133 | arm64/hwcap: Remove SF8MMx references | arm | N-A | hwcap 清理 |
| 134 | AArch64 AMUv1-based average freq | arm | **PORTABLE** | cpufreq core `cpuinfo_avg_freq`+`arch_freq_get_on_cpu` 通用（`drivers/cpufreq/cpufreq.c`）；arch 实现 PATTERN |
| 135 | arm64: mitigate CVE-2024-7881 | arm | N-A | 推测执行 + SMCCC |
| 136 | arm64: errata: Ampere AC04_CPU_50 | arm | N-A | 厂商 errata |
| 137 | arm64/gcs: Fix documentation for HWCAP | arm | N-A | GCS(Zicfiss) hwcap 文档（riscv 有自己 hwprobe 文档）|
| 138 | arm64/sysreg: Sort sysreg by encoding | arm | N-A | sysreg 工具 |
| 139 | KVM: arm64: nv: Fix sysreg RESx-ication | arm | N-A | NV sysreg |
| 140 | Add support for NoTagAccess memory attribute | arm | N-A | MTE stage-2 |
| 141 | arm64: Support 2024 dpISA extensions | arm | N-A | arm64 hwcap/ISA |
| 142 | arm64: errata: Rework Spectre BHB (not assume safe) | arm | N-A | Spectre-BHB + MIDR（"未知即脆弱"默认思想不足以移植）|
| 143 | kvm/coresight: exclude guest/host | arm | N-A | CoreSight + KVM SPE/TRBE |

### 同质 N-A 分组小结（便于综合）
- **KVM arm64 sysreg / feature-framework / RESx / FGT / NV**（sysreg 编码 + EL2 语义）：#1,5,6,10,16,17,23,25,26,38,43,48,51,52,53,55,56,59,60,63*,67,68,70,75,76,77,82,88,89,90,94,95,96,98,99,110,111,116,123,127,128,132,139 —— arm64 私有，最大群。
- **vGIC / GIC(v3/v5/ITS/LR/CDEOI)**：#3,27,31,32,33,57,61,64,71,83,86,97,103,125,143 —— 中断控制器 HW（riscv 用 AIA）。
- **SME / SPE / BRBE / CoreSight-TRBE**（矩阵/采样/追踪 HW）：#2,12,28,54,58,108,115,130,131,143 —— 无 riscv 对应。
- **MTE**（内存标签）：#44,69,106,107,114,140 —— riscv 仅 Supm 掩码。
- **厂商 MIDR errata**：#8,11,13,15,35,46,66,86,101,105,112,113,118,120,136,142 —— riscv 四厂商 errata 框架已 ALREADY，具体项 arm64 专属。
- **SMMU / MPAM / 固件-bootwrapper / SoC-DT-驱动**：#20,21,22,24,34,37,42,47,49,50,65,93,100,104,122,124 —— HW/固件/板级专属。

> 注：#63 标 PATTERN（防御性编译检查），其余同群为 N-A。

---

## 结论

cpufeature-alt 桶对 RISC-V 的**架构移植价值极低**：144 条中 123 条 N-A，主体是 KVM/arm64 的 sysreg/EL2/vGIC/SME/SPE/MTE/MPAM/NV 与厂商 MIDR errata，均绑定 ARM 专有硬件/ISA/固件 ABI，riscv 无对应或走完全不同的机制（AIA、hwprobe、SBI、四厂商 errata）。

真正可借鉴的仅少数**通用底座**与 **arch 机制**：
- **PORTABLE**（自动/近自动适用）：`lib/crc` static key 硬化(#121)、cpufreq core `cpuinfo_avg_freq`(#134)；以及 7 条 gpio/pinctrl 通用驱动重构（无 riscv-arch 特异价值）。
- **PATTERN**（riscv 需重写）：**cmdline 按扩展覆盖 ISA(#81) 是唯一较高价值的真实缺口**；module alternatives 校验(#73)、cpuinfo c_show 系列(#4/14/119) 价值低。
- **ALREADY**（负向发现，防误报）：HOTPLUG_PARALLEL(#9) 与 KVM 可写 vendor id(#129) riscv 均已具备。

**给主代理的最强 3 条**：#81（PATTERN，`cpufeature.c`/`pi/`，cmdline ISA 覆盖）、#134（PORTABLE，`drivers/cpufreq`）、#73（PATTERN，`module.c`）。
