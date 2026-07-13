# KVM x86/arm 补丁 → RISC-V 可移植性汇总

> 分析区间：**2025-01-01 ~ 2026-07-10**　|　数据源：[patchwork.kernel.org KVM 项目](https://patchwork.kernel.org/project/kvm/list/?state=*&archive=both)
> 辅助源码：Linux 7.2.0-rc3（`/Users/zq/Desktop/patch-work/linux-riscv`）
> 目标：从该区间全部 KVM 补丁中收集 x86/arm 架构补丁，逐一判定其移植到 RISC-V KVM 的可能性，列举潜在可移植候选，并标注「原补丁 ↔ 可移植点 ↔ RISC-V 落点」。

---

## TL;DR（速览）

- 区间内 KVM 补丁共 **21,687 个** → 按 series 去重为 **2,578 个逻辑系列**，其中 **x86/arm 系列 1,187 个**。
- 按可移植性分三层：**Tier A 通用（21）/ Tier B 模式可移植（206）/ Tier C 硬件专属（526）**，另有 misc 282、pull-request 105（非特性单元）、kvm-unit-tests 47。
- **最高价值移植方向**（riscv 明确缺失、上游已在 x86/arm 落地）：
  1. **guest_memfd / 内存属性**（riscv 未 select `KVM_GUEST_MEMFD`，arm64 已有）
  2. **G-stage 大页 eager split + 关闭 dirty-log 后合并**（riscv 仅 lazy）
  3. **stage-2 ptdump 调试**、**IRQ bypass/直注**、**async page fault**、**PMU event filter**、**HW 断点/单步调试**
  4. **selftests 补齐**（guest_memfd_test、dirty_log_page_splitting_test、AIA/PMU 功能测试）
- 详细候选排名见 [§4](#4-top-可移植候选排名)；每类明细见 [`analysis/`](analysis/)。

---

## 1. 方法论

### 1.1 数据采集
- 通过 patchwork REST API（`/api/1.2/patches/`，`project=kvm`、`state=*`、`archive=both`）分页抓取区间内**全部** 21,687 条补丁元数据。
- 脚本：[`scripts/fetch_patches.py`](scripts/fetch_patches.py)（断点续抓 + 指数退避重试 + 礼貌延时）。
- 产出：[`data/all_patches.jsonl`](data/all_patches.jsonl)（每条含 id/name/date/state/submitter/series/web_url/mbox/msgid）。

### 1.2 分类与去重
- 脚本：[`scripts/classify.py`](scripts/classify.py)。
- **架构分类**：基于标题 + series 名的正则（含词边界，避免 `its`/`arm` 误判），分 x86 / arm / x86+arm / riscv / other / common。
- **按 series 去重**：归一化系列名（去 `[PATCH vN]`、`m/n` 编号、`vN` 版本），保留最新版本；`21,687 → 4,510 series 版本 → 2,578 逻辑系列`。
- **特性分类**：按 20 类 / 3 层级关键词规则打标签（映射见 [`analysis/_taxonomy.md`](analysis/_taxonomy.md)），并单列 pull-request / kvm-unit-tests 等非特性单元。
- 产出：[`data/x86_arm_series.csv`](data/x86_arm_series.csv)（去重分类索引，覆盖全部 1,187 条 x86/arm 系列）、[`data/category_counts.md`](data/category_counts.md)、[`data/by_category/`](data/by_category/)（按类别分组供分析）。

### 1.3 可移植性分析
- 每个特性类别由一个子代理分析，输入 = 该类别系列清单 + [RISC-V 能力基线](analysis/_baseline_riscv.md) + 本地内核源码只读访问。
- 对每条系列判定四态之一（见 §3.2）；对强候选 `curl` 其 `mbox` 全文核对 diff，并用本地源码验证 riscv 落点。
- 各类别明细写入 [`analysis/<类别>.md`](analysis/)。

### 1.4 局限与诚实声明
- 架构/类别分类是关键词启发式，存在边界噪声；子代理会在分析时修正个别归类。
- 「可移植」是**上游代码层面的技术判断**，非移植工作量承诺；PATTERN 类需在 riscv 侧重写，工作量差异大。
- 深挖（mbox 全文核对）集中在各类最强候选；Tier-C 大类以批量归类为主（依据其硬件专属性质）。
- 分析基于单一内核树快照（7.2.0-rc3）；部分「缺口」可能有正在评审的补丁。

---

## 2. 数据概览

| 指标 | 数值 |
|---|---|
| 区间原始补丁 | **21,687** |
| 去重逻辑系列 | **2,578** |
| x86/arm 系列 | **1,187** |

### 2.1 全体系列架构分布
| 架构 | 系列数 |
|---|---|
| x86 | 979 |
| common（通用，无架构前缀） | 936 |
| other（s390/ppc/loongarch） | 242 |
| riscv | 213 |
| arm | 194 |
| x86+arm（跨架构） | 14 |

> 注：`common` 系列多属 `virt/kvm/*` 通用层，天然对 riscv 生效，不在本次「x86/arm 专项」计数内，但其中的通用机制同样惠及 riscv。

### 2.2 x86/arm 系列 · 层级与类别分布
| 层级 | 类别 | 系列数 | 分析文件 |
|---|---|---|---|
| A 通用 | guest_memfd | 10 | [tierA_generic.md](analysis/tierA_generic.md) |
| A 通用 | core | 4 | [tierA_generic.md](analysis/tierA_generic.md) |
| A 通用 | io-irq-infra | 3 | [tierA_generic.md](analysis/tierA_generic.md) |
| A 通用 | docs | 4 | [tierA_generic.md](analysis/tierA_generic.md) |
| B 模式 | reg-access | 45 | [reg_access.md](analysis/reg_access.md) |
| B 模式 | mmu-stage2 | 44 | [mmu_stage2.md](analysis/mmu_stage2.md) |
| B 模式 | pmu | 34 | [pmu.md](analysis/pmu.md) |
| B 模式 | selftests | 31 | [selftests.md](analysis/selftests.md) |
| B 模式 | mmio-insn | 19 | [mmio_debug.md](analysis/mmio_debug.md) |
| B 模式 | pv-hypercall | 16 | [timer_pv.md](analysis/timer_pv.md) |
| B 模式 | timer-clock | 13 | [timer_pv.md](analysis/timer_pv.md) |
| B 模式 | debug-introspect | 4 | [mmio_debug.md](analysis/mmio_debug.md) |
| C 硬件 | confidential (TDX/SEV/pKVM/CCA) | 229 | [confidential.md](analysis/confidential.md) |
| C 硬件 | nested | 126 | [nested_hwvirt.md](analysis/nested_hwvirt.md) |
| C 硬件 | irqchip-hw (APIC/VGIC/ITS) | 74 | [irqchip_hw.md](analysis/irqchip_hw.md) |
| C 硬件 | vendor-enlighten (Hyper-V/Xen) | 54 | [vendor_legacy.md](analysis/vendor_legacy.md) |
| C 硬件 | x86-legacy (SMM/MTRR/PIT) | 16 | [vendor_legacy.md](analysis/vendor_legacy.md) |
| C 硬件 | hw-virt-engine | 11 | [nested_hwvirt.md](analysis/nested_hwvirt.md) |
| C 硬件 | fpu-xstate | 9 | [vendor_legacy.md](analysis/vendor_legacy.md) |
| C 硬件 | arch-infra | 7 | [vendor_legacy.md](analysis/vendor_legacy.md) |
| — | misc（待细分诊） | 282 | [misc.md](analysis/misc.md) |
| — | pull-request（非特性单元，已排除） | 105 | — |
| T | kvm-unit-tests（独立测试套件） | 47 | [selftests.md](analysis/selftests.md) |

---

## 3. 可移植性框架

### 3.1 三层级（详见 [analysis/_taxonomy.md](analysis/_taxonomy.md)）
- **Tier A — GENERIC 通用层**：代码位于 `virt/kvm/*` 或架构无关，改动通常对所有架构（含 riscv）一次生效 → 基调 PORTABLE。
- **Tier B — PATTERN-PORTABLE 模式可移植**：架构专属实现但机制可复用，需在 riscv 侧重写 → 基调 PATTERN。
- **Tier C — HW-SPECIFIC 硬件专属**：依赖 x86/arm 特有硬件（VMX/SVM/GIC/ITS/nested/TDX/SEV/pKVM/Hyper-V/Xen/SMM），riscv 无对应 → 基调 N-A，仅当扩展通用底座时计入。

### 3.2 判定四态
| 判定 | 含义 |
|---|---|
| **ALREADY** | riscv 已实现等价能力 |
| **PORTABLE** | 通用层/架构无关，改动应能直接或几乎直接适用于 riscv |
| **PATTERN** | 机制可复用，需在 riscv 侧重写（给出落点文件） |
| **N-A** | 依赖 x86/arm 专有硬件，不可移植 |

### 3.3 RISC-V 能力基线
riscv KVM 现状与缺口详见 [`analysis/_baseline_riscv.md`](analysis/_baseline_riscv.md)。要点：已成熟实现 G-stage MMU、AIA 中断、Sstc 定时器、SBI-PMU、FP/Vector、广泛 SBI 扩展、ONE_REG、dirty ring、steal-time、binary stats；明确缺失 guest_memfd、大页 eager split、ptdump、IRQ bypass、async_pf、PMU event filter、HW 调试等。

---

## 4. Top 可移植候选排名

> 全部 1,082 条已分析 x86/arm 系列（排除 105 pull-request）中，判定为可移植的共 **108 条**（PORTABLE 43 + PATTERN 65），另 9 条 riscv 已有。
> 下表按**移植价值 + 上游成熟度 + 落点清晰度**排序，分四档。每条给出「原补丁 → 可移植点 → riscv 落点 → 来源」。完整逐条判定见各 [`analysis/*.md`](analysis/)（含 web_url）。

### P1 — 旗舰候选（riscv 明确缺失的大特性，上游已成熟，价值最高）

| # | 可移植点 | 判定 | riscv 落点 | 来源 |
|---|---|---|---|---|
| 1 | **guest_memfd / 内存属性启用**：通用引擎（`virt/kvm/guest_memfd.c`、`KVM_CAP_GUEST_MEMFD`、mem-attr、mmap、in-place 转换）已在树内，riscv 仅未 select。多个系列汇聚（host mmap、mmap()、in-place 转换、populate 重构） | PORTABLE | `Kconfig` 加 `select KVM_GUEST_MEMFD`；`mmu.c` 缺页路径加 `kvm_mem_is_private()→kvm_gmem_get_pfn()` 分支（仿 arm64 `mmu.c:1644`） | [tierA_generic](analysis/tierA_generic.md)、[confidential](analysis/confidential.md)（L73/L75/L60/L130/L54） |
| 2 | **async page fault (async_pf)**：核心 `virt/kvm/async_pf.c` 通用，riscv 全缺；异步缺页避免 vCPU 阻塞 | PATTERN | 新增 `vcpu_sbi_apf.c`（新 SBI 扩展）+ `mmu.c` 缺页钩子 + `vcpu.c` + `select KVM_ASYNC_PF` | [timer_pv](analysis/timer_pv.md) |
| 3 | **IRQ bypass / posted IRQ 直接注入**：riscv 未 select `HAVE_KVM_IRQ_BYPASS`，但 IMSIC 已有 VS-file 硬件直注后端（HWACCEL），仅差架构钩子 | PATTERN | `aia.c`/`aia_imsic.c` 新增 `kvm_arch_irq_bypass_*` 生产者/消费者钩子 + IRTE 映射 | [irqchip_hw](analysis/irqchip_hw.md)（x86 device posted IRQ / arm64 vGICv4 forwarding） |
| 4 | **KVM_PRE_FAULT_MEMORY 预缺页**：通用 ioctl/CAP 机制（`KVM_GENERIC_PRE_FAULT_MEMORY`）已在 `kvm_main.c`，riscv 未 select | PORTABLE | `Kconfig` select + `mmu.c` 实现 `kvm_arch_vcpu_pre_fault_memory()`（复用 `kvm_riscv_gstage_map()`）+ 广告 CAP | [nested_hwvirt](analysis/nested_hwvirt.md) L113 [`20260612…`](https://patchwork.kernel.org/project/kvm/patch/20260612162354.73378-3-jackabt.amazon@gmail.com/)、[misc](analysis/misc.md) #240 |

### P2 — 高价值候选（明确缺口，落点清晰，需 riscv 侧实现）

| # | 可移植点 | 判定 | riscv 落点 | 来源 |
|---|---|---|---|---|
| 5 | **PMU event filter**：riscv 无（对照 x86 `pmu_event_filter`） | PATTERN | `vcpu_pmu.c` `kvm_riscv_vcpu_pmu_ctr_cfg_match()` + 新 CAP/ioctl | [pmu](analysis/pmu.md) |
| 6 | **Mediated / 直通 vPMU**：架构无关 perf-core（`exclude_guest`/mediated API）可复用 | PATTERN | `vcpu_pmu.c` + `drivers/perf/riscv_pmu*`（RISC-V Counter Delegation Smcdeleg/Ssccfg） | [pmu](analysis/pmu.md) |
| 7 | **大页处理**：①关闭 dirty-log 后 collapse/合并大页（riscv `gstage.c:264` 明确未做）②dirty-log 开启时 eager 预拆 | PATTERN | `gstage.c:306`（复用 split）+ `mmu.c:19`（wp region 钩子） | [mmu_stage2](analysis/mmu_stage2.md) |
| 8 | **HW guest debug**：断点/单步/watchpoint；riscv `kvm_guest_debug_arch`/`kvm_debug_exit_arch` 为空结构，仅软件断点 | PATTERN | 需 riscv Sdtrig 支持 + `vcpu.c`/`vcpu_exit.c` + 填充 uapi 调试结构 | [mmio_debug](analysis/mmio_debug.md)（多条 x86 #DB/DR 共同印证） |
| 9 | **stage-2 ptdump 调试**：arm64 有 `ptdump.c`，riscv 无 | PATTERN | 新增 debugfs stage-2 页表 dumper（walk `gstage`） | [mmio_debug](analysis/mmio_debug.md)（缺口登记，本批无直接输入系列） |
| 10 | **KVM Userfault（post-copy 迁移）**：底座 `KVM_MEM_USERFAULT` 通用；无需 userfaultfd 的 post-copy | PORTABLE+PATTERN | `select KVM_GENERIC_PAGE_FAULT` + `mmu.c:535` 缺页钩子 + `kvm_page_fault` 结构 | [mmu_stage2](analysis/mmu_stage2.md) #15 |

### P3 — 通用层直接受益（PORTABLE，低成本、高置信，改上游通用码即惠及 riscv）

| # | 可移植点 | 判定 | riscv 落点 | 来源 |
|---|---|---|---|---|
| 11 | **`kvm_arch_flush_shadow_all()` 竞态修复**：上游补丁已直接改 `arch/riscv/kvm/mmu.c`+`vm.c` | PORTABLE | `mmu.c`/`vm.c`（协同上游） | [mmu_stage2](analysis/mmu_stage2.md) #36（最高置信） |
| 12 | **irqfd 注册全局唯一**：通用 `virt/kvm/eventfd.c` 注册竞态修正 | PORTABLE | 无需新增，riscv AIA 经 irqfd 自动受益 | [vendor_legacy](analysis/vendor_legacy.md) [`20250522…`](https://patchwork.kernel.org/project/kvm/patch/20250522235223.3178519-8-seanjc@google.com/) |
| 13 | **directed yield 优化 `kvm_vcpu_on_spin()`**：3 补丁全在通用 `kvm_main.c` | PORTABLE | `vcpu_insn.c:86`（WFI/pause 调用点）自动受益 | [misc](analysis/misc.md) #187（最强隐藏项） |
| 14 | **KVM↔VFIO 模块引用解耦** | PORTABLE | `virt/kvm/vfio.c`+`kvm_main.c` 通用自动生效 | [reg_access](analysis/reg_access.md) #38 |
| 15 | **无锁 SPTE aging（MGLRU 性能）** | PORTABLE+PATTERN | opt-in `KVM_MMU_NOTIFIER_AGING_LOCKLESS` + `mmu.c:264/284` `kvm_age_gfn` 无锁化 | [mmu_stage2](analysis/mmu_stage2.md) #3 |
| 16 | **MMIO/kvm_io_bus 注册加速（SRCU）** | PORTABLE | 通用 `kvm_io_bus` 自动生效 | [irqchip_hw](analysis/irqchip_hw.md) |
| 17 | **`kvm_online_cpu()` 关中断修复** | PORTABLE | 通用 `kvm_main.c` CPU 热插拔（riscv 用 `KVM_GENERIC_HARDWARE_ENABLING`） | [misc](analysis/misc.md) #115 |

### P4 — 其他模式候选（PATTERN，中低价值或需较多重写）

| # | 可移植点 | 判定 | riscv 落点 | 来源 |
|---|---|---|---|---|
| 18 | steal-time 计入 host 挂起时长 + 计费修正 | PATTERN | `vcpu_sbi_sta.c` | [timer_pv](analysis/timer_pv.md) |
| 19 | stage-2 拆销路径让出 CPU（reschedule） | PATTERN | `gstage.c:439`（复用 `cond_resched_rwlock_write`） | [mmu_stage2](analysis/mmu_stage2.md) #17 |
| 20 | WFI/WFE disable-exits 能力 | PATTERN | `vcpu_insn.c` + 新 `KVM_CAP_RISCV_DISABLE_EXITS` | [selftests](analysis/selftests.md) B24 |
| 21 | VMM 注入 external abort（带 syndrome，NISV 优雅退出） | PATTERN | `vcpu_exit.c` + 新异常注入 CAP/UAPI | [mmio_debug](analysis/mmio_debug.md) |
| 22 | `array_index_nospec` Spectre-v1 索引硬化 | PATTERN | `vcpu_sbi_*.c`/`vcpu_onereg.c` | [misc](analysis/misc.md) #95/198/235 |
| 23 | get-reg-list blessed-list 迁移纪律 | PATTERN | `tools/.../riscv/get-reg-list.c` | [reg_access](analysis/reg_access.md) #25/26 |
| 24 | vCPU wait/yield tracepoint | PATTERN | `trace.h` 加 `kvm_sched_event` + WFI/SBI-yield 埋点 | [mmio_debug](analysis/mmio_debug.md) |
| 25 | `user_mem_abort()` 状态对象化重构 / 原子缺页 bug 自查 | PATTERN | `mmu.c:537` `kvm_riscv_gstage_map()` | [nested_hwvirt](analysis/nested_hwvirt.md) #82/91/79 |
| 26 | fast MMIO bus writes（`KVM_FAST_MMIO_BUS`） | PATTERN | `vcpu_insn.c` `mmio_store` | [mmio_debug](analysis/mmio_debug.md) |
| 27 | selftests 补齐：irqfd_test 非 x86 修复 / kvm_run 完成标志 / 只读 memslot 测试 / 类型统一 | PORTABLE+PATTERN | `tools/.../kvm/`（公共 + `riscv/`、`lib/riscv/`） | [selftests](analysis/selftests.md) B15/B1/B21 |

> 说明：P1–P4 覆盖各类别最强候选（约 30 项，含若干由多系列汇聚的方向）；其余 PORTABLE/PATTERN 长尾（纯清理/风格统一/低价值 bug 自查等）逐条列于各 `analysis/*.md` 全量判定表中。

---

## 5. 分类别分析汇总

各类别四态计数（覆盖全部 1,082 条已分析 x86/arm 系列；每类全量逐条判定见对应 `analysis/*.md`）：

| 类别 | 系列数 | ALREADY | PORTABLE | PATTERN | N-A | 明细 |
|---|---:|---:|---:|---:|---:|---|
| Tier A 通用（guest_memfd 等） | 21 | 1 | 11 | 2 | 7 | [tierA_generic](analysis/tierA_generic.md) |
| mmu-stage2 | 44 | 0 | 4 | 14 | 26 | [mmu_stage2](analysis/mmu_stage2.md) |
| reg-access | 45 | 1 | 1 | 11 | 32 | [reg_access](analysis/reg_access.md) |
| pmu | 34 | 0 | 0 | 8 | 26 | [pmu](analysis/pmu.md) |
| timer + pv-hypercall | 29 | 3 | 1 | 4 | 21 | [timer_pv](analysis/timer_pv.md) |
| selftests + kvm-unit-tests | 78 | 0 | 4 | 2 | 72 | [selftests](analysis/selftests.md) |
| mmio-insn + debug | 23 | 0 | 0 | 6 | 17 | [mmio_debug](analysis/mmio_debug.md) |
| irqchip-hw | 74 | 0 | 3 | 5 | 66 | [irqchip_hw](analysis/irqchip_hw.md) |
| nested + hw-virt-engine | 137 | 0 | 0 | 6 | 131 | [nested_hwvirt](analysis/nested_hwvirt.md) |
| vendor + x86-legacy + fpu + infra | 86 | 1 | 4 | 0 | 81 | [vendor_legacy](analysis/vendor_legacy.md) |
| misc（细分诊） | 282 | 2 | 4 | 6 | 270 | [misc](analysis/misc.md) |
| confidential（TDX/SEV/pKVM/CCA） | 229 | 1 | 11 | 1 | 216 | [confidential](analysis/confidential.md) |
| **合计** | **1,082** | **9** | **43** | **65** | **965** | — |

**要点解读**：
- **可移植集中在两处**：①**通用底座**（guest_memfd / 内存属性 / pre-fault / irqfd / memslot / directed-yield，多来自 Tier A、confidential 的通用例外、misc 隐藏项）；②**stage-2 MMU 与 PV 机制**（大页管理、userfault、async_pf、steal-time）。
- **confidential 的价值不在机密计算本身**：229 条中 216 条 N-A，但 11 条 PORTABLE 全部是它们**顺带扩展的通用 guest_memfd 底座**——这正是 riscv 启用 guest_memfd 的上游依据。
- **reg-access / pmu 可移植密度低但非零**：riscv ONE_REG 与 SBI-PMU 已成熟，缺的是 event filter、mediated vPMU、get-reg-list 迁移纪律等**增量机制**。
- **N-A 占 89%**：绝大多数 x86/arm 补丁锚定专有硬件（VMX/SVM/GIC/ITS/nested/TDX/SEV/pKVM/Hyper-V/Xen/SMM/XSAVE），riscv 无对应，符合预期。

---

## 6. 结论与建议

### 6.1 总体结论
- 在 2025-01 ~ 2026-07 的 21,687 个 KVM 补丁中，x86/arm 专项系列约 1,082 个（去重后），其中 **108 个（约 10%）对 RISC-V KVM 有移植价值**：43 个属通用层可直接受益，65 个机制可复用需在 riscv 侧重写。
- RISC-V KVM 基础设施已相当完整（G-stage MMU、AIA、Sstc、SBI-PMU、ONE_REG、dirty ring、steal-time 均已就位），因此移植机会集中在**通用底座的补齐**与**性能/可观测性/迁移能力**的增量特性，而非核心功能。

### 6.2 建议的移植优先级（roadmap）
1. **第一梯队（通用底座，投入产出比最高）**：
   - **guest_memfd 启用**（候选 #1）——最高价值，上游引擎现成，riscv 仅需 `select KVM_GUEST_MEMFD` + 一个缺页分支；可解锁后续机密计算路线。
   - **KVM_PRE_FAULT_MEMORY**（#4）、**irqfd 全局唯一**（#12）、**directed-yield 优化**（#13）、**flush_shadow_all 竞态修复**（#11）——均为低成本 PORTABLE，改通用码即生效。
2. **第二梯队（明确特性缺口）**：**async_pf**（#2）、**IRQ bypass/IMSIC 直注**（#3）、**PMU event filter**（#5）、**大页 collapse/eager split**（#7）、**KVM Userfault post-copy**（#10）。
3. **第三梯队（可观测/调试/迁移健壮性）**：**stage-2 ptdump**（#9）、**HW guest debug**（#8）、**无锁 SPTE aging**（#15）、**steal-time 增强**（#18）、**get-reg-list 迁移纪律**（#23）、**selftests 补齐**（#27）。

### 6.3 明确不适用（无需跟进）
嵌套虚拟化（riscv 尚未实现）、机密计算本体（无 CoVE）、VMX/SVM/GIC/ITS/APIC 硬件模拟、Hyper-V/Xen 增强、SMM/MTRR/PIT 等 x86 遗留、x86 全指令软件模拟器——共约 965 条，riscv 无对应硬件，不在移植范围。

### 6.4 使用本报告
- 按候选编号在 §4 定位「原补丁 → 可移植点 → riscv 落点」；点开对应 `analysis/*.md` 查全量逐条判定与 `web_url`。
- `data/x86_arm_series.csv` 提供全部 1,187 条去重系列的可检索索引（架构/类别/层级/状态/日期/URL）。
- 复现：`python3 scripts/fetch_patches.py && python3 scripts/classify.py`。

---

## 附录：文件索引

| 路径 | 说明 |
|---|---|
| [`scripts/fetch_patches.py`](scripts/fetch_patches.py) | patchwork 元数据抓取（可复现） |
| [`scripts/classify.py`](scripts/classify.py) | 分类 / 去重 / 打标签 |
| [`data/all_patches.jsonl`](data/all_patches.jsonl) | 全量 21,687 条补丁元数据 |
| [`data/x86_arm_series.csv`](data/x86_arm_series.csv) | 去重后 1,187 条 x86/arm 系列分类索引 |
| [`data/category_counts.md`](data/category_counts.md) | 分类统计 |
| [`data/by_category/`](data/by_category/) | 按类别分组的系列清单 |
| [`analysis/_baseline_riscv.md`](analysis/_baseline_riscv.md) | RISC-V KVM 能力基线 |
| [`analysis/_taxonomy.md`](analysis/_taxonomy.md) | KVM 特性分类法与层级 |
| [`analysis/*.md`](analysis/) | 各类别可移植性明细 |
