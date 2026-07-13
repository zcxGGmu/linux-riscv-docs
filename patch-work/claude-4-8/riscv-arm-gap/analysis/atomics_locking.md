# atomics-locking 可移植性分析（linux-arm-kernel → RISC-V）

## 摘要

- **系列总数**：71
- **四态计数**：ALREADY 1 · PORTABLE 9 · PATTERN 10 · N-A 51
- **重要提示**：本桶 signal 噪声极高——**约 40 条是 DRM atomic-KMS 假阳性**（"atomic" 指原子显示提交 `atomic_check`/`atomic_commit`，**非 CPU 原子指令**），另有一批是 **驱动 "sleep-in-atomic" / spinlock 递归 bugfix**（meson/mtk/i2c-imx/net 等），对 riscv arch 无可移植价值，均判 N-A。真正的原子/锁/屏障工作集中在 ~15 条。

### 本类 Top 候选（按价值排序）

1. **barrier: smp_cond_load_\*_timeout()**（#5 v13，另 #50/#58/#70 为旧版）— PORTABLE(generic core)+PATTERN(riscv Zawrs hook)。**旗舰**。
2. **arm64: support poll_idle() / cpuidle-haltpoll**（#69）— PORTABLE(cpuidle core)+PATTERN(riscv 缺 TIF_POLLING_NRFLAG/haltpoll)。
3. **kernel: hq-spinlock**（#27）— PORTABLE，新增通用自适应排队自旋锁，nginx +68~78%。
4. **arm64: per-CPU 原子用 load-LSE**（#46）— PATTERN，riscv **无 `asm/percpu.h`**，可用 AMO 实现。
5. **arm64: unaligned atomic emulation**（#45）— PATTERN(riscv traps.c 已有 misaligned 框架)+PORTABLE(prctl uapi)。
6. **random: lockless fast path + cmpxchg64_local**（#40）— PORTABLE，riscv 原语已具备。
7. **kunit: smp_cond_load_\*_timeout 测试**（#17）— PORTABLE，#5 的测试伴随。

---

## Top 可移植候选（深度）

### 1. barrier: Add smp_cond_load_{relaxed,acquire}_timeout()（旗舰）
- **原补丁**：`[v13,01/15] asm-generic: barrier` 系列（https://patchwork.kernel.org/project/linux-arm-kernel/patch/20260702013334.140905-8-ankur.a.arora@oracle.com/）状态=new。旧版：#50(v7)、#58(v4 timewait)、#70(v1)。
- **可移植点**：在 `asm-generic/barrier.h` 新增 `smp_cond_load_{relaxed,acquire}_timeout(ptr,cond,time_expr,time_limit)`，`include/linux/atomic.h` 派生 `atomic[64]_cond_read_*_timeout()`（**已 curl 核对**：diff 落在 `include/linux/atomic.h` + `Documentation/atomic_t.txt`，纯 generic）。带超时的自旋等待原语，供 rqspinlock/poll_idle 复用。
- **riscv 落点**：generic 部分（asm-generic/barrier.h、include/linux/atomic.h、Documentation）**直接适用**；arch hook 落 `arch/riscv/include/asm/barrier.h`——riscv 已有 `smp_cond_load_relaxed`→`__cmpwait_relaxed`（Zawrs `wrs.nto`，barrier.h:69-77），需扩出带 deadline 检查的 `_timeout` 变体（arm64 用 WFET/WFE+deadline，riscv 用 `wrs.nto`+轮询时钟）。
- **判定**：**PORTABLE**（generic core）+**PATTERN**（riscv Zawrs 落点已存在，增量重写超时逻辑）。

### 2. arm64: support poll_idle() / cpuidle-haltpoll
- **原补丁**：`arm64: support poll_idle()`（https://patchwork.kernel.org/project/linux-arm-kernel/patch/20250218213337.377987-12-ankur.a.arora@oracle.com/）状态=new，v10 11 patches。
- **可移植点**：generic `cpuidle/poll_state.c` 改用 `smp_cond_load_relaxed_timewait()` 轮询；`ARCH_HAS_CPU_RELAX`→`ARCH_HAS_OPTIMIZED_POLL` 并上移 `arch/Kconfig`；`ACPI: processor_idle` 支持 LPI 轮询态。arch 侧：定义 `TIF_POLLING_NRFLAG`、`select ARCH_HAS_OPTIMIZED_POLL`、`asm/cpuidle_haltpoll.h`。
- **riscv 落点**：**已 grep 核对 riscv 三者皆缺**——`arch/riscv/include/asm/thread_info.h` 无 `TIF_POLLING_NRFLAG`、arch 无 `ARCH_HAS_OPTIMIZED_POLL`/`cpuidle_haltpoll`。generic(poll_state/Kconfig/ACPI) PORTABLE；riscv 需补 TIF 标志 + haltpoll header，且轮询后端可接 Zawrs（与 #5 组合）。
- **判定**：**PATTERN**（riscv arch enablement）+**PORTABLE**（cpuidle core）。真实缺口。

### 3. kernel: add hq-spinlock（通用自适应自旋锁）
- **原补丁**：`[RFC,v3,1/7] kernel: add hq-spinlock types` 系列（https://patchwork.kernel.org/project/linux-arm-kernel/patch/20260415164459.2904963-7-fedorov.nikita@h-partners.com/）状态=new。
- **可移植点**：新增 hq-spinlock（hierarchical/adaptive queued spinlock）通用类型——patch1-5 在 `kernel/`+`include/linux` 落通用底座（types/inner logic/contention detection/tunables），patch6 `spin_lock_init_hq()` 供 lockref 用（**已 curl**：patch6 仅改 `include/linux/lockref.h`）。Kunpeng920 nginx +68~78%。
- **riscv 落点**：纯通用 `kernel/locking/`+`include/linux`，走 spinlock API，**架构无关，riscv 自动受益**（riscv combo spinlock 之上再叠一层通用自适应锁）。
- **判定**：**PORTABLE**。注：RFC，未必落地，但机制通用。

### 4. arm64: Use load LSE atomics for non-return per-CPU atomics
- **原补丁**：`arm64: Use load LSE atomics for the non-return per-CPU atomic operations`（https://patchwork.kernel.org/project/linux-arm-kernel/patch/20251106155213.3186582-1-catalin.marinas@arm.com/）状态=new。
- **可移植点**：**已 curl**——`this_cpu_add/or/andnot` 从 store-only LSE（STADD/STCLR/STSET）改为 load 形（LDADD/LDCLR/LDSET，dst 寄存器弃用），鼓励 uarch "near" 执行、避免 srcu_read_{lock,unlock} 背靠背 posting 开销（Reviewed-by: Palmer Dabbelt）。
- **riscv 落点**：**已 grep 核对 riscv 无 `arch/riscv/include/asm/percpu.h`**（用 asm-generic：irq-disable + 普通 RMW，**根本不是原子指令**）。更大机会：新建 `arch/riscv/include/asm/percpu.h`，用 AMO（`amoadd.w/d`、`amoor`、`amoand`，Zabha 子字）实现 percpu 非返回原子，一步到位跳过 arm64 的 STADD→LDADD 演进。
- **判定**：**PATTERN**。该补丁本身是 arm64-uarch 微调，但"percpu 用单条原子指令"的机制 riscv 尚未利用，落点明确。

### 5. arm64: Implement unaligned atomic emulation
- **原补丁**：`[RFC,v2,1/1] arch: arm64: Implement unaligned atomic emulation`（https://patchwork.kernel.org/project/linux-arm-kernel/patch/20251117160841.334224-2-andrealmeid@igalia.com/）状态=new。
- **可移植点**：**已 curl**——新增 `prctl(PR_ARM64_UNALIGN_ATOMIC_EMULATE)`（`include/uapi/linux/prctl.h`+`kernel/sys.c` generic 分发）+ TIF 标志；`mm/fault.c` 捕获 LSE 原子对齐 fault，`unaligned_atomic.c`（520 行）trap-and-emulate。解决游戏等 x86→arm64 移植中未对齐原子问题。
- **riscv 落点**：**已 grep 核对** riscv `arch/riscv/kernel/traps.c` 已有 `misaligned_handler[]`/`handle_misaligned_{load,store}` 未对齐标量访存模拟框架——扩展到 AMO/LR-SC 未对齐模拟为自然 PATTERN；prctl ABI 部分（去 arm64 前缀化）PORTABLE。
- **判定**：**PATTERN**（riscv traps.c 落点已存在）+PORTABLE(prctl 协商 ABI)。

### 6. random: lockless fast path for get_random_uXX() + cmpxchg64_local
- **原补丁**：`Improve get_random_u8() for use in randomize kstack`（https://patchwork.kernel.org/project/linux-arm-kernel/patch/20251127092226.1439196-13-ardb+git@google.com/）状态=new。
- **可移植点**：`drivers/char/random.c` 用 local cmpxchg 做无锁 fast path（**已 curl**：patch5 改 random.c）；配套把 hexagon/arc 的 `cmpxchg64_local()` 接到 generic 实现；`randomize_kstack` entry 处用 `get_random_u8()`。纯 generic。
- **riscv 落点**：**已 grep 核对** riscv `cmpxchg.h` 已有 `arch_cmpxchg64_local`（cmpxchg.h:297），generic 无锁路径**直接适用**，riscv 自动受益；randomize_kstack 落 entry 通路。
- **判定**：**PORTABLE**。

### 7. kunit: tests for smp_cond_load_\*_timeout()
- **原补丁**：`[v11,1/2] kunit: add tests for smp_cond_load_*_timeout()`（https://patchwork.kernel.org/project/linux-arm-kernel/patch/20260521083038.134260-1-ankur.a.arora@oracle.com/）状态=new。
- **可移植点**：#5 的 kunit 测试（含 clock 测试），通用 lib/kunit，验证任意 arch 的 `smp_cond_load_*_timeout` 实现。
- **riscv 落点**：generic 测试，riscv 实现 #5 arch hook 后可直接跑验证。**判定：PORTABLE**。

---

## 全量判定表

| # | 系列 | arch | 判定 | 可移植点(若有) | riscv落点(若有) |
|---|---|---|---|---|---|
| 5 | barrier: smp_cond_load_\*_timeout (v13) | arm | **PORTABLE+PATTERN** | asm-generic barrier + atomic_cond_read_timeout | asm-generic/barrier.h; `arch/riscv/.../barrier.h`(Zawrs) |
| 50 | barrier: smp_cond_load_\*_timeout (v7 RESEND) | arm | PORTABLE+PATTERN | 同#5 旧版 | 同#5 |
| 58 | barrier: smp_cond_load_\*_timewait (v4) | arm | PORTABLE+PATTERN | 同#5 旧版(timewait 命名) | 同#5 |
| 70 | barrier: Introduce smp_cond_load_\*_timeout (v1) | arm | PORTABLE+PATTERN | 同#5 最初版 | 同#5 |
| 69 | arm64: support poll_idle()/haltpoll | arm | **PATTERN+PORTABLE** | cpuidle poll_state + ARCH_HAS_OPTIMIZED_POLL 上移 | `thread_info.h`(TIF_POLLING_NRFLAG)、`asm/cpuidle_haltpoll.h`、cpuidle/poll_state.c |
| 27 | kernel: hq-spinlock | generic | **PORTABLE** | 新增通用自适应排队自旋锁 | `kernel/locking/`+`include/linux`(arch 无关) |
| 46 | arm64: per-CPU 用 load-LSE 原子 | arm | **PATTERN** | percpu 非返回原子用单条原子指令 | 新建 `arch/riscv/include/asm/percpu.h`(AMO) |
| 45 | arm64: unaligned atomic emulation | arm | **PATTERN+PORTABLE** | prctl + trap-emulate 未对齐原子 | `arch/riscv/kernel/traps.c`(misaligned 框架)+prctl uapi |
| 40 | random: lockless fast path + cmpxchg64_local | generic | **PORTABLE** | local-cmpxchg 无锁路径 | drivers/char/random.c; riscv cmpxchg64_local 已有 |
| 17 | kunit: smp_cond_load_\*_timeout 测试 | generic | **PORTABLE** | #5 的通用 kunit 测试 | lib/kunit(arch 无关) |
| 6 | dma-mapping: track shared DMA (CC_SHARED) v7 | arm | **PORTABLE** | 通用 confidential-DMA(direct/pool/swiotlb) | `kernel/dma/*`(riscv CoVE 受益) |
| 12 | dma-mapping: DMA_ATTR_CC_SHARED v6 | other | **PORTABLE** | 同#6 旧版 | `kernel/dma/*` |
| 25 | KVM: arm64: WFI wake w/ userspace irqchip | arm | **PATTERN** | 用户态 irqchip 时中断唤醒 vcpu | `arch/riscv/kvm/vcpu_insn.c`(kvm_riscv_vcpu_wfi) |
| 29 | KVM: arm64: disable WFI/WFE exits cap | arm | **PATTERN** | KVM_CAP 不 trap WFI(passthrough) | `arch/riscv/kvm/vcpu.c`;WFE 部分 N-A(无对应) |
| 30 | KVM: arm64: user_mem_abort() bug fix | arm | **PATTERN** | atomic-fault 页泄漏/vma_shift 陈旧 | `arch/riscv/kvm/mmu.c`(gstage_map_page) |
| 52 | arm64: Make EFI calls preemptible | arm | **PATTERN** | 去 efi_rt_lock、EFI 上下文可抢占 | riscv EFI runtime + kernel-mode vector |
| 31 | arm64: silence sparse in (cmp)xchg cast | arm | **PATTERN**(低) | cmpxchg 类型双关 sparse 消警 | `arch/riscv/include/asm/cmpxchg.h` |
| 61 | arm64: prefetch before LSE atomics | arm | **PATTERN**(低) | 原子前预取目标 | `atomic.h`+Zicbop `prefetch.w` |
| 3 | arm64: idle=<wfi\|yield\|nop> early_param | arm | **PATTERN**(低) | 选择 idle 指令的启动参数 | `arch/riscv/kernel/process.c`(riscv 仅 wfi，价值有限) |
| 33 | arm64: unconditional LSE/PAN/EPAN | arm | **ALREADY**(+N-A) | LSE→riscv Zabha/Zacas 运行时已有 | `cmpxchg.h`;PAN/EPAN 无 riscv 对应→N-A |
| 41 | arm64: LSE 宏移除无用参数 | arm | N-A | arm64 LSE 宏 cleanup，无 riscv 值 | — |
| 53 | arm64: near-atomics 优化 (__lse_ll_sc_body) | arm | N-A | arm64 uarch "near atomics" 专属 | — |
| 49 | Overhead of arm64 LSE per-CPU atomics?(讨论) | arm | N-A | 邮件讨论，非补丁 | — |
| 59 | Interrupts enabled early by spinlock guard(讨论) | generic | N-A | bug 报告讨论线程 | — |
| 44 | per-vCPU vLPI injection API | arm | N-A | GICv4/ITS vLPI 硬件专属 | — |
| 55 | KVM: arm64: vgic spinlock API fix | arm | N-A | vgic=GIC 专属 | — |
| 66 | firmware: arm_ffa notification fixes | generic | N-A | FF-A 固件 ABI(arm 专属 Tier-C) | — |
| 56 | firmware: arm_scmi cleanups+doc | generic | N-A | SCMI 固件 doc/cleanup | — |
| 57 | firmware: arm_scmi cleanups(dup) | generic | N-A | 同#56 | — |
| 1 | drm/imx ipuv3 atomic check | generic | N-A | DRM atomic-KMS 假阳性(imx 驱动) | — |
| 2 | drm/exynos mic atomic bridge v2 | generic | N-A | DRM atomic-KMS 假阳性 | — |
| 4 | drm: simple pipe→atomic helpers | generic | N-A | DRM atomic-KMS 假阳性 | — |
| 8 | drm/bridge imx8mp atomic_create_state | generic | N-A | DRM atomic-KMS 假阳性 | — |
| 9 | drm/bridge convert all to atomic | generic | N-A | DRM atomic-KMS 假阳性 | — |
| 10 | drm color format property | generic | N-A | DRM KMS 属性 | — |
| 13 | drm/atomic rework state allocation | generic | N-A | DRM atomic-KMS 假阳性 | — |
| 18 | drm dw_hdmi enable/disable cleanup | generic | N-A | DRM KMS 驱动 | — |
| 28 | drm/bridge stm_lvds atomic_check | generic | N-A | DRM atomic-KMS 假阳性 | — |
| 34 | drm zynqmp_dp retrain(smp_load/store) | generic | N-A | DRM 驱动(用 generic smp_load/store) | — |
| 36 | drm CRTC post-blend color pipeline v3 | generic | N-A | DRM KMS | — |
| 37 | drm/rockchip no post-atomic_check fixups | generic | N-A | DRM atomic-KMS 假阳性 | — |
| 38 | drm revert/fix enable/disable seq | generic | N-A | DRM KMS | — |
| 47 | drm/sun4i DE33 layer refactor | generic | N-A | DRM KMS 驱动 | — |
| 48 | drm/atomic-helper flush kthread worker | generic | N-A | DRM KMS | — |
| 51 | drm/atmel-hlcdc memory bugs | generic | N-A | DRM KMS 驱动 | — |
| 54 | drm post-blend color pipeline v2 | generic | N-A | 同#36 旧版 | — |
| 60 | drm/mediatek atomic_disable err handling | generic | N-A | DRM atomic-KMS 假阳性 | — |
| 62 | drm analogix_dp bridge_connector | generic | N-A | DRM KMS 驱动 | — |
| 63 | drm/bridge get/put first_bridge | generic | N-A | DRM KMS 框架 | — |
| 7 | gpio shared-proxy sleep-in-atomic(meson) | generic | N-A | 驱动锁上下文 bugfix | — |
| 11 | net airoha atomic_t→int counter | generic | N-A | 驱动 cleanup | — |
| 14 | i2c imx SMBus block-read atomic v2 | generic | N-A | i2c 驱动(atomic xfer 模式) | — |
| 15 | i2c imx SMBus block-read(v1) | generic | N-A | 同#14 | — |
| 16 | irqchip exynos-combiner remove spinlock | generic | N-A | irqchip 驱动 cleanup | — |
| 19 | net macb PCIe 屏障/watchdog | generic | N-A | 驱动 MMIO 屏障(macb 专属) | — |
| 20 | iio xilinx-ams guard(spinlock) | generic | N-A | 驱动 cleanup(用 generic guard) | — |
| 21 | net sparx5 sleep-in-atomic fixes | generic | N-A | 驱动 bugfix | — |
| 22 | firmware samsung acpm barrier/UAF fixes | generic | N-A | 驱动 bugfix(LKMM 屏障但 acpm 专属) | — |
| 23 | net dsa mt7530 sleep-in-atomic | generic | N-A | 驱动 bugfix | — |
| 24 | media videobuf2 dma_resv fences | generic | N-A | media 框架(dma_resv) | — |
| 26 | pwm atmel-tcb mark atomic | generic | N-A | pwm 驱动(pwm atomic API) | — |
| 32 | watchdog imx7ulp WFI(i.MX94) | generic | N-A | 驱动+SoC 专属 | — |
| 35 | net airoha schedule-while-atomic | generic | N-A | 驱动 bugfix | — |
| 39 | pmdomain mtk spinlock recursion v2 | generic | N-A | 驱动 bugfix(mtk) | — |
| 42 | pmdomain mtk spinlock recursion | generic | N-A | 同#39 | — |
| 43 | pmdomain mtk spinlock recursion URGENT | generic | N-A | 同#39 | — |
| 64 | mt76 mt7996 sleep-while-atomic | generic | N-A | wifi 驱动 bugfix | — |
| 65 | i2c imx guard+drop prefix | generic | N-A | 驱动 cleanup | — |
| 67 | i2c imx adapting mainline | generic | N-A | 同#65 | — |
| 68 | net mtk-star-emac spinlock recursion | generic | N-A | 驱动 bugfix | — |
| 71 | gpio xilinx raw spinlock | generic | N-A | 驱动(raw spinlock 转换) | — |

**N-A 分组说明**：
- **DRM atomic-KMS 假阳性（20 条：#1,2,4,8,9,10,13,18,28,34,36,37,38,47,48,51,54,60,62,63）**："atomic" 指原子显示提交，非 CPU 原子，与 riscv arch 无关。
- **驱动 sleep-in-atomic / spinlock-recursion / guard cleanup bugfix（~23 条：#7,11,14,15,16,19,20,21,22,23,24,26,32,35,39,42,43,64,65,67,68,71 等）**：厂商驱动锁上下文修复，无 riscv arch 落点。
- **arm 固件 ABI / GIC / uarch 专属（#41,44,49,53,55,56,57,59,66）**：FF-A/SCMI/vLPI/near-atomics/讨论线程等，Tier-C，N-A。
