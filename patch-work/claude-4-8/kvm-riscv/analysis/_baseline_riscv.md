# RISC-V KVM 能力基线（移植性判定依据）

> 来源：对本地内核树 `/Users/zq/Desktop/patch-work/linux-riscv`（Linux 7.2.0-rc3）`arch/riscv/kvm/` 的源码盘点。
> 用途：阶段 2 各子代理据此判定 x86/arm 补丁对 riscv 是「已有 / 可移植 / 模式可移植 / 不适用」。

## 已成熟实现（判 ALREADY 的依据）

| 子系统 | riscv 现状 | 关键文件 |
|---|---|---|
| G-stage MMU | Sv32/39/48/57x4、PMD/PUD 大页、hugetlb+THP、mmu_notifier、`KVM_CAP_VM_GPA_BITS` 动态页级 | `gstage.c` `mmu.c` `tlb.c` |
| dirty logging | 写保护式；快写故障路径；`KVM_DIRTY_LOG_MANUAL_CAPS` | `mmu.c:19/100/464` `gstage.c:446` |
| **dirty ring** | **已有 ACQ_REL 变体**（`HAVE_KVM_DIRTY_RING_ACQ_REL`） | `Kconfig` `vcpu.c:706` |
| 远程 TLB | HFENCE.GVMA/VVMA 全变体、Svinval、range flush | `tlb.c` |
| 中断 (AIA) | in-kernel irqchip = APLIC+IMSIC，3 种 IMSIC 模式(含 HWACCEL)、MSI 路由 | `aia*.c` `vm.c` |
| irqfd/ioeventfd | 均支持 (`HAVE_KVM_IRQ_ROUTING/MSI`, `KVM_CAP_IOEVENTFD`) | 通用 + `vm.c` |
| 定时器 | Sstc VS-timer + hrtimer 兜底 | `vcpu_timer.c` |
| PMU | SBI-PMU（需 host Sscofpmf）、snapshot、overflow 注入 | `vcpu_pmu.c` `vcpu_sbi_pmu.c` |
| FP/Vector | 惰性存取、ONE_REG 暴露 | `vcpu_fp.c` `vcpu_vector.c` |
| SBI 扩展 | base/hsm/sta/pmu/fwft/time/ipi/rfence/srst/susp/dbcn/mpxy… | `vcpu_sbi_*.c` |
| **steal-time** | **已有**（SBI STA） | `vcpu_sbi_sta.c` |
| ONE_REG | 10 大类、~75 ISA 扩展控制、`KVM_GET_REG_LIST` | `vcpu_onereg.c` `isa.c` |
| binary stats | VM+VCPU stats（14 计数器） | `vcpu.c:29` `vm.c:16` |
| MMIO/insn | load/store 模拟（含压缩指令）、HLVX | `vcpu_insn.c` `vcpu_exit.c` |
| NACL | SBI 嵌套加速 shim（**非**嵌套虚拟化） | `nacl.c` |

## 明确缺口（判 PORTABLE / PATTERN 的机会点）

1. **guest_memfd / `KVM_CREATE_GUEST_MEMFD` + `KVM_GENERIC_MEMORY_ATTRIBUTES`** — 未 select；arm64 已有；核心 `virt/kvm/guest_memfd.c` 大部分通用。→ 高价值。
2. **大页 eager split** — riscv 仅 lazy fault-driven（`gstage.c:274/306`）；**关闭 dirty-log 后不回收/合并大页**（`gstage.c:265` 明确「not support now」）。x86/arm 有 eager split。→ 高价值。
3. **ptdump / stage-2 页表 dumper** — arm64 有 `ptdump.c`，riscv 无。
4. **IRQ bypass / posted interrupts**（`HAVE_KVM_IRQ_BYPASS` 未选）— IMSIC 有直注潜力。
5. **selftests 缺口**：`guest_memfd_test`、`dirty_log_page_splitting_test`、AIA/IMSIC 功能测试、`pmu_counters_test`/`pmu_event_filter_test`。
6. **HW 断点/单步**（`kvm_guest_debug_arch` 为空）、**PMU event filter**、**TSO dirty-ring 变体**、**async-PF/更多 PV 特性**。

## 明确不适用（判 N-A，除非扩展了通用底座）

嵌套虚拟化（riscv 无，`vcpu_sbi_replace.c:130` 明确 TODO）、机密计算（无 CoVE；对应 TDX/SEV-SNP/pKVM/CCA）、VMX/SVM 世界切换、GIC/VGIC/ITS 内部、Hyper-V/Xen 增强、SMM/MTRR/PIT 等 x86 遗留。
