# ①ISA 批准差集 —— 特权 / RAS / QoS / 调试簇

> 内核树（只读）：`/Users/zq/Desktop/patch-work/linux-riscv`（Linux v7.2.0-rc3）。
> 判定语义：「该批准扩展是否值得且可行地在 riscv 内核补上」。四态 = ALREADY / PORTABLE / PATTERN / N-A。
> 每条 ① 候选均已（a）联网核实 ratified 状态与年份；（b）搜 lore/LWN/patchwork 判 greenfield 度。

## 四态计数小结

| 判定 | 数量 | 候选 |
|---|---|---|
| ALREADY | 0 | （本簇候选无一在 `riscv_isa_ext[]` 内；`smstateen` 在集内但为基线而非候选） |
| PORTABLE | 1 | **Ssqosid**（通用 `fs/resctrl/` 已整树在，arch 仅接线） |
| PATTERN | 3 | **Sdtrig**（新 `hw_breakpoint.c`）、**Ssdbltrp**（traps/entry+KVM）、**Ssstateen**（低，门控用途） |
| N-A | 1 | **Smdbltrp**（M 态双陷入，S 态内核无直接工作，属固件/OpenSBI） |

**本轮头号可动作缺口：Ssqosid（QoS）** —— 见下方「resctrl 修正」显著结论。
**四条主候选全部为「真缺口 + 已有活跃在途 RFC」**，无一处于无人认领的纯 greenfield（详见 §6 greenfield 表）。

---

## 0. resctrl 修正结论（推翻第三轮 `riscv-contrib-scan` 的 N-A 判定）

第三轮把 resctrl/MPAM 判为 N-A「RISC-V 无对应硬件」——**该结论错误，本轮予以推翻**：

1. **硬件存在**：`Ssqosid`（QoS Identifiers 扩展，v1.0 已批准，随 Priv 1.13 纳入；CBQRI 规范 2024）即 RISC-V 的 QoS 硬件对端，功能对位 x86 RDT / arm64 MPAM。它提供 `srmcfg` S/HS 态 CSR，承载 RCID + MCID 两个标识符随 hart 请求下发到共享资源控制器。
2. **通用层已整树在**：只读核实 `fs/resctrl/` **已在内核树内**且完整——`rdtgroup.c`(117 KB)、`monitor.c`(53 KB)、`ctrlmondata.c`、`pseudo_lock.c`、`internal.h`、`Kconfig`、`Makefile` 俱全。该目录正是从 x86 抽出的**架构无关 resctrl 文件系统**，供各 arch 复用。
3. **别家已接线，唯 riscv 缺**：`grep -rn ARCH_HAS_CPU_RESCTRL arch/` → `arch/Kconfig`（定义）+ `arch/x86/Kconfig` + `arch/arm64/Kconfig` **三处 select，独缺 arch/riscv**。arm64 侧 `ARM64_MPAM`（`arch/arm64/Kconfig:2053-2056`）`select ARCH_HAS_CPU_RESCTRL` + `ARM64_MPAM_DRIVER`——**证明 MPAM 已把 resctrl 复用跑通，riscv 走同一条路即可**。
4. `fs/resctrl/Kconfig`：`RESCTRL_FS` `depends on ARCH_HAS_CPU_RESCTRL`——riscv 只要 `select` 它即可点亮整套 resctrl 用户态 ABI。

**结论**：Ssqosid/resctrl 是**明确高价值、可动作**的缺口，**不再是 N-A**。

---

## 1. Ssqosid（QoS，≈ x86 RDT / arm64 MPAM）—— 本轮头号

- **候选**：`Ssqosid`（来源：`cpufeature.c` 无 `ssqosid`；`hwcap.h` 无 `RISCV_ISA_EXT_SSQOSID`；`arch/riscv` 全树 **零 `srmcfg`**）。
- **现状（只读核实）**：
  - `grep -w ssqosid arch/riscv/kernel/cpufeature.c` → **无**（未识别）。
  - `grep -rn srmcfg arch/riscv/` → **全树零匹配**（CSR 未定义、无上下文切换）。
  - `arch/riscv/Kconfig` 未 `select ARCH_HAS_CPU_RESCTRL`（`grep -rn RESCTRL arch/riscv/` 空）。
  - 通用 `fs/resctrl/` **已在树内**（见 §0）；`include/linux/resctrl.h` 已备完整 arch glue 结构体（`resctrl_schema`/`resctrl_cache`/`resctrl_membw`/`resctrl_mon`/`resctrl_staged_config`）。
- **落点**：
  1. `arch/riscv/kernel/cpufeature.c` —— `__RISCV_ISA_EXT_DATA(ssqosid, …)` 探测 + `hwcap.h` 加 `RISCV_ISA_EXT_SSQOSID`。
  2. `arch/riscv/Kconfig` —— `select ARCH_HAS_CPU_RESCTRL`（点亮 `RESCTRL_FS`）。
  3. **`arch/riscv/include/asm/resctrl.h`（新）** —— 提供 `resctrl_arch_sched_in()` 等 arch glue，在任务切入时把 `RCID|MCID` 写入 `srmcfg` CSR。**对端参照**：x86 `arch/x86/include/asm/resctrl.h:100` `__resctrl_sched_in(tsk)` 把 CLOSid/RMID 写 `IA32_PQR_MSR`（`:167` 处调用）——riscv 完全镜像此模型。
  4. **上下文切换机制**：`srmcfg` 可复用现有 per-task CSR 模式——`thread_struct`（`arch/riscv/include/asm/processor.h:106`）已有 `envcfg` 字段（`:113`），`switch_to.h:84` 已有 `__switch_to_envcfg(next)` 钩子（`:73` `envcfg_update_bits`）；`srmcfg` 依样添加 `thread` 字段 + 切换钩子。
  5. **CBQRI 控制器**：cache/带宽控制器为**内存映射寄存器**（非 CSR），需一个 arch 侧探测 + 编程的 controller 驱动——此部分是 PATTERN 味最重的 arch 工作（相较 srmcfg 与 fs 复用而言）。
- **判定**：**PORTABLE**（headline）。最大红利——resctrl 用户态文件系统/ABI——**已整树在树内、免费复用**；arch 侧核心为 `select` + `srmcfg` sched-in glue（少量、有 x86/arm64 双对端可抄）。CBQRI controller MMIO 编程属 PATTERN 子块，但不改变「通用层已就绪」的 PORTABLE 主基调。
  - **greenfield 度**：**真缺口，但已有高度活跃在途工作，非无人认领**。Drew Fustini（BayLibre→现推进者）主导，已迭代至 **`[PATCH RFC v2 xx/17]`（LKML，2026-02）** 的 17 补丁大系列（`RISC-V: Add support for srmcfg CSR from Ssqosid ext`）；CSR 早期名 `sqoscfg` 已按批准规范改名 `srmcfg`。LWN 报道 [Articles/1038951](https://lwn.net/Articles/1038951/)。LPC 2025 有专题（CBQRI / RQSC / resctrl），仍有开放设计题（resctrl 是否新增带宽资源类型、DT vs ACPI RQSC 表）。**贡献策略：宜跟随/补强 Fustini 系列，而非另起炉灶。**

---

## 2. Sdtrig（调试触发器 = 硬件断点 / 观察点，≈ arm64 `hw_breakpoint.c`）

- **候选**：`Sdtrig`（来源：`cpufeature.c` 无 `sdtrig`；`arch/riscv` **零 `hw_breakpoint*`**；未 `select HAVE_HW_BREAKPOINT`）。
- **现状（只读核实）**：
  - `find arch/riscv -iname '*hw_breakpoint*'` → **无**；`grep -rn HAVE_HW_BREAKPOINT arch/riscv/` → **无**（perf hw_breakpoint / ptrace HW watchpoint / kgdb 硬件断点全部未接）。
  - `csr.h` 无 `CSR_TSELECT/TDATA1-3/TINFO/TCONTROL/SCONTEXT`（Sdtrig 触发器 CSR 全缺）。
  - `arch/riscv/kernel/ptrace.c:375` `riscv_user_regset[]` 仅 `REGSET_X/F/V/TAGGED_ADDR_CTRL/CFI`——**无 `REGSET_HW_BREAK/REGSET_HW_WATCH`**（arm64 有 `NT_ARM_HW_BREAK`/`NT_ARM_HW_WATCH`）。
- **落点**：
  1. **`arch/riscv/kernel/hw_breakpoint.c`（全新）** + `arch/riscv/include/asm/hw_breakpoint.h` + `Kconfig` `select HAVE_HW_BREAKPOINT`。**对端参照**：`arch/arm64/kernel/hw_breakpoint.c`（**1021 行**，已核实存在）。
  2. **接 perf**：实现 `arch_install_hw_breakpoint`/`arch_uninstall_hw_breakpoint`/`hw_breakpoint_arch_parse` 等 perf `HW_BREAKPOINT` 回调。
  3. **接 ptrace**：`ptrace.c:375` `riscv_user_regset[]` 增 `REGSET_HW_BREAK`/`REGSET_HW_WATCH`（镜像 arm64 regset）。
  4. **接 kgdb**：`arch/riscv/kernel/kgdb.c` 硬件断点钩子。
  5. **关键架构差异（务必注意）**：RISC-V S 态**不直接访问触发器 CSR**——触发器由 M 态拥有，S 态经 **SBI Debug Trigger 扩展**（`riscv-sbi-doc/ext-debug-triggers`）install/uninstall/update。故 `hw_breakpoint.c` 走 SBI 调用，**不同于 arm64 直接编程 debug 寄存器**。单步用 Sdtrig 的 `icount`（规范无 resume 标志，须移除断点后 icount 单步）。
- **判定**：**PATTERN**。arm64 有成熟 1021 行对端；riscv 需全新 arch 文件 + perf/ptrace/kgdb 三方接线，经 SBI 中介。价值高（GDB 硬件观察点、内核 kgdb、perf mem 事件全依赖之）。
  - **greenfield 度**：**真缺口，在途工作活跃**。两条谱系：(1) **hw_breakpoint 框架**——Himanshu Chauhan（Ventana，2024-02 首发 RFC）+ Jesse Taube（Rivos，2025-07）合流为 **8 补丁系列（2025-08）**`riscv: add initial support for hardware breakpoints`（perf + SBI Debug Trigger + ptrace regset + icount 单步 + selftests；LWN [1030993](https://lwn.net/Articles/1030993/)、[963234](https://lwn.net/Articles/963234/)）；Taube 实习结束后由 Chauhan 接手。(2) **Sdtrig CSR + KVM**——Max Hsu / Yong-Xuan Wang 系列（ISA 解析 + CSR 定义 + DT + KVM `hcontext/scontext`；LWN [967153](https://lwn.net/Articles/967153/)）。**贡献策略：补强现有 8 补丁系列（如虚拟化、内核态触发器仍待办）或复审。**

---

## 3. Ssdbltrp / Smdbltrp（双陷入 RAS）

- **候选**：`Ssdbltrp`（S 态）/ `Smdbltrp`（M 态）（来源：`cpufeature.c` 无二者；`ENVCFG` flags `csr.h:214-231` **无 DTE 位**）。
- **现状（只读核实）**：
  - `grep -wE 'ssdbltrp|smdbltrp' cpufeature.c` → **无**（未识别）。
  - `csr.h` `xENVCFG flags`（`:214-231`：STCE/PBMTE/ADUE/PMM/CBZE/CBCFE/LPE/SSE/CBIE/FIOM）**无 `ENVCFG_DTE`**（bit 59）；`sstatus` 无 `SDT`（bit 24）。
  - `traps.c`：现有 `do_trap_error`（`:132`）、`DO_ERROR_INFO` 宏族（`:147`+）、`die()`（`:76`）、NMI 入口（`irqentry_nmi_enter`）——**无双陷入（异常码 16）处理路径**。
  - **FWFT 已部分落地**：`sbi.h:38` `SBI_EXT_FWFT`、**`sbi.h:429` `SBI_FWFT_DOUBLE_TRAP = 0x3` 已在树内**——即 Clément Léger 系列的 SBI 固件特性底座已合入，但 `ssdbltrp` 本体（cpufeature 解析 + `sstatus.SDT` 管理 + DTE 使能 + 临界错误处理 + KVM 接线）**尚未接**。
  - KVM：`vcpu.c:727` 现仅 swap `host_senvcfg`；无 `henvcfg.DTE`（bit 59）guest 接线。
- **落点**：
  1. `cpufeature.c` + `hwcap.h` —— 识别 `ssdbltrp`。
  2. `csr.h` —— 加 `ENVCFG_DTE`(bit 59) + `SSTATUS_SDT`(bit 24)（H 扩展再加 `henvcfg.DTE`/`vsstatus.SDT`）。
  3. `arch/riscv/kernel/traps.c` / entry（`entry.S`）—— 陷入进出正确 set/clear `sstatus.SDT`；异常码 16（double trap，**不可委派**，`medeleg/hedeleg` bit16 只读 0）的临界错误处理器（依赖 `mtval2`）。
  4. **KVM**：经已在树的 `SBI_FWFT_DOUBLE_TRAP` 走 FWFT 使能；`henvcfg.DTE` guest 上下文（`arch/riscv/kvm/vcpu.c`）。
- **判定**：**Ssdbltrp → PATTERN**（arch trap/entry 的 SDT 状态机 + KVM FWFT glue，OS 价值中等——主要是让 S 态在临界不可重入期正确升级到 M 态而非静默错乱，属 RAS 健壮性）。**Smdbltrp → N-A**（M 态双陷入 → RNMI/`dcsr.cetrig` 调试进入，属 M 态固件/OpenSBI + 调试器领域，S 态内核无直接工作）。
  - **greenfield 度（Ssdbltrp）**：**真缺口，有在途 Linux 系列**。Clément Léger（Rivos）系列：`dt-bindings` + ISA 解析 + `handle Ssdbltrp mstatus SDT bit` + `double trap driver` + `kvm: SBI FWFT SBI_FWFT_DOUBLE_TRAP_ENABLE`；LWN [970359](https://lwn.net/Articles/970359/)。**FWFT 底座（`SBI_FWFT_DOUBLE_TRAP`）已合入树**，说明系列正分步落地。QEMU v8（2025-01）已支持。规范：Double Trap v1.0，**2024-08-23 批准**（Ved Shanbhogue）。

---

## 4. state-enable 束：Ssstateen（S 态视图）

- **候选**：`Ssstateen`（来源：`cpufeature.c:581` 有 `smstateen` 但 **无 `ssstateen`**）。
- **现状（只读核实）**：
  - `grep -w smstateen cpufeature.c` → `:581 __RISCV_ISA_EXT_DATA(smstateen, RISCV_ISA_EXT_SMSTATEEN)`（已识别，`hwcap.h:52` = 43）；`grep -w ssstateen` → **无**。
  - CSR 地址**已备**：`csr.h:324 CSR_SSTATEEN0 = 0x10c`；`csr.h:242-243` `SMSTATEEN0_SSTATEEN0`（mstateen0 bit 63，门控 sstateen0/hstateen0 访问）。
  - `smstateen` 现主要用于 **KVM** 门控 guest 对扩展状态的访问（`kvm/vcpu_config.c`、`vcpu_onereg.c`、`isa.c` 等），**非**主机任务上下文切换。
- **落点**：`cpufeature.c` + `hwcap.h` 增 `ssstateen` 识别；`dt-bindings` extensions.yaml。规范关系：**Smstateen = 全量**（mstateen*+sstateen*+hstateen*）；**Ssstateen = S 态子集**（仅 sstateen0-3 + hstateen0-3，无 M 态 CSR）。二者同为 v1.0 批准，已并入 Priv Arch ch4。RVA23 要求 Ssstateen（因其要求 H）。
- **判定**：**PATTERN（低）**。真缺口（识别集确无 `ssstateen`），但**单独价值低**——state-enable 本质是**其他扩展状态访问的门控位**，非独立功能；主机检测已由 `smstateen` 覆盖，`ssstateen` 主要意义在**profile 合规解析**（RVA23 显式列出）与 hstateen guest 门控（部分已由 smstateen 路径覆盖）。宜随其所门控的扩展一并补识别，不作为独立高价值贡献点。（不判 N-A：它有真实 OS 语义、已批准、非 M 态。）

---

## 5. 无 OS 语义 / 纯 M 态 / draft → N-A（本簇附带核实）

| 候选 | 理由 | 落点 |
|---|---|---|
| **Smdbltrp** | M 态双陷入 → RNMI / `dcsr.cetrig` 调试进入；S 态内核无直接工作 | 固件 / OpenSBI |
| **Smrnmi** | 可恢复 NMI，纯 M 态 | —（M 态） |
| **Smepmp** | M 态 PMP 增强，纯 M 态 | —（M 态） |
| **Smstateen** | 已识别（`cpufeature.c:581`）——基线，非缺口 | ALREADY |

---

## 6. greenfield 度汇总（① 候选必注：真缺口 but 在途？）

| 候选 | 批准状态/年份 | 在树？ | 在途 RFC / 主推者 | greenfield 结论 |
|---|---|---|---|---|
| **Ssqosid** | v1.0，随 Priv 1.13；CBQRI 2024 | 否（零 `srmcfg`） | **活跃**：Drew Fustini，RFC v2 **17 补丁**（LKML 2026-02）；LWN 1038951；LPC 2025 | 真缺口，**高度活跃**，宜跟随 |
| **Sdtrig** | Debug 规范 Trigger Module，已批准 | 否（零 `hw_breakpoint`） | **活跃**：Chauhan+Taube 8 补丁（2025-08）；Hsu/Wang CSR+KVM 系列 | 真缺口，**活跃**，宜补强 |
| **Ssdbltrp** | Double Trap v1.0，**2024-08-23** | 部分（FWFT 底座 `sbi.h:429` 已入，本体未接） | **在途**：Clément Léger 系列；LWN 970359；QEMU v8 | 真缺口，**分步落地中** |
| **Smdbltrp** | Double Trap v1.0，2024-08-23 | 否 | （随上系列，M 态部分） | N-A（M 态/固件） |
| **Ssstateen** | v1.0，Priv Arch ch4 | 否（`smstateen` 有，`ssstateen` 无） | 无独立系列（多随其他扩展捎带） | 真缺口但低价值/门控 |

---

## 7. 可追溯性（关键 `文件:行` 证据）

- `arch/riscv/kernel/cpufeature.c:581` —— 仅 `smstateen` 命中；`ssqosid/ssdbltrp/smdbltrp/sdtrig/ssstateen` 全无。
- `arch/riscv/include/asm/hwcap.h:52` —— `RISCV_ISA_EXT_SMSTATEEN 43`；`:118` `MAX 128`；无候选 define。
- `fs/resctrl/`（`rdtgroup.c`/`monitor.c`/`ctrlmondata.c`/`pseudo_lock.c`/`internal.h`/`Kconfig`）—— 通用层整树在。
- `arch/arm64/Kconfig:2053-2056` —— `ARM64_MPAM` `select ARCH_HAS_CPU_RESCTRL` + `ARM64_MPAM_DRIVER`；`fs/resctrl/Kconfig` `RESCTRL_FS depends on ARCH_HAS_CPU_RESCTRL`；`arch/riscv` 独缺 select。
- `arch/x86/include/asm/resctrl.h:100/167` —— `__resctrl_sched_in()` 写 `IA32_PQR_MSR`（srmcfg 对端模型）。
- `arch/riscv/include/asm/processor.h:106-126`（`envcfg` 字段 `:113`）+ `switch_to.h:84`（`__switch_to_envcfg`）—— srmcfg per-task 切换模式模板。
- `arch/riscv/include/asm/csr.h:214-231`（ENVCFG flags，**无 DTE**）、`:242-243`（`SMSTATEEN0_SSTATEEN0`）、`:324`（`CSR_SSTATEEN0 0x10c`）、`:378/420`（`CSR_HENVCFG/MENVCFG`）。
- `arch/riscv/include/asm/sbi.h:38`（`SBI_EXT_FWFT`）、`:429`（`SBI_FWFT_DOUBLE_TRAP 0x3`，已在树）。
- `arch/arm64/kernel/hw_breakpoint.c`（1021 行，Sdtrig 对端）；`arch/riscv/kernel/ptrace.c:375`（`riscv_user_regset[]` 无 HW_BREAK/HW_WATCH）。
- `arch/riscv/kvm/vcpu.c:727`（仅 swap `host_senvcfg`，无 DTE）。

## 参考（联网核实来源）

- Ssqosid / CBQRI：[docs.riscv.org CBQRI](https://docs.riscv.org/reference/debug-trace-ras/cbqri/_attachments/riscv-cbqri.pdf)、[LWN 1038951](https://lwn.net/Articles/1038951/)、[LPC 2025 QoS](https://lpc.events/event/19/contributions/2183/)
- Double Trap：[Ratified PDF 2024-08-23](https://docs.riscv.org/reference/isa/extensions/dbltrp/_attachments/riscv-double-trap.pdf)、[Ssdbltrp priv](https://docs.riscv.org/reference/isa/priv/ssdbltrp.html)、[LWN 970359](https://lwn.net/Articles/970359/)
- Sdtrig：[LWN 1030993](https://lwn.net/Articles/1030993/)、[LWN 963234](https://lwn.net/Articles/963234/)、[LWN 967153](https://lwn.net/Articles/967153/)
- Smstateen/Ssstateen：[docs.riscv.org priv/smstateen](https://docs.riscv.org/reference/isa/priv/smstateen.html)、[riscv-profiles#154](https://github.com/riscv/riscv-profiles/issues/154)
