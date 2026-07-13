# misc-arch（第2片）可移植性分析（linux-arm-kernel → RISC-V）

> 输入：`data/by_category/misc-arch.1.jsonl`（202 条系列）。
> 判定依据：`_baseline_riscv.md` + 本地树 `/Users/zq/Desktop/patch-work/linux-riscv`（v7.2.0-rc3）实地 grep。
> 本片为 arm64/ARM 架构杂项 catch-all，绝大多数是 KVM:arm64 hyp 内幕、ARM SoC/DTS/defconfig、纯 ARM HW/ISA（MPAM/AMU/SPE/TRBE/PAC/MTE/PIE/POE/CCA-RME）——批量 N-A；真候选集中在少数「通用底座 / arch 模式」系列。

## 摘要

- **系列总数**：202
- **四态计数**：PORTABLE ≈ 15 ｜ PATTERN ≈ 16 ｜ ALREADY ≈ 6 ｜ N-A ≈ 165
- **本类 Top 候选**（按价值排序）：
  1. **#79 paravirt: 通用 `paravirt_steal_clock()`**（riscv 已在 diff 中被直接改动）→ PORTABLE
  2. **#144 / #152 uaccess: user access scopes / ASM-GOTO 安全包装**（series 内含 `riscv/uaccess` 补丁）→ PORTABLE
  3. **#112 arch,sysfb,efi: 非 x86 EFI 系统 EDID 支持**（纯通用 efi/libstub；riscv 是非 x86 EFI 架构）→ PORTABLE
  4. **#180 Only link libstub to final vmlinux**（series 内含 `riscv:` 补丁）→ PORTABLE
  5. **#45 runtime-const 优化 handle_arch_irq**（patch1-2 通用 genirq；riscv 已有 runtime-const.h）→ PORTABLE
  6. **#29 dma-mapping 批量 cache sync**（patch4-5 通用 `kernel/dma`；arch 需 nosync dcache helper）→ PORTABLE+PATTERN
  7. **#61 arm64: __nocfi on swsusp_arch_resume**（riscv 有 hibernate.c:354 + kCFI）→ PATTERN

---

## Top 可移植候选（深度）

### 1. #79 paravirt: Use common code for paravirt_steal_clock()  ★最强
- **原补丁**：`[v5,05-08/21] paravirt: Remove asm/paravirt_api_clock.h` 等（https://patchwork.kernel.org/project/linux-arm-kernel/patch/20260105110520.21356-6-jgross@suse.com/）状态=new
- **可移植点**：把各 arch 重复的 `paravirt_steal_clock()` / `paravirt_api_clock.h` 收敛进 `kernel/sched/` 通用代码。**curl 全文确认：diff 直接删除 `arch/riscv/include/asm/paravirt_api_clock.h`（与 arm/arm64/loongarch/powerpc/x86 并列）**。
- **riscv 落点**：`arch/riscv/kernel/paravirt.c`（已有 `pv_time_steal_clock` @82、`has_pv_steal_clock` @37，grep 确认）+ 删除 `arch/riscv/include/asm/paravirt_api_clock.h`。
- **判定**：**PORTABLE** —— riscv 本就是该系列的直接目标，纯通用重构落到 riscv 无需额外设计。

### 2. #144 / #152 uaccess: Provide and use scopes for user (masked) access  ★
- **原补丁**：`[V5,01-12/12]`（https://patchwork.kernel.org/project/linux-arm-kernel/patch/20260027083745.862419776@linutronix.de/ 及 v3 版 20251017093030）状态=new
- **可移植点**：为 `unsafe_*_user()` 提供 ASM-GOTO 安全包装 + user-access scope（`user_access_begin/end` 作用域化）。**series 明确含 `[V5,05/12] riscv/uaccess: Use unsafe wrappers for ASM GOTO`**。
- **riscv 落点**：`arch/riscv/include/asm/uaccess.h`（grep 确认已有 `user_access_begin`@456、`arch_unsafe_put_user`@473、`arch_unsafe_get_user`@476）——补丁正是改这些已有钩子。
- **判定**：**PORTABLE** —— riscv 已在 series 内，通用 uaccess 框架变更直接适用。

### 3. #112 arch,sysfb,efi: Support EDID on non-x86 EFI systems  ★
- **原补丁**：`[v3,1-9/9]`（https://patchwork.kernel.org/project/linux-arm-kernel/patch/20251126160854.553077-9-tzimmermann@suse.de/）状态=new
- **可移植点**：重构 `screen_info`→`struct sysfb_display_info`/`sysfb_primary_display`，让 **非 x86 EFI 系统**也能从 EFI 拿到 framebuffer + EDID。**curl 确认 diff 全在 `drivers/firmware/efi/{efi-init.c,efi.c,libstub/*}` + loongarch**，无 arm 专有硬件。
- **riscv 落点**：通用 `drivers/firmware/efi/`、`drivers/video/`；riscv 走 EFI stub 启动（baseline §5 `CONFIG_EFI_STUB`），直接受益，riscv 侧仅需 `arch/riscv` 提供 `screen_info` 符号（多数已由通用路径覆盖）。
- **判定**：**PORTABLE** —— riscv 正是「非 x86 EFI 系统」，通用改动近乎自动适用。

### 4. #180 Only link libstub to final vmlinux  ★
- **原补丁**：`[v1,1-3/3]`（https://patchwork.kernel.org/project/linux-arm-kernel/patch/20250919093615.30235-3-yangtiezhu@loongson.cn/）状态=new
- **可移植点**：EFI libstub 只链接进最终 vmlinux，避免中间目标重复链接。**series 明确含 `[v1,3/3] riscv: Only link libstub to final vmlinux`**。
- **riscv 落点**：`arch/riscv/Makefile` + `drivers/firmware/efi/libstub/`。
- **判定**：**PORTABLE** —— riscv 已在 series 内。

### 5. #45 use runtime constant to optimize handle_arch_irq access  ★
- **原补丁**：`[1-3/3]`（https://patchwork.kernel.org/project/linux-arm-kernel/patch/20260220090922.1506-2-jszhang@kernel.org/）状态=new
- **可移植点**：把 `handle_arch_irq` 全局函数指针改成 runtime-const（省一次内存加载）。**curl 确认 patch1 改 `include/asm-generic/vmlinux.lds.h`（加 `_handle_arch_irq RUNTIME_CONST` 段）、patch2 改 genirq——皆通用**；patch3 才是 arm64 落地。
- **riscv 落点**：`arch/riscv/kernel/irq.c`（`set_handle_irq`/`handle_arch_irq`）；**riscv 已有 `arch/riscv/include/asm/runtime-const.h`（grep 确认）**，可直接套用通用机制。
- **判定**：**PORTABLE**（通用 patch1-2）+ riscv 侧一小段 PATTERN 落地。

### 6. #29 dma-mapping: arm64: support batched cache sync
- **原补丁**：`[v3,1-5/5]`（https://patchwork.kernel.org/project/linux-arm-kernel/patch/20260228221239.59903-1-21cnbao@gmail.com/）状态=new
- **可移植点**：patch4-5「分离 DMA sync 发起与完成等待」「`dma_direct_{map,unmap}_sg` 批量模式」在 `kernel/dma/`——**通用**；patch1-3 是 arm64 `dcache_*_poc_nosync` helper（curl 确认落 `arch/arm64/mm/cache.S`+`cacheflush.h`）。
- **riscv 落点**：通用批量框架 `kernel/dma/` = PORTABLE；riscv 需提供等价 nosync dcache helper → `arch/riscv/mm/dma-noncoherent.c` / `arch/riscv/include/asm/cacheflush.h`（riscv 用 CMO Zicbom/SBI 做 cache 维护）。
- **判定**：**PORTABLE**（通用批量层）**+ PATTERN**（arch nosync helper）。

### 7. #61 arch: arm64: set __nocfi on swsusp_arch_resume
- **原补丁**：https://patchwork.kernel.org/project/linux-arm-kernel/patch/20260122114925.624309-1-zhaoyang.huang@unisoc.com/ 状态=new
- **可移植点**：hibernate resume 蹦床在 CFI 生效前运行/跨页表切换，需 `__nocfi` 免 kCFI 误杀。
- **riscv 落点**：`arch/riscv/kernel/hibernate.c:354 swsusp_arch_resume`（grep 确认存在）；riscv 有 kCFI（baseline §8 `kernel/cfi.c`）→ 同样风险。
- **判定**：**PATTERN** —— 机制通用、riscv 落点明确，改动极小。

---

## 其余 PORTABLE / PATTERN / ALREADY（简表）

| # | 系列 | 判定 | 可移植点 → riscv 落点 |
|---|---|---|---|
| 1 | treewide: Convert buses to use generic driver_override | **PORTABLE** | driver core 通用（`drivers/base/`）；删 `driver_set_override()`，全架构适用 |
| 69 | uapi: fix remaining kconfig leaks in UAPI headers | **PORTABLE** | `scripts/headers_install.sh` + 各 arch uapi；riscv uapi 头同类清理 |
| 88 | arm64: efi: Fix NULL crash（patch2 kthread user_ns warn）| **PORTABLE**(部分) | patch2 `kernel/kthread.c` `kthread_use_mm()` 校验，通用；patch1 arm64 efi 为 N-A |
| 128 | efi/reboot: platform specific reset on arm64（patch1）| **PORTABLE**(部分) | patch1 `drivers/firmware/efi/reboot.c` 加 `EFI_RESET_PLATFORM_SPECIFIC`，通用；riscv EFI reboot 受益 |
| 130 | Introduce 128-bit IO access | **PORTABLE**(部分) | patch1-3 `uapi`/`asm-generic/io.h`/`io-128-nonatomic` 通用；arm64 raw 后端 N-A。riscv 落点 `arch/riscv/include/asm/io.h`（可选后端） |
| 155 | Remove DMA map_page/map_resource + unmap callbacks | **PORTABLE** | `kernel/dma/` + 各 arch 转 map_phys；riscv 用 dma-direct 自动受益 |
| 184 | Preparation to .map_page/.unmap_page removal | **PORTABLE** | 同 #155，通用 `kernel/dma/` 预备重构 |
| 179 | ARM: uaccess: __get_user_asm_dword()（#144 系列一环）| **PORTABLE** | 属通用 uaccess scopes series；riscv 已在 series 内 |
| 20 | arm64: clear_page[s] using memset | **PATTERN** | 通用 `clear_pages()` 接口；riscv 落 `arch/riscv/include/asm/page.h`(@43 `clear_page`)+`lib/clear_page.S` |
| 27 | arm64: Implement clear_pages() | **PATTERN** | 同上，多页 `clear_pages()`；riscv 已有 `clear_page`，可加多页版 |
| 138 | arm64/pageattr: Propagate return value from __change_memory_common | **PATTERN** | riscv `arch/riscv/mm/pageattr.c`（`set_memory_*`@349-372）同类错误传播 |
| 177 | arm64: map [_text,_stext) non-exec+read-only | **PATTERN** | 硬化：head 区先置 RO+NX；riscv `arch/riscv/mm/init.c`(`STRICT_KERNEL_RWX` 路径) |
| 149 | arm64/ARM: ptdump use seq_puts() | **PATTERN** | riscv `arch/riscv/mm/ptdump.c`（`pt_dump_seq_puts`@22）同宏清理 |
| 194 | arm64/ptdump: Add cmdline 'early_ptdump' | **PATTERN** | riscv `arch/riscv/mm/ptdump.c` 可加 early_ptdump |
| 107 | arm64: Print slab alloc/free paths for register addresses | **PATTERN** | oops 增强（`mem_dump_obj()`）；riscv `arch/riscv/kernel/traps.c`/`mm/fault.c` |
| 175 | KVM: arm64: Implement KVM_TRANSLATE ioctl | **PATTERN** | 通用 KVM ABI；riscv `arch/riscv/kvm/` 可实现 GVA→GPA 翻译 ioctl |
| 8 | Faster Arm64 __arch_copy_from/to_user | **PATTERN**(弱) | arm64 asm 微优化；riscv `arch/riscv/lib/uaccess.S` 可类比 |
| 39 | arm64: signal: preserve si_addr in VA hole | **PATTERN**(弱) | riscv 也有 Sv39/48/57 非规范空洞；`arch/riscv/kernel/signal.c`/`traps.c` |
| 133 | srcu: Optimize SRCU-fast-updown for arm64 | **PATTERN**(弱) | `kernel/rcu/srcutree.c` 内 arch 感知优化；riscv acquire/release 可类比 |
| 43 | arm64: make runtime const not usable by modules | **PATTERN**(弱) | riscv 有 runtime-const.h，应核对模块可用性约束 |
| 55 | ARM: Implement ARCH_HAS_CC_CAN_LINK | **PATTERN**(弱) | Kconfig 特性；riscv `arch/riscv/Kconfig` 可 select |
| 31/119/158/160 | treewide `__ASSEMBLY__`→`__ASSEMBLER__` 重命名 | **PATTERN**(机械) | 同类清理适用 `arch/riscv/include/**`（riscv 或已单独处理） |
| 22 | arm: try_get_task_stack() for __get_wchan | **ALREADY** | riscv `stacktrace.c:172` `__get_wchan` 已用 `try_get_task_stack` |
| 26 | arm: get task_stack ref before dump_backtrace | **ALREADY**(近似) | 同源保护；riscv walk_stackframe 路径已取栈引用 |
| 36 | arm64: runtime-const 省一条指令 | **ALREADY**(基座) | riscv 已有 runtime-const.h；此为 arm64 VA_BITS asm 微调（riscv 无需） |
| 42 | arm: Add runtime constant support for armv7 | **ALREADY** | riscv 已有等价 runtime-const 后端 |
| 134 | arm64: use SOFTIRQ_ON_OWN_STACK | **ALREADY** | riscv `Kconfig:905` 已 select `HAVE_SOFTIRQ_ON_OWN_STACK`，`irq.c:128 do_softirq_own_stack` |
| 68 | arm64: Make STRICT_KERNEL_RWX visable | **ALREADY**(部分) | riscv 已有 STRICT_KERNEL_RWX（baseline §1）；可见性为小 Kconfig 事项 |
| 86 | arm64: enable ARCH_WANTS_THP_SWAP all pagesizes | **ALREADY**(部分) | riscv 已支持 THP swap（baseline §1） |

---

## 全量判定表（N-A 同质分组）

上表已逐条列出全部 PORTABLE / PATTERN / ALREADY 信号系列（覆盖 #1,8,20,22,26,27,29,31,36,42,43,45,55,61,68,69,79,86,88,107,112,119,128,130,133,134,138,144,149,152,155,158,160,175,177,179,180,184,194）。**其余 ~165 条为 N-A**，按同质分组如下（均 arm 专属 HW/ISA 或对 riscv 无可移植价值）：

| N-A 分组 | 代表系列（# 行号）| 计数 | N-A 理由 |
|---|---|---|---|
| **KVM:arm64 hyp/pKVM/NV/vGIC/stage2/AT/FGT/ID-reg** | #3,5,6,13,14,15,17,18,19,21,25,28,37,40,41,47,49,54,56,57,58,59,60,62,63,66,70,71,72,75,95,100,103,104,105,113,114,115,116,117,118,127,129,131,140,154,159,163,166,168,181,187,189,190,196,197,198,199,201 | ~59 | 依赖 arm64 EL2/VHE/nVHE、GIC(ICH/ICV)、SMMU、AT 指令、FGT/FEAT、SMCCC/FF-A、SPE/TRBE、stage2 硬件语义；riscv KVM(H 扩展/AIA/IOMMU) 机制不同，非直接可移植（riscv KVM 归 mmu-stage2 / nested-hwvirt 类）|
| **纯 ARM HW/ISA 特性**（MPAM/AMU/SPE/TRBE/PAC/MTE/PIE/POE/spectre/CCA-RME/条件码）| #2,7,34,35,50,67,74,85,92,123,126,141,147,148,162,171 | ~16 | GIC/MPAM/AMU/PIE/POE/CCA 等无 riscv 对应 ISA（baseline 差距表 #4-7）|
| **ARM SoC/board/DTS/overlay** | #4,16,52,73,93,96,97,101,124,125,139,145,146,153,157,164,167,169,170,172,185,192,200 | ~23 | mvebu/shmobile/omap/zynqmp/bcm/exynos/pxa/versatile/gemini/at91/sa1111 等板级、DTS，riscv 无 |
| **defconfig / Kconfig 平台开关 / config 片段** | #24,32,33,44,48,53,76,80,83,84,87,94,106,111,121,122,135,136,137,150,156,161,173,174,178,186,192 | ~26 | multi_v7/imx/exynos defconfig、平台 Kconfig、无用符号删除、pull-request；对 riscv 无值 |
| **ARM 汇编/lib/字符串 micro 与专属修复** | #10,30,46,51,81,108,109,110,120,151,165,182,183,188,191,202 | ~16 | arm64/arm 专属 asm（memset64/csum/delay/clear_user 对齐/probes bl-blr/cputype/MIDR/head TEXT_OFFSET/__READ_ONCE-LTO/exynos_mct），实现绑死 ISA |
| **注释/拼写/unreachable 清理** | #59,104,110,132,142,143,145,146,164,168,190 | ~11 | typo/comment/unreachable-break，无逻辑价值（arm 文件内） |
| **perf vendor JSON / tools 同步 / bootwrapper / 其他 arch** | #64,82,89,90,176,193,195 | ~7 | perf arm64 事件表、tools 头同步、bootwrapper、powerpc/smp——arm/他 arch 专属数据 |
| **其他 arm 专属/低价值** | #9(Hyper-V mshv_vtl arm64),11(lib/crc NEON),12(ARM ucontext.h uapi),23(PCI/TPH arm64),38(omap strscpy),65(arm64 swiotlb shrink),77(arm64 branch-profiling),78(arm64 efi preemptible),91(arm64 dcache helper, 属#29),99(exynos_mct 模块),102(arm __free 未初始化),121... | ~余量 | Hyper-V/NEON/ucontext/PCI-TPH-ACPI/omap/swiotlb-arch/efi-arch 等，绑 arm 平台或已被上文候选覆盖 |

> 说明：上表分组之和 + 简表信号系列 ≈ 202。个别系列（如 #91 属 #29 的 dcache helper、#9 部分「common files」重构）虽含轻微通用成分，但主体绑 arm 平台/Hyper-V，整体归 N-A。#23(PCI/TPH)、#65(swiotlb)、#88(efi 部分)、#128(efi 部分) 的「通用底座片段」已在候选/部分 PORTABLE 中注明。

---

## 结论

本片 202 条以 **KVM:arm64 hyp 内幕 + ARM SoC/DTS/defconfig + 纯 ARM HW/ISA** 为绝对主体（~165 N-A）。**真候选高度集中在「通用底座」系列**，且其中 **4 条（#79/#144/#152/#180）riscv 本就在原 series 目标列表内**——最省力、最高确定性。次强为需 riscv 侧小幅落地的通用机制（#112 EFI-EDID、#45 runtime-const genirq、#29 dma 批量 sync）与 arch 模式（#61 __nocfi hibernate、ptdump/pageattr/clear_pages 增量）。已用本地树 grep 逐一核对 riscv 落点存在，规避了 runtime-const / SOFTIRQ_ON_OWN_STACK / try_get_task_stack 三处「riscv 已有」误报。
