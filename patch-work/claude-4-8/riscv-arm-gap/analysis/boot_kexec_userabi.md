# boot / kexec / vdso / signal 可移植性分析（linux-arm-kernel → RISC-V）

> 输入：`data/by_category/smallcombo.jsonl`（4 小类合并：boot-head 10 + kexec-crash 19 + vdso 14 + signal-ptrace-elf 16 = **59 系列**）
> 基线树：Linux **v7.2.0-rc3**（`/Users/zq/Desktop/patch-work/linux-riscv`）。所有 riscv 落点均已用 Grep/Read 核对。
> 深挖（curl 全文 + diff 核对）：#7 module text-poke、#13 KHO、#16 dm-crypt、#18 crashkernel-CMA、#39 vdso-auxclock、#44 ptrace-live-x0，共 6 条。

## 摘要

| 子主题 | 系列数 | ALREADY | PORTABLE | PATTERN | N-A |
|---|---|---|---|---|---|
| boot-head | 10 | 1 | 2 | 5 | 2 |
| kexec-crash | 19 | 3 | 4 | 6 | 6 |
| vdso | 14 | 2 | 8 | 1 | 3 |
| signal-ptrace-elf | 16 | 1 | 5 | 2 | 8 |
| **合计** | **59** | **7** | **19** | **14** | **19** |

**核心判据（先查基线，多判 ALREADY）**：
- riscv 已在**新版通用 vdso 底座**上：`arch/riscv/kernel/vdso.c:16` 已 `#include <linux/vdso_datastore.h>`，`asm/vdso/gettimeofday.h:64` 已用 `struct vdso_time_data` → vdso 核心重构系列（#42/#43）判 **ALREADY**。
- riscv kexec 三个 loader 均 `struct kexec_buf kbuf = {}`（零初始化）→ kexec_buf 初始化/`random` 字段系列（#21/#23/#24）判 **ALREADY**（#23 系列内已含 riscv 补丁）。
- riscv `ptrace.c` 已全面使用 `USER_REGSET_NOTE_TYPE()`（:377/:386/…）→ regset note-name 系列（#56）判 **ALREADY**。
- riscv fixmap 已 `NR_FIX_BTMAPS = SZ_256K/PAGE_SIZE`（fixmap.h:46）→ 256K early_ioremap（#1）判 **ALREADY**。

**Top 候选（按价值排序）**：
1. **#18 crashkernel CMA 预留**（PATTERN，~4 行）— 通用 `reserve_crashkernel_cma()` 已在树内，riscv 只差在 `arch/riscv/mm/init.c` 接线。
2. **#16/#19 dm-crypt 密钥传给 kdump**（PATTERN，1 行调用）— 通用 `kernel/crash_dump_dm_crypt.c` 已存在，riscv 未调用。
3. **#44 ptrace live-x0（seccomp/audit）**（PATTERN）— riscv `syscall.h:71` 同样用 `orig_a0`，**共享同一缺陷**。
4. **#13 KHO radix/scratch 泛化**（PORTABLE）— `kernel/liveupdate/kexec_handover.c` 架构无关，riscv 接入 KHO 时直接受益。
5. **#39 vdso 辅助时钟**（PORTABLE）— 纯通用 `include/vdso/`+`kernel/time`，riscv `vgettimeofday.c` 自动受益。
6. **#7 livepatch 晚期模块重定位**（PORTABLE 通用锁 + PATTERN arch text-poke）— riscv 有 `patch.c` 但缺 LIVEPATCH，属前瞻模式。

---

## Top 可移植候选（深度）

### #18 arm64: kexec: crashkernel CMA reservation — **PATTERN**（高价值）
- **原补丁**：`[v2] arm64: kexec: Add support for crashkernel CMA reservation`（https://patchwork.kernel.org/project/linux-arm-kernel/patch/20260126081334.699147-1-ruanjinjie@huawei.com/）state=new
- **可移植点**：通用底座**已就绪**——`include/linux/crash_reserve.h:32 reserve_crashkernel_cma()`、`kernel/crash_reserve.c:475`、`parse_crashkernel()` 已支持 `,cma` 后缀（SUFFIX_CMA）。arm64 diff 仅 3 处：`arch_reserve_crashkernel()` 增 `cma_size`、把 `parse_crashkernel(...&cma_size...)`（原 NULL）、追加 `reserve_crashkernel_cma(cma_size)`；`machine_kexec_file.c` 排除 CMA 区。
- **riscv 落点**：`arch/riscv/mm/init.c:1321 arch_reserve_crashkernel()`——当前 `parse_crashkernel(..., NULL, &high)` 传 NULL、且**未**调用 `reserve_crashkernel_cma()`，与 arm64 改前**逐行同构**；外加 `arch/riscv/kernel/machine_kexec_file.c` 少量排除逻辑。
- **判定**：**PATTERN**——通用 CMA 基础设施 ALREADY，riscv 仅需 ~4 行 arch 接线，落点精确、风险低。

### #16/#19 kdump: 传 dm-crypt(LUKS) 密钥给 kdump 内核 — **PATTERN**
- **原补丁**：`kdump: Enable LUKS-encrypted dump target support in ARM64 and PowerPC`（https://patchwork.kernel.org/project/linux-arm-kernel/patch/20260225060347.718905-2-coxu@redhat.com/）；及 arm64-only 版 `[v3] arm64/kdump: pass dm-crypt keys`（.../20260123081326.1362666-1-coxu@redhat.com/）
- **可移植点**：通用实现 `kernel/crash_dump_dm_crypt.c` + `include/linux/crash_core.h:93 crash_load_dm_crypt_keys()` **已在树内**；各 arch 仅在 kexec_file loader 里加**一行** `crash_load_dm_crypt_keys(image)`（x86 `kexec-bzimage64.c:527`、arm64 `machine_kexec_file.c:138`、ppc `elf_64.c` 均如此）。v5 系列 1/3 还把打印移出 arch 代码到通用层（进一步降低 arch 负担）。
- **riscv 落点**：`arch/riscv/kernel/machine_kexec_file.c`（当前无 dm_crypt 调用）加一行调用 + Kconfig `select` 依赖。
- **判定**：**PATTERN**——通用底座 ALREADY，arch 侧接近零成本。

### #44 arm64: ptrace: use live x0 for seccomp and audit — **PATTERN**（riscv 共享缺陷）
- **原补丁**：`[v2] arm64: ptrace: use live x0 for seccomp and audit after ptrace`（https://patchwork.kernel.org/project/linux-arm-kernel/patch/2f435bab0d61d0bf8fbaa54203525aae8e8f5371.1782384161.git.sunyiqixm@gmail.com/）state=new
- **可移植点**：arm64 修 `syscall_get_arguments()` 用 `regs->regs[0]`（活值）而非 `regs->orig_x0`（陈旧），使 ptracer 改过首参后 seccomp/audit 看到新值；`audit_syscall_entry` 同步改用 `regs->regs[0]`。
- **riscv 落点**：`arch/riscv/include/asm/syscall.h:71 args[0] = regs->orig_a0;`——**与 arm64 改前逐字同构**（riscv 亦有 `orig_a0`），极可能存在**同一缺陷**；对应改为 `regs->a0` 并核对 audit 路径。
- **判定**：**PATTERN**——非 riscv 已解决；同构模式，落点精确到单行。

### #13 mshv/KHO: 泛化 radix 树 + 扩展 scratch — **PORTABLE**（KHO 核心）/ N-A（mshv）
- **原补丁**：`mshv: enable kexec with Hyper-V donated pages and partitions`（https://patchwork.kernel.org/project/linux-arm-kernel/patch/20260528004204.1484584-11-jloeser@linux.microsoft.com/）state=new，RFC 20 patches
- **可移植点**：KHO（Kernel Hand-Over）框架**已在树内且架构无关**——`kernel/liveupdate/kexec_handover.c`、`include/linux/kexec_handover.h`、`include/linux/kho_radix_tree.h`、`mm/mm_init.c`（`CONFIG_KEXEC_HANDOVER`）。深挖的 10/20「extended scratch」仅动通用 `kexec_handover.c`+`mm/mm_init.c`。前序「generalize radix tree APIs / callbacks」纯通用。
- **riscv 落点**：无需 arch 改动即随通用 KHO 演进；riscv 接入 KHO/liveupdate 时自动受益。mshv/Hyper-V 分区部分 → **N-A**。
- **判定**：**PORTABLE**（KHO 通用核心）。

### #39 vdso: Add support for auxiliary clocks — **PORTABLE**
- **原补丁**：`vdso: Add support for auxiliary clocks`（https://patchwork.kernel.org/project/linux-arm-kernel/patch/20250701-vdso-auxclock-v1-10-df7d9f87b9b8@linutronix.de/）state=new，14 patches，arch=generic
- **可移植点**：深挖 10/14「Introduce aux_clock_resolution_ns()」仅动 `include/vdso/auxclock.h`+`kernel/time/timekeeping.c`；整个系列在通用 `lib/vdso/`、`vdso/vsyscall`、selftests 上做辅助时钟。
- **riscv 落点**：riscv 已在通用 vdso 底座（`vdso_datastore.h`/`vdso_time_data`），`arch/riscv/kernel/vdso/vgettimeofday.c` 自动获能，至多加一个 `__vdso_clock_*` 别名。
- **判定**：**PORTABLE**——纯通用时间/vdso 层。

### #7 livepatch, arm64/module: 晚期模块重定位（text-poke）— **PORTABLE**（通用锁）+ **PATTERN**（arch）
- **原补丁**：`livepatch, arm64/module: Enable late module relocations`（https://patchwork.kernel.org/project/linux-arm-kernel/patch/20250522205205.3408764-3-dylanbhatch@google.com/）state=new
- **可移植点**：1/2「Generalize late module relocation locking」把 livepatch 晚期重定位的加锁上提到通用 `kernel/`（PORTABLE）；2/2 arch 用 text-poke API 在已 RO 的模块正文上打补丁（`arch/arm64/kernel/module.c`，113 行）。
- **riscv 落点**：通用锁直接适用；arch 侧 `arch/riscv/kernel/module.c`（`apply_relocate_add`）+ 复用 `arch/riscv/kernel/patch.c`（`patch_text`/`__patch_insn_write`/`text_mutex`，已存在）。**注意**：riscv `Kconfig` **暂无 LIVEPATCH**（grep 无 `HAVE_LIVEPATCH`），故此为前瞻性模式，落地前需先使能 livepatch。
- **判定**：**PORTABLE**（通用锁）/ **PATTERN**（arch text-poke 重定位）。

---

## 全量判定表

### 子主题 A：boot-head（10）

| # | 系列 | arch | 判定 | 可移植点 | riscv 落点 | web_url |
|---|---|---|---|---|---|---|
| 1 | arm64: fixmap: Allow 256K early_ioremap() at any offset | arm | **ALREADY** | riscv fixmap 已 256K | `asm/fixmap.h:46 NR_FIX_BTMAPS=SZ_256K/PAGE_SIZE`（7 slots）；early_ioremap 走通用 `mm/early_ioremap.c` | .../20260708023514.2445926-1-pengyu@kylinos.cn/ |
| 2 | arm64: smp: Do not mark secondary CPUs possible under nosmp | arm | PATTERN(低) | nosmp 下不置 possible 的 bugfix | `arch/riscv/kernel/smpboot.c:58`（nosmp）`:173`（set_cpu_possible） | .../20260506090851.1858467-1-zhangpengjie2@huawei.com/ |
| 3 | firmware: sysfb: Consolidate config/code wrt. sysfb_primary_screen | other | **PORTABLE** | 通用 firmware/sysfb 框架整合（screen_info 重定位） | `drivers/firmware/sysfb*.c`（通用，无 riscv arch 改动） | .../20260402092305.208728-2-tzimmermann@suse.de/ |
| 4 | Exynos Thermal code improvement | generic | **N-A** | Samsung Exynos 温控驱动 | — （SoC 驱动） | .../20260214181930.238981-10-linux.amoon@gmail.com/ |
| 5 | arm64/boot: Zero-initialize idmap PGDs before use | arm | PATTERN(低) | 早期 idmap 页表清零 bugfix | `arch/riscv/kernel/head.S`/`mm/init.c`（riscv early PGD 在 BSS 已清零，多半 N/A） | .../20250822041526.467434-1-CFSworks@gmail.com/ |
| 6 | [v7] arm64/module: Use text-poke API for late relocations | arm | PATTERN | 已 RO 模块正文用 text-poke 打补丁 | `arch/riscv/kernel/module.c` + `patch.c`（依赖 livepatch） | .../20250603223417.3700218-1-dylanbhatch@google.com/ |
| 7 | livepatch, arm64/module: Enable late module relocations | arm | **PORTABLE**+PATTERN | 通用晚期重定位加锁上提 + arch text-poke | `kernel/livepatch/`（通用）；`arch/riscv/kernel/module.c`+`patch.c` | .../20250522205205.3408764-3-dylanbhatch@google.com/ |
| 8 | arm64/module: Enable late module relocations（v2） | arm | PATTERN | `aarch64_insn_copy`→`text_poke` 改名 + 模块 | `arch/riscv/kernel/patch.c`（命名）/`module.c` | .../20250412010940.1686376-3-dylanbhatch@google.com/ |
| 9 | [v2] arm64/kernel: Always use level 2 or higher for early mappings | arm | PATTERN | 早期映射粒度（避免细页早映射） | `arch/riscv/mm/init.c`（`create_kernel_page_table`/best_map_size） | .../20250311073043.96795-2-ardb+git@google.com/ |
| 10 | [v1] arm64: head.S: Do not trap access to MPAMSM_EL1 | arm | **N-A** | MPAM（资源分区）EL1 sysreg/EL2 trap，arm 专有 | — | .../20250205164630.1706058-1-tabba@google.com/ |

### 子主题 B：kexec-crash（19）

| # | 系列 | arch | 判定 | 可移植点 | riscv 落点 | web_url |
|---|---|---|---|---|---|---|
| 11 | [v3] iommu/arm-smmu-v3: Shrink queues in kdump kernel | arm | **N-A** | arm-SMMU 驱动内部（kdump 缩队列，思想可类比 riscv IOMMU） | — （HW 特定） | .../20260706084708.8072-1-kas@kernel.org/ |
| 12 | iommu/arm-smmu-v3: Fix device crash on kdump kernel | arm | **N-A** | arm-SMMU kdump 适配（思想类比 `drivers/iommu/riscv/`） | — （HW 特定） | .../bdb1e8c97159b87a8563a1f5e5f495b1d5cd734f.../ |
| 13 | mshv: enable kexec with Hyper-V donated pages / KHO | generic | **PORTABLE**/N-A | KHO radix/scratch 泛化（架构无关）；mshv 部分 N-A | `kernel/liveupdate/kexec_handover.c`（通用）；riscv 接入 KHO 时受益 | .../20260528004204.1484584-11-jloeser@linux.microsoft.com/ |
| 14 | arm64: kexec: Remove duplicate allocation for trans_pgd | arm | PATTERN(低) | trans_pgd 清理 | riscv 无 trans_pgd（`kexec_relocate.S` 恒等映射），多半 N/A | .../20260405114231.264761-1-wsw9603@163.com/ |
| 15 | arm64/kexec: Select KEXEC_BPF to support UEFI-style kernel image | arm | PATTERN | 用 BPF 解析镜像格式（通用 KEXEC_BPF 底座） | `arch/riscv/kernel/kexec_image.c`+Kconfig（可 select） | .../20260322014402.8815-11-piliu@redhat.com/ |
| 16 | kdump: Enable LUKS-encrypted dump target（dm-crypt）ARM64+PPC | arm | **PATTERN** | 通用 `crash_dump_dm_crypt.c` 已在树；arch 加 1 行调用 | `arch/riscv/kernel/machine_kexec_file.c`（加 `crash_load_dm_crypt_keys()`） | .../20260225060347.718905-2-coxu@redhat.com/ |
| 17 | vmcoreinfo: Expose hardware error recovery statistics via sysfs | generic | **PORTABLE** | 通用 vmcoreinfo/sysfs 统计 | `kernel/vmcore_info.c`+通用 sysfs（无 arch 改动） | .../20260202-vmcoreinfo_sysfs-v2-1-8f3b5308b894@debian.org/ |
| 18 | [v2] arm64: kexec: Add support for crashkernel CMA reservation | arm | **PATTERN** | 通用 `reserve_crashkernel_cma()` 已在树；arch ~4 行接线 | `arch/riscv/mm/init.c:1321 arch_reserve_crashkernel()` + `machine_kexec_file.c` | .../20260126081334.699147-1-ruanjinjie@huawei.com/ |
| 19 | [v3] arm64/kdump: pass dm-crypt keys to kdump kernel | arm | **PATTERN** | 同 #16（arm64-only 版），arch 1 行调用 | `arch/riscv/kernel/machine_kexec_file.c` | .../20260123081326.1362666-1-coxu@redhat.com/ |
| 20 | kexec: add kexec flag to control debug printing | arm | **PORTABLE** | 通用 kexec 调试 flag + 打印（`kernel/kexec*.c`） | `kernel/kexec_core.c`（通用）+ `arch/riscv/kernel/machine_kexec.c`（打印微调） | .../20251219093134.2268620-2-maqianga@uniontech.com/ |
| 21 | [v2] arm64: kernel: initialize missing kexec_buf->random field | arm | **ALREADY** | riscv `kbuf = {}` 已零初始化 `random` | `kexec_elf.c/kexec_image.c/machine_kexec_file.c`（均 `= {}`） | .../20251201105118.2786335-1-yeoreum.yun@arm.com/ |
| 22 | [v2] documentation/arm64 : kdump fixed typo errors | arm | **N-A** | arm64 kdump 文档纠错 | — （arm64 文档） | .../20250908111118.46666-2-hariconscious@gmail.com/ |
| 23 | kexec: Fix invalid field access | arm | **ALREADY** | **系列内已含 `[2/3] riscv: kexec: Initialize kexec_buf struct`** | `arch/riscv/kernel/*`（`kbuf = {}` 已合入） | .../20250827-kbuf_all-v1-3-1df9882bb01a@debian.org/ |
| 24 | arm64: kexec: Initialize kexec_buf struct in image_load() | arm | **ALREADY** | 同族 kexec_buf 初始化，riscv 已 `= {}` | `arch/riscv/kernel/kexec_image.c/kexec_elf.c` | .../20250826-akpm-v1-1-3c831f0e3799@debian.org/ |
| 25 | [PATCHv5,10/12] arm64/kexec: Add PE image format support | arm | PATTERN | kexec_file 支持 PE/COFF(EFI) 镜像的 arch loader | `arch/riscv/kernel/kexec_image.c`（新增 PE loader） | .../20250819012428.6217-11-piliu@redhat.com/ |
| 26 | documentation/arm64 : kdump fixed typo errors | arm | **N-A** | arm64 文档纠错（#22 早期版） | — | .../20250816120731.24508-1-hariconscious@gmail.com/ |
| 27 | printk: Fix panic log flush to serial console during kdump（PREEMPT_RT） | generic | **PORTABLE** | 通用 printk panic flush | `kernel/printk/`（无 arch 改动） | .../20250807112247.170127-1-cuiguoqi@kylinos.cn/ |
| 28 | [V2] rtc: zynqmp: Restore alarm functionality after kexec | generic | **N-A** | Xilinx Zynq RTC 驱动 | — （SoC 驱动） | .../20250730142110.2354507-1-harini.t@amd.com/ |
| 29 | rtc: zynqmp: Add shutdown callback for kexec support | generic | **N-A** | Zynq RTC 驱动 | — （SoC 驱动） | .../20250724170517.974356-1-harini.t@amd.com/ |

### 子主题 C：vdso（14）

| # | 系列 | arch | 判定 | 可移植点 | riscv 落点 | web_url |
|---|---|---|---|---|---|---|
| 30 | vDSO: Replace CONFIG_GENERIC_GETTIMEOFDAY ifdeffery with IS_ENABLED() | other | **PORTABLE** | **系列内含 `[6/7] clocksource/drivers/timer-riscv`** | `drivers/clocksource/timer-riscv.c` + 通用 vdso | .../20260709-vdso-arch-clockmodes-v1-1-3fd780bbf851@linutronix.de/ |
| 31 | vDSO: Respect COMPAT_32BIT_TIME | arm | **PORTABLE** | 通用 `time:` 部分；arch vdso32 (x86/arm/ppc) | `kernel/time/`（通用）；rv32 vdso（若需） | .../20260702-vdso-compat_32bit_time-v3-3-db9f36d8d432@linutronix.de/ |
| 32 | arm64: vdso: fix AArch32 compat init allocation leaks | arm | **N-A** | AArch32（32 位兼容 vdso）专属泄漏修复 | — （riscv compat 为 rv32-on-rv64，机制不同） | .../20260323214117.241216-1-osama.abdelkader@gmail.com/ |
| 33 | [1/4] arm64: xen/crypto/vdso: SPDX comment style | arm | **N-A** | 逐 arch 的 SPDX 注释风格（`.S` 文件） | — （cosmetic；riscv 文件独立） | .../20260301003853.2504449-1-objecting@objecting.org/ |
| 34 | vDSO: header file cleanups | arm | **PORTABLE** | 通用 vdso 头文件卫生（显式 include），跨 arch | `arch/riscv/.../vdso/*.h`（同类整理） | .../20260227-vdso-header-cleanups-v2-15-35d60acf7410@linutronix.de/ |
| 35 | vDSO: Provide clock_getres_time64() where applicable | arm | **PORTABLE** | 通用 vdso + selftests（32 位 time64） | 通用 `lib/vdso/` + `tools/testing/selftests/vDSO/` | .../20251223-vdso-compat-time32-v1-7-97ea7a06a543@linutronix.de/ |
| 36 | vdso: Various cleanups | arm | **PORTABLE** | **系列内含 `[06/11] riscv: vdso: Untangle kconfig logic`** | `arch/riscv/kernel/vdso/` + Kconfig | .../20250826-vdso-cleanups-v1-7-d9b65750e49f@linutronix.de/ |
| 37 | arm64: uapi: Provide correct __BITS_PER_LONG for the compat vDSO | arm | **N-A** | AArch32 compat vdso uapi 专属 | — | .../20250821-vdso-arm64-compat-bitsperlong-v1-2-700bcabe7732@linutronix.de/ |
| 38 | vdso/gettimeofday: Fix code refactoring | generic | **PORTABLE** | 通用 vdso 重构 bugfix | `lib/vdso/`（通用，无 arch 改动） | .../20250710062249.3533485-1-m.szyprowski@samsung.com/ |
| 39 | vdso: Add support for auxiliary clocks | generic | **PORTABLE** | 通用辅助时钟（`include/vdso/`+`kernel/time`+`lib/vdso`） | 通用；`arch/riscv/kernel/vdso/vgettimeofday.c` 自动受益 | .../20250701-vdso-auxclock-v1-10-df7d9f87b9b8@linutronix.de/ |
| 40 | vdso: Work around and reject absolute relocations | arm | **PORTABLE**+PATTERN | 通用「构建期拒绝绝对重定位」；arm64 GCC 绕过为 arch | 通用 vdso 构建 + `arch/riscv/kernel/vdso/Makefile` | .../20250430-vdso-absolute-reloc-v2-2-5efcc3bc4b26@linutronix.de/ |
| 41 | arm64: vdso: Use __arch_counter_get_cntvct() | arm | PATTERN(低) | arm 通用定时器计数器访问重构 | riscv 用 `rdtime`（`asm/vdso/gettimeofday.h` 已有自有访问器） | .../20250407-arm-vdso-v1-1-7012de25b195@debian.org/ |
| 42 | vdso: Rework struct vdso_time_data and introduce struct vdso_clock | arm | **ALREADY** | riscv 已用 `struct vdso_time_data` | `asm/vdso/gettimeofday.h:64`（已合入通用底座） | .../20250303-vdso-clock-v1-1-c1b5c69a166f@linutronix.de/ |
| 43 | vDSO: Introduce generic data storage | arm | **ALREADY** | riscv 已 `#include <linux/vdso_datastore.h>` | `arch/riscv/kernel/vdso.c:16` | .../20250204-vdso-store-rng-v3-3-13a4669dfc8c@linutronix.de/ |

### 子主题 D：signal-ptrace-elf（16）

| # | 系列 | arch | 判定 | 可移植点 | riscv 落点 | web_url |
|---|---|---|---|---|---|---|
| 44 | [v2] arm64: ptrace: use live x0 for seccomp and audit after ptrace | arm | **PATTERN** | 首参用活值而非陈旧 orig；riscv **共享同缺陷** | `arch/riscv/include/asm/syscall.h:71`（`orig_a0`→`a0`）+ audit 路径 | .../2f435bab0d61d0bf8fbaa54203525aae8e8f5371.../ |
| 45 | [v3] kselftest/arm64: Include <asm/ptrace.h> for user_gcs definition | arm | **N-A** | arm64 GCS selftest 构建修复 | — （riscv 有自有 CFI/Zicfiss selftest） | .../20260429-selftests_arm64_gcc15-v3-1-7fd68be56b83@arm.com/ |
| 46 | crypto: Standalone crypto module | generic | **PORTABLE** | 通用 crypto + 从内存加载模块（架构无关） | `crypto/`、`kernel/module/`（非 arch） | .../20260418002032.2877-9-wanjay@amazon.com/ |
| 47 | [1/3] fs: fix architecture-specific compat_ftruncate64 | generic | **PORTABLE** | 通用 fs compat 系统调用清理 | `fs/`（通用）；riscv rv32 compat 受益 | .../20260323070205.2939118-4-hch@lst.de/ |
| 48 | crypto: Standalone crypto module (Series 1/4): Core implementation | generic | **PORTABLE** | 同 #46（早期版），通用 crypto/module | `crypto/`、`kernel/module/` | .../20260212024228.6267-9-wanjay@amazon.com/ |
| 49 | [v2] arm64: poe: fix stale POR_EL0 values for ptrace | arm | **N-A** | POE（Permission Overlay，POR_EL0）arm 专有 ISA | — （无 riscv 对应） | .../20260127133926.2677180-1-joey.gouly@arm.com/ |
| 50 | perf annotate arch clean up | generic | **PORTABLE** | perf 用户态工具清理（constify、泄漏修复） | `tools/perf/`（工具） | .../20260122213516.671089-7-irogers@google.com/ |
| 51 | arm64: ptrace: fix hw_break_set() to set addr and ctrl together | arm | **N-A** | arm64 HW 断点 ptrace regset | — （riscv 无等价 HW-breakpoint regset） | .../20251018133731.42505-2-b10902118@ntu.edu.tw/ |
| 52 | Introduce kmemdump | generic | **PORTABLE** | 通用 kmemdump + coreimage ELF + vmcore_info 注册（RFC） | `kernel/`、`mm/`（通用核心）；qcom 后端 N-A | .../20250912150855.2901211-3-eugen.hristev@linaro.org/ |
| 53 | kselftest/arm64: Don't open code SVE_PT_SIZE() in fp-ptrace | arm | **N-A** | arm64 SVE ptrace selftest | — （SVE→RVV；riscv 有自有向量 ptrace 测试） | .../20250812-arm64-fp-trace-macro-v1-1-317cfff986a5@kernel.org/ |
| 54 | [v3] remoteproc: imx_dsp_rproc: recovery + coredump | generic | **N-A** | NXP i.MX DSP remoteproc 驱动 | — （SoC 驱动） | .../20250722075225.544319-1-shengjiu.wang@nxp.com/ |
| 55 | remoteproc: imx_dsp_rproc: coredump + recovery（v2） | generic | **N-A** | 同上 NXP 驱动 | — | .../20250704052529.1040602-3-shengjiu.wang@nxp.com/ |
| 56 | [05/23] ARM: ptrace: Use USER_REGSET_NOTE_TYPE() | arm | **ALREADY** | riscv `ptrace.c` 已全面用 `USER_REGSET_NOTE_TYPE()` | `arch/riscv/kernel/ptrace.c:377/386/396/406/416`… | .../20250701135616.29630-6-Dave.Martin@arm.com/ |
| 57 | remoteproc: imx_dsp_rproc: coredump + recovery | generic | **N-A** | 同上 NXP 驱动 | — | .../20250618062644.3895785-3-shengjiu.wang@nxp.com/ |
| 58 | [-next] arm64/ptrace: Fix stack-out-of-bounds read in regs_get_kernel_stack_nth() | arm | **PATTERN** | `regs_get_kernel_stack_nth()` OOB 读修复（kprobes/ftrace 用） | `arch/riscv/include/asm/ptrace.h`（核对 riscv 变体是否同缺陷） | .../20250604005533.1278992-1-wutengda@huaweicloud.com/ |
| 59 | arm64/ptrace: Make user_hwdebug_state.dbg_regs[] array size as ARM_MAX_BRP | arm | **N-A** | arm64 HW debug regset uapi（ARM_MAX_BRP） | — | .../20250421055212.123774-1-anshuman.khandual@arm.com/ |

---

## 备注（判定纪律回溯）
- **勿误报为「新可移植」**：vdso 核心底座（#42/#43）、kexec_buf 初始化（#21/#23/#24）、regset note-name（#56）、256K fixmap（#1）riscv **均已具备** → ALREADY。
- **通用底座已在树、arch 仅需接线**的三条最值得做：#18（crashkernel CMA）、#16/#19（dm-crypt 密钥）、#44（ptrace live 首参，且 riscv 同缺陷）。
- **arm 专属 HW/ISA** 判 N-A：MPAM(#10)、arm-SMMU(#11/#12)、POE(#49)、HW-breakpoint/SVE regset(#51/#53/#59)、SoC 驱动(#4/#28/#29/#54/#55/#57)、AArch32 compat vdso(#32/#37)。
