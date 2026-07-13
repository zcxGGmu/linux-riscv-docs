# generic-cross 可移植性分析（linux-arm-kernel → RISC-V）— shard 1

> 输入：`data/by_category/generic-cross.0.jsonl`（236 条系列，全部 tier=A / arch=generic）。
> 本桶为「无 arch 前缀的通用/跨架构补丁」，但绝大多数是**被抄送到 arm-list 的驱动/子系统噪声**
> （USB/Bluetooth/ALSA/fbdev/EDAC/clocksource SoC 驱动/staging/arm_mpam/arm-cca/CoreSight）。
> 本文价值在于**从噪声中挑出真正对 arch 有意义的通用核心改动**（uaccess/preempt/futex/sched/trace-core/
> arch_topology/word-at-a-time/OF-core/printk）。同质驱动噪声合并成组计数。

## 摘要

- **系列总数**：236
- **四态计数**：
  - **PORTABLE（arch 相关的通用核心 / 值得关注）**：约 27 条
  - **PORTABLE（通用 infra/build/tooling，自动适用但 arch 意义低）**：约 24 条
  - **N-A / 不相关（驱动/SoC/ARM 硬件/讨论帖/pull-req/stable 回合）**：约 184 条
  - **riscv-native（本身即 RISC-V 补丁，无需移植）**：1 条（#137）
  - **ALREADY**：0（通用桶，不映射到既有 riscv arch 特性；#137 属 riscv 原生）
- **判定要点**：真正落在 `kernel/`、`mm/`、`lib/`、`include/linux`、核心 `drivers/base`、`kernel/trace`、
  `scripts/`、`tools/perf` 且惠及所有架构 → PORTABLE（对 riscv 自动或几乎直接适用）；
  ARM 专有硬件/ISA（MPAM/CCA/CoreSight/SPE/arch-timer）与单一 SoC 驱动 → N-A。

### 本类 Top 候选（按 arch 价值排序）

1. **preempt: `__preempt_count_{sub,add}_return()`**（#229）— riscv 无 `asm/preempt.h`，走 `asm-generic/preempt.h`，通用改动直接生效；可选 arch 优化。
2. **uaccess: `scoped_user_access()` 系列**（#125/#126）+ **ASM-GOTO 安全包装 `unsafe_*_user()`**（#216）+ **`__user_write_access_begin()`**（#224）— 核心 uaccess 基础设施，riscv `uaccess.h` 已有对应 hook。
3. **Tracefs support for pKVM**（#122，30 patches）— 通用 `ring-buffer remotes`/`trace remotes`（`kernel/trace/`）可移植；pKVM 消费者为 ARM 专有 → 扩展通用底座。
4. **futex: Optimise size check `get_futex_key()`**（#6）— 纯 `kernel/futex/core.c`，PORTABLE 自动适用。
5. **arch_topology: stub `topology_core_has_smt()`**（#210）— riscv `smpboot.c` 用 arch_topology，直接受益。
6. **vfs/dcache `load_unaligned_zeropad()` RCU-sleep 修复**（#180/#176）— 触发点是 arch `word-at-a-time.h`；riscv 有 `load_unaligned_zeropad`。
7. **ring-buffer: persistent ring buffers 健壮化**（#82）— 通用 `kernel/trace` 引导持久化 trace。

## Top 可移植候选（深度）

### 1. preempt: Introduce `__preempt_count_{sub,add}_return()`（#229）
- **原补丁**：`[v13,04/17] preempt: Introduce __preempt_count_{sub,add}_return()`
  (https://patchwork.kernel.org/project/linux-arm-kernel/patch/20251013155205.2004838-5-lyude@redhat.com/) 状态=new
- **可移植点**：为 preempt-count 增加返回旧值的原子加/减原语（lazy-preemption 铺路）。curl 确认 diff 触及
  `include/asm-generic/preempt.h` + `arch/{arm64,s390,x86}/include/asm/preempt.h`。
- **riscv 落点**：riscv **无** `arch/riscv/include/asm/preempt.h`（本地核对：文件不存在），故使用
  `include/asm-generic/preempt.h` — 通用新原语**对 riscv 自动生效**；如需性能可后续新增 `arch/riscv/include/asm/preempt.h`。
- **判定**：**PORTABLE**（通用 fallback 直接适用；arch 优化为可选 PATTERN）。

### 2. uaccess: `scoped_user_access()` 更新 + const 修复（#125 / #126）
- **原补丁**：`uaccess: Updates to scoped_user_access()`
  (https://patchwork.kernel.org/project/linux-arm-kernel/patch/20260302132755.1475451-5-david.laight.linux@gmail.com/) 状态=new；
  及 `uaccess: Fix build of scoped user access with const pointer`
  (https://patchwork.kernel.org/project/linux-arm-kernel/patch/4e994e13b48420ef36be686458ce3512657ddb41.1772393211.git.chleroy@kernel.org/)
- **可移植点**：`__scoped_user_access()` 基于 `cleanup.h`（with()/and_with()）的作用域化用户访问，signal 路径改用之。
  curl 确认 diff 落 `include/linux/uaccess.h`（通用核心）。
- **riscv 落点**：通用 `include/linux/uaccess.h`；arch 侧依赖 `user_access_begin/end` —
  本地核对 `arch/riscv/include/asm/uaccess.h:456` 已定义 `user_access_begin`，故直接适用。
- **判定**：**PORTABLE**（核心 uaccess，riscv hook 已具备）。

### 3. uaccess: ASM-GOTO 安全包装 `unsafe_*_user()`（#216）+ `__user_write_access_begin()`（#224）
- **原补丁**：`[V6,02/12] uaccess: Provide ASM GOTO safe wrappers for unsafe_*_user()`
  (https://patchwork.kernel.org/project/linux-arm-kernel/patch/877bweujtn.ffs@tglx/)；
  `epoll: Save one stac/clac pair`（含 `uaccess: Add __user_write_access_begin()`）
  (https://patchwork.kernel.org/project/linux-arm-kernel/patch/20251023000535.2897002-2-kuniyu@google.com/)
- **可移植点**：为 `unsafe_get/put_user()` 提供 asm-goto 安全包装、新增 `__user_write_access_begin()`（省一对 stac/clac）。
- **riscv 落点**：`arch/riscv/include/asm/uaccess.h:473-476` 已有 `arch_unsafe_{put,get}_user`（本地核对），
  通用包装层直接覆盖 riscv；riscv 无 SMAP，stac/clac 对应为空但 API 一致。
- **判定**：**PORTABLE**（核心 uaccess 通用层）。

### 4. Tracefs support for pKVM（#122，30 patches）
- **原补丁**：`Tracefs support for pKVM`
  (https://patchwork.kernel.org/project/linux-arm-kernel/patch/20260309162516.2623589-6-vdonnefort@google.com/) 状态=new
- **可移植点**：curl 确认前半部为**通用**基础设施——`ring-buffer remotes`（从远端/hypervisor 读 ring buffer）、
  `trace remotes`（`include/linux/trace_remote.h`、`kernel/trace/trace_remote.c`、`kernel/trace/trace.c/.h`、Kconfig/Makefile）。
- **riscv 落点**：通用 `kernel/trace/` 直接适用；riscv 若发展自有 hypervisor/固件 trace 可复用该 remote 框架。
  pKVM（`arch/arm64/kvm/hyp`）消费者为 **ARM 专有 → N-A**。
- **判定**：**PORTABLE（通用 trace-remote 底座）+ N-A（pKVM 挂接）** — 典型「扩展通用底座」。

### 5. futex: Optimise the size check `get_futex_key()`（#6）
- **原补丁**：(https://patchwork.kernel.org/project/linux-arm-kernel/patch/20260701161736.xYYizA0e@linutronix.de/) 状态=new
- **可移植点**：curl 确认仅改 `kernel/futex/core.c`（1 file，1 行）—— futex key 大小检查优化。
- **riscv 落点**：纯通用 `kernel/futex/`，无 arch 依赖。
- **判定**：**PORTABLE**（自动适用所有架构）。

### 6. arch_topology: stub `topology_core_has_smt()`（#210）
- **原补丁**：`[v2,-next] arch_topology: Provide a stub topology_core_has_smt() for !CONFIG_GENERIC_ARCH_TOPOLOGY`
  (https://patchwork.kernel.org/project/linux-arm-kernel/patch/20251105103849.4093-1-yangyccccc@gmail.com/)
- **可移植点**：curl 确认改 `include/linux/arch_topology.h` —— 为未启用 GENERIC_ARCH_TOPOLOGY 的配置提供 stub。
- **riscv 落点**：本地核对 `arch/riscv/kernel/smpboot.c:12,54,240` 引入 `<linux/arch_topology.h>` 并调 `store_cpu_topology`，
  riscv 直接受益于该头文件修正。
- **判定**：**PORTABLE**。

### 7. vfs: `load_unaligned_zeropad()` RCU/might-sleep 修复（#180 / #176）
- **原补丁**：`[RFC] vfs: Fix might sleep in load_unaligned_zeropad() with rcu read lock held`
  (https://patchwork.kernel.org/project/linux-arm-kernel/patch/20251126101952.174467-1-xieyuanbin1@huawei.com/)；
  `[Bug report] hash_name() may cross page boundary`
  (https://patchwork.kernel.org/project/linux-arm-kernel/patch/20251203014800.4988-1-xieyuanbin1@huawei.com/)
- **可移植点**：curl 确认改 `fs/dcache.c`、`fs/namei.c` 的 `load_unaligned_zeropad()` 调用点；根因是该原语跨页时的缺页/唤醒行为。
- **riscv 落点**：修复本体在通用 VFS（PORTABLE）；相关 arch 原语在 `arch/riscv/include/asm/word-at-a-time.h:59`
  `load_unaligned_zeropad`（本地核对存在），riscv 同样受影响、同样受益。
- **判定**：**PORTABLE**（通用 VFS 修复；arch word-at-a-time 相关）。

### 8. ring-buffer: Making persistent ring buffers robust（#82，7 patches）
- **原补丁**：(https://patchwork.kernel.org/project/linux-arm-kernel/patch/177751974458.2136606.11417873091855386539.stgit@mhiramat.tok.corp.google.com/) 状态=new
- **可移植点**：`kernel/trace/ring_buffer.c` 持久化 ring buffer（reserve_mem 引导保留区）在 panic 刷写、跳过无效 sub-buffer、校验等健壮化。
- **riscv 落点**：通用 `kernel/trace/`；riscv 支持 `reserve_mem`/persistent trace 即受益。
- **判定**：**PORTABLE**。

### 9. sched: 修复 rt/dl 线程 schedstats（#135 / #157）
- **原补丁**：`[v2,RESEND] sched: fix incorrect schedstats for rt and dl thread`
  (https://patchwork.kernel.org/project/linux-arm-kernel/patch/20260204115959.3183567-1-dengjun.su@mediatek.com/)
- **可移植点**：`kernel/sched/` rt/dl 调度类统计修正。
- **riscv 落点**：纯通用 `kernel/sched/`，无 arch 依赖。
- **判定**：**PORTABLE**。

### 10. of/irq: Handle explicit interrupt parent（#189）
- **原补丁**：(https://patchwork.kernel.org/project/linux-arm-kernel/patch/e89669c9b3a4fbac4a972ffadcbe00fddb365472.1763557994.git.geert+renesas@glider.be/)
- **可移植点**：`drivers/of/irq.c` 处理显式 `interrupt-parent` 解析。
- **riscv 落点**：通用 OF/DT 层；riscv 为 DT 主导架构，中断树解析直接适用。
- **判定**：**PORTABLE**。

### 11. printk cleanup - part 3 / nbcon（#162，19 patches）
- **原补丁**：(https://patchwork.kernel.org/project/linux-arm-kernel/patch/20251227-printk-cleanup-part3-v1-19-21a291bcf197@suse.com/)
- **可移植点**：`kernel/printk/` nbcon 控制台框架清理（console_is_usable/nbcon、suspend/resume 上下文、register_console_force）。
- **riscv 落点**：通用 printk/console 基础设施，所有架构共享。
- **判定**：**PORTABLE**。

### 12. arch,sysfb: 合并 screen/edid info（#186，6 patches）
- **原补丁**：(https://patchwork.kernel.org/project/linux-arm-kernel/patch/20251121135624.494768-4-tzimmermann@suse.de/)
- **可移植点**：`drivers/firmware/sysfb`+efi earlycon/sysfb 将 `screen_info`/`edid_info` 收敛到 `sysfb_primary_display`。
- **riscv 落点**：本地核对 `arch/riscv/kernel/image-vars.h:32` `__efistub_sysfb_primary_display = sysfb_primary_display`，
  riscv 经 EFI/sysfb 直接受影响，需跟随通用重构。
- **判定**：**PORTABLE**。

### 其他值得一提（PORTABLE，简述）
- **#39 kconfig: 移除 AutoFDO/Propeller 的 arch 专属配置** → 变通用，riscv 日后可选启用 PGO/Propeller（build infra）。
- **#150 integrity: `arch_ima_get_secureboot` integrity-wide** → 泛化 arch IMA secureboot hook，riscv 可补齐。
- **#99 rust: 抬升最低 Rust/bindgen 版本** → 影响含 riscv 在内所有支持 Rust 的架构。
- **#136/#140 perf 跨平台 KVM / 去 arch 目录依赖**、**#143 perf regs `perf_reg_name` 重构** → tools/perf 通用化，riscv perf 受益。
- **#174 KVM: 移除 `kvm_stats_desc` overlay**、**#226 cpu: stress-ng hard-lockup（printk/sched 上下文）** → 通用 KVM/cpu 核心。

## 全量判定表

> PORTABLE 逐条列出；N-A 噪声按子系统合并成组（含代表 web_url）。

### PORTABLE（arch 相关 / 通用核心，逐条）

| # | 系列 | 判定 | 可移植点 | riscv 落点 | web_url |
|---|---|---|---|---|---|
| 6 | futex: Optimise size check get_futex_key() | PORTABLE★ | futex key 大小检查 | kernel/futex/core.c | .../20260701161736.xYYizA0e@linutronix.de/ |
| 16 | char: mem: keep arch range checks overflow-safe | PORTABLE | phys 范围检查防溢出 | drivers/char/mem.c(+arch hook) | .../20260625085800.4505-1-alhouseenyousef@gmail.com/ |
| 39 | kconfig: remove arch-specific AutoFDO/Propeller | PORTABLE★ | PGO/Propeller 通用化 | kconfig / build | .../20260604195612.3757860-2-xur@google.com/ |
| 72 | tracing: Fix nr_subbufs in simple_ring_buffer_init_mm | PORTABLE | ring buffer 初始化修复 | kernel/trace/ | .../20260512135420.99194-1-devnexen@gmail.com/ |
| 82 | ring-buffer: persistent ring buffers robust | PORTABLE★ | 持久化 trace 健壮化 | kernel/trace/ring_buffer.c | .../177751974458.2136606...stgit@mhiramat.../ |
| 99 | rust: bump minimum Rust and bindgen | PORTABLE | Rust 工具链基线 | rust/ kbuild | .../20260405235309.418950-32-ojeda@kernel.org/ |
| 122 | Tracefs support for pKVM | PORTABLE★+N-A | trace/ring-buffer remotes(通用) | kernel/trace/trace_remote.c | .../20260309162516.2623589-6-vdonnefort@google.com/ |
| 125 | uaccess: Updates to scoped_user_access() | PORTABLE★ | scoped_user_access 核心 | include/linux/uaccess.h | .../20260302132755.1475451-5-david.laight.../ |
| 126 | uaccess: Fix scoped user access const ptr | PORTABLE | 同上 const 修复 | include/linux/uaccess.h | .../4e994e13...git.chleroy@kernel.org/ |
| 135 | sched: fix schedstats rt/dl thread (v2) | PORTABLE★ | rt/dl 调度统计 | kernel/sched/ | .../20260204115959.3183567-1-dengjun.su@mediatek.com/ |
| 136 | perf Cross platform KVM support | PORTABLE | perf kvm 跨平台 | tools/perf/ | .../20260203182640.3911987-3-irogers@google.com/ |
| 140 | perf kvm stat: Remove use of arch directory | PORTABLE | 同上 v1 | tools/perf/ | .../20260128074106.788156-1-irogers@google.com/ |
| 143 | perf regs: arch__sample_reg_masks→perf_reg_name | PORTABLE | perf regs 重构 | tools/perf/util | .../20260121021735.3625244-1-irogers@google.com/ |
| 147 | mm, swap: Restore swap_space attr (v2) | PORTABLE | swap_state 属性/防 panic | mm/swap_state.c | .../20260116062535.306453-2-robin.kuo@mediatek.com/ |
| 150 | integrity: arch_ima_get_secureboot integrity-wide | PORTABLE★ | 泛化 IMA secureboot hook | security/integrity(+arch) | .../20260115004328.194142-2-coxu@redhat.com/ |
| 151 | Restore swap_space attr (v1) | PORTABLE | 同 #147 | mm/swap_state.c | .../20260115001405.3513440-1-robin.kuo@mediatek.com/ |
| 157 | sched/rt: fix schedstats rt thread (v1) | PORTABLE | 同 #135 | kernel/sched/rt.c | .../20260108031309.2754003-1-dengjun.su@mediatek.com/ |
| 162 | printk cleanup - part 3 (nbcon) | PORTABLE★ | nbcon 控制台框架清理 | kernel/printk/ | .../20251227-printk-cleanup-part3-v1-19-...@suse.com/ |
| 174 | KVM: Remove kvm_stats_desc pseudo-overlay | PORTABLE | 通用 KVM stats | virt/kvm/ | .../20251205232655.445294-1-seanjc@google.com/ |
| 176 | hash_name() may cross page boundary (RCU) | PORTABLE★ | word-at-a-time 跨页 | fs/(+asm/word-at-a-time.h) | .../20251203014800.4988-1-xieyuanbin1@huawei.com/ |
| 180 | vfs: Fix might-sleep load_unaligned_zeropad rcu | PORTABLE★ | 同上，VFS 调用点 | fs/dcache.c,namei.c | .../20251126101952.174467-1-xieyuanbin1@huawei.com/ |
| 186 | arch,sysfb: move screen/edid into single place | PORTABLE★ | sysfb_primary_display 收敛 | drivers/firmware/sysfb(+arch) | .../20251121135624.494768-4-tzimmermann@suse.de/ |
| 189 | of/irq: Handle explicit interrupt parent | PORTABLE★ | OF 中断父节点解析 | drivers/of/irq.c | .../e89669c9...git.geert+renesas@glider.be/ |
| 210 | arch_topology: stub topology_core_has_smt() | PORTABLE★ | arch_topology 头修正 | include/linux/arch_topology.h | .../20251105103849.4093-1-yangyccccc@gmail.com/ |
| 216 | uaccess: ASM GOTO safe wrappers unsafe_*_user() | PORTABLE★ | unsafe_*_user asm-goto 包装 | include/linux/uaccess.h | .../877bweujtn.ffs@tglx/ |
| 224 | epoll + uaccess __user_write_access_begin() | PORTABLE | 省 stac/clac 的 uaccess API | include/linux/uaccess.h | .../20251023000535.2897002-2-kuniyu@google.com/ |
| 226 | cpu: fix hard lockup (printk/sched context) | PORTABLE | cpu 硬锁修复 | kernel/cpu.c,printk | .../20250918064907.1832-1-shechenglong@xfusion.com/ |
| 229 | preempt: __preempt_count_{sub,add}_return() | PORTABLE★ | preempt-count 返回旧值原语 | asm-generic/preempt.h(riscv 用) | .../20251013155205.2004838-5-lyude@redhat.com/ |

### PORTABLE（通用 infra/build/tooling，自动适用、arch 意义低；合并组）

| 组 | 代表系列(#) | 判定 | 说明 | 代表 web_url |
|---|---|---|---|---|
| kbuild/scripts 构建 | 27,130,133,138,191,214,236 | PORTABLE(低) | 模块链接/CFLAGS/FIT/build-id/efistub 链接等，所有 arch 共享 | .../20260612133139.1919042-1-petr.pavlu@suse.com/ |
| tracing/printk 头与配置 | 15,22,76,78 | PORTABLE(低) | trace_printk.h 迁移、BOOT_PRINTK_DELAY 移除 | .../20260625104402.210473477@kernel.org/ |
| kernel 核心杂项 | 43(params),53(cpu/hotplug smt) | PORTABLE(低) | pure_initcall/kobject warning | .../20260601101942.4002661-1-shashank.mahadasyam@sony.com/ |
| driver core / PM 核心 | 98,100,116,168,234 | PORTABLE(低) | dev accessors/fwnode flags/PM runtime/fw_devlink | .../20260406162231.v5.7...@changeid/ |
| lib / 通用工具 | 70(debugobjects),86(strscpy),164(dyndbg),231(Kconfig 文案) | PORTABLE(低) | 编译告警/字符串安全/动态调试 | .../20260513145425.1579430-1-arnd@kernel.org/ |
| tools/perf 通用 | 113(去 libunwind),221(auxtrace) | PORTABLE(低) | perf 构建/合成 id 助手 | .../20260321234220.848859-2-irogers@google.com/ |
| 安全/完整性调试 | 83(ima 调试) | PORTABLE(低) | late_initcall_sync 度量调试 | .../7734099f...camel@linux.ibm.com/ |
| gpiolib/clkdev 框架 | 10(gpio_name),194(MAX_DEV_ID) | PORTABLE(低) | 通用驱动框架小改 | .../20260629135917.1308621-1-arnd@kernel.org/ |

> 备注：#58「Arm32 string.h int→unsigned char」为 arch/arm 汇编字符串语义修正 —— 概念可类比，
> 但 riscv 主要用通用 `lib/string.c`，落点 `arch/riscv/lib/*`，判 **PATTERN(低)/大体 ALREADY**。
> #71「locking/hqlock_core」在主线无对应文件（疑似厂商/out-of-tree），暂判 **N-A（待核）**。
> #235「minmax.h 回合到 6.1.y」为 stable 反向移植（已在主线），判 **N-A（非新工作）**。
> #137「RISC-V: Skip stopping cycle counter」为 **riscv 原生补丁**（drivers/perf/riscv_pmu*），无需移植。

### N-A / 不相关（驱动/SoC/ARM 硬件/噪声，按子系统合并计数）

| 子系统组 | 大致条数 | 代表 #（web_url 见输入 JSONL） | 判定依据 |
|---|---|---|---|
| USB 驱动（dwc3/mtu3/xhci/gadget/udc/chipidea/ehci/ohci/typec/core） | ~34 | 3,14,17,18,19,29,32,46,48,55,73,80,104,117,148,155,169,200,219,220 | 单一 USB 控制器/glue 驱动，与 arch 移植无关 |
| Bluetooth（btmtk/btusb/btmtksdio/hci_bcm4377/h4） | ~18 | 7,23,34,41,47,54,62,68,103,105,110,158,166,173,188,217,222 | 蓝牙芯片驱动/ID |
| ALSA/hda | 8 | 172,175,190,201,205,206,207,208 | 声卡 codec 驱动 |
| fbdev | 6 | 35,59,60,81,124,152 | 帧缓冲驱动 |
| clocksource SoC 定时器驱动 | 8 | 11,31,36,52,109,112,134,203 | 具体 SoC 定时器（含 ARM arch-timer-mmio） |
| clk/samsung | 2 | 12,13 | Samsung 时钟驱动泄漏修复 |
| EDAC | 5 | 38,65,69,74,87 | 内存 ECC 驱动 |
| hwrng / RNG（含 m68k coldfire） | 4 | 8,21,181,183 | RNG 驱动/m68k arch |
| char/xilinx_hwicap | 3 | 20,42,170 | Xilinx ICAP 字符设备 |
| STM class / CoreSight STM | 9 | 49,50,75,101,141,161,171,185,218 | 系统 trace 模块驱动 |
| perf ARM 硬件（cs-etm/arm_spe/hisi-ptt） | 7 | 4,40,66,144,195,225,227 | CoreSight/SPE/HiSilicon PTT，ARM 专有 |
| perf Intel vendor events | 2 | 33,128 | Intel 事件 JSON |
| arm_mpam / fs/resctrl | 10 | 5,37,64,91,92,93,94,95,127,204 | ARM MPAM 资源分区；riscv 无 resctrl 后端 |
| virt: arm-cca-guest | 4 | 24,28,57,96 | ARM 机密计算（RSI/RMM），ARM 专有 |
| staging vc04/vchiq/RaspberryPi | 6 | 9,107,108,160,178,215 | Broadcom VideoCore |
| net 驱动（stmmac/smc91x/mt76/veth/netfilter） | 10 | 1,2,30,45,90,142,167,196,197,209 | 具体网卡/子系统驱动 |
| devfreq | 4 | 56,111,114,230 | devfreq 框架/驱动 |
| dts/board/SoC/power/pwm/gpu/mfd | ~14 | 44,115,121,123,129,145,146,179,187,211,213,232,233 | 板级/SoC/固件 |
| 驱动清理（FIELD_*/named-init/kmalloc_array/const/match_data） | ~10 | 61,63,80,89,119,139,159,184,26,84 | 机械式驱动清理 |
| media | 3 | 26,139,165 | 媒体驱动/测试 |
| efi arm/stmm | 3 | 132,199,223 | ARM EFI/standalone-MM |
| KVM arm nested / stage-2 | 1 | 67 | ARM 嵌套 stage-2 |
| ata | 1 | 159 | AHCI 驱动清理 |
| 讨论/报告/merge/mailmap/CREDITS/warning | ~7 | 88,153,163,182,192,228,58? | 非补丁或合并通知 |
| 其他杂项（uintptr/hqlock/minmax 回合等） | 3 | 71,119,235 | 见上「备注」 |

（以上 N-A 组合计约 184 条；逐条 web_url 均在 `generic-cross.0.jsonl` 对应行。）

## 结论

generic-cross shard-1 的 236 条中，**真正对 arch 有移植意义的通用核心改动约 27 条**，另有约 24 条通用
infra/build/tooling 会自动适用 riscv 但意义较低；其余约 184 条为被抄送到 arm-list 的驱动/SoC/ARM 硬件噪声（N-A）。
最高价值候选是 **uaccess 系列（#125/#126/#216/#224）**、**preempt 返回值原语（#229）**、
**pKVM 的通用 trace-remote 底座（#122）** 与 **arch_topology/word-at-a-time/futex/sched** 等核心修正——
它们要么对 riscv **自动生效**（走 asm-generic 或纯通用代码），要么 riscv 侧 hook（`uaccess.h`/`smpboot.c`/
`word-at-a-time.h`/`image-vars.h`）**已就位**，经本地源码核对确认落点存在。
