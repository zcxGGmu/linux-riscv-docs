# MMIO/指令退出 + 调试/内省 可移植性分析

> 输入：`data/by_category/B_mmio-insn.jsonl`（19 条）+ `data/by_category/B_debug-introspect.jsonl`（4 条），共 **23 条系列**。
> 判定依据：`_baseline_riscv.md`、`_taxonomy.md`，并对本地内核树 `/Users/zq/Desktop/patch-work/linux-riscv` 的 `arch/riscv/kvm/` 逐点核对。

## 摘要

- **系列总数 23**：ALREADY=0 / PORTABLE=0 / **PATTERN=6** / **N-A=17**。
- 本类无「纯通用层（virt/kvm）」系列——全部为 x86/arm 架构专属实现（`emulate.c`、`svm.c`、`vmx.c`、arm64 sysreg/AT、各自 `trace.h`）。故 PORTABLE=0；可移植价值集中在 6 条 **PATTERN**（机制可复用、需在 riscv 侧重写）。
- N-A 的 17 条压倒性来自 **x86/SVM/VMX 专有指令与 CPU 漏洞缓解**（WRMSRNS、VERW/MDS/L1TF/MMIO-Stale-Data、STGI/CLGI/VMMCALL/INVLPGA、AVX 全指令模拟器、VMX insn-info）与 **arm 专有 ISA/系统寄存器**（FEAT_LSUI、FEAT_S1POE/ATS1A）。

### 本类 Top 候选（按价值排序）

1. **arm：userspace 注入 external abort（含 syndrome）** → PATTERN。补 riscv 当前「无法优雅处理不可解码 MMIO」的空白。
2. **x86：CR3 写入 guest-debug 退出信息** → PATTERN。riscv `kvm_debug_exit_arch` 目前为空结构，加 `satp` 即得等价能力，改动极小。
3. **x86：vCPU wait/yield tracepoint** → PATTERN。riscv `trace.h` 仅有 entry/exit，可加 WFI/SBI-yield 调度事件。
4. **x86(SVM)：fast MMIO bus writes** → PATTERN。ioeventfd 写命中时跳过指令解码，落点 `vcpu_insn.c`。
5. **x86：enrich kvm_fast_mmio trace 字段** → PATTERN（低价值，riscv `trace.h` 增补 MMIO 埋点）。
6. **x86：单步下 emulated HLT 保留 KVM_EXIT_DEBUG** → PATTERN（依赖 riscv 先实现单步；WFI 为 HLT 类比）。

### 贯穿性缺口（合成结论）

多条 x86 调试系列（#DB/DR6/HW-BP-in-emulator、CR3-in-debug、单步/HLT）共同指向 riscv 的**最大结构性缺口：guest debug 仅软件断点**。已核实：`kvm_guest_debug_arch`、`kvm_debug_exit_arch` **均为空结构体**；`vcpu.c:533` 的 set_guest_debug 仅在开启时通过 `vcpu_config.c:27` 取消 `EXC_BREAKPOINT` 委派，`vcpu_exit.c:242` 命中 `EXC_BREAKPOINT` 直接置 `KVM_EXIT_DEBUG` 且**不回传任何上下文**。硬件断点/单步/watchpoint 需 riscv **Sdtrig（触发模块）** 支持后在 `vcpu.c`/新 `vcpu_debug.c` 重写——这是本批调试类补丁的天然 riscv 落点，但**无单条输入系列可直接移植**（x86 的实现深度绑定 DRx/#DB 与 `emulate.c`）。候选 #2/#6 是其中**可独立落地的最小切片**。

---

## Top 可移植候选（深度）

### 1. arm64：VMM 向 guest 注入 external abort（可带 syndrome）—— PATTERN ⭐
- **原补丁**：`A couple of improvements for VMM to inject external abort to guest`（https://patchwork.kernel.org/project/kvm/patch/20250731212004.1437336-5-jiaqiyan@google.com/）状态=new，arm，4 patches。
- **可移植点**（curl 全文已核）：为 `kvm_vcpu_events` 增 `ext_iabt_pending` / `ext_abt_esr` 字段，并加 `KVM_CAP_ARM_INJECT_EXT_IABT`，允许 userspace 在**无法处理的 I/O 访问**（缺指令 syndrome 解码信息、或该 IPA 无设备映射）时，把「带 ISS 语法域的同步外部中止」重放进 faulting vCPU；地址复用 vCPU 上已有的 fault。
- **riscv 落点**：`arch/riscv/kvm/vcpu_exit.c`——注入机制**已存在**（`kvm_riscv_vcpu_trap_redirect()` 可写 `VSCAUSE/VSTVAL/VSEPC` 回注 guest）；需新增 UAPI（新 `KVM_CAP` + `KVM_INTERRUPT` 之外的异常注入 ioctl / vcpu_events 等价物）让 userspace 指定注入 `EXC_LOAD/STORE/INST_ACCESS_FAULT` 及 `stval`。**依据**：已核 `vcpu.c:251` userspace 目前**仅能注入中断**（`KVM_INTERRUPT`→`IRQ_VS_EXT`），不能注入带 syndrome 的同步异常；且 `vcpu_insn.c` 不可解码 MMIO 走 `-EOPNOTSUPP`（449/566/595/669 行）→ 经 `vcpu_exit.c` 当作错误**直接杀掉 guest**，riscv **无 NISV 式优雅退出**（grep 确认无对应）。
- **判定**：PATTERN。机制/UAPI 语义完全可复用，riscv 需新增 CAP + 异常注入路径并把不可解码 MMIO 从「-EOPNOTSUPP 杀 guest」改为「退用户态 / 回注 access-fault」。

### 2. x86：把 CR3 写入 guest-debug 退出信息 —— PATTERN ⭐（低成本）
- **原补丁**：`KVM: x86: Accelerate reading CR3 for guest debug`（https://patchwork.kernel.org/project/kvm/patch/20251121193204.952988-2-yosry.ahmed@linux.dev/）状态=new，x86，3 patches。
- **可移植点**（curl 已核）：`kvm_debug_exit_arch` 增 `__u64 cr3`，在 `KVM_EXIT_DEBUG` 时填入页表基址寄存器，用 `KVM_CAP_X86_GUEST_DEBUG_CR3` 协商；目的是让 VM 调试器**免去每次断点额外 ioctl 读 CR3**（原文称显著变慢）。
- **riscv 落点**：`arch/riscv/include/uapi/asm/kvm.h` 的 `struct kvm_debug_exit_arch{}`（**当前为空**，已核第 37 行）——加 `__u64 sepc; __u64 satp;`；在 `vcpu_exit.c:242` 的 `EXC_BREAKPOINT` 分支填 `run->debug.arch.satp = ncsr_read(CSR_VSATP)`（并回传 `sepc`）；新增 `KVM_CAP_RISCV_GUEST_DEBUG_ADDR_SPACE` 类似协商位。
- **判定**：PATTERN。思想 100% 通用（把地址空间根寄存器随调试退出一并回传），riscv 侧仅寥寥数行且**恰好补上「退出零上下文」缺口**，是最干净的落地切片。

### 3. x86：vCPU wait/yield tracepoint —— PATTERN
- **原补丁**：`KVM: x86: Add tracepoint for vCPU wait/yield paths`（https://patchwork.kernel.org/project/kvm/patch/tencent_2A66410581309346060C5BDC8CD108053005@qq.com/）状态=new，x86，1 patch。
- **可移植点**（curl 已核）：在 `arch/x86/kvm/trace.h` 新增 `trace_kvm_sched_event`，覆盖 PLE（pause-loop-exit）、HLT 模拟、PV yield（`KVM_HC_SCHED_YIELD`/Hyper-V/Xen）等等待/让步路径；纯观测、不改调度行为。
- **riscv 落点**：`arch/riscv/kvm/trace.h`（**当前仅 kvm_entry/kvm_exit**，已核）新增 `kvm_sched_event`；埋点落在 **WFI 模拟**（`vcpu_insn.c` 虚拟指令路径）与 **SBI HSM/定向让步**（`vcpu_sbi_*.c`）等价点。x86 的 PLE/Hyper-V/Xen 分支 N-A，其余（HLT↔WFI、PV-yield↔SBI）可映射。
- **判定**：PATTERN。事件语义可移，埋点位置架构相关，落点明确。

### 4. x86(SVM)：fast MMIO bus writes —— PATTERN
- **原补丁**：`KVM: SVM: Add fast MMIO bus writes`（https://patchwork.kernel.org/project/kvm/patch/20251113221642.1673023-2-seanjc@google.com/）状态=new，x86，2 patches。
- **可移植点**：写型 MMIO 退出若命中已注册的 ioeventfd（如 doorbell），走 `KVM_FAST_MMIO_BUS` **零长度匹配**、跳过完整指令解码/模拟。
- **riscv 落点**：`arch/riscv/kvm/vcpu_insn.c` 的 `kvm_riscv_vcpu_mmio_store()`——当 `htinst` 需回退到 `kvm_riscv_vcpu_unpriv_read()` 解码（bit0==0 情形）时，可先查 `KVM_FAST_MMIO_BUS` 命中即返回，省去解码。riscv 已支持 ioeventfd（基线），但**未注册/查询 fast MMIO bus**（已核 riscv 无 `fast_mmio`/`KVM_FAST_MMIO_BUS` 引用）。
- **判定**：PATTERN。机制通用；**惟 riscv 多数情形 `htinst` 已直供转换指令、解码本就轻量**，收益窄于 x86，故列为次级候选。

### 5–6（简）
- **enrich kvm_fast_mmio trace 字段**（https://patchwork.kernel.org/project/kvm/patch/tencent_DB120129B359660BBBD7CCC9681F507C0105@qq.com/）→ PATTERN：riscv `trace.h` 可仿此丰富 MMIO 埋点字段；低价值。
- **单步下 emulated HLT 保留 KVM_EXIT_DEBUG**（https://patchwork.kernel.org/project/kvm/patch/20260709053949.211165-1-SaiMadhu.KoyyalaHariVenkata@amd.com/）→ PATTERN：概念=模拟「等待类指令」时不丢失调试退出；riscv 类比为 WFI（`vcpu_insn.c`）。**前置依赖 riscv 先实现单步**，故暂不可独立落地。

---

## 全量判定表

### B_mmio-insn（19）

| 系列 | 判定 | 可移植点(若有) | riscv落点(若有) | web_url |
|---|---|---|---|---|
| KVM: x86: Advertise support for WRMSRNS | N-A | x86 MSR 专有指令；riscv 用 CSR/ONE_REG | — | https://patchwork.kernel.org/project/kvm/patch/20250227010111.3222742-3-seanjc@google.com/ |
| x86/bugs/mmio: Rename mmio_stale_data_clear… | N-A | x86 MMIO-Stale-Data(MDS) 缓解，纯命名 | — | https://patchwork.kernel.org/project/kvm/patch/20250416-mmio-rename-v2-1-ad1f5488767c@linux.intel.com/ |
| VMM 注入 external abort to guest (arm) | **PATTERN** | userspace 带 syndrome 注入同步外部中止；不可解码 MMIO 优雅路径 | `vcpu_exit.c`(trap_redirect 已有)+新 CAP/异常注入 UAPI(`vcpu.c`) | https://patchwork.kernel.org/project/kvm/patch/20250731212004.1437336-5-jiaqiyan@google.com/ |
| KVM: SVM: Don't skip unrelated insn if INT3 replaced | N-A | SVM next_rip/断点注入实现 bug | — | https://patchwork.kernel.org/project/kvm/patch/71043b76fc073af0fb27493a8e8d7f38c3c782c0.1761606191.git.osandov@fb.com/ |
| Unify VERW mitigation for guests | N-A | x86 VERW/CPU-buffer 清除缓解 | — | https://patchwork.kernel.org/project/kvm/patch/20251029-verw-vm-v1-3-babf9b961519@linux.intel.com/ |
| [v3] SVM: Don't skip unrelated insn if INT3/INTO | N-A | 同上（v3） | — | https://patchwork.kernel.org/project/kvm/patch/1cc6dcdf36e3add7ee7c8d90ad58414eeb6c3d34.1762278762.git.osandov@fb.com/ |
| KVM: SVM: Add fast MMIO bus writes | **PATTERN** | ioeventfd 写命中走 KVM_FAST_MMIO_BUS 跳过解码 | `vcpu_insn.c: kvm_riscv_vcpu_mmio_store()`+注册 fast MMIO bus | https://patchwork.kernel.org/project/kvm/patch/20251113221642.1673023-2-seanjc@google.com/ |
| x86/bugs: KVM: L1TF and MMIO Stale Data cleanups | N-A | x86 L1TF/MDS 硬件漏洞缓解(VMX/SVM asm) | — | https://patchwork.kernel.org/project/kvm/patch/20251113233746.1703361-3-seanjc@google.com/ |
| KVM: emulate: enable AVX moves | N-A | x86 全指令软件模拟器 `emulate.c`（riscv 无对应） | — | https://patchwork.kernel.org/project/kvm/patch/20251114003633.60689-2-pbonzini@redhat.com/ |
| Improve handling of debug exc during insn emulation | N-A | 绑定 x86 `emulate.c` + DRx/#DB 硬件调试 | (思想并入 guest-debug 合成缺口) | https://patchwork.kernel.org/project/kvm/patch/19dc9f355b395a8e7c99b449ca5e93c8fbf5c49c.1766066076.git.houwenlong.hwl@antgroup.com/ |
| KVM: SVM: Align SVM with APM behaviors | N-A | SVM EFER.SVME/#UD/VMMCALL 语义 | — | https://patchwork.kernel.org/project/kvm/patch/20260106041250.2125920-3-chengkev@google.com/ |
| Align SVM with APM behaviors (V4) | N-A | SVM STGI/CLGI/INVLPGA 专有指令 | — | https://patchwork.kernel.org/project/kvm/patch/20260228033328.2285047-2-chengkev@google.com/ |
| x86/svm: Add testing for L1 intercept bug | N-A | SVM intercept 的 kvm-unit-tests | — | https://patchwork.kernel.org/project/kvm/patch/20260312204009.3168871-2-chengkev@google.com/ |
| support FEAT_LSUI (arm) | N-A | arm 专有 ISA 扩展；「暴露 ISA 给 guest」模式 riscv 已由 `isa.c`/`vcpu_onereg.c` 具备(reg-access 域) | — | https://patchwork.kernel.org/project/kvm/patch/20260314175133.1084528-2-yeoreum.yun@arm.com/ |
| Add GDB remote debug stub for x86 and arm64 | N-A | **kvmtool 用户态**特性(基于既有 KVM_SET_GUEST_DEBUG)；非内核改动 | (提示 riscv 单步缺口；可另在 kvmtool 加 riscv 后端) | https://patchwork.kernel.org/project/kvm/patch/20260401042034.755639-2-liuwf0302@gmail.com/ |
| mlx5 support for VFIO self test (arm) | N-A | mlx5 设备 + VFIO 迁移测试；arm64 selftest IO barrier 属 selftests 域 | — | https://patchwork.kernel.org/project/kvm/patch/8-v2-72e9640932fd+2c64-mlx5st_jgg@nvidia.com/ |
| KVM: x86: Improve #DB handling in the emulator | N-A | x86 `emulate.c` + #DB/DR6/HW-BP | (并入 guest-debug 合成缺口) | https://patchwork.kernel.org/project/kvm/patch/20260515222638.1949982-9-seanjc@google.com/ |
| KVM: VMX: Refactor VMX instruction information access | N-A | VMX 专有 insn-info 域解码 | — | https://patchwork.kernel.org/project/kvm/patch/20260522172652.181396-1-chang.seok.bae@intel.com/ |
| KVM: arm64: FEAT_{S1POE,ATS1A} support fixes | N-A | arm 专有系统寄存器 + AT 地址翻译指令 | — | https://patchwork.kernel.org/project/kvm/patch/20260602155430.2088142-4-maz@kernel.org/ |

### B_debug-introspect（4）

| 系列 | 判定 | 可移植点(若有) | riscv落点(若有) | web_url |
|---|---|---|---|---|
| KVM: x86: Accelerate reading CR3 for guest debug | **PATTERN** | 把页表基址寄存器随 KVM_EXIT_DEBUG 回传，免额外 ioctl | `uapi/asm/kvm.h: kvm_debug_exit_arch{}`(空→加 satp/sepc)+`vcpu_exit.c:242`+新 CAP | https://patchwork.kernel.org/project/kvm/patch/20251121193204.952988-2-yosry.ahmed@linux.dev/ |
| KVM: x86: enrich kvm_fast_mmio trace event fields | **PATTERN** | 丰富 MMIO tracepoint 字段 | `arch/riscv/kvm/trace.h`(增补 MMIO 埋点) | https://patchwork.kernel.org/project/kvm/patch/tencent_DB120129B359660BBBD7CCC9681F507C0105@qq.com/ |
| KVM: x86: Add tracepoint for vCPU wait/yield paths | **PATTERN** | vCPU 等待/让步调度事件埋点(观测) | `trace.h`(加 kvm_sched_event)+WFI(`vcpu_insn.c`)/SBI-yield(`vcpu_sbi_*.c`) | https://patchwork.kernel.org/project/kvm/patch/tencent_2A66410581309346060C5BDC8CD108053005@qq.com/ |
| Preserve KVM_EXIT_DEBUG on emulated HLT with single-step | **PATTERN** | 模拟等待类指令时不丢调试退出 | WFI(`vcpu_insn.c`)+`vcpu_exit.c`；**前置依赖 riscv 单步** | https://patchwork.kernel.org/project/kvm/patch/20260709053949.211165-1-SaiMadhu.KoyyalaHariVenkata@amd.com/ |

---

## 附：与基线缺口的对应

- 基线缺口 #3「ptdump / stage-2 页表 dumper（arm64 有 `ptdump.c`，riscv 无）」：**本批 23 条中无对应输入系列**（arm64 `ptdump.c` 的引入不在此 23 条内）。已核 riscv KVM **无 ptdump**、arm64 `arch/arm64/kvm/ptdump.c` 存在——该缺口仍成立，建议由 mmu-stage2/主代理统筹为独立新增（debugfs stage-2 ptdump，落点新 `arch/riscv/kvm/ptdump.c` + `gstage.c` 遍历），本报告在此登记以免遗漏。
- 基线缺口 #6「HW 断点/单步（`kvm_guest_debug_arch` 为空）」：由本批多条 x86 调试系列共同印证，见上「贯穿性缺口」。可独立落地切片=候选 #2（satp 入 debug 退出）；完整 HW 断点/单步/watchpoint 需 riscv **Sdtrig** 硬件支持后重写。
