# ①ISA 批准差集 —— perf / 计数器簇

> 内核树：`/Users/zq/Desktop/patch-work/linux-riscv`（Linux **v7.2.0-rc3**，只读核实）。
> 本分片候选：`Ssctr/Smctr`（分支记录）、`Smcdeleg/Ssccfg`（计数器委派）、`Smcsrind/Sscsrind`（间接 CSR）、`Smcntrpmf`（计数器特权过滤）。
> 判定语义：「该缺口是否值得且可行地在 riscv 补上」。① 候选必注 **greenfield 度**（是否已有在途 RFC）。

## 四态计数表（本分片）

| 判定 | 数量 | 候选 |
|---|---|---|
| ALREADY | 0 | —（四者在 `cpufeature.c`/`hwcap.h` 全零匹配，均非假阳） |
| PORTABLE | 0 | —（无「通用侧已在树、arch 仅 select」型；均需 arch 实现） |
| **PATTERN** | **4** | Ssctr/Smctr、Smcdeleg/Ssccfg、Smcsrind/Sscsrind、Smcntrpmf |
| N-A | 0 | —（四者均有 S 态 perf 集成语义，非纯 M 态/draft） |

**一句话结论**：四者都是**真缺口**（v7.2.0-rc3 树内零实现），但**全部已有活跃在途上游系列**（多来自 Rivos），**greenfield 度普遍偏低**。贡献动作应是**评审 / 测试 / 接力在途系列**，而非从零起步。最强、最独立的单点是 **Ssctr/Smctr 分支记录**（≈ x86 LBR / arm64 BRBE，riscv perf 现完全无 branch-stack）。

---

## 假阳排除（对照 `_baseline_riscv.md §一` 92 项已识别集）

`grep -w` 于 `arch/riscv/kernel/cpufeature.c` + `arch/riscv/include/asm/hwcap.h`：

| 扩展 | cpufeature/hwcap | 全 arch/riscv 树 | 结论 |
|---|---|---|---|
| ssctr / smctr | 零匹配 | 零匹配 | 真缺口 |
| smcdeleg / ssccfg | 零匹配 | 零匹配 | 真缺口 |
| smcsrind / sscsrind | 零匹配 | 零匹配 | 真缺口（注：`siselect/sireg` **机制**已存在但仅 AIA 用，见下） |
| smcntrpmf | 零匹配 | 零匹配 | 真缺口 |

已识别的相邻扩展（勿混淆）：`smstateen`（`cpufeature.c:581`，`hwcap.h:52` = 43）、`sscofpmf`（溢出采样，`riscv_pmu_sbi.c:1197` 在用）。**注意 `ssstateen`（S 态 state-enable）本身未单独识别**——树内仅 `smstateen`，`ssstateen` 只出现在 SpaceMiT `k3.dtsi` 设备树，`hwcap.h`/`cpufeature.c` 无对应 `RISCV_ISA_EXT_SSSTATEEN`。

---

## 依赖链（本簇的核心结构）

```
                 [state-enable 门]
  smstateen(已识别) --bit60--> siselect/sireg 访问许可
                     --bit54--> CTR CSR 访问许可(S态)

  Sscsrind (间接CSR, 基础机制门, 批2024-02-22)
     │  (提供 sireg2..sireg6 窗口，绕开 CSR 地址空间上限)
     ├──────────────> Smcdeleg/Ssccfg (计数器委派, 批2024)
     │                     │   menvcfg.CDE=1 使能；新增 scountinhibit
     │                     └──> Smcntrpmf 的 S 态直读 (mcyclecfg/minstretcfg 经委派可见)
     │
     └──────────────> Ssctr/Smctr (分支记录, 批2024-11 frozen v1.0)
                           另需: smstateen bit54 门 + Sscofpmf(已识别)
                           (ctrsource/ctrtarget/ctrdata 经 sireg/sireg1/sireg2 访问,
                            xiselect 范围 0x200-0x2ff, 最深 256 条)

  Smcntrpmf (Zicntr 特权过滤, 批 v1.0) —— 独立于上链，但 S 态直读需 Smcdeleg
```

要点：**`Sscsrind` 是本簇的公共依赖门**——委派链（Ssccfg）与分支记录链（Ssctr）都经它访问超出 CSR 地址空间的寄存器窗口；而 `smstateen` 的两个 bit（60→CSR 间接、54→CTR）是访问许可门。**修正给定任务书的「Ssctr ← Ssstateen」**：更精确是 `Ssctr ← Sscsrind + smstateen[54] + Sscofpmf`（state-enable 走 bit 54，非泛指 Ssstateen）。

---

## 候选 1：Ssctr / Smctr（控制转移记录 / 分支记录）—— **最强单点**

- **候选**：`Ssctr`（S 态）/`Smctr`（M 态）控制转移记录。来源：`cpufeature.c`/`hwcap.h` 零匹配；分支记录 CSR（`sctrctl`/`sctrstatus`/`sctrdepth`/`ctrsource`/`ctrtarget`/`ctrdata`/`SCTRCLR`）全 arch/riscv 树零匹配（已只读核实）。
- **现状**：riscv perf **完全无 branch-stack 支持**——`drivers/perf/riscv_pmu.c:312-313` 硬性拒绝：
  ```
  /* driver does not support branch stack sampling */
  if (has_branch_stack(event)) return -EOPNOTSUPP;
  ```
  即用户态 `perf record -b` / `PERF_SAMPLE_BRANCH_STACK` 在 riscv 上一律 `-EOPNOTSUPP`。AutoFDO / 热路径分析无硬件支撑。
- **落点**：**新增** `drivers/perf/riscv_ctr.c`（CTR 采集驱动）+ CTR CSR 定义入 `arch/riscv/include/asm/csr.h`（`sctrctl` 等）+ cpufeature 识别（`cpufeature.c` 的 `riscv_isa_ext[]` 近 `:581` + `hwcap.h` 新 `RISCV_ISA_EXT_S{M,S}CTR`）+ 上下文切换保存/恢复 CTR 状态 + `riscv_pmu.c:312` 解除 branch-stack 拒绝并接 `perf_branch_stack`。**对端**：arm64 `drivers/perf/arm_brbe.c`(+`arm_brbe.h`，喂 `arm_pmuv3.c`)、x86 `arch/x86/events/intel/lbr.c`。**使能门**：`Sscsrind` + `smstateen[54]` + `Sscofpmf`（均见依赖链）。
- **判定**：**PATTERN**。真缺口、对端成熟、落点清晰，是本簇里语义最独立、用户可见价值最高者（perf branch-stack 从无到有）。**greenfield 度：低**——已有 Rajnesh Kanwal（Rivos）`[v3] riscv: pmu: Add support for Control Transfer Records Ext.`（2025-05-23，patchwork.ozlabs.org，7 patches，含 perf 工具 `remove_loops()` 扩到 256 条），QEMU + OpenSBI 已合并上游，**内核驱动尚未合并**。LWN 综述见 `Articles/976017`。

---

## 候选 2：Smcdeleg / Ssccfg（计数器委派）—— **性能价值最高**

- **候选**：`Smcdeleg`（M 态委派）/`Ssccfg`（S 态计数器配置）。来源：`cpufeature.c`/`hwcap.h` 零匹配；`scountinhibit` CSR、`menvcfg.CDE` 位全树零匹配（已核实）。
- **现状**：riscv PMU **完全走 SBI PMU**——每次计数器 config-match / start / stop 均 `sbi_ecall(SBI_EXT_PMU,...)` 陷入 M 态：
  - `riscv_pmu_sbi.c:566` `SBI_EXT_PMU_COUNTER_CFG_MATCH`（选计数器）
  - `:806` `SBI_EXT_PMU_COUNTER_START`、`:836` `SBI_EXT_PMU_COUNTER_STOP`
  - 仅**读**硬件计数器是直读 CSR（`:772` `riscv_pmu_ctr_read_csr(info.csr)`），配置全需陷入。
  高频 start/stop（采样、上下文切换）陷入开销显著。
- **落点**：`drivers/perf/riscv_pmu_sbi.c` **重构**为「SBI 路 + ISA 委派路」双后端（Ssccfg 使能时 S 态直写 `mhpmeventN`/`mhpmcounterN` 经 `sireg`，用 `scountinhibit` 直接起停，免 SBI 陷入）+ cpufeature 识别 + `menvcfg.CDE`/`scountinhibit` CSR 定义。**对端**：arm64 `drivers/perf/arm_pmuv3.c`（直接经 sysreg 读写 PMU，无固件陷入）即此模型的成熟形态。**依赖**：`Sscsrind`（经其访问委派计数器窗口）+ `smstateen[60]`。
- **判定**：**PATTERN**。真缺口、性能收益明确（去 SBI 陷入）。**greenfield 度：低**——Atish Patra（Rivos）`Add Counter delegation ISA extension support`：`[PATCH RFC 00/20]`（2024-02）→ v4/v5（2025-01/02），17 patches + Charlie Jenkins 1 patch（`perf: Skip PMU SBI extension`），把 SBI PMU 驱动改名为通用驱动同时支持两种机制；QEMU+OpenSBI 已合并，**内核系列尚未合并**。LWN 综述见 `Articles/1005174`。

---

## 候选 3：Smcsrind / Sscsrind（间接 CSR 访问）—— **公共依赖门**

- **候选**：`Smcsrind`（M）/`Sscsrind`（S）间接 CSR 访问。来源：`cpufeature.c`/`hwcap.h` 零匹配。
- **现状**：**间接 CSR 机制的寄存器已存在，但仅供 AIA 用，未作为独立 ISA 扩展识别**：
  - `arch/riscv/include/asm/csr.h:348-349` 定义 `CSR_SISELECT(0x150)`/`CSR_SIREG(0x151)`；`:437-438` `MISELECT/MIREG`；`:499-525` 有 `CSR_ISELECT`/`CSR_IREG` 按 M/S 态别名。
  - 实际消费者仅两处：`drivers/irqchip/irq-riscv-imsic-state.c:31-56`（AIA IMSIC irqchip）与 `arch/riscv/include/asm/kvm_aia.h:148`（KVM-AIA 仿真）。即当前只覆盖 Smaia/Ssaia 原生的 `sireg`，**未提供 `sireg2..sireg6` 扩展窗口**，也无 `Smcsrind/Sscsrind` 的 cpufeature 识别与 state-enable(bit60) 门管理。
  - **修正基线**：基线称「`sireg` 现仅 KVM-AIA 用」略欠——**AIA IMSIC irqchip（非虚拟化路径）亦在用**。
- **落点**：cpufeature 识别（`cpufeature.c` `riscv_isa_ext[]` + `hwcap.h`）+ 新增间接 CSR 访问 helper（在途系列命名 `Sxcsrind` + `asm/csr_ind.h` 类）+ `smstateen[60]` 门。**对端**：无直接「用户可见子系统」对端——它是**机制层**，价值在于解锁候选 2/1。
- **判定**：**PATTERN**（机制层，**独立价值低、依赖价值高**）。**greenfield 度：低**——随候选 2 的 Atish 委派系列一并在途（`dt-bindings: riscv: add Sxcsrind ISA extension description` 等），ratified 2024-02-22 v1.0.0。

---

## 候选 4：Smcntrpmf（Cycle/Instret 特权模式过滤）—— **价值最低**

- **候选**：`Smcntrpmf`（扩展 `Zicntr` 的特权模式过滤；即任务书所指「smcntr?」）。来源：`cpufeature.c`/`hwcap.h` 零匹配；`mcyclecfg`(0x321)/`minstretcfg`(0x322) CSR 全树零匹配。
- **现状**：**特权过滤已由 SBI 抽象覆盖**——`riscv_pmu_sbi.c:516-530` `pmu_sbi_get_filter_flags()` 把 `event->attr.exclude_kernel/exclude_user` 翻成 SBI 配置标志 `SBI_PMU_CFG_FLAG_SET_{S,U,VS,VU}INH`，由 SBI 固件（其底层可能正是用 Smcntrpmf/Sscofpmf 实现）落地。即**用户可见的过滤语义现已可用**，Smcntrpmf 的内核直接价值仅在「委派后 S 态直配」路径出现。
- **落点**：cpufeature 识别 + `mcyclecfg/minstretcfg` CSR 定义；仅在 Ssccfg 直读路径下由 `riscv_pmu_sbi.c`（重构后）直接写过滤位。**对端**：arm64/x86 PMU 驱动的 `exclude_kernel/exclude_user` 硬件过滤位。**依赖**：S 态可见需 `Smcdeleg/Ssccfg`。
- **判定**：**PATTERN（低）**。真缺口但**收益边际**——SBI 路已覆盖过滤语义，仅委派路径受益。**greenfield 度：低**——parsing/dt-bindings 随 Atish 委派系列在途；ratified v1.0，QEMU 已合并。

---

## 次要项 / 相邻事实（小表）

| 项 | 现状（文件:行） | 说明 |
|---|---|---|
| branch-stack 核心设施 | 通用侧 `include/uapi/linux/perf_event.h` 已在 | `PERF_SAMPLE_BRANCH_STACK` 通用，缺的只是 riscv arch 采集端（候选1） |
| 硬件计数器直读 | `riscv_pmu_sbi.c:772` | 读已直读 CSR；委派（候选2）解决的是**配置/起停**陷入，非读 |
| sscofpmf 溢出采样 | `riscv_pmu_sbi.c:1197` | 已识别在用；是候选1（CTR）freeze/采样触发的依赖 |
| ssstateen（S 态 stateen） | 仅 `k3.dtsi` DTS，无 `RISCV_ISA_EXT_SSSTATEEN` | 未单独识别；候选1/2/3 的 state-enable 门当前仅 KVM 侧 `vcpu.c:729/740` swap `sstateen0` |
| Kconfig | `drivers/perf/Kconfig:78`(RISCV_PMU)/`:98`(RISCV_PMU_SBI) | 委派系列拟把 `RISCV_PMU_SBI` 通用化 |

---

## 关键发现 / 修正汇总

1. **四态**：ALREADY 0 / PORTABLE 0 / **PATTERN 4** / N-A 0。四者皆真缺口（树内零实现），无假阳。
2. **greenfield 度普遍低（本簇最重要发现）**：四者**全部有活跃在途上游系列**——CTR 走 Rajnesh Kanwal v3（2025-05）；委派/间接CSR/Smcntrpmf 走 Atish Patra 委派大系列（RFC 00/20 → v4/v5，2025-初）。QEMU/OpenSBI 侧多已合并，**内核侧均未合并**。贡献姿势 = **接力/评审/测试在途系列**，非从零。
3. **最强单点**：**Ssctr/Smctr 分支记录**（落点 `drivers/perf/riscv_ctr.c` 新增 + 解除 `riscv_pmu.c:312` 的 branch-stack 拒绝），对端 x86 LBR / arm64 BRBE 成熟，用户可见价值（`perf record -b`/AutoFDO）最高。
4. **依赖门修正**：`Sscsrind` 是本簇公共依赖门；`Ssctr` 的 state-enable 门精确为 `smstateen[54]`（非泛指 Ssstateen），`Sscsrind` 门为 `smstateen[60]`。
5. **基线微修**：间接 CSR（`sireg/siselect`）除 KVM-AIA 外，**AIA IMSIC irqchip**（`irq-riscv-imsic-state.c`）亦在用。
6. **Smcntrpmf 价值下修**：SBI 路（`riscv_pmu_sbi.c:516-530`）已覆盖 exclude_kernel/user 过滤语义，其内核增益仅在委派直配路径。
