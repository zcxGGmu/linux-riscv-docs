# 厂商增强 + x86 遗留 + FPU/XSTATE + arch-infra 可移植性分析（Tier C）

> 输入四文件共 **86 条系列**：
> - `C_vendor-enlighten.jsonl`（54：Hyper-V / Xen / kvmclock-pvclock / QEMU accel）
> - `C_x86-legacy.jsonl`（16：SMM / MTRR / PIT / PIC / IOAPIC / SGX）
> - `C_fpu-xstate.jsonl`（9：XSAVE / XSTATE / CET / APX / FXSAVE）
> - `C_arch-infra.jsonl`（7：kvm_x86_ops / kvm_x86_call / uaccess / mitigations）
>
> 判定依据：`_baseline_riscv.md`、`_taxonomy.md`，并核对本地内核树 `/Users/zq/Desktop/patch-work/linux-riscv`。

## 摘要

| 判定 | 计数 | 说明 |
|---|---|---|
| **PORTABLE** | 4 | 1 条强候选（generic irqfd 重构）+ 3 条纯清理/风格（coalesced_mmio bool、selftests 类型统一 ×2） |
| **ALREADY** | 1 | guest FPU 缺省/惰性状态管理——riscv `vcpu_fp.c`/`vcpu_vector.c` 已有等价机制 |
| **PATTERN** | 0 | （device-posted-IRQ / kvm-unit-tests backtrace 仅“相邻”，见备注，判 N-A） |
| **N-A** | 81 | x86/arm 生态专属：Hyper-V/Xen guest ABI、kvmclock、SMM/MTRR/PIT/PIC、XSAVE、VMX/SVM、kvm_x86_ops、x86 缓解措施 |

**核心结论**：本批 86 条整体判定基调 = **N-A**（占 94%）。这些系列几乎全部锚定 x86 专有硬件/固件语义（Hyper-V/Xen 半虚拟化 guest ABI、x86 kvmclock/pvclock、PC 遗留设备 SMM/MTRR/PIT/PIC/IOAPIC、x86 XSAVE 状态区、VMX/SVM 世界切换、x86 `kvm_x86_ops` 静态调用底座），riscv 无对应硬件且不需扩展通用底座。**唯一有实质价值的可移植项是 generic irqfd 注册重构**（触及 `virt/kvm/eventfd.c`，riscv AIA 经 irqfd 直接受益）。

### 本类 Top 候选（按价值排序）
1. **KVM: Make irqfd registration globally unique**（PORTABLE，强）→ `virt/kvm/eventfd.c` + `sched/wait`；riscv AIA irqfd 自动受益。
2. **KVM: Avoid literal numbers as return values**（PORTABLE，纯清理）→ `virt/kvm/coalesced_mmio.c` 返回 bool 的通用小改。
3. **KVM: selftests: Convert to kernel-style types**（2025-05-01）与其 v3（2026-04-20）（PORTABLE，风格）→ 通用 selftest lib 头（`gva_t`/`gpa_t`/`u64`），riscv selftests 目录同步适用。
4. **x86/fpu: Initialize guest fpstate ... from guest defaults**（ALREADY）→ 概念等价于 riscv 已有的 per-vcpu 惰性 guest FP/V 状态；x86 XSAVE/XFD 容器本身不移植。

---

## Top 可移植候选（深度）

### 1. KVM: Make irqfd registration globally unique  —— PORTABLE（强）
- **原补丁**：`KVM: Make irqfd registration globally unique`（v3, 13 patches, 2025-05-22）
  https://patchwork.kernel.org/project/kvm/patch/20250522235223.3178519-8-seanjc@google.com/  状态=new
- **可移植点**：对 **通用层 `virt/kvm/eventfd.c`** 的 irqfd 注册路径做重排/加锁修正——在持 `irqfds.lock` 时经 `vfs_poll()` 回调把 irqfd 挂入 eventfd 等待队列并加入 KVM 链表，令注册全局唯一/原子，消除注册竞态；配套核心改动 `sched/wait: Drop WQ_FLAG_EXCLUSIVE from add_wait_queue_priority()`。属架构无关的正确性重构（curl 确认 patch 03/13 diff 落在 `virt/kvm/eventfd.c`）。
- **riscv 落点**：无需新增文件——riscv `arch/riscv/kvm/Kconfig` 已 `select HAVE_KVM_IRQCHIP / HAVE_KVM_IRQ_ROUTING / HAVE_KVM_MSI`，故 riscv 走通用 `eventfd.c` irqfd 路径；AIA（`aia_imsic.c`/`aia_device.c` 的 MSI 路由）经 irqfd 注入的场景直接受益。核对：`virt/kvm/eventfd.c` 存在且为通用实现。
- **判定**：**PORTABLE** —— 纯 `virt/kvm/*` 通用层修正，对所有 in-kernel-irqchip 架构（含 riscv）一次性生效。

### 2. KVM: Avoid literal numbers as return values  —— PORTABLE（纯清理）
- **原补丁**：`KVM: Avoid literal numbers as return values`（10 patches, 2025-12-05）
  https://patchwork.kernel.org/project/kvm/patch/20251205074537.17072-9-jgross@suse.com/  状态=new
- **可移植点**：patch 01 `Switch coalesced_mmio_in_range() to return bool` 落在通用 `virt/kvm/coalesced_mmio.c`；其余（`kvm_complete_insn_gp`、`set_cr/set_dr`、`KVM_MSR_RET_*`、APIC MSR）均为 x86 专属。
- **riscv 落点**：`virt/kvm/coalesced_mmio.c`（通用，riscv 支持 coalesced MMIO/`KVM_CAP_IOEVENTFD`）。
- **判定**：**PORTABLE（低价值）** —— 仅通用 coalesced_mmio 的返回类型清理适用；x86 部分 N-A。

### 3. KVM: selftests: Convert to kernel-style types（含 v3）  —— PORTABLE（风格）
- **原补丁**：`KVM: selftests: Convert to kernel-style types`（10, 2025-05-01）
  https://patchwork.kernel.org/project/kvm/patch/20250501183304.2433192-11-dmatlack@google.com/  状态=new
  以及其扩版 `KVM: selftests: Use kernel-style integer and g[vp]a_t types`（v3, 19, 2026-04-20）
  https://patchwork.kernel.org/project/kvm/patch/20260420212004.3938325-11-seanjc@google.com/
- **可移植点**：通用 selftest lib 头/工具的类型统一（`vm_vaddr_t→gva_t`、`vm_paddr_t→gpa_t`、`uint64_t→u64` 等），Hyper-V 专属测试部分不适用。
- **riscv 落点**：`tools/testing/selftests/kvm/`（通用 lib 头）与 `tools/testing/selftests/kvm/riscv/`——lib 类型变更后 riscv 目录需同步跟进。
- **判定**：**PORTABLE（纯风格）** —— 通用 lib 头改动波及所有架构 selftests；机械改名，价值低。

### 备注：两类“相邻但不移植”（判 N-A）
- **KVM: x86/xen: Fix Xen/GPC/PREEMPT_RT ... rwlock_t**（2026-05-08 / 2026-05-29 两版）含 `pfncache.c`（通用 GPC）的加锁清理。**但 riscv 未 `select KVM_GENERIC_PFNCACHE`（仅 `KVM_GENERIC_HARDWARE_ENABLING`），不编译 `pfncache.c`/不使用 gfn_to_pfn_cache**，且 riscv steal-time（`vcpu_sbi_sta.c`）不走 GPC → 对 riscv 无落点，判 **N-A**。（若未来 riscv 引入 GPC，其无锁/trylock 模式可复用。）
- **KVM: x86: Add a module param to control and enumerate device posted IRQs**（arch-infra）与 IRQ-bypass/posted-interrupt 相关；baseline 列 IRQ-bypass 为缺口且 IMSIC 有直注潜力，但此补丁是 x86 posted-interrupt/IOMMU IRTE 专属枚举 → 判 **N-A**，仅备注该能力方向对应 `aia_imsic.c` 的独立 PATTERN 机会（不在本补丁范围）。

---

## 全量判定表

### C_vendor-enlighten（54）

| 系列 | 判定 | 可移植点 / riscv落点 | web_url |
|---|---|---|---|
| KVM: x86: Hyper-V SEND_IPI fix and partial testcase | N-A | Hyper-V SEND_IPI hypercall + in-kernel APIC，guest ABI 专属 | https://patchwork.kernel.org/project/kvm/patch/20250118003454.2619573-4-seanjc@google.com/ |
| KVM: x86: Update Xen-specific CPUID leaves during mangling | N-A | Xen CPUID mangling | https://patchwork.kernel.org/project/kvm/patch/20250122161612.20981-1-fgriffo@amazon.co.uk/ |
| KVM: x86: Update Xen TSC leaves during CPUID emulation | N-A | Xen TSC CPUID | https://patchwork.kernel.org/project/kvm/patch/20250124150539.69975-1-fgriffo@amazon.co.uk/ |
| KVM: x86: pvclock fixes and cleanups | N-A | x86 kvmclock/pvclock + Xen；riscv 用 Sstc/time SBI 无 kvmclock | https://patchwork.kernel.org/project/kvm/patch/20250201013827.680235-10-seanjc@google.com/ |
| KVM: x86: Address performance degradation due to APICv inhibits | N-A | x86 APICv inhibit + Hyper-V synic | https://patchwork.kernel.org/project/kvm/patch/3d8ed6be41358c7635bd4e09ecdfd1bc77ce83df.1738595289.git.naveen@kernel.org/ |
| KVM: x86/xen: Only write Xen hypercall page for guest writes to MSR | N-A | Xen hypercall page MSR | https://patchwork.kernel.org/project/kvm/patch/de0437379dfab11e431a23c8ce41a29234c06cbf.camel@infradead.org/ |
| i386/xen: Move KVM_XEN_HVM_CONFIG ioctl to kvm_xen_init_vcpu() | N-A | QEMU Xen 侧 | https://patchwork.kernel.org/project/kvm/patch/20250207143724.30792-2-dwmw2@infradead.org/ |
| KVM: x86/xen: Restrict hypercall MSR index | N-A | Xen hypercall MSR range | https://patchwork.kernel.org/project/kvm/patch/20250215011437.1203084-6-seanjc@google.com/ |
| QEMU's Hyper-V HV_X64_MSR_EOM is broken with split IRQCHIP | N-A | Hyper-V synic MSR + split irqchip | https://patchwork.kernel.org/project/kvm/patch/Z8ZBzEJ7--VWKdWd@google.com/ |
| MSR refactor with new MSR instructions support | N-A | x86 RDMSR/WRMSR 新指令重构 | https://patchwork.kernel.org/project/kvm/patch/20250422082216.1954310-3-xin@zytor.com/ |
| hw/hyperv: remove duplication compilation units | N-A | QEMU Hyper-V 编译单元 | https://patchwork.kernel.org/project/kvm/patch/20250424232829.141163-3-pierrick.bouvier@linaro.org/ |
| MSR code cleanup part one | N-A | x86 MSR 访问清理 | https://patchwork.kernel.org/project/kvm/patch/20250427092027.1598740-4-xin@zytor.com/ |
| kernel-hacking: introduce CONFIG_NO_AUTO_INLINE | N-A | 误归类；通用内核调试 config（nvme/mm/vfio…），非 KVM | https://patchwork.kernel.org/project/kvm/patch/20250429-noautoinline-v3-7-4c49f28ea5b5@uniontech.com/ |
| KVM: selftests: Convert to kernel-style types | **PORTABLE** | 通用 selftest lib 类型统一 → `selftests/kvm/riscv` 同步（风格，低价值） | https://patchwork.kernel.org/project/kvm/patch/20250501183304.2433192-11-dmatlack@google.com/ |
| KVM: x86/xen: Allow 'out of range' event channel ports in IRQ routing table | N-A | Xen evtchn 路由语义（虽触 routing 但语义专属 Xen） | https://patchwork.kernel.org/project/kvm/patch/e489252745ac4b53f1f7f50570b03fb416aa2065.camel@infradead.org/ |
| **KVM: Make irqfd registration globally unique** | **PORTABLE** | `virt/kvm/eventfd.c` irqfd 注册重构 + `sched/wait` → riscv AIA irqfd 受益（强） | https://patchwork.kernel.org/project/kvm/patch/20250522235223.3178519-8-seanjc@google.com/ |
| Fix warning for missing export.h in Hyper-V drivers | N-A | Hyper-V 驱动 export.h（x86/hv/PCI-hv/mana） | https://patchwork.kernel.org/project/kvm/patch/20250611100459.92900-6-namjain@linux.microsoft.com/ |
| Tweak TLB flushing when VMX is running on Hyper-V | N-A | VMX-on-Hyper-V EPT flush（嵌套） | https://patchwork.kernel.org/project/kvm/patch/4266fc8f76c152a3ffcbb2d2ebafd608aa0fb949.1750432368.git.jpiotrowski@linux.microsoft.com/ |
| x86/hyper-v: Filter non-canonical addresses ... HVCALL_FLUSH_VIRTUAL_ADDRESS_LIST(_EX) | N-A | Hyper-V PV TLB flush hypercall | https://patchwork.kernel.org/project/kvm/patch/c090efb3-ef82-499f-a5e0-360fc8420fb7@tum.de/ |
| treewide: Fix typo "notifer" | N-A | 拼写修正（KVM x86 + 多驱动），非特性 | https://patchwork.kernel.org/project/kvm/patch/94190C5F54A19F3E+20250722073431.21983-3-wangyuli@uniontech.com/ |
| KVM: selftests: Fix typo in hyperv cpuid test message | N-A | Hyper-V selftest 拼写 | https://patchwork.kernel.org/project/kvm/patch/20250824181642.629297-1-alok.a.tiwari@oracle.com/ |
| i386/xen: Advertise XEN_HVM_CPUID_EXT_DEST_ID ... | N-A | QEMU Xen CPUID | https://patchwork.kernel.org/project/kvm/patch/9912a9c26aa322623b09ace7a01c7a86665e147a.camel@infradead.org/ |
| KVM: x86: hyper-v: Use guard() instead of mutex_lock() | N-A | Hyper-V 文件内 guard() 清理 | https://patchwork.kernel.org/project/kvm/patch/20250901131604.646415-1-liaoyuanhong@vivo.com/ |
| KVM: SVM: Enable AVIC for Zen4+ (if x2AVIC) | N-A | SVM AVIC（x86 中断虚拟化硬件） | https://patchwork.kernel.org/project/kvm/patch/20250919215934.1590410-7-seanjc@google.com/ |
| KVM: selftests: Use GUEST_ASSERT_EQ() ... Hyper-V SVM test | N-A | Hyper-V SVM selftest | https://patchwork.kernel.org/project/kvm/patch/20251114164001.1791718-1-seanjc@google.com/ |
| KVM: Avoid literal numbers as return values | **PORTABLE** | `coalesced_mmio_in_range()`→bool 通用小改；余 x86（低价值） | https://patchwork.kernel.org/project/kvm/patch/20251205074537.17072-9-jgross@suse.com/ |
| KVM: SVM: Fix exit_code bugs | N-A | SVM VMRUN exit_code 处理 | https://patchwork.kernel.org/project/kvm/patch/20251230211347.4099600-2-seanjc@google.com/ |
| kvm: hyper-v: Delay firing of expired stimers | N-A | Hyper-V synthetic timer | https://patchwork.kernel.org/project/kvm/patch/20260115141520.24176-1-graf@amazon.com/ |
| x86/hyper-v: Validate entire GVA range ... during PV TLB flush | N-A | Hyper-V PV TLB flush | https://patchwork.kernel.org/project/kvm/patch/00a7a31b-573b-4d92-91f8-7d7e2f88ea48@tum.de/ |
| accel: Try to build without target-specific knowledge | N-A | QEMU accel（kvm/mshv/hvf/xen）构建 | https://patchwork.kernel.org/project/kvm/patch/20260225051303.91614-5-philmd@linaro.org/ |
| i386/hyperv: add stubs for synic enablement | N-A | QEMU Hyper-V synic stub | https://patchwork.kernel.org/project/kvm/patch/20260319122137.142178-3-anisinha@redhat.com/ |
| hw/hyperv: fix SynIC not initialized for CPUs after the first | N-A | QEMU Hyper-V synic 初始化 | https://patchwork.kernel.org/project/kvm/patch/20260320154752.204725-1-anisinha@redhat.com/ |
| KVM: x86/xen: Fix sleeping lock in hard IRQ context on PREEMPT_RT | N-A | Xen evtchn PREEMPT_RT（xen.c 专属） | https://patchwork.kernel.org/project/kvm/patch/20260329131543.91733-1-shaikhkamal2012@gmail.com/ |
| KVM: x86/xen: Fix PREEMPT_RT sleeping lock bug | N-A | Xen evtchn trylock | https://patchwork.kernel.org/project/kvm/patch/20260402013102.21951-1-shaikhkamal2012@gmail.com/ |
| KVM: selftests: Use kernel-style integer and g[vp]a_t types (v3) | **PORTABLE** | 通用 selftest lib 类型统一（`gva_t`/`gpa_t`/`u64`）→ `selftests/kvm/riscv` 同步（风格，低价值） | https://patchwork.kernel.org/project/kvm/patch/20260420212004.3938325-11-seanjc@google.com/ |
| KVM: x86/xen: Fix Xen / GPC / PREEMPT_RT issues with rwlock_t | N-A | 含 `pfncache.c` 通用改，但 riscv 不编译 GPC → 无落点 | https://patchwork.kernel.org/project/kvm/patch/20260508181717.3230988-3-dwmw2@infradead.org/ |
| KVM: x86/xen: bail in IRQ context on PREEMPT_RT in kvm_xen_set_evtchn_fast() | N-A | Xen evtchn fast path | https://patchwork.kernel.org/project/kvm/patch/20260506-xen-rt-sleep-v1-1-53b6b60a671d@igalia.com/ |
| [v4] KVM: x86/xen: Do not corrupt KVM clock ... (+KVM_[GS]ET_CLOCK_GUEST) | N-A | x86 kvmclock 迁移 + UAPI pvclock-abi（x86 专属） | https://patchwork.kernel.org/project/kvm/patch/20260509224824.3264567-24-dwmw2@infradead.org/ |
| KVM: x86: Fix Xen hypercall tracepoint argument assignment | N-A | Xen hypercall tracepoint | https://patchwork.kernel.org/project/kvm/patch/20260512015313.1685784-1-maqianga@uniontech.com/ |
| KVM: x86: Clean up kvm_<reg>_{read,write}() mess | N-A | x86 GPR cache/INVLPGA/ENCLS/Xen | https://patchwork.kernel.org/project/kvm/patch/20260514215355.1648463-7-seanjc@google.com/ |
| [RFC] timekeeping: Add clocksource read_raw() ... | N-A | 核心 timekeeping + hyperv/kvmclock 消费者（x86） | https://patchwork.kernel.org/project/kvm/patch/20260526230635.136914-4-dwmw2@infradead.org/ |
| KVM/x86: Drop "1" as MSR emulation return value | N-A | x86 MSR 返回值（APIC/HV/VMX/SVM） | https://patchwork.kernel.org/project/kvm/patch/20260528113605.267111-2-jgross@suse.com/ |
| KVM: x86/xen: Fix Xen/GP/PREEMPT_RT issues with rwlock_t (v2) | N-A | 同上 GPC/pfncache；riscv 无 GPC → 无落点 | https://patchwork.kernel.org/project/kvm/patch/20260529165114.748639-10-seanjc@google.com/ |
| KVM: x86: GPR accessors and x86.{c,h} spring cleaning | N-A | x86 GPR 访问器/清理 | https://patchwork.kernel.org/project/kvm/patch/20260529222223.870923-7-seanjc@google.com/ |
| timekeeping: Implement and use read_snapshot() functionality | N-A | hyperv/kvmclock clocksource + ptp vmclock | https://patchwork.kernel.org/project/kvm/patch/20260604095755.64849-3-dwmw2@infradead.org/ |
| PCI: Add support for Scalable I/O Virtualization | N-A | PCI SIOV 子系统（非 arch/*/kvm；通用 PCI/vfio） | https://patchwork.kernel.org/project/kvm/patch/20260604150153.3619662-9-dimitri.daskalakis1@gmail.com/ |
| KVM: x86/xen: Read long_mode only once in kvm_xen_set_evtchn_fast() | N-A | Xen evtchn long_mode | https://patchwork.kernel.org/project/kvm/patch/aiHPPUk5DY7rH-zL@v4bel/ |
| KVM: x86/xen: Clean up 32-bit vs. 64-bit shared info mode handling | N-A | Xen shared_info 模式 | https://patchwork.kernel.org/project/kvm/patch/20260605143034.3603-3-dwmw2@infradead.org/ |
| KVM: x86: hyper-v: Bound the bank index in hv_is_vp_in_sparse_set() | N-A | Hyper-V VP sparse set | https://patchwork.kernel.org/project/kvm/patch/aiQyZIJtO-2Aj_xN@v4bel/ |
| KVM: apply chainsaw to struct kvm_mmu | N-A | x86 软 MMU 重构（kvm_pagewalk/gva_to_gpa），riscv 无此结构 | https://patchwork.kernel.org/project/kvm/patch/20260624214218.73796-3-pbonzini@redhat.com/ |
| [v2] KVM: x86/xen: Add KVM_XEN_VCPU_ATTR_TYPE_WRITE_HYPERCALL_PAGE | N-A | Xen hypercall page attr | https://patchwork.kernel.org/project/kvm/patch/a99988d6102171663aab8d62d04cc6686d467565.camel@infradead.org/ |
| KVM: x86: hyper-v: Clamp stimer deadline to avoid livelock | N-A | Hyper-V synthetic timer | https://patchwork.kernel.org/project/kvm/patch/20260703205201.2667136-1-clopez@suse.de/ |
| Cleaning up the KVM clock mess (v6) | N-A | x86 kvmclock/pvclock 大重构（同 v4 家族） | https://patchwork.kernel.org/project/kvm/patch/20260703212145.343527-13-dwmw2@infradead.org/ |
| KVM: x86/xen: Convert evtchn_ports from IDR to XArray | N-A | Xen evtchn 端口容器 | https://patchwork.kernel.org/project/kvm/patch/20260706081311.13633-1-frn1furkan10@gmail.com/ |

### C_x86-legacy（16）

| 系列 | 判定 | 可移植点 / riscv落点 | web_url |
|---|---|---|---|
| x86/apic: SVM AVIC tests and some cleanups | N-A | kvm-unit-tests x86 APIC/AVIC/PIT | https://patchwork.kernel.org/project/kvm/patch/c13882ced3c713058c9a1ccf425f396319832b5d.1740479886.git.naveen@kernel.org/ |
| KVM: x86: Cancel hrtimer ... saving PIT state ... | N-A | PC 遗留 PIT(i8254) hrtimer | https://patchwork.kernel.org/project/kvm/patch/20250317091917.72477-1-liamni-oc@zhaoxin.com/ |
| KVM: x86: forcibly leave SMM mode on vCPU reset | N-A | SMM（x86 系统管理模式） | https://patchwork.kernel.org/project/kvm/patch/20250324175707.19925-1-m.lobanov@rosa.ru/ |
| [v3] KVM: SVM: forcibly leave SMM mode on vCPU reset | N-A | SMM + SVM | https://patchwork.kernel.org/project/kvm/patch/20250414171207.155121-1-m.lobanov@rosa.ru/ |
| target/i386: KVM: add hack for Windows vCPU hotplug with SGX | N-A | SGX（x86 飞地） | https://patchwork.kernel.org/project/kvm/patch/20250609132347.3254285-2-andrey.zhadchenko@virtuozzo.com/ |
| KVM: x86: Add I/O APIC kconfig, delete irq_comm.c | N-A | x86 PIC/IOAPIC/PIT 内核内 irqchip 重构；riscv AIA 自成体系 | https://patchwork.kernel.org/project/kvm/patch/20250611213557.294358-19-seanjc@google.com/ |
| [v2] Documentation: KVM: Add reference specs for PIT and LAPIC ioctls | N-A | PIT/LAPIC ioctl 文档（x86 设备） | https://patchwork.kernel.org/project/kvm/patch/20250905174736.260694-1-r772577952@gmail.com/ |
| Fix a lost async pagefault notification when the guest is using SMM | N-A | async-PF × SMM 交互（SMM 专属；riscv 无 SMM 且未启 async-PF） | https://patchwork.kernel.org/project/kvm/patch/20251015033258.50974-4-mlevitsk@redhat.com/ |
| x86: Restrict KVM-induced symbol exports to KVM | N-A | x86 符号导出（spec_ctrl/mtrr_state/ptdump） | https://patchwork.kernel.org/project/kvm/patch/20251112173944.1380633-3-seanjc@google.com/ |
| KVM: VMX: Always reflect SGX EPCM #PFs back into the guest | N-A | SGX EPCM #PF | https://patchwork.kernel.org/project/kvm/patch/20251121222018.348987-1-seanjc@google.com/ |
| KVM: x86: Ignore cpuid faulting in SMM | N-A | SMM + CPUID faulting | https://patchwork.kernel.org/project/kvm/patch/20260210234613.1383279-1-jmattson@google.com/ |
| [v2] KVM: x86: Take PIC lock on KVM_GET_IRQCHIP path | N-A | x86 PIC 锁 | https://patchwork.kernel.org/project/kvm/patch/20260529140013.14925-2-clopez@suse.de/ |
| KVM: x86: WARN and fail kvm_set_irq() if a PIC or I/O APIC vector is invalid | N-A | x86 PIC/IOAPIC 向量校验 | https://patchwork.kernel.org/project/kvm/patch/20260618185213.2019937-1-seanjc@google.com/ |
| [v2] KVM: x86: Exempt in-kernel PIC from "disappearing" interrupt warning | N-A | x86 PIC | https://patchwork.kernel.org/project/kvm/patch/86078441-92eb-4461-b823-7d3539ac5859@mail.kernel.org/ |
| [v2] KVM: x86: Destroy the PIC and IOAPIC before destroying vCPUs | N-A | x86 PIC/IOAPIC 销毁次序（riscv AIA 独立 teardown） | https://patchwork.kernel.org/project/kvm/patch/20260706180025.2735341-3-bestswngs@gmail.com/ |
| [v2] x86/mtrr: Drop stale linux/kvm_para.h include | N-A | MTRR 头清理 | https://patchwork.kernel.org/project/kvm/patch/20260708135232.160302-1-1234567weewee457@gmail.com/ |

### C_fpu-xstate（9）

| 系列 | 判定 | 可移植点 / riscv落点 | web_url |
|---|---|---|---|
| x86/fpu/xstate: Always preserve non-user xfeatures/flags in __state_perm | N-A | x86 XSAVE `__state_perm` 内部 | https://patchwork.kernel.org/project/kvm/patch/174652509391.406.2586983182542897870.tip-bot2@tip-bot2/ |
| x86/fpu: Initialize guest fpstate and FPU pseudo container from guest defaults | **ALREADY** | 概念=guest 专属 FPU 状态/缺省；riscv 已有惰性 guest FP/V（`vcpu_fp.c`/`vcpu_vector.c`）。x86 XSAVE/XFD 容器本身不移植 | https://patchwork.kernel.org/project/kvm/patch/20250509081615.248896-1-chao.gao@intel.com/ |
| Introduce CET supervisor state support | N-A | x86 CET supervisor xstate（guest-only xfeature） | https://patchwork.kernel.org/project/kvm/patch/20250522151031.426788-5-chao.gao@intel.com/ |
| KVM: x86: Cleanup #MC and XCR0/XSS/PKRU handling | N-A | x86 XCR0/XSS/PKRU/#MC | https://patchwork.kernel.org/project/kvm/patch/20251118222328.2265758-2-seanjc@google.com/ |
| x86: xsave: Cleanups and AVX testing | N-A | kvm-unit-tests x86 xsave/AVX | https://patchwork.kernel.org/project/kvm/patch/20251121180901.271486-2-seanjc@google.com/ |
| i386/cpu: Support APX for KVM | N-A | QEMU x86 APX（扩展 GPR 入 xsave 区） | https://patchwork.kernel.org/project/kvm/patch/20251211070942.3612547-9-zhao1.liu@intel.com/ |
| x86, fpu: check for consistency after loading fpregs | N-A | x86 FPU 加载一致性检查 | https://patchwork.kernel.org/project/kvm/patch/20251222212426.834058-1-pbonzini@redhat.com/ |
| KVM: x86: Fix incorrect memory constraint for FXSAVE in emulator | N-A | x86 FXSAVE 模拟器约束 | https://patchwork.kernel.org/project/kvm/patch/20260212102854.15790-1-ubizjak@gmail.com/ |
| KVM: x86: Zero-initialize temporary fxregs_state buffers in FXSAVE emulation | N-A | x86 FXSAVE 模拟缓冲清零 | https://patchwork.kernel.org/project/kvm/patch/20260212212457.24483-1-ubizjak@gmail.com/ |

### C_arch-infra（7）

| 系列 | 判定 | 可移植点 / riscv落点 | web_url |
|---|---|---|---|
| KVM: VMX: Reinstate __exit attribute for vmx_exit | N-A | VMX 模块 __exit 属性 | https://patchwork.kernel.org/project/kvm/patch/20250102154050.2403-1-costas.argyris@amd.com/ |
| KVM: x86: Add a module param to control and enumerate device posted IRQs | N-A | x86 posted-interrupt/IOMMU IRTE；能力方向对应 `aia_imsic.c` 独立 PATTERN（不在本补丁范围） | https://patchwork.kernel.org/project/kvm/patch/20250315025615.2367411-1-seanjc@google.com/ |
| KVM: x86: Revert kvm_x86_ops.mem_enc_ioctl() back to an OPTIONAL hook | N-A | x86 `kvm_x86_ops` + mem_enc（SEV/TDX） | https://patchwork.kernel.org/project/kvm/patch/20250502203421.865686-1-seanjc@google.com/ |
| Better backtraces for leaf functions | N-A | kvm-unit-tests x86/arm backtrace；Makefile late-CFLAGS 脚手架通用但 riscv 未触及 | https://patchwork.kernel.org/project/kvm/patch/20250915215432.362444-3-minipli@grsecurity.net/ |
| KVM: x86: align the code with kvm_x86_call() | N-A | x86 `kvm_x86_call()` 静态调用底座 | https://patchwork.kernel.org/project/kvm/patch/20260105065423.1870622-1-jun.miao@intel.com/ |
| uaccess: Convert small fixed size copy_{to/from}_user() to scoped user access | N-A | 核心内核 uaccess 重构（非 KVM 专属；riscv uaccess 由其自身维护） | https://patchwork.kernel.org/project/kvm/patch/0ee46bb228d97163fbdc14f2a7c52b93d8bc34ce.1777306795.git.chleroy@kernel.org/ |
| VMSCAPE optimization for BHI variant | N-A | x86 推测执行缓解（VMSCAPE/BHI/IBPB） | https://patchwork.kernel.org/project/kvm/patch/20260622-vmscape-bhb-v12-8-76cbda0ae3e5@linux.intel.com/ |

---

## 验证记录（本地内核树 `/Users/zq/Desktop/patch-work/linux-riscv`）
- `virt/kvm/eventfd.c`、`coalesced_mmio.c`、`pfncache.c`、`irqchip.c` 均存在（通用层）。
- riscv `arch/riscv/kvm/Kconfig` 选中 `HAVE_KVM_IRQCHIP / HAVE_KVM_IRQ_ROUTING / HAVE_KVM_MSI` → 走通用 irqfd（`eventfd.c`）；AIA 落点 `aia_imsic.c`/`aia_device.c`/`aia_aplic.c`/`aia.c` 齐备。
- riscv **未** select `KVM_GENERIC_PFNCACHE`（仅 `KVM_GENERIC_HARDWARE_ENABLING`）→ 不编译 `pfncache.c`/GPC ⇒ Xen/GPC/PREEMPT_RT 系列对 riscv **无落点**（判 N-A）。
- riscv 已有 `vcpu_fp.c`/`vcpu_vector.c`（惰性 guest FP/V）⇒ x86 XSAVE/XSTATE 系列无移植需求。
- curl 确认 `KVM: Make irqfd registration globally unique` patch 03/13 diff 落在 `virt/kvm/eventfd.c`（通用层，PORTABLE 成立）。
