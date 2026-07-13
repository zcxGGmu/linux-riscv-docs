# Tier C — in-kernel 中断控制器硬件 (irqchip-hw) 可移植性分析

> 输入：`kvm-riscv/data/by_category/C_irqchip-hw.jsonl`（74 条系列）
> 判定依据：`_baseline_riscv.md` / `_taxonomy.md` + 本地内核树 `/Users/zq/Desktop/patch-work/linux-riscv`
> 基调：APIC/AVIC/IOAPIC（x86）与 VGIC/ITS/GICv3-5（arm64）内部实现 riscv 无对应（riscv 用 AIA=APLIC+IMSIC，自成体系）→ 绝大多数 **N-A**。真正价值集中在 **IRQ-bypass / 直接注入** 一族（映射 IMSIC VS-file 直注），以及少数被误归入本类的 **通用层 (virt/kvm/\*)** 系列。

## 摘要

- **系列总数：74**
- **四态计数：ALREADY 0 / PORTABLE 3 / PATTERN 5 / N-A 66**
  - PORTABLE 与 PATTERN 均为「本类被误分类的通用系列」或「机制可复用」候选；纯 GIC/APIC/AVIC/VMX/x86-debug 寄存器模拟一律 N-A。

### 本类 Top 候选（按价值排序）

| # | 系列 | 判定 | riscv 落点 |
|---|---|---|---|
| 1 | KVM: x86: Add a module param for device posted IRQs | **PATTERN** | `aia.c` + `aia_imsic.c`（新增 irq_bypass 生产者/消费者钩子） |
| 2 | KVM: arm64: Set/unset vGIC v4 forwarding if direct IRQs are supported | **PATTERN** | `aia_imsic.c`（VS-file 转发 set/unset + 直注能力门控） |
| 3 | KVM: arm64: Allow vGICv4 configuration per VM | **PATTERN** | `aia_device.c`（新增 `KVM_DEV_RISCV_AIA_CONFIG_*` 直注开关属性） |
| 4 | KVM: Speed up MMIO registrations（patch 3-4） | **PORTABLE** | 通用 `virt/kvm/kvm_main.c`（kvm_io_bus SRCU）自动生效 |
| 5 | KVM: kvm_set_memory_region() cleanups | **PORTABLE** | 通用 `virt/kvm/kvm_main.c` memslot API 自动生效 |
| 6 | KVM: Add arch hooks for KVM syscore ops（patch 1） | **PORTABLE** | 通用 syscore 钩子；riscv 可 opt-in 实现 |
| 7 | sched/fair, KVM: Semantics-aware directed yield (v3) | **PATTERN** | sched/ 通用底座 + riscv 侧 IPI 跟踪（`aia*` / vcpu spin 路径） |

**核心发现（IMSIC 直注缺口）**：riscv **未 select `HAVE_KVM_IRQ_BYPASS`**（`arch/riscv/` 全树 0 命中），`aia.c`/`aia_imsic.c` **无任何** `kvm_arch_irq_bypass_*`/IRTE 等价钩子。但通用底座 `virt/lib/irqbypass.c` 与 `virt/kvm/eventfd.c`（弱符号 `kvm_arch_irq_bypass_stop/start`、`kvm_arch_has_irq_bypass()`）已就位，且 **IMSIC 已实现 VS-file 硬件直注后端**（`vsfile_cpu/vsfile_hgei`、HWACCEL 模式）。→ 缺的只是「把 VFIO 透传设备 MSI 直接落到 guest IMSIC VS-file」的架构钩子，这正是本类 #1/#2/#3 三条 arm64/x86 补丁揭示的机制。

---

## Top 可移植候选（深度）

### 1. KVM: x86: Add a module param for device posted IRQs —— **PATTERN**
- **原补丁**：`KVM: x86: Add a module param for device posted IRQs`（<https://patchwork.kernel.org/project/kvm/patch/20250401161804.842968-3-seanjc@google.com/>）状态=new，3 patches
- **可移植点**：IRQ-bypass / posted-interrupt 的 **通用控制骨架**。curl 确认 diff 引入 `kvm_arch_has_irq_bypass()` 门控与 `avic_pi_update_irte()` 的 `!kvm_arch_has_assigned_device() || !kvm_arch_has_irq_bypass()` 早退；并加模块参数枚举「设备 posted IRQ」能力。x86 用 IRTE、arm64 用 vLPI 映射，riscv 对应「把透传设备 MSI 重定向到 guest IMSIC VS-file」。
- **riscv 落点**：`arch/riscv/kvm/aia.c`（新增 `kvm_arch_irq_bypass_add_producer/del_producer/stop/start` 与 `kvm_arch_has_irq_bypass()`，Kconfig `select HAVE_KVM_IRQ_BYPASS`）+ `aia_imsic.c`（把 producer 的 host IRQ 亲和/MSI 地址落到 `imsic->vsfile_pa`）。依据：`eventfd.c:490-492` 已用弱钩子等待架构实现；riscv 侧现为 0 命中（已 grep 确认）。
- **判定**：**PATTERN** —— 通用底座与 IMSIC 直注后端都在，仅需补架构钩子，机制与 x86/arm64 同构。

### 2. KVM: arm64: Set/unset vGIC v4 forwarding if direct IRQs are supported —— **PATTERN**
- **原补丁**：`KVM: arm64: Set/unset vGIC v4 forwarding if direct IRQs are supported`（<https://patchwork.kernel.org/project/kvm/patch/20250728223710.129440-1-rananta@google.com/>）状态=new，1 patch
- **可移植点**：curl 全文暴露了 arm64 直注的**完整调用链**——`kvm_arch_irq_bypass_add_producer → irq_bypass_register_producer → kvm_vgic_v4_set_forwarding → its_map_vlpi`，以及用 `vgic_supports_direct_irqs(kvm)` 门控 set/unset。这就是 riscv 需要照搬的「透传设备中断转发到 hypervisor 直注文件」范式：riscv 侧对应 `kvm_riscv_aia_imsic_*` 把 host MSI 转发绑定到 `vsfile_hgei`。
- **riscv 落点**：`arch/riscv/kvm/aia_imsic.c`（新增 `..._set/unset_forwarding()`，复用 `imsic_vsfile_local_*`/`vsfile_pa`）+ 直注能力探测函数（对应 `vgic_supports_direct_irqs`，依据 IMSIC HWACCEL 是否可用即 `vsfile_cpu >= 0`）。
- **判定**：**PATTERN** —— 调用链清晰、IMSIC 已有 VS-file 后端，最高价值参考实现。

### 3. KVM: arm64: Allow vGICv4 configuration per VM —— **PATTERN**
- **原补丁**：`KVM: arm64: Allow vGICv4 configuration per VM`（<https://patchwork.kernel.org/project/kvm/patch/20250514192159.1751538-4-rananta@google.com/>）状态=new，3 patches
- **可移植点**：per-VM 直注开关。curl 确认新增 `KVM_DEV_ARM_VGIC_CONFIG_GICV4` 设备属性（UNAVAILABLE/DISABLE/ENABLE，须在 vGIC init 前设置），并配 selftest。riscv 已有对称的 `KVM_DEV_RISCV_AIA_CONFIG_*` 属性框架（`aia_device.c:57-151`，含 MODE/IDS/GROUP_BITS 等，且有 `kvm_riscv_aia_initialized()` 的 init-前后写保护），天然适配再加一个「直注模式」开关。
- **riscv 落点**：`arch/riscv/kvm/aia_device.c`（`aia_config()` 增 `KVM_DEV_RISCV_AIA_CONFIG_DIRECT_INJECT` 分支；`KVM_DEV_RISCV_AIA_CONFIG_MODE` 已区分 IMSIC 模式，可复用）。
- **判定**：**PATTERN** —— 属性框架已在，仅需增一枚开关 + 与 #1/#2 的钩子联动。

### 4. KVM: Speed up MMIO registrations —— **PORTABLE**（仅 patch 3-4）
- **原补丁**：`KVM: Speed up MMIO registrations`（<https://patchwork.kernel.org/project/kvm/patch/20250909100007.3136249-2-keirf@google.com/>）状态=new，4 patches
- **可移植点**：patch 3「Implement barriers before accessing kvm->buses[] on SRCU read paths」+ patch 4「Avoid synchronize_srcu() in kvm_io_bus_register_dev()」改的是**通用 `virt/kvm/kvm_main.c` 的 kvm_io_bus**，去掉设备注册热路径上的 `synchronize_srcu()`，对所有架构（含 riscv 的 MMIO/ioeventfd 注册）一次性提速。patch 1-2（`vgic_ready` 宏/顺序）为 arm 专属 → 那两条 N-A。
- **riscv 落点**：无需 riscv 侧改动，`virt/kvm/kvm_main.c` 合入即自动惠及 riscv（riscv 用同一 kvm_io_bus）。
- **判定**：**PORTABLE**（Tier A 通用，误归入本类）。

### 5. KVM: kvm_set_memory_region() cleanups —— **PORTABLE**
- **原补丁**：`KVM: kvm_set_memory_region() cleanups`（<https://patchwork.kernel.org/project/kvm/patch/20250111002022.1230573-6-seanjc@google.com/>）状态=new，5 patches
- **可移植点**：纯通用 memslot API 重构——open-code `kvm_set_memory_region()`、断言 `slots_lock`、新增 KVM-internal memslot 专用 API、禁止 internal memslot 使用 flags。全部落在 `virt/kvm/kvm_main.c` 的通用 memory-region 路径，riscv G-stage 走同一入口。
- **riscv 落点**：无需 riscv 侧改动，通用层合入即生效（riscv `mmu.c`/`gstage.c` 经 `kvm_set_memory_region` 通用入口受益）。
- **判定**：**PORTABLE**（Tier A 通用，误归入本类；标题带「x86」仅因作者与 4/5 补丁位置）。

### 6. KVM: Add arch hooks for KVM syscore ops —— **PORTABLE**（仅 patch 1）
- **原补丁**：`[RFC] KVM: Add arch hooks for KVM syscore ops`（<https://patchwork.kernel.org/project/kvm/patch/20250623132714.965474-1-dwmw2@infradead.org/>）状态=new，2 patches
- **可移植点**：patch 1 在通用 KVM 增加架构 syscore（suspend/resume/shutdown）回调钩子，属通用底座扩展，任意架构可 opt-in。patch 2「vgic-its: Unmap all vPEs on shutdown」为 ITS 专属 → N-A。
- **riscv 落点**：通用钩子随合入可用；riscv 如需在系统挂起/关机时处理 AIA 状态可在 `aia.c` 实现该 arch 钩子（当前非必需）。
- **判定**：**PORTABLE**（通用钩子）；ITS 用例 N-A。

### 7. sched/fair, KVM: Semantics-aware directed yield for oversubscribed KVM (v3) —— **PATTERN**
- **原补丁**：`sched/fair, KVM: Semantics-aware directed yield for oversubscribed KVM`（<https://patchwork.kernel.org/project/kvm/patch/20260612013355.59231-8-kernellwp@gmail.com/>）状态=new，10 patches（v2 见 <https://patchwork.kernel.org/project/kvm/patch/20251219035334.39790-10-kernellwp@gmail.com/>，9 patches）
- **可移植点**：sched/fair 的 EEVDF lag-credit / next-buddy / `yield_to_task_fair()` deboost 为**核心调度器通用改动**（所有架构自动受益）；KVM 侧「IPI tracking infrastructure for directed yield」是架构使能点——记录 vCPU 间 IPI 以在 PLE/spin 时选更优 yield 目标。riscv 可在 AIA/SBI-IPI 路径复刻 IPI 跟踪，喂给通用 directed-yield。
- **riscv 落点**：通用 sched/ 部分无需 riscv 改动；IPI 跟踪落 `arch/riscv/kvm/`（`aia*.c` 或 SBI IPI 处理 + `kvm_vcpu_on_spin` 目标选择路径）。
- **判定**：**PATTERN** —— 通用底座直接受益，架构使能部分需 riscv 侧小幅重写。

---

## 全量判定表（覆盖 74 条）

| # | 系列 | arch | 判定 | 可移植点 / 理由 | riscv 落点 | web_url |
|---|---|---|---|---|---|---|
| 1 | KVM: kvm_set_memory_region() cleanups | x86 | **PORTABLE** | 通用 memslot API 重构 | virt/kvm/kvm_main.c（自动） | 20250111002022.1230573-6 |
| 2 | arm64: support poll_idle() | arm | **PATTERN**(弱) | ARCH_HAS_OPTIMIZED_POLL 移入 arch/Kconfig（通用）+ poll_idle；KVM halt-polling 相关 | arch/riscv（TIF_POLLING_NRFLAG+poll_idle，非 kvm/） | 20250218213337.377987-12 |
| 3 | KVM: SVM: 4096 vcpus with x2AVIC | x86 | N-A | AVIC 物理 ID 表扩展，纯 SVM 硬件 | — | 330d10700c1172982bcb7947a37c0351f7b50958 |
| 4 | KVM: x86: ioapic: Optimize EOI handling | x86 | N-A | IOAPIC EOI 减 VM-exit，riscv 无 IOAPIC | — | 20250303052227.523411-1 |
| 5 | KVM: x86: Add module param for device posted IRQs | x86 | **PATTERN** | IRQ-bypass/posted-intr 控制骨架 + `kvm_arch_has_irq_bypass()` | aia.c + aia_imsic.c | 20250401161804.842968-3 |
| 6 | KVM: arm64: Allow vGICv4 configuration per VM | arm | **PATTERN** | per-VM 直注开关属性 | aia_device.c（新 CONFIG 属性） | 20250514192159.1751538-4 |
| 7 | x86/traps: Fix DR6/DR7 inintialization | x86 | N-A | x86 调试寄存器复位值 | — | 20250613070118.3694407-2 |
| 8 | KVM: arm64: control GICD_TYPER2.nASSGIcap | arm | N-A | GIC 分发器 vSGI 能力位 | — | 20250613155239.2029059-2 |
| 9 | kvm/arm: trap-me-harder implementation | arm | N-A | QEMU + out-of-kernel GICv3 + CP-reg 全陷入 | — | 20250617163351.2640572-12 |
| 10 | x86/traps: Fix DR6/DR7 initialization (v3) | x86 | N-A | 同 #7 | — | 20250618172723.1651465-2 |
| 11 | Fix DR6/DR7 initialization (v4) | x86 | N-A | 同 #7 | — | 20250620231504.2676902-2 |
| 12 | KVM: Add arch hooks for KVM syscore ops | arm | **PORTABLE** | patch1 通用 syscore 钩子；patch2(ITS vPE) N-A | 通用；aia.c 可 opt-in | 20250623132714.965474-1 |
| 13 | KVM: SVM: Enable AVIC by default from Zen 4 | x86 | N-A | AVIC 默认开启 | — | 20250626145122.2228258-1 |
| 14 | KVM: arm64: GICv3-on-GICv5 FEAT_GCIE_LEGACY | arm | N-A | GICv5 主机兼容 GICv3 客户机 | — | 20250627100847.1022515-4 |
| 15 | KVM: x86/mmu: TDP MMU NX huge page recovery under read lock | x86 | N-A | x86 iTLB-multihit NX-hugepage 缓解，属 mmu-stage2 且 riscv 无此缓解 | (mmu 组) | 20250707224720.4016504-8 |
| 16 | KVM: arm64: nv: Userspace register visibility fixes | arm | N-A | 嵌套 + GICv3 EL2 寄存器可见性 | — | 20250714122634.3334816-2 |
| 17 | KVM: arm64: Userspace GICv3 sysreg access fixes | arm | N-A | GICv3 系统寄存器访问/排序 | — | 20250718111154.104029-2 |
| 18 | arch/x86/kvm/ioapic: Remove license boilerplate | x86 | N-A | 许可证样板清理（IOAPIC 文件） | — | 20250728152843.310260-1 |
| 19 | KVM: arm64: Set/unset vGIC v4 forwarding if direct IRQs | arm | **PATTERN** | 直注转发完整调用链 + 能力门控 | aia_imsic.c（VS-file 转发） | 20250728223710.129440-1 |
| 20 | KVM: x86: Clean up lowest priority IRQ code | x86 | N-A | x86 APIC lowest-priority/vector-hashing 投递 | — | 20250821214209.3463350-4 |
| 21 | KVM: SVM: Fix LAPIC TPR sync into VMCB::V_TPR (AVIC) | x86 | N-A | AVIC/VMCB TPR 同步 | — | a5efbf76990d023c7cf21c5a4c170f4ad0234d85 |
| 22 | KVM: SVM: Enable AVIC by default on Zen 4+ | x86 | N-A | AVIC 默认开启 | — | 46b11506a6cf566fd55d3427020c0efea13bfc6a |
| 23 | KVM: SVM: 4k vCPUs with x2AVIC | x86 | N-A | AVIC 物理 ID 上限扩展 | — | e5c9c471ab99a130bf9b728b77050ab308cf8624 |
| 24 | KVM: Speed up MMIO registrations | arm | **PORTABLE** | patch3-4 通用 kvm_io_bus 去 synchronize_srcu；patch1-2(vgic) N-A | virt/kvm/kvm_main.c（自动） | 20250909100007.3136249-2 |
| 25 | x86/boot,KVM: Move VMXON/VMXOFF to CPU lifecycle | x86 | N-A | VMX 世界开关生命周期；`kvm_rebooting` 删除亦为 VMX 驱动 | — | 20250909182828.1542362-6 |
| 26 | KVM: x86: skip userspace IOAPIC EOI (Directed EOI) | x86 | N-A | IOAPIC Directed-EOI | — | 20250918162529.640943-1 |
| 27 | KVM: Export KVM-internal symbols for sub-modules | x86 | N-A | 子模块符号导出收敛（riscv KVM 单体，无 kvm-intel/amd 分模块）；`kvm_is_gpa_in_memslot` 通用助手随之可用 | 通用助手已在 | 20250919003303.1355064-4 |
| 28 | arm64/sysreg: Feat descriptor + ICH_VMCR_EL2 | arm | N-A | arm64 sysreg 生成（GIC ICH_VMCR_EL2） | — | 20251007153505.1606208-3 |
| 29 | Documentation: GICv3 docs for GICv5 hosts | arm | N-A | GIC 文档 | — | 20251007154848.1640444-1 |
| 30 | KVM: arm64: gic-v3: ICH_HCR traps for v2-on-v3/v3 | arm | N-A | GIC 陷入配置 | — | 20251007160704.1673584-1 |
| 31 | KVM: SVM: Unregister GALog notifier on module exit | x86 | N-A | AVIC GA-Log 通知器 | — | 20251016190643.80529-4 |
| 32 | KVM: arm64: vgic-v3: Trap all if no in-kernel irqchip | arm | N-A | GIC 陷入（弱：userspace-irqchip 全陷入思路，arm 专属） | — | 20251021094358.1963807-1 |
| 33 | arm64/sysreg: Prefix descriptor + ICH_VMCR_EL2 | arm | N-A | arm64 sysreg 生成 | — | 20251022134526.2735399-5 |
| 34 | KVM: arm64: Fix handling of ID_PFR1_EL1.GIC | arm | N-A | ID 寄存器 GIC 字段 | — | 20251030122707.2033690-2 |
| 35 | KVM: x86: Fix an FPU+CET splat | x86 | N-A | x86 FPU/CET load/put 加固（riscv FP/vector 另有惰性实现） | — | 20251030185802.3375059-3 |
| 36 | KVM: arm64: Add LR overflow infrastructure (v2,45) | arm | N-A | GICv3 List-Register 溢出 | — | 20251109171619.1507205-20 |
| 37 | KVM: VMX: configure SVI during runtime APICv activation | x86 | N-A | VMX APICv SVI | — | 20251110063212.34902-1 |
| 38 | KVM: arm64: GICv3: Check impl before ICH_VTR_EL2 | arm | N-A | GIC 寄存器访问守卫 | — | 20251113172524.2795158-1 |
| 39 | KVM: arm64: GICv3: Don't advertise ICH_HCR_EL2.En==1 | arm | N-A | GIC 能力广告 | — | 20251114093541.3216162-1 |
| 40 | KVM: arm64: LR overflow infra (v3,dregs) | arm | N-A | GIC LR 溢出 | — | 20251117091527.1119213-6 |
| 41 | KVM: arm64: LR overflow infra (v4,49) | arm | N-A | GIC LR 溢出 | — | 20251120172540.2267180-21 |
| 42 | KVM: x86: APIC and I/O APIC cleanups | x86 | N-A | x86 APIC/IOAPIC 内部加固（弱：guest-triggerable ASSERT→WARN_ON_ONCE/clamp 防御思路） | — | 20251206004311.479939-2 |
| 43 | Enable GICv5 Legacy CPUIF trapping & TDIR cap | arm | N-A | GICv5 主机陷入 | — | 20251208152724.3637157-4 |
| 44 | sched/kvm: Semantics-aware vCPU scheduling (v2) | x86 | **PATTERN** | 见 #66（同主题 v2） | sched/(通用)+riscv IPI 跟踪 | 20251219035334.39790-10 |
| 45 | WHPX support for Arm | arm | N-A | QEMU Windows Hypervisor Platform（用户态） | — | 20251228235422.30383-17 |
| 46 | KVM: SVM: Fix off-by-one typo in AVIC comment | x86 | N-A | 注释 typo | — | 20260109035037.1015073-1 |
| 47 | arm64: Support GICv5-based guests (kvmtool) | arm | N-A | kvmtool GICv5 | — | 20260116182606.61856-12 |
| 48 | KVM: x86: Userspace control for Suppress EOI Broadcast | x86 | N-A | x2APIC/IOAPIC EOI 广播抑制 | — | 20251229111708.59402-2 |
| 49 | KVM: arm64: Standardize debugfs iterators | arm | N-A | vgic-debug/idreg debugfs seq_file 迭代器（弱：debugfs 迭代器清理范式，riscv KVM debugfs 极简） | — | 20260202085721.3954942-3 |
| 50 | KVM: SVM: Fix CR8 interception woes with AVIC | x86 | N-A | AVIC CR8 拦截 | — | 20260203190711.458413-3 |
| 51 | KVM: x86: AMD Extended APIC registers | x86 | N-A | 扩展 APIC；弱：`KVM_CAP_LAPIC2`+变长状态 ioctl(`KVM_GET/SET_LAPIC2`) 版本化范式可借鉴 | — | 20260204074452.55453-10 |
| 52 | i386/kvm: extended APIC register space | x86 | N-A | QEMU 侧扩展 APIC | — | 20260219054207.471303-8 |
| 53 | irqchip/gic-v5: Fix IRS_IDR0.virt flag inversion | arm | N-A | GICv5 irqchip 驱动修复 | — | 20260225083130.3378490-1 |
| 54 | KVM: x86: Fix UBSAN bool warnings in module params | x86 | N-A | avic/nx_huge_pages bool 参数读取（弱：通用 bugfix 范式，内容 x86） | — | 20260225145050.2350278-2 |
| 55 | KVM: x86: Add LAPIC guard in kvm_apic_write_nodecode() | x86 | N-A | LAPIC 写守卫 | — | tencent_7A9F1B4D75468C0CF5DE1B6902038C948B07 |
| 56 | KVM: arm64: Introduce vGIC-v5 with PPI support (v7,41) | arm | N-A | vGICv5 PPI | — | 20260319154937.3619520-8 |
| 57 | KVM: arm64: First batch of vgic-v5 fixes (16) | arm | N-A | vGICv5 修复 | — | 20260401103611.357092-3 |
| 58 | KVM: arm64: vgic-v5: Fold PPI state | arm | N-A | vGICv5 PPI 状态 | — | 20260401162152.932243-1 |
| 59 | KVM: arm64: vgic: Fix IIDR revision + revision 1 | arm | N-A | vgic IIDR 寄存器 | — | 20260408113256.2095505-4 |
| 60 | KVM: arm64: vgic: Skip vCPU trylock pre-init | arm | N-A | vgic 锁（弱：pre-init 免 trylock 微范式） | — | 6564c8b967948e30a8d3f35b6ef5de79dd5feeb7 |
| 61 | KVM: arm64: vgic: Fix IGROUPR writability + IIDR | arm | N-A | vgic 寄存器可写性 | — | 20260511113558.3325004-3 |
| 62 | KVM: SVM: Disable AVIC IPI virt on Hygon 18h | x86 | N-A | AVIC 勘误规避 | — | 20260522040014.3380201-1 |
| 63 | KVM: x86: ioapic: Use old_dest_mode consistently | x86 | N-A | IOAPIC 写路径修复 | — | 20260528031624.1929-1 |
| 64 | GiantVM based on shared memory | x86 | N-A | 分布式 VM 转发 LAPIC ICR/APIC 到用户态（研究，x86 LAPIC） | — | 20260605100031.834938-4 |
| 65 | KVM: SVM: Clear dummy V_IRQ in vmcb01 (AVIC off) | x86 | N-A | AVIC/VMCB V_IRQ | — | 20260610070512.85463-1 |
| 66 | sched/fair,KVM: Semantics-aware directed yield (v3) | x86 | **PATTERN** | sched/fair EEVDF lag-credit(通用)+KVM IPI 跟踪使能 directed-yield | sched/(通用)+riscv IPI 跟踪 | 20260612013355.59231-8 |
| 67 | x86/apic:KVM: Use cpu_physical_id() for AVIC | x86 | N-A | AVIC APIC-ID 获取 | — | 20260612185459.591892-1 |
| 68 | KVM: arm64: Race between affinity change and LPI disable | arm | N-A | GIC LPI 竞态修复 | — | 20260615181625.3029352-1 |
| 69 | KVM: x86: Clamp EOI vector if OOB instead of bugging | x86 | N-A | APIC EOI 加固（弱：clamp 代替 BUG 防御思路） | — | 20260618185515.2021642-1 |
| 70 | KVM: VMX: Update SVI during runtime APICv (6.6.y) | x86 | N-A | VMX APICv 回移 | — | 20260622100324.65288-1 |
| 71 | KVM: x86: Spring cleaning, part 2 | x86 | N-A | x86 头文件/宏迁移清理 | — | 20260625220450.3354415-4 |
| 72 | KVM: SVM: Fix unlikely UAF for GA Log IRQs | x86 | N-A | AVIC GA-Log 生命周期 UAF | — | 20260630210156.457151-2 |
| 73 | KVM: arm64: Add GICv5 IRS support (v3,40) | arm | N-A | GICv5 IRS | — | 20260703154811.3355680-26 |
| 74 | KVM: x86/ioapic: Cancel eoi_inject work before vCPU destroy | x86 | N-A | IOAPIC 拆除顺序 UAF 修复（弱：销毁 vCPU 前取消延迟工作的生命周期范式） | — | 20260705050443.1331662-1 |

> web_url 列为 patchwork message-id 片段；完整地址 = `https://patchwork.kernel.org/project/kvm/patch/<片段>@.../`（PORTABLE/PATTERN 行已在上方深度小节给出完整 URL）。

---

## 结论

本类 74 条中 **66 条 N-A**：GIC/VGIC/ITS/GICv3-5、APIC/AVIC/x2AVIC/IOAPIC、VMX/SVM 世界切换、x86 DR6/DR7 与 FPU/CET 等，均为 riscv 无对应的宿主硬件寄存器模拟或勘误规避，且不扩展通用底座。

**真正价值有二**：
1. **IRQ-bypass / IMSIC 直接注入（#5 x86 posted-IRQ、#19 arm64 v4 转发、#6 arm64 per-VM 配置）** —— 三条揭示了「透传设备中断绕过 hypervisor、直落 guest 中断文件」的完整通用机制（`irq_bypass_register_producer` ↔ `kvm_arch_irq_bypass_add_producer` ↔ 架构 map/forward）。riscv 通用底座（`virt/lib/irqbypass.c`、`eventfd.c` 弱钩子）与 IMSIC VS-file 硬件直注后端均已就位，**唯缺 `arch/riscv/kvm/aia.c` 的架构钩子与 `HAVE_KVM_IRQ_BYPASS` select**——这是本类最高价值、落点最明确的移植方向，与基线缺口 #4 完全吻合。
2. **被误分类的通用系列（#1 memslot API、#24 kvm_io_bus SRCU、#12 syscore 钩子）** —— 属 `virt/kvm/*` Tier A，合入即惠及 riscv，无需架构改动。

外加 **directed-yield（#44/#66）** 与 **poll_idle（#2）** 两条以通用/核心层为主、riscv 侧仅需小幅使能的 PATTERN。
