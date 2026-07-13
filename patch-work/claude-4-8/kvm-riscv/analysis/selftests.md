# selftests + kvm-unit-tests 可移植性分析

> 输入：`B_selftests.jsonl`（31 条，Tier B）+ `T_kvm-unit-tests.jsonl`（47 条，Tier T），共 **78 条**。
> 基线核对源码：`/Users/zq/Desktop/patch-work/linux-riscv`（Linux 7.2.0-rc3）。
> riscv 已构建的 selftests（`Makefile.kvm:218-228`）：全部 `TEST_GEN_PROGS_COMMON`（demand_paging / dirty_log / guest_print / **irqfd_test** / kvm_binary_stats / kvm_create_max_vcpus / kvm_page_table / **set_memory_region_test** / memslot_modification_stress / memslot_perf）+ `riscv/sbi_pmu_test` `riscv/ebreak_test` `access_tracking_perf_test` `arch_timer` `coalesced_io_test` `dirty_log_perf_test` `get-reg-list` `mmu_stress_test` `rseq_test` `steal_time`。
> riscv **未**构建（文件存在但未入 riscv 列表）：`guest_memfd_test` `pre_fault_memory_test` `hardware_disable_test` `system_counter_offset_test` `dirty_log_page_splitting_test`(x86) `pmu_counters_test`/`pmu_event_filter_test`(x86)。

## 摘要

### KVM selftests（B，31 条）
- **PORTABLE 4**：B1（kvm_run 完成标志）、B12（selftests 可移植性 fallback）、B15（irqfd_test 非 x86 修复）、B13（mm 去 nth_page，树级自动适用）。
- **PATTERN 2**：B21（只读 memslot 测试）、B24（WFI/WFE per-VM disable-exits CAP）。
- **ALREADY 0**（B26/B30 是 arm64 对 steal_time 的修复，riscv 的 `__riscv` STA 分支已独立工作，故对 riscv 判 N-A 而非 ALREADY）。
- **N-A 25**：arm64 set_id_regs / MDSCR / AArch64-sticky / NV / shadow_stage2 / SEA、x86 fastops / AMX / APERF-MPERF / SVM-GIF / APIC-freq / ICEBP、vfio selftests（arm64/x86 专属构建门控）、x86 ARCH 规整等。

### kvm-unit-tests（T，47 条）
- **PORTABLE 0 / PATTERN 0 / N-A 47**。该套件是**独立用户态仓库**（`kvm-unit-tests`，riscv 有自己的 `riscv/` 目标与维护线），本批 47 条全为 x86 架构专属测试内容（nVMX/nSVM/VMX/SVM/APIC/IOAPIC/PIT/PMU-perfmon/xsave-AVX-APX-AMX/emulator/DR 调试寄存器/PKS/PKU/LAM/CET/GMET）或 x86 目标的 run 脚本/CI/编译修复 → 对 linux-riscv **内核** KVM 无落点。仅 3 条含「思想可借鉴」但价值极低（见表内注：#2 原子 bitops 正确性、#18 未处理异常打印错误码、#44 run 脚本 `-accel` 选项），不作为移植候选。

### 本类 Top 候选（按价值排序）
1. **B15** irqfd_test 非 x86 修复 — PORTABLE（直接惠及 riscv 已构建的 COMMON 测试）
2. **B1** kvm_run 需完成标志 — PORTABLE（通用 kvm_main.c + 通用 selftests 助手）
3. **B21** 只读 memslot 测试 — PATTERN（riscv 已支持 `KVM_MEM_READONLY`，缺测试）
4. **B24** WFI/WFE per-VM disable-exits — PATTERN（riscv 陷入 WFI 但无 disable-exits CAP）
5. **B12** selftests 可移植性 fallback — PORTABLE（通用 lib 构建健壮性）
6. **B13** mm 去 nth_page — PORTABLE（树级清理，riscv 自动含入，非专项动作）

---

## Top 可移植候选（深度）

### 1. B15 — KVM: selftests: Fix irqfd_test for non-x86 architectures　【PORTABLE】
- **原补丁**：<https://patchwork.kernel.org/project/kvm/patch/20250930193301.119859-1-oliver.upton@linux.dev/>（state=new，arch 标记 x86 但内容面向**非 x86**）
- **可移植点**：curl 确认 diff 触及 `include/kvm_util.h` + 公共 `irqfd_test.c` + 各架构 `lib/{arm64,s390,x86}/processor.c`，为非 x86 架构补齐 irqfd_test 所需的每架构助手/默认 irqchip 语义。`irqfd_test` 属 `TEST_GEN_PROGS_COMMON`（`Makefile.kvm:62`），**riscv 已构建**。
- **riscv 落点**：`tools/testing/selftests/kvm/irqfd_test.c`（公共，自动获益）；`lib/riscv/processor.c` —— riscv 已定义 `kvm_arch_has_default_irqchip()`（processor.c:569）、`vm_arch_vcpu_add`、`vcpu_arch_set_entry_point`，需镜像补丁给 arm64/s390 新增的同名助手（若有）并回归验证 riscv AIA in-kernel irqchip 下 irqfd_test 通过。
- **判定**：PORTABLE —— 公共测试 + 通用头，riscv 是非 x86 目标，本修复正是让该类测试在 riscv 上健壮运行。

### 2. B1 — KVM: Add a kvm_run flag to signal need for completion　【PORTABLE】
- **原补丁**：<https://patchwork.kernel.org/project/kvm/patch/20250111012450.1262638-2-seanjc@google.com/>（state=new，5 patches）
- **可移植点**：patch 2「Clear vcpu->run->flags at start of KVM_RUN **for all architectures**」+ patch 3「Add a **common** kvm_run flag（`KVM_RUN_NEEDS_COMPLETION`）」为通用层改动；patch 4/5 为通用 selftests 助手（`KVM_RUN` + `immediate_exit` 分离、依 `KVM_RUN_NEEDS_COMPLETION` 完成用户态退出）。
- **riscv 落点**：`virt/kvm/kvm_main.c`（KVM_RUN 起始清 `run->flags`）与 `include/uapi/linux/kvm.h`（新标志）——通用，riscv 自动生效；`tools/testing/selftests/kvm/lib/kvm_util.c` 通用助手，riscv MMIO/SBI 用户态退出测试可直接复用。
- **判定**：PORTABLE —— 显式「for all architectures / common」，无架构假设。

### 3. B21 — KVM: selftests: Add test case for readonly memslots　【PATTERN】
- **原补丁**：<https://patchwork.kernel.org/project/kvm/patch/57c05d4d7db845be9250b7a4f6537e98636d70ca.1772090306.git.yohei.kojima@sony.com/>（state=new，2 patches）
- **可移植点**：patch 1「Extract memslot setup from spawn_vm()」curl 确认改在**公共** `set_memory_region_test.c`（riscv 已构建）；patch 2 加只读 memslot 用例。**riscv KVM 已支持只读 memslot**：`arch/riscv/kvm/Kconfig:26 select HAVE_KVM_READONLY_MEM`、`vm.c:186 KVM_CAP_READONLY_MEM`、`mmu.c:194/549` 依 `KVM_MEM_READONLY` 置写权限并产生写故障 → 退出。
- **riscv 落点**：`tools/testing/selftests/kvm/set_memory_region_test.c` —— 提取部分为通用重构；只读用例现挂 x86，需加 riscv 适配（guest 写只读区触发 `KVM_EXIT_MMIO`/写保护路径断言）。
- **判定**：PATTERN —— 特性 riscv 已具备，测试机制通用，落点在公共测试文件，仅 guest 汇编/断言需 riscv 化。

### 4. B24 — KVM: arm64: Add per-VM WFI/WFE exit disable capability　【PATTERN】
- **原补丁**：<https://patchwork.kernel.org/project/kvm/patch/20260408202557.2102476-3-dwmw2@infradead.org/>（state=new，2 patches：`KVM_CAP_ARM_DISABLE_EXITS` for WFI/WFE + selftest）
- **可移植点**：为空转指令（WFI/WFE）提供 per-VM「disable exit / passthrough」协商能力，减少陷出。riscv 现状：**陷入 WFI 并阻塞**（`vcpu.c:32 wfi_exit_stat`，`aia_imsic.c:698` 注释「upon WFI trap … kvm_vcpu_block()」），但 `arch/riscv/kvm/` **无任何 `DISABLE_EXITS`/`disable_exits` 机制**（grep 为空）。x86 有 `KVM_CAP_X86_DISABLE_EXITS`、arm 此系列新增 `KVM_CAP_ARM_DISABLE_EXITS`。
- **riscv 落点**：`arch/riscv/kvm/vcpu_insn.c`/`vcpu.c`（WFI 陷入处理）+ 新增 `KVM_CAP_RISCV_DISABLE_EXITS`（vm.c 协商）；配套新 selftest。
- **判定**：PATTERN —— 三态协商模式与空转直通思想通用，riscv 侧需重写陷入策略与 CAP。中等价值。

### 5. B12 — KVM: selftests: portability fallbacks（__packed/pthread/memfd/backtrace…）　【PORTABLE】
- **原补丁**：<https://patchwork.kernel.org/project/kvm/patch/20250829142556.72577-7-aqibaf@amazon.com/>（state=new，含 `lib/assert.c` backtrace fallback 等）
- **可移植点**：curl 确认（patch 6/9）改 `lib/assert.c`；全系列为通用 lib 的构建/运行健壮性 fallback（`__packed` 属性、`pthread_attr_setaffinity_np`、`memfd_create` 兼容、`PAGE_SIZE` 重定义防护、backtrace 兜底），面向非 glibc/旧工具链。
- **riscv 落点**：`tools/testing/selftests/kvm/lib/assert.c`、`lib/kvm_util.c`、`include/*` —— 通用，改善 riscv（尤其交叉编译/musl CI）构建与断言诊断。
- **判定**：PORTABLE —— 纯通用框架健壮性，无架构耦合。

### 6. B13 — mm: remove nth_page()　【PORTABLE（树级，非专项动作）】
- **原补丁**：<https://patchwork.kernel.org/project/kvm/patch/20250901150359.867252-38-david@redhat.com/>（state=new，37 patches，arch=x86+arm 实为 mm 全树）
- **可移植点**：全树移除 `nth_page()` 的清理，含 selftests；一次性落地、arch 中立。
- **riscv 落点**：无需 riscv 专项动作，`arch/riscv` 与通用 mm/selftests 随树合入自动含入。
- **判定**：PORTABLE（平凡）—— 列此仅为完整性；对 riscv 移植路线无独立行动项。

---

## 全量判定表 A：KVM selftests（B，31 条）

| # | 系列 | arch | 判定 | 可移植点(若有) | riscv落点(若有) | web_url |
|---|---|---|---|---|---|---|
| B1 | Add a kvm_run flag to signal need for completion | x86 | **PORTABLE** | 通用 `run->flags` 清零 + 公共 `KVM_RUN_NEEDS_COMPLETION` + 通用 selftests 助手 | `virt/kvm/kvm_main.c`、`uapi/linux/kvm.h`、`lib/kvm_util.c` | [link](https://patchwork.kernel.org/project/kvm/patch/20250111012450.1262638-2-seanjc@google.com/) |
| B2 | Add NV Selftest cases | arm | N-A | 嵌套虚拟化（VNCR/guest hyp），riscv 无 | — | [link](https://patchwork.kernel.org/project/kvm/patch/20250206164120.4045569-2-gankulkarni@os.amperecomputing.com/) |
| B3 | arm64: page attrs Inner-Shareable | arm | N-A | arm64 内存共享域/硬件宏，架构专属 | — | [link](https://patchwork.kernel.org/project/kvm/patch/20250405001042.1470552-2-rananta@google.com/) |
| B4 | arm64: Make AArch64 support sticky | arm | N-A | arm64 AArch64/AArch32 EL 控制 | — | [link](https://patchwork.kernel.org/project/kvm/patch/20250429114117.3618800-3-maz@kernel.org/) |
| B5 | Add a test for x86's fastops emulation | x86 | N-A | x86 指令软件模拟器专属（riscv 仅轻量 MMIO 解码） | — | [link](https://patchwork.kernel.org/project/kvm/patch/20250506011250.1089254-1-seanjc@google.com/) |
| B6 | Disable APERF/MPERF read intercepts | x86 | N-A | x86 APERF/MPERF MSR 拦截；`*_in_guest` u64 位图为 x86 内部 | — | [link](https://patchwork.kernel.org/project/kvm/patch/20250530185239.2335185-2-jmattson@google.com/) |
| B7 | arm64/debug: Drop DBG_MDSCR_* macros | arm | N-A | arm64 MDSCR 调试寄存器 | — | [link](https://patchwork.kernel.org/project/kvm/patch/20250613023646.1215700-2-anshuman.khandual@arm.com/) |
| B8 | arm64: test checking KVM's own UUID | arm | N-A | arm SMCCC vendor-hypercall UUID 探测；riscv 用 SBI base（机制不同） | (SBI base 探测，价值低) | [link](https://patchwork.kernel.org/project/kvm/patch/20250806171341.1521210-1-maz@kernel.org/) |
| B9 | Move Intel/AMD module param helpers | x86 | N-A | x86 selftests 助手重构 | — | [link](https://patchwork.kernel.org/project/kvm/patch/20250806225159.1687326-1-seanjc@google.com/) |
| B10 | arm64: Sync ID_AA64MMFR3_EL1 set_id_regs | arm | N-A | arm64 ID 寄存器特性屏蔽测试 | — | [link](https://patchwork.kernel.org/project/kvm/patch/20250818-kvm-arm64-selftests-mmfr3-idreg-v1-1-2f85114d0163@kernel.org/) |
| B11 | fix irqfd_test on arm64 | arm | N-A | arm64 专属修复（公共 irqfd_test 的 arm64 分支）；riscv 相关修复见 B15 | (见 B15) | [link](https://patchwork.kernel.org/project/kvm/patch/20250825155203.71989-1-sebott@redhat.com/) |
| B12 | selftests portability fallbacks | x86 | **PORTABLE** | 通用 lib 构建/运行 fallback（__packed/pthread/memfd/backtrace） | `lib/assert.c`、`lib/kvm_util.c`、`include/*` | [link](https://patchwork.kernel.org/project/kvm/patch/20250829142556.72577-7-aqibaf@amazon.com/) |
| B13 | mm: remove nth_page() | x86+arm | **PORTABLE**（树级） | mm 全树清理，arch 中立，随树合入 | 无专项动作（`arch/riscv`+通用自动含入） | [link](https://patchwork.kernel.org/project/kvm/patch/20250901150359.867252-38-david@redhat.com/) |
| B14 | arm64: Cover ID_AA64ISAR3_EL1 set_id_regs | arm | N-A | arm64 ID 寄存器测试 | — | [link](https://patchwork.kernel.org/project/kvm/patch/20250920-kvm-arm64-id-aa64isar3-el1-v1-2-1764c1c1c96d@kernel.org/) |
| B15 | Fix irqfd_test for non-x86 architectures | x86 | **PORTABLE** | 公共 irqfd_test + `kvm_util.h` + 各架构 processor.c 助手，面向非 x86 | `irqfd_test.c`（公共）、`lib/riscv/processor.c`（镜像助手，riscv 已建 irqfd_test） | [link](https://patchwork.kernel.org/project/kvm/patch/20250930193301.119859-1-oliver.upton@linux.dev/) |
| B16 | ARCH from x86_64 to x86 override | x86 | N-A | selftests Makefile x86 ARCH 名规整 | — | [link](https://patchwork.kernel.org/project/kvm/patch/20251007223057.368082-1-seanjc@google.com/) |
| B17 | handle guest SEA via KVM_EXIT_ARM_SEA | arm | N-A | arm 同步外部中止（RAS/SEA）新 UAPI；riscv 无对应 RAS 通路（「退用户态处理内存错误」思想可远期借鉴） | (远期：访问故障退用户态) | [link](https://patchwork.kernel.org/project/kvm/patch/20251013185903.1372553-3-jiaqiyan@google.com/) |
| B18 | SVM: GIF and EFER.SVME independent | x86 | N-A | x86 SVM/嵌套（GIF、nested_state） | — | [link](https://patchwork.kernel.org/project/kvm/patch/20251121204803.991707-3-yosry.ahmed@linux.dev/) |
| B19 | x86, fpu/kvm: fix crash with AMX | x86 | N-A | x86 AMX/XFD/TILELOAD（#NM），架构专属 FPU | — | [link](https://patchwork.kernel.org/project/kvm/patch/20260101090516.316883-3-pbonzini@redhat.com/) |
| B20 | vfio: selftests: only build on arm64/x86_64 | arm | N-A | VFIO selftests（非 KVM）构建门控，显式排除 riscv | — | [link](https://patchwork.kernel.org/project/kvm/patch/20260202-vfio-selftest-only-64bit-v2-1-9c3ebb37f0f4@fb.com/) |
| B21 | Add test case for readonly memslots | x86 | **PATTERN** | 公共 `set_memory_region_test.c` 提取 + 只读 memslot 用例；riscv 已支持 `KVM_MEM_READONLY` | `set_memory_region_test.c`（公共），只读用例需 riscv 化 | [link](https://patchwork.kernel.org/project/kvm/patch/57c05d4d7db845be9250b7a4f6537e98636d70ca.1772090306.git.yohei.kojima@sony.com/) |
| B22 | arm64: Improve diagnostics set_id_regs | arm | N-A | arm64 set_id_regs 诊断改进 | — | [link](https://patchwork.kernel.org/project/kvm/patch/20260317-kvm-arm64-set-id-regs-aarch64-v5-2-a60f2b956e22@kernel.org/) |
| B23 | vfio: selftests: Build tests on aarch64 | arm | N-A | VFIO selftests（非 KVM）arm64 使能 | — | [link](https://patchwork.kernel.org/project/kvm/patch/20260319-vfio-selftests-aarch64-v2-1-bb2621c24dc4@fb.com/) |
| B24 | arm64: per-VM WFI/WFE exit disable CAP | arm | **PATTERN** | 空转指令 disable-exits/直通协商；riscv 陷 WFI 但无 disable-exits | `vcpu_insn.c`/`vcpu.c` + 新 `KVM_CAP_RISCV_DISABLE_EXITS` + selftest | [link](https://patchwork.kernel.org/project/kvm/patch/20260408202557.2102476-3-dwmw2@infradead.org/) |
| B25 | vfio: selftests: Allow builds ARCH=x86 | x86 | N-A | VFIO selftests（非 KVM）x86 构建 | — | [link](https://patchwork.kernel.org/project/kvm/patch/20260428232707.2139059-1-dmatlack@google.com/) |
| B26 | fix steal_time for arm64 | arm | N-A | steal_time 公共但此为 `__aarch64__` 分支修复；riscv `__riscv` STA 分支已独立工作 | (riscv 已支持) | [link](https://patchwork.kernel.org/project/kvm/patch/20260504112808.21276-1-sebott@redhat.com/) |
| B27 | SVM: Always intercept ICEBP, INT1 selftests | x86 | N-A | x86 SVM ICEBP/INT1 调试异常 | — | [link](https://patchwork.kernel.org/project/kvm/patch/e03f092dfbb7d391a6bf2797ba01e122ba080bcd.camel@infradead.org/) |
| B28 | x86: Return VM's actual APIC bus frequency | x86 | N-A | x86 LAPIC 总线频率（riscv AIA 无 APIC 频率语义） | — | [link](https://patchwork.kernel.org/project/kvm/patch/20260522173526.3539407-2-seanjc@google.com/) |
| B29 | arm64: Run shadow_stage2 varying guest modes | arm | N-A | arm64 nested shadow stage-2；riscv 无嵌套 | — | [link](https://patchwork.kernel.org/project/kvm/patch/20260528045930.450339-1-itaru.kitayama@fujitsu.com/) |
| B30 | fix steal_time arm64 host page size >4K | arm | N-A | steal_time `__aarch64__` 分支页大小修复；riscv 分支独立（页大小健壮性思想可自查） | (riscv 已支持) | [link](https://patchwork.kernel.org/project/kvm/patch/335f21e5-493d-012d-b07c-2e48cc2b9aeb@redhat.com/) |
| B31 | x86: fix spelling in xapic_ipi_test comment | x86 | N-A | x86 xapic 测试注释拼写 | — | [link](https://patchwork.kernel.org/project/kvm/patch/20260702015739.367597-1-wangyan01@kylinos.cn/) |

## 全量判定表 B：kvm-unit-tests（T，47 条，独立用户态套件）

> 全部 **N-A**（对 linux-riscv 内核 KVM 无落点）。riscv 在 kvm-unit-tests 上游有独立 `riscv/` 目标与维护线；本批均为 x86 架构专属测试内容或 x86 目标构建/CI 基础设施。仅 #2/#18/#44 含极低价值「思想借鉴」，已注明但不列为候选。

| # | 系列 | 判定 | N-A 理由 | web_url |
|---|---|---|---|---|
| T1 | nVMX: Clear A/D enable bit in EPTP … | N-A | 嵌套 VMX（EPT A/D） | [link](https://patchwork.kernel.org/project/kvm/patch/20250214160639.981517-1-seanjc@google.com/) |
| T2 | x86: Make set/clear_bit() atomic | N-A | x86 lib 位操作 SMP 正确性（riscv lib 用 AMO，另仓） | [link](https://patchwork.kernel.org/project/kvm/patch/20250214173644.22895-1-nsaenz@amazon.com/) |
| T3 | x86: Drop "enabled" from kvm_vcpu_pv_apf_data | N-A | x86 async-PF PV 结构；riscv 无 async-PF | [link](https://patchwork.kernel.org/project/kvm/patch/20250221225744.2231975-1-seanjc@google.com/) |
| T4 | x86: Move SMP #defines apic-defs.h→smp.h | N-A | x86 头文件重构 | [link](https://patchwork.kernel.org/project/kvm/patch/20250221233832.2251456-1-seanjc@google.com/) |
| T5 | x86: ioapic EOI interception testcase | N-A | x86 IOAPIC | [link](https://patchwork.kernel.org/project/kvm/patch/20250304211348.126107-1-seanjc@google.com/) |
| T6 | nVMX: canonical checks forced emulation | N-A | 嵌套 VMX + x86 FEP | [link](https://patchwork.kernel.org/project/kvm/patch/20250523090848.16133-1-chenyi.qiang@intel.com/) |
| T7 | x86/pks: skip PKS test if unsupported | N-A | x86 PKS（保护键） | [link](https://patchwork.kernel.org/project/kvm/patch/20250529205904.3790571-1-seanjc@google.com/) |
| T8 | x86/pmu: zero PERF_GLOBAL_CTRL | N-A | x86 perfmon PMU；riscv 为 SBI-PMU | [link](https://patchwork.kernel.org/project/kvm/patch/20250529210157.3791397-1-seanjc@google.com/) |
| T9 | x86/run: -vnc none iff QEMU supports | N-A | x86 目标 run 脚本 | [link](https://patchwork.kernel.org/project/kvm/patch/20250529213458.3796184-1-seanjc@google.com/) |
| T10 | travis.yml: Remove aarch64 job | N-A | 项目 CI 配置 | [link](https://patchwork.kernel.org/project/kvm/patch/20250530115214.187348-1-thuth@redhat.com/) |
| T11 | x86: Disable PIT re-injection for (x2)AVIC | N-A | x86 PIT/AVIC | [link](https://patchwork.kernel.org/project/kvm/patch/20250603235433.196211-1-seanjc@google.com/) |
| T12 | x86: Delete split IRQ chip apic/ioapic | N-A | x86 APIC/IOAPIC | [link](https://patchwork.kernel.org/project/kvm/patch/20250604000812.199087-1-seanjc@google.com/) |
| T13 | x86/pmu: verify all GP counters | N-A | x86 perfmon PMU | [link](https://patchwork.kernel.org/project/kvm/patch/20250611075842.20959-1-dapeng1.mi@linux.intel.com/) |
| T14 | x86/emulator64: non-canonical CR2 | N-A | x86 指令模拟器 | [link](https://patchwork.kernel.org/project/kvm/patch/20250612141637.131314-1-minipli@grsecurity.net/) |
| T15 | x86/run: -display none | N-A | x86 目标 run 脚本 | [link](https://patchwork.kernel.org/project/kvm/patch/20250708150658.136533-1-pbonzini@redhat.com/) |
| T16 | x86: nSVM npt_rw_pfwalk_check | N-A | 嵌套 SVM（NPT） | [link](https://patchwork.kernel.org/project/kvm/patch/20250714095614.30657-1-maqianga@uniontech.com/) |
| T17 | x86/pmu: fix compilation on macOS | N-A | x86 PMU 测试 macOS 构建修复 | [link](https://patchwork.kernel.org/project/kvm/patch/20250723164742.1174289-1-thuth@redhat.com/) |
| T18 | x86: Print error code for unhandled exceptions | N-A | x86 测试 harness UX（打印错误码；思想可自查，价值低） | [link](https://patchwork.kernel.org/project/kvm/patch/20250724191557.1990954-1-minipli@grsecurity.net/) |
| T19 | x86: nSVM instruction interrupts | N-A | 嵌套 SVM | [link](https://patchwork.kernel.org/project/kvm/patch/20250820162926.3498713-1-chengkev@google.com/) |
| T20 | x86: nSVM EPT A/D bits | N-A | 嵌套 SVM | [link](https://patchwork.kernel.org/project/kvm/patch/20250820162951.3499017-1-chengkev@google.com/) |
| T21 | x86/svm: extract IP from LBR MSRs | N-A | x86 SVM LBR | [link](https://patchwork.kernel.org/project/kvm/patch/20251113224639.2916783-1-yosry.ahmed@linux.dev/) |
| T22 | x86/emulator: DR6_BUS_LOCK writable | N-A | x86 调试寄存器/总线锁检测 | [link](https://patchwork.kernel.org/project/kvm/patch/20251113235416.1709504-1-seanjc@google.com/) |
| T23 | x86/vmexit: WBINVD/INVD latency | N-A | x86 缓存指令 VM-Exit | [link](https://patchwork.kernel.org/project/kvm/patch/20251113235946.1710922-1-seanjc@google.com/) |
| T24 | xsave: AVX instruction emulation | N-A | x86 XSAVE/AVX | [link](https://patchwork.kernel.org/project/kvm/patch/20251114003228.60592-1-pbonzini@redhat.com/) |
| T25 | x86/debug: DR7 local/global enable macros | N-A | x86 调试寄存器 | [link](https://patchwork.kernel.org/project/kvm/patch/20251126191736.907963-1-seanjc@google.com/) |
| T26 | x86/svm: unsupported instruction intercept | N-A | x86 SVM 拦截 | [link](https://patchwork.kernel.org/project/kvm/patch/20251205080228.4055341-3-chengkev@google.com/) |
| T27 | x86/cstart: fix x2APIC SMP save_id | N-A | x86 引导/x2APIC | [link](https://patchwork.kernel.org/project/kvm/patch/20251218232618.2504147-1-seanjc@google.com/) |
| T28 | x86/svm: exit code as u64 | N-A | x86 SVM | [link](https://patchwork.kernel.org/project/kvm/patch/20251230191342.4052363-1-seanjc@google.com/) |
| T29 | x86: increase timeout vmx_pf_*_test | N-A | 嵌套 VMX 测试超时 | [link](https://patchwork.kernel.org/project/kvm/patch/20260102183039.496725-1-yosry.ahmed@linux.dev/) |
| T30 | x86: #PF test for SVM DecodeAssists | N-A | x86 SVM DecodeAssists | [link](https://patchwork.kernel.org/project/kvm/patch/20260115164342.27736-1-alejandro.garciavallejo@amd.com/) |
| T31 | x86: apic/vmexit serialize deadline timer | N-A | x86 APIC deadline 定时器 | [link](https://patchwork.kernel.org/project/kvm/patch/7acdd9974effabe5dc461aa755eacf9fb0697467.1770116601.git.isaku.yamahata@intel.com/) |
| T32 | x86: nVMX RTM debugging retry loop | N-A | 嵌套 VMX RTM 调试 | [link](https://patchwork.kernel.org/project/kvm/patch/20260227213849.3653331-1-jmattson@google.com/) |
| T33 | x86: increase access_fep timeout | N-A | x86 强制模拟前缀（FEP）测试 | [link](https://patchwork.kernel.org/project/kvm/patch/20260317225327.4068448-1-yosry@kernel.org/) |
| T34 | x86/eventinj: fix flush_cache for Clang | N-A | x86 事件注入测试构建修复 | [link](https://patchwork.kernel.org/project/kvm/patch/20260413094948.14505-1-thuth@redhat.com/) |
| T35 | x86: xsave APX instruction emulation | N-A | x86 XSAVE/APX | [link](https://patchwork.kernel.org/project/kvm/patch/20260420212355.507827-1-chang.seok.bae@intel.com/) |
| T36 | x86: Disable PKU vmx_pf_*_test | N-A | 嵌套 VMX + x86 PKU | [link](https://patchwork.kernel.org/project/kvm/patch/20260514200536.1603737-1-seanjc@google.com/) |
| T37 | x86/xsave: VMOVDQA→VMOVNTDQA | N-A | x86 XSAVE/SIMD | [link](https://patchwork.kernel.org/project/kvm/patch/20260514204020.1614792-1-seanjc@google.com/) |
| T38 | x86/apic: LVT timer mode readback | N-A | x86 APIC LVT | [link](https://patchwork.kernel.org/project/kvm/patch/20260514210708.1627866-1-seanjc@google.com/) |
| T39 | x86/debug: DR6 empty on INT1/ICEBP #DB | N-A | x86 调试寄存器/#DB | [link](https://patchwork.kernel.org/project/kvm/patch/20260514211237.1629774-1-seanjc@google.com/) |
| T40 | x86/emulator: ENTER + emulated MMIO | N-A | x86 指令模拟器 | [link](https://patchwork.kernel.org/project/kvm/patch/20260514211510.1630673-1-seanjc@google.com/) |
| T41 | x86: intel-iommu GCC 16.1 workaround | N-A | x86 IOMMU 测试编译器规避 | [link](https://patchwork.kernel.org/project/kvm/patch/20260520084546.365816-1-thuth@redhat.com/) |
| T42 | svm: fix rflags and rax offsets | N-A | x86 SVM | [link](https://patchwork.kernel.org/project/kvm/patch/20260521092311.86030-1-pbonzini@redhat.com/) |
| T43 | x86/vmx: remove superfluous vmx_cet config | N-A | x86 VMX CET | [link](https://patchwork.kernel.org/project/kvm/patch/20260527152333.4062942-1-seanjc@google.com/) |
| T44 | x86/run: separate -accel option | N-A | x86 目标 run 脚本（加速器选择；思想可借鉴，价值低） | [link](https://patchwork.kernel.org/project/kvm/patch/20260528071712.1407929-1-xiaoyao.li@intel.com/) |
| T45 | x86/svm: comprehensive GMET tests | N-A | x86 SVM GMET | [link](https://patchwork.kernel.org/project/kvm/patch/20260528192410.1047581-1-jon@nutanix.com/) |
| T46 | x86/emulator64: CMPXCHG8B/16B emulation | N-A | x86 指令模拟器 | [link](https://patchwork.kernel.org/project/kvm/patch/20260706062153.346-1-sarunkod@amd.com/) |
| T47 | x86/vmx: skip LAM CR3 bits 32-bit guest | N-A | 嵌套 VMX + x86 LAM | [link](https://patchwork.kernel.org/project/kvm/patch/20260707070240.78295-1-xudong.hao@intel.com/) |

---

## 结论要点
- **selftests（内核 tree）是唯一有真实移植价值的子类**：6 个候选中 B15/B1/B12 为通用层直接受益（riscv 已构建对应公共测试），B21/B24 为「特性已具备/机制通用、需 riscv 侧补测试或 CAP」的 PATTERN。
- **kvm-unit-tests 全 N-A**：独立用户态仓库 + 本批纯 x86 架构测试内容，与 linux-riscv 内核 KVM 移植无交集。
- 验证依据：`arch/riscv/kvm/{Kconfig,vm.c,mmu.c,vcpu.c}`、`aia_imsic.c`、`tools/testing/selftests/kvm/{Makefile.kvm,irqfd_test.c,steal_time.c,lib/riscv/processor.c}`；curl 核对 B1/B12/B15/B21 diff 触及文件。
