# trace-probe 可移植性分析（linux-arm-kernel → RISC-V）

> 类别：ftrace / kprobes / uprobes / BPF-JIT / jump_label / static_call / kgdb。
> 判定纪律：riscv 与 arm64 在本域**已基本对等**（dynamic ftrace WITH_ARGS/CALL_OPS/DIRECT_CALLS、
> FUNCTION_GRAPH_FREGS、kprobes/kretprobes/uprobes、BPF-JIT 64+32 含 kfunc/arena/percpu/fsession/load-acq、
> jump_label、kgdb）。故：BPF 通用/verifier/core 改动 → **PORTABLE**；arch JIT 精修 → **PATTERN**（落点
> `arch/riscv/net/bpf_jit_*`）；ftrace/kprobes/uprobes 通用核 → **PORTABLE**；arm64 汇编 trampoline / 已存在能力 → PATTERN/ALREADY。

## 摘要

- **系列总数：71**
- **ALREADY：4** — riscv 已实现等价能力（含 1 条 riscv 原生系列）。
- **PORTABLE：33** — 通用 bpf/ftrace/uprobes/kprobes 核 + selftests + 通用 tracepoint/tooling。
- **PATTERN：26** — arch JIT 精修 / kprobes-uprobes-kgdb arch 侧 / static_call 缺口。
- **N-A：8** — arm 专有硬件（SMMU/GIC-ITS/MPAM/SCMI/StrongARM）或 arm64-KVM-hyp 专属。

（多数 bpf 系列为「通用核 PORTABLE + riscv JIT 跟进 PATTERN」的复合形态，下表按**首要价值**归类并注明拆分。）

### 本类 Top 候选（按价值排序）

1. **ftrace,bpf: single direct ops for bpf trampolines**（PORTABLE）—— 通用 ftrace/trampoline 核重构。
2. **emit ENDBR/BTI for indirect jump targets**（PORTABLE+PATTERN）—— 核层 CFI + riscv Zicfilp `lpad`。
3. **bpf: Mitigate Spectre v1 using barriers**（PORTABLE+PATTERN）—— verifier 核 + riscv `bpf_jit_bypass_spec`。
4. **kernel/events/uprobes: uprobe_write_opcode() rewrite**（PORTABLE）—— 通用 uprobes 核。
5. **kprobes: fix cur_kprobe corruption**（PORTABLE）—— 通用 kprobes 重入 bug 修复。
6. **Resilient Queued Spin Lock**（PORTABLE）—— `kernel/bpf/rqspinlock.c` 通用锁。
7. **arm64: Enable UPROBES with GCS**（PATTERN）—— GCS→Zicfiss，影子栈 × uprobes。
8. **arm64: static call trampolines**（PATTERN）—— riscv 尚无 `HAVE_STATIC_CALL`，真缺口。

---

## Top 可移植候选（深度）

### 1. ftrace,bpf: Use single direct ops for bpf trampolines（9 patches, generic）
- **原补丁**：https://patchwork.kernel.org/project/linux-arm-kernel/patch/20251230145010.103439-8-jolsa@kernel.org/ 状态=new
- **可移植点**：纯通用 ftrace/BPF-trampoline 核重构——移除 `FTRACE_OPS_FL_JMP`、`alloc_and_copy_ftrace_hash` direct-friendly、导出 hash 函数、新增 `update_ftrace_direct_{add,del,mod}`、trampoline ip 哈希表（curl 核实 diff 落 `kernel/bpf/trampoline.c` + `include/linux/bpf.h` + `kernel/trace/ftrace.c`，无 arch 代码）。
- **riscv 落点**：**自动适用**。riscv 已 `select HAVE_DYNAMIC_FTRACE_WITH_DIRECT_CALLS`（`arch/riscv/Kconfig:161`），共享 `kernel/trace/ftrace.c` 的 direct-ops 机制；无需 arch 改动即受益于「单 direct ops」优化。
- **判定**：**PORTABLE** —— 改动全在通用层，riscv 经 DIRECT_CALLS select 直接获益。

### 2. emit ENDBR/BTI instructions for indirect jump targets（v15, 5 patches）
- **原补丁**：https://patchwork.kernel.org/project/linux-arm-kernel/patch/20260416064341.151802-3-xukuohai@huaweicloud.com/ 状态=new
- **可移植点**：前 3 patch 为通用核——「把常量致盲移出 arch JIT」「向 JIT 传 `bpf_verifier_env`」「新增探测间接跳转目标的 helper」（curl 核实 diff 落 `kernel/bpf/core.c` +86/-... 、`verifier.c`、`include/linux/filter.h`，**所有 arch 的 `bpf_jit_core.c` 仅 +2 行签名同步**，含 `arch/riscv/net/bpf_jit_core.c`）。末 2 patch 为 x86 ENDBR / arm64 BTI。
- **riscv 落点**：核层三补丁 **PORTABLE**（riscv JIT 签名随之改）；「间接跳转目标发 landing-pad」在 riscv = 发 **Zicfilp `lpad`**（已确认 `arch/riscv/include/asm/assembler.h:86` 有 `lpad`、`csr.h:21` zicfilp 状态位）→ 在 `arch/riscv/net/bpf_jit_comp64.c` 新增 emit，**PATTERN**。
- **判定**：**PORTABLE（核）+ PATTERN（riscv Zicfilp 发射）** —— BTI↔Zicfilp 直接对应，价值高。
- 注：#17（v12）为本系列旧版本，判定相同；#23「fix BTI exception when gotox」引入通用 `gotox_point`/`bpf_jit_insn_aux_data`（PORTABLE）+ arm64 BTI 修复（riscv Zicfilp PATTERN），同族。

### 3. bpf: Mitigate Spectre v1 using barriers（v4, 9 patches）
- **原补丁**：https://patchwork.kernel.org/project/linux-arm-kernel/patch/20260603205800.334980-4-luis.gerhorst@fau.de/ 状态=new
- **可移植点**：verifier 核重构（`do_check_insn()` 拆分、misconfig/internal 返回 `-EFAULT`、`sanitize_stack_spill`→`nospec_result` 改名、nospec 纳入 v1 barrier）——全在 `kernel/bpf/verifier.c`/`core.c`。arch 侧新增 `bpf_jit_bypass_spec_v1/v4()`（arm64/powerpc）。
- **riscv 落点**：verifier 核 **PORTABLE**（riscv 直接受益于 Spectre-v1 缓解）；`bpf_jit_bypass_spec_v1/v4()` 需在 `arch/riscv/net/bpf_jit_comp64.c` 补 arch 实现（riscv 若默认不 bypass，则 verifier 自动插 barrier），**PATTERN**。
- **判定**：**PORTABLE（verifier 核）+ PATTERN（riscv JIT bypass 钩子）** —— 安全价值高。#65（RFC 旧版）同族。

### 4. kernel/events/uprobes: uprobe_write_opcode() rewrite（v3, 3 patches, generic）
- **原补丁**：https://patchwork.kernel.org/project/linux-arm-kernel/patch/20250321113713.204682-4-david@redhat.com/ 状态=new
- **可移植点**：纯通用 uprobes 核——`remove_breakpoint()`/`set_swbp()`/`set_orig_insn()`/`uprobe_write_opcode()` 改传 VMA、重写 opcode 写入路径（curl 核实 diff 落 `kernel/events/uprobes.c` 312 行，无 arch 代码）。
- **riscv 落点**：**自动适用**。riscv uprobes（`arch/riscv/kernel/probes/uprobes.c`）走通用 `uprobe_write_opcode()`，重写后直接受益。
- **判定**：**PORTABLE** —— 通用 uprobes 基础设施。

### 5. kprobes: fix cur_kprobe corruption during re-entrant kprobe_busy_begin()（generic）
- **原补丁**：https://patchwork.kernel.org/project/linux-arm-kernel/patch/20260302105347.3602192-2-khaja.khaji@oss.qualcomm.com/ 状态=new
- **可移植点**：通用 kprobes 重入 bug——`kprobe_busy_begin/end` 用 per-CPU 深度计数保存/恢复 `current_kprobe`，防 softirq 中 `kprobe_flush_task` 破坏 cur_kprobe（curl 核实 diff 落 `kernel/kprobes.c` +34，新增 `kprobe_busy_depth`/`kprobe_busy_saved_current`）。
- **riscv 落点**：**自动适用**。riscv 使用同一套 `current_kprobe` per-CPU（已确认 `arch/riscv/kernel/probes/kprobes.c:19,145`），修复后 riscv 单步路径同样免于 panic。
- **判定**：**PORTABLE** —— 通用 kprobes 核修复。

### 6. Resilient Queued Spin Lock（v4, 25 patches）
- **原补丁**：https://patchwork.kernel.org/project/linux-arm-kernel/patch/20250316040541.108729-23-memxor@gmail.com/ 状态=new
- **可移植点**：为 BPF 提供带死锁检测/超时的 rqspinlock——MCS/qspinlock helper 移入公共头、拷出 `kernel/bpf/rqspinlock.c`、去 PV。主体在 `kernel/bpf/` + `include/asm-generic/`（已确认 `kernel/bpf/rqspinlock.c` 存在）。
- **riscv 落点**：**PORTABLE（主体）**。riscv 有 combo spinlock（ticket↔qspinlock），可复用 `arch_mcs_spin_lock_contended` 等公共 helper；仅极少数 `arch_mcs_*` 语义需在 riscv 侧核对（PATTERN 边角）。
- **判定**：**PORTABLE** —— 通用 BPF 锁基础设施（本条更贴近 atomics-locking，此处仅计数与指路）。

### 7. arm64: Enable UPROBES with GCS（v7, 7 patches）
- **原补丁**：https://patchwork.kernel.org/project/linux-arm-kernel/patch/20250825033421.463669-2-jeremy.linton@arm.com/ 状态=new
- **可移植点**：让 uretprobe 与影子栈（GCS）共存——拆分 ret/bl/blr 探测、新增用户态 GCS 存取器、uretprobe 改写返回地址时同步影子栈。
- **riscv 落点**：**PATTERN**。GCS↔riscv **Zicfiss**（已确认 `arch/riscv/kernel/usercfi.c`、`asm/usercfi.h`）。riscv 开 Zicfiss 后 uretprobe 改写返回地址同样需同步影子栈 → 落 `arch/riscv/kernel/probes/uprobes.c` + `rethook.c` + `usercfi.c`。emerging-feature 平行，价值高。
- **判定**：**PATTERN** —— 机制（影子栈 × uretprobe）可直接照搬到 Zicfiss。

### 8. arm64: implement support for static call trampolines（v7）/ static calls when kCFI（v8）
- **原补丁**：https://patchwork.kernel.org/project/linux-arm-kernel/patch/20260313061852.4025964-1-cmllamas@google.com/ 状态=new
- **可移植点**：为 arm64 实现 `HAVE_STATIC_CALL`（+ kCFI 下用 trampoline）。
- **riscv 落点**：**PATTERN + 真缺口**。已确认 `arch/riscv/Kconfig` **未** select `HAVE_STATIC_CALL`（riscv 目前走通用 fallback）。可参照本系列在 riscv 新增 `arch/riscv/include/asm/static_call.h` + `arch/riscv/kernel/`（patch text + trampoline）。
- **判定**：**PATTERN** —— riscv 侧尚无静态调用，机制可移植（#18 v8 kCFI 版同族）。

---

## 全量判定表（覆盖 71 条）

| # | 系列 | arch | 判定 | 可移植点(若有) | riscv落点(若有) | web_url |
|---|---|---|---|---|---|---|
| 1 | cBPF JIT spray hardening | other/x86 | PORTABLE | bpf 防 JIT-spray 框架 + pack 分配器（x86 IBPB 部分 N-A） | `kernel/bpf/core.c` | [link](https://patchwork.kernel.org/project/linux-arm-kernel/patch/20260709-cbpf-jit-spray-hardening-7-1-y-v1-3-5ac5a2d6797f@linux.intel.com/) |
| 2 | arm64: kgdb: Fix interrupt-induced single-step | arm | PATTERN | 单步与中断竞态处理 | `arch/riscv/kernel/kgdb.c` | [link](https://patchwork.kernel.org/project/linux-arm-kernel/patch/20260615052903.207943-1-liuqiqi@kylinos.cn/) |
| 3 | iommu/arm-smmu-v3: tracepoint for EVTQ | arm | N-A | arm-SMMU-v3 专有硬件 | — | [link](https://patchwork.kernel.org/project/linux-arm-kernel/patch/20260613130007.18563-1-chenjun102@huawei.com/) |
| 4 | arm64: ftrace: DIRECT_CALLS without CALL_OPS | arm | PATTERN | 解耦 direct-calls 与 call-ops | `arch/riscv/kernel/ftrace.c`（riscv 现二者耦合，Kconfig:161-162） | [link](https://patchwork.kernel.org/project/linux-arm-kernel/patch/20260609-arm64-ftrace-direct-calls-v1-2-4a46f266697f@linux.dev/) |
| 5 | bpf, arm64: Stack argument fixes | arm | PATTERN | JIT 栈参数冗余 MOV 修复（selftests PORTABLE） | `arch/riscv/net/bpf_jit_comp64.c` | [link](https://patchwork.kernel.org/project/linux-arm-kernel/patch/20260528161750.1900674-3-puranjay@kernel.org/) |
| 6 | bpf: Recover arena kernel faults w/ scratch page | generic | PORTABLE | arena 缺页恢复（riscv 有 arena） | `kernel/bpf/arena.c`/`verifier.c` | [link](https://patchwork.kernel.org/project/linux-arm-kernel/patch/20260522015946.784267-1-tj@kernel.org/) |
| 7 | sched_ext: Sub-allocator over BPF arena pages | generic | PORTABLE | sched_ext + arena 子分配器 | `kernel/sched/ext*`, `kernel/bpf/arena.c` | [link](https://patchwork.kernel.org/project/linux-arm-kernel/patch/dd5b3702a826666242b6eb6e805bf83f@kernel.org/) |
| 8 | arm64: Add user/kernel page-fault tracepoints | arm | PATTERN | 缺页路径 tracepoint（trace event 定义通用） | `arch/riscv/mm/fault.c` | [link](https://patchwork.kernel.org/project/linux-arm-kernel/patch/20260520045524.75670-1-jbouron@amazon.com/) |
| 9 | ARM: disable broken eBPF JIT on Risc PC | arm | N-A | StrongARM/RiscPC 旧硬件 quirk | — | [link](https://patchwork.kernel.org/project/linux-arm-kernel/patch/20260518014920.135011-1-enelsonmoore@gmail.com/) |
| 10 | ARM: kprobes: MODULE_DESCRIPTION test module | arm | N-A | arch/arm kprobes 测试模块（无 riscv 等价） | — | [link](https://patchwork.kernel.org/project/linux-arm-kernel/patch/20260518013132.130914-1-enelsonmoore@gmail.com/) |
| 11 | ARM: kprobes: test: add MODULE_DESCRIPTION | arm | N-A | 同 #10（arm 测试模块 modpost） | — | [link](https://patchwork.kernel.org/project/linux-arm-kernel/patch/20260504065957.2040055-1-arnd@kernel.org/) |
| 12 | bpf, arm64: Support stack arguments | arm | PATTERN | JIT 栈参数支持 + REG_0 映射（selftests PORTABLE） | `arch/riscv/net/bpf_jit_comp64.c` | [link](https://patchwork.kernel.org/project/linux-arm-kernel/patch/20260427234801.2104511-2-puranjay@kernel.org/) |
| 13 | arm32, bpf: Reject BPF-to-BPF calls in JIT | generic | PATTERN | arm32 JIT 限制（32 位专属） | `arch/riscv/net/bpf_jit_comp32.c` | [link](https://patchwork.kernel.org/project/linux-arm-kernel/patch/20260417143353.838911-1-puranjay@kernel.org/) |
| 14 | bpf, arm32: Reject BPF_PSEUDO_CALL in JIT | generic | PATTERN | 同 #13（arm32 JIT） | `arch/riscv/net/bpf_jit_comp32.c` | [link](https://patchwork.kernel.org/project/linux-arm-kernel/patch/20260417103004.3552500-1-puranjay@kernel.org/) |
| 15 | emit ENDBR/BTI for indirect jump targets (v15) | arm | PORTABLE+PATTERN | 核：致盲外移/传 verifier_env/探测间接跳转；arch：BTI→Zicfilp | `kernel/bpf/core.c`,`verifier.c` + `arch/riscv/net/bpf_jit_comp64.c`(lpad) | [link](https://patchwork.kernel.org/project/linux-arm-kernel/patch/20260416064341.151802-3-xukuohai@huaweicloud.com/) |
| 16 | bpf, arm64/riscv: Remove redundant icache flush | arm | PORTABLE | **riscv 补丁已在系列内**（2/2） | `arch/riscv/net/bpf_jit_core.c` | [link](https://patchwork.kernel.org/project/linux-arm-kernel/patch/20260413191111.3426023-2-puranjay@kernel.org/) |
| 17 | emit ENDBR/BTI for indirect jump targets (v12) | arm | PORTABLE+PATTERN | 同 #15（旧版本） | 同 #15 | [link](https://patchwork.kernel.org/project/linux-arm-kernel/patch/20260403132811.753894-3-xukuohai@huaweicloud.com/) |
| 18 | arm64: static call trampolines when kCFI | arm | PATTERN | 静态调用 + kCFI trampoline | `arch/riscv/` 无 `HAVE_STATIC_CALL` | [link](https://patchwork.kernel.org/project/linux-arm-kernel/patch/20260331110422.301901-2-ardb+git@google.com/) |
| 19 | fsi: trace_call__##name() guarded tracepoint | generic | PORTABLE | 通用 guarded-tracepoint 基础设施 | `include/linux/tracepoint.h`, `drivers/fsi` | [link](https://patchwork.kernel.org/project/linux-arm-kernel/patch/20260323160052.17528-10-vineeth@bitbyteword.org/) |
| 20 | arm64: implement static call trampolines (v7) | arm | PATTERN | 为 arch 实现 `HAVE_STATIC_CALL` | `arch/riscv/include/asm/static_call.h`(新), `kernel/` | [link](https://patchwork.kernel.org/project/linux-arm-kernel/patch/20260313061852.4025964-1-cmllamas@google.com/) |
| 21 | fsi: trace_invoke_##name() guarded tracepoint | generic | PORTABLE | 同 #19（旧命名） | `include/linux/tracepoint.h` | [link](https://patchwork.kernel.org/project/linux-arm-kernel/patch/20260312150523.2054552-10-vineeth@bitbyteword.org/) |
| 22 | KVM: arm64: ring buffer include + ftrace dep | arm | N-A | arm64 pKVM hyp tracing 专属 | — | [link](https://patchwork.kernel.org/project/linux-arm-kernel/patch/20260312123601.625063-3-arnd@kernel.org/) |
| 23 | fix BTI exception when execute gotox | arm | PORTABLE+PATTERN | 核：`gotox_point`/`bpf_jit_insn_aux_data`；arch：BTI→Zicfilp | `kernel/bpf/verifier.c`,`core.c` + `arch/riscv/net/` | [link](https://patchwork.kernel.org/project/linux-arm-kernel/patch/20260306221330.630971-3-yeoreum.yun@arm.com/) |
| 24 | kprobes: fix cur_kprobe corruption (re-entrant) | generic | PORTABLE | 通用 kprobes 重入修复（per-CPU 保存/恢复） | `kernel/kprobes.c`（riscv 用同一 current_kprobe） | [link](https://patchwork.kernel.org/project/linux-arm-kernel/patch/20260302105347.3602192-2-khaja.khaji@oss.qualcomm.com/) |
| 25 | arm64: bpf: 8-byte align JIT buffer (atomic tearing) | arm | PATTERN | JIT 缓冲对齐防原子撕裂 | `arch/riscv/net/bpf_jit_core.c` | [link](https://patchwork.kernel.org/project/linux-arm-kernel/patch/20260226075525.233321-1-tabba@google.com/) |
| 26 | arm64: bpf: Fix UBSAN misaligned access in JIT | arm | PATTERN | JIT 非对齐访问修复 | `arch/riscv/net/bpf_jit_comp64.c` | [link](https://patchwork.kernel.org/project/linux-arm-kernel/patch/20260225091359.3299924-1-tabba@google.com/) |
| 27 | bpf: Introduce 64-bit bitops kfuncs | arm | PORTABLE+PATTERN | 核：kfunc 定义（riscv 支持 kfunc）；arch JIT 加速 | `kernel/bpf/` + `arch/riscv/net/bpf_jit_comp64.c` | [link](https://patchwork.kernel.org/project/linux-arm-kernel/patch/20260219142933.13904-2-leon.hwang@linux.dev/) |
| 28 | arm64: kprobes: disable preempt across XOL single-step | arm | PATTERN | XOL 单步禁抢占 | `arch/riscv/kernel/probes/kprobes.c` | [link](https://patchwork.kernel.org/project/linux-arm-kernel/patch/20260217133855.3142192-2-khaja.khaji@oss.qualcomm.com/) |
| 29 | bpf, arm64: Add fsession support | arm | ALREADY | riscv JIT 已支持 fsession（通用 `bpf_jit_supports_fsession()` PORTABLE） | `arch/riscv/net/bpf_jit_comp64.c:2156` | [link](https://patchwork.kernel.org/project/linux-arm-kernel/patch/20260131144950.16294-3-leon.hwang@linux.dev/) |
| 30 | iommu: Fix NULL deref io_page_fault tracepoint | generic | PORTABLE | 通用 iommu tracepoint NULL 修复 | `drivers/iommu/*` | [link](https://patchwork.kernel.org/project/linux-arm-kernel/patch/20260128-iommu-io_page_fault_null_fix-v2-1-de047be6dd3a@riscstar.com/) |
| 31 | arm64/ftrace,bpf: Fix partial regs after bpf_prog_run | arm | PATTERN | ftrace regs 恢复（override_return，selftest PORTABLE） | `arch/riscv/kernel/ftrace.c`, `mcount-dyn.S` | [link](https://patchwork.kernel.org/project/linux-arm-kernel/patch/20260112121157.854473-1-jolsa@kernel.org/) |
| 32 | uprobes: kmap_atomic → kmap_local_page | arm | PORTABLE | **riscv 补丁已在系列内**（1/5）+ 通用 5/5 | `arch/riscv/kernel/probes/uprobes.c` + `kernel/events/uprobes.c` | [link](https://patchwork.kernel.org/project/linux-arm-kernel/patch/20260103084243.195125-6-ming.jvle@gmail.com/) |
| 33 | bpf: tailcall: Eliminate max_entries/bpf_func at runtime | arm | PORTABLE+PATTERN | 核：`bpf_arch_tail_call_prologue_offset`；arch JIT 跟进 | `kernel/bpf/` + `arch/riscv/net/bpf_jit_comp64.c` | [link](https://patchwork.kernel.org/project/linux-arm-kernel/patch/20260102150032.53106-5-leon.hwang@linux.dev/) |
| 34 | ftrace,bpf: single direct ops for bpf trampolines | generic | PORTABLE | 通用 ftrace/trampoline 核重构（9 patch） | `kernel/trace/ftrace.c`, `kernel/bpf/trampoline.c`（riscv 经 DIRECT_CALLS 受益） | [link](https://patchwork.kernel.org/project/linux-arm-kernel/patch/20251230145010.103439-8-jolsa@kernel.org/) |
| 35 | bpf: arm64: fix sparse warnings | arm | PATTERN | JIT sparse 注解（trivial） | `arch/riscv/net/bpf_jit_comp64.c` | [link](https://patchwork.kernel.org/project/linux-arm-kernel/patch/20251219191310.3204425-1-puranjay@kernel.org/) |
| 36 | bpf: Optimize recursion detection on arm64 | arm | PORTABLE+PATTERN | 核：递归检测 helper 抽取；arch：去原子优化 | `kernel/bpf/trampoline.c` + `arch/riscv/net/` | [link](https://patchwork.kernel.org/project/linux-arm-kernel/patch/20251219184422.2899902-2-puranjay@kernel.org/) |
| 37 | Add NMI Support to RISC-V via SSE | other(riscv) | ALREADY | **riscv 原生系列**（非 arm→riscv 移植） | `drivers/firmware/riscv/*`, `arch/riscv/kernel/smp.c` | [link](https://patchwork.kernel.org/project/linux-arm-kernel/patch/20251127125305.89961-6-cuiyunhui@bytedance.com/) |
| 38 | bpf: Implement BPF_LINK_UPDATE for tracing links | arm | PORTABLE+PATTERN | 核：link update scaffolding（freplace/fentry/fexit）；arch trampoline update | `kernel/bpf/trampoline.c` + `arch/riscv/net/` | [link](https://patchwork.kernel.org/project/linux-arm-kernel/patch/20251118005305.27058-3-jordan@jrife.io/) |
| 39 | context_tracking,x86: Defer IPIs until user→kernel | other/x86 | PORTABLE(部分) | 通用 jump_label/static_call/context_tracking/rcu 注解（x86 IPI 延迟机制 N-A） | `kernel/context_tracking.c`, `kernel/jump_label.c`, `kernel/static_call*` | [link](https://patchwork.kernel.org/project/linux-arm-kernel/patch/20251114151428.1064524-3-vschneid@redhat.com/) |
| 40 | tracing: Enable kprobe for selected Arm64 asm (v2) | arm | PATTERN | 标注 asm 函数可 kprobe | `arch/riscv/kernel/*.S` + kprobes blacklist | [link](https://patchwork.kernel.org/project/linux-arm-kernel/patch/20251103185237.2284456-1-benniu@meta.com/) |
| 41 | tracing: Enable kprobe tracing for Arm64 asm | arm | PATTERN | 同 #40（旧版） | 同 #40 | [link](https://patchwork.kernel.org/project/linux-arm-kernel/patch/20251027181749.240466-1-benniu@meta.com/) |
| 42 | arm64: ftrace: fix unreachable PLT for ftrace_caller | arm | PATTERN | 模块加载 ftrace PLT 可达性 | `arch/riscv/kernel/ftrace.c`, `module.c` | [link](https://patchwork.kernel.org/project/linux-arm-kernel/patch/20250905032236.3220885-1-panfan@qti.qualcomm.com/) |
| 43 | arm64: kgdb: Ensure atomic single-step execution | arm | PATTERN | kgdb 原子单步 | `arch/riscv/kernel/kgdb.c` | [link](https://patchwork.kernel.org/project/linux-arm-kernel/patch/1756972043-12854-1-git-send-email-mengchenli64@gmail.com/) |
| 44 | arm64: Enable UPROBES with GCS | arm | PATTERN | uretprobe × 影子栈（GCS→Zicfiss） | `arch/riscv/kernel/probes/uprobes.c`, `rethook.c`, `usercfi.c` | [link](https://patchwork.kernel.org/project/linux-arm-kernel/patch/20250825033421.463669-2-jeremy.linton@arm.com/) |
| 45 | arm_mpam: static key when mpam enabled | generic | N-A | MPAM 为 arm 专有 resctrl 硬件 | — | [link](https://patchwork.kernel.org/project/linux-arm-kernel/patch/20250822153048.2287-24-james.morse@arm.com/) |
| 46 | ARM: ftrace: Implement HAVE_FUNCTION_GRAPH_FREGS | arm | ALREADY | riscv 已 select（32 位 ARM 追赶） | `arch/riscv/Kconfig:166` | [link](https://patchwork.kernel.org/project/linux-arm-kernel/patch/20250818103931.1100084-1-richard@nod.at/) |
| 47 | Support kCFI + BPF on arm64 | arm | PORTABLE+PATTERN | 核：CFI 类型宏 + BPF CFI helper 移入通用；arch 集成 | `kernel/bpf/` + `include/linux/cfi.h` + `arch/riscv/net/`,`kernel/cfi.c` | [link](https://patchwork.kernel.org/project/linux-arm-kernel/patch/20250801001004.1859976-6-samitolvanen@google.com/) |
| 48 | bpf, arm64: relax constraint (structs on stack) | arm | PATTERN | JIT 放宽栈结构约束（selftest PORTABLE） | `arch/riscv/net/bpf_jit_comp64.c` | [link](https://patchwork.kernel.org/project/linux-arm-kernel/patch/20250709-arm64_relax_jit_comp-v1-1-3850fe189092@bootlin.com/) |
| 49 | selftests/bpf: tracing_multi testcases | generic | PORTABLE | 通用 bpf selftests | `tools/testing/selftests/bpf/` | [link](https://patchwork.kernel.org/project/linux-arm-kernel/patch/20250703121521.1874196-18-dongml2@chinatelecom.cn/) |
| 50 | firmware: arm_scmi: xfer inflight debug/trace | generic | N-A | arm SCMI 固件 ABI 专属 | — | [link](https://patchwork.kernel.org/project/linux-arm-kernel/patch/20250630105544.531723-3-philip.radford@arm.com/) |
| 51 | arm/probes/uprobes: Remove redundant preempt around kmap | generic | PATTERN | kmap_atomic 已禁抢占（概念通用） | `arch/riscv/kernel/probes/uprobes.c` | [link](https://patchwork.kernel.org/project/linux-arm-kernel/patch/20250615141129.653384-2-ysk@kzalloc.com/) |
| 52 | bpf-restrict-fs fails without DIRECT_CALLS on arm64 | arm | PATTERN | Kconfig 依赖（riscv 已有 DIRECT_CALLS） | `arch/riscv/Kconfig` | [link](https://patchwork.kernel.org/project/linux-arm-kernel/patch/20250610232418.GA3544567@ax162/) |
| 53 | selftests/bpf: Fix compile error bin_attribute | generic | PORTABLE | 通用 selftests 编译修复 | `tools/testing/selftests/bpf/` | [link](https://patchwork.kernel.org/project/linux-arm-kernel/patch/tencent_A6502A28AF21A3CA88B106F3421159869708@qq.com/) |
| 54 | bpf: Mitigate Spectre v1 using barriers (v4) | arm | PORTABLE+PATTERN | 核：verifier 重构+nospec；arch：`bpf_jit_bypass_spec_v1/v4` | `kernel/bpf/verifier.c` + `arch/riscv/net/bpf_jit_comp64.c` | [link](https://patchwork.kernel.org/project/linux-arm-kernel/patch/20260603205800.334980-4-luis.gerhorst@fau.de/) |
| 55 | bpf, arm64: support up to 12 arguments | arm | PATTERN | JIT 支持 ≤12 参（selftest PORTABLE） | `arch/riscv/net/bpf_jit_comp64.c` | [link](https://patchwork.kernel.org/project/linux-arm-kernel/patch/20250527-many_args_arm64-v3-1-3faf7bb8e4a2@bootlin.com/) |
| 56 | selftests/bpf: Fix build warning | generic | PORTABLE | 通用 selftests | `tools/testing/selftests/bpf/` | [link](https://patchwork.kernel.org/project/linux-arm-kernel/patch/20250509123802.695574-1-skb99@linux.ibm.com/) |
| 57 | selftests/bpf: Fix build error | generic | PORTABLE | 通用 selftests | `tools/testing/selftests/bpf/` | [link](https://patchwork.kernel.org/project/linux-arm-kernel/patch/20250509122348.649064-1-skb99@linux.ibm.com/) |
| 58 | barrier: introduce smp_cond_load_*_timewait() | arm | PORTABLE+PATTERN | 核：`asm-generic/barrier.h` + wait_policy；arch：riscv Zawrs | `include/asm-generic/barrier.h` + `arch/riscv/include/asm/barrier.h` | [link](https://patchwork.kernel.org/project/linux-arm-kernel/patch/20250502085223.1316925-3-ankur.a.arora@oracle.com/) |
| 59 | selftests/bpf: Convert comma to semicolon | generic | PORTABLE | 通用 selftests（trivial） | `tools/testing/selftests/bpf/` | [link](https://patchwork.kernel.org/project/linux-arm-kernel/patch/20250401061546.1990156-1-nichen@iscas.ac.cn/) |
| 60 | kernel/events/uprobes: uprobe_write_opcode() rewrite | generic | PORTABLE | 通用 uprobes 核重写（传 VMA） | `kernel/events/uprobes.c`（riscv 自动受益） | [link](https://patchwork.kernel.org/project/linux-arm-kernel/patch/20250321113713.204682-4-david@redhat.com/) |
| 61 | Resilient Queued Spin Lock (25 patches) | arm | PORTABLE | 通用 BPF rqspinlock（死锁检测/超时） | `kernel/bpf/rqspinlock.c` + `include/asm-generic/` | [link](https://patchwork.kernel.org/project/linux-arm-kernel/patch/20250316040541.108729-23-memxor@gmail.com/) |
| 62 | Introduce load-acquire/store-release BPF instructions | arm | ALREADY | riscv JIT 已实现（`emit_atomic_ld_st` BPF_LOAD_ACQ）；核指令定义 PORTABLE | `arch/riscv/net/bpf_jit_comp64.c:564-588` | [link](https://patchwork.kernel.org/project/linux-arm-kernel/patch/5a4d2a52b2cc022bf86d0b572789f0b3bc3d5162.1741049567.git.yepeilin@google.com/) |
| 63 | add function metadata support | generic | PORTABLE | 通用 bpf/ftrace 函数元数据 | `kernel/bpf/`, `kernel/trace/` | [link](https://patchwork.kernel.org/project/linux-arm-kernel/patch/20250226121537.752241-1-dongml2@chinatelecom.cn/) |
| 64 | scripts/sorttable: ftrace: Fix bugs w/ sorttable & ARM64 | generic | PORTABLE | scripts/sorttable + ftrace mcount_loc 核 | `scripts/sorttable.c`, `kernel/trace/ftrace.c` | [link](https://patchwork.kernel.org/project/linux-arm-kernel/patch/20250225182054.290128736@goodmis.org/) |
| 65 | bpf: Mitigate Spectre v1 speculation barriers (RFC) | arm | PORTABLE+PATTERN | 同 #54（RFC 旧版） | 同 #54 | [link](https://patchwork.kernel.org/project/linux-arm-kernel/patch/20250224203619.594724-5-luis.gerhorst@fau.de/) |
| 66 | scripts/sorttable: Remove place holders for weak funcs | arm | PORTABLE | scripts/sorttable + ftrace（arm64 boot 排序 PATTERN） | `scripts/sorttable.c`, `kernel/trace/ftrace.c` | [link](https://patchwork.kernel.org/project/linux-arm-kernel/patch/20250218200023.221100846@goodmis.org/) |
| 67 | arm64: kprobe: fix single stepping support | arm | PATTERN | kprobes 单步修复 | `arch/riscv/kernel/probes/kprobes.c` | [link](https://patchwork.kernel.org/project/linux-arm-kernel/patch/tencent_9DCAEBDF4D9BCDB4687B502DB6B608E4FB0A@qq.com/) |
| 68 | xsk: TX metadata Launch Time support | generic | PORTABLE | XDP/xsk 核（NIC 驱动 stmmac/igc 硬件专属 N-A） | `net/xdp/`, `net/core/` | [link](https://patchwork.kernel.org/project/linux-arm-kernel/patch/20250116155350.555374-5-yoong.siang.song@intel.com/) |
| 69 | KVM: arm64: vgic-its: debugfs + tracepoints | arm | N-A | GIC/ITS 中断控制器硬件 | — | [link](https://patchwork.kernel.org/project/linux-arm-kernel/patch/20250113193128.1533449-3-jingzhangos@google.com/) |
| 70 | arm64: Fix 5-level paging in kexec/hibernate trampoline | arm | PATTERN | 重定位 trampoline 处理 5 级页表（Sv57） | `arch/riscv/kernel/machine_kexec*.c`, `kexec_relocate.S` | [link](https://patchwork.kernel.org/project/linux-arm-kernel/patch/20250110175145.785702-2-ardb+git@google.com/) |
| 71 | bpf, arm64: Simplify emit_lse_atomic/emit_a64_add_i | arm | PATTERN | JIT 原子发射化简/优化 | `arch/riscv/net/bpf_jit_comp64.c`(`emit_atomic_rmw`) | [link](https://patchwork.kernel.org/project/linux-arm-kernel/patch/fedbaca80e6d8bd5bcba1ac5320dfbbdab14472e.1735868489.git.yepeilin@google.com/) |

---

## 关键结论

- 本域 riscv 与 arm64 **已高度对等**：ftrace（WITH_ARGS/CALL_OPS/DIRECT_CALLS/FUNCTION_GRAPH_FREGS）、kprobes/uprobes、
  BPF-JIT（arena/percpu/fsession/load-acquire/store-release）均已在树，故大量 bpf「新特性」对 riscv 是**核层 PORTABLE + JIT 跟进 PATTERN**，
  少数（fsession #29、load-acquire #62、FUNCTION_GRAPH_FREGS #46）直接判 **ALREADY**。
- **最高迁移价值**集中在通用核：ftrace 单 direct-ops（#34）、uprobes 重写（#60）、kprobes 重入修复（#24）、
  Spectre-v1 verifier 缓解（#54）、rqspinlock（#61）——这些**无需 arch 改动即惠及 riscv**。
- **最具「照搬」价值的 arch 模式**：CFI 硬化（ENDBR/BTI→Zicfilp #15/#23）、uretprobe×影子栈（GCS→Zicfiss #44）、
  静态调用 trampoline（riscv 真缺 `HAVE_STATIC_CALL` #18/#20）。
- **真 N-A（8 条）**：arm-SMMU（#3）、GIC-ITS（#69）、MPAM（#45）、SCMI（#50）、StrongARM/RiscPC（#9）、
  arm64-pKVM-hyp（#22）、arm-kprobes 测试模块（#10/#11）。
