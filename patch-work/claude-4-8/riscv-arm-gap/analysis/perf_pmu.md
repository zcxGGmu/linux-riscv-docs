# perf-pmu 可移植性分析（linux-arm-kernel → RISC-V）

> 基线内核树：Linux v7.2.0-rc3（`/Users/zq/Desktop/patch-work/linux-riscv`）。
> riscv perf 现状（`_baseline_riscv.md` §10）：`drivers/perf/riscv_pmu_sbi.c`（+legacy/riscv_pmu.c）= SBI-PMU + **sscofpmf 计数器溢出采样** + SBI-PMU snapshot；`arch/riscv/kernel/perf_callchain.c` / `perf_regs.c`。**无 SPE（统计采样）对应；无硬件分支记录（BRBE）对应**（`riscv_pmu.c:313 has_branch_stack` 直接拒绝）。

## 摘要

- **系列总数：285**
- 四态计数（按系列主体判定）：**ALREADY 8 / PORTABLE 21 / PATTERN 3 / N-A 253**
  - 其中 253 条 N-A 里，**6 条含一个孤立的通用子补丁**（PORTABLE 片段，见「混合系列」小节，可单独 cherry-pick）。
- **关键纪律发现**：本桶最「显眼」的 perf-core 通用候选 **已在基线树落地**，勿误报为新可移植：
  - **§102 mediated vPMU** 通用底座（`perf_time_ctx`/`timeguest`/`handle_mediated_pmi`/`perf_create_mediated_pmu`）→ 已在 `include/linux/perf_event.h:1002/1050/1681/1934`。
  - **§110 `perf_event_attr::config4`** → 已在 `perf_event.h:549`（`PERF_ATTR_SIZE_VER9=144`）。
  - **§212/§222 非连续 AUX 页 + `PERF_PMU_CAP_AUX_PREFER_LARGE`** → 已在 `ring_buffer.c:685`、`perf_event.h:307`。
- N-A 主体为 ARM 专有硬件：CoreSight 硬件跟踪（~118 条）、厂商 system/uncore PMU 驱动（arm-cmn/arm-ni/arm_cspmu/arm_dsu/hisi/dwc_pcie/thunderx2/fujitsu/apple/…，~62 条）、SPE 统计采样（~21 条）、KVM arm64 PMUv3 虚拟化（~15 条）、SoC「PMU」= 电源管理单元（exynos/dove/allwinner，非 perf，~16 条）。

### 本类 Top 候选（按 riscv 价值排序）

| # | 系列 | 判定 | riscv 价值 |
|---|---|---|---|
| 1 | §229 perf: per-function metrics（交替采样周期 + 抖动）| PORTABLE(core) | 高——`kernel/events/core.c` 通用特性，**基线未合入**，riscv_pmu 溢出处理已周期正确，自动受益 |
| 2 | §281/§244/§277/§278 perf 工具通用系统调用表 + 构建 | PORTABLE(tools) | 高——多条出自 rivosinc(riscv)，直接改善 riscv perf 用户态 |
| 3 | §119 perf: `default_overflow_compatible` 通用标志 | PORTABLE(core) | 中高——`kernel/events/core.c` 通用标志，**基线未合入** |
| 4 | §167 perf: Rework event_init/group 校验 | PATTERN | 中——riscv_pmu 事件/组校验可采用同一硬化模式 |
| 5 | §283 arm_pmu: 计数器 enable 清理 | PATTERN | 中——add/start 中「不在 add() 里 disable」逻辑可映射到 riscv_pmu |
| 6 | §83/§86/§200/§33/§49/§53 perf 工具重构 | PORTABLE(tools) | 中——去 arch `__weak`/去全局 `perf_env`/python/scripting 重组，减少 riscv arch 胶水 |

---

## Top 可移植候选（深度，已 curl 全文 + Grep 核对落点）

### 1. §229 A mechanism for efficient support for per-function metrics — PORTABLE(core)
- **原补丁**：`A mechanism for efficient support for per-function metrics`（https://patchwork.kernel.org/project/linux-arm-kernel/patch/20250408171530.140858-2-mark.barnett@arm.com/）状态=new，v4，5 patches。
- **可移植点**：patch 2/5「Allow periodic events to alternate between two sample periods」、3/5「Allow adding fixed random jitter to the sampling period」= 纯 `kernel/events/core.c` + `perf_event_attr` 通用扩展；patch 1/5「Record sample last_period before updating」修正各 arch PMU 驱动（powerpc/x86）在 `*_set_period` 更新周期**之前**记录 `last_period` 的顺序。
- **riscv 落点**：通用特性经 `kernel/events/core.c` 对 riscv_pmu **自动生效**；无需 arch 改写。核对：`drivers/perf/riscv_pmu_sbi.c:1125` 已是 `perf_sample_data_init(&data,0,hw_evt->last_period)` **先于** `riscv_pmu_event_set_period()`（:1126），即 riscv 已具备 patch 1/5 要修的正确顺序，无回归风险。
- **基线核对**：Grep `kernel/events/core.c`+uapi 无 `alternate/jitter/alt_sample_period` 字段，uapi 最高 `config4`(VER9) → **该特性尚未合入基线**，为真实开放候选。
- **判定**：PORTABLE——通用 perf core 采样周期机制，架构无关。

### 2. §281/§244/§277/§278 perf 工具通用系统调用表与构建 — PORTABLE(tools)
- **原补丁**：`perf tools: Use generic syscall scripts for all archs`（.../20250108-perf_syscalltbl-v6-11-7543b5293098@rivosinc.com/）；`perf: Support multiple system call tables in the build`（.../20250319050741.269828-5-irogers@google.com/）；`[RFC] lib perf: Select syscall table at runtime`（.../20250114-perf_syscall_arch_runtime-v1-1-5b304e408e11@rivosinc.com/）；`perf tools: Expose quiet/verbose variables in Makefile.perf`（.../20250114-perf_make_test-v1-1-decc1c517b11@rivosinc.com/）。
- **可移植点**：`tools/perf/` 用户态构建/syscall 表框架泛化——把逐 arch 硬编码 syscall 表改为通用生成脚本 + 运行时选择，明确覆盖 arch=csky/arc/sh/sparc/**riscv**。
- **riscv 落点**：`tools/perf/arch/riscv/`（已存在 Build/util/Makefile）+ 通用 `tools/perf/util/`。多条补丁作者为 rivosinc，直接面向 riscv。
- **判定**：PORTABLE——纯用户态、架构无关、riscv 为显式受益方。

### 3. §119 perf: Introduce default_overflow_compatible flag — PORTABLE(core)
- **原补丁**：`tracing/wprobe: Fix to avoid infinite watchpoint exception on arm64`（.../176179482721.959775.9568162681903659824.stgit@devnote2/）patch 1/2「perf: Introduce default_overflow_compatible flag」。
- **可移植点**：patch 1/2 在 perf core 引入通用 `default_overflow_compatible` 标志（区分默认溢出处理器）；patch 2/2 才在 arm64 wprobe 消费。
- **riscv 落点**：`kernel/events/core.c` / `include/linux/perf_event.h`（通用），riscv 侧 hw_breakpoint/wprobe 可同样受益。基线 Grep 无 `default_overflow_compatible` → 未合入。
- **判定**：PORTABLE（core 部分）；arm64 wprobe 消费部分为 arch，riscv 需自身接线。

### 4. §167 perf: Rework event_init checks — PATTERN
- **原补丁**：`perf: Rework event_init checks`（.../925c34a4b7f0defc3582a9fcccb6af1c21279a86.1755096883.git.robin.murphy@arm.com/）19 patches，treewide 修各 PMU 驱动的组校验。
- **可移植点**：统一模式——「组校验漏算事件自身 + 采用标准写法避免 racy 访问 sibling 链表 + 删去与 core 冗余的检查」（curl patch 06/19 确认）。**非单点框架补丁**，每驱动各自修。
- **riscv 落点**：`drivers/perf/riscv_pmu.c:304 riscv_pmu_event_init`（及 add 绑定路径）可采用同一硬化模式。
- **判定**：PATTERN——机制/写法可复用，需在 riscv_pmu 侧照做。

### 5. §283 arm_pmu: Counter enabling clean-ups — PATTERN
- **原补丁**：`arm_pmu: Counter enabling clean-ups`（.../20250107-arm-pmu-cleanups-v1-v1-7-313951346a25@kernel.org/）7 patches。
- **可移植点**：patch 2/7「Don't disable counter in armpmu_add()」、3/7「Don't disable counter in armv8pmu_enable_event()」——精简 add/enable 路径里冗余的 disable 调用，属通用 PMU 状态机清理思想。
- **riscv 落点**：`drivers/perf/riscv_pmu.c:257 riscv_pmu_add` / `:240 riscv_pmu_start` / `riscv_pmu_sbi.c` start-stop 逻辑可对照精简。
- **判定**：PATTERN——arm_pmu 专属实现，但 add/enable 清理思想可映射 riscv_pmu。

### 混合系列（主体 N-A，含 1 个通用子补丁，PORTABLE 片段）
- **§18** `arm64: Add BRBE support for bpf_get_branch_snapshot()`（.../20260616155716.2631508-4-puranjay@kernel.org/）：patch 1/4「perf/core: Fix sched_task callbacks for CPU-wide branch stack events」、2/4「perf/core: Clear the whole branch entry」= 通用 `kernel/events/core.c`（PORTABLE）；3/4 arm64 BRBE = N-A。**riscv 无分支记录硬件**（`riscv_pmu.c:313`），core 修复对 riscv 价值低。
- **§36/§51/§54** `*acpi_mod_name*`：patch「kernel: param: initialize module_kset…」「driver core: platform: set mod_name…」= 通用 `kernel/params.c`/`drivers/base/platform.c`（PORTABLE）；coresight `pass THIS_MODULE` = N-A。
- **§92** `perf arm_spe: Extend operations`：patch 1/2「perf/uapi: Extend data source fields」= 通用 `uapi/linux/perf.h`（PORTABLE 片段）；其余 arm_spe 工具 = N-A。
- **§126** `genirq: Add support for percpu_devid IRQ affinity`：patch 01–04（irqdomain/ACPI-irq/of-irq/platform firmware-agnostic irq 检索）= 通用 irq 基础设施（PORTABLE 片段，宜归 irqchip 桶）；GIC/apple-aic 消费 = N-A。
- **§274** `Improve ABI documentation generation`：ABI/docs 构建工具改进（PORTABLE 片段，属 docs-tooling）；样本仅 coresight ABI + arm asymmetric-32bit，价值低。

---

## 全量判定表

### ALREADY（riscv 已具备等价能力 / 基线已合入 / riscv 原生补丁）

| 系列 | arch | 判定 | 依据（riscv 落点/基线） | web_url |
|---|---|---|---|---|
| §102 KVM: x86: mediated vPMUs（perf core 底座）| other | ALREADY | mediated vPMU 通用底座已在 `perf_event.h:1002/1050/1681/1934`、`core.c` | .../20251206001720.468579-6-seanjc@google.com/ |
| §110 perf: arm_spe Armv8.8（`config4`）| generic | ALREADY | `config4` 已在 `uapi/.../perf_event.h:549`（VER9）；arm_spe 消费 N-A | .../20251111-james-perf-feat_spe_eft-v10-1-…@linaro.org/ |
| §212 perf: 非连续 AUX 页默认 | generic | ALREADY | `PERF_PMU_CAP_AUX_PREFER_LARGE` 已在 `perf_event.h:307`、`ring_buffer.c:685` | .../20250508232642.148767-1-yabinc@google.com/ |
| §222 perf,coresight: 非连续 AUX 页 capability | generic | ALREADY | 同上（core 能力位已合入）；coresight 消费 N-A | .../20250421215818.3800081-2-yabinc@google.com/ |
| §115 riscv: SBI Supervisor Software Events | other | ALREADY | riscv 原生（`perf: RISC-V: add SSE event`）；`drivers/perf/riscv_pmu_sbi.c` | .../20251105082639.342973-6-cleger@rivosinc.com/ |
| §146 Add SBI v3.0 PMU enhancements | other | ALREADY | riscv 原生（`drivers/perf/riscv` SBI v3.0 + KVM）| .../20250909-pmu_event_info-v6-1-…@rivosinc.com/ |
| §159 drivers/perf: riscv: Remove redundant ternary | other | ALREADY | riscv 原生清理（riscv_pmu_sbi.c）| .../20250828122510.30843-1-liaoyuanhong@vivo.com/ |
| §169 perf: riscv: skip empty batches in counter start | other | ALREADY | riscv 原生（riscv_pmu_sbi 计数器启动）| .../20250804025110.11088-1-cuiyunhui@bytedance.com/ |

### PORTABLE（通用/架构无关，几乎直接适用 riscv）

| 系列 | arch | 层 | 可移植点 | riscv 落点 | web_url |
|---|---|---|---|---|---|
| §229 per-function metrics（交替周期+抖动）| generic | core | `kernel/events/core.c` 采样周期机制 | 经 core 自动生效；`riscv_pmu.c:202`/`riscv_pmu_sbi.c:1125` | .../20250408171530.140858-2-mark.barnett@arm.com/ |
| §119 perf: default_overflow_compatible flag | arm | core | 通用溢出处理器标志（patch 1/2）| `kernel/events/core.c`, `perf_event.h` | .../176179482721.959775.9568162681903659824.stgit@devnote2/ |
| §18 perf/core: 分支栈 sched_task/清理修复 | arm | core | patch 1–2/4 通用 branch-stack 修复（riscv 无分支HW，价值低）| `kernel/events/core.c` | .../20260616155716.2631508-4-puranjay@kernel.org/ |
| §281 perf tools: 全 arch 通用 syscall 脚本 | other | tools | 通用 syscall 表生成（含 riscv）| `tools/perf/arch/riscv/`, `tools/perf/util/` | .../20250108-perf_syscalltbl-v6-11-…@rivosinc.com/ |
| §244 perf: 构建支持多 syscall 表 | generic | tools | 多 arch syscall 表构建 | `tools/perf/` | .../20250319050741.269828-5-irogers@google.com/ |
| §277 lib perf: 运行时选择 syscall 表 | generic | tools | 运行时 syscall 表（riscv 作者）| `tools/lib/perf/`, `tools/perf/arch/riscv/` | .../20250114-perf_syscall_arch_runtime-v1-1-…@rivosinc.com/ |
| §278 perf tools: Makefile quiet/verbose | generic | tools | 构建变量暴露（riscv 作者）| `tools/perf/Makefile.perf` | .../20250114-perf_make_test-v1-1-…@rivosinc.com/ |
| §33 perf python: Modernize Python API | other | tools | 通用 perf python API | `tools/perf/util/python.c` | .../20260522220435.2378363-9-irogers@google.com/ |
| §49 perf: Reorganize scripting support | other | tools | 通用 perf 脚本框架重组 | `tools/perf/util/` | .../20260428071903.1886173-9-irogers@google.com/ |
| §53 perf inject: itrace branch stack 等（59 补丁）| other | tools | 通用 perf 工具重构 | `tools/perf/` | .../20260425224951.174663-10-irogers@google.com/ |
| §83 perf regs: bug fix + 去 __weak arch 函数 | generic | tools | 去 arch `__weak`，UAPI 相对路径 | `tools/perf/util/`, `tools/perf/arch/riscv/util/` | .../20260203024356.444942-2-dapeng1.mi@linux.intel.com/ |
| §86 perf regs: 去 arch __weak 函数 | generic | tools | 同上（v2）| `tools/perf/util/` | .../20260127070259.2720468-2-dapeng1.mi@linux.intel.com/ |
| §200 perf: Remove global perf_env | generic | tools | 通用去全局态重构 | `tools/perf/util/env.c` | .../20250527064153.149939-6-irogers@google.com/ |
| §45 perf tool: iostat 多平台 | other | tools | iostat 框架泛化为多平台 | `tools/perf/util/iostat.c` | .../20260507063737.3542950-3-wangyushan12@huawei.com/ |
| §87 perf tool: iostat 多平台（早期版）| other | tools | 同上 | `tools/perf/util/iostat.c` | .../20260126123514.3238425-3-wangyushan12@huawei.com/ |
| §73 bitmap: cleanup bitmaps printing | other | lib | `lib/` 通用位图打印清理 | `lib/`（架构无关）| .../20260303200842.124996-2-ynorov@nvidia.com/ |
| §97 drivers: perf: use bitmap_empty() | generic | drivers | 通用 helper 用法清理（跨 drivers/perf）| `drivers/perf/`（含 riscv）| .../20251216012004.341288-1-yury.norov@gmail.com/ |
| §118 tools/perf: Fix spelling typo | generic | tools | 文档/拼写 | `tools/perf/` | .../20251031025810.1939-1-chuguangqing@inspur.com/ |
| §187 perf test: sh→bash | generic | tools | 测试脚本 shebang | `tools/perf/tests/` | .../20250623-james-perf-bash-tests-v1-1-…@linaro.org/ |
| §182 watchdog/perf: 提供调周期函数 | arm | kernel | patch 1/2 通用 `kernel/watchdog_perf.c`（riscv 暂无 perf-hardlockup 消费）| `kernel/watchdog_perf.c` | .../20250701110214.27242-2-yangyicong@huawei.com/ |
| §224 perf: 编译测试默认不启用 | generic | drivers | `drivers/perf/Kconfig` 默认值（通用）| `drivers/perf/Kconfig` | .../20250417074650.81561-1-krzysztof.kozlowski@linaro.org/ |

### PATTERN（arch 专属，机制可在 riscv_pmu 重写）

| 系列 | arch | 可移植点 | riscv 落点 | web_url |
|---|---|---|---|---|
| §167 perf: Rework event_init checks | generic | PMU 组校验硬化模式（漏算自身/racy sibling/去冗余）| `drivers/perf/riscv_pmu.c:304` event_init | .../925c34a4b7f0defc3582a9fcccb6af1c21279a86.1755096883.git.robin.murphy@arm.com/ |
| §283 arm_pmu: Counter enabling clean-ups | arm | add/enable 路径去冗余 disable | `drivers/perf/riscv_pmu.c:240/257` | .../20250107-arm-pmu-cleanups-v1-v1-7-313951346a25@kernel.org/ |
| §172 arm_pmuv3: UBSAN 负 hw.idx 防御 | arm | 计数器 idx 负值防御性检查 | `drivers/perf/riscv_pmu_sbi.c` 计数器 idx | .../20250723104359.364547-5-ysk@kzalloc.com/ |

### N-A（依赖 ARM 专有硬件/ISA，无 riscv 对应；同质合并成组，覆盖全部剩余系列）

| 组（ARM 专有硬件/ISA）| 数量 | 代表系列（行号）| 判定依据 |
|---|---|---|---|
| **CoreSight 硬件跟踪**（ETM/ETB/ETF/ETR/TMC/TRBE/CTI/TPDM/TPDA/STM/CATU/funnel/replicator/tnoc/ctcu + cs-etm 工具 + coresight docs）| ~118 | §1,6,7,10,13,14,15,17,19,28,30,31,35,37,39,40,42,43,44,46,52,57,58,60,61,62,63,65,68,69,70,71,72,74,75,76,78,79,80,89,90,91,95,103,104,107,108,109,113,114,125,131,134,135,139,142,143,145,149,152,153,155,156,163,166,168,170,171,173,176,178,179,183,186,191,194,196,198,199,201,203,204,205,207,208,209,210,214,215,216,217,218,219,220,233,234,236,239,240,241,247,250,251,252,253,259,260,266,267,268,273,276,279,280,285 | ARM CoreSight 硬件跟踪子系统，riscv 无对应硬件（riscv 用 SBI/自研 trace，不在此列）|
| **厂商 system/uncore PMU 驱动**（arm-cmn/arm-ni/arm_cspmu/arm_dsu/hisi/dwc_pcie/thunderx2/fujitsu/apple_m1/amlogic/imx/meson/nvidia_t410/cxlpmu）| ~62 | §2,3,11,12,20,29,38,41,50,55,66,67,77,82,85,98,105,106,112,116,122,124,127,132,136,137,140,147,157,158,164,165,175,177,180,184,190,192,193,195,202,206,211,213,223,225,226,227,231,232,235,237,238,245,248,255,258,261,262,263,269,275 | 特定 SoC/互连/uncore 硬件 PMU，寄存器/拓扑专属；riscv 需各自厂商驱动 |
| **SPE 统计采样**（arm_spe 驱动 + perf arm-spe 工具 + KVM SPE）| ~21 | §9,59,64,81,88,96,101,111,123,128,129,141,144,148,181,185,221,230,256,257,282 | ARM SPE 统计采样硬件；riscv 仅 sscofpmf 计数器溢出采样，无统计采样器 |
| **KVM arm64 PMUv3 虚拟化**（EL2/partitioned/Apple PMUv3）| ~15 | §4,8,16,32,34,188,189,228,242,243,249,254,264,270,272 | arm64 EL2/PMUv3 虚拟化 ABI；riscv KVM PMU 为独立 SBI 实现 |
| **SoC「PMU」= 电源管理单元（非 perf）**（exynos/dove/allwinner phy/s3c-wdt/scmi-perf）| ~16 | §5,22,23,25,27,84,94,121,130,133,150,151,174,197,246,284 | 关键词撞名——实为电源/时钟管理单元或 SCMI 性能域，与 perf PMU 无关 |
| **arm_pmu CPU-PMU 杂项（非 pattern）**（CPU-ID 数据/寄存器专属/构建/头文件）| ~7 | §26,47,56,117,120,138,271 | arm_pmuv3 CPU-ID 表、PMCCNTR_EL0/SMT 寄存器、arm 构建/头依赖，无复用价值 |
| **arm64 perf 头/syscall/build/arch-callchain** | ~5 | §21,48,99,162,265 | arm64 专属 syscall 表符号链接、ESR 宏、device-mem callchain、编译修复 |
| **arm64 hw_breakpoint/watchpoint/ptrace** | ~3 | §24,100,161 | arm64 调试寄存器 BAS/断点长度校验，riscv 触发/调试寄存器不同 |
| **perf test x86 专属** | 1 | §160 | x86 topdown 测试构建修复 |
| **混合系列（主体 N-A，含 PORTABLE 片段，已在上文列出）** | 6 | §18,36,51,54,92,126,274 | 主体依赖 ARM 硬件；通用子补丁另计 |

> N-A 合计 253（含混合 6）。以上行号并集 + ALREADY(8)/PORTABLE(21)/PATTERN(3) 覆盖输入全部 285 条系列。

---

## 结论

RISC-V perf/PMU 子系统在基线树中已相当成熟：SBI-PMU + sscofpmf 溢出采样 + snapshot + callchain/regs 齐备，且**本桶中最显眼的 perf-core 通用增强（mediated vPMU、config4、非连续 AUX 页）均已随最新内核合入**。真正开放的可移植价值集中在两处：(1) **perf-core 通用采样机制**（§229 交替周期+抖动、§119 通用溢出标志）——架构无关、经 `kernel/events/core.c` 自动惠及 riscv_pmu；(2) **perf 用户态工具泛化**（§281/244/277/278 通用 syscall 表与构建，多出自 riscv 厂商）。arch 层可借鉴的模式仅少数 arm_pmu 清理/校验硬化（§167/283/172）。其余 ~253 条系列绑定 ARM 专有硬件（CoreSight/SPE/厂商 uncore PMU/KVM PMUv3）或与 perf 无关（SoC 电源「PMU」），对 riscv 无直接可移植价值。
