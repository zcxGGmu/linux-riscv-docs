# PMU 虚拟化 可移植性分析

> 类别：Tier B — PMU（`x86/kvm/pmu.c`、`arm64/kvm/pmu-emul.c` → riscv `arch/riscv/kvm/vcpu_pmu.c`）
> 判定依据：本地内核树 `/Users/zq/Desktop/patch-work/linux-riscv`（`vcpu_pmu.c` 934 行、`vcpu_sbi_pmu.c` 98 行、`asm/kvm_vcpu_pmu.h`）+ 四条候选 mbox 全文核对。

## 摘要

- **系列总数：34**
- **四态计数**：ALREADY 0 / PORTABLE 0 / **PATTERN 8** / **N-A 26**
- riscv PMU 现状（判定基线）：`vcpu_pmu.c` 已是「**host-perf-event 后端的仿真型 vPMU**」——每个 guest 计数器由 `perf_event_create_kernel_counter()` 后端支撑，`kvm_riscv_pmu_overflow()` 处理溢出并注入中断（需 host Sscofpmf），含 snapshot 共享区（`snapshot_addr`/`sdata`）、SBI-PMU 全套 ctr_start/stop/cfg_match/read。
- **两处已核实的空缺**（grep 全空）：
  1. **无 PMU event filter**（对照 x86 `kvm_x86_pmu_event_filter` / `KVM_SET_PMU_EVENT_FILTER`）——`grep -rn "event_filter" arch/riscv/kvm/` 无匹配。
  2. **无 HW 计数器直通 / mediated / 计数器委托**（`grep -rni "passthrough|mediated|deleg"` 无匹配）——当前 100% 靠 host perf 仿真。

### 本类 Top 候选（按 riscv 价值排序）

1. **Mediated vPMU（x86，series 19 v6 / 3 v4）** — PATTERN — 直通式 vPMU 大方向；含**架构无关的 perf 核心**基础设施（`exclude_guest`/mediated-PMU API），对应 RISC-V「计数器委托 Counter Delegation（Smcdeleg/Ssccfg）」路线。
2. **PMU event filter（x86，series 25）** — PATTERN — 直接补 riscv 已核实的空缺；落点 `vcpu_pmu.c`。
3. **ARM64 PMU Partitioning（arm，series 27）** — PATTERN — host/guest 硬件计数器分区，arm 版「计数器直通」，为 riscv 委托设计提供蓝本。
4. **SVM PMC virtualization（x86，series 16）** — PATTERN — 通用「HW-virtualized PMU 的 perf capability」标志可复用。
5. **Multiple host PMUs（arm，series 33）** — PATTERN — 异构（big.LITTLE 式）host-PMU 绑定；riscv vcpu_pmu 同样基于 host perf event，异构 SoC 同题。
6. **Mediated vPMU PerfMon v5（x86，series 34）** — PATTERN — 计数器位图/访问器重构，并入 #1 主题。

---

## Top 可移植候选（深度）

### 1. Mediated vPMU for x86（series 19 v6，44 patches；series 3 v4，38 patches）
- **原补丁**：`KVM: x86: Add support for mediated vPMUs`（https://patchwork.kernel.org/project/kvm/patch/20251206001720.468579-6-seanjc@google.com/）状态=new；早期版 `Mediated vPMU 4.0 for x86`（https://patchwork.kernel.org/project/kvm/patch/20250324173121.1275209-4-mizhang@google.com/）。
- **可移植点**：把 vPMU 从「host perf 仿真」升级为「把物理计数器**直通**给 guest、VM-exit/entry 时上下文切换 PMU 状态」。mbox 核对（patch 05/44）确认前若干补丁改的是 **`kernel/events/core.c` + `include/linux/perf_event.h`**（`perf: Add APIs to create/release mediated guest vPMUs`、`perf: Add generic exclude_guest support`、`EVENT_GUEST` 标志、`perf ctx time` 清理）——**这部分架构无关**，是任何架构做直通 vPMU 的公共前置。
- **riscv 落点**：(a) 消费 perf 核心新 API 的直通模型重写在 `arch/riscv/kvm/vcpu_pmu.c`（新增「委托模式」路径，与现仿真路径并存）；(b) 依赖 RISC-V 计数器委托扩展（Smcdeleg/Ssccfg + Smcsrind），host 侧 `drivers/perf/riscv_pmu*.c` 需生成/释放 mediated PMU。经 grep 证实 riscv KVM 当前**无任何 mediated/deleg 代码**。
- **判定**：PATTERN — 通用 perf-core 前置属架构无关（近 PORTABLE），但 KVM 侧直通逻辑必须按 RISC-V 委托 ISA 重写。

### 2. PMU event filter（series 25，2 patches；关联 series 22）
- **原补丁**：`KVM: x86/pmu: Fix a fixed PMC event filter bypass bug`（https://patchwork.kernel.org/project/kvm/patch/20260603231905.1738487-3-seanjc@google.com/）状态=new。mbox 核对：patch 1/2 修 `FIXED_CTR_CTRL` 重编程时按硬件值过滤，patch 2/2 是 `tools/testing/selftests/kvm/x86/pmu_event_filter_test.c` 回归测试。
- **可移植点**：event filter **机制**本身——允许 userspace 通过 ioctl（x86 `KVM_SET_PMU_EVENT_FILTER`）设定 guest 可编程的事件 allow/deny 列表；guest 请求某事件时在 KVM 侧校验。
- **riscv 落点**：`arch/riscv/kvm/vcpu_pmu.c` 的 `kvm_riscv_vcpu_pmu_ctr_cfg_match()`（当前直接把 SBI 事件转 perf config 无过滤）——新增 per-VM filter 位图 + 新 KVM_CAP/ioctl；selftest 新增 riscv 版 `pmu_event_filter`。基线与 grep 双重确认 riscv **无 event filter**（`_baseline_riscv.md` 缺口 6、`grep event_filter` 空）。
- **判定**：PATTERN — 明确空缺，机制与 UAPI 形态清晰，riscv 侧独立重写即可，不依赖 x86 硬件。

### 3. ARM64 PMU Partitioning（series 27，21 patches）
- **原补丁**：`ARM64 PMU Partitioning`（https://patchwork.kernel.org/project/kvm/patch/20260612192909.1153907-3-coltonlewis@google.com/）状态=new。mbox 核对（patch 02/21）：改 `arch/arm64/include/asm/arm_pmuv3.h`、`drivers/perf/arm_pmuv3.c`、`include/kvm/arm_pmu.h`——即「perf 驱动泛化 + KVM 消费」两段式。
- **可移植点**：用 `MDCR_EL2.HPMN` 把物理计数器**分区**为 host 段与 guest 直通段，guest 直接读写自己那段计数器（低开销直通）。这是 arm 版「计数器直通」，与 #1 的 x86 mediated vPMU 思路互为印证。
- **riscv 落点**：概念落到 `arch/riscv/kvm/vcpu_pmu.c` + host 侧 `drivers/perf/riscv_pmu*.c`；RISC-V 对应机制是**计数器委托**（Smcdeleg 把一部分 hpmcounter 委托给 VS 模式）。为 riscv 直通/分区设计提供最直接蓝本。
- **判定**：PATTERN — 硬件寄存器（HPMN）arm 专属，但「分区 + 直通子集」机制强可复用。

### 4. SVM PMC virtualization（series 16，7 patches, RFC）
- **原补丁**：`KVM: SVM: Support for PMC virtualization`（https://patchwork.kernel.org/project/kvm/patch/c056b4c5abc7b0ffa7a4579aa6503fc99fa51fc1.1762960531.git.sandipan.das@amd.com/）状态=new。sample 显示 patch 1/7 `perf: Add a capability for hardware virtualized PMUs`（通用 perf），2/7 起为 `x86/cpufeatures` + VMCB（AMD 硬件，mbox 确认 patch 2/7 改 `arch/x86/include/asm/cpufeatures.h`）。
- **可移植点**：仅 patch 1/7 的**通用 perf capability 标志**（`PERF_PMU_CAP_VIRTUALIZED_VPMU`）——标记某 host PMU 支持硬件直通，供 KVM 查询。
- **riscv 落点**：该 perf 标志将来可由 `drivers/perf/riscv_pmu*.c` 在支持委托的平台上置位，`vcpu_pmu.c` 据此启用直通路径。SVM/VMCB 实现本身 N-A。
- **判定**：PATTERN（通用 capability 部分可复用；AMD SVM 实现 N-A）。

### 5. KVM: arm64: PMU: Use multiple host PMUs（series 33，7 patches）
- **原补丁**：`KVM: arm64: PMU: Use multiple host PMUs`（https://patchwork.kernel.org/project/kvm/patch/20260706-hybrid-v8-6-de459617b59d@rsg.ci.i.u-tokyo.ac.jp/）状态=new。sample：RCU 保护 PMU 列表、按 target CPU 探测 armpmu、`FIXED_COUNTERS_ONLY` 仿真、pPMU 未覆盖全部 CPU 时禁用 vPMU。
- **可移植点**：异构系统（大小核）上把 vCPU 的 vPMU **绑定到具体 host PMU**，并在覆盖不全时安全降级——纯软件后端管理逻辑。
- **riscv 落点**：`arch/riscv/kvm/vcpu_pmu.c`。riscv vPMU 同样基于 host perf event（`perf_event_create_kernel_counter`），异构 RISC-V SoC 面临同样「多 host PMU / 计数器集不一致」问题，此绑定与降级逻辑可借鉴。
- **判定**：PATTERN — 无 arm 硬件耦合，属可复用的 host-PMU 后端管理模式。

### 6. Mediated vPMU PerfMon v5（series 34，15 patches）
- **原补丁**：`KVM: x86/pmu: Add mediated vPMU PerfMon v5 support`（https://patchwork.kernel.org/project/kvm/patch/20260707183405.15571-5-zide.chen@intel.com/）状态=new。
- **可移植点**：`all_valid_pmc_idx→mask` 位图化、PMC bitmap accessor helpers、`kvm_host_pmu` 抽象等**结构性重构**——直通 vPMU 的通用数据模型。PerfMon v5/PERF_METRICS 语义 x86 专属。
- **riscv 落点**：并入 #1 主题；`vcpu_pmu.c` 若引入直通模式，可参考其计数器位图/访问器组织。
- **判定**：PATTERN（重构模式可复用；PerfMon v5 硬件语义 N-A）。

---

## 全量判定表

| # | 系列 | 判定 | 可移植点(若有) | riscv落点(若有) | web_url |
|---|---|---|---|---|---|
| 1 | x86/pmu: Fixes and improvements (kvm-unit-tests,18) | N-A | x86 PMU 单测重构/精修，语义 x86 专属 | — | https://patchwork.kernel.org/project/kvm/patch/20250215013636.1214612-4-seanjc@google.com/ |
| 2 | Enable x86 mediated vPMU (QEMU target/i386,3) | N-A | QEMU 用户态 x86；`kvm_arch_pre_create_vcpu` 属 QEMU 内部钩子 | — | https://patchwork.kernel.org/project/kvm/patch/20250324123712.34096-2-dapeng1.mi@linux.intel.com/ |
| 3 | Mediated vPMU 4.0 for x86 (38) | **PATTERN** | 通用 perf-core `exclude_guest`/mediated API + 直通 vPMU 模型 | `vcpu_pmu.c` + `drivers/perf/riscv_pmu*`（Smcdeleg 委托） | https://patchwork.kernel.org/project/kvm/patch/20250324173121.1275209-4-mizhang@google.com/ |
| 4 | x86/pmu_pebs: PMI_VECTOR 初始化 (1) | N-A | x86 PEBS 中断向量 | — | https://patchwork.kernel.org/project/kvm/patch/20250424052201.7194-1-dapeng1.mi@linux.intel.com/ |
| 5 | context_tracking,x86: Defer some IPIs (25) | N-A | RCU/objtool/context_tracking 内核底层，非 KVM PMU | — | https://patchwork.kernel.org/project/kvm/patch/20250429113242.998312-24-vschneid@redhat.com/ |
| 6 | arm64: support EL2 (kvm-unit-tests,9) | N-A | arm64 EL2/timer 引导，KUT 专属 | — | https://patchwork.kernel.org/project/kvm/patch/20250529135557.2439500-9-joey.gouly@arm.com/ |
| 7 | Fix pmu test errors on SRF/CWF (kvm-unit-tests,5) | N-A | Intel 平台 overcount 修正 | — | https://patchwork.kernel.org/project/kvm/patch/20250712174915.196103-4-dapeng1.mi@linux.intel.com/ |
| 8 | x86: HPET counter read micro benchmark (1) | N-A | x86 HPET 基准 | — | https://patchwork.kernel.org/project/kvm/patch/20250714145055.1487738-1-imammedo@redhat.com/ |
| 9 | Fix PMU kselftests errors on GNR/SRF/CWF (5) | N-A | x86 arch-events + event_filter 测试放宽（x86 语义）；riscv 应另建 pmu selftests | (借鉴) `selftests/kvm/riscv` | https://patchwork.kernel.org/project/kvm/patch/20250718001905.196989-2-dapeng1.mi@linux.intel.com/ |
| 10 | x86: add HPET counter tests (kvm-unit-tests,5) | N-A | x86 HPET + APIC id_map | — | https://patchwork.kernel.org/project/kvm/patch/20250725095429.1691734-2-imammedo@redhat.com/ |
| 11 | KVM: x86: Fastpath cleanups and PMU prep work (18) | N-A | x86 VM-exit fastpath（WRMSR/IPI/TSC_DEADLINE），riscv 退出模型不同 | — | https://patchwork.kernel.org/project/kvm/patch/20250805190526.1453366-19-seanjc@google.com/ |
| 12 | KVM: VMX: immediate form of MSR instructions (6) | N-A | VMX + 新 x86 ISA（MSR 立即数形式） | — | https://patchwork.kernel.org/project/kvm/patch/20250805202224.1475590-5-seanjc@google.com/ |
| 13 | Fix pmu test errors on GNR/SRF/CWF (kvm-unit-tests v3,8) | N-A | 同 #7（v3） | — | https://patchwork.kernel.org/project/kvm/patch/20250903064601.32131-4-dapeng1.mi@linux.intel.com/ |
| 14 | x86,fs/resctrl: AMD ABMC (33) | N-A | resctrl 带宽监控计数器，非 KVM vPMU；AMD 专属 | — | https://patchwork.kernel.org/project/kvm/patch/be18d59ef5458b22ef65fac59d9c2d06eda01d57.1757108044.git.babu.moger@amd.com/ |
| 15 | Fix warning in perf_get_x86_pmu_capability() (1) | N-A | x86 perf capability 告警修复 | — | https://patchwork.kernel.org/project/kvm/patch/20251010005239.146953-1-dapeng1.mi@linux.intel.com/ |
| 16 | KVM: SVM: Support for PMC virtualization (7) | **PATTERN** | 通用「HW-virtualized PMU perf capability」标志（patch 1/7） | `drivers/perf/riscv_pmu*` 置标志 + `vcpu_pmu.c` 直通路径；SVM/VMCB 部分 N-A | https://patchwork.kernel.org/project/kvm/patch/c056b4c5abc7b0ffa7a4579aa6503fc99fa51fc1.1762960531.git.sandipan.das@amd.com/ |
| 17 | x86/pmu: Fix test errors GNR/SRF/CWF (kvm-unit-tests v4,8) | N-A | 同 #7/#13（v4） | — | https://patchwork.kernel.org/project/kvm/patch/20251120233149.143657-4-seanjc@google.com/ |
| 18 | KVM: x86/pmu: Do not accidentally create BTS events (1) | N-A | x86 BTS 事件 | — | https://patchwork.kernel.org/project/kvm/patch/20251201142359.344741-1-sieberf@amazon.com/ |
| 19 | KVM: x86: Add support for mediated vPMUs (v6,44) | **PATTERN** | 通用 perf-core（`kernel/events/core.c`+`perf_event.h`，mbox 已核）+ 直通 vPMU 模型（最新完整版） | `vcpu_pmu.c` 新增委托模式 + `drivers/perf/riscv_pmu*`（Smcdeleg/Ssccfg） | https://patchwork.kernel.org/project/kvm/patch/20251206001720.468579-6-seanjc@google.com/ |
| 20 | target/i386: Misc PMU, PEBS, MSR fixes (QEMU,11) | N-A | QEMU 用户态 x86 | — | https://patchwork.kernel.org/project/kvm/patch/20260128231003.268981-11-zide.chen@intel.com/ |
| 21 | KVM: x86 selftests: Add Hygon CPUs support (4) | N-A | x86 厂商（Hygon/AMD-compat）检测 + event_filter 测试 | — | https://patchwork.kernel.org/project/kvm/patch/20260212103841.171459-2-zhiquan_li@163.com/ |
| 22 | annotate kvm_x86_pmu_event_filter __counted_by() (1) | N-A | 纯 x86 结构体加固；指向 event-filter 特性（riscv 缺口，见 #25） | — | https://patchwork.kernel.org/project/kvm/patch/20260212140556.3883030-2-clopez@suse.de/ |
| 23 | KVM: arm64: PMUVer 作无符号字段 (1) | N-A | arm64 ID_AA64DFR0 字段符号性修复，riscv ISA-ext 位图模型不同 | — | https://patchwork.kernel.org/project/kvm/patch/20260421164112.2448553-1-jingzhangos@google.com/ |
| 24 | perf/x86: Don't write PEBS_ENABLED on KVM transitions (9) | N-A | x86 PEBS host/guest 切换隔离 | — | https://patchwork.kernel.org/project/kvm/patch/20260508231353.406465-6-seanjc@google.com/ |
| 25 | KVM: x86/pmu: Fix a fixed PMC event filter bypass bug (2) | **PATTERN** | PMU event filter 机制（allow/deny 事件 + UAPI），riscv 已核实无 | `vcpu_pmu.c` `kvm_riscv_vcpu_pmu_ctr_cfg_match()` + 新 CAP/ioctl + selftest | https://patchwork.kernel.org/project/kvm/patch/20260603231905.1738487-3-seanjc@google.com/ |
| 26 | x86: fixes for running KUT as EFI on non-QEMU hosts (8) | N-A | x86 EFI 引导 / KUT 基础设施 | — | https://patchwork.kernel.org/project/kvm/patch/20260609140901.95727-4-gmazz@amazon.de/ |
| 27 | ARM64 PMU Partitioning (21) | **PATTERN** | HPMN 分区 + guest 直通计数器子集（perf 驱动泛化+KVM，mbox 已核） | `vcpu_pmu.c` + `drivers/perf/riscv_pmu*`（Smcdeleg 委托子集） | https://patchwork.kernel.org/project/kvm/patch/20260612192909.1153907-3-coltonlewis@google.com/ |
| 28 | x86 compilation fixes + arm64 PMU improvements (kvmtool,7) | N-A | kvmtool 用户态；arm64 PMU-after-GIC 初始化顺序 | — | https://patchwork.kernel.org/project/kvm/patch/20260618155001.226266-5-alexandru.elisei@arm.com/ |
| 29 | KVM: x86/pmu: wrmsrq() 替代 wrmsrl() (1) | N-A | x86 MSR API 清理 | — | https://patchwork.kernel.org/project/kvm/patch/20260625090057.4864-1-likexu@tencent.com/ |
| 30 | KVM: x86/pmu: Clean up vPMU comments (1) | N-A | x86 注释/空行清理 | — | https://patchwork.kernel.org/project/kvm/patch/20260625090155.6326-1-likexu@tencent.com/ |
| 31 | KVM: x86/pmu: Add hardware Topdown metrics support (8) | N-A | Intel PERF_METRICS / fixed counter 3，硬件专属 | — | https://patchwork.kernel.org/project/kvm/patch/20260629231938.15129-8-zide.chen@intel.com/ |
| 32 | KVM: arm64: Expose PMMIR_EL1.SLOTS to guests (3) | **PATTERN** | `KVM_ARM_VCPU_PMU_V3_STRICT` vCPU 特性——UAPI 协商的「严格直通 PMU」模式（PMMIR 寄存器 arm 专属） | `vcpu_pmu.c` + ONE_REG（strict 模式协商思路） | https://patchwork.kernel.org/project/kvm/patch/20260702190421.420992-2-congkai@amazon.com/ |
| 33 | KVM: arm64: PMU: Use multiple host PMUs (7) | **PATTERN** | 异构多 host-PMU 绑定 + 覆盖不全降级（纯软件后端管理） | `vcpu_pmu.c`（host perf event 后端选择） | https://patchwork.kernel.org/project/kvm/patch/20260706-hybrid-v8-6-de459617b59d@rsg.ci.i.u-tokyo.ac.jp/ |
| 34 | KVM: x86/pmu: mediated vPMU PerfMon v5 support (15) | **PATTERN** | PMC 位图化/访问器重构（直通 vPMU 数据模型）；PerfMon v5 语义 x86 专属 | `vcpu_pmu.c`（并入 #19 直通模型） | https://patchwork.kernel.org/project/kvm/patch/20260707183405.15571-5-zide.chen@intel.com/ |

---

## 关键结论

1. **本类无 PORTABLE / 无 ALREADY**：riscv 已有 SBI-PMU 仿真型 vPMU（含 overflow 注入 + snapshot），故没有「补基础功能」的 ALREADY；而 34 条中真正落在 `virt/kvm/*` 的通用改动为 0，故无纯 PORTABLE。**唯一接近 PORTABLE 的是 mediated vPMU 系列内的 perf-core 补丁**（`kernel/events/core.c`），属架构无关内核基础设施，但因整系列价值需 riscv 侧重写，整体判 PATTERN。

2. **三条战略主线**（均 PATTERN，同指向 RISC-V 计数器委托 Smcdeleg/Ssccfg）：
   - **直通/mediated vPMU**（#3/#19/#34，x86）+ **分区**（#27，arm）——把 vPMU 从「host perf 仿真」推进到「硬件计数器直通」，是 riscv vPMU 的下一阶段架构方向。
   - **event filter**（#25）——独立、低耦合、可立即补的空缺，落点明确（`cfg_match` + 新 CAP/ioctl）。
   - **host-PMU 后端管理**（#33，arm）——异构 SoC 上的 vPMU 绑定/降级，与 riscv 现有 host-perf-event 后端天然契合。

3. **26 条 N-A** 集中在：x86/arm 单元测试与 selftest 平台修正（overcount/HPET/EFI/Hygon）、QEMU/kvmtool 用户态、x86 PEBS/BTS/Topdown/MSR 硬件专属、AMD resctrl、arm ID 寄存器修复——均无 riscv 对应硬件或不属 KVM 内核 vPMU 逻辑。
