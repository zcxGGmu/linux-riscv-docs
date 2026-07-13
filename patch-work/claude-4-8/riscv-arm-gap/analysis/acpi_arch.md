# acpi-arch 可移植性分析（linux-arm-kernel → RISC-V）

> 输入：`data/by_category/acpi-arch.jsonl`（54 条系列，全部 Tier B）。
> 判定依据：`_baseline_riscv.md` + 本地内核树 `/Users/zq/Desktop/patch-work/linux-riscv`（v7.2.0-rc3）。
> 关键基线事实（已 Grep 核对存在）：
> - `arch/riscv/kernel/acpi.c`、`acpi_numa.c`；`drivers/acpi/riscv/{irq,cppc,cpuidle,rhct,rimt,init}.c`。
> - riscv **已有 ACPI CPPC-FFH**（`drivers/acpi/riscv/cppc.c`，走 `SBI_EXT_CPPC`）、**ACPI LPI cpuidle**（`cpuidle.c`，`RISCV_FFH_LPI_TYPE_SBI`）。
> - riscv **已 `select ACPI_SPCR_TABLE`** 并在 `arch/riscv/kernel/acpi.c:163` 调 `acpi_parse_spcr()`。
> - `drivers/acpi/apei/{ghes,ghes_helpers,hest,bert,erst,einj}.c` + `drivers/ras/{ras,cec}.c` 通用 RAS 框架齐备；`ghes.c` 已含 `task_work`/`memory_failure_cb`/`ghes_task_work`。
> - `drivers/acpi/pptt.c` 由**通用** `drivers/base/cacheinfo.c`（`cache_setup_acpi` weak）与 `arch_topology.c` 消费；riscv 走通用路径。
> - `drivers/iommu/iommu.c` 通用核 + `drivers/iommu/riscv/iommu.c`。

---

## 摘要

- **系列总数**：54（全 Tier B）
- **四态计数**：ALREADY 0 ｜ PORTABLE 26 ｜ PATTERN 2 ｜ N-A 26
  - 说明：riscv ACPI 底座（SPCR/CPPC-FFH/LPI/RINTC/RHCT/RIMT/SRAT）**已存在**，故本批补丁多为「通用核改进/重构」（PORTABLE，直接惠及 riscv）或「arm 专属表/固件 ABI」（N-A）。无纯 ALREADY（补丁均为增量而非底座本身）。
  - 6 条为**混合系列**（generic 通用部分 PORTABLE + arm 专属部分 N-A/PATTERN）：#1、#5、#13、#23、#33、#51。

### 本类 Top 候选（按 riscv 价值排序）
1. **#1 GICv5 IWB ACPI IRQ probe deferral (v4, 7p)** — **直接修补 riscv ACPI IRQ 代码** + 抽通用 ACPI 依赖基础设施。
2. **#8/#20 APEI: share GHES CPER helpers + DT FFH provider (10p)** — 把 firmware-first RAS 的 CPER/GHES 助手抽成可复用模块 + DT FFH provider（脱离 arm/ACPI 绑定）。
3. **#30 ras: share firmware-first estatus handling (12p)** — 通用 `drivers/ras/` estatus 核 + provider-ops 抽象。
4. **#33(PPTT 子集) + #41/#42/#44/#45** — 通用 ACPI PPTT 助手（cpumask/cache-id/level），供通用 cacheinfo/topology。
5. **#2 + #28 + #14 + #40 CPPC 框架改进** — 通用 CPPC 核（FFH 配对读钩子/FIE），riscv 已有 SBI CPPC-FFH 实现。
6. **#48 ACPI: Improve SPCR handling on SPCR-less systems** — riscv 直接调 `acpi_parse_spcr()`。
7. **#51 Support SMT control（通用部分）** — `cpu/SMT` + `arch_topology` OF SMT 控制，riscv 现无。
8. **#52 iommu: Fix longstanding probe issues** — 通用 IOMMU 核探测路径，惠及 riscv IOMMU。

---

## Top 可移植候选（深度，已 curl 核对 diff）

### 1. GICv5 IWB ACPI IRQ probe deferral（#1 v4 / #13 v1）
- **原补丁**：`irqchip/ACPI: Arm GICv5 IWB ACPI IRQ probe deferral`（https://patchwork.kernel.org/project/linux-arm-kernel/patch/20260709-gic-v5-acpi-iwb-probe-deferral-v4-1-48dae790f871@kernel.org/）状态=new
- **可移植点 / diff 实质**（curl 核对）：
  - `[1/7]` 新增 `acpi_device_clear_deps()` 于 **`include/linux/acpi.h`**（通用 ACPI 头）。
  - `[2/7][3/7][4/7]` **直接修补 riscv**：`riscv_acpi_irq_get_dep()` 循环终止、`acpi_get_handle()` 状态检查、`riscv_acpi_add_prt_dep()` 循环处理 —— 即本地 `drivers/acpi/riscv/irq.c:308/323/384/403`。
  - `[5/7]` 把 **RISC-V 中断控制器 autodep 从 riscv 私有搬进通用 `drivers/acpi/irq.c`**，供 GICv5 IWB 与 riscv 共用。
- **riscv 落点**：`drivers/acpi/riscv/irq.c`（已存在，patch 2/3/4 就是改它）、`drivers/acpi/irq.c`（通用汇合点）、`include/linux/acpi.h`。核对：`riscv_acpi_irq_get_dep`/`riscv_acpi_add_prt_dep` 确在树内。
- **判定**：**PORTABLE**（患 1/5 通用 ACPI 基础设施 + 2/3/4 本就是 riscv 代码；仅 6/7 GICv5 IWB/IORT 为 N-A）。**riscv 相关度最高**。

### 2. ACPI: APEI: share GHES CPER helpers + DT FFH provider（#8 v5 / #20 v3, 10p）
- **原补丁**：https://patchwork.kernel.org/project/linux-arm-kernel/patch/20260529-topics-ahmtib01-ras_ffh_arm_internal_review-v5-7-2e0500d42642@arm.com/ 状态=new
- **可移植点 / diff 实质**（curl `[07/10]`）：改 `drivers/Makefile`、`drivers/acpi/Kconfig`、`drivers/acpi/apei/{Kconfig,Makefile}`、`include/acpi/ghes.h`、`include/cxl/event.h` —— 把 GHES 的 CPER 读取/GHESv2 ack/estatus cache/vendor/CXL 助手抽成**独立可复用模块**，并新增 **DT FFH（devicetree firmware-first）provider**，使 firmware-first RAS 不再绑死 ACPI+arm。
- **riscv 落点**：`drivers/acpi/apei/ghes.c`、`include/acpi/ghes.h`（通用，riscv 编 ACPI 即得）；DT FFH 路径对 **DT-boot riscv** 平台直接有价值。
- **判定**：**PORTABLE**（通用 `drivers/acpi/apei/` + `include/acpi/`）。

### 3. ras: share firmware-first estatus handling（#30, 12p）
- **原补丁**：https://patchwork.kernel.org/project/linux-arm-kernel/patch/20251217112845.1814119-9-ahmed.tiba@arm.com/ 状态=new
- **可移植点 / diff 实质**（curl `[08/12]`）：向 `drivers/acpi/apei/ghes.c` 加 **estatus provider-ops（+157 行）**，把 estatus 核接口/实现/vendor 处理/queuing+IRQ-NMI/CPER 迭代助手下沉到通用 `drivers/ras/` 层（`efi/cper` 亦改用迭代助手）。
- **riscv 落点**：`drivers/ras/`、`drivers/acpi/apei/ghes.c`、`drivers/firmware/efi/cper.c`（均通用）。riscv 有 `drivers/ras/{ras,cec}.c` 底座可承接。
- **判定**：**PORTABLE**（通用 RAS 框架重构）。

### 4. ACPI/PPTT 助手族（#33 patches 1–5 / #41 / #42 / #44 / #45）
- **原补丁**：`arm_mpam: Add basic mpam driver`（https://patchwork.kernel.org/project/linux-arm-kernel/patch/20251119122305.302149-10-ben.horgan@arm.com/）+ james.morse `[03/33][04/33][05/33][06/33]` 独立 PPTT 补丁。
- **可移植点**：`acpi_pptt_cache_v1_full`、按 processor-container / cache_id 填 cpumask、按 cache-id 查 cache level、`acpi_count_levels()` 不再要求调用方清零。curl `[09/34]` 得到的是 MPAM 表解析（`drivers/acpi/arm64/mpam.c` 411 行，**N-A**）；但 PPTT 助手（1–5）落在**通用 `drivers/acpi/pptt.c`**。
- **riscv 落点**：`drivers/acpi/pptt.c`（通用）→ 由通用 `drivers/base/cacheinfo.c`（`cache_setup_acpi`）/`arch_topology.c` 消费，riscv ACPI 缓存/拓扑走此路径。
- **判定**：**PORTABLE**（PPTT 助手）；MPAM 驱动/表本体（#33 其余、#43）**N-A**（arm resctrl 类硬件）。

### 5. CPPC 框架改进（#2 / #28 / #14 / #40）
- **#2** `ACPI: CPPC: add paired FFH feedback-counter read hook`（https://patchwork.kernel.org/project/linux-arm-kernel/patch/20260708082818.808041-2-zhangpengjie2@huawei.com/）：curl 核对改 **`drivers/acpi/cppc_acpi.c`(+50) + `include/acpi/cppc_acpi.h`(+7)**，加通用 FFH 配对读 API。arm64 用 AMU sysreg 实现，**riscv 用 `drivers/acpi/riscv/cppc.c`（SBI）实现**同一钩子。
- **#28/#14/#40**：`cppc_perf_ctrs_in_pcc_cpu()` 导出、`cppc_fie_kworker_init()` 抽出、FIE 用 tick 更新 non-PCC、丢弃越界 `delivered_perf` 样本、FIE 告警打印修整 —— 全在通用 `drivers/acpi/cppc_acpi.c` / `drivers/cpufreq/cppc_cpufreq.c`。
- **riscv 落点**：`drivers/acpi/cppc_acpi.c`、`drivers/cpufreq/cppc_cpufreq.c`（通用）+ riscv 已有 FFH 后端 `drivers/acpi/riscv/cppc.c`。
- **判定**：**PORTABLE**（通用 CPPC 核）；`arch_freq_scale` 挂钩为 PATTERN（riscv `arch_topology`）。

### 6. ACPI: Improve SPCR handling on SPCR-less systems（#48, 2p）
- **原补丁**：https://patchwork.kernel.org/project/linux-arm-kernel/patch/20250620131309.126555-3-me@linux.beauty/ 状态=new
- **可移植点**：`acpi_parse_spcr()` 在 SPCR 支持关闭时返回 `-ENODEV`；SPCR 表缺失时抑制误导性 console 消息 —— 通用 `drivers/acpi/spcr.c`。
- **riscv 落点**：`drivers/acpi/spcr.c`（通用），**riscv 直接调用** `acpi_parse_spcr()`（`arch/riscv/kernel/acpi.c:163`），`select ACPI_SPCR_TABLE`。
- **判定**：**PORTABLE**（arm64 侧后续 console-msg 调整 #35/#37 为 N-A）。

### 7. Support SMT control（#51 通用部分, 4p）
- **原补丁**：https://patchwork.kernel.org/project/linux-arm-kernel/patch/20250311075143.61078-5-yangyicong@huawei.com/ 状态=new
- **可移植点**：`[1/4]` `cpu/SMT: Provide a default topology_is_primary_thread()`（**`kernel/cpu.c`** / `include/linux/topology.h`）、`[2/4]` `arch_topology: Support SMT control for OF based system`（**`drivers/base/arch_topology.c`**）。curl `[4/4]` 仅 `arch/arm64/Kconfig` 开 `HOTPLUG_SMT`。
- **riscv 落点**：`arch/riscv/Kconfig`（`select HOTPLUG_SMT`）+ 通用 `arch_topology`；riscv 无 `topology_is_primary_thread` 覆盖 → 直接吃通用默认。arm64 ACPI SMT（`[3/4]`）为 PATTERN。
- **判定**：**PORTABLE**（通用 SMT 基础设施）+ PATTERN（arch 挂钩）。

### 8. iommu: Fix the longstanding probe issues（#52, 4p）
- **原补丁**：https://patchwork.kernel.org/project/linux-arm-kernel/patch/d219663a3f23001f23d520a883ac622d70b4e642.1740753261.git.robin.murphy@arm.com/ 状态=new
- **可移植点**：通用 IOMMU 核探测路径修复（default domain race、`iommu_init_device()` 解析 ops、`dev->iommu` 状态一致性、DT/ACPI 解析纳入正规 probe 路径）—— `drivers/iommu/iommu.c`。
- **riscv 落点**：`drivers/iommu/iommu.c`（通用核，已存在 `iommu_probe_device_lock` 等）→ 惠及 `drivers/iommu/riscv/iommu.c`。
- **判定**：**PORTABLE**。

### 其他值得记录的通用改进（PORTABLE，未逐一 curl）
- **#17** `ACPI: processor: idle: 不传播 acpi_processor_ffh_lpi_probe() -ENODEV` → 通用 `drivers/acpi/processor_idle.c`，riscv 有 LPI-FFH（`drivers/acpi/riscv/cpuidle.c`）可受益。
- **#5** `cpu/hotplug: Fix NULL kobject in cpuhp_smt_enable()` → 通用 `kernel/cpu.c`（patch 2）；arm64 smp 部分 PATTERN（`arch/riscv/kernel/smpboot.c`）。
- **#23** GICv5 code-first ACPI boot：`[1/6]` irqdomain fwid `parent` 字段、`[2/6]` PCI/MSI `pci_msi_map_rid_ctlr_node()` **firmware-agnostic** → 通用 irqdomain / PCI-MSI，PORTABLE；GICv5 IRS/ITS/IWB 探测 N-A。
- **#47/#49** APEI 同步错误 task_work + SIGBUS → 通用 `drivers/acpi/apei/ghes.c`（机制**已在树内**：`task_work`/`memory_failure_cb`/`ghes_task_work`），SEA notify 由 arm64 触发；riscv 未来对接同步访问故障可复用。
- **#32** thermal core 父设备 + ACPI 停建 "device" sysfs 链 → 通用 `drivers/thermal/`、`drivers/acpi/{processor,fan,video}`。
- **#38** cpufreq `__free()` scope-based 清理 → 通用多子系统。
- **#11** `ACPI: Use LIST_HEAD()` → 通用 `drivers/acpi` 清理（jszhang，riscv 维护者）。
- **#21** `Rename get_acpi_id_for_cpu()→acpi_get_cpu_acpi_id() on non-x86` → 通用非-x86 重命名（当前树无该符号，纯头/通用改动）。

---

## 全量判定表（54 条）

| # | 系列 (arch, n) | 判定 | 可移植点 | riscv 落点 |
|---|---|---|---|---|
| 1 | GICv5 IWB ACPI IRQ probe deferral v4 (arm,7) | **PORTABLE** | acpi_device_clear_deps + riscv IRQ dep 修复 + autodep 搬入通用 irq.c | `drivers/acpi/riscv/irq.c`, `drivers/acpi/irq.c`, `include/linux/acpi.h` |
| 2 | CPPC FFH feedback-counter skew (arm,2) | **PORTABLE** | 通用 FFH 配对读钩子 | `drivers/acpi/cppc_acpi.c`; 后端 `drivers/acpi/riscv/cppc.c` |
| 3 | ACPI: IORT: validate RMR node bounds (generic,1) | N-A | IORT arm64 专属（bounds-check 思想可类比 RIMT） | (`drivers/acpi/riscv/rimt.c` 参考) |
| 4 | ACPI: APMT: validate node bounds (generic,1) | N-A | APMT arm 性能监控表专属 | — |
| 5 | arm64 acpi NULL kobject cpuhp_smt (arm,2) | **PORTABLE** | cpu/hotplug 核修复 (patch2) | `kernel/cpu.c`; arm64 smp→`arch/riscv/kernel/smpboot.c`(PATTERN) |
| 6 | mailbox bcm2835 ACPI RPi4 (generic,1) | N-A | SoC 专属驱动 ACPI glue | — |
| 7 | Armv8 RAS Extensions kernel-first (arm,16) | N-A | Armv8 RAS sysreg (ERX*)/AEST 专属 | — |
| 8 | APEI share GHES CPER helpers + DT FFH v5 (generic,10) | **PORTABLE** | GHES/CPER 助手抽模块 + DT FFH provider | `drivers/acpi/apei/`, `include/acpi/ghes.h` |
| 9 | APEI Handle repeated SEA error storms v2 (generic,1) | PATTERN | 错误风暴抑制逻辑 | `drivers/acpi/apei/ghes.c`（SEA notify=arm64 触发）|
| 10 | arm_scmi ACPI PCC transport (generic,9) | N-A | SCMI=arm 固件 ABI（riscv 用 SBI）；通用 fwnode 少量 | — |
| 11 | ACPI: Use LIST_HEAD() (generic,1) | **PORTABLE** | 通用 ACPI 清理 | `drivers/acpi/*`（通用）|
| 12 | arm64 realm probing RSI earlier (arm,4) | N-A | arm CCA Realm RSI/PSCI/SMCCC | — |
| 13 | GICv5 IWB ACPI IRQ probe deferral v1 (arm,2) | **PORTABLE** | =#1 早期版：riscv autodep 搬入通用 | `drivers/acpi/irq.c`（GICv5 部分 N-A）|
| 14 | cpufreq cppc discard out-of-range perf (generic,1) | **PORTABLE** | CPPC cpufreq 健壮性 | `drivers/cpufreq/cppc_cpufreq.c` |
| 15 | IORT Root Complex PASID on SMMUv3 (arm,3) | N-A | IORT + SMMUv3 arm IOMMU | — |
| 16 | arm64 cpuidle tolerate no deep PSCI (arm,1) | N-A | PSCI LPI arm 专属 | (`drivers/acpi/riscv/cpuidle.c` 用 SBI) |
| 17 | ACPI processor idle FFH LPI -ENODEV RFC (generic,1) | **PORTABLE** | 通用 idle 不传播 arch FFH -ENODEV | `drivers/acpi/processor_idle.c`；riscv LPI-FFH 受益 |
| 18 | ACPI AGDI newline v3 (generic,1) | N-A | AGDI arm64 驱动 trivial | — |
| 19 | acpi arm64 agdi newline (arm,1) | N-A | =#18 arm64 版 | — |
| 20 | cover APEI GHES CPER + DT FFH v3 (generic,10) | **PORTABLE** | =#8 早期版 | `drivers/acpi/apei/` |
| 21 | Rename get_acpi_id_for_cpu non-x86 (other,1) | **PORTABLE** | 通用非-x86 重命名 | `include/linux/acpi.h`（通用）|
| 22 | Arm LFA SMCCC timeout+platform drv (arm,2) | N-A | SMCCC 固件 ABI（riscv 用 SBI）| — |
| 23 | GICv5 Code first ACPI boot (generic,6) | **PORTABLE** | irqdomain fwid parent + PCI/MSI firmware-agnostic | `kernel/irq/irqdomain.c`, `drivers/pci/msi/`（GICv5 探测 N-A）|
| 24 | i2c xiic ACPI (generic,1) | N-A | 设备驱动 ACPI glue（arch 无关，riscv ACPI 本就支持）| — |
| 25 | ACPI AGDI interrupt signaling v6 (generic,1) | N-A | AGDI arm64 专属 | — |
| 26 | 8250_mtk ACPI (generic,1) | N-A | 串口驱动 ACPI glue（arch 无关）| — |
| 27 | ARM Error Source Table V2 (generic,17) | N-A | AEST arm RAS 专属 | — |
| 28 | cpufreq CPPC FIE ticks non-PCC (generic,3) | **PORTABLE** | CPPC 核抽出 + FIE tick 更新 | `drivers/acpi/cppc_acpi.c`, `drivers/cpufreq/cppc_cpufreq.c` |
| 29 | MAINTAINERS ARM64 ACPI (arm,1) | N-A | 元数据 | — |
| 30 | ras: share firmware-first estatus (generic,12) | **PORTABLE** | 通用 estatus 核 + provider-ops | `drivers/ras/`, `drivers/acpi/apei/ghes.c`, `drivers/firmware/efi/cper.c` |
| 31 | pinctrl/GPIO MediaTek MT8901 (generic,2) | N-A | SoC pinctrl 驱动 | — |
| 32 | thermal core parent device + ACPI sysfs (generic,8) | **PORTABLE** | 通用 thermal 核 + ACPI sysfs 链清理 | `drivers/thermal/`, `drivers/acpi/{processor,fan,video}` |
| 33 | arm_mpam basic driver (arm,34) | **PORTABLE** | PPTT 助手(1–5) 通用；MPAM 驱动/表 N-A | `drivers/acpi/pptt.c`（MPAM=`drivers/acpi/arm64/mpam.c` N-A）|
| 34 | arm64 acpi newline deferred APEI (arm,1) | N-A | arm64 trivial | — |
| 35 | arm64 acpi Drop SPCR console msg (arm,2) | N-A | arm64 console 消息（SPCR 核通用）| (`drivers/acpi/spcr.c` 通用)|
| 36 | APEI SEA storm (generic,1) | PATTERN | =#9 早期版 | `drivers/acpi/apei/ghes.c` |
| 37 | arm64 acpi fix console msg check (arm,1) | N-A | arm64 SPCR 消息 | — |
| 38 | cpufreq __free() cleanup (arm,6) | **PORTABLE** | scope-based 清理（多子系统）| `drivers/cpufreq/`, `drivers/thermal/`, `kernel/power/` |
| 39 | IORT memory leak iort_rmr_alloc_sids (generic,1) | N-A | IORT arm64 bugfix | — |
| 40 | cpufreq CPPC FIE warning prints (generic,2) | **PORTABLE** | CPPC FIE 告警修整 | `drivers/cpufreq/cppc_cpufreq.c` |
| 41 | PPTT stop acpi_count_levels clear [04/33] (generic,1) | **PORTABLE** | PPTT 语义修正 | `drivers/acpi/pptt.c` |
| 42 | PPTT cpumask from processor container [03/33] (generic,1) | **PORTABLE** | PPTT 助手 | `drivers/acpi/pptt.c` |
| 43 | ACPI MPAM Parse MPAM table [08/33] (generic,1) | N-A | MPAM 表 arm 专属 | `drivers/acpi/arm64/mpam.c` |
| 44 | PPTT cpumask from cache_id [06/33] (generic,1) | **PORTABLE** | PPTT 助手 | `drivers/acpi/pptt.c` |
| 45 | PPTT find cache level by cache-id [05/33] (generic,1) | **PORTABLE** | PPTT 助手 | `drivers/acpi/pptt.c` |
| 46 | clocksource standalone MMIO ARM arch timer (generic,4) | N-A | GTDT + arm_arch_timer（riscv 用 Sstc/SBI）| — |
| 47 | APEI hardlockup infinite SEA loop v19 (generic,2) | **PORTABLE** | 同步错误 task_work + SIGBUS（机制已在树内）| `drivers/acpi/apei/ghes.c`（SEA notify=arm64）|
| 48 | ACPI Improve SPCR handling SPCR-less v2 (generic,2) | **PORTABLE** | acpi_parse_spcr -ENODEV / 抑制误导消息 | `drivers/acpi/spcr.c`；riscv 调 `acpi.c:163` |
| 49 | APEI handle sync errors task work v18 (generic,2) | **PORTABLE** | =#47 早期版 | `drivers/acpi/apei/ghes.c` |
| 50 | /dev/mshv root partition driver (arm,9) | N-A | Hyper-V 专属；`acpi:numa export node_to_pxm` 通用 trivial | (`drivers/acpi/numa/srat.c`) |
| 51 | Support SMT control on arm64 (arm,4) | **PORTABLE** | cpu/SMT 默认 + arch_topology OF SMT 控制 | `kernel/cpu.c`, `drivers/base/arch_topology.c`, `arch/riscv/Kconfig` |
| 52 | iommu Fix longstanding probe issues (generic,4) | **PORTABLE** | 通用 IOMMU 核探测路径修复 | `drivers/iommu/iommu.c` → `drivers/iommu/riscv/` |
| 53 | ACPI GTDT relax Platform Timers count (generic,1) | N-A | GTDT arm timer 表 | — |
| 54 | serial 8250_mtk ACPI v2 (generic,1) | N-A | =#26 串口驱动 ACPI glue | — |

### 同质 N-A 分组说明
- **arm 专属 RAS/表**：#7、#27（AEST/Armv8-RAS），#43（MPAM 表），#3/#4/#15/#39（IORT/APMT），#46/#53（GTDT/arm-timer），#18/#19/#25（AGDI）— 依赖 arm 专属固件表/系统寄存器，riscv 用 RINTC/RHCT/RIMT/SRAT/Sstc，无对应。
- **arm 固件 ABI**：#10（SCMI/PCC）、#22（SMCCC）、#12（RSI/Realm）、#16（PSCI idle）— riscv 用 SBI；仅思想类比。
- **设备/SoC 驱动 ACPI glue**（arch 无关但非架构可移植项）：#6、#24、#26、#31、#54。
- **元数据/arm64 trivial**：#29、#34、#35、#37。
- **Hyper-V**：#50（唯 `node_to_pxm` 导出通用）。
