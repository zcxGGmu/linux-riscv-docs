# KVM 特性分类法与可移植性层级

> 来源：对 `arch/x86/kvm/`、`arch/arm64/kvm/`、`virt/kvm/`、`tools/testing/selftests/kvm/` 的源码盘点。
> 用途：把 x86/arm 补丁归入三层级，决定分析深度与移植判定基调。

## 三层级定义

- **Tier A — GENERIC（通用层）**：代码位于 `virt/kvm/*` 或属架构无关逻辑。改动通常对所有架构（含 riscv）一次性生效。→ 判定基调多为 PORTABLE。
- **Tier B — PATTERN-PORTABLE（模式可移植）**：架构专属实现，但**机制/思想**可复用，需在 riscv 侧重写。→ 判定基调多为 PATTERN。
- **Tier C — HW-SPECIFIC（硬件专属）**：依赖 x86/arm 特有硬件，riscv 暂无对应。→ 判定基调多为 N-A，仅当扩展了通用底座时才计入。

## 类别 → 层级映射

| 类别 | 层级 | x86/arm 代表文件 | riscv 落点 |
|---|---|---|---|
| core（生命周期/ioctl/CAP） | A | `virt/kvm/kvm_main.c` | 自动适用 |
| mmu-stage2（页表/大页/split/dirty-log） | B | `x86/kvm/mmu/tdp_mmu.c`, `arm64/kvm/mmu.c`+`hyp/pgtable.c` | `gstage.c` `mmu.c` |
| guest_memfd（私有内存/内存属性） | A | `virt/kvm/guest_memfd.c` | 新 Kconfig+钩子 |
| dirty-ring | A | `virt/kvm/dirty_ring.c` | 已有 |
| io-irq-infra（irqfd/ioeventfd/routing/bypass） | A | `virt/kvm/eventfd.c`,`coalesced_mmio.c` | 通用 + `aia*.c` |
| stats（binary stats） | A | `virt/kvm/binary_stats.c` | 已有 |
| reg-access（ONE_REG/sys_reg/cpuid） | B | `arm64/kvm/sys_regs.c`, `x86/kvm/cpuid.c` | `vcpu_onereg.c` `isa.c` |
| pmu | B | `x86/kvm/pmu.c`, `arm64/kvm/pmu-emul.c` | `vcpu_pmu.c` |
| timer-clock | B | `arm64/kvm/arch_timer.c`, x86 lapic/kvmclock | `vcpu_timer.c` |
| pv-hypercall（steal-time/psci/async_pf） | B | `arm64/kvm/pvtime.c`, `virt/kvm/async_pf.c` | `vcpu_sbi_*.c` |
| mmio-insn（退出/解码） | B | `arm64/kvm/mmio.c`, `x86/kvm/emulate.c`※ | `vcpu_insn.c` `vcpu_exit.c` |
| debug-introspect（ptdump/debugfs/guest-debug） | B | `arm64/kvm/ptdump.c`,`debug.c`, `x86/kvm/debugfs.c` | 新增 |
| selftests | B/A | `selftests/kvm/lib/*` + 通用测试 | `selftests/kvm/riscv` |
| irqchip-hw（APIC/AVIC/VGIC/ITS 内部） | C | `x86/kvm/lapic.c`, `arm64/kvm/vgic/` | 无（AIA 自成体系） |
| hw-virt-engine（VMX/SVM/hyp switch） | C | `x86/kvm/vmx/`,`svm/`, `arm64/kvm/hyp/` | 无 |
| nested | C | `x86/kvm/vmx/nested.c`, `arm64/kvm/nested.c` | 无 |
| confidential（TDX/SEV/pKVM/CCA） | C | `x86/kvm/vmx/tdx.c`,`svm/sev.c`, `arm64/kvm/pkvm.c` | 无（仅 gmem 底座可移） |
| vendor-enlighten（Hyper-V/Xen） | C | `x86/kvm/hyperv.c`,`xen.c` | 无 |
| x86-legacy（SMM/MTRR/PIT） | C | `x86/kvm/smm.c`,`mtrr.c` | 无 |

※ x86 全指令软件模拟器 `emulate.c` 无 riscv 对应（riscv 只需轻量 MMIO 解码）。

## 跨架构机制（历来 x86/arm 先行、后移植到 riscv）

| 机制 | 通用/架构文件 | riscv 状态 |
|---|---|---|
| dirty ring | `virt/kvm/dirty_ring.c` | ✅ 已有 |
| guest_memfd / gmem | `virt/kvm/guest_memfd.c` | ❌ 未有（arm64 已 select） |
| 内存属性 | `virt/kvm/kvm_main.c`（`KVM_GENERIC_MEMORY_ATTRIBUTES`） | ❌ 未有 |
| mmu_notifier / gfn-range 失效 | `virt/kvm/kvm_main.c` | ✅ 通用适用 |
| 大页 eager split / dirty-log 性能 | `arm64/kvm/mmu.c`+`hyp/pgtable.c`; `x86/kvm/mmu/tdp_mmu.c` | ⚠️ 思想可移到 `gstage.c` |
| binary stats | `virt/kvm/binary_stats.c` | ✅ 通用 |
| ONE_REG 管线 | `arm64/kvm/guest.c`+`sys_regs.c` | ✅ 已有 |
| KVM_CAP 协商模式 | `virt/kvm/kvm_main.c` | ✅ 通用 |
| selftest lib 增量 | `selftests/kvm/lib/kvm_util.c` | ⚠️ riscv 目录存在但滞后 |
| coalesced PIO/MMIO | `virt/kvm/coalesced_mmio.c` | ✅ 通用 |
| pfncache | `virt/kvm/pfncache.c` | ✅ 通用 |
| pre-fault memory | `virt/kvm/kvm_main.c`（`KVM_GENERIC_PRE_FAULT_MEMORY`） | ⚠️ 可 opt-in |
| ptdump（stage-2 调试） | `arm64/kvm/ptdump.c` | ⚠️ 思想可移 |

**分诊要点**：只碰 `virt/kvm/*`（Tier A）的系列几乎必然与 riscv 相关；Tier B 系列是后续移植候选（盯 `gstage.c`/`vcpu_onereg.c`/`vcpu_pmu.c`/`vcpu_timer.c`/`vcpu_sbi_*.c`/selftests）；Tier C 系列除非扩展通用底座否则低/无可移植。
