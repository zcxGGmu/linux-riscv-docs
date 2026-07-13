# misc 杂项 可移植性分析

> 输入：`kvm-riscv/data/by_category/?_misc.jsonl`（282 条系列，行号=表内 #）。
> 本类为「未命中特定关键词」的 x86/arm 维护补丁，绝大多数为架构专属 fix/cleanup/refactor。
> 核心任务：从噪声中挖出触碰 `virt/kvm/*` 通用层或机制可复用于 riscv 的隐藏可移植项。

## 摘要

- **系列总数**：282
- **四态计数**：ALREADY = 2 ｜ PORTABLE = 4 ｜ PATTERN = 6 ｜ N-A = 270
- 结论：misc 桶信噪比极低（~96% N-A）。绝大多数是 VMX/SVM/SEV/TDX/AVIC/nested/emulate/CET/speculation/GIC/arm-sysreg 的架构专属改动，或 kvm-unit-tests / QEMU / kvmtool / 纯内核构建补丁 —— 对 riscv 无移植价值。
- **挖出的真金（通用层 `virt/kvm/kvm_main.c`，改动对 riscv 自动/近自动生效）**：
  1. **[#187] KVM: x86: Optimize kvm_vcpu_on_spin() directed yield** — PORTABLE，3 补丁全在 `kvm_main.c`，riscv `vcpu_insn.c:86` 调用点直接受益。
  2. **[#115] KVM: Disable IRQs in kvm_online_cpu()/kvm_offline_cpu()** — PORTABLE，patch 1 修 `kvm_main.c` CPU 热插拔路径（riscv 用 `KVM_GENERIC_HARDWARE_ENABLING`）。
  3. **[#240] kvm: rework memory prefault** — PORTABLE，重构通用 `KVM_GENERIC_PRE_FAULT_MEMORY`（riscv 尚未 select，是明确缺口）。
  4. **[#275] KVM: s390: Introduce arm64 KVM（含通用 KVM/VFIO 基础设施子集）** — PORTABLE（部分），"Remove KVM_MMIO as config option"/"Make device name configurable"/VFIO 引用计数为通用改动，触碰 riscv Kconfig。
- **机制可复用（PATTERN）**：[#51] irq-bypass 内联（指向 IMSIC 直注缺口）、[#95/#198/#235] `array_index_nospec` 反 Spectre-v1 索引硬化、[#204] `gfn_to_pfn_cache` 用于 steal-time、[#207] kvm-unit-tests GDB stub/单步（调试缺口）。
- **ALREADY（已证明通用层自动覆盖 riscv）**：[#56] `kvm_trylock_all_vcpus`（已合并，riscv `aia_device.c:30` 已调用）、[#75] riscv kvmtool 支持（riscv 原生补丁）。

## Top 可移植候选（深度，已 curl mbox + 本地源码核对）

### 1. [#187] KVM: x86: Optimize kvm_vcpu_on_spin() directed yield — **PORTABLE**
- **原补丁**：`KVM: x86: Optimize kvm_vcpu_on_spin()`（https://patchwork.kernel.org/project/kvm/patch/tencent_EAB2053E04BF4C7F996CEC61331C23154007@qq.com/）状态=new，3 补丁。
- **可移植点**：3 补丁全部改 `virt/kvm/kvm_main.c`（经 mbox 确认 `+++ b/virt/kvm/kvm_main.c`）：① 增强 `kvm_vcpu_eligible_for_directed_yield()` 识别「黄金」被让渡目标；② 主循环跳过 `IN_GUEST_MODE` 的 vcpu；③ 依 vcpu 数动态调整 try 次数。纯通用 vcpu 调度/让渡优化，与架构无关。
- **riscv 落点**：无需新增代码——通用函数改动直接生效；riscv 的 `arch/riscv/kvm/vcpu_insn.c:86`（WFI/`SBI pause` → `kvm_vcpu_on_spin(vcpu, ...)`）为现成调用点，自动获益。
- **判定**：PORTABLE —— Tier A 通用层，riscv 已是该 API 的消费者。

### 2. [#115] KVM: Disable IRQs in kvm_online_cpu()/kvm_offline_cpu() — **PORTABLE**
- **原补丁**：`[v3,1/2] KVM: Disable IRQs in kvm_online_cpu()/kvm_offline_cpu()`（https://patchwork.kernel.org/project/kvm/patch/15fa59ba7f6f849082fb36735e784071539d5ad2.1758002303.git.houwenlong.hwl@antgroup.com/）状态=new，2 补丁。
- **可移植点**：patch 1 改 `virt/kvm/kvm_main.c`（mbox 确认 `+++ b/virt/kvm/kvm_main.c`）——在 CPU 上/下线回调中关中断，修通用硬件使能路径的时序正确性。patch 2（`kvm_on_user_return` 注释/代码）为 x86 专属 → N-A。
- **riscv 落点**：`kvm_online_cpu`/`kvm_offline_cpu` 在 `kvm_main.c:5609/5629`；riscv `Kconfig` `select KVM_GENERIC_HARDWARE_ENABLING`，走同一路径，patch 1 自动生效。
- **判定**：PORTABLE（仅 patch 1；patch 2 N-A）。

### 3. [#240] kvm: rework memory prefault — **PORTABLE**
- **原补丁**：`[1/2] kvm: rework memory prefault`（https://patchwork.kernel.org/project/kvm/patch/20260526125220.1560451-1-arnd@kernel.org/）状态=new，2 补丁。
- **可移植点**：mbox 确认改动集中在通用层 `include/linux/kvm_host.h`、`virt/kvm/Kconfig`、`virt/kvm/kvm_main.c`（另含 x86/s390 的 Kconfig+host.h 适配）。重构 `KVM_GENERIC_PRE_FAULT_MEMORY`（`KVM_PRE_FAULT_MEMORY` ioctl）机制。
- **riscv 落点**：`arch/riscv/kvm/Kconfig`（当前**未** select `KVM_GENERIC_PRE_FAULT_MEMORY`，基线缺口#确认）；opt-in 后需在 gstage 侧提供 `kvm_arch_vcpu_pre_fault_memory` 落点（`gstage.c`/`mmu.c`）。属基线明确的「可 opt-in」缺口。
- **判定**：PORTABLE —— 通用机制重构 + riscv 现存缺口，价值中高。

### 4. [#275] KVM: s390: Introduce arm64 KVM（通用 KVM/VFIO 基础设施子集）— **PORTABLE（部分）**
- **原补丁**：`KVM: s390: Introduce arm64 KVM`（https://patchwork.kernel.org/project/kvm/patch/20260706085229.979525-12-seiden@linux.ibm.com/）状态=new，27 补丁。
- **可移植点**：sample_titles 中的通用子集——`KVM: Make device name configurable`、`KVM: Remove KVM_MMIO as config option`、`KVM,vfio: remove symbol_get(kvm_get_kvm_safe/kvm_put_kvm)`、`VFIO: take reference to the KVM module`——均为 `virt/kvm/*` + KVM-VFIO 胶合层通用改动。其余大量「s390 复用 arm64 头文件」的构建工具补丁（如所 curl 的 patch 11「s390: Use arm64 headers」）为 N-A。
- **riscv 落点**：`arch/riscv/kvm/Kconfig` 当前 `select KVM_MMIO`——若上游将 KVM_MMIO 由 config 选项改为无条件，riscv Kconfig 需同步（treewide 改动含 riscv）；VFIO 引用计数改动对所有支持 vfio 的架构通用。
- **判定**：PORTABLE（仅通用 KVM/VFIO 子集；arm64/s390 头共享工具 N-A）。价值中低（多为 infra/refcount 清理）。

### 5. [#51] KVM: arm64, x86: make kvm_arch_has_irq_bypass() inline — **PATTERN**
- **原补丁**：`[v2] KVM: arm64, x86: make kvm_arch_has_irq_bypass() inline`（https://patchwork.kernel.org/project/kvm/patch/20250424172832.401651-1-pbonzini@redhat.com/）状态=new。
- **可移植点**：补丁本身仅把 x86/arm 的 `kvm_arch_has_irq_bypass()` 改为内联（mbox 确认只碰 `arch/{arm64,x86}`，不碰 `virt/kvm`）——本体非可移植。**真正价值**是它点出 IRQ bypass / posted-interrupt 通用框架（`virt/kvm` + `irqbypass.ko` 的 producer/consumer）——本地 grep 确认 riscv **完全无** `irq_bypass`（基线缺口#4）。
- **riscv 落点**：新增 `arch/riscv/kvm/` irq-bypass producer，基于 IMSIC 直注（HWACCEL 模式已具直注潜力，见 `aia*.c`）；需 `select HAVE_KVM_IRQ_BYPASS` 并实现 `kvm_arch_has_irq_bypass()`。
- **判定**：PATTERN —— 机制可复用，riscv 侧全新实现，价值中（依赖 IMSIC 直注推进）。

### 6. [#95/#198/#235] `array_index_nospec` 反 Spectre-v1 索引硬化 — **PATTERN**
- **代表补丁**：`[v3] KVM: x86: use array_index_nospec with indices that come from guest`（https://patchwork.kernel.org/project/kvm/patch/20250804064405.4802-1-thijs@raymakers.nl/）；另 #198（`__pv_send_ipi`）、#235（`kvm_vcpu_ioctl_x86_set_mce`）同模式。
- **可移植点**：对来自 guest 的数组下标统一加 `array_index_nospec()`，为通用 Spectre-v1 安全硬化范式（非 x86 专属逻辑）。
- **riscv 落点**：审查 riscv 侧一切以 guest 提供值作数组索引处——`vcpu_sbi.c`/`vcpu_sbi_*.c`（SBI EID/FID 分发）、`vcpu_onereg.c`/`isa.c`（ONE_REG 索引）、`aia_imsic.c`（guest file 索引）——按需补 `array_index_nospec()`。
- **判定**：PATTERN —— 安全模式可移植，落点需 riscv 侧逐一核对。

### 7. [#204] KVM: x86: Use gfn_to_pfn_cache for record_steal_time — **PATTERN**
- **原补丁**：`[v3] KVM: x86: Use gfn_to_pfn_cache for record_steal_time`（https://patchwork.kernel.org/project/kvm/patch/1d6712ed413ea66ef376d1410811997c3b416e99.camel@infradead.org/）状态=new。
- **可移植点**：把 steal-time 结构的 guest 内存访问从每次 `gfn→hva` 转换改为常驻 `gfn_to_pfn_cache`（`virt/kvm/pfncache.c`，通用）。降低热路径开销 + 修 memslot 变更竞态。
- **riscv 落点**：riscv 已有 steal-time（SBI STA，`vcpu_sbi_sta.c`）；当前用直接 `kvm_vcpu_write_guest` 类访问，可改用 `gfn_to_pfn_cache` 缓存 SBI STA 共享结构页。pfncache 为通用底座（基线列为通用适用）。
- **判定**：PATTERN —— 机制通用、riscv 已有 steal-time 落点，价值中低（优化非功能）。

### 8. [#207] Add GDB stub and step-debug support (kvm-unit-tests, x86+arm64) — **PATTERN**
- **原补丁**：`Add GDB stub and step-debug support for x86 and arm64`（https://patchwork.kernel.org/project/kvm/patch/177458000064.86256.18394173730946703220@gmail.com/）状态=new，2 补丁。
- **可移植点**：kvm-unit-tests 内 GDB stub + 单步调试测试基架，思想跨架构；关联基线调试缺口（HW 断点/单步，`kvm_guest_debug_arch` 为空）。
- **riscv 落点**：kvm-unit-tests riscv 目录新增对应 stub；长线呼应 riscv `KVM_SET_GUEST_DEBUG`/单步实现。
- **判定**：PATTERN —— 测试/调试基架可复用，价值低（riscv guest-debug 本体尚缺）。

## 全量判定表（覆盖 282 条；# = JSONL 行号）

> N-A 一句话给理由；PORTABLE/PATTERN/ALREADY 见上文深度条目（web_url 已附）。

| # | 系列（简） | arch | 判定 | 理由 / riscv落点 |
|---|---|---|---|---|
| 1 | Fix comment of handle_vmx_instruction | x86 | N-A | VMX 注释 |
| 2 | SVM str_enabled_disabled() helper | x86 | N-A | SVM cleanup |
| 3 | Address Space Isolation (ASI) | x86 | N-A | x86 mm 缓解，非 KVM 通用 |
| 4 | x86: Clean up MP_STATE transitions | x86 | N-A | x86 pv_unhalted 专属 |
| 5 | x86: use kvfree_rcu | x86 | N-A | cleanup |
| 6 | Remove unused iommu_domain from kvm_arch | x86 | N-A | x86 结构清理 |
| 7 | Load DR6 with guest value | x86 | N-A | x86 调试寄存器 |
| 8 | cpuid: add type suffix const 48 | x86 | N-A | 构建告警 |
| 9 | SRSO_USER_KERNEL_NO not synthesized | x86 | N-A | x86 speculation |
| 10 | arm64: Remove cyclical dep in arm_pmuv3.h | arm | N-A | arm 构建 |
| 11 | x86: Bump per-CPU stack to 12KiB | x86 | N-A | kvm-unit-tests |
| 12 | x86/bugs: SRSO_MSR_FIX | x86 | N-A | x86 speculation |
| 13 | kvm,sched: Add gtime halted | x86 | N-A | RFC，KVM 部分 x86 专属（sched 侧思想通用但实现 x86） |
| 14 | Unify IBRS virtualization | x86 | N-A | x86 speculation |
| 15 | x86: split/bus lock smoke test | x86 | N-A | kvm-unit-tests |
| 16 | x86: Use macros for selectors in asm | x86 | N-A | kvm-unit-tests |
| 17 | kvm-unit-tests x86 pull | x86 | N-A | 测试 pull |
| 18 | x86: Fix "debug" test on AMD | x86 | N-A | kvm-unit-tests |
| 19 | x86: Always set mp_state RUNNABLE on HLT wake | x86 | N-A | x86 HLT/mp_state 专属 |
| 20 | SVM: Inject #GP INVPCID non-canonical | x86 | N-A | SVM 指令 |
| 21 | SVM: VMGEXIT GHCB exit codes readable | x86 | N-A | SEV/SVM |
| 22 | VMX: Remove EPT_VIOLATIONS_ACC_*_BIT | x86 | N-A | VMX EPT |
| 23 | vhost task creation failure / nx_huge_page | x86 | N-A | nx_huge_page 为 x86 影子分页 |
| 24 | VMX: Extract entry/exit control checks | x86 | N-A | VMX |
| 25 | SVM: Fix DEBUGCTL bugs | x86 | N-A | SVM/x86 调试 |
| 26 | x86: Optimize "stale" EOI bitmap / IO-APIC | x86 | N-A | x86 irqchip |
| 27 | SVM: avoid frequency indirect calls | x86 | N-A | SVM |
| 28 | x86: block KVM_CAP_SYNC_REGS if protected | x86 | N-A | SYNC_REGS+机密计算，riscv 无 |
| 29 | Forbid load_host_xsave with guest protected | x86 | N-A | x86 xsave+机密 |
| 30 | Make ASIDs static for SVM | x86 | N-A | SVM ASID |
| 31 | x86: Unify cross-vCPU IBPB | x86 | N-A | x86 speculation |
| 32 | x86: Check high 32bits clear in vcpu_ioctl_run | x86 | N-A | x86 专属字段（保留字校验思想通用，价值低） |
| 33 | x86: clean up a return | x86 | N-A | trivial |
| 34 | x86: Sort CPUID_8000_0021_EAX bits | x86 | N-A | x86 cpuid |
| 35 | arm64: default QEMU CPU "max" (v3) | arm | N-A | kvm-unit-tests 配置 |
| 36 | x86: Expose ARCH_CAP_FB_CLEAR | x86 | N-A | x86 speculation |
| 37 | x86: Acquire SRCU in KVM_GET_MP_STATE | x86 | N-A | x86 apic 内存访问；SRCU 保护为通用模式但 riscv GET_MP_STATE 无 guest 访存 |
| 38 | VMX: Fix lockdep false positive PI wakeup | x86 | N-A | VMX posted-int |
| 39 | x86/irq: Optimize KVM's PIR harvesting | x86 | N-A | VMX posted-int |
| 40 | VMX: quirk to (not) honor guest PAT | x86 | N-A | VMX PAT |
| 41 | arm: Drop 32-bit kvmtool | arm | N-A | kvmtool |
| 42 | arm64: Debug cleanups | arm | N-A | arm 调试 |
| 43 | arm64: default QEMU CPU "max" (v4) | arm | N-A | kvm-unit-tests 配置 |
| 44 | X86_FEATURE_PREFETCHI (AMD) | x86 | N-A | x86 cpufeature |
| 45 | x86/msr: Standardize u32 MSR indices | x86 | N-A | x86 msr |
| 46 | x86: asm_inline in kvm_hypercall | x86 | N-A | x86 asm |
| 47 | x86: Correct use of kvm_rip_read() | x86 | N-A | x86 tracepoint |
| 48 | x86: Don't report guest usermode emu error | x86 | N-A | x86 emulate |
| 49 | x86/e820: Discard high memory 32-bit | x86 | N-A | x86 boot |
| 50 | SVM: move kfree() out of spin_lock | x86 | N-A | SVM（锁外释放为通用范式，位置 x86，价值低） |
| 51 | make kvm_arch_has_irq_bypass() inline | x86+arm | **PATTERN** | IRQ-bypass 框架，riscv 无（缺口#4）→ IMSIC 直注 producer |
| 52 | SVM: dump_ghcb() GHCB snapshot | x86 | N-A | SEV |
| 53 | x86/msr: Add missing includes | x86 | N-A | 头文件 |
| 54 | SVM: SRSO BP_SPEC_REDUCE on VM count | x86 | N-A | SVM speculation |
| 55 | target/i386: EPYC CPU models | x86 | N-A | QEMU |
| 56 | KVM: lockdep improvements (lock_all_vcpus) | x86+arm | **ALREADY** | 通用 `kvm_(try)lock_all_vcpus` 已合并；riscv `aia_device.c:30` 已调用 |
| 57 | VMX: noinstr for is_td_vcpu/is_td | x86 | N-A | VMX TDX |
| 58 | VMX: __always_inline is_td_vcpu | x86 | N-A | VMX TDX |
| 59 | VMX: braces for ext interrupt info | x86 | N-A | VMX |
| 60 | perf/x86: struct for guest PEBS | x86 | N-A | x86 perf PEBS |
| 61 | target/i386/kvm: Refine VMX controls | x86 | N-A | QEMU |
| 62 | x86/msr: SPEC_CTRL coverage | x86 | N-A | kvm-unit-tests |
| 63 | x86: Clean up MSR interception (32p) | x86 | N-A | x86 MSR bitmap |
| 64 | More cleanups to MSR interception | x86 | N-A | x86 MSR bitmap |
| 65 | x86: Fix build warnings export.h | x86 | N-A | 构建 |
| 66 | x86: Dynamically alloc bitmap (frame size) | x86 | N-A | x86（大栈位图动态分配思想通用，价值低） |
| 67 | x86: CET fixes and enhancements | x86 | N-A | kvm-unit-tests CET |
| 68 | arm/arm64: kvmtool in runner script | arm | N-A | kvm-unit-tests 脚本（riscv 亦可受益，价值低） |
| 69 | Improve CET tests | x86 | N-A | kvm-unit-tests CET |
| 70 | ARCH_CAPABILITIES not advertised on AMD | x86 | N-A | x86 |
| 71 | VMX: host MSR read/write helpers | x86 | N-A | VMX |
| 72 | x86: Advertise support for LKGS | x86 | N-A | x86 指令 |
| 73 | kvm-unit-tests x86 pull | x86 | N-A | 测试 pull |
| 74 | x86/kvm: native qspinlock realtime hinted | x86 | N-A | x86 guest pv-spinlock |
| 75 | riscv: Add kvmtool support | arm | **ALREADY** | riscv 原生补丁（kvm-unit-tests），非 x86→riscv 移植 |
| 76 | SVM: Emulate PERF_CNTR_GLOBAL_STATUS_SET | x86 | N-A | SVM PMU |
| 77 | objtool: indirect calls in __nocfi | x86 | N-A | x86 emulate/objtool |
| 78 | arm64: Clear pending exception before inject | arm | N-A | arm 异常 |
| 79 | VMX: zero unused kvm_tdx_capabilities | x86 | N-A | TDX |
| 80 | VMX: Fix an indentation | x86 | N-A | trivial |
| 81 | x86: Don't recheck L1 intercepts userspace IO | x86 | N-A | x86 nested |
| 82 | perf/x86: PERF_CAP_PEBS_TIMING_INFO | x86 | N-A | x86 perf |
| 83 | x86: Handle KCOV __init vs inline | x86 | N-A | 构建 |
| 84 | x86: simplify kvm_vector_to_index() | x86 | N-A | x86 apic |
| 85 | arm64: Check SYSREGS_ON_CPU | arm | N-A | arm sysreg |
| 86 | arm64: Filter HCR_EL2.VSE in hyp ctx | arm | N-A | arm |
| 87 | x86: Remove space before \n | x86 | N-A | trivial |
| 88 | x86/kvm: Downgrade host poll msgs pr_debug | x86 | N-A | 日志 cleanup |
| 89 | x86/kvm: native qspinlock dedicated vCPUs | x86 | N-A | x86 guest pv-spinlock |
| 90 | x86/irq: introduce repair_irq | x86 | N-A | x86 irq |
| 91 | stackleak: Clang stack depth tracking | x86+arm | N-A | 内核硬化，非 KVM |
| 92 | x86/kvm: kvm_async_pf_task_wake local static | x86 | N-A | x86 async-PF guest |
| 93 | arm64: Move vLPI/vSGI to direct_msis | arm | N-A | arm GIC |
| 94 | arm64: nv: check ESR_EL2.VNCR | arm | N-A | arm nested |
| 95 | x86: array_index_nospec guest indices | x86 | **PATTERN** | Spectre-v1 索引硬化 → riscv vcpu_sbi_*/onereg 索引 |
| 96 | x86: Sync APIC State with QEMU split | x86 | N-A | x86 apic |
| 97 | VMX: Micro-optimize SPEC_CTRL | x86 | N-A | VMX |
| 98 | arm64: AT + SR accessor fixes | arm | N-A | arm nested |
| 99 | VMX: Make CR4.CET guest owned bit | x86 | N-A | VMX CET |
| 100 | arm64: FEAT_RASv1p1 support | arm | N-A | arm RAS |
| 101 | x86/cpu/topology: AMD/Hygon virt | x86 | N-A | x86 topology |
| 102 | VMX: Fix SPEC_CTRL handling | x86 | N-A | VMX |
| 103 | cpufreq: __free() for cpufreq_cpu_get (18p) | x86+arm | N-A | treewide `__free()` 清理；KVM 部分 x86（范式通用价值低） |
| 104 | x86: Latch INITs specific CPU states | x86 | N-A | x86 INIT/SIPI |
| 105 | perf test: x86 topdown build error | x86 | N-A | perf test |
| 106 | x86/apic: guard() instead of mutex_lock | x86 | N-A | x86 apic（guard() 范式通用价值低） |
| 107 | x86,fs/resctrl: SDCIAE | x86 | N-A | x86 resctrl |
| 108 | SVM: memdup_user() | x86 | N-A | SVM（memdup 范式通用价值低） |
| 109 | arm64: Mark freed S2 MMUs invalid | arm | N-A | arm nested S2 |
| 110 | Enable Shadow Stack Virt for SVM | x86 | N-A | SVM CET |
| 111 | x86: Fix hypercalls docs section order | x86 | N-A | docs |
| 112 | x86: Restrict writeback of SMI state | x86 | N-A | x86 SMM |
| 113 | x86: Remove outdated kvm_on_user_return | x86 | N-A | x86 user-return MSR |
| 114 | arm64: TTW reporting SEA + 52bit PA | arm | N-A | arm PTW |
| 115 | KVM: Disable IRQs in kvm_online_cpu() | x86 | **PORTABLE** | patch1 通用 `kvm_main.c` CPU 热插拔；patch2 x86 N-A |
| 116 | x86/vmx: align kernel VMX defs | x86 | N-A | kvm-unit-tests |
| 117 | x86: ENTER/LEAVE not branches | x86 | N-A | x86 emulate |
| 118 | x86: Drop "cache" from user-return MSR setter | x86 | N-A | x86 user-return MSR |
| 119 | x86: Init allow_smaller_maxphyaddr earlier | x86 | N-A | x86 setup |
| 120 | x86: Advertise EferLmsleUnsupported | x86 | N-A | x86 EFER |
| 121 | VMX: Remove stale vmx_set_dr6() decl | x86 | N-A | VMX |
| 122 | SVM: Handle EferLmsleUnsupported | x86 | N-A | x86 EFER |
| 123 | SVM: Don't set GIF clearing EFER.SVME | x86 | N-A | SVM |
| 124 | VMX: #UD on SEAMCALL/TDCALL | x86 | N-A | VMX TDX |
| 125 | x86: Unify L1TF flushing per-CPU var | x86 | N-A | x86 L1TF |
| 126 | VMX: Unify L1D flush for L1TF | x86 | N-A | VMX L1TF |
| 127 | Enable FRED with KVM VMX (22p) | x86 | N-A | VMX FRED |
| 128 | x86: MSR_IA32_S_CET not by XSAVES | x86 | N-A | x86 doc |
| 129 | More tests selective CR0 intercept | x86 | N-A | kvm-unit-tests svm |
| 130 | x86: dedup unhandled VM-Exit reporting | x86 | N-A | x86（riscv vcpu_exit.c 自有报告，价值低） |
| 131 | SVM: raw spinlock ir_list_lock | x86 | N-A | SVM AVIC |
| 132 | x86: Document GIF virt gap on AMD | x86 | N-A | doc |
| 133 | SVM: Mark VMCB_LBR dirty on DebugCtl[LBR] | x86 | N-A | SVM LBR |
| 134 | VMX: Fix valid GVA on EPT violation | x86 | N-A | VMX EPT |
| 135 | x86: dedup loading guest/host XCR0/XSS | x86 | N-A | x86 xsave |
| 136 | SVM: SPEC_CTRL[63:32] ctx switch | x86 | N-A | SVM speculation |
| 137 | VMX: loaded_vmcs_clear() static | x86 | N-A | VMX |
| 138 | x86: "checked" get_user/put_user | x86 | N-A | x86（uaccess 范式通用价值低） |
| 139 | KVM: ERAPS feature (svm) | x86 | N-A | SVM |
| 140 | x86: Alloc/free user_return_msrs at (un)load | x86 | N-A | x86 user-return MSR |
| 141 | x86: dedup loading guest/host XCR0/XSS (v2) | x86 | N-A | x86 xsave |
| 142 | arm64: Finalize ID registers once per VM | arm | N-A | arm ID regs |
| 143 | SVM: Fix/clean up OSVW handling (0/5) | x86 | N-A | SVM OSVW |
| 144 | SVM: Serialize OSVW global vars (1/5) | x86 | N-A | SVM OSVW |
| 145 | x86: Improve CET tests (v4) | x86 | N-A | kvm-unit-tests CET |
| 146 | x86: Remove unused kvm_mmu_may_ignore_pat | x86 | N-A | x86 mmu decl |
| 147 | kvm-unit-tests x86 pull | x86 | N-A | 测试 pull |
| 148 | x86: Enforce EXPORT_SYMBOL_FOR_KVM_INTERNAL | x86 | N-A | 宏本体通用（已在树）但强制 x86 专属 |
| 149 | arm64: 32bit ID registers writable | arm | N-A | arm ID regs |
| 150 | x86: Fix NULL deref amd_pmu_refresh() | x86 | N-A | x86 pmu |
| 151 | arm64: ICH_HCR_EL2_TDIR cap | arm | N-A | arm GIC |
| 152 | arm64: endian cast kvm_swap_s1_desc | arm | N-A | arm nested |
| 153 | arm64: no FIELD_PREP() in initialisers | arm | N-A | arm |
| 154 | arm64: endian cast kvm_swap_s[12]_desc v2 | arm | N-A | arm nested |
| 155 | arm64: Fix spelling "Unexpeced" | arm | N-A | trivial |
| 156 | arm64: ARM_SMCCC_OWNER_ARCH in place of 0 | arm | N-A | arm SMCCC |
| 157 | x86/kvm: Avoid freeing stack node async_pf | x86 | N-A | x86 async-PF guest |
| 158 | x86: Don't read CR3 async pf when protected | x86 | N-A | x86 async-PF+机密 |
| 159 | perf/x86/intel: no BTS for guests | x86 | N-A | x86 perf |
| 160 | SVM: No L1 intercepts for un-advertised insn | x86 | N-A | SVM nested |
| 161 | deadlock irq_set_thread_affinity (SVM IRTE) | x86 | N-A | SVM IOMMU |
| 162 | x86: kvm_fpu_get() = fpregs_lock_and_load() | x86 | N-A | x86 fpu |
| 163 | x86/vmx: unit tests for Intel MBEC | x86 | N-A | kvm-unit-tests |
| 164 | x86: Retry guest entry -EBUSY nested_events | x86 | N-A | x86 nested |
| 165 | arm64: gic: Check vGICv3 when clearing TWI | arm | N-A | arm GIC |
| 166 | x86: Merge pending debug causes vectoring #DB | x86 | N-A | x86 调试 |
| 167 | hw/i386/pc: Remove deprecated PC machines | x86 | N-A | QEMU |
| 168 | SVM: Check vCPU ID vs max x2AVIC ID | x86 | N-A | SVM AVIC |
| 169 | VMX: Remove nested_mark_vmcs12_pages_dirty | x86 | N-A | VMX nested |
| 170 | VMX: Don't register PI wakeup if alloc fails | x86 | N-A | VMX posted-int |
| 171 | KVM/arm64 fixes for 6.19 | arm | N-A | arm pull |
| 172 | x86: Mitigate kvm-clock drift masterclock | x86 | N-A | x86 pvclock |
| 173 | x86: SRCU protection KVM_GET_SREGS2 | x86 | N-A | x86 sregs（SRCU 模式通用，riscv 无 SREGS2） |
| 174 | x86,fs/resctrl: GLBE | x86 | N-A | x86 resctrl |
| 175 | x86: Drop WARN INIT/SIPI in Wait-For-SIPI | x86 | N-A | x86 INIT/SIPI |
| 176 | x86: x2APIC EOI broadcast suppression | x86 | N-A | x86 apic |
| 177 | x86: SRCU protection PDPTRs __get_sregs2 | x86 | N-A | x86 sregs |
| 178 | SVM: __read_mostly module params | x86 | N-A | SVM（属性优化价值低） |
| 179 | SVM: __ro_after_init module params | x86 | N-A | SVM（硬化范式价值低） |
| 180 | x86/x2apic: Fix hang on resume s2ram | x86 | N-A | x86 apic |
| 181 | arm64: nv: kvm_phys_size() VNCR range | arm | N-A | arm nested |
| 182 | target/i386: VMX tertiary controls | x86 | N-A | QEMU |
| 183 | x86: Fix SRCU traversal mask_notifiers | x86 | N-A | x86（SRCU 遍历修正，位置 x86） |
| 184 | x86/cpufeatures: AVX512 BMM | x86 | N-A | x86 cpufeature |
| 185 | x86: Advertise AVX512 BMM | x86 | N-A | x86 cpuid |
| 186 | VMX: Drop obsolete branch hint prefixes | x86 | N-A | VMX asm |
| 187 | x86: Optimize kvm_vcpu_on_spin() yield | x86 | **PORTABLE** | 全在通用 `kvm_main.c`；riscv vcpu_insn.c:86 自动受益 |
| 188 | x86: Defer non-arch exception payload | x86 | N-A | x86 异常 |
| 189 | VMX: Fix MSR update add_atomic_switch_msr | x86 | N-A | VMX |
| 190 | i386/kvm: msr_handlers dup (35p) | x86 | N-A | QEMU+机密 |
| 191 | x86: Fix C++ user API VLAs | x86 | N-A | x86 uapi（uapi 卫生范式价值低） |
| 192 | x86: Fix triple faults handling | x86 | N-A | x86 nested |
| 193 | x86: Drop redundant deliver_exception_payload | x86 | N-A | x86 异常 |
| 194 | x86: Fail build if required #define missing | x86 | N-A | 构建断言（范式价值低） |
| 195 | x86: kvm: Init static calls before SMP boot | x86 | N-A | x86 static call |
| 196 | x86: __DECLARE_FLEX_ARRAY() UAPI VLAs | x86 | N-A | x86 uapi |
| 197 | SVM: Propagate TCE to guest | x86 | N-A | SVM EFER |
| 198 | x86: array_index_nospec __pv_send_ipi | x86 | **PATTERN** | Spectre-v1 索引硬化（同#95）→ riscv 索引处 |
| 199 | x86: cmpxchg16b emulation | x86 | N-A | x86 emulate |
| 200 | VMX: Remove unnecessary parentheses | x86 | N-A | trivial |
| 201 | SVM: Advertise TCE to userspace | x86 | N-A | x86 EFER |
| 202 | SVM: helper for LBR field pointer | x86 | N-A | SVM LBR |
| 203 | x86: Syzkaller nested_run_pending defense | x86 | N-A | x86 nested |
| 204 | x86: gfn_to_pfn_cache for record_steal_time | x86 | **PATTERN** | pfncache 通用 → riscv vcpu_sbi_sta.c |
| 205 | x86/split_lock: log guest bus lock exits | x86 | N-A | x86 split-lock |
| 206 | Combined GMET and MBEC tests | x86 | N-A | kvm-unit-tests |
| 207 | Add GDB stub and step-debug (x86+arm64) | x86+arm | **PATTERN** | 测试/调试基架 → kvm-unit-tests riscv + guest-debug 缺口 |
| 208 | x86: Don't leave APF half-enabled | x86 | N-A | x86 async-PF |
| 209 | x86: Async #PF MSR fix and cleanups | x86 | N-A | x86 async-PF |
| 210 | x86: Rate-limit global clock updates | x86 | N-A | x86 pvclock |
| 211 | SVM: Fix page overflow sev_dbg_crypt() | x86 | N-A | SEV |
| 212 | x86: inlines instead of macros is_sev_*guest | x86 | N-A | SEV |
| 213 | VMX: restore host CR2 after VM exit | x86 | N-A | VMX（CR2 x86 专属寄存器） |
| 214 | x86/kvm/vmx: IRQ/NMI dispatch vs hrtimer | x86 | N-A | VMX |
| 215 | x86: Fastpath userspace exit fix | x86 | N-A | x86 fastpath |
| 216 | arm64: Wake-up from WFI userspace irqchip | arm | N-A | arm WFI（用户态 irqchip 唤醒思想相关，价值低） |
| 217 | skip redundant sync IPIs (mmu_gather) | x86 | N-A | 主机 mm TLB，非 KVM |
| 218 | VMX: IRR scan when PIR empty PID.ON | x86 | N-A | VMX posted-int |
| 219 | x86/apic: fix false test failures | x86 | N-A | kvm-unit-tests |
| 220 | x86: Fix max_irr when PIR empty PID.ON | x86 | N-A | x86 apic |
| 221 | x86/cpu: Skip MSR_IA32_PLATFORM_ID virt | x86 | N-A | x86 cpu |
| 222 | x86/virt: RCU lockdep emergency virt cb | x86 | N-A | x86 virt |
| 223 | x86: check nEPT/nNPT slow flush hypercalls | x86 | N-A | x86 nested |
| 224 | x86: Fix/clarify PIR->IRR transfer | x86 | N-A | x86 apic |
| 225 | x86/virt: Silence RCU lockdep splat v2 | x86 | N-A | x86 virt |
| 226 | x86/kvm: Include linux/types.h kvm_para.h | x86 | N-A | x86 头文件 |
| 227 | x86: Fix shadow paging UAF unexpected GFN | x86 | N-A | x86 影子分页 |
| 228 | x86: Swap dst/src operand MOVNTDQA | x86 | N-A | x86 emulate |
| 229 | x86/kvm/vmx: Move IRQ/NMI dispatch (v3) | x86 | N-A | VMX |
| 230 | VMX: module param to disable CET | x86 | N-A | VMX CET |
| 231 | x86: use flush arg of __link_shadow_page | x86 | N-A | x86 影子分页 |
| 232 | x86/microcode: no MSR_IA32_PLATFORM_ID guest | x86 | N-A | x86 microcode |
| 233 | SVM: Fix x2AVIC MSR interception | x86 | N-A | SVM AVIC |
| 234 | SVM: Flush TLB xAVIC=>x2AVIC | x86 | N-A | SVM AVIC |
| 235 | x86: array_index_nospec set_mce | x86 | **PATTERN** | Spectre-v1 索引硬化（同#95）→ riscv 索引处 |
| 236 | SVM: Page Modification Logging (PML) | x86 | N-A | 硬件脏页日志，riscv 无对应 |
| 237 | x86: Fix ERAPS RAP clear INVPCID | x86 | N-A | x86 |
| 238 | x86: Remove unused X86EMUL_MODE_HOST | x86 | N-A | x86 emulate |
| 239 | add minimal tests for 32-bit guests | x86 | N-A | kvm-unit-tests |
| 240 | kvm: rework memory prefault | arm | **PORTABLE** | 通用 `kvm_main.c`+`virt/kvm/Kconfig` PRE_FAULT_MEMORY 重构；riscv 未 select（缺口） |
| 241 | VMX: _safe MSR accessors LBR | x86 | N-A | VMX LBR |
| 242 | VMX: bad values proxied LBR MSR writes | x86 | N-A | VMX LBR |
| 243 | kvm-unit-tests x86 pull | x86 | N-A | 测试 pull |
| 244 | kvm-unit-tests x86 backtraces | x86 | N-A | kvm-unit-tests |
| 245 | x86: Fix return type guest_cpuid_has() | x86 | N-A | x86 cpuid |
| 246 | x86: fls() instead of ffs() rmaps histogram | x86 | N-A | x86 影子分页 stats |
| 247 | SVM: Page modification logging support | x86 | N-A | 硬件脏页日志 |
| 248 | x86: fix #GP check em_dr_write() | x86 | N-A | x86 emulate |
| 249 | x86/lam: test page AREA_LOW | x86 | N-A | kvm-unit-tests |
| 250 | x86: Use <linux/lockdep.h> | x86 | N-A | x86 头文件 |
| 251 | add reserved bit tests 32-bit guests | x86 | N-A | kvm-unit-tests |
| 252 | arm64: kvm_for_each_vncr_tlb() helper | arm | N-A | arm nested |
| 253 | arm64: mmu_lock while init vncr_tlb | arm | N-A | arm nested |
| 254 | x86/msr: rid rdmsrl()/wrmsrl() | x86 | N-A | x86 msr |
| 255 | x86: IDT limit check __emulate_int_real() | x86 | N-A | x86 emulate |
| 256 | x86: MCE fixes | x86 | N-A | x86 MCE（含#235 nospec，已单列） |
| 257 | VMX: KVM_REQ_EVENT on TPR below threshold | x86 | N-A | VMX apic |
| 258 | x86: recompute CR8 intercept PPR update | x86 | N-A | x86 apic |
| 259 | x86: Fix emulated MOV DR{4,5} #GP (8p) | x86 | N-A | x86 emulate/调试 |
| 260 | target/i386/kvm: CET SSP MSR check | x86 | N-A | QEMU |
| 261 | linux-6.1.y build errors GCC/glibc | x86 | N-A | 构建 |
| 262 | VMX: vmread_error_trampoline uncallable C | x86 | N-A | VMX |
| 263 | SVM: Remove redundant ret=0 set_nested_state | x86 | N-A | SVM nested |
| 264 | x86: WARN RTC pending EOI off rails | x86 | N-A | x86 apic |
| 265 | x86: Bug the VM not kernel ISR count | x86 | N-A | x86 apic（KVM_BUG_ON 哲学通用，价值低） |
| 266 | x86: Drop WARN_ON_ONCE disappearing irq | x86 | N-A | x86 apic |
| 267 | SVM: handle wraparound asid_generation | x86 | N-A | SVM ASID |
| 268 | Add running protected VMs on arm64 (kvmtool) | arm | N-A | kvmtool pKVM |
| 269 | x86: Fix shadow paging UAF unexpected role | x86 | N-A | x86 影子分页 |
| 270 | x86/msr: Drop 32-bit MSR interfaces | x86 | N-A | x86 msr |
| 271 | VMX: cached vcpu_vmx pointer helpers | x86 | N-A | VMX |
| 272 | SVM: Add Bus Lock Detect support | x86 | N-A | SVM |
| 273 | mm: page allocator APIs cleanup (VMX) | x86 | N-A | mm 通用 + VMX 适配（非可移植 KVM 逻辑） |
| 274 | Add cmpxchg16b emulation | x86 | N-A | x86 emulate+uaccess |
| 275 | KVM: s390: Introduce arm64 KVM (27p) | arm | **PORTABLE** | 通用子集：Remove KVM_MMIO config / device name / VFIO refcount（触 riscv Kconfig）；余 N-A |
| 276 | x86: Document/enforce APIC base memory hole | x86 | N-A | x86 apic |
| 277 | module: Limit ELF includes module.h | x86 | N-A | 内核构建 |
| 278 | arm64: Fix TLBI level stage2_relax_perms | arm | N-A | arm stage2 |
| 279 | Add AMD IOMMU GAPPI support | x86 | N-A | SVM IOMMU posted-int |
| 280 | x86: Document APIC base memory hole | x86 | N-A | x86 doc |
| 281 | SVM: Do not warn on IGNNE MSR write | x86 | N-A | SVM |
| 282 | x86: Remove AMX-TF32 enumeration | x86 | N-A | x86 cpuid |

## 判定纪律说明

- **未把 riscv 已有误报为可移植**：#56（`kvm_lock_all_vcpus`）经本地源码确认已合并且 riscv 已调用（`aia_device.c:30`）→ 判 ALREADY；#75 为 riscv 原生补丁 → ALREADY。
- **未把纯硬件拔高**：PML(#236/#247)、AVIC/x2AVIC、posted-int/PIR、L1TF/CET/SEV/TDX、GIC/nested/arm-sysreg 一律 N-A。
- **通用底座部分单列**：#115（patch1 通用 / patch2 x86）、#275（通用 KVM/VFIO 子集 / 架构头共享 N-A）均已注明「仅通用部分 PORTABLE」。
- **弱范式降级为 N-A + 备注**：`__free()`/`guard()`/`memdup_user()`/`__ro_after_init`/SRCU 保护/KVM_BUG_ON 等通用编码范式因落点为 x86 专属且价值低，判 N-A 并附一句说明，不虚增 PATTERN 计数。
