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
| 通用 helper 下沉 | `riscv-arm-x86-gap` **GEN-02/03/06/09/13** | 先做行为不变的 generic helper，再迁移 RISC-V | P0/G2，机械且低风险 |
| 驱动 devres/机械迁移一批 | `riscv-contributions-explore` P0「低」难度项 | 如 `devm_clk_bulk_get_optional_enable`、`sg_nents_for_dma` 等 | 大量「通用代码已覆盖 RISC-V」的低风险清理 |

### 4.2 中期高价值：多为 active-RFC（接力/评审姿势）

价值高但通常已有活跃上游系列，**宜复现评审意见、补测试、补待办子块，而非平行重写**：

- **可观测性/加固**：reliable stacktrace → livepatch（`riscv-arm-x86-gap` CORE-01，active RFC）；`static_call` 后端（CORE-03）；`Sdtrig` 硬件断点（CORE-02 + `claude-4-8/riscv-isa-optgap`，active RFC）；BPF `arch_bpf_stack_walk`/exceptions（CORE-06/07/08）；KCSAN/KASAN SW_TAGS（CORE-12；`riscv_arm_isa/` 指向基于 Ssnpm/Supm 的软件标签）。
- **MMU/DMA**：批量非一致 DMA 同步（`riscv-arm-x86-gap` MM-02 = `riscv-contributions-explore` #9，P0）；`pte_needs_flush()`/`ptep_try_set()`/范围 TLB 批处理（MM-06/07/11）。
- **ISA 特性**：`Ssqosid`/resctrl（`claude-4-8/riscv-isa-optgap`，推翻旧「无硬件」判断，active RFC Fustini）；`Ssctr/Smctr` 分支记录、计数器委派（active RFC Rivos）。
- **KVM/虚拟化**：G-stage 脱锁销毁与可调度化（`kvm-riscv` + `riscv-arm-x86-gap` VIRT-02）；`KVM_PRE_FAULT_MEMORY`（VIRT-04）；G-stage/IOMMU ptdump（VIRT-01）；coherent 平台 `KVM_VFIO`（VIRT-06）；大量 KVM selftests 迁移（`kvm-riscv` T1）。

### 4.3 专题研究：先转成补丁边界再动手

`fpsimd/` 与 `riscv_arm_isa/` 偏研究，投稿前须转成具体落点与测试：

- **RVV 内核态**（`fpsimd/kilo/`）：CPU 绑定优化（估 10–30%，列为最高优先）、状态刷新、ptrace regset、coredump note、perf 监控；可复用 `kernel_vector_begin/end()`、`TIF_RISCV_V_DEFER_RESTORE`、`CONFIG_RISCV_ISA_V_PREEMPTIVE`；可移植 ARM64 `fp-stress` kselftest。**任何优化都必须先有压力测试与回归证据**（抢占/异常/信号/ptrace/KVM world switch）。
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

## 从候选到补丁的工作流

1. **选候选**：优先 `P0` / `T1-near-term` / `greenfield` / 状态 `unclaimed` 的项。
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
