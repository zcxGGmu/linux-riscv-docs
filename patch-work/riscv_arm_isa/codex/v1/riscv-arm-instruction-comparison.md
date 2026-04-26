# RISC-V / ARM 指令集扩展对比与评估方案（面向规范与测试落地）

## 0. 文档目标与范围

本文针对以下 7 组主题给出两部分内容：

1. **硬件规范导向的功能特性对比**（RISC-V vs ARM）。
2. **性能评估方案设计**（仅针对 `Zifencei`、`Svnapot`、`Ssnpm`、`Sstc`、`H-扩展`；按要求不对 `Sstvala`、`Ssstrict` 给出性能评估）。

覆盖条目：

- `Zifencei / ARM ISB`
- `Sstvala / ARM FAR`
- `Svnapot`
- `Ssnpm`
- `Sstc / ARM Generic Timer`
- `H-扩展 / ARM FEAT_VHE`
- `Ssstrict`

---

## 1. 规范对比（硬件语义）

### 1.1 Zifencei / ARM ISB（指令同步屏障）

#### RISC-V（Zifencei）

- 核心指令：`FENCE.I`。
- 语义：保证**本 hart**后续取指可见该 hart 之前已可见的数据写入。
- 关键限制：`FENCE.I` 本身不保证多 hart 全局可见；跨核自修改代码需额外数据栅栏 + 远端同步机制。
- 生态语义：RISC-V 文档明确提到 Linux 用户态通常通过系统调用而非直接依赖 `FENCE.I` 维持 I-cache 一致性。

#### ARM（ISB）

- 核心指令：`ISB`。
- 语义：刷新流水线/重新取指，使后续指令在新的上下文状态下执行。
- 工程事实：在自修改代码/页表与属性更新场景，ARM 通常将 `ISB` 与 cache maintenance + `DSB` 组合使用。

#### 对比结论

- 两者都面向“后续取指看到更新后的执行上下文”。
- RISC-V 的 `FENCE.I` 语义更聚焦“本 hart 的 I/D 同步”；ARM 的 `ISB` 在实际软件栈中常作为屏障序列末端使用。
- 跨核代码发布上，二者都需要系统级配合，不是单指令即可覆盖全部一致性问题。

---

### 1.2 Sstvala / ARM FAR（故障地址寄存器）

#### RISC-V（Sstvala）

- `Sstvala` 为 profile 定义扩展：要求 `stval` 在对应异常场景写入“软件处理所需的值”（典型是 fault VA）。
- 在 RVA23 文档中，`Sstvala` 的目标是降低异常处理行为歧义，提升 OS/Hypervisor 可移植性。

#### ARM（FAR_ELx / AArch32 IFAR/DFAR 映射）

- `FAR_EL1/FAR_EL2/...` 用于承载同步异常相关 fault address。
- AArch64 与 AArch32 传统 IFAR/DFAR 之间存在架构映射关系。

#### 对比结论

- 两者都服务于 page fault / abort 路径的可诊断性。
- RISC-V 的 `Sstvala` 更体现为“Profile 层对实现行为的约束补齐”；ARM 的 FAR 语义长期稳定、软件依赖成熟。

---

### 1.3 Svnapot（NAPOT 页转换）

#### RISC-V（Svnapot）

- 作用：在 Sv39/Sv48/Sv57 框架中，通过 `pte.N=1` 表达 NAPOT 连续映射。
- 当前 ratified 文本中，`pte.N=1` 的可用编码是**受限且显式定义**的；保留编码必须触发页故障。
- 工程价值：减少页表项数量、提升 TLB 覆盖效率，降低大连续映射的页表管理开销。

#### ARM（Contiguous 映射提示 + 大页/块映射）

- ARM 侧常见做法是：
  - 使用块映射（block mappings）降低页表层级开销；
  - 在页表条目中使用 contiguous hint，提示硬件优化连续条目行为。

#### 对比结论

- 两者目标一致：扩大单条 TLB/页表描述的有效覆盖范围。
- RISC-V `Svnapot` 是“明确扩展语义”；ARM 更偏“既有页表机制 + 提示/块映射组合”。

---

### 1.4 Ssnpm（监管器级指针屏蔽）

#### RISC-V（Pointer Masking: Ssnpm/Smnpm/Smmpm）

- `Ssnpm`：由 S-mode 控制下一特权级（U/VU）地址高位屏蔽策略。
- 关键机制：`senvcfg`/`henvcfg` 等中的 `PMM` 字段控制 PMLEN。
- 规范值（RV64 常见）：`PMLEN=0/7/16`（由 PMM 编码选择）。
- 扩展本质：让 CPU 对高位 tag 执行“地址计算忽略”，为 HWASAN 类软件标记机制提供硬件基础。

#### ARM（TBI / MTE 关联）

- ARM TBI：地址翻译可忽略 top byte（常见于用户态 tagged pointers）。
- ARM MTE：在 TBI 之上引入分配标签与检查机制，具备更强硬件强制语义。

#### 对比结论

- `Ssnpm` 与 ARM TBI 在“高位地址忽略”这一层最接近；
- 若比较“内存标签检查完整方案”，ARM MTE 的硬件原生程度更高，RISC-V 生态则更依赖软件/运行时配套。

---

### 1.5 Sstc / ARM Generic Timer（定时器扩展）

#### RISC-V（Sstc）

- 新增 CSR：`stimecmp`（S 级）与 `vstimecmp`（VS 级）。
- 触发条件：`time >= stimecmp`（S）与 `(time + htimedelta) >= vstimecmp`（VS）。
- 价值：减少原先 S/VS 定时器依赖 M-mode 代理的开销，降低 trap/仿真路径成本。

#### ARM（Generic Timer）

- 体系寄存器：`CNTFRQ`, `CNTPCT`, `CNTP_CVAL`, `CNTV_CVAL` 等。
- 长期作为 Arm A-profile 定时基准设施，和虚拟化/中断栈耦合成熟。

#### 对比结论

- 二者都提供物理/虚拟计时基准与比较寄存器。
- `Sstc` 的核心收益是“把 S/VS 定时器路径从更高特权级代理中释放出来”；ARM Generic Timer 在软件生态成熟度上更领先。

---

### 1.6 H-扩展 / ARM FEAT_VHE（虚拟化）

#### RISC-V（H 扩展）

- 引入虚拟化模式位 `V` 与 `VS/VU` 运行语义。
- 支持两阶段地址转换（VS-stage + G-stage）。
- 定义了 VS 侧 CSR 视图（如 `vsstatus`, `vsatp`, `vstval` 等）。

#### ARM（FEAT_VHE）

- 目标：使 Host 内核在 EL2 运行时更接近“原生 EL1 体验”，减少陷入/切换开销。
- 与 ARM 既有 EL2/Stage-2 机制配合，优化 KVM Host 路径。

#### 对比结论

- 二者都在追求“降低虚拟化常见路径开销”。
- ARM VHE 的主线软件生态更成熟；RISC-V H 扩展在近几年发展迅速，接口与测试覆盖持续增强。

---

### 1.7 Ssstrict（严格执行）

#### RISC-V（Ssstrict）

- Profile 定义语义：标准/保留编码空间内，执行未实现 opcode 或访问未实现 CSR 必须触发非法指令异常（contained trap 到 S-mode 处理）。
- 同时强调：不规定自定义编码空间行为。

#### ARM 对应语义

- ARM 没有同名扩展；但在架构手册中对未分配/未定义编码有既定异常语义（同时历史上存在 `UNPREDICTABLE` 类行为描述）。

#### 对比结论

- `Ssstrict` 的价值是把实现差异压缩到 profile 可控范围，减少“静默容忍”导致的不确定性。
- 其重点是**行为确定性与生态一致性**，而非吞吐或时延优化。

---

## 2. 性能评估方案（排除 Sstvala / Ssstrict）

> 说明：ISA 合规测试和性能测试是两条线。前者回答“对不对”，后者回答“快不快”。
> 下述方案均先做合规门槛，再做性能量化。

### 2.1 统一前置（所有性能项共用）

#### 基线与控制变量

- 固件、内核配置、编译器版本固定。
- 关闭频率漂移与能耗策略干扰（固定 governor）。
- 绑核执行（`taskset`/cpuset），隔离背景负载。
- 每项最少 30 次重复，输出 P50/P95/P99 与置信区间。

#### 统一采样指标

- 时延：ns/us 级 wall-clock + 周期计数。
- 微架构：`perf stat`（TLB miss、cache miss、branch miss、instructions/cycles）。
- 虚拟化：VM-exit 次数、vCPU 运行占比、定时器注入延迟。

#### 合规门槛（先过门槛再跑性能）

- RISC-V：`riscv-arch-test + RISCOF`。
- 内核路径：Linux `kselftest` / `KVM selftests` / `kvm-unit-tests`。
- ARM 平台级：`Arm SystemReady ACS (sysarch-acs)`。

---

### 2.2 Zifencei / ISB 性能评估

#### 目标

量化“代码更新后可执行”的同步成本（JIT/热补丁/动态装载）。

#### 核心指标

- patch-to-run latency（写指令到首次正确执行的时延）。
- I-cache 相关 miss 与分支预测恢复成本。
- 多核发布时跨核同步尾延迟。

#### 推荐套件与实现

- 合规：`riscv-arch-test`（Zifencei 相关）、RISCOF。
- 内核自测承载：Linux `kselftest`（可新增/扩展 JIT microbench 用例）。
- 虚拟化场景：`kvm-unit-tests`（对 guest 内代码发布路径做 A/B）。

#### 实验设计

- 单核：`store -> fence/sync -> execute` 循环，统计均值与尾延迟。
- 多核：一个核发布代码，N 个核执行，测收敛时间。
- A/B：
  - RISC-V：仅 `FENCE.I` 与“含远端同步”的完整流程。
  - ARM：`ISB` 单独与 `cache maintenance + DSB + ISB` 完整序列。

---

### 2.3 Svnapot 性能评估

#### 目标

验证连续映射对 TLB 命中、页表遍历开销与应用吞吐的影响。

#### 核心指标

- `dTLB/iTLB` miss 率与 walk 周期。
- 页错误率、内核页表操作时间。
- 应用吞吐（内存带宽型、随机访存型）。

#### 推荐套件与实现

- Linux `kselftest/mm`：`hugepage-mmap`, `hugepage-shm`, `thuge-gen`, `transhuge-stress`, `split_huge_page_test`。
- KVM 路径：Linux `KVM selftests` + `kvm-unit-tests` MMU 类测试。
- 合规门槛：RISCOF/arch-test + 平台页表能力检查。

#### 实验设计

- 对照组：4KiB 基页映射。
- 实验组：启用 `Svnapot` 连续映射（或平台支持的等效大页策略）。
- 工作负载：
  - 顺序带宽（STREAM 类）
  - 随机访存（pointer-chasing）
  - Guest 内存密集型（虚拟化场景）

---

### 2.4 Ssnpm 性能评估

#### 目标

评估指针高位屏蔽对用户态访存、系统调用 ABI、标签化运行时开销的影响。

#### 核心指标

- 用户态 load/store 开销变化（PMLEN=0/7/16）。
- 带标签指针参与 syscall 的开销与失败路径成本。
- Sanitizer/标签检查场景下的吞吐下降比例。

#### 推荐套件与实现

- Linux `kselftest/riscv/abi/pointer_masking.c`（已覆盖 `PR_SET/GET_TAGGED_ADDR_CTRL`、fork/exec、sysctl、读写系统调用行为）。
- Linux `kselftest/riscv/hwprobe`（确认 `Supm` 等能力暴露）。
- ARM 侧对照：AArch64 Tagged Address ABI 文档与对应用户态行为测试基线。

#### 实验设计

- Case A：仅启用 pointer masking，不启用 tagged ABI。
- Case B：pointer masking + tagged ABI。
- Case C：结合 sanitizer（如 HWASAN 风格）工作负载。
- 输出：每 case 的 IPC、syscall/s、fault rate、P99 延迟。

---

### 2.5 Sstc / ARM Generic Timer 性能评估

#### 目标

量化定时器中断路径时延与抖动，验证虚拟化下定时器注入效率。

#### 核心指标

- 定时器 IRQ latency（P50/P99）。
- jitter（周期稳定性）。
- 虚拟化场景 VM-exit 相关开销（特别是 timer path）。

#### 推荐套件与实现

- Linux `KVM selftests`：`arch_timer`（已用于 arm64/riscv 定时器自测路径）。
- `kvm-unit-tests`：timer 相关单测。
- Linux `kselftest/timers` + `rt-tests` (`cyclictest`)：系统级时延/抖动度量。

#### 实验设计

- 裸机：周期 10us/100us/1ms 三档。
- 虚拟化：Host + 1/2/4 Guests，比较注入延迟退化。
- A/B：
  - RISC-V：无 `Sstc`（代理路径） vs 有 `Sstc`（直接 CSR 路径）。
  - ARM：普通 EL1 计时路径 vs VHE Host 场景。

---

### 2.6 H-扩展 / FEAT_VHE 性能评估

#### 目标

量化虚拟化核心路径的开销：切换、二阶段地址翻译、中断与 I/O。

#### 核心指标

- VM-entry/exit 开销。
- 二阶段翻译引入的 TLB/walk 额外成本。
- Guest 内核构建、网络、块 I/O 的相对性能。

#### 推荐套件与实现

- Linux `KVM selftests`（API 与路径级验证）。
- `kvm-unit-tests`（guest 视角功能与陷入行为）。
- Arm SystemReady `sysarch-acs`（BSA/SBSA 合规基线，确保平台架构能力一致）。
- 宏基准可选：内核编译、`iperf3`、`fio`、`hackbench`（用于最终业务相关性验证）。

#### 实验设计

- 裸机 vs Guest 对照（同核数、同内存、同频率策略）。
- 单 Guest 与多 Guest 过载场景分开统计。
- 二阶段翻译压力测试：大内存随机访问 + 高频缺页/映射变更。

---

### 2.7 虚拟机全生命周期性能开销评估（补充：覆盖 create 到 destroy）

> 结论先行：当前生态里**没有单一测试套件**能完整覆盖虚拟机生命周期全部性能环节。  
> 工程上应采用“分层组合”方案：`libvirt TCK + QEMU functional tests + KVM selftests + kvm-unit-tests + 宏基准`。

#### 生命周期阶段与指标（RISC-V/ARM 通用）

| 阶段 | 关键操作 | 关键性能指标 | 推荐套件/工具 |
|---|---|---|---|
| 0. 准备/定义 | `define`, 资源绑定, 镜像准备 | 定义耗时、失败率、配置校验耗时 | `libvirt TCK`, `virsh` |
| 1. 创建/启动 | `create/start` 到 guest 可登录 | create latency、boot-to-login、固件阶段耗时 | `libvirt TCK`, `QEMU functional`, 自定义 boot timer |
| 2. 空闲运行 | idle 维持 | host CPU 占用、VM-exit/s、内存常驻集 | `kvm_stat`, `perf`, `KVM selftests` |
| 3. 负载运行 | CPU/内存/IO/网络 | 吞吐、尾延迟、overhead%（相对裸机） | `fio`, `iperf3`, `stress-ng`, 宏基准 |
| 4. 动态资源变更 | vCPU/memory hotplug, balloon, memslot 变化 | 热插拔耗时、性能跌落窗口、恢复时间 | `KVM selftests` (`memslot_perf_test`, `kvm_page_table_test`) |
| 5. 快照/检查点 | internal/external snapshot | snapshot 耗时、I/O 抖动、stun time | `virsh snapshot-*`, `QEMU functional` |
| 6. 实时迁移 | pre-copy/post-copy 迁移 | 总迁移时长、停机时间、脏页收敛、迁移流量 | `virsh migrate`, `KVM selftests` (`dirty_log_perf_test`, `dirty_log_test`) |
| 7. 暂停/恢复 | `suspend/resume` | suspend/resume latency、恢复后性能回稳时间 | `libvirt TCK`, `virsh`, 业务探针 |
| 8. 重启 | `reboot` | reboot-to-service、状态一致性恢复耗时 | `libvirt TCK`, `virsh` |
| 9. 关机/销毁 | `shutdown/destroy/undefine` | 优雅关机时长、强制销毁时长、资源回收滞后 | `libvirt TCK`, `virsh` |
| 10. 故障恢复（可选） | host/guest 异常后重建 | MTTR、数据完整性、恢复后性能偏移 | `QEMU functional` + 运维脚本 |

#### 分层测试职责（避免“一套件包打天下”误区）

- `libvirt TCK`：生命周期 API/状态机正确性与可重复操作流程（libvirt 官方推荐集成测试框架之一，且用于上游 CI）。  
- `QEMU tests/functional`：从 VMM 角度验证启动、设备、迁移、管理命令路径。  
- `KVM selftests`：内核 KVM API 与关键性能路径（dirty logging、memslot、页表、timer）微基准。  
- `kvm-unit-tests`：Guest 视角的 CPU/异常/设备行为，验证体系结构特性在虚机内是否符合预期。  
- 宏基准（`fio/iperf3/内核编译`）：把生命周期操作映射到业务可感知 SLA。

#### RISC-V 与 ARM 的对照维度（建议最小 A/B 组）

- RISC-V：
  - `H=off` vs `H=on`（若平台可切换）。
  - `Sstc=off` vs `Sstc=on`（关注定时器注入路径）。
  - `Svnapot=off` vs `Svnapot=on`（关注迁移与内存密集阶段的 TLB 行为）。
- ARM：
  - `VHE=off` vs `VHE=on`。
  - Generic Timer 标准配置作为基线。

#### 统一统计口径（建议直接写入测试规程）

- 启动类指标：从 `virsh start/create` 返回前后 + guest 首个健康检查成功时间（例如 SSH/agent ready）。  
- 迁移类指标：  
  - `total_migration_time`（开始到完成）；  
  - `downtime`（业务不可用窗口）；  
  - `convergence_rounds`（pre-copy 收敛轮次）；  
  - `bytes_transferred`。  
- 销毁类指标：`destroy` 到 host 资源完全释放（vCPU 线程消失、内存回收完成）。  
- 统一输出：P50/P95/P99、均值、标准差、样本量、95% 置信区间。

#### 建议执行顺序（端到端回归流水线）

1. 合规门槛：`RISCOF/riscv-arch-test`（RISC-V）+ `sysarch-acs`（ARM 平台能力）。  
2. 生命周期功能门槛：`libvirt TCK` + `QEMU functional`。  
3. 内核路径性能：`KVM selftests` + `kvm-unit-tests`。  
4. 业务相关性能：宏基准 + 生命周期操作注入（迁移/快照/热插拔）。  
5. 回归阈值判定：与上一稳定版本比较，超过阈值自动告警（建议 3%/5% 双阈值）。

---

## 3. 为什么不做 Sstvala / Ssstrict 性能评估

- `Sstvala`：本质是异常信息可用性/一致性约束，主要影响**故障处理正确性与可诊断性**，不是 steady-state 热路径优化项。
- `Ssstrict`：本质是保留/未实现编码的确定性异常语义，偏**安全与一致性约束**，不直接对应可比较的吞吐型收益。

可做的是：

- 功能一致性测试（异常触发、寄存器值、trap delegation 路径）。
- 回归测试（不同实现对同一非法编码行为一致）。

---

## 4. 权威测试套件映射表（当前软件生态）

| 目标 | 套件/框架 | 权威性来源 | 与本次扩展关系 |
|---|---|---|---|
| RISC-V ISA 合规 | `riscv-arch-test` + `RISCOF` | RISC-V 官方兼容性测试生态 | Zifencei、特权/异常/CSR 基线 |
| Linux 内核行为 | `kselftest` | Linux 主线官方自测框架 | Svnapot/Ssnpm/Sstc 相关路径 |
| 虚拟化接口与行为 | `KVM selftests` | Linux 主线 KVM 官方自测 | Sstc/H 扩展/定时器/VM 路径 |
| Guest 视角虚拟化 | `kvm-unit-tests` | KVM 社区主线测试项目 | H 扩展与定时器、异常处理 |
| 生命周期管理与状态机 | `libvirt TCK` | libvirt 官方推荐并用于上游 CI 的集成测试框架 | create/start/suspend/resume/migrate/shutdown/undefine |
| VMM 功能与迁移路径 | `QEMU tests/functional` | QEMU 官方测试框架 | 启动、设备、迁移与管理路径验证 |
| Arm 平台架构合规 | `Arm sysarch-acs`（含 BSA/SBSA ACS） | Arm 官方 SystemReady 合规体系 | Generic Timer/虚拟化平台能力基线 |

---

## 5. 推荐最小可复现实验矩阵

### 5.1 平台维度

- RISC-V：`Sstc on/off`、`Svnapot on/off`、`Ssnpm pmlen=0/7/16`、`H on/off`。
- ARM：`VHE on/off`、Generic Timer 标准路径。

### 5.2 工作负载维度

- 微基准：屏障、TLB、timer IRQ、VM-exit。
- 系统基准：`kselftest`/`KVM selftests`/`kvm-unit-tests`。
- 宏基准：编译、网络、块 I/O、内存密集任务。
- 生命周期操作：create/start/suspend/resume/snapshot/migrate/reboot/shutdown/destroy。

### 5.3 输出维度

- 必须输出：P50/P95/P99、标准差、样本数、CPU 频率与温度信息、内核配置摘要。

---

## 6. 参考资料（规范与套件）

### RISC-V 规范

1. Zifencei v2.0（Unprivileged ISA）  
   https://docs.riscv.org/reference/isa/unpriv/zifencei.html
2. Supervisor ISA / Svnapot  
   https://docs.riscv.org/reference/isa/v20240411/priv/svnapot.html
3. Pointer Masking Extensions v1.0.0（含 Ssnpm）  
   https://docs.riscv.org/reference/isa/priv/zpm.html
4. Sstc v1.0  
   https://docs.riscv.org/reference/isa/priv/sstc.html
5. Hypervisor Extension H v1.0  
   https://docs.riscv.org/reference/isa/priv/hypervisor.html
6. RVA23 Profile 1.0（含 Sstvala/Ssstrict 定义）  
   https://docs.riscv.org/reference/profiles/rva23/_attachments/rva23-profile.pdf

### ARM 与 Linux 文档

7. AArch64 Booting（含 architected timer 前置要求）  
   https://www.kernel.org/doc/html/latest/arch/arm64/booting.html
8. AArch64 Tagged Address ABI（用于 Ssnpm/TBI 对照的软件 ABI 语义）  
   https://www.kernel.org/doc/html/latest/arch/arm64/tagged-address-abi.html
9. Arm Developer（ARM ARM 文档入口，如 DDI0487）  
   https://developer.arm.com/documentation/ddi0487/latest

### 测试套件

10. RISC-V Architecture Test SIG（riscv-arch-test）  
    https://github.com/riscv-non-isa/riscv-arch-test
11. RISCOF 文档  
    https://riscof.readthedocs.io/en/1.19.0/intro.html
12. Linux kselftest 总览  
    https://docs.kernel.org/dev-tools/kselftest.html
13. Linux KVM 测试要求（明确 selftests + kvm-unit-tests）  
    https://docs.kernel.org/6.17/virt/kvm/review-checklist.html
14. kvm-unit-tests  
    https://github.com/kvm-unit-tests/kvm-unit-tests
15. Linux 源码浏览：`tools/testing/selftests/riscv/abi/pointer_masking.c`  
    https://codebrowser.dev/linux/linux/tools/testing/selftests/riscv/abi/pointer_masking.c.html
16. Linux 源码浏览：`tools/testing/selftests/mm`（hugepage/thuge 等）  
    https://codebrowser.dev/linux/linux/tools/testing/selftests/mm
17. Linux 源码浏览：`tools/testing/selftests/kvm/arch_timer.c`  
    https://codebrowser.dev/linux/linux/tools/testing/selftests/kvm/arch_timer.c.html
18. Arm System Architecture ACS（sysarch-acs）  
    https://github.com/ARM-software/sysarch-acs
19. libvirt Testing（含 TCK 在上游 CI 的定位）  
    https://libvirt.org/testing.html
20. libvirt virsh 手册（生命周期命令语义）  
    https://www.libvirt.org/manpages/virsh.html
21. QEMU Functional Tests 文档  
    https://www.qemu.org/docs/master/devel/testing/functional.html

---

*文档版本：2.1*  
*更新日期：2026-02-12*  
*说明：本版新增“虚拟机全生命周期性能开销评估”专章，补齐 create→destroy 的端到端测试设计。*
