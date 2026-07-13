# 计划：KVM x86/arm 补丁 → RISC-V 可移植性汇总

## Context（背景与目标）

用户要求：基于 patchwork.kernel.org 的 KVM 项目补丁列表，探索 **2025-01-01 ~ 2026-07-10** 区间内的全部 KVM 补丁，收集所有 **x86/arm 架构**补丁，逐一分析其移植到 **RISC-V** 架构的可能性，最终列举潜在可移植的补丁。产出一篇汇总文档，放在 `kvm-riscv/` 路径下，标注「原补丁 ↔ 可移植点 ↔ RISC-V 落点」的对应关系。

**辅助资源**：本地内核源码 `/Users/zq/Desktop/patch-work/linux-riscv`（可用于对比分析）。
**范围约束**：只在当前路径（`.../claude-4-8/`）下产出；不探索其他无关路径。

### 关键现实约束（侦察已确认）
- 全区间 KVM 补丁总量 = **21,687 个**（patchwork API `state=*&archive=both`，217 页 × 100）。
- 架构分布抽样（300 条样本）：common ~40%、**x86 ~30%**、**arm ~16%**、other-arch ~10%、riscv ~4%。
- 推算 x86/arm 合计约 **1 万个补丁**；按 series 去重后约 **~2,000 个独立系列**。
- 逐条写散文分析 2 千+ 系列不现实 → 采用**「全量自动分类索引 + 候选项深度分析」**分层策略，兼顾「针对每个分析」与可行性。

## 数据源与接口

- Patchwork REST API（已验证可用，无需鉴权）：
  `https://patchwork.kernel.org/api/1.2/patches/?project=kvm&since=2025-01-01T00:00:00&before=2026-07-10T00:00:00&per_page=100&page=N`
- 每条记录字段：`id, name(标题), date, submitter, series[id/name/version], state, web_url, msgid, mbox`。
- 深挖候选补丁时用 `mbox` URL 获取补丁全文（含 diff）。

## 分析框架（来自源码盘点 Agent B，已落地）

按 KVM 特性分为 3 个可移植性层级（20 类）：

- **Tier A — GENERIC（通用层，`virt/kvm/*`）**：几乎必然适用于 riscv。含核心 VM/vCPU 生命周期与 ioctl/CAP、内存槽与 mmu_notifier、dirty ring、irqfd/ioeventfd/coalesced、guest_memfd/内存属性、binary stats、pfncache、pre-fault memory。
- **Tier B — PATTERN-PORTABLE（模式可移植）**：机制可复用，需在 riscv 侧重写实现。含 stage-2/G-stage 页表与 dirty-log 性能（eager split）、ONE_REG/特性枚举、PMU、定时器/pv-clock、steal-time/pv-time/hypercall、MMIO 退出路径、ptdump/debug、selftest 框架与通用测试。riscv 落点：`gstage.c / vcpu_onereg.c / vcpu_pmu.c / vcpu_timer.c / vcpu_sbi_*.c / selftests`。
- **Tier C — HW-SPECIFIC（硬件专属，低/无可移植）**：in-kernel 中断控制器内部（GICv3/ITS、APIC/AVIC）、VMX/SVM 世界切换、嵌套虚拟化、机密计算（TDX/SEV-SNP/pKVM/CCA）、Hyper-V/Xen 增强、SMM/MTRR/PIT 等 x86 遗留。仅当其扩展了通用底座时才计入可移植。

**关键校准事实**：riscv 已具备 `HAVE_KVM_IRQCHIP / IRQ_ROUTING / MSI / READONLY_MEM / DIRTY_RING_ACQ_REL`；**尚未** select `KVM_GUEST_MEMFD`（arm64 已有）→ guest_memfd 是明确的高价值移植候选。

## RISC-V 能力基线（源码盘点 Agent A，已落地）

内核树 = Linux 7.2.0-rc3（`/Users/zq/Desktop/patch-work/linux-riscv`）。**已成熟实现**：
- G-stage MMU（Sv32/39/48/57x4、大页、mmu_notifier、远程 TLB range flush）、AIA 中断（APLIC+IMSIC，含 HWACCEL）、Sstc 定时器、SBI-PMU、FP/Vector、广泛 SBI 扩展（base/hsm/sta/pmu/fwft/rfence/srst/…）、ONE_REG（10 大类，~75 ISA 扩展控制）、dirty ring（ACQ_REL）、binary stats、NACL（嵌套加速 shim，非嵌套虚拟化）。

**明确缺口（x86/arm 有、riscv 无或部分）——即移植候选来源**：
1. **guest_memfd / `KVM_CREATE_GUEST_MEMFD` + 内存属性** —— riscv 未 select；arm64 已有；核心在 `virt/kvm/guest_memfd.c`（大部分通用）。
2. **G-stage 大页 eager split / dirty-log 性能** —— riscv 仅 lazy fault-driven；且**关闭 dirty-log 后不回收/合并大页**（`gstage.c:265` 明确 TODO）。x86 有 eager split + `dirty_log_page_splitting_test`。
3. **ptdump / stage-2 页表 dumper** —— arm64 有 `ptdump.c`，riscv 无。
4. **IRQ bypass / posted interrupts**（`HAVE_KVM_IRQ_BYPASS` 未选）—— x86 posted-intr、arm64 GICv4 直注；riscv IMSIC 有潜力。
5. **selftests 缺口**：`guest_memfd_test`、`dirty_log_page_splitting_test`、AIA/IMSIC 功能测试、`pmu_counters_test`/`pmu_event_filter_test`（riscv 无对应）。
6. **硬件断点/单步调试**（`kvm_guest_debug_arch` 为空）、**PMU event filter**、**TSO dirty-ring 变体**、**async-PF/更多 PV 特性**。

**明确不适用（Tier-C，仅在扩展通用底座时才计入）**：嵌套虚拟化、机密计算(TDX/SEV/pKVM/CCA)、VMX/SVM、GIC/VGIC/ITS 内部、Hyper-V/Xen、SMM/MTRR。

## Top 可移植候选（初步，待阶段 2 用补丁全文与源码逐一确认）

| # | 移植点 | 层级 | riscv 落点 | patchwork 来源类别 |
|---|--------|------|-----------|------------------|
| 1 | guest_memfd / 内存属性 | A/B | 新 Kconfig + mmu 钩子 | `KVM: guest_memfd`, `KVM: x86/arm64: gmem` |
| 2 | 大页 eager split + 关闭 dirty-log 后合并 | B | `gstage.c` | `KVM: arm64/x86: eager split`, `dirty_log_perf` |
| 3 | stage-2 ptdump 调试 | B | 新 `ptdump`/debugfs | `KVM: arm64: ptdump` |
| 4 | IRQ bypass / 直注 | B/C | `aia_imsic.c` | `KVM: irq bypass`, `GICv4` |
| 5 | 通用 selftest lib/测试 | A/B | `selftests/kvm/riscv` | `KVM: selftests: *` |
| 6 | Tier-A 通用改动（`virt/kvm/*`） | A | 自动适用 | `KVM:`(无架构前缀) |

## 实施步骤

### 阶段 0：数据采集（Python 脚本 → `kvm-riscv/data/`）
- 抓取全部 217 页元数据 → `all_patches.jsonl`（~21,687 条）。
- 健壮性：失败重试、断点续抓、礼貌延时；仅取元数据不取全文。

### 阶段 1：分类与去重（Python 脚本）
- 精化架构分类器（修正 `its`/`arm` 等误判，基于标题 + series 名）。
- **按 series 去重**：归一化系列名（去 `[vN]`、`[PATCH]`、`m/n` 计数），保留最新版本。
- 按 20 类 / 3 层级打标签（关键词规则）。
- 产出：`x86_arm_series.csv`（每系列一行：标题/架构/类别/层级/状态/日期/web_url）+ `category_counts.md`（统计）。

### 阶段 2：可移植性分析（并行子代理，每类一个）
- 分派：Tier-A/B 每个类别一个子代理（约 10-12 个，分批并行）；Tier-C 合并为 1-2 个「批量归类」代理（只标记低/无可移植，不深挖）。
- 每个子代理输入：该类别去重系列清单（含 web_url/mbox）+ riscv 基线摘要 + 本地源码访问权。
- 对每个系列判定四态之一：`ALREADY(riscv 已有) / PORTABLE(通用层直接适用) / PATTERN(机制可复用需重写) / N-A(硬件专属不适用)`。
- 对 PORTABLE/PATTERN：给出**具体可移植点** + **riscv 落点文件/机制**；对每类最强的 3-6 个候选拉 `mbox` 全文确认 diff 与落点成立。
- 产出结构化结果（表格：系列名/状态/判定/可移植点/riscv 落点/web_url）。

### 阶段 3：综合与成文（主代理 → `kvm-riscv/`）
- `README.md`：方法论与数据出处、总体统计、三层级概览、**Top 40-60 可移植候选排名表**（原补丁 → 可移植点 → riscv 落点 → 依据）、结论与建议。
- `analysis/`：按 Tier/类别拆分的明细文档（遵循「多而小」，每文件 <800 行）。
- `data/`：`all_patches.jsonl`（全量）+ `x86_arm_series.csv`（去重分类索引，覆盖全部 ~2000 系列）+ `category_counts.md`（统计）作为可追溯证据。
- `scripts/`：抓取与分类的 Python 脚本（可复现）。

## 关键决策（已采用合理默认，可在审批时调整）
- **深度**：全量自动分类索引（覆盖全部去重系列，每条带判定）+ Top 40-60 候选深度分析。兼顾「针对每个分析」与可行性。
- **数据范围**：全量抓取 21,687 条 → 按 series 去重保最新版；索引含所有 state 但标注，深挖优先 accepted/mainlined/new 与新特性（superseded 中间版本经去重自然滤除）。
- **结构**：`kvm-riscv/` 下多文件（README + analysis/ + data/ + scripts/），中文成文与项目一致。
- **不做**：不触碰其他路径；不修改内核源码（只读分析）；不逐条为 Tier-C HW 专属补丁写散文。

## 验证方式
- 数据完整性：`all_patches.jsonl` 行数 ≈ 21,687；去重后系列数、各架构/类别计数自洽（脚本打印校验）。
- 抽查：随机抽 10 个「PORTABLE/PATTERN」结论，核对 mbox 全文与 riscv 源码落点是否成立。
- 交叉核对：结论与 riscv 基线一致（不把已有特性误报为「可移植」，不把纯 HW 特性误报为可移植）。
- 可追溯：文档中每个候选都带 patchwork `web_url` 与 riscv 目标文件路径。

## 预期规模与成本提示
- 网络：217 次 API 分页请求（元数据）+ 数十次 mbox 全文抓取（仅候选）。
- 算力：约 12-14 个分析子代理分批并行。这是一次较大的 token 投入，属研究型任务的合理开销。
