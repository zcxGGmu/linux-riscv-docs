# 定时器/时钟 + 半虚拟化/超调用 可移植性分析

> 输入：`data/by_category/B_timer-clock.jsonl`（13 条）+ `data/by_category/B_pv-hypercall.jsonl`（16 条），共 **29 条**。
> 基线核对：本地树 `/Users/zq/Desktop/patch-work/linux-riscv`（`arch/riscv/kvm/`）。

## 摘要

- **系列总数 29**（timer-clock 13 + pv-hypercall 16）
- **四态计数**：ALREADY 3 / PORTABLE 1 / PATTERN 4 / N-A 21
  - timer-clock：PATTERN 3、N-A 10
  - pv-hypercall：ALREADY 3、PORTABLE 1、PATTERN 1、N-A 11

### 核对到的 riscv 基线事实（判定依据）
- **steal-time 已有**：`vcpu_sbi_sta.c`（SBI STA），`kvm_riscv_vcpu_record_steal_time()` 用 `current->sched_info.run_delay` 累计，字段 `vcpu->arch.sta.last_steal`——与 x86 `record_steal_time()` 的 `last_steal`/`run_delay` 完全同构。
- **PV IPI 已有**：`vcpu_sbi_replace.c` 的 `vcpu_sbi_ext_ipi`（`SBI_EXT_IPI_SEND_IPI`）——guest→guest IPI 走 SBI 超调用，即 PV-IPI。
- **PV TLB flush 已有**：`vcpu_sbi_replace.c` 的 RFENCE 全变体。
- **HSM(≈PSCI) 已有**：`vcpu_sbi_hsm.c`；**SBI 转发用户态已有**：`vcpu_sbi_forward.c` + `KVM_EXIT_RISCV_SBI`。
- **定时器为一次性(one-shot)模型**：`vcpu_timer.c` 用 `next_cycles`/`stimecmp` + hrtimer 兜底，**无周期(periodic)定时器模式** → x86 「periodic APIC/HV timer」类锁死 bug 无对应。
- **明确缺口 async_pf**：`arch/riscv/` 全树无 async_pf；通用核心 `virt/kvm/async_pf.c` 存在，仅 x86/s390 `select KVM_ASYNC_PF`。→ 最高价值移植点。
- **无 kvmclock/TSC 调优旋钮**：riscv guest 直接读 `time` CSR（Sstc），无 pvclock 式全局时钟；无 guest 时间缩放硬件。

### 本类 Top 候选（按价值排序）
1. **[pv] KVM: x86: Fix and a cleanup for async #PFs** — PATTERN（旗舰缺口：async_pf）→ 新增 SBI 扩展 + `vcpu.c` + `select KVM_ASYNC_PF`
2. **[timer] Include host suspended time in steal time (v8)** — PATTERN → `vcpu_sbi_sta.c`
3. **[timer] Fix and enhance KVM steal accounting** — PATTERN → `vcpu_sbi_sta.c`
4. **[timer] Include host suspended time in steal time (v3, 早期版)** — PATTERN（含通用 helper `kvm_total_suspend_ns()`）
5. **[pv] KVM: Remove include/kvm, standardize includes** — PORTABLE（通用 include 重构，riscv 一并受益；低价值）

---

## Top 可移植候选（深度，已 curl 核对 diff）

### 1. async #PF —— 旗舰缺口
- **原补丁**：KVM: x86: Fix and a cleanup for async #PFs（https://patchwork.kernel.org/project/kvm/patch/20250215010609.1199982-3-seanjc@google.com/）状态=new
- **diff 实质**：本系列本身仅是 x86 微调（`send_user_only`→`send_always` 反转重命名、受保护 guest 不注入 PV async #PF），改的是 `arch/x86/kvm/x86.c` 的 `apf` 状态机。但其依赖的**核心 `virt/kvm/async_pf.c` 是架构无关的**（工作队列、`kvm_setup_async_pf`、`kvm_check_async_pf_completion`）。
- **可移植点**：async page fault 整套机制——host 遇 swapped-out guest 页时不阻塞，异步换入并向 guest 注入「页未就绪/已就绪」通知，guest 侧可调度他任务。riscv **完全缺失**。
- **riscv 落点**：`arch/riscv/kvm/Kconfig` 新增 `select KVM_ASYNC_PF`；新增一个 SBI 扩展（async-PF 通知 ABI，参照 STA 的 shmem 约定）落在新文件 `vcpu_sbi_apf.c`；在 `mmu.c` 缺页路径调用 `kvm_setup_async_pf()`；`vcpu.c` 注入完成通知。核心复用 `virt/kvm/async_pf.c`（已存在，已验证）。
- **判定**：**PATTERN**（核心通用+机制清晰，但 riscv 侧需设计 SBI 通知 ABI 并重写注入路径）；本批最高价值。

### 2. 把 host 挂起时长计入 steal-time（v8）
- **原补丁**：KVM: x86: Include host suspended time in steal time（https://patchwork.kernel.org/project/kvm/patch/20250722055030.3126772-2-suleiman@google.com/）状态=new
- **diff 实质**：patch1「Advance guest TSC after deep suspend」是 x86 TSC 专属（`host_was_suspended`）；**patch2「Include host suspended duration in steal time」** 才是可移植内核——把 host S3/S4 挂起期间 guest 不可运行的时长，folded 进 guest 的 steal_time。
- **可移植点**：steal-time 语义扩展——「host 不可用时间」（挂起）也算偷取时间，避免 guest 挂起后误判时钟跳变。
- **riscv 落点**：`vcpu_sbi_sta.c` 的 `kvm_riscv_vcpu_record_steal_time()`（已有 shmem 写入路径），叠加一个 per-VM 挂起时长 delta；可配合 riscv 已有的 SBI SUSP（`vcpu_sbi_system.c`）。
- **判定**：**PATTERN**，steal-time 已有、字段同构，仅需增补挂起时长累计。

### 3. 修正并增强 steal 计费
- **原补丁**：Fix and enhance KVM steal accounting for both guest and host（https://patchwork.kernel.org/project/kvm/patch/20260505003044.78693-4-dongli.zhang@oracle.com/）状态=new
- **diff 实质（已 curl）**：`record_steal_time()` 引入 `last_downtime_steal`/`downtime_steal`，在 `kvm_vm_ioctl_set_clock()`(KVM_SET_CLOCK) 记录停机 delta 并折入 steal；另有「enable 时重置 `last_steal`」修正。均基于 `current->sched_info.run_delay`——**与 riscv 同一字段**。
- **可移植点**：(a) 使能 steal-time 时重置 `last_steal`（避免首次读到巨量偷取）；(b) 把 KVM_SET_CLOCK/停机盲区计入 steal。
- **riscv 落点**：`vcpu_sbi_sta.c`（`last_steal` 重置逻辑已在 reset 路径，可对齐 enable 语义）；停机 delta 需在 riscv 的时钟设置路径补钩子。
- **判定**：**PATTERN**，机制与 riscv steal-time 高度同构。

### 4. steal-time 挂起计费（v3 早期版，含通用 helper）
- **原补丁**：KVM: x86: Include host suspended time in steal time（https://patchwork.kernel.org/project/kvm/patch/20250107042202.2554063-2-suleiman@google.com/）状态=new
- **可移植点**：patch1「Introduce `kvm_total_suspend_ns()`」是**架构无关**的挂起时长统计 helper（可落 `virt/kvm/` 或 `kvm_host.h`），供各架构 steal-time 复用。
- **riscv 落点**：通用 helper 一次落地即可被 `vcpu_sbi_sta.c` 复用；本条为 #2 的前身，价值随 #2。
- **判定**：**PATTERN**（其通用 helper 部分近乎 PORTABLE）。

### 5. include 树形重构（通用清理）
- **原补丁**：KVM: Remove include/kvm, standardize includes（https://patchwork.kernel.org/project/kvm/patch/20250611001042.170501-7-seanjc@google.com/）状态=new
- **可移植点**：`include/kvm/iodev.h`→`include/linux/kvm_iodev.h`、各架构停止把 `virt/kvm` 塞进 include path——机械式全树重构，riscv 一并被同一补丁改到。
- **riscv 落点**：`arch/riscv/kvm/*` 的 `#include` 随之更新（riscv 经 ioeventfd 用到 iodev.h）；无需 riscv 专属逻辑。
- **判定**：**PORTABLE**（Tier-A 式通用清理，价值低但确属通用）。

---

## 全量判定表

### timer-clock（13）
| 系列 | 判定 | 可移植点(若有) | riscv落点(若有) | web_url |
|---|---|---|---|---|
| KVM: x86: Include host suspended time in steal time (v3) | PATTERN | 挂起时长计入 steal；通用 helper `kvm_total_suspend_ns()` | `vcpu_sbi_sta.c`（+可选 `virt/kvm/`） | https://patchwork.kernel.org/project/kvm/patch/20250107042202.2554063-2-suleiman@google.com/ |
| kvm: x86: fix infinite loop in kvm_guest_time_update when tsc is 0 | N-A | — kvmclock(pvclock) 专属；riscv 直读 `time` CSR | — | https://patchwork.kernel.org/project/kvm/patch/20250514064941.51609-1-liuyuntao12@huawei.com/ |
| KVM: x86: Provide a cap to disable APERF/MPERF read intercepts | N-A | — x86 APERF/MPERF MSR 拦截（selftest CPU-pin helper 可小幅借鉴） | —（selftests 侧 `lib/`） | https://patchwork.kernel.org/project/kvm/patch/20250626001225.744268-2-seanjc@google.com/ |
| KVM: x86: avoid underflow when scaling TSC frequency | N-A | — x86 TSC 比例缩放硬件；riscv 无 guest 时间缩放 | — | https://patchwork.kernel.org/project/kvm/patch/20250709175303.228675-1-pbonzini@redhat.com/ |
| KVM: x86: Include host suspended time in steal time (v8) | PATTERN | host 挂起时长 folded 进 steal_time（patch2） | `vcpu_sbi_sta.c` | https://patchwork.kernel.org/project/kvm/patch/20250722055030.3126772-2-suleiman@google.com/ |
| kvm:x86: simplify kvmclock update logic | N-A | — kvmclock 全局时钟更新逻辑（riscv 无 pvclock） | — | https://patchwork.kernel.org/project/kvm/patch/20250917092824.4070217-3-lei.chen@smartx.com/ |
| KVM: x86: fix some kvm period timer BUG | N-A | — x86 周期 APIC/HV timer；riscv 定时器为 one-shot | — | https://patchwork.kernel.org/project/kvm/patch/20251107034802.39763-2-fuqiang.wng@gmail.com/ |
| KVM: x86: Fix hard lockup with periodic timer in guest | N-A | — 同上，周期 APIC/HV timer 专属 | — | https://patchwork.kernel.org/project/kvm/patch/20251113205114.1647493-5-seanjc@google.com/ |
| paravirt: cleanup and reorg | N-A | — x86 guest 侧 paravirt 管线重排(sched_clock/pvspinlock) | — | https://patchwork.kernel.org/project/kvm/patch/20260105110520.21356-7-jgross@suse.com/ |
| arm64: EL2 support (kvm-unit-tests) | N-A | — arm64 EL2/NV 测试基建 | — | https://patchwork.kernel.org/project/kvm/patch/20260114115703.926685-10-joey.gouly@arm.com/ |
| KVM: SVM: Fix x2AVIC MSR interception mess | N-A | — AMD SVM/x2AVIC 硬件 | — | https://patchwork.kernel.org/project/kvm/patch/20260409222449.2013847-3-seanjc@google.com/ |
| Fix and enhance KVM steal accounting | PATTERN | 使能时重置 `last_steal`；KVM_SET_CLOCK 停机计入 steal | `vcpu_sbi_sta.c` | https://patchwork.kernel.org/project/kvm/patch/20260505003044.78693-4-dongli.zhang@oracle.com/ |
| KVM: x86: Block TSC multiplier writes for protected guest TSC | N-A | — x86 机密(TDX)+TSC 缩放硬件 | — | https://patchwork.kernel.org/project/kvm/patch/20260512111830.1295437-1-jun.miao@intel.com/ |

### pv-hypercall（16）
| 系列 | 判定 | 可移植点(若有) | riscv落点(若有) | web_url |
|---|---|---|---|---|
| KVM: x86: Fix and a cleanup for async #PFs | PATTERN | async page fault 整套机制（核心 `virt/kvm/async_pf.c` 通用） | 新 `vcpu_sbi_apf.c` + `mmu.c` + `vcpu.c` + `select KVM_ASYNC_PF` | https://patchwork.kernel.org/project/kvm/patch/20250215010609.1199982-3-seanjc@google.com/ |
| x86/msr: let paravirt inline rdmsr/wrmsr instructions | N-A | — x86 MSR guest 侧内联；riscv 用 CSR | — | https://patchwork.kernel.org/project/kvm/patch/20250506092015.1849-3-jgross@suse.com/ |
| KVM: Remove include/kvm, standardize includes | PORTABLE | 通用 include 重构（iodev.h→kvm_iodev.h），全树一并生效 | `arch/riscv/kvm/*` include 更新（自动） | https://patchwork.kernel.org/project/kvm/patch/20250611001042.170501-7-seanjc@google.com/ |
| kvm: x86: implement PV send_IPI method | ALREADY | riscv 经 SBI IPI 超调用发 IPI（本补丁是 guest 侧 x86 apic callback 插桩） | `vcpu_sbi_replace.c`（`vcpu_sbi_ext_ipi`） | https://patchwork.kernel.org/project/kvm/patch/20250718062429.238723-1-lulu@redhat.com/ |
| x86/kvm: Reorder PV spinlock checks for dedicated CPU case | N-A | — x86 PV qspinlock guest 侧 | — | https://patchwork.kernel.org/project/kvm/patch/20250718094936.5283-1-lirongqing@baidu.com/ |
| 答复: Re: x86/kvm: Reorder PV spinlock checks... | N-A | — 邮件回复，无补丁内容 | — | https://patchwork.kernel.org/project/kvm/patch/c985fbdb96aa44cdb9788d92046b958e@baidu.com/ |
| x86 hypercall spring/summer cleanup (kvm-unit-tests) | N-A | — x86 hypercall patching 测试 | — | https://patchwork.kernel.org/project/kvm/patch/20250724191050.1988675-3-minipli@grsecurity.net/ |
| x86/paravirt: add backoff mechanism to virt_spin_lock | N-A | — x86 PV spinlock guest 侧退避 | — | https://patchwork.kernel.org/project/kvm/patch/20250813005043.1528541-1-wangyang.guo@intel.com/ |
| [kvmtool] Import arm-smccc.h from Linux 6.17-rc7 | N-A | — arm SMCCC 头 / kvmtool 用户态 | — | https://patchwork.kernel.org/project/kvm/patch/20250930103130.197534-6-suzuki.poulose@arm.com/ |
| KVM: x86: Return "unsupported" not "invalid" on unsupported PV MSR | N-A | — x86 PV MSR 语义；riscv SBI 已返回 NOT_SUPPORTED | —（`vcpu_sbi.c` 已妥善处理） | https://patchwork.kernel.org/project/kvm/patch/20251230205948.4094097-1-seanjc@google.com/ |
| arm64: Handle PSCI calls in userspace (kvmtool v5) | ALREADY | riscv 内核已支持 SBI 转发用户态（KVM_EXIT_RISCV_SBI）；本系列是 kvmtool 用户态 | `vcpu_sbi_forward.c` + `KVM_EXIT_RISCV_SBI`（内核已备；kvmtool/QEMU riscv 侧另需用户态适配） | https://patchwork.kernel.org/project/kvm/patch/20260108175753.1292097-4-suzuki.poulose@arm.com/ |
| x86: Cleanups around slow_down_io() | N-A | — x86 guest paravirt io_delay | — | https://patchwork.kernel.org/project/kvm/patch/20260119182632.596369-3-jgross@suse.com/ |
| arm: add kvm-psci-version vcpu property (QEMU) | N-A | — QEMU arm PSCI 版本属性（用户态） | — | https://patchwork.kernel.org/project/kvm/patch/20260220115656.4831-2-sebott@redhat.com/ |
| kvmtool: arm64: Handle PSCI calls in userspace (v7) | ALREADY | 同上；riscv 内核 SBI 用户态转发已备，本系列为 kvmtool 用户态 | `vcpu_sbi_forward.c` + `KVM_EXIT_RISCV_SBI`（内核已备） | https://patchwork.kernel.org/project/kvm/patch/20260330142334.3309961-14-suzuki.poulose@arm.com/ |
| x86/apic: PV IPI robustness and subtest selection (kvm-unit-tests) | N-A | — x86 apic PV IPI 测试（patch2 测试选择 helper 泛用性极小） | — | https://patchwork.kernel.org/project/kvm/patch/20260619152006.3684428-5-jmattson@google.com/ |
| KVM: x86: Ignore pending PV EOI if vCPU has disabled PV EOIs | N-A | — x86 APIC PV EOI；riscv AIA 无 PV EOI | — | https://patchwork.kernel.org/project/kvm/patch/20260624220516.3033391-1-seanjc@google.com/ |

---

## 结论

- 本批 29 条中，**真正有价值的移植点集中在 steal-time 增强与 async_pf 新增**。
- **async_pf 是最高价值缺口**：通用核心已在 `virt/kvm/async_pf.c`，riscv 仅需设计 SBI 通知 ABI + 缺页路径钩子 + `select KVM_ASYNC_PF`。
- **steal-time 三条（timer #1/#5/#12）** 机制与 riscv `vcpu_sbi_sta.c` 高度同构（同用 `sched_info.run_delay`/`last_steal`），属低风险增补。
- 其余大多为 x86 kvmclock/TSC 缩放/APIC 周期定时器/PV spinlock/PV EOI 等**硬件或 guest 侧 paravirt 专属**，或 arm/kvmtool/QEMU **用户态工具**——riscv 无对应或内核原语已具备。
