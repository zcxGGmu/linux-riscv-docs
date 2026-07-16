# Linux RISC-V 潜在贡献点探索 · 开发者指引

本目录汇总了**多轮、多方法**面向 Linux RISC-V 内核的贡献点挖掘。不同子目录用不同信号源：有的从 KVM / linux-arm-kernel 邮件列表出发，有的系统比较 RISC-V 与 arm64/x86 的架构接口，有的从只读内核树静态扫描、ISA 批准差集或汇编优化差集出发，还有的是 RVV/FPSIMD、ISA 对标等专题研究。

> **把它当作「候选池 + 路线图」，不要把任何结论直接当成可立即投稿的事实。**
> 绝大多数报告固定在某个基线（Linux v7.2.0-rc2/rc3、2025–2026 某时间窗），**开工前必须重新核查当前 mainline、linux-next、对应 maintainer tree 和 lore**，确认没有更新版本、替代系列或已合并/被拒。数据快照日约为 2026-07。

---

<!-- OPENCLAW_TASK_CLAIMS_START -->

## 任务领取登记（OpenClaw 自动维护）

> 这个区块由 `claw-mac-linux` 在 Discord `#linux-riscv` 频道中根据领取消息维护。领取前会先检查是否已被占用，避免重复开工。

| 状态 | 候选 / 任务 | 领取人 | Discord ID | 时间（Asia/Shanghai） | 来源 |
|---|---|---|---|---|---|

<!-- OPENCLAW_TASK_CLAIMS_END -->

## 30 秒决策：按目标选入口

| 你的目标 | 优先阅读 |
|---|---|
| 想尽快独立落地一个 greenfield 小补丁 | 本页 [§4 新贡献者起点](#41-新贡献者greenfield-独立小补丁) → [`claude-4-8/riscv-isa-optgap/`](claude-4-8/riscv-isa-optgap/README.md)、[`riscv-arm-x86-gap/09-…roadmap`](riscv-arm-x86-gap/09-ranked-contribution-roadmap.md) |
| 想系统理解 RISC-V 相对 arm64/x86 的架构缺口 | [`riscv-arm-x86-gap/`](riscv-arm-x86-gap/README.md)（90 候选，带编号/评分/首个可提交单元） |
| 想从近期 ARM 邮件补丁找可移植机会 | [`riscv-contributions-explore/`](riscv-contributions-explore/README.md)（168 候选）、[`claude-4-8/riscv-arm-gap/`](claude-4-8/riscv-arm-gap/README.md) |
| 想做 KVM / G-stage / AIA / IOMMU / PMU | [`kvm-riscv/`](kvm-riscv/README.md)（70 候选，T1/T2/T3）、[`claude-4-8/kvm-riscv/`](claude-4-8/kvm-riscv/README.md) |
| 想做 RVV / 内核态 Vector / 上下文切换 / 测试 | [`fpsimd/`](fpsimd/)（专题研究，见 `kilo/` gap 分析） |
| 想做 ISA 语义、RISC-V↔ARM 对标或性能测试方案 | [`riscv_arm_isa/`](riscv_arm_isa/)（对标研究，非候选表） |
| 想追溯原始数据、脚本与子代理分析过程 | [`claude-4-8/`](claude-4-8/) |
| 只想补基础资料（QEMU/KVM/规范链接） | [`kvm-cfi/`](kvm-cfi/README.md) |

---

## 目录地图

| 目录 | 发现方法 | 规模 | 分级体系 | 成熟度 | 适合人群 |
|---|---|---|---|---|---|
| [`riscv-arm-x86-gap/`](riscv-arm-x86-gap/) | 架构接口差距对比（RISC-V vs arm64 vs x86） | **90 候选**（P0 26/P1 48/P2 16） | P0–P2 优先级 + G0–G4 通用化度 | 候选清单（带首个可提交单元） | 想系统选题、要明确编号与落点的人 |
| [`riscv-contributions-explore/`](riscv-contributions-explore/) | linux-arm-kernel 邮件挖掘（2025-01~2026-07-10，6.5 万补丁→2.9 万谱系） | **168 候选**（P0 56/P1 74/P2 38） | P0–P2 | 候选清单 + 分领域审计 | 想跟踪近期上游、从 ARM 社区迁移机制的人 |
| [`kvm-riscv/`](kvm-riscv/) | KVM Patchwork/lore（2025 全年 + 2026H1） | **70 候选**（T1 26/T2 25/T3 19） | T1 近期/T2 需重写/T3 依赖基础 | 候选清单 | 熟悉 KVM、G-stage、AIA、SBI PMU、guest_memfd 的人 |
| [`claude-4-8/`](claude-4-8/) | **四轮四方法**（见下）的完整工作区，含脚本/分类/四态判定 | 四组深挖 | 四态：ALREADY/PORTABLE/PATTERN/N-A | 候选 + 可复现原始数据 | 需要复现、核对分类、追溯 patchwork/lore 链接的人 |
| [`fpsimd/`](fpsimd/) | 专题：ARM64 FPSIMD/SVE/SME ↔ RISC-V Vector 状态管理 | 5 个 gap 候选 + 逐补丁精读 | 三阶段路线图 | **研究报告**（`kilo/` 最接近落地） | 想做 RVV 上下文切换、ptrace/coredump、性能与测试的人 |
| [`riscv_arm_isa/`](riscv_arm_isa/) | 专题：RISC-V↔ARM ISA/虚拟化语义对标 + 性能方法学 | 7 组扩展对标 + 2 份虚拟化性能方案 | — | **研究报告**（几乎无现成候选） | 做规范研究、测试方案、虚拟化性能基线的人 |
| [`kvm-cfi/`](kvm-cfi/) | 参考资料/工具链接集合 | — | — | 链接，非候选 | 初学者、需要补基础资料的人 |

### `claude-4-8/` 的四轮（四种发现方法各一）

| 子目录 | 方法 | 规模/结论 |
|---|---|---|
| [`kvm-riscv/`](claude-4-8/kvm-riscv/README.md) | KVM 邮件列表 | 21,687 补丁 |
| [`riscv-arm-gap/`](claude-4-8/riscv-arm-gap/README.md) | linux-arm-kernel 邮件列表 | 66,718 补丁；~450 PORTABLE + ~210 PATTERN + ~61 ALREADY |
| [`riscv-contrib-scan/`](claude-4-8/riscv-contrib-scan/README.md) | 只读内核树静态扫描（features 矩阵 / Kconfig select 差集 / 代码 TODO） | 从 ~307 原始信号甄别出约 12 个高价值，真:噪 ≈ 1:7.7 |
| [`riscv-isa-optgap/`](claude-4-8/riscv-isa-optgap/README.md) | ISA 批准差集 + asm-generic 优化差集 | ALREADY 13 / PORTABLE 1 / PATTERN 17 / N-A 6 |

---

## 发现方法学（理解候选为何不同、如何互补）

同一个贡献点可能被多种方法从不同角度发现，编号体系互不相同。理解方法能帮你判断候选的**新鲜度**与**落地姿势**：

- **A. 邮件列表挖掘**（`kvm-riscv/`、`claude-4-8/{kvm-riscv,riscv-arm-gap}`、`riscv-contributions-explore/`）：跟踪在途上游补丁，适合迁移通用机制/测试方法。**风险**：邮件状态变化快，可能已合并或被替代。
- **B. 架构接口差距对比**（`riscv-arm-x86-gap/`）：系统比较三架构接口，识别缺失能力与可下沉的通用化机会。**风险**：缺 `select` 未必是缺口（可能硬件模型不同或已有 fallback）。
- **C. 内核树静态扫描**（`claude-4-8/riscv-contrib-scan/`）：从当前树 grep 真实缺口。**风险**：机器信号噪声高（真:噪 ≈ 1:7.7），须逐条回源码核实。
- **D. ISA 批准 + asm 优化差集**（`claude-4-8/riscv-isa-optgap/`）：RVI 已批准扩展 ∖ 内核已识别集；riscv 回退通用 C/标量 vs arm64/x86 ISA 优化汇编。最 RISC-V 专属、假阳低。
- **E. 专题研究**（`fpsimd/`、`riscv_arm_isa/`、`kvm-cfi/`）：深潜某一主题的机制/对标/性能方法学。**多为背景与选题材料，须先转成具体内核落点与测试边界，才是补丁。**

## 全量内容审计与可信度

本次汇总逐类覆盖 `patch-work/` 的 **188 个文件**：131 份 Markdown、47 份分类 JSONL、5 个采集/分类脚本、2 份 CSV、1 个 shell 探针、1 份 PDF 和 1 份抓取进度 JSON。原始索引用于追溯，最终任务只从已经人工甄别的 ranked/curated 报告中提取，避免把分类器命中直接当作贡献点。

| 内容簇 | 实际覆盖 | 汇总结论 | 在本清单中的处理 |
|---|---|---|---|
| `riscv-arm-x86-gap/` | 12 份方法、接口、专题、路线图和来源索引 | 90 个候选中，26 个原 P0、48 个原 P1、16 个原 P2；81 个在固定基线中未发现覆盖系列 | 作为架构接口任务的主编号和本地证据入口 |
| `riscv-contributions-explore/` | 168 个精选候选、227 个原始补丁链接、4 个领域审计 | 大量 generic/driver-core 补丁已天然覆盖 RISC-V；真正需要 RISC-V 补丁的是 arch glue、测试、驱动采用和语义重写 | 与 `MM/IRQ/CORE/PLAT/VIRT/GEN` 去重；机械采用合成工作包 |
| `kvm-riscv/` | 2025 + 2026H1 两期报告、70 个去重候选 | 近期价值集中在 selftests、G-stage 正确性、AIA、SBI PMU/timer；guest_memfd、nested、CoVE 依赖重 | 保留独有的测试任务；实现类与 `VIRT-*` 合并 |
| `claude-4-8/` | 21,687 KVM 补丁、66,718 ARM 补丁的 JSONL/CSV 与分类脚本；静态扫描约 309 个信号；ISA/asm 差集 37 项 | 原始扫描噪声高；静态 TODO 真缺口约 1:7.7。ISA/asm 差集给出 6 个真正 greenfield 项 | 只采纳四态甄别后的 PORTABLE/PATTERN；ALREADY/N-A 不进入待办 |
| `fpsimd/` | 37 份 RVV/FPSIMD 状态管理、原系列、调用链、测试和 1 份 25 页 PDF | 旧文档的 5 个 gap 多数已过时；ptrace、coredump、kernel Vector 已有，当前可靠增量是 stress/preempt selftest 与 context 内存策略 | 测试先行；CPU 绑定/刷新/统计均标低置信度 |
| `riscv_arm_isa/` | ISA 对标、Ssnpm/MTE、SPEC2006 与 VM 生命周期方案 | 适合做 benchmark/spec gap 设计，不是现成内核补丁；文中的定量分值没有实测数据支撑 | 作为验证与需求形成任务，不直接标高优先实现 |
| `kvm-cfi/` | QEMU/KVM、ARM/RISC-V 规范和工具链接 | 参考资料集，不包含独立可提交缺口 | 不单列代码任务 |
| `.context/`、脚本、原始数据 | 研究计划、抓取/分类实现、进度文件 | 说明数据来源和复现路径，不代表维护者接受方向 | 作为 provenance，不作为贡献候选 |

数据完整性限制：ARM 抓取脚本引用的 `data/all_patches.jsonl` 未保留，因此 66,718 条原始 patch 不能只靠当前目录重算；但 `arm_series.csv` 的 10,745 条逻辑系列与 23 个分类 JSONL 的总数闭合。KVM/ARM 分类器主要按标题正则工作，可能把 DRM “atomic bridge” 等误分，Patchwork `state=new` 也不能证明尚未合入。采集脚本还存在关闭 TLS 校验、输出与进度更新之间中断可能重复追加的复现风险。最终状态必须以当前源码和邮件线程为准。

### 统一评分口径

- **优先级**：`P1` = 近期高价值公开贡献；`P2` = 有价值但需更多前置或设计；`P3` = 探索/长期；`P0` 仅保留给安全或紧急私下事项，本目录当前没有。原报告 `P0/P1/P2` 统一映射为本页 `P1/P2/P3`。
- **难度**：`XS` 文档/单行；`S` 单模块和聚焦测试；`M` 相邻模块或行为变化；`L` 架构语义/并发/硬件验证；`XL` 跨子系统、UAPI、安全模型或多维护者协调。
- **置信度**：`高` = 有当前基线、源链接、明确落点和验证路径；`中` = 缺硬件/复现或需确认上游状态；`低` = 研究假设、无实测或方向依赖尚未稳定。
- **状态**：`greenfield` 可先查重后独立起系列；`unclaimed` 仅表示固定基线未发现完整系列；`active RFC` 应参与现有系列；`foundation` 必须先完成依赖；所有状态都要在开工日重查 mainline、linux-next、maintainer tree 与 lore。

当前 **Top 5**：IRQ-09 clockevent `oneshot-stopped`、CORE-14 `HAVE_CMPXCHG_LOCAL`、BOOT-01 crashkernel CMA、ISA-01 Zbb `memcmp`、ISA-03 POLYVAL。它们的共同点是缺口经当前树抽检仍存在、首补丁边界明确、验证路径可控。

---

## 4. 推荐起点（跨目录合并去重）

> 核心判断轴：**greenfield（内核侧无在途补丁，适合从零独立落地）** vs **active-RFC（已有活跃上游系列，宜接力/评审/补测试而非另起炉灶）**。

### 4.1 新贡献者：greenfield 独立小补丁

边界窄、依赖少、可独立评审，适合作为第一个补丁：

| 候选 | 来源目录 | 落点 / 首步 | 备注 |
|---|---|---|---|
| `memcmp` + `memchr` Zbb 优化 | `claude-4-8/riscv-isa-optgap` | 新增 `arch/riscv/lib/{memcmp,memchr}.S` + 补 `__HAVE_ARCH_*` 宏 | **greenfield 最干净**，可整段复用现有 `strcmp.S`/`strnlen.S` |
| `polyval` 加速钩子 | `claude-4-8/riscv-isa-optgap` | 在 `lib/crypto/riscv/gf128hash.h` 补 `polyval_*_arch` | 复用已在树的 `ghash_zvkg` + 转换 helper，成本极低 |
| `strchr` / `strrchr` Zbb 变体 | `claude-4-8/riscv-isa-optgap` | 改现有 `.S` 加 Zbb 分派 | 原作者已明示预留为 Zbb 基线 |
| 选择 `HAVE_CMPXCHG_LOCAL` | `riscv-arm-x86-gap` **CORE-14**（≡ contrib-scan §1） | 仅 `select` + 补编译矩阵和原子语义测试 | G0，多目录交叉印证 |
| clockevent 补 `oneshot-stopped` | `riscv-arm-x86-gap` **IRQ-09** | 接线 `.set_state_oneshot_stopped`，附 Sstc/SBI 测试 | G1，单钩子 |
| 通用 helper 下沉 | `riscv-arm-x86-gap` **GEN-02/03/06/09/13** | 先做行为不变的 generic helper，再迁移 RISC-V | 原报告 P0/G2；本页映射为 P1，机械且低风险 |
| 驱动 devres/机械迁移一批 | `riscv-contributions-explore` 原 P0「低」难度项 | 如 `devm_clk_bulk_get_optional_enable`、`sg_nents_for_dma` 等 | 通用 API 已合入；只针对仍使用旧模式的具体 RISC-V 驱动做采用 |

### 4.2 中期高价值：多为 active-RFC（接力/评审姿势）

价值高但通常已有活跃上游系列，**宜复现评审意见、补测试、补待办子块，而非平行重写**：

- **可观测性/加固**：reliable stacktrace → livepatch（`riscv-arm-x86-gap` CORE-01，active RFC）；`static_call` 后端（CORE-03）；`Sdtrig` 硬件断点（CORE-02 + `claude-4-8/riscv-isa-optgap`，active RFC）；BPF `arch_bpf_stack_walk`/exceptions（CORE-06/07/08）；KCSAN/KASAN SW_TAGS（CORE-12；`riscv_arm_isa/` 指向基于 Ssnpm/Supm 的软件标签）。
- **MMU/DMA**：批量非一致 DMA 同步（`riscv-arm-x86-gap` MM-02 = `riscv-contributions-explore` #9，P0）；`pte_needs_flush()`/`ptep_try_set()`/范围 TLB 批处理（MM-06/07/11）。
- **ISA 特性**：`Ssqosid`/resctrl（`claude-4-8/riscv-isa-optgap`，推翻旧「无硬件」判断，active RFC Fustini）；`Ssctr/Smctr` 分支记录、计数器委派（active RFC Rivos）。
- **KVM/虚拟化**：G-stage 脱锁销毁与可调度化（`kvm-riscv` + `riscv-arm-x86-gap` VIRT-02）；`KVM_PRE_FAULT_MEMORY`（VIRT-04）；G-stage/IOMMU ptdump（VIRT-01）；coherent 平台 `KVM_VFIO`（VIRT-06）；大量 KVM selftests 迁移（`kvm-riscv` T1）。

### 4.3 专题研究：先转成补丁边界再动手

`fpsimd/` 与 `riscv_arm_isa/` 偏研究，投稿前须转成具体落点与测试：

- **RVV 内核态**（`fpsimd/`）：当前树已有 ptrace、coredump、kernel-mode Vector 与可抢占 Vector；真实增量是移植 ARM64 `fp-stress`、补 `CONFIG_RISCV_ISA_V_PREEMPTIVE` 内核自测，再量化 context 内存/切换成本。CPU 绑定和状态刷新只保留为低置信研究，**没有压力测试与 profile 证据前不得提交优化**。
- **虚拟化性能方法学**（`riscv_arm_isa/codex/v1/`）：SPEC CPU2006 折损率、11 阶段 VM 生命周期方案可直接拿去设计 benchmark（当前均无实测数据）。

### 4.4 明确不适合作为第一个补丁

nested KVM、CoVE / 机密计算、IOMMU SVA/PASID、机密 DMA、direct interrupt injection、`memcpy/memset` 的 RVV 化（社区有争议）——这些是长期方向或受 UAPI/固件/硬件/安全模型约束（多为 `riscv-arm-x86-gap` P2 / G4）。

---

## 候选去重与交叉引用

多个目录会从不同方法命中同一贡献点，**开工前先跨目录搜一遍**，避免重复投入或漏看已有评审：

- `HAVE_CMPXCHG_LOCAL`：`riscv-arm-x86-gap` CORE-14 ≡ `claude-4-8/riscv-contrib-scan` 与 `riscv-isa-optgap`。
- `Sdtrig` / 硬件断点：`riscv-arm-x86-gap` CORE-02 ≡ `claude-4-8/riscv-isa-optgap`（priv 簇）。
- 批量非一致 DMA 同步：`riscv-arm-x86-gap` MM-02 ≡ `riscv-contributions-explore` #9。
- reliable stacktrace / livepatch：`riscv-arm-x86-gap` CORE-01 ≡ `riscv-contributions-explore`（core-tooling）≡ `claude-4-8/riscv-arm-gap`。
- KVM G-stage / AIA / guest_memfd / PMU：`kvm-riscv`、`riscv-arm-x86-gap` VIRT-*、`riscv-contributions-explore`（irq-timer-pmu-kvm）与 `claude-4-8/kvm-riscv` 大量交叉。
- KASAN_SW_TAGS：`riscv_arm_isa/`（Ssnpm/MTE 研究）指向，`riscv-arm-x86-gap`/`claude-4-8` 亦列为真缺口。

---

## Linux RISC-V 移植贡献统一待办

下表是跨目录去重后的**领取主清单**。复选框代表尚待完成，不表示维护者已同意；“源”是原补丁、对端实现或当前源码基线，“证据”链接到本地完整候选卡片。

### P1：近期优先，greenfield / 聚焦 PR

| 待办 | 难度 | 置信 | 状态 / 首个可提交单元 | 源与证据 |
|---|---|---|---|---|
| [ ] **ISA-01：Zbb `memcmp`** | S | 高 | greenfield；新增 `arch/riscv/lib/memcmp.S`、宏、PIE/KASAN 处理和 lib 测试 | [对端/模板源码](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/arch/riscv/lib/strcmp.S?id=d96fcfe1b7f94ac742984ae7986b94a116abff1b) · [证据](claude-4-8/riscv-isa-optgap/analysis/asm_string.md#候选-1memcmppattern最干净首推) |
| [ ] **ISA-02：Zbb `memchr`** | S | 高 | greenfield；复用 `strnlen.S` 的 `orc.b` 有界搜索并补 `__HAVE_ARCH_MEMCHR` | [对端/模板源码](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/arch/riscv/lib/strnlen.S?id=d96fcfe1b7f94ac742984ae7986b94a116abff1b) · [证据](claude-4-8/riscv-isa-optgap/analysis/asm_string.md) |
| [ ] **ISA-03：Zvkg POLYVAL hooks** | S | 高 | greenfield；先复用 `ghash_zvkg` 与转换 helper 接三个 `polyval_*_arch` 钩子 | [现有 RISC-V glue](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/lib/crypto/riscv/gf128hash.h) · [证据](claude-4-8/riscv-isa-optgap/analysis/asm_crypto.md) |
| [ ] **ISA-04：Zbb `strchr/strrchr`** | S | 高 | greenfield；在现有字节循环上加 Zbb 分派，两个函数可拆成独立补丁 | [当前系列证据](claude-4-8/riscv-isa-optgap/analysis/asm_string.md) · [汇总](claude-4-8/riscv-isa-optgap/README.md) |
| [ ] **CORE-14：完整启用 `HAVE_CMPXCHG_LOCAL`** | S | 高 | unclaimed；`select` + `asm/percpu.h` 快路径 + PREEMPT/宽度语义测试，不能只加 Kconfig | [RISC-V cmpxchg](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/arch/riscv/include/asm/cmpxchg.h?id=d96fcfe1b7f94ac742984ae7986b94a116abff1b) · [证据](riscv-arm-x86-gap/05-core-abi-observability-hardening.md#core-14) |
| [ ] **IRQ-09：clockevent `oneshot-stopped`** | S | 高 | unclaimed；接 `.set_state_oneshot_stopped = riscv_clock_shutdown`，覆盖 Sstc/SBI | [当前驱动](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/drivers/clocksource/timer-riscv.c?id=d96fcfe1b7f94ac742984ae7986b94a116abff1b) · [证据](riscv-arm-x86-gap/04-irq-smp-time.md#irq-09) |
| [ ] **GEN-03：复用 `perf_get_regs_user()` fallback** | XS | 高 | unclaimed；行为不变地删除 RISC-V 重复实现并做 perf 编译/采样回归 | [generic API](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/include/linux/perf_regs.h?id=d96fcfe1b7f94ac742984ae7986b94a116abff1b) · [证据](riscv-arm-x86-gap/08-genericization-opportunities.md#gen-03) |
| [ ] **GEN-06：通用 PCI raw bus lookup** | S | 高 | unclaimed；新增 `pci_generic_raw_read/write()`，首版只迁移 RISC-V | [PCI core](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/drivers/pci/access.c?id=d96fcfe1b7f94ac742984ae7986b94a116abff1b) · [证据](riscv-arm-x86-gap/08-genericization-opportunities.md#gen-06) |
| [ ] **GEN-09：`copy_oldmem_page()` generic default** | S | 高 | unclaimed；提供 memremap 默认实现并迁移 RISC-V，特殊架构保留 override | [crash API](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/include/linux/crash_dump.h?id=d96fcfe1b7f94ac742984ae7986b94a116abff1b) · [证据](riscv-arm-x86-gap/08-genericization-opportunities.md#gen-09) |
| [ ] **GEN-13：下沉 cacheinfo `ci_leaf_init()`** | S | 高 | unclaimed；机械下沉 helper，不改变 cache 信息来源策略 | [arm64 邻近系列](https://lore.kernel.org/linux-arm-kernel/20251119122305.302149-6-ben.horgan@arm.com/) · [证据](riscv-arm-x86-gap/08-genericization-opportunities.md#gen-13) |
| [ ] **KVM-T01：AIA config/attribute freeze selftest** | M | 高 | 新增 `aia_device_test`：合法/非法 config、INIT 前可写、INIT 后冻结，按 EMUL/AUTO/HWACCEL 能力 skip | [arm64 模板](https://patchwork.kernel.org/project/kvm/patch/20250613155239.2029059-5-rananta@google.com/) · [证据](claude-4-8/kvm-riscv/analysis/selftests.md) |
| [ ] **KVM-T02：IMSIC MSI 注入 + WFI 唤醒测试** | M | 高 | 依赖 AIA helper；先单 vCPU smoke test，再覆盖错误 target、pending/enable 与跨 vCPU | [MSI 源测试](https://patchwork.kernel.org/project/kvm/patch/20250923050942.206116-36-Neeraj.Upadhyay@amd.com/) · [WFI 源测试](https://patchwork.kernel.org/project/kvm/patch/20250923050942.206116-32-Neeraj.Upadhyay@amd.com/) |
| [ ] **KVM-T03：SBI STA vCPU 重建/换线程** | M | 高 | 删除/重建 vCPU 并换 pthread 后，验证 steal time 单调且不过跳 | [源补丁](https://patchwork.kernel.org/project/kvm/patch/20260505003044.78693-5-dongli.zhang@oracle.com/) · [证据](claude-4-8/kvm-riscv/analysis/timer_pv.md) |
| [ ] **KVM-T04：SBI PMU 重编程累计值** | M | 高 | 先写 cfg_match/stop/reconfigure/start 的失败测试，再修 counter/perf hardware value 合并 | [源补丁](https://patchwork.kernel.org/project/kvm/patch/20260603231905.1738487-2-seanjc@google.com/) · [证据](claude-4-8/kvm-riscv/analysis/pmu.md) |
| [ ] **DRV-01：低风险 devres/helper 采用批次** | S | 中 | 每个驱动单独 PR：优先 clk、dmaengine、runtime-PM、workqueue、scatterlist helper；先确认 generic 补丁已合入 | [168 项总表 #6/#11/#14/#30/#34/#37](riscv-contributions-explore/analysis/curated_candidates.md) · [示例源补丁](https://lore.kernel.org/linux-arm-kernel/20260116192725.972966-2-suraj.gupta2@amd.com/) |
| [ ] **BOOT-01：crashkernel CMA 接线** | XS | 高 | code-derived；在 RISC-V 预留流程调用现有 `reserve_crashkernel_cma()`，核对预留顺序 | [arm64 源补丁](https://patchwork.kernel.org/project/linux-arm-kernel/patch/20260126081334.699147-1-ruanjinjie@huawei.com/) · [证据](claude-4-8/riscv-arm-gap/analysis/boot_kexec_userabi.md) |
| [ ] **GEN-VMEMMAP：复用 generic vmemmap PMD helper** | XS | 高 | 参与现有系列，删除 RISC-V 私有重复 helper，补 sparsemem/hotplug 构建测试 | [v3 源系列](https://patchwork.kernel.org/project/linux-arm-kernel/patch/20260601084845.3792171-3-songmuchun@bytedance.com/) · [证据](claude-4-8/riscv-arm-gap/analysis/mm_pgtable_1.md) |
| [ ] **CORE-KPROBE：修复重入 `kprobe_busy_begin()` 状态** | S | 高 | 通用修复；保存/恢复外层 current probe/ctlblk 状态，并补 RISC-V 异常嵌套压力 | [源补丁](https://lore.kernel.org/linux-arm-kernel/20260302105347.3602192-2-khaja.khaji@oss.qualcomm.com/) · [证据](riscv-contributions-explore/analysis/audit_core_tooling.md) |
| [ ] **RVV-T02：可抢占 kernel-mode Vector 自测** | L | 高 | 为调度、softirq、signal、CPU migration、nested depth 与 dirty/restore 标志构造内核测试 | [RVV v11 系列](https://lore.kernel.org/all/20240115055929.4736-1-andy.chiu@sifive.com/) · [证据](fpsimd/vector/SIMD_SVE_VECTOR_KERNEL/some-new-notes-6-10/riscv-vector性能优化-6-30.md#22-vector-selftests) |

### P1：高价值架构工作

| 待办 | 难度 | 置信 | 状态 / 首个可提交单元 | 源与证据 |
|---|---|---|---|---|
| [ ] **MM-02：批量非一致 DMA 同步** | L | 高 | unclaimed；先拆 Zicbom issue/completion helper，vendor provider 保守 fallback | [源系列](https://lore.kernel.org/linux-arm-kernel/20260228221316.59934-1-21cnbao@gmail.com/) · [证据](riscv-arm-x86-gap/03-mmu-memory-tlb.md#mm-02) |
| [ ] **MM-05：批量清大 folio young 位** | M | 高 | unclaimed；只加 `test_and_clear_young_ptes()`，不改变 TLB 语义 | [参考提交](https://git.kernel.org/pub/scm/linux/kernel/git/next/linux-next.git/commit/?id=9970a9a27ffca8b45c4a242f90adeb979fcaafb0) · [证据](riscv-arm-x86-gap/03-mmu-memory-tlb.md#mm-05) |
| [ ] **MM-06：精确 `pte_needs_flush()`** | M | 高 | unclaimed；先覆盖 4K PTE 位级决策与 selftest，THP 后续 | [参考源码](https://git.kernel.org/pub/scm/linux/kernel/git/next/linux-next.git/tree/arch/arm64/include/asm/tlbflush.h?id=bee763d5f341b99cf472afeb508d4988f62a6ca1) · [证据](riscv-arm-x86-gap/03-mmu-memory-tlb.md#mm-06) |
| [ ] **MM-07：原子 `ptep_try_set()`** | M | 高 | unclaimed；strict-zero cmpxchg + KUnit，BPF 消费者后续 | [参考提交](https://git.kernel.org/pub/scm/linux/kernel/git/next/linux-next.git/commit/?id=258df8fce42fecc23cd04242de3d39f1fe836433) · [证据](riscv-arm-x86-gap/03-mmu-memory-tlb.md#mm-07) |
| [ ] **MM-10：hot-remove 叶子边界/安全释放** | L | 高 | unclaimed；先加 preflight，拒绝切开已有 leaf | [参考提交](https://git.kernel.org/pub/scm/linux/kernel/git/next/linux-next.git/commit/?id=95a58852b0e5413b6ef4c93da60a80e89da9986a) · [证据](riscv-arm-x86-gap/03-mmu-memory-tlb.md#mm-10) |
| [ ] **MM-11：hot-remove 范围 TLB 批处理** | M | 高 | unclaimed；把逐页 flush 合为单次 range invalidation，释放晚于远端完成 | [源补丁](https://lore.kernel.org/linux-arm-kernel/20260309025725.455004-2-anshuman.khandual@arm.com/) · [证据](riscv-arm-x86-gap/03-mmu-memory-tlb.md#mm-11) |
| [ ] **CORE-13：native acquire/release AMO** | M | 高 | unclaimed；先替换一个 primitive 的 fence fallback，用 LKMM/objdump 证明等价 | [当前源码](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/arch/riscv/include/asm/atomic.h?id=d96fcfe1b7f94ac742984ae7986b94a116abff1b) · [证据](riscv-arm-x86-gap/05-core-abi-observability-hardening.md#core-13) |
| [ ] **CORE-16：`ARCH_HAS_EXECMEM_ROX`** | L | 高 | unclaimed；先做 RW→ROX allocator 并迁移一个 BPF JIT consumer | [generic execmem](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/mm/execmem.c?id=d96fcfe1b7f94ac742984ae7986b94a116abff1b) · [证据](riscv-arm-x86-gap/05-core-abi-observability-hardening.md#core-16) |
| [ ] **PLAT-06：CPPC FIE + RV32 `READ_HI`** | M | 高 | unclaimed；先修 high-low-high 一致性读，再扩展 IRQ-off FIE | [源补丁](https://lore.kernel.org/r/20250818143600.894385-2-apatel@ventanamicro.com) · [证据](riscv-arm-x86-gap/06-platform-acpi-numa-power-ras.md#plat-06) |
| [ ] **VIRT-01：G-stage ptdump** | M | 高 | unclaimed；只读 walker + VM debugfs，IOMMU dump 另起系列 | [arm64 模板](https://lore.kernel.org/linux-arm-kernel/20250407053113.746295-2-anshuman.khandual@arm.com/) · [证据](riscv-arm-x86-gap/07-kvm-iommu-virtualization.md#virt-01) |
| [ ] **VIRT-02：G-stage 脱锁销毁/可调度化** | L | 高 | unclaimed；先 detach root、锁外释放，普通 memslot zap 不变 | [源补丁](https://patchwork.kernel.org/project/kvm/patch/20251113052452.975081-4-rananta@google.com/) · [证据](riscv-arm-x86-gap/07-kvm-iommu-virtualization.md#virt-02) |
| [ ] **VIRT-04：`KVM_PRE_FAULT_MEMORY`** | M | 高 | unclaimed；接现有 G-stage fault helper，限制一种 memslot，并启用 selftest | [源补丁](https://patchwork.kernel.org/project/kvm/patch/20260612162354.73378-3-jackabt.amazon@gmail.com/) · [证据](riscv-arm-x86-gap/07-kvm-iommu-virtualization.md#virt-04) |

### P1：active RFC，只接力/评审/补测试

| 待办 | 难度 | 置信 | 合理贡献姿势 | 源与证据 |
|---|---|---|---|---|
| [ ] **CORE-01：reliable unwinder → livepatch** | L | 高 | 复现最新系列，补异常栈/模块/负测；不要平行定义另一套 frame contract | [v2 系列](https://lists.infradead.org/pipermail/linux-riscv/2026-June/093484.html) · [证据](riscv-arm-x86-gap/05-core-abi-observability-hardening.md#core-01) |
| [ ] **CORE-02 / ISA-Sdtrig：硬件断点** | XL | 高 | 补 perf/ptrace/KGDB 资源竞争、SBI-DBTR/直接 CSR 与虚拟化测试 | [在途系列](https://lists.infradead.org/pipermail/linux-riscv/2025-May/070170.html) · [证据](riscv-arm-x86-gap/05-core-abi-observability-hardening.md#core-02) |
| [ ] **CORE-06：`arch_bpf_stack_walk()`** | M | 高 | 补损坏 frame、tailcall/bpf2bpf/trampoline 组合 selftests | [v2 cover](https://lists.infradead.org/pipermail/linux-riscv/2026-June/093432.html) · [证据](riscv-arm-x86-gap/05-core-abi-observability-hardening.md#core-06) |
| [ ] **CORE-07：BPF exceptions** | L | 高 | 在 CORE-06 frame ABI 上补 exception landing/返回值/组合回归 | [在途补丁](https://lists.infradead.org/pipermail/linux-riscv/2026-June/093434.html) · [证据](riscv-arm-x86-gap/05-core-abi-observability-hardening.md#core-07) |
| [ ] **CORE-08：BPF subprog tailcalls** | L | 高 | 补 counter/frame 组合测试和 CI，不另写不兼容 JIT 规则 | [在途补丁](https://lists.infradead.org/pipermail/linux-riscv/2026-July/094209.html) · [证据](riscv-arm-x86-gap/05-core-abi-observability-hardening.md#core-08) |
| [ ] **IRQ-01：IRQ runtime constant** | M | 高 | 参与现有 genirq/RISC-V 接线，复测 alternatives、I-cache 与热路径收益 | [源补丁](https://lore.kernel.org/linux-arm-kernel/20260220090922.1506-3-jszhang@kernel.org/) · [证据](riscv-arm-x86-gap/04-irq-smp-time.md#irq-01) |
| [ ] **ISA-05：Ssqosid / resctrl** | L | 高 | 跟进 Fustini 系列；补 `srmcfg` sched-in、CBQRI、虚拟化和 resctrl selftests | [证据与在途索引](claude-4-8/riscv-isa-optgap/analysis/isa_priv_ras_qos.md) · [重要修正](claude-4-8/riscv-isa-optgap/README.md) |
| [ ] **ISA-06：Ssctr/Smctr branch stack** | L | 高 | 跟进现有系列；补 `perf record -b`、上下文切换和 KVM 暴露测试 | [证据与在途索引](claude-4-8/riscv-isa-optgap/analysis/isa_perf_counters.md) |
| [ ] **ISA-07：Smcdeleg/Ssccfg 计数器委派** | L | 高 | 跟进 Atish 系列；验证 SBI/直写双后端、过滤和 guest ownership | [证据与在途索引](claude-4-8/riscv-isa-optgap/analysis/isa_perf_counters.md) |

---

### P2：有价值的聚焦系列

| 待办 | 难度 | 置信 | 首个可提交单元 / 前置 | 源与证据 |
|---|---|---|---|---|
| [ ] **ISA-08：NH/Adiantum RVV** | L | 中 | greenfield；先实现单一 RVV NH core，必须带 crypto testmgr 与真实 fscrypt benchmark | [Adiantum 背景](https://lwn.net/Articles/772378/) · [证据](claude-4-8/riscv-isa-optgap/analysis/asm_crypto.md) |
| [ ] **ATOMIC-01：Zawrs 超时等待 helper** | M | 高 | generic helper 合入后，为 RISC-V 增 `wrs.nto` deadline variant | [v13 源补丁](https://patchwork.kernel.org/project/linux-arm-kernel/patch/20260702013334.140905-8-ankur.a.arora@oracle.com/) · [证据](claude-4-8/riscv-arm-gap/analysis/atomics_locking.md) |
| [ ] **MM-01：generic lazy-MMU 接口/测量** | M | 中 | 先接 no-op hooks、KUnit 和观测；没有可合并操作时不得宣称性能收益 | [源系列](https://lore.kernel.org/linux-arm-kernel/20251215150323.2218608-8-kevin.brodsky@arm.com/) · [证据](riscv-arm-x86-gap/03-mmu-memory-tlb.md#mm-01) |
| [ ] **MM-03：`cpu_cache_invalidate_memregion()`** | L | 中 | 先定义可拒绝的 Zicbom 物理范围后端；无能力时不得静默成功 | [arm64 参考](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/commit/?id=4d873c5dc3ed) · [证据](riscv-arm-x86-gap/03-mmu-memory-tlb.md#mm-03) |
| [ ] **MM-04：`ARCH_HAS_UACCESS_FLUSHCACHE`** | M | 中 | 保守 C copy-and-flush；明确 short copy 与 persistence-domain 语义 | [arm64 参考](https://git.kernel.org/pub/scm/linux/kernel/git/next/linux-next.git/tree/arch/arm64/lib/uaccess_flushcache.c?id=bee763d5f341b99cf472afeb508d4988f62a6ca1) · [证据](riscv-arm-x86-gap/03-mmu-memory-tlb.md#mm-04) |
| [ ] **MM-08：PBMT pageattr/PFN-map 一致性** | L | 中 | 先实现缓存类型冲突检测与 alias 同步，覆盖 DAX/PFNMAP | [源补丁](https://lore.kernel.org/r/20250722091504.45974-2-cuiyunhui@bytedance.com) · [证据](riscv-arm-x86-gap/03-mmu-memory-tlb.md#mm-08) |
| [ ] **MM-09：direct-map 大页 re-collapse** | L | 中 | 只做 PMD 级安全重合并，pageattr/模块/BPF/kexec 压测 | [参考提交](https://git.kernel.org/pub/scm/linux/kernel/git/next/linux-next.git/commit/?id=41d88484c71cd4f659348da41b7b5b3dbd3be1f6) · [证据](riscv-arm-x86-gap/03-mmu-memory-tlb.md#mm-09) |
| [ ] **MM-12：通用 hotplug 页表 teardown walker** | L | 中 | 先抽 callback walker 并只迁移一种架构，保持 free/flush 顺序 | [源补丁](https://lore.kernel.org/20260601084845.3792171-4-songmuchun@bytedance.com) · [证据](riscv-arm-x86-gap/03-mmu-memory-tlb.md#mm-12) |
| [ ] **MM-14：versioned ASID allocator 公共核心** | L | 中 | 抽纯 allocator 核心，首个消费者用 RISC-V；需小 ASID 位宽压力测试 | [RISC-V 基线](https://git.kernel.org/pub/scm/linux/kernel/git/next/linux-next.git/tree/arch/riscv/mm/context.c?id=bee763d5f341b99cf472afeb508d4988f62a6ca1) · [证据](riscv-arm-x86-gap/03-mmu-memory-tlb.md#mm-14) |
| [ ] **MM-15：active-hart 本地/远端 TLB 选择** | L | 中 | 先建立独立 active-hart 状态和 local-only fast path | [arm64 参考](https://lore.kernel.org/linux-arm-kernel/20260523134710.3827956-1-linu.cherian@arm.com/) · [证据](riscv-arm-x86-gap/03-mmu-memory-tlb.md#mm-15) |
| [ ] **MM-16：kernel mapping publication contract** | L | 中 | 先写清同步模型和测试，再接 RISC-V hook，避免只搬 barrier | [参考提交](https://git.kernel.org/pub/scm/linux/kernel/git/next/linux-next.git/commit/?id=6659d027998083fbb6d42a165b0c90dc2e8ba989) · [证据](riscv-arm-x86-gap/03-mmu-memory-tlb.md#mm-16) |
| [ ] **MM-COPYMC：分阶段接 `ARCH_HAS_COPY_MC`** | L | 中 | 先跟 generic fallback/hwpoison；RISC-V machine-check backend 单独 RFC | [源系列](https://patchwork.kernel.org/project/linux-arm-kernel/patch/20260618092124.3901230-7-tianruidong@linux.alibaba.com/) · [证据](claude-4-8/riscv-arm-gap/analysis/mm_pgtable_1.md) |
| [ ] **IRQ-04：IMSIC Multi-MSI 分配/回滚** | M | 中 | 先实现 parent-domain 批量分配和失败回滚，覆盖稀疏 ID | [参考补丁](https://lore.kernel.org/linux-arm-kernel/b906a38d443577de45923b335d80fc54c5638da0.1750860131.git.namcao@linutronix.de/) · [证据](riscv-arm-x86-gap/04-irq-smp-time.md#irq-04) |
| [ ] **IRQ-06：IMSIC remote sync hard irq_work** | L | 中 | 先证明时序收益与 hard-IRQ 安全，覆盖 CPU hotplug/affinity move | [当前实现](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/drivers/irqchip/irq-riscv-imsic-state.c?id=d96fcfe1b7f94ac742984ae7986b94a116abff1b) · [证据](riscv-arm-x86-gap/04-irq-smp-time.md#irq-06) |
| [ ] **IRQ-08：SBI HSM late-AP 代际控制** | L | 中 | 先构造启动超时后迟到 hart 的复现和状态机测试 | [相关提交](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/commit/?id=231fb999a9acd17b1335e79f0fd6fc627353a6bc) · [证据](riscv-arm-x86-gap/04-irq-smp-time.md#irq-08) |
| [ ] **IRQ-10：clocksource 稳定性证明** | M | 中 | 先量化跨 hart 偏差/漂移，再决定 `MUST_VERIFY` 策略 | [当前驱动](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/drivers/clocksource/timer-riscv.c?id=d96fcfe1b7f94ac742984ae7986b94a116abff1b) · [证据](riscv-arm-x86-gap/04-irq-smp-time.md#irq-10) |
| [ ] **CORE-03：static-call backend** | L | 中 | trampoline encoding/patching + selftest；模块距离、KCFI、I-cache 是验收门 | [generic core](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/kernel/static_call.c?id=d96fcfe1b7f94ac742984ae7986b94a116abff1b) · [证据](riscv-arm-x86-gap/05-core-abi-observability-hardening.md#core-03) |
| [ ] **CORE-04：完整 `ftrace_regs`/CFI call-ops** | L | 中 | 先固定寄存器保存 ABI和一个 call-op 路径，再扩展 kprobes | [RISC-V 基线](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/arch/riscv/include/asm/ftrace.h?id=d96fcfe1b7f94ac742984ae7986b94a116abff1b) · [证据](riscv-arm-x86-gap/05-core-abi-observability-hardening.md#core-04) |
| [ ] **CORE-12：KCSAN architecture enablement** | M | 中 | `select` + noinstr/atomic/entry/uaccess 插桩审计，先跑 sanitizer build matrix | [KCSAN Kconfig](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/lib/Kconfig.kcsan?id=d96fcfe1b7f94ac742984ae7986b94a116abff1b) · [证据](riscv-arm-x86-gap/05-core-abi-observability-hardening.md#core-12) |
| [ ] **CORE-17：默认 `VMAP_STACK`** | M | 中 | 先完成 RV32、overflow stack、kdump/hibernate 回归，再改默认值 | [RISC-V Kconfig](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/arch/riscv/Kconfig?id=d96fcfe1b7f94ac742984ae7986b94a116abff1b) · [证据](riscv-arm-x86-gap/05-core-abi-observability-hardening.md#core-17) |
| [ ] **PLAT-01：ACPI CPU physical hotplug** | L | 中 | UID↔hartid↔cpuid 映射 helper 和失败回滚先行 | [arm64 参考](https://lore.kernel.org/r/20240529133446.28446-18-Jonathan.Cameron@huawei.com) · [证据](riscv-arm-x86-gap/06-platform-acpi-numa-power-ras.md#plat-01) |
| [ ] **PLAT-02：SRAT Generic Initiator/_OSC** | M | 中 | 去架构名门控、补 capability 与 initiator-only node 测试 | [源补丁](https://patch.msgid.link/20250913023224.39281-1-xueshuai@linux.alibaba.com) · [证据](riscv-arm-x86-gap/06-platform-acpi-numa-power-ras.md#plat-02) |
| [ ] **PLAT-09：EFI capsule cache-maintenance hook** | L | 中 | 先通用化空 hook/capability，再接 non-coherent/Zicbom | [EFI core](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/drivers/firmware/efi/capsule.c?id=d96fcfe1b7f94ac742984ae7986b94a116abff1b) · [证据](riscv-arm-x86-gap/06-platform-acpi-numa-power-ras.md#plat-09) |
| [ ] **PLAT-10：crash hotplug 动态 `elfcorehdr`** | M | 中 | 先接动态事件 hook、容量检查和并发处理 | [公共 helper](https://patch.msgid.link/20260629094746.191843-4-ruanjinjie@huawei.com) · [证据](riscv-arm-x86-gap/06-platform-acpi-numa-power-ras.md#plat-10) |
| [ ] **PLAT-11/12：APEI/GHES/RAS 基础** | L | 中 | 先做映射属性/Kconfig 与 EINJ 注入；processor CPER/EDAC 后续 | [GHES core](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/drivers/acpi/apei/ghes.c?id=d96fcfe1b7f94ac742984ae7986b94a116abff1b) · [证据](riscv-arm-x86-gap/06-platform-acpi-numa-power-ras.md#plat-11) |
| [ ] **PLAT-13：ACPI memory hotplug 闭环** | M | 中 | QEMU/firmware add-remove-readd 测试先行，只修复复现出的残余问题 | [vmemmap 前置](https://lore.kernel.org/20260630-mark-after-vmemmap-populate-v4-1-febbc15da028@iscas.ac.cn) · [证据](riscv-arm-x86-gap/06-platform-acpi-numa-power-ras.md#plat-13) |
| [ ] **VIRT-03：guest_memfd shared/mappable** | L | 中 | 单一 shared fault path，private/CoVE 不进首版 | [arm64 源补丁](https://patchwork.kernel.org/project/kvm/patch/20250729225455.670324-19-seanjc@google.com/) · [证据](riscv-arm-x86-gap/07-kvm-iommu-virtualization.md#virt-03) |
| [ ] **VIRT-05：KVM userfault exits** | L | 中 | 先限一种 G-stage fault/单一 memslot 类型，定义重试/退出 ABI | [源补丁](https://patchwork.kernel.org/project/kvm/patch/20250618042424.330664-7-jthoughton@google.com/) · [证据](riscv-arm-x86-gap/07-kvm-iommu-virtualization.md#virt-05) |
| [ ] **VIRT-06：coherent 平台 `KVM_VFIO`** | L | 中 | 先只启用 coherent 平台；non-coherent DMA 另发 RFC | [KVM/VFIO 系列](https://patchwork.kernel.org/project/kvm/patch/20250611224604.313496-55-seanjc@google.com/) · [证据](riscv-arm-x86-gap/07-kvm-iommu-virtualization.md#virt-06) |
| [ ] **KVM-T05：dirty-log 关闭后恢复 huge leaf** | L | 高 | 先写 4K→PMD/PUD collapse 回归，再实现 ioctl 上下文的安全 coalesce/HFENCE | [arm eager-split 参考](https://patchwork.kernel.org/project/kvm/patch/20260629111820.1873540-3-leo.bras@arm.com/) · [证据](claude-4-8/kvm-riscv/analysis/mmu_stage2.md) |
| [ ] **KVM-T06：dirty-ring memstress 创建参数** | S | 高 | capability-gated 地在 VM 创建时启用 dirty ring，增强 full-ring/高并发覆盖 | [源补丁](https://patchwork.kernel.org/project/kvm/patch/20260629105950.1790259-2-leo.bras@arm.com/) · [证据](kvm-riscv/00-portability-overview.zh-CN.md) |
| [ ] **KVM-T07：local timer latency selftest** | M | 中 | 分别测 Sstc 与 hrtimer fallback，报告分布而非硬编码过紧阈值 | [x86 源测试](https://patchwork.kernel.org/project/kvm/patch/b54bdd9878213e06a410db415cc6aaa79000341b.1772732517.git.isaku.yamahata@intel.com/) · [证据](claude-4-8/kvm-riscv/analysis/timer_pv.md) |
| [ ] **RVV-T01：移植 `fp-stress`** | M | 中 | 在任何状态管理优化前，先覆盖 signal、ptrace、抢占、softirq 与多线程上下文切换 | [arm64 源补丁](https://lore.kernel.org/r/20220829154452.824870-5-broonie@kernel.org) · [证据](fpsimd/vector-test/fp-stress-patch-analysis.md) |
| [ ] **RVV-MEM：kernel Vector context 惰性分配** | L | 中 | 先量化 fork/idle task 内存，再设计可睡眠预分配或安全 fallback | [RVV v11 patch](https://lore.kernel.org/all/20240115055929.4736-11-andy.chiu@sifive.com/) · [证据](fpsimd/kilo/riscv-kernel-mode-vector-deep-analysis.md) |
| [ ] **IOMMU-T01：RISC-V 页表 KUnit** | M | 中 | 先覆盖 leaf level、NAPOT/superpage、权限、invalid entry 和 map/unmap rollback | [ARM KUnit 参考](https://lore.kernel.org/linux-arm-kernel/20251103123355.1769093-5-smostafa@google.com/) · [证据](riscv-contributions-explore/analysis/audit_mmu_memory.md) |
| [ ] **SCHED-01：SCHED_CLUSTER/SMT/HOTPLUG_SMT 接线** | M | 中 | 先证明 `arch_topology` 已提供正确 cluster/thread mask，再逐 capability 启用 | [静态扫描证据](claude-4-8/riscv-contrib-scan/analysis/kconfig_sched_mm_rest.md) |

### 已覆盖/不应另起 RISC-V port

以下是研究快照中的旧候选或通用系列，经 2026-07-13 的 v7.2-rc3 本地内核树抽检已有等价实现。后续只跟随通用修复，不再领取 RISC-V 专属移植：

- `kvm_binary_stats_test`、`irqfd_test`、`dirty_log_test` 已在 common 构建；`steal_time` 已进入 RISC-V 构建。
- SBI PMU 现有自测只使用规范保证存在的 cycles/instructions，“仅校验硬件支持事件”已不是缺口。
- G-stage 已覆盖 write-protect 后远端 HFENCE、memslot 边界、GPA 表示上限、替换 leaf 后 flush 和 fault unwind 引用释放。
- RVV ISA/signal/prctl/KVM/kernel-mode/preemptive Vector/context slab 已存在；ptrace 已有 `NT_RISCV_VECTOR` 与 `validate_v_ptrace`，coredump 通过 regset `core_note_type` 自动包含 Vector，不需要独立 `fill_vector_note()`。
- MSI teardown、per-CPU IRQ affinity、通用 devres/helper API 已合入；后续只能针对具体 RISC-V 驱动采用，不应再提交“移植框架”。
- directed yield、CPU hotplug IRQ、KVM/VFIO 引用解耦、MMIO 注册加速、syscore hook、guest_memfd 通用内部修复属于共享 core；通用补丁覆盖全树时不应制造 RISC-V 副本。
- 静态扫描中的 `PARAVIRT`、`GENERIC_IRQ_ENTRY`、`EXECMEM`、`VMAP_STACK`、`JUMP_LABEL`、`PERF_EVENTS`、`PTDUMP` 等多项信号是传递 select 或扫描口径造成的假阳，详见 [`riscv-contrib-scan`](claude-4-8/riscv-contrib-scan/README.md)。

### P3：长期、低置信或需维护者先确认

| 待办/方向 | 难度 | 置信 | 暂缓原因 | 源与证据 |
|---|---|---|---|---|
| [ ] **RVV-OPT：CPU 绑定/双向状态跟踪** | XL | 低 | 文档中的 10–30% 和具体 benchmark 数字缺少可复现实测；先完成 RVV-T01 和基线 profile | [ARM 延迟恢复](https://lore.kernel.org/all/1399548184-9534-2-git-send-email-ard.biesheuvel@linaro.org/) · [证据](fpsimd/kilo/gap-analysis-01-cpu-binding.md) |
| [ ] **RVV-FLUSH：Vector 状态刷新 API** | L | 低 | 需先证明当前 deferred restore 在迁移/signal/exec/ptrace 上存在可复现错误或浪费 | [原 RVV 系列](https://lore.kernel.org/all/20240115055929.4736-1-andy.chiu@sifive.com/) · [证据](fpsimd/kilo/gap-analysis-02-state-flush.md) |
| [ ] **RVV-STATS：Vector 保存/恢复统计 ABI** | M | 低 | sysfs ABI 与热路径开销未获维护者需求；优先临时 tracepoint/benchmark | [证据](fpsimd/kilo/gap-analysis-05-performance-monitoring.md) |
| [ ] **KASAN SW_TAGS / Ssnpm-Supm 路线** | XL | 低 | Ssnpm/Supm 不等于 MTE；tag ABI、shadow layout、入口/uaccess 安全均未证明 | [专题研究](riscv_arm_isa/cc/riscv_arm_ssnpm_mte_research.md) |
| [ ] **NMI 簇（AIA IPRIO pseudo-NMI）** | XL | 低 | 五个 capability 相互依赖，且当前 buddy hardlockup detector 已可用 | [静态扫描证据](claude-4-8/riscv-contrib-scan/README.md#4-top-候选分级按价值可行性) |
| [ ] **VIRT-08/09/10/11/13：IOMMU MSI、PRI/IOPF、SVA、nested HWPT、vIOMMU** | XL | 中 | 依赖 PCIe PASID/PRI、IOMMUFD、queue ABI、GSCID/VMID 与硬件验证，需逐层 RFC | [详细候选](riscv-arm-x86-gap/07-kvm-iommu-virtualization.md#virt-08) |
| [ ] **VIRT-12：AMO_HWAD DMA dirty tracking** | XL | 低 | 硬件/规范可用性与 KVM/IOMMU dirty-log 接口尚不稳定 | [源补丁](https://lore.kernel.org/linux-arm-kernel/20260629111820.1873540-8-leo.bras@arm.com/) · [证据](riscv-arm-x86-gap/07-kvm-iommu-virtualization.md#virt-12) |
| [ ] **VIRT-14：nested KVM/shadow G-stage** | XL | 低 | 架构状态/UAPI 和硬件扩展尚未稳定；不适合作为独立移植任务 | [arm64 测试参考](https://lore.kernel.org/linux-arm-kernel/20250512105251.577874-4-gankulkarni@os.amperecomputing.com/) · [证据](riscv-arm-x86-gap/07-kvm-iommu-virtualization.md#virt-14) |
| [ ] **VIRT-15：CoVE/private memory** | XL | 低 | 安全模型、firmware ABI、guest_memfd/memory attributes 均是硬前置 | [arm64 参考](https://patchwork.kernel.org/project/kvm/patch/20260513131757.116630-26-steven.price@arm.com/) · [证据](riscv-arm-x86-gap/07-kvm-iommu-virtualization.md#virt-15) |
| [ ] **CORE-05/09/11/15/18：高级 probes/BPF/stack/双宽原子链** | L–XL | 中 | 分别依赖 CORE-01/04/06/08/16 或 Zacas 设计；按依赖完成后再拆 | [完整依赖图](riscv-arm-x86-gap/05-core-abi-observability-hardening.md#3-能力链与实施依赖) |
| [ ] **MM-13、PLAT-08：linear alias 硬化/EFI recovery stack** | L–XL | 中 | early boot、kexec、异常恢复与多架构策略风险高 | [MM-13](riscv-arm-x86-gap/03-mmu-memory-tlb.md#mm-13) · [PLAT-08](riscv-arm-x86-gap/06-platform-acpi-numa-power-ras.md#plat-08) |
| [ ] **IRQ-02/03/05：IRQ/IPI/MSI 状态机通用化** | L–XL | 中 | 先完成 runtime-constant、AIA 生命周期和实测需求，再抽公共层 | [完整专题](riscv-arm-x86-gap/04-irq-smp-time.md) |
| [ ] **ISA-09：Ssdbltrp** | L | 中 | 已有人推进；Linux 只处理 S 态部分，M 态 `Smdbltrp` 属 OpenSBI | [证据](claude-4-8/riscv-isa-optgap/analysis/isa_priv_ras_qos.md) |
| [ ] **ISA-10：SM4 bulk / RVV memcpy-memset-memmove** | L | 低 | 使用场景细分；内核态 Vector 保存成本和短路径策略有争议 | [crypto](claude-4-8/riscv-isa-optgap/analysis/asm_crypto.md) · [string](claude-4-8/riscv-isa-optgap/analysis/asm_string.md) |
| [ ] **BENCH-01：RISC-V/ARM VM 生命周期基线** | M | 中 | 先实现可重复采集脚本；当前 11 阶段方案没有实测结果 | [方案](riscv_arm_isa/codex/v1/riscv-arm-virtualization-lifecycle-performance-plan.md) |
| [ ] **BENCH-02：SPEC2006 虚拟化折损率** | L | 低 | 许可、平台可比性和统计方法先于结论；现有分值是定性估计 | [方案](riscv_arm_isa/codex/v1/riscv-arm-spec2006-virtualization-performance-plan.md) |
| [ ] **OBS-01：RISC-V page-fault tracepoint** | S | 中 | 先确认 trace ABI 与地址泄露策略，覆盖 instruction/load/store fault，静态关闭零负担 | [arm64 源补丁](https://lore.kernel.org/linux-arm-kernel/61063f55e2c2df6db69cb63eac9d6653f38fbfbd.1747649899.git.namcao@linutronix.de/) · [证据](riscv-contributions-explore/analysis/audit_mmu_memory.md) |

### 未提升为主任务的完整索引

为避免顶层表重复 90 个候选卡片，以下原始编号仍保留为次级待办；其优先级、首补丁、依赖、维护者和源链接均在对应文件中。只有在主清单候选被占用或具备相关硬件时再领取。

| 领域 | 完整候选 | 说明 |
|---|---|---|
| MMU/Memory | [MM-01..16](riscv-arm-x86-gap/03-mmu-memory-tlb.md#2-16-项候选总表) | 16 项；主清单已提升 13 项，`MM-13` 在 P3 |
| IRQ/SMP/Time | [IRQ-01..10](riscv-arm-x86-gap/04-irq-smp-time.md) | 10 项；未单列的 IRQ-07 已在 linux-next，仅剩测试后续 |
| Core/ABI/Hardening | [CORE-01..18](riscv-arm-x86-gap/05-core-abi-observability-hardening.md#2-十八项总表) | 18 项；依赖链条目在 P3 合并展示 |
| Platform/ACPI/RAS | [PLAT-01..13](riscv-arm-x86-gap/06-platform-acpi-numa-power-ras.md) | 13 项；PLAT-03/04/05/07 属通用化/策略确认，PLAT-08 在 P3 |
| KVM/IOMMU | [VIRT-01..15](riscv-arm-x86-gap/07-kvm-iommu-virtualization.md) | 15 项；长期基础设施合并到 P3 |
| Genericization | [GEN-01..18](riscv-arm-x86-gap/08-genericization-opportunities.md) | 18 项；低风险项已提升，其余须先证明第二消费者和维护收益 |
| ARM 邮件候选 | [168 项总表](riscv-contributions-explore/analysis/curated_candidates.md) | 已天然共享的 generic patch 不重复作为 RISC-V 实现任务；按驱动/平台采用时回查 |
| KVM 邮件候选 | [70 项总表](kvm-riscv/00-portability-overview.zh-CN.md#全部候选) | T1 测试项优先；T2/T3 与 VIRT 主编号交叉去重 |

---

## 从候选到补丁的工作流

1. **选候选**：优先本页 `P1` / 原报告 `T1-near-term` / `greenfield` / 状态 `unclaimed` 的项。
2. **核查新鲜度**：在 mainline、linux-next、对应 maintainer tree、lore 搜索候选符号、补丁标题、作者与落点文件；确认没有更新版本或并行工作。
3. **缩小首版边界**：只做一个 hook / 一个 helper / 一个 Kconfig capability / 一个 selftest；把后续能力留到 v2 或第二个系列。
4. **确认 RISC-V 语义**：区分「通用层可直接复用」与「arm64/x86 模式可借鉴但必须按 RISC-V 语义重写」（内存模型、TLB、中断、虚拟化、固件 ABI 尤其如此）。
5. **补测试**：至少准备编译矩阵；涉及 ABI/KVM/MMU/Vector/DMA/IOMMU/perf 的候选需要对应 selftests、KUnit、kselftest 或 QEMU/硬件测试。
6. **准备投稿**：用 `scripts/get_maintainer.pl` 生成收件人并抄送 linux-riscv；说明原始参考系列、RISC-V 差异、验证环境、已排除的替代方案。

---

## 验证要求

| 类型 | 最低验证 |
|---|---|
| 纯文档 / 路线图 | 链接有效、引用路径存在、候选无重复或明显过期 |
| Kconfig / capability enablement | `defconfig`/`allnoconfig`/`allyesconfig` 或交叉构建；证明启用后无虚假能力暴露 |
| arch helper / asm 优化 | 功能 selftest、KUnit 或 lib 测试；`objdump` 检查关键指令；视情况覆盖 KASAN/KCSAN/UBSAN 构建 |
| MMU / TLB / DMA | QEMU + 至少一个硬件或平台说明；TLB/CMO 顺序证明；压力测试与错误注入 |
| KVM / IOMMU / AIA | kvm selftests、启动 guest、irq/timer/PMU 场景；涉及 VFIO/IOMMU 时需设备或仿真验证 |
| Vector / FPSIMD | 上下文切换压力、信号/ptrace/coredump、preempt/softirq/exception 场景，必要时补专门 kselftest |

---

## 重要边界

- 「可移植」通常指**机制可复用**，不代表可逐行复制 arm64/x86 代码。涉及内存模型、TLB、中断、虚拟化、固件 ABI 时须按 RISC-V 规范重新证明语义。
- 报告固定在某基线与时间窗；**2026-07 之后的上游状态必须重新确认**。
- 标记 `active RFC` / `在途` / `next` 的候选更适合参与评审、补测试或拆分系列，不适合另起炉灶。
- `P2` / `G4` / CoVE / nested KVM / IOMMU SVA/PASID / 机密 DMA 等长期方向，不应作为新贡献者的第一个补丁。
- `fpsimd/`、`riscv_arm_isa/` 中的性能方案与对标研究，投稿前要先转成具体内核落点、测试和维护者可评审的补丁边界；`riscv_arm_isa/` 的量化打分是定性结论、无实测数据。
- 优先级是工程调研结论，**不代表维护者已接受该方向**。

---

## 维护方式

后续新增探索目录或候选时，请同步更新本 README：

1. 在「目录地图」加一行，写明发现方法、规模、分级体系、成熟度和适合人群。
2. 在「推荐起点」只加入已被证据支持、可追溯到具体落点的候选，并标注 greenfield / active-RFC。
3. 若跨目录命中同一候选，补进「候选去重与交叉引用」。
4. 若某候选已合入、被替代或被证伪，保留历史说明并标注新状态，避免后来者重复投入。
