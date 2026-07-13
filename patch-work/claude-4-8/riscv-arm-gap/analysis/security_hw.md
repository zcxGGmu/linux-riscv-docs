# security-hw 可移植性分析（linux-arm-kernel → RISC-V）

> 类别：MTE/BTI/PAC/GCS/CFI/影子栈/pointer-masking/KASLR/通用硬化。
> 判定纪律：BTI→**Zicfilp**、GCS→**Zicfiss**、TBI/tagged-addr→**Supm** 均已在 riscv 落地
> （`arch/riscv/kernel/usercfi.c`/`process.c`）→ ALREADY/PATTERN；**MTE/PAC 无 riscv 对应 ISA → N-A**
> （除非扩展通用底座如 prctl/ABI）；通用硬化（KASLR/randomize_kstack/kCFI/spectre 通用缓解）→ PORTABLE。

## 摘要

- **系列总数**：45
- **判定计数**：ALREADY=1 / PORTABLE=8 / PATTERN=13 / N-A=23
- **深挖验证**：curl 取全文 6 条（#14/#43/#30/#5/#27/#15）+ Grep 核对 riscv 落点 8 处，全部路径已确认存在。

### 本类 Top 候选（按价值排序）

| # | 系列 | 判定 | riscv 落点 |
|---|---|---|---|
| 1 | Fix bugs and performance of kstack offset randomisation | **PORTABLE** | `arch/riscv/kernel/traps.c:338`（消费 `add_random_kstack_offset`）|
| 2 | per-function storage support | **PORTABLE**(框架)+PATTERN(arch) | `kernel/trace/kfunc_md.c`(新增通用) + `arch/riscv/kernel/ftrace.c` |
| 3 | iommufd: Cache invalidation hardening | **PORTABLE**(核心 1-3) | `drivers/iommu/iommufd/`（通用 uAPI 边界硬化）|
| 4 | kcfi: Prepare for GCC support | **PORTABLE**(通用底座) | `kernel/cfi.c`（`report_cfi_failure` 报告标准化）|
| 5 | arm64/gcs: Allow reuse of user managed shadow stacks | **PATTERN**+PORTABLE(prctl) | `arch/riscv/kernel/usercfi.c`（`save/restore_user_shstk`）|
| 6 | [v2] arm64/gcs: Fix error handling in arch_set_shadow_stack_status() | **PATTERN** | `arch/riscv/kernel/usercfi.c:384`（同名函数已存在）|
| 7 | arm64: insn: Route BTI to simulate_nop | **PATTERN** | `arch/riscv/kernel/probes/`（Zicfilp `lpad` 单步处理）|
| 8 | arm64: panic if IRQ shadow call stack allocation fails | **PATTERN** | `arch/riscv/kernel/irq.c:87`（`scs_alloc` for `irq_shadow_call_stack_ptr`）|

---

## Top 可移植候选（深度）

### 1. Fix bugs and performance of kstack offset randomisation —— PORTABLE
- **原补丁**：https://patchwork.kernel.org/project/linux-arm-kernel/patch/20260303150840.3789438-2-ryan.roberts@arm.com/ 状态=new（v5, 2 patches, arch=generic）
- **可移植点**：patch1「Maintain kstack_offset per task」把 `kstack_offset` 从 per-CPU 改为 per-task（触及
  `include/linux/randomize_kstack.h`、`include/linux/sched.h`、`init/main.c`、`kernel/fork.c`——**全部通用**）；
  patch2「Unify random source across arches」统一各架构随机源。curl 确认 diffstat 仅 4 个通用文件。
- **riscv 落点**：riscv 在 `arch/riscv/kernel/traps.c:338` 已调用 `add_random_kstack_offset()`（syscall 入口）。
  本系列改的是**通用框架内部实现**，riscv 作为消费者**自动受益**，无需 arch 改动。
- **判定**：**PORTABLE**——纯通用 `kernel/`+`include/linux/` 改动，riscv 已是既有用户，直接适用。

### 2. per-function storage support —— PORTABLE（通用框架）+ PATTERN（arch 实现）
- **原补丁**：https://patchwork.kernel.org/project/linux-arm-kernel/patch/20250303132837.498938-3-dongml2@chinatelecom.cn/ 状态=new（v4, 4 patches）
- **可移植点**：patch2「add per-function metadata storage」**新建通用框架** `include/linux/kfunc_md.h` +
  `kernel/trace/kfunc_md.c`（curl 确认 `create mode 100644`，266 行纯通用）；为每函数关联元数据（用于 ftrace/fprobe 等）。
  patch1/3 为 x86（ibt/fineibt offset），patch4 为 arm64 实现。
- **riscv 落点**：通用框架落 `kernel/trace/kfunc_md.c`（riscv 直接可用）；arch 侧「按函数前导字节存元数据」需仿 arm64/x86
  在 `arch/riscv/kernel/ftrace.c` / 函数 padding（`-fpatchable-function-entry`，riscv 已用于 ftrace）落地。
- **判定**：**PORTABLE**（通用存储框架）+ **PATTERN**（arch 侧 padding 元数据实现，riscv 已有 patchable-entry 基础）。

### 3. iommufd: Cache invalidation hardening and SMMUv3 batching rework —— PORTABLE（核心）
- **原补丁**：https://patchwork.kernel.org/project/linux-arm-kernel/patch/00748c5cbea95a938d032269001a598203b06bbc.1780521606.git.nicolinc@nvidia.com/ 状态=new（4 patches, arch=arm）
- **可移植点**：patch1「Set upper bounds on cache invalidation entry_num and entry_len」+ patch3「Avoid copying the
  user array twice in the full-array copy helper」是 **iommufd 核心 uAPI 边界硬化**（防用户传入越界 entry_num/len），
  与具体 IOMMU 硬件无关；patch2 为 iommufd selftest。仅 patch4「arm-smmu-v3: Process vIOMMU invalidations in batches」
  是 SMMUv3 专属（curl 确认 patch4 只改 `drivers/iommu/arm/arm-smmu-v3/arm-smmu-v3-iommufd.c`）。
- **riscv 落点**：`drivers/iommu/iommufd/`（通用框架）。riscv IOMMU（`drivers/iommu/riscv/`）经 iommufd 暴露嵌套
  失效 uAPI 时，同样需要这层入参边界校验——安全硬化直接适用。
- **判定**：patch1/3 **PORTABLE**（通用 iommufd 安全底座），patch4 **N-A**（SMMUv3 专属），patch2 selftest PORTABLE。

### 4. kcfi: Prepare for GCC support —— PORTABLE（通用 kCFI 底座）
- **原补丁**：https://patchwork.kernel.org/project/linux-arm-kernel/patch/20250904034656.3670313-2-kees@kernel.org/ 状态=new（v2, 9 patches, arch=other）
- **可移植点**：系列含大量**通用 kCFI 底座**：patch1「Move `__nocfi` out of compiler-specific header」
  （`include/linux/compiler_types.h`）、「Document `cfi=` bootparam」、「Standardize on common "CFI:" prefix for CFI
  reports」、「Add "debug" option to cfi=」。这些是跨架构 kCFI 基础设施，为 GCC kCFI 铺路。x86 专属部分（traps 布局、
  retpoline 清理）N-A。
- **riscv 落点**：riscv 已走通用 `kernel/cfi.c`（Grep 确认 `report_cfi_failure()` 输出 "CFI failure at %pS"，
  `cfi_warn`/`ARCH_USES_CFI_TRAPS`），并 `select ARCH_SUPPORTS_CFI`（`arch/riscv/Kconfig:65`）。报告前缀标准化与
  `cfi=` bootparam 统一**直接惠及 riscv kCFI**；GCC kCFI 支持成熟后 riscv 亦可受益。
- **判定**：**PORTABLE**（通用 kCFI 报告/bootparam/属性标准化），x86 硬件细节 N-A。

### 5. arm64/gcs: Allow reuse of user managed shadow stacks —— PATTERN + PORTABLE（prctl ABI）
- **原补丁**：https://patchwork.kernel.org/project/linux-arm-kernel/patch/20250921-arm64-gcs-exit-token-v1-1-45cf64e648d5@kernel.org/ 状态=new（RFC, 3 patches）
- **可移植点**：新增 `PR_SHADOW_STACK_EXIT_TOKEN` 语义——线程退出时在其 GCS 顶写入 token，使用户态可复用已退出线程的
  影子栈。curl 确认 patch1 触及 **`include/uapi/linux/prctl.h`（通用 ABI）** + `arch/arm64/mm/gcs.c`（arch 实现）。
  GCS→**Zicfiss**：riscv 影子栈机制等价。
- **riscv 落点**：`arch/riscv/kernel/usercfi.c` 已有 `save_user_shstk`/`restore_user_shstk`/`create_rstor_token`
  （Grep 确认 `usercfi.c:159/183/207`）——「退出 token / 复用」概念可直接映射到这套 token 原语；prctl 常量属通用 uAPI。
- **判定**：**PORTABLE**（`prctl.h` ABI 常量）+ **PATTERN**（riscv `usercfi.c` 侧实现 exit-token 写入）。

### 6. [v2] arm64/gcs: Fix error handling in arch_set_shadow_stack_status() —— PATTERN
- **原补丁**：https://patchwork.kernel.org/project/linux-arm-kernel/patch/20260202-arm64_cgs-v2-1-e6a837edf021@debian.org/ 状态=new（1 patch）
- **可移植点**：修复 `arch_set_shadow_stack_status()` 中启用失败后的错误处理/状态回滚。此函数是 `PR_SHADOW_STACK_ENABLE`
  prctl 的 arch 后端，为通用影子栈 ABI 的架构实现点。
- **riscv 落点**：**riscv 已有同名函数** `arch/riscv/kernel/usercfi.c:384 arch_set_shadow_stack_status`
  （Grep 确认；另有 `arch_get_…:371`、`arch_lock_…:438`）。arm64 的错误处理修复思路应对照检查 riscv 版本是否有同类回滚缺陷。
- **判定**：**PATTERN**——机制/接口对等，riscv 侧按同一 bug 模式自检并修复。

### 7. arm64: insn: Route BTI to simulate_nop to avoid XOL/SS at function entry —— PATTERN
- **原补丁**：https://patchwork.kernel.org/project/linux-arm-kernel/patch/20260217133855.3142192-3-khaja.khaji@oss.qualcomm.com/ 状态=new（v2, 2 patches）
- **可移植点**：探针（kprobes/uprobes）落在函数入口的 **BTI 落地指令**上时，走 `simulate_nop` 而非 XOL/单步，避免破坏
  分支目标校验。BTI→**Zicfilp**：riscv 的 `lpad`（landing pad）指令在函数入口有同样角色。
- **riscv 落点**：`arch/riscv/kernel/probes/`（`decode-insn.c` 分派 + `simulate-insn.c` 已有 `simulate_jal/jalr/...`
  一族 simulate 函数，Grep 确认）。riscv 开启 Zicfilp 后，探针落在 `lpad` 上需同样路由到「模拟 NOP」以免破坏落地页语义。
- **判定**：**PATTERN**——riscv `probes/` 需为 `lpad` 增加与 BTI 等价的 simulate 处理。

### 8. arm64: panic if IRQ shadow call stack allocation fails —— PATTERN
- **原补丁**：https://patchwork.kernel.org/project/linux-arm-kernel/patch/20260324161545.5441-1-osama.abdelkader@gmail.com/ 状态=new（1 patch）
- **可移植点**：IRQ 影子调用栈分配失败时直接 `panic()`（避免继续运行到无 SCS 保护的中断路径）。属 SCS 初始化硬化。
- **riscv 落点**：**riscv 已有 IRQ SCS**：`arch/riscv/kernel/irq.c:87` `s = scs_alloc(cpu_to_node(cpu))` 为
  per-cpu `irq_shadow_call_stack_ptr` 分配（Grep 确认 `irq.c:72-87`、`asm/scs.h`、`CONFIG_SHADOW_CALL_STACK`）。
  同一「分配失败即 panic」硬化可平移到 riscv 的 IRQ SCS 分配点。
- **判定**：**PATTERN**——riscv `irq.c` 的 `scs_alloc` 返回值检查处加同等硬化。

---

## 其余 PATTERN / PORTABLE（简述）

- **static_call: use CFI-compliant return0 stubs**（generic，PORTABLE）——修 `kernel/static_call.c`
  `__static_call_return0`（Grep 确认存在），使 return0 stub 满足 kCFI 类型哈希。riscv 用 static_call（`paravirt.c`）
  + `select ARCH_SUPPORTS_CFI`，通用改动直接适用。web_url: .../20260311225822.1565895-1-cmllamas@google.com/
- **Resolve ARM kCFI build failure in idpf xsk.c**（arm，PORTABLE+PATTERN）——patch1 引入 `__nocfi_generic`
  （**已在本树** `include/linux/compiler_types.h:495-498`，随 `CONFIG_ARCH_USES_CFI_GENERIC_LLVM_PASS`）；
  patch3 为通用 `libeth` 驱动。riscv 若命中同类「generic LLVM CFI pass」问题，可仿 patch2 `select` 该 Kconfig（PATTERN）。
- **arm64/gcs: Flush the GCS locking state on exec**（arm，PATTERN）——exec 时清影子栈 lock 状态。riscv
  `usercfi.c` 有 `set_shstk_lock`/`is_shstk_locked`（Grep 确认），落点 `arch/riscv/kernel/process.c` `flush_thread` 邻域。
- **arm64/gcs: Don't call gcs_free() when releasing task_struct** / **…during flush_gcs()**（arm，PATTERN×2）——
  影子栈释放生命周期修复；riscv 对应 `usercfi.c` `shstk_release`（`usercfi.c:342`），需对照生命周期正确性。
- **arm64/gcs: Don't try to access GCS registers if arm64.nogcs is enabled**（arm，PATTERN 弱）——cmdline 关闭时
  避免访问 GCS CSR；riscv 对应 `nousercfi`/Zicfiss 关闭路径，落点 `usercfi.c`。
- **arm64: gcs: Honour mprotect(PROT_NONE) on shadow stack**（#15 patch2，arm，PATTERN）——curl 确认改
  `arch/arm64/mm/mmap.c`；riscv 影子栈 VMA 已用 `VM_SHADOW_STACK`（Grep 确认 `arch/riscv/mm/pgtable.c:170/178`、
  `mm/mmap.c:650`），PROT_NONE 语义应在 riscv 侧同样校验。同系列 patch1（PTE_SHARED/LPA2）N-A（arm64 页表位专属）。
- **KVM: arm64: Provide guest support for GCS**（arm，PATTERN 弱）——KVM 虚拟化影子栈；riscv KVM
  （`arch/riscv/kvm/`）尚无 Zicfiss guest 支持，机制类比但需大量 arch 重写（arm64 用 FGT/PSTATE.EXLOCK/ERET 模拟）。
- **arm64 kaslr 系列**（#38 nokaslr cmdline / #42 linear region warning / #44 parange，arm，PATTERN 弱）——riscv
  KASLR 在 `arch/riscv/kernel/pi/`（位置无关早期码，_baseline §5）；cmdline 解析/线性区随机化告警思路可参考，但
  arm64 线性映射布局（linear_region_size/parange）与 riscv 差异大，价值低。
- **string: Disable read_word_at_a_time() optimizations if kernel MTE**（arm，PORTABLE 但惰性）——改通用
  `lib/string`/`include`，但以 `CONFIG_KASAN_HW_TAGS`(MTE) 为门；riscv 无 HW_TAGS，落地后**对 riscv 无实际效果**。
- **nvmem: apple-spmi-nvmem: wrap regmap calls to satisfy CFI**（generic，PORTABLE 低值）——「包装间接调用以满足
  kCFI 类型」是通用模式，但驱动为 Apple SoC 专属，riscv 一般不构建。

---

## N-A 分组（依赖 ARM 专有 HW/ISA，无 riscv 对应、不扩展通用底座）

- **MTE（内存标签）共 6 条**：#11 TFSR_EL1 checks、#18/#23 PSTATE.TCO 优化、#25 copy_highpage 已标记、#26 zero page
  PG_mte_tagged。**riscv 无 MTE ISA**（仅 Supm 指针掩码，掩码≠标签检查，_baseline §9/§14）→ 全 **N-A**。
- **Spectre/branch-predictor 硬件缓解共 6 条**：#19 TSV110 BHB、#20 ARM32 branch predictor hardening、#22 arm spectre
  lockup（printk-in-sched 触发点绑定 arm spectre 路径）、#37/#39 ARM32 spectre-v2、#40 HIP09 BHB、#45 proton-pack
  Spectre-BSE（Cortex-A7x）。均绑定 **ARM CPU 型号/分支预测器硬件**（`arch/arm64/kernel/proton-pack.c` 等）→ **N-A**。
  （riscv 侧 spectre 类缓解走 errata/厂商框架，机制不同。）
- **arm64 patch-scs（dynamic SCS 动态打补丁）共 2 条**：#7/#12 `advance_loc4`——arm64 `patch-scs.c` 解析 `.eh_frame`
  动态插桩 SCS；riscv **无 dynamic SCS patching**（仅编译期 SCS）→ **N-A**。
- **KVM/pKVM + GIC/ITS/PSCI 共 2 条**：#9 pkvm PSCI relay、#13 ITS hardening for pKVM（14 patches，GIC/ITS/MMIO
  donate）→ ARM 中断控制器 + pKVM 固件专属 → **N-A**。
- **OMAP/板级 CFI-type 共 2 条**：#4/#6 OMAP4 `finish_suspend` CFI 类型——OMAP SoC 专属回调 → **N-A**。
- **ARM32 CFI hw-breakpoint 共 2 条**：#1/#2「CFI breakpoints only on demand」——arm32 用**硬件断点**实现 kCFI BUG；
  riscv kCFI 走 trap（`ebreak`/`ARCH_USES_CFI_TRAPS`），机制不同 → **N-A**。
- **arm64 GCS selftest/firmware 共 3 条**：#28 basic-gcs CFLAGS、#31 basic-gcs 清理、#33 boot-wrapper-aarch64 启用
  GCS（arm 固件项目，非内核）→ **N-A**（riscv 有独立 CFI selftest）。

---

## 全量判定表

| # | 系列 | arch | 判定 | 可移植点(若有) | riscv落点(若有) | web_url |
|---|---|---|---|---|---|---|
| 1 | [v4] ARM: breakpoint: CFI breakpoints only on demand | arm | N-A | — | — | [link](https://patchwork.kernel.org/project/linux-arm-kernel/patch/20260703-arm32-cfi-bug-v4-1-c26acb640a8f@kernel.org/) |
| 2 | [v2] RFC: ARM: breakpoint: CFI breakpoints only on demand | generic | N-A | arm32 hw-breakpoint 实现 kCFI；riscv 走 trap | — | [link](https://patchwork.kernel.org/project/linux-arm-kernel/patch/20260701-arm32-cfi-bug-v2-1-9bf922593e00@kernel.org/) |
| 3 | [RESEND] nvmem: apple-spmi-nvmem: wrap regmap calls to satisfy CFI | generic | PORTABLE(低值) | 包装间接调用满足 kCFI | `drivers/nvmem/`（Apple 驱动，riscv 不构建）| [link](https://patchwork.kernel.org/project/linux-arm-kernel/patch/20260611-apple-spmi-nvmem-cfi-v1-1-9dd90938ef4a@mainlining.org/) |
| 4 | [v3] ARM: OMAP2+: Add CFI type for omap4_finish_suspend | arm | N-A | OMAP SoC 专属 | — | [link](https://patchwork.kernel.org/project/linux-arm-kernel/patch/20260604054048.18980-1-bavishimithil@gmail.com/) |
| 5 | iommufd: Cache invalidation hardening and SMMUv3 batching rework | arm | **PORTABLE**(核心1-3)/N-A(4) | iommufd uAPI 边界硬化 | `drivers/iommu/iommufd/` | [link](https://patchwork.kernel.org/project/linux-arm-kernel/patch/00748c5cbea95a938d032269001a598203b06bbc.1780521606.git.nicolinc@nvidia.com/) |
| 6 | ARM: OMAP2+: Make OMAP4 finish_suspend callback CFI-safe | arm | N-A | OMAP SoC 专属（#4 早期版）| — | [link](https://patchwork.kernel.org/project/linux-arm-kernel/patch/20260512042341.1452-1-bavishimithil@gmail.com/) |
| 7 | [RFC] arm64/scs: Fix potential sign extension issue of advance_loc4 | arm | N-A | arm64 patch-scs（dynamic SCS）| — | [link](https://patchwork.kernel.org/project/linux-arm-kernel/patch/20260413095459.2470584-1-guanwentao@uniontech.com/) |
| 8 | arm64: panic if IRQ shadow call stack allocation fails | arm | **PATTERN** | IRQ SCS 分配失败即 panic | `arch/riscv/kernel/irq.c:87`(`scs_alloc`) | [link](https://patchwork.kernel.org/project/linux-arm-kernel/patch/20260324161545.5441-1-osama.abdelkader@gmail.com/) |
| 9 | KVM: arm64: pkvm; Rework aspects of the PSCI relay | arm | N-A | KVM/PSCI/pkvm 专属 | — | [link](https://patchwork.kernel.org/project/linux-arm-kernel/patch/20260321212419.2803972-3-maz@kernel.org/) |
| 10 | static_call: use CFI-compliant return0 stubs | generic | **PORTABLE** | return0 stub 满足 kCFI 类型 | `kernel/static_call.c`（riscv 用 static_call+kCFI）| [link](https://patchwork.kernel.org/project/linux-arm-kernel/patch/20260311225822.1565895-1-cmllamas@google.com/) |
| 11 | arm64: mte: Skip TFSR_EL1 checks and barriers... | arm | N-A | MTE（无 riscv ISA）| — | [link](https://patchwork.kernel.org/project/linux-arm-kernel/patch/20260311175054.3889093-1-usama.anjum@arm.com/) |
| 12 | arm64/scs: Fix handling of advance_loc4 | arm | N-A | arm64 patch-scs（dynamic SCS）| — | [link](https://patchwork.kernel.org/project/linux-arm-kernel/patch/CAC+fAGbCjQSGbtkbGr5Qb=tPez1i4KZ7TtC0DPHxGbC0wLvBAw@mail.gmail.com/) |
| 13 | KVM: ITS hardening for pKVM | arm | N-A | GIC/ITS + pKVM MMIO donate 专属 | — | [link](https://patchwork.kernel.org/project/linux-arm-kernel/patch/20260310124933.830025-2-sebastianene@google.com/) |
| 14 | Fix bugs and performance of kstack offset randomisation | generic | **PORTABLE** | randomize_kstack per-task + 统一随机源 | `arch/riscv/kernel/traps.c:338`（既有消费者，自动受益）| [link](https://patchwork.kernel.org/project/linux-arm-kernel/patch/20260303150840.3789438-2-ryan.roberts@arm.com/) |
| 15 | arm64: Assorted GCS fixes | arm | **PATTERN**(p2)/N-A(p1) | mprotect(PROT_NONE) on 影子栈 | `arch/riscv/mm/`+`usercfi.c`（`VM_SHADOW_STACK`）| [link](https://patchwork.kernel.org/project/linux-arm-kernel/patch/20260223174533.1478164-3-catalin.marinas@arm.com/) |
| 16 | arm64: insn: Route BTI to simulate_nop... | arm | **PATTERN** | 探针落 BTI/落地页→simulate_nop（BTI→Zicfilp）| `arch/riscv/kernel/probes/`（`lpad` 处理）| [link](https://patchwork.kernel.org/project/linux-arm-kernel/patch/20260217133855.3142192-3-khaja.khaji@oss.qualcomm.com/) |
| 17 | [v2] arm64/gcs: Fix error handling in arch_set_shadow_stack_status() | arm | **PATTERN** | 影子栈启用失败错误处理（GCS→Zicfiss）| `arch/riscv/kernel/usercfi.c:384`(同名函数) | [link](https://patchwork.kernel.org/project/linux-arm-kernel/patch/20260202-arm64_cgs-v2-1-e6a837edf021@debian.org/) |
| 18 | arm64: mte: Improve performance by explicitly disabling unwanted tag checking | arm | N-A | MTE | — | [link](https://patchwork.kernel.org/project/linux-arm-kernel/patch/20251030-mte-tighten-tco-v2-2-e259dda9d5b3@os.amperecomputing.com/) |
| 19 | arm64: Add support for TSV110 Spectre-BHB mitigation | arm | N-A | ARM CPU 分支预测器专属 | — | [link](https://patchwork.kernel.org/project/linux-arm-kernel/patch/20251227092448.732059-1-yangjinqian1@huawei.com/) |
| 20 | ARM: fix hash_name() and branch predictor issues | arm | N-A | ARM32 分支预测器 + fault 专属 | — | [link](https://patchwork.kernel.org/project/linux-arm-kernel/patch/E1vSaSB-00000000NiD-1mnP@rmk-PC.armlinux.org.uk/) |
| 21 | arm64/gcs: Flush the GCS locking state on exec | arm | **PATTERN** | exec 时清影子栈 lock（GCS→Zicfiss）| `arch/riscv/kernel/process.c`+`usercfi.c`(`set_shstk_lock`) | [link](https://patchwork.kernel.org/project/linux-arm-kernel/patch/20251129-arm64-gcs-flush-lock-v1-1-902b3ba6f39d@kernel.org/) |
| 22 | arm64: spectre: Fix hard lockup and cleanup mitigation messages | arm | N-A | printk-in-sched 触发点绑定 arm spectre 路径 | — | [link](https://patchwork.kernel.org/project/linux-arm-kernel/patch/20251031091507.1896-3-shechenglong@xfusion.com/) |
| 23 | arm64: mte: Improve performance by tightening handling of PSTATE.TCO | arm | N-A | MTE | — | [link](https://patchwork.kernel.org/project/linux-arm-kernel/patch/20251030-mte-tighten-tco-v1-1-88c92e7529d9@os.amperecomputing.com/) |
| 24 | Resolve ARM kCFI build failure in idpf xsk.c | arm | **PORTABLE**(p1/p3)/PATTERN(p2) | `__nocfi_generic`（已在树）+ 通用 libeth 驱动 | `include/linux/compiler_types.h:495`+`arch/riscv/Kconfig`(可 select) | [link](https://patchwork.kernel.org/project/linux-arm-kernel/patch/20251025-idpf-fix-arm-kcfi-build-error-v1-1-ec57221153ae@kernel.org/) |
| 25 | [v2] arm64: mte: Do not warn if the page is already tagged in copy_highpage() | arm | N-A | MTE | — | [link](https://patchwork.kernel.org/project/linux-arm-kernel/patch/20251022101704.4015055-1-catalin.marinas@arm.com/) |
| 26 | arm64: mte: Do not flag the zero page as PG_mte_tagged | arm | N-A | MTE | — | [link](https://patchwork.kernel.org/project/linux-arm-kernel/patch/20250924123528.1536835-1-catalin.marinas@arm.com/) |
| 27 | arm64/gcs: Allow reuse of user managed shadow stacks | arm | **PATTERN**+PORTABLE(prctl) | `PR_SHADOW_STACK_EXIT_TOKEN` ABI + 复用（GCS→Zicfiss）| `include/uapi/linux/prctl.h`+`arch/riscv/kernel/usercfi.c`(`save/restore_user_shstk`) | [link](https://patchwork.kernel.org/project/linux-arm-kernel/patch/20250921-arm64-gcs-exit-token-v1-1-45cf64e648d5@kernel.org/) |
| 28 | kselftest/arm64/gcs/basic-gcs: Respect parent directory CFLAGS | arm | N-A | arm64 GCS selftest 构建细节 | — | [link](https://patchwork.kernel.org/project/linux-arm-kernel/patch/20250916-arm64-gcs-nolibc-v1-1-ee54aa65fc26@weissschuh.net/) |
| 29 | KVM: arm64: Provide guest support for GCS | arm | PATTERN(弱) | KVM 虚拟化影子栈（GCS→Zicfiss）| `arch/riscv/kvm/`（尚无 Zicfiss guest，需大量重写）| [link](https://patchwork.kernel.org/project/linux-arm-kernel/patch/20250912-arm64-gcs-v16-5-6435e5ec37db@kernel.org/) |
| 30 | kcfi: Prepare for GCC support | other | **PORTABLE**(通用底座) | `__nocfi` 迁移 + `cfi=` bootparam + "CFI:" 报告标准化 | `kernel/cfi.c`(`report_cfi_failure`) | [link](https://patchwork.kernel.org/project/linux-arm-kernel/patch/20250904034656.3670313-2-kees@kernel.org/) |
| 31 | kselftest/arm64/gcs: Cleanups for basic-gcs.c | arm | N-A | arm64 GCS selftest 清理 | — | [link](https://patchwork.kernel.org/project/linux-arm-kernel/patch/20250821-nolibc-gcs-fixes-v1-2-88519836c915@weissschuh.net/) |
| 32 | [v2] arm64/gcs: Don't call gcs_free() when releasing task_struct | arm | **PATTERN** | 影子栈释放生命周期（GCS→Zicfiss）| `arch/riscv/kernel/usercfi.c:342`(`shstk_release`) | [link](https://patchwork.kernel.org/project/linux-arm-kernel/patch/20250714-arm64-gcs-release-task-v2-1-8a83cadfc846@kernel.org/) |
| 33 | [boot-wrapper-aarch64,v2] Enable GCS if it is present in the HW | arm | N-A | arm64 boot-wrapper 固件（非内核）| — | [link](https://patchwork.kernel.org/project/linux-arm-kernel/patch/20250711071813.25935-1-tamas.kaman@arm.com/) |
| 34 | kselftest/arm64: Add coverage for the interaction of vfork() and GCS | arm | **ALREADY**(nolibc)/N-A(arm test) | nolibc `vfork()` | `tools/include/nolibc/sys.h:401`(**已在树**) | [link](https://patchwork.kernel.org/project/linux-arm-kernel/patch/20250703-arm64-gcs-vfork-exit-v3-2-1e9a9d2ddbbe@kernel.org/) |
| 35 | arm64/gcs: Don't try to access GCS registers if arm64.nogcs is enabled | arm | PATTERN(弱) | cmdline 关闭时避免访问 CFI CSR | `arch/riscv/kernel/usercfi.c` | [link](https://patchwork.kernel.org/project/linux-arm-kernel/patch/20250619-arm64-fix-nogcs-v1-1-febf2973672e@kernel.org/) |
| 36 | arm64/gcs: Don't call gcs_free() during flush_gcs() | arm | **PATTERN** | flush_gcs 生命周期（GCS→Zicfiss）| `arch/riscv/kernel/usercfi.c`+`process.c` | [link](https://patchwork.kernel.org/project/linux-arm-kernel/patch/20250611-arm64-gcs-flush-thread-v1-1-cc26feeddabd@kernel.org/) |
| 37 | [RFC,RESEND] ARM: spectre-v2: fix the spectre operation that may be bypassed | arm | N-A | ARM32 spectre-v2 硬件缓解 | — | [link](https://patchwork.kernel.org/project/linux-arm-kernel/patch/20250606014335.1772-1-xieyuanbin1@huawei.com/) |
| 38 | [stable,6.6.y] arm64: kaslr: fix nokaslr cmdline parsing | arm | PATTERN(弱) | nokaslr cmdline 解析 | `arch/riscv/kernel/pi/`（KASLR 早期码，布局差异大）| [link](https://patchwork.kernel.org/project/linux-arm-kernel/patch/20250603125233.2707474-1-chenridong@huaweicloud.com/) |
| 39 | ARM: spectre-v2: fix unstable cpu get | arm | N-A | ARM32 spectre-v2 | — | [link](https://patchwork.kernel.org/project/linux-arm-kernel/patch/20250424100437.27477-1-xieyuanbin1@huawei.com/) |
| 40 | arm64: Add support for HIP09 Spectre-BHB mitigation | arm | N-A | ARM CPU 分支预测器专属 | — | [link](https://patchwork.kernel.org/project/linux-arm-kernel/patch/20250325141900.2057314-1-yangjinqian1@huawei.com/) |
| 41 | string: Disable read_word_at_a_time() optimizations if kernel MTE is enabled | arm | PORTABLE(惰性) | 通用 `lib/string`，但以 MTE(HW_TAGS) 为门 | `lib/`（riscv 无 HW_TAGS，落地后无效果）| [link](https://patchwork.kernel.org/project/linux-arm-kernel/patch/20250308023314.3981455-1-pcc@google.com/) |
| 42 | [v2] arm64: kaslr: warning linear region randomization on failure | arm | PATTERN(弱) | 线性区随机化失败告警 | `arch/riscv/mm/`（arm64 线性布局专属，价值低）| [link](https://patchwork.kernel.org/project/linux-arm-kernel/patch/20250304042634.591375-1-kpark3469@gmail.com/) |
| 43 | per-function storage support | arm | **PORTABLE**(框架)+PATTERN(arch) | 通用 `kfunc_md` 每函数元数据框架 | `kernel/trace/kfunc_md.c`(新增)+`arch/riscv/kernel/ftrace.c`(padding) | [link](https://patchwork.kernel.org/project/linux-arm-kernel/patch/20250303132837.498938-3-dongml2@chinatelecom.cn/) |
| 44 | arm64: kaslr: consider parange is bigger than linear_region_size | arm | PATTERN(弱) | KASLR 线性区/parange | `arch/riscv/mm/`（arm64 布局专属）| [link](https://patchwork.kernel.org/project/linux-arm-kernel/patch/20250224062111.66528-1-kpark3469@gmail.com/) |
| 45 | arm64: proton-pack: Add Spectre-BSE mitigation for Cortex-A7{2,3,5} | arm | N-A | ARM CPU (Cortex-A7x) 分支预测器专属 | — | [link](https://patchwork.kernel.org/project/linux-arm-kernel/patch/20250122174736.1560714-4-james.morse@arm.com/) |

---

## 判定依据小结

- **GCS→Zicfiss / BTI→Zicfilp / tagged-addr→Supm 已在 riscv 落地**（`arch/riscv/kernel/usercfi.c` 全套影子栈 API：
  `arch_{get,set,lock}_shadow_stack_status`、`save/restore_user_shstk`、`create_rstor_token`、`shstk_release`；
  `RISCV_USER_CFI` Kconfig + Zicfilp/Zicfiss）→ 8 条 GCS 修复/增强判 **PATTERN**（机制对等，riscv 侧按同模式实现/自检）。
- **MTE/PAC 无 riscv 对应 ISA** → 6 条 MTE 系列全 **N-A**（Supm 仅指针掩码，无 tag 检查/存储）。
- **通用硬化落 `kernel/`/`include/linux/`/`lib/`/`drivers/*框架`** → randomize_kstack、per-function storage、
  iommufd 边界硬化、kCFI 报告标准化、static_call CFI stub 判 **PORTABLE**。
- **ARM CPU 分支预测器 spectre + GIC/ITS/pKVM/PSCI + OMAP/boot-wrapper** → **N-A**（HW/固件专属）。
