# §3 代码内 TODO/FIXME/桩 候选四态判定（RISC-V 贡献点静态扫描）

> 来源：`README.md` §3a（54 处代码级）+ §3b（2 处 DTS）。内核树只读：`/Users/zq/Desktop/patch-work/linux-riscv`（v7.2.0-rc3）。
> 判定语义：「该 TODO/桩是否代表值得且可行在 riscv 补上的真缺口」。逐一 Read 上下文核实。

## 摘要

- **候选总数**：56（§3a 54 + §3b 2）。
- **四态计数**：ALREADY 0 / PORTABLE 0 / **PATTERN 6（真缺口，仅 3 有实际价值）** / **N-A + 噪声 50**。
- **关键修正**：团队初判的「8 真缺口」经逐行核实后 **2 处证伪、降级为 N-A**：
  - **BPF-JIT 1/2 字节 RMW 原子**（comp64:615）——**不是缺口**：BPF verifier 自身（`kernel/bpf/verifier.c:6420 check_atomic_rmw`）就拒绝非 W/DW 的 RMW 原子；arm64 的 `emit_lse_atomic`/`emit_ll_sc_atomic` 也**只按 `isdw` 处理 W/DW**，同样不支持 B/H。riscv 的 `pr_err_once` 是**与 verifier 对齐的防御性死代码**。「arm64 已支持」的前提不成立。
  - **perf guest-OS callchain**（perf_callchain.c:32/43）——**价值极低**：x86（`arch/x86/events/core.c:2861,2979`）与 arm64（`arch/arm64/kernel/perf_callchain.c:23,34`）**均有逐字相同的 "don't support guest os callchain" TODO 并同样提前 return**。三家都没做 → 非架构差距，属 perf-core 级共性待办。

### 本批 Top 候选（按价值排序）

1. **IOMMU Second-Stage（G-stage/嵌套翻译）** `drivers/iommu/riscv/iommu.c:1149` — PATTERN，**高值**（VFIO 设备直通/虚机 DMA 隔离），与 kvm 轮重叠。
2. **KVM AIA IMSIC↔IOMMU 映射（IRQ bypass）** `arch/riscv/kvm/aia_imsic.c:773,864` — PATTERN，**高值**，**阻塞于 #1**（IOMMU MSI-remap/2nd-stage 未合），与 kvm 轮重叠。
3. **IMSIC Multi-MSI** `drivers/irqchip/irq-riscv-imsic-platform.c:230` — PATTERN，**中值**（多向量连续 MSI 设备，如部分 NVMe/NIC）。
4. **kprobes REJECTED 指令改模拟** `arch/riscv/kernel/probes/decode-insn.c:29` — PATTERN，低中值。
5. **PMU 虚拟化计数器协调** `drivers/perf/riscv_pmu_sbi.c:1132`+`arch/riscv/kvm/vcpu_pmu.c:320,343` — PATTERN，低中值（KVM PMU 已存在，为协调/设计 TODO），与 kvm 轮重叠。
6. **spinlock：static_key→alternative** `arch/riscv/include/asm/spinlock.h:18` — PATTERN，低值（清理/优化，非功能缺口，与 static_call 主题相关）。

---

## Top 深度候选

### 1. IOMMU Second-Stage（G-stage）翻译未合入 — `drivers/iommu/riscv/iommu.c:1149`

- **候选**：`iommu.c:1149`（来源：代码 TODO）——注释明言 *"the Second-Stage feature have not yet been merged, also issue IOTINVAL.GVMA once second-stage support is merged"*。
- **现状**：riscv IOMMU 驱动已支持 First-Stage（S/VS-stage，进程 DMA 隔离）与 iohgatp GSCID 失效路径（`iommu.c:1131-1152`），但 **G-stage（Second-Stage，虚机层地址翻译/嵌套）未合入**。同处 `iommu.c:1190` 亦注 SVA/PASID 未合（`inval_pdt=false, pc=NULL`）。故 `iodir_iotinval` 目前只发 `IOTINVAL.VMA`，缺 `IOTINVAL.GVMA`。
- **落点**：`drivers/iommu/riscv/iommu.c`（+ `iommu-bits.h` 的 iohgatp/GVMA 命令），机制对端参照 `drivers/iommu/intel/`（nested）/`drivers/iommu/arm/arm-smmu-v3/`（S2 + nested domain）。属 riscv IOMMU HW 专属实现，非通用层可 select。
- **判定**：**PATTERN**（高值）。G-stage 是 VFIO 设备直通/虚机 DMA 隔离的前置；riscv IOMMU 规范已定义（iohgatp/GSCID/IOTINVAL.GVMA 位域已在驱动中出现），属「规范已定、驱动待补」的在途工作。**与 kvm 轮的 IOMMU 主题交叉引用**。

### 2. KVM AIA IMSIC↔IOMMU 映射（设备直通 IRQ bypass）— `arch/riscv/kvm/aia_imsic.c:773,864`

- **候选**：`aia_imsic.c:773`（release 路径「Purge the IOMMU mapping ???」）、`:864`（update 路径「Update the IOMMU mapping ???」）。
- **现状**：KVM 已完整维护 IMSIC VS-file 的 **G-stage MMIO 映射**（`kvm_riscv_mmu_ioremap`/`iounmap`，`:770,858`）用于虚机 MSI 直达；但当设备经 IOMMU 直通时，**IOMMU 侧 MSI 地址重映射（把 guest IMSIC 地址翻到当前 VS-file 物理页）未接线**——故 vCPU 迁移换 VS-file 时无法同步更新 IOMMU MSI 表，两个 TODO 均带 `???` 表示设计未定。
- **落点**：`arch/riscv/kvm/aia_imsic.c` + `drivers/iommu/riscv/iommu.c`（MSI page-table / `msi_iova`），参照 arm64 `drivers/irqchip/irq-gic-v3-its.c` 的 ITS+SMMU IRQ bypass 与 `kvm/vgic/vgic-its.c`。
- **判定**：**PATTERN**（高值），**强依赖 #1**（IOMMU MSI-remap/2nd-stage）。这是「AIA 硬件加速 + 设备直通」闭环的最后一环。**与 kvm 轮的 AIA/IOMMU 主题重叠**。

### 3. IMSIC Multi-MSI 未支持 — `drivers/irqchip/irq-riscv-imsic-platform.c:230`

- **候选**：`irq-riscv-imsic-platform.c:230` — `imsic_irq_domain_alloc()` 内 `if (nr_irqs > 1) return -EOPNOTSUPP;`。
- **现状**：IMSIC irqdomain 一次只分配 1 个向量；单设备请求**连续多个 MSI（Multi-MSI，非 MSI-X）**会被拒。affinity/force-move/单 MSI 均已实现（`:216,207`）。
- **落点**：`drivers/irqchip/irq-riscv-imsic-platform.c`（`imsic_irq_domain_alloc` + `irq-riscv-imsic-state.c` 的向量分配需支持连续块 + 对齐），参照 `drivers/irqchip/irq-gic-v3-mbi.c`/x86 `arch/x86/kernel/apic/vector.c` 的多向量连续分配。
- **判定**：**PATTERN**（中值）。属 riscv irqchip 驱动增量，机制清晰；受益面为需连续 MSI 的少数设备（部分 NVMe/传统 NIC，多数走 MSI-X 不受影响）。

### 4. kprobes REJECTED 指令改模拟 — `arch/riscv/kernel/probes/decode-insn.c:29`

- **候选**：`decode-insn.c:29` — 注释「the REJECTED ones below need to be implemented」；当前 `c_jal`、`c_ebreak`（`:32-33`）及 `system`/`fence`（`:24-25`）被 `RISCV_INSN_REJECTED`。命中 REJECTED 的 kprobe 在 `kprobes.c:89` 返回 `-EINVAL`。
- **现状**：kprobes/uprobes 框架完备（基线已列），jal/jalr/auipc/branch/c_j/c_jr/c_jalr/c_beqz/c_bnez 已 SIMULATE；仅少数指令仍 REJECTED（无法在其上下探针）。
- **落点**：`arch/riscv/kernel/probes/simulate-insn.c`（新增 c_jal 等的模拟器）+ `decode-insn.c` 改 `SET_SIMULATE`，参照 arm64 `arch/arm64/kernel/probes/simulate-insn.c`。
- **判定**：**PATTERN**（低中值）。非功能性阻断（kprobes 整体可用），仅覆盖率缺口；system/fence 类通常本就不宜探测。

### 5. PMU 虚拟化计数器协调 — `drivers/perf/riscv_pmu_sbi.c:1132` + `arch/riscv/kvm/vcpu_pmu.c:320,343`

- **候选**：`riscv_pmu_sbi.c:1132`（溢出处理「need to stop the guest counters once virtualization support is added」）；`vcpu_pmu.c:320`（「Should we keep it for RISC-V ?」，注明 ARM64 这样做而 x86 不做）；`:343`（「Do we really want to clear the value in hardware counter」）。
- **现状**：KVM PMU 虚拟化**已存在**（`arch/riscv/kvm/vcpu_pmu.c` 全文件 + `vcpu_sbi_pmu.c`），三处均为**设计取舍/协调 TODO**而非硬缺口：host PMU 溢出路径尚未在 guest 运行时停计数（可能串扰）；guest 计数器清零/重载语义待定。
- **落点**：`arch/riscv/kvm/vcpu_pmu.c` + `drivers/perf/riscv_pmu_sbi.c`（溢出中断路径感知 guest 态），参照 arm64 `arch/arm64/kvm/pmu-emul.c`。
- **判定**：**PATTERN**（低中值，精修类）。**与 kvm 轮 PMU 主题重叠**，交叉引用即可。

### 6. spinlock：以 alternative 取代 static key — `arch/riscv/include/asm/spinlock.h:18`

- **候选**：`spinlock.h:18` — 「Use an alternative instead of a static key when we are able to parse the extensions string earlier in the boot process」。
- **现状**：combo-spinlock（ticket↔qspinlock 运行时切换，基线已列）用 `DECLARE_STATIC_KEY_TRUE(qspinlock_key)` + `static_branch_unlikely` 选路（`:21-29`）——**功能完整**。TODO 仅想在 boot 早期解析扩展串后改用 alternative（省一次 static-key 判定、更早定型）。
- **落点**：`arch/riscv/include/asm/spinlock.h` + `arch/riscv/kernel/cpufeature.c`（扩展串早解析 + alternative patch），与 static_call/text-patch 主题相关。
- **判定**：**PATTERN**（低值）。纯优化/清理，非功能缺口；收益微小。

---

## 全量判定表

> 8 处「真缺口」候选中，**6 判 PATTERN**（仅前 3 有实际价值），**2 经核实降级 N-A**（见摘要「关键修正」）。其余 ~46 处为噪声，成组标注。

### A. 真缺口（PATTERN，6 处 / 覆盖 12 行）

| 候选 | 来源 | 判定 | 缺口性质 / riscv 落点 | 备注（arm64/x86 状态） |
|---|---|---|---|---|
| iommu.c:1149 | 代码TODO | **PATTERN** | G-stage/2nd-stage 翻译未合；`drivers/iommu/riscv/iommu.c` | arm64=arm-smmu-v3 nested；高值，kvm 轮重叠 |
| aia_imsic.c:773,864 | 代码TODO | **PATTERN** | IMSIC↔IOMMU MSI 重映射（IRQ bypass）；`kvm/aia_imsic.c`+`iommu/riscv/` | arm64=GICv4 ITS+SMMU；依赖 iommu.c:1149；kvm 轮重叠 |
| irq-riscv-imsic-platform.c:230 | 代码TODO | **PATTERN** | Multi-MSI 连续向量分配；`irq-riscv-imsic-{platform,state}.c` | arm64/x86 已支持多向量；中值 |
| decode-insn.c:29 (+kprobes.c:89) | 代码TODO | **PATTERN** | REJECTED 指令补模拟；`probes/simulate-insn.c` | arm64 有对应 simulate；低中值 |
| riscv_pmu_sbi.c:1132 (+vcpu_pmu.c:320,343) | 代码TODO | **PATTERN** | guest 态 PMU 计数协调；`kvm/vcpu_pmu.c`+`perf/riscv_pmu_sbi.c` | arm64=pmu-emul；精修类，kvm 轮重叠 |
| spinlock.h:18 | 代码TODO | **PATTERN** | static_key→alternative；`asm/spinlock.h`+`cpufeature.c` | 低值优化；static_call 主题相关 |

### B. 经核实降级为 N-A（原列真缺口，2 处 / 覆盖 5 行）

| 候选 | 来源 | 判定 | 证伪依据 |
|---|---|---|---|
| bpf_jit_comp64.c:615（1/2字节 RMW 原子） | 代码TODO | **N-A（防御死代码）** | BPF verifier `check_atomic_rmw`（verifier.c:6420）+ arm64 `emit_lse_atomic`（isdw-only）**均只支持 W/DW**；B/H RMW 全平台不合法。附 comp32:1277（RV32 仅 BPF_ADD 原子）=低值 PATTERN、comp32:1292（RV32 DW 原子）=N-A（无 RV32 64位 AMO HW） |
| perf_callchain.c:32,43（guest-OS callchain） | 代码TODO | **N-A（共性待办，非架构差距）** | x86(core.c:2861,2979)、arm64(perf_callchain.c:23,34) **逐字相同 TODO + 提前 return**；三家都没做，价值极低 |

### C. 噪声成组（~46 行）

| 组 | 行（文件:行） | 判定 | 理由 |
|---|---|---|---|
| **misaligned UABI 常量+探测机制**（12） | hwprobe.h:96/106/111；traps_misaligned.c:204；unaligned_access_speed.c:25/324/332/333/347/348/373/383；Kconfig:977 | **噪声** | `*_UNSUPPORTED` 是 UAPI 常量定义 + boot 探速解析/per-cpu 初始化 + Kconfig 帮助文；riscv 已有完整 misaligned 模拟+探测（基线）。均非缺口 |
| **运行时能力日志 pr_\***（9） | acpi.c:93；cpufeature.c:1080；module.c:358/365；sbi.c:142；process.c:137；riscv_pmu.c:319；riscv_pmu_sbi.c:1450；bpf_jit.h:202；vcpu_sbi.c:610 | **噪声** | 均为 pr_err/warn/info/debug 或 SBI-v0.1 遗留分支，报告运行时状态，非待办 |
| **ALREADY 特性的正常分支**（6） | usercfi.c:291/299/345/441/491（影子栈/IBT）；vector.c:193（RVV） | **噪声（ALREADY）** | Zicfiss/Zicfilp/RVV 均已实现（基线）；这些是「未启用则跳过」的正常运行时守卫 |
| **by-design / N-A 语义**（10） | sys_riscv.c:84(ni_syscall)；image.h:16(无大端 RISC-V)；mmio.h:109(清理注释)；init.c:263(无 highmem)/822(SATP 解释注释)；purgatory/Makefile:49(构建注释)；head.S:347(遗留 spinwait 启动微优化)；iommu.c:232(无轮询回退)/774(HW 探测防御)；vcpu_sbi_replace.c:131(嵌套虚拟化未实现的防御 fallthrough) | **N-A/噪声** | 或按设计如此、或 riscv 无对应语义、或纯注释/构建；vcpu_sbi_replace.c:131 关联「嵌套虚拟化」独立大特性（kvm 轮范畴），此行本身仅防御性返回 not-supported |

### D. §3b DTS 板级（2 处）

| 候选 | 判定 | 理由 |
|---|---|---|
| pic64gx-pinctrl.dtsi:76（标签重整）；jh7110-orangepi-rv.dts:47（GPIO21 带外 IRQ 缺 pinctrl） | **N-A（板级）** | 具体开发板 DTS 待办，非架构可移植缺口 |

---

## 结论

- **真正值得投入的真缺口 = 3**：IOMMU Second-Stage、KVM AIA IMSIC↔IOMMU 映射、IMSIC Multi-MSI（前两者构成「设备直通/IRQ bypass」闭环，且与 **kvm 轮**、IOMMU 主题深度重叠——建议合并为一个「AIA+IOMMU 直通」贡献簇）。
- **低值真缺口 = 3**：kprobes REJECTED 模拟、PMU 虚拟化协调、spinlock alternative 化。
- **降级 N-A = 2**：BPF 1/2 字节 RMW（防御死代码）、perf guest callchain（x86/arm64 亦无）。
- **纯噪声/N-A = 46（§3a 44 + §3b 2）**：常量定义、能力日志、ALREADY 特性守卫、by-design 语义、板级 DTS。
- 真缺口:噪声 ≈ **6:46 ≈ 1:7.7**（若只计有价值的 3 处则 ≈ 1:15），比初估 1:3 更偏噪声——原因是逐行核实排除了防御性/共性待办的假阳。
