# RISC-V 跨架构通用化贡献机会

## 1. 范围与结论

本文只讨论 arm64、x86 与 RISC-V 之间的 **架构接口通用化**：把已经在两个或三个架构中重复出现的控制流、默认实现、能力判断或状态选择下沉到 generic core，同时保留指令编码、异常入口、页表语义、固件策略和硬件动作等架构边界。

固定研究基线为：

- mainline：`d96fcfe1b7f94ac742984ae7986b94a116abff1b`，Linux 7.2-rc2，日期 `2026-07-10`；
- linux-next：`bee763d5f341b99cf472afeb508d4988f62a6ca1`，`next-20260710`；
- 邮件窗口：`2025-01-01` 至 `2026-07-10`。

统一注册表在 Genericization 领域保留 **18 个主候选**：

| 维度 | 统计 |
|---|---|
| 优先级 | P0：5；P1：12；P2：1 |
| G 分类 | G2：16；G3：2 |
| 上游状态 | unclaimed：17；dormant：1 |
| 原始架构 | x86：1；arm64：8；x86+arm64：9 |

这里的状态描述“该精确通用化工作是否已被上游认领”。公共前置已经进入 mainline 或 linux-next、但注册表所定义的剩余工作仍无人推进时，状态仍为 `unclaimed`，并在候选卡片的“基线校准”中单独说明。

优先级严格采用统一注册表的六维评分：

- `G2`：两个或更多架构重复实现，适合下沉公共 helper 或状态机；
- `G3`：RISC-V 已有 fallback，但需要架构语义证明或快路径优化；
- 基础阈值：P0=24-30、P1=18-23、P2=12-17；存在有界依赖或实质架构证明时可降一级，不能只按总分忽略抽象风险。

## 2. 18 项总表

| ID | 候选 | 分组 | G | P | 状态 | 原始架构 | 总分 |
|---|---|---|---|---|---|---|---:|
| GEN-01 | runtime-const 公共迭代器 | 共享状态机 | G2 | P1 | unclaimed | x86+arm64 | 23 |
| GEN-02 | 通用 register-offset table walker | 机械 helper | G2 | P0 | unclaimed | x86+arm64 | 29 |
| GEN-03 | 复用现有 `perf_get_regs_user()` generic fallback | 机械 helper | G2 | P0 | unclaimed | x86+arm64 | 29 |
| GEN-04 | 生成式复用 ptdump 层级 callback | 机械 helper | G2 | P1 | unclaimed | x86+arm64 | 23 |
| GEN-05 | ACPI early table map/unmap 默认实现 | generic default | G2 | P1 | unclaimed | x86+arm64 | 23 |
| GEN-06 | 下沉 `raw_pci_read/write()` 通用 bus lookup | 机械 helper | G2 | P0 | unclaimed | arm64 | 29 |
| GEN-07 | PCI topology opt-in `dev_to_node` helper | generic default | G2 | P1 | unclaimed | arm64 | 23 |
| GEN-08 | 统一 `no-steal-acc` 参数与策略所有权 | 共享状态机 | G2 | P1 | unclaimed | x86 | 23 |
| GEN-09 | 提供 `copy_oldmem_page()` generic default | generic default | G2 | P0 | unclaimed | arm64 | 29 |
| GEN-10 | crash/kdump 默认 RAM walk hooks 与解析 wrapper | generic default | G2 | P1 | unclaimed | x86+arm64 | 23 |
| GEN-11 | ftrace call-ops 选择 helper | 共享状态机 | G2 | P1 | unclaimed | arm64 | 23 |
| GEN-12 | LZO 快路径改用高效非对齐能力 | 能力门控 | G3 | P1 | unclaimed | x86+arm64 | 20 |
| GEN-13 | 机械下沉 cacheinfo `ci_leaf_init()` | 机械 helper | G2 | P0 | unclaimed | arm64 | 29 |
| GEN-14 | 用 `GENERIC_ARCH_TOPOLOGY` 替换架构名判断 | 能力门控 | G2 | P1 | dormant | arm64 | 23 |
| GEN-15 | PCI ACPI host 使用现有能力组合门控 | 能力门控 | G2 | P1 | unclaimed | arm64 | 23 |
| GEN-16 | 显式 opt-in 的 no-immediate-flush young-bit helper | 页表/高风险 | G3 | P2 | unclaimed | arm64 | 15 |
| GEN-17 | 向下增长栈 uretprobe 存活 helper | 机械 helper | G2 | P1 | unclaimed | x86+arm64 | 23 |
| GEN-18 | 参数化 syscall trace symbol matcher | 机械 helper | G2 | P1 | unclaimed | x86+arm64 | 23 |

## 3. 机械 helper

<a id="gen-02"></a>
### GEN-02：通用 register-offset table walker

- **注册表归属**：`GEN:HC-02 + CORE:CAH-04`；G2；P0；unclaimed；原始架构 x86+arm64。
- **六维评分**：impact=4，generality=5，readiness=5，validation=5，hardware-independence=5，acceptance=5；总分 29。
- **基线校准**：mainline 中三架构仍有重复实现，linux-next 未收敛。
- **精确路径与符号**：`arch/arm64/kernel/ptrace.c:104`、`arch/x86/kernel/ptrace.c:125`、`arch/riscv/kernel/ptrace.c:496`、`kernel/ptrace.c`、`include/linux/ptrace.h`、`regs_query_register_offset()`。
- **RISC-V 缺口**：三个架构共同重复的契约只包括遍历 `struct pt_regs_offset` 表并返回 offset。独立审查确认 `regs_query_register_name()` 并非三架构共同实现，首版不得把 name lookup 一并抽象。
- **通用化方案**：在 `kernel/ptrace.c` 或 `include/linux/ptrace.h` 提供 offset-only table walker；三架构继续拥有各自的 `regoffset_table`、别名和 ABI 条件，仅保留薄 wrapper。
- **首版系列边界**：第一补丁增加 table walker 与终止项规则；随后分别迁移 arm64、x86、RISC-V；最后增加表驱动 KUnit。不要在首版统一表布局或 name lookup。
- **阻塞与风险**：表终止符、重复别名、x86 32/64 位条件项，以及错误地把架构特有名称查询扩展成公共 ABI。
- **验证**：kprobe、uprobe、fprobe 的合法/非法 `%reg` 参数；重复别名和终止项 KUnit；arm64、x86、RISC-V 构建。
- **维护者方向**：ptrace core、tracing/kprobes，以及 arm64、x86、RISC-V 维护者。
- **来源**：[ptrace core](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/kernel/ptrace.c?id=d96fcfe1b7f94ac742984ae7986b94a116abff1b)、[RISC-V ptrace](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/arch/riscv/kernel/ptrace.c?id=d96fcfe1b7f94ac742984ae7986b94a116abff1b)、[arm64 ptrace](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/arch/arm64/kernel/ptrace.c?id=d96fcfe1b7f94ac742984ae7986b94a116abff1b)、[x86 ptrace](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/arch/x86/kernel/ptrace.c?id=d96fcfe1b7f94ac742984ae7986b94a116abff1b)。

<a id="gen-03"></a>
### GEN-03：复用现有 `perf_get_regs_user()` generic fallback

- **注册表归属**：`GEN:HC-03 + CORE:CAH-06`；G2；P0；unclaimed；原始架构 x86+arm64。
- **六维评分**：impact=4，generality=5，readiness=5，validation=5，hardware-independence=5，acceptance=5；总分 29。
- **基线校准**：arm64、RISC-V 与 x86-32 的实现同构；x86-64 因 NMI 稳定副本而特殊；linux-next 未变化。
- **精确路径与符号**：`include/linux/perf_regs.h`、`arch/arm64/kernel/perf_regs.c:101`、`arch/riscv/kernel/perf_regs.c:38`、`arch/x86/kernel/perf_regs.c:103`、`perf_get_regs_user()`。
- **RISC-V 缺口**：generic fallback 已经存在，缺口不是再发明一个默认 API，而是让 `HAVE_PERF_REGS` 架构复用现有 fallback，同时保留需要稳定寄存器副本的架构 override。
- **通用化方案**：arm64、RISC-V 和 x86-32 使用现有 generic inline；x86-64 保留 NMI-safe override。独立审查不支持为此新增未经需要证明的 capability。
- **首版系列边界**：先证明 generic fallback 与三份简单实现完全等价；删除 arm64/RISC-V/x86-32 重复定义；不改变 x86-64 NMI 路径。
- **阻塞与风险**：未来 RISC-V NMI/PMU 是否需要稳定副本；native/compat ABI、寄存器 mask 和 sample layout 必须不变。
- **验证**：`perf record --sample-regs-user`、callchain、compat task、NMI PMU 压力；逐字段比较迁移前后 perf sample ABI。
- **维护者方向**：perf core、arm64、x86、RISC-V。
- **来源**：[generic perf regs API](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/include/linux/perf_regs.h?id=d96fcfe1b7f94ac742984ae7986b94a116abff1b)、[RISC-V perf regs](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/arch/riscv/kernel/perf_regs.c?id=d96fcfe1b7f94ac742984ae7986b94a116abff1b)、[arm64 perf regs](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/arch/arm64/kernel/perf_regs.c?id=d96fcfe1b7f94ac742984ae7986b94a116abff1b)。

<a id="gen-04"></a>
### GEN-04：生成式复用 ptdump 层级 callback

- **注册表归属**：`GEN:HC-04`；G2；P1；unclaimed；原始架构 x86+arm64。
- **六维评分**：impact=3，generality=5，readiness=4，validation=4，hardware-independence=5，acceptance=2；总分 23。
- **基线校准**：三架构 wrapper 在 mainline 中仍重复，linux-next 未收敛；邮件显示 ptdump 邻近工作活跃，但精确通用化无人认领。
- **精确路径与符号**：`arch/arm64/mm/ptdump.c:254`、`arch/x86/mm/dump_pagetables.c:391`、`arch/riscv/mm/ptdump.c:321`、`include/linux/ptdump.h`、`note_page_pte/pmd/pud/p4d/pgd/flush`。
- **RISC-V 缺口**：每个架构都维护一组形状相同的层级 wrapper，修复 folded level 或 callback 接口时需要重复修改；但 raw entry 类型和 effective protection 仍是架构语义。
- **通用化方案**：首选生成式宏或 inline helper，例如 `DEFINE_PTDUMP_LEVEL_CALLBACKS()`，只生成类型适配 wrapper，不改变 `ptdump_state` ABI，也不把页表值强制归一化为一个通用类型。
- **首版系列边界**：增加生成式 helper；迁移一个架构验证接口；再迁移其余架构。统一 callback 结构或 raw value 表示不属于首版。
- **阻塞与风险**：folded level 编号、effective protection callback、不同宽度 entry，以及宏抽象可能降低可读性。邮件核验将其标为低收益，更适合作为 ptdump 系列的附带清理。
- **验证**：逐行比较 `debugfs/kernel_page_tables`；`CONFIG_DEBUG_WX` 结果不变；覆盖不同页表级数和 folded 配置。
- **维护者方向**：ptdump/MM、arm64、x86、RISC-V。
- **来源**：[KVM arm64 ptdump v2 邻近工作](https://lore.kernel.org/linux-arm-kernel/20260630121005.1130996-7-weilin.chang@arm.com/)。

<a id="gen-06"></a>
### GEN-06：下沉 `raw_pci_read/write()` 通用 bus lookup

- **注册表归属**：`GEN:HC-07`；G2；P0；unclaimed；原始架构 arm64。
- **六维评分**：impact=4，generality=5，readiness=5，validation=5，hardware-independence=5，acceptance=5；总分 29。
- **基线校准**：arm64 与 RISC-V 的 bus lookup 路径在 mainline 中重复，linux-next 未变化。
- **精确路径与符号**：`arch/arm64/kernel/pci.c:14,24`、`arch/riscv/kernel/acpi.c:319,329`、`arch/x86/pci/common.c`、`drivers/pci/access.c`、`pci_find_bus()`、`raw_pci_read/write()`。
- **RISC-V 缺口**：arm64/RISC-V 都先 `pci_find_bus()`，再调用 `bus->ops->{read,write}`，却分别保存在架构目录；x86 同名接口还承载 legacy config mechanism，不能被无条件替换。
- **通用化方案**：在 `drivers/pci/access.c` 提供 `pci_generic_raw_read/write()`；arm64/RISC-V 直接使用；x86 仅在不需要 legacy raw ops 的路径选择复用。
- **首版系列边界**：增加 generic helper；迁移 arm64；迁移 RISC-V；用注释和类型约束明确 bus reference/lifetime。不要在同一系列重构 x86 legacy PCI。
- **阻塞与风险**：PCI domain、热拔插期间 bus 生命周期、AML config access、x86 legacy config mechanism。
- **验证**：ACPI AML PCI config access、ECAM、多 PCI domain、热插拔和错误 bus/device/function。
- **维护者方向**：PCI core、ACPI PCI、arm64、RISC-V；x86 作为潜在复用者参与审阅。
- **来源**：[PCI access core](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/drivers/pci/access.c?id=d96fcfe1b7f94ac742984ae7986b94a116abff1b)。

<a id="gen-13"></a>
### GEN-13：机械下沉 cacheinfo `ci_leaf_init()`

- **注册表归属**：`GEN:HC-18`；G2；P0；unclaimed；原始架构 arm64。
- **六维评分**：impact=4，generality=5，readiness=5，validation=5，hardware-independence=5，acceptance=5；总分 29。
- **基线校准**：arm64 与 RISC-V 的 `ci_leaf_init()` 仍重复；linux-next 未收敛。
- **精确路径与符号**：`arch/arm64/kernel/cacheinfo.c:34`、`arch/riscv/kernel/cacheinfo.c:67`、`drivers/base/cacheinfo.c`、`include/linux/cacheinfo.h`、`ci_leaf_init()`、`use_arch_cache_info()`。
- **RISC-V 缺口**：可安全共用的是 leaf 的机械初始化和公共字段设置。DT、ACPI PPTT、ISA/CSR discovery 谁是权威来源，属于独立的架构和固件策略。
- **通用化方案**：只把 `ci_leaf_init()` 下沉为 `cacheinfo_init_leaf()` 或等价 helper，arm64/RISC-V 调用它；不触碰 `use_arch_cache_info()` 和信息来源优先级。
- **首版系列边界**：第一补丁增加公共初始化 helper；第二、第三补丁迁移 arm64 和 RISC-V。原 HC-18 的“来源 capability”必须拆出并降为附录观察，不与机械重构一起提交。
- **阻塞与风险**：必须证明 cache ID、leaf 数、共享 CPU map、firmware/ISA 优先级完全不变。
- **验证**：arm64/RISC-V 的 DT、ACPI PPTT、无固件 cache 描述启动；逐项比较 `/sys/devices/system/cpu/*/cache/`。
- **维护者方向**：cacheinfo core、ACPI PPTT、arm64、RISC-V。
- **来源**：[PPTT cache helper v6 邻近工作](https://lore.kernel.org/linux-arm-kernel/20251119122305.302149-6-ben.horgan@arm.com/)。

<a id="gen-17"></a>
### GEN-17：向下增长栈 uretprobe 存活 helper

- **注册表归属**：`GEN:HC-26`；G2；P1；unclaimed；原始架构 x86+arm64。
- **六维评分**：impact=3，generality=5，readiness=4，validation=4，hardware-independence=5，acceptance=2；总分 23。
- **基线校准**：arm64/RISC-V 实现仍重复，linux-next 未变化。
- **精确路径与符号**：`arch/arm64/kernel/probes/uprobes.c:139`、`arch/riscv/kernel/probes/uprobes.c:120`、`kernel/events/uprobes.c`、`arch_uretprobe_is_alive()`。
- **RISC-V 缺口**：arm64/RISC-V 对向下增长栈使用相同的普通调用 `<` 与 chain-call `<=` 比较，generic weak default 无法直接表达这一模式。
- **通用化方案**：在 uprobes core 提供 `uretprobe_is_alive_stack_grows_down()`，arm64/RISC-V 直接调用；x86 仅在 CET/shadow-stack 语义允许时评估接入。
- **首版系列边界**：只下沉纯栈比较；迁移 arm64/RISC-V；不尝试统一 trampoline、返回地址恢复或 shadow stack。
- **阻塞与风险**：GCS/CET、尾调用、信号帧、alt stack、异常帧和架构 trampoline。
- **验证**：递归、尾调用、chain call、signal/altstack，以及 GCS/CET/CFI 组合。
- **维护者方向**：uprobes、tracing、arm64、RISC-V。
- **来源**：[uretprobe/tracing core](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/kernel/trace/trace_uprobe.c?id=d96fcfe1b7f94ac742984ae7986b94a116abff1b)。

<a id="gen-18"></a>
### GEN-18：参数化 syscall trace symbol matcher

- **注册表归属**：`GEN:HC-27 + CORE:CAH-05`；G2；P1；unclaimed；原始架构 x86+arm64。
- **六维评分**：impact=3，generality=5，readiness=4，validation=4，hardware-independence=5，acceptance=2；总分 23。
- **基线校准**：arm64、RISC-V、x86 仍保留架构 matcher，linux-next 未出现完整通用化系列。
- **精确路径与符号**：`arch/arm64/include/asm/ftrace.h:203,210`、`arch/riscv/include/asm/ftrace.h:31,37`、`kernel/trace/trace_syscalls.c`、`arch_syscall_match_sym_name()`。
- **RISC-V 缺口**：缺口不是 syscall entry ABI，而是 generic tracing 仍要求架构用函数重复编码 native/compat wrapper 的前缀和别名规则。
- **通用化方案**：generic core 接收 native/compat prefix 与 alias 描述；架构只提供 `is_compat_syscall(regs)` 和前缀表；x86 保留 ia32/x32 多 ABI 规则。
- **首版系列边界**：先下沉字符串匹配框架；arm64/RISC-V 使用固定 prefix；最后让 x86 用表表达多 ABI prefix/alias。若 x86 证明抽象不足，不阻塞前两个架构的机械收敛。
- **阻塞与风险**：LTO/CFI 符号重写、compat wrapper 命名、x32/ia32、多重 alias 和静态 syscall wrapper。
- **验证**：`perf trace`、tracefs `sys_enter_*`/`sys_exit_*`、native/compat selftests、kallsyms、LTO、CFI 构建。
- **维护者方向**：tracing/syscall core、arm64、x86、RISC-V。
- **来源**：[syscall tracing core](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/kernel/trace/trace_syscalls.c?id=d96fcfe1b7f94ac742984ae7986b94a116abff1b)、[RISC-V ftrace](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/arch/riscv/kernel/ftrace.c?id=d96fcfe1b7f94ac742984ae7986b94a116abff1b)、[arm64 ftrace](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/arch/arm64/kernel/ftrace.c?id=d96fcfe1b7f94ac742984ae7986b94a116abff1b)。

## 4. Generic default

<a id="gen-05"></a>
### GEN-05：ACPI early table map/unmap 默认实现

- **注册表归属**：`GEN:HC-05 + GEN:HC-06`；G2；P1；unclaimed；原始架构 x86+arm64。
- **六维评分**：impact=3，generality=5，readiness=4，validation=4，hardware-independence=5，acceptance=2；总分 23。
- **基线校准**：三架构 early unmap 同构；arm64/RISC-V early map 同构，x86 多出 `phys == 0` 策略；linux-next 未变化。
- **精确路径与符号**：`arch/arm64/kernel/acpi.c:102`、`arch/x86/kernel/acpi/boot.c:121`、`arch/riscv/kernel/acpi.c:219`、`drivers/acpi/osl.c`、`include/linux/acpi.h`、`__acpi_map_table()`、`__acpi_unmap_table()`。
- **RISC-V 缺口**：默认 `early_memremap()`/`early_memunmap()` 生命周期被复制在架构目录，导致 ACPI early-table 修复无法由公共实现覆盖。
- **通用化方案**：ACPI OSL 提供 map/unmap default；公共实现负责 size 检查与 early map/unmap；x86 或其他架构可 override 物理地址 0、特殊映射窗口等策略。
- **首版系列边界**：两个独立核心补丁：先提供 unmap default，再提供 map default 和 x86 override；后续分别迁移三架构。map 与 unmap 可同一 cover letter，但必须独立可回退。
- **阻塞与风险**：链接符号所有权、`__init`/`__ref`、initmem 释放、极早期页表状态、x86 物理地址 0 策略。
- **验证**：三架构 ACPI 启动；RSDP/XSDT/MADT/SRAT；section mismatch；size=0/phys=0 故障注入。
- **维护者方向**：ACPI core、early memremap、arm64、x86、RISC-V。
- **来源**：[ACPI OSL](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/drivers/acpi/osl.c?id=d96fcfe1b7f94ac742984ae7986b94a116abff1b)、[RISC-V ACPI](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/arch/riscv/kernel/acpi.c?id=d96fcfe1b7f94ac742984ae7986b94a116abff1b)。

<a id="gen-07"></a>
### GEN-07：PCI topology opt-in `dev_to_node` helper

- **注册表归属**：`GEN:HC-08`；G2；P1；unclaimed；原始架构 arm64。
- **六维评分**：impact=3，generality=5，readiness=4，validation=4，hardware-independence=5，acceptance=2；总分 23。
- **基线校准**：arm64/RISC-V 都从 `bus->dev` 取得 node；asm-generic 的 `!CONFIG_NUMA` 默认仍返回 `-1`。
- **精确路径与符号**：`arch/arm64/kernel/pci.c:36`、`arch/riscv/include/asm/pci.h:19`、`include/asm-generic/topology.h:27`、`dev_to_node()`、`pcibus_to_node()`、`__pcibus_to_node()`。
- **RISC-V 缺口**：重复实现真实存在，但直接把 asm-generic 默认改为 `dev_to_node()` 会改变其他架构行为，且会破坏 `!CONFIG_NUMA` 分支的现有契约。
- **通用化方案**：在 PCI core 提供显式 opt-in helper/capability，由已经保证 PCI bus device node 初始化的架构选择；不改变全局 asm-generic 默认值。
- **首版系列边界**：增加 opt-in helper；arm64/RISC-V 迁移；以构建和运行审计确认哪些其他 generic PCI domain 架构能够选择。不要自动扩散到所有架构。
- **阻塞与风险**：PCI bus device 的 NUMA node 初始化时序，固件缺失节点时的 fallback，以及 x86 的 `__pcibus_to_node()` 特殊路径。
- **验证**：sysfs `numa_node`、PCI probe、IRQ affinity、多 segment、CPU/memory hotplug 后节点稳定性。
- **维护者方向**：PCI、NUMA/topology、arm64、RISC-V。
- **来源**：[asm-generic topology](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/include/asm-generic/topology.h?id=d96fcfe1b7f94ac742984ae7986b94a116abff1b)。

<a id="gen-09"></a>
### GEN-09：提供 `copy_oldmem_page()` generic default

- **注册表归属**：`GEN:HC-10`；G2；P0；unclaimed；原始架构 arm64。
- **六维评分**：impact=4，generality=5，readiness=5，validation=5，hardware-independence=5，acceptance=5；总分 29。
- **基线校准**：arm64/RISC-V 实现完全重复，linux-next 未变化；x86 因加密内存和 ioremap 路径需要 override。
- **精确路径与符号**：`arch/arm64/kernel/crash_dump.c:15`、`arch/riscv/kernel/crash_dump.c:12`、`kernel/crash_core.c`、`include/linux/crash_dump.h`、`fs/proc/vmcore.c`、`copy_oldmem_page()`；generic default 的具体落点应由 crash/kdump 维护者在现有 core 文件之间确定。
- **RISC-V 缺口**：`memremap(MEMREMAP_WB)`、`copy_to_iter()`、`memunmap()` 的默认 vmcore 读取路径复制在两个架构中。
- **通用化方案**：在 crash dump core 提供 `copy_oldmem_page_memremap()` 或直接提供可 override 的 generic default；arm64/RISC-V 使用默认实现，x86、s390 和机密计算架构保留特殊实现。
- **首版系列边界**：增加 default；迁移 arm64/RISC-V；不修改 x86 encrypted/private memory 行为，也不扩展 oldmem 映射策略。
- **阻塞与风险**：旧内存 cacheability、highmem、encrypted/private memory、不可 WB 映射区间。
- **验证**：kdump `/proc/vmcore`、跨页 offset/csize、短拷贝、映射失败、不同 crashkernel 布局。
- **维护者方向**：kdump/crash dump、arm64、RISC-V。
- **来源**：[crash dump API](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/include/linux/crash_dump.h?id=d96fcfe1b7f94ac742984ae7986b94a116abff1b)。

<a id="gen-10"></a>
### GEN-10：crash/kdump 默认 RAM walk hooks 与解析 wrapper

- **注册表归属**：`GEN:HC-11 + GEN:HC-12`；G2；P1；unclaimed；原始架构 x86+arm64。
- **六维评分**：impact=3，generality=5，readiness=4，validation=4，hardware-independence=5，acceptance=2；总分 23。
- **基线校准**：linux-next 已用 `crash_prepare_headers()` 和 `arch_*` hooks 收敛 crash header 主流程。原 HC-11 的 mainline-era callback 抽取边界已经过时，候选只剩默认 RAM walk hooks 和仍重复的轻量解析 wrapper。
- **精确路径与符号**：linux-next `arch/riscv/kernel/machine_kexec_file.c:40`、`arch/x86/kernel/crash.c:150,227`、`kernel/crash_reserve.c`、`kernel/kexec_file.c`、`crash_prepare_headers()`、`get_nr_ram_ranges_callback()`、`prepare_elf64_ram_headers_callback()`、`parse_crashkernel()`、`reserve_crashkernel_generic()`。
- **RISC-V 缺口**：公共 header/range 基础已经进入 linux-next，但默认 System RAM walk 和架构 wrapper 仍可继续收敛；架构 low/high、CMA、保留区和 ELF machine policy 不能被默认实现吞掉。
- **通用化方案**：基于 linux-next 新边界提供默认 RAM walk `arch_*` hooks；另以 policy callback 或参数保留 crashkernel size、high/low、CMA 和物理地址上限。
- **首版系列边界**：两个独立补丁组：一是默认 RAM walk hooks；二是保留 policy 的 crashkernel wrapper。不得回退到旧的“重写整个 crash ELF header 流程”方案。
- **阻塞与风险**：extra slot、低端内存排除、CMA crash ranges、memory hotplug、各架构默认 size/high/low 和地址上限。
- **验证**：crash hotplug、memory hotplug 后 ELF header 重建、kdump；`crashkernel=`、`,high`、`,low`、自动大小语法和资源树。
- **维护者方向**：kexec/kdump、crash reserve、x86、arm64、RISC-V。
- **来源**：[linux-next 公共 helper `5beabef0cffa`](https://git.kernel.org/pub/scm/linux/kernel/git/next/linux-next.git/commit/?id=5beabef0cffa)、[RISC-V 接入 `7b078a0aa275`](https://git.kernel.org/pub/scm/linux/kernel/git/next/linux-next.git/commit/?id=7b078a0aa275)、[mainline crash core](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/kernel/crash_core.c?id=d96fcfe1b7f94ac742984ae7986b94a116abff1b)。

## 5. 能力门控

<a id="gen-12"></a>
### GEN-12：LZO 快路径改用高效非对齐能力

- **注册表归属**：`GEN:HC-17`；G3；P1；unclaimed；原始架构 x86+arm64。
- **六维评分**：impact=4，generality=3，readiness=3，validation=4，hardware-independence=3，acceptance=3；总分 20。
- **基线校准**：`lib/lzo/lzodefs.h` 仍按 x86-64/arm64 架构名选择快路径，linux-next 未变化。
- **精确路径与符号**：`lib/lzo/lzodefs.h:24-39`、`CONFIG_HAVE_EFFICIENT_UNALIGNED_ACCESS`、`RISCV_EFFICIENT_UNALIGNED_ACCESS`、`LZO_USE_CTZ64`、`LZO_FAST_64BIT_MEMORY_ACCESS`。
- **RISC-V 缺口**：RISC-V 可能在部分平台具备高效非对齐访问，但这一属性可能是运行时、异构或固件相关，不能因为 RV64 就复制 arm64/x86 的编译期假设。
- **通用化方案**：优先验证现有 `BITS_PER_LONG == 64 && CONFIG_HAVE_EFFICIENT_UNALIGNED_ACCESS` 是否足够；只有现有能力过宽时才引入更精确的 `HAVE_FAST_UNALIGNED_64BIT_ACCESS`。
- **首版系列边界**：先只替换 `COPY8` 条件并保持当前 arm64/x86 可见配置不变；基准和异常测试通过后，再讨论 `LZO_USE_CTZ64` 与完整 64 位快路径；RISC-V enablement 必须作为独立补丁。
- **阻塞与风险**：运行时异构、misaligned trap/emulation、不同 cacheline 行为，以及“功能可用”与“性能足够快”的能力语义混淆。
- **验证**：LZO KUnit、随机语料、未对齐地址、边界长度、压缩/解压交叉验证；多款 RISC-V 平台性能和 trap 计数。
- **维护者方向**：LZO/lib、RISC-V unaligned-access、arm64、x86。
- **来源**：[LZO source](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/lib/lzo/lzo1x_compress.c?id=d96fcfe1b7f94ac742984ae7986b94a116abff1b)。

<a id="gen-14"></a>
### GEN-14：用 `GENERIC_ARCH_TOPOLOGY` 替换架构名判断

- **注册表归属**：`GEN:HC-20`；G2；P1；dormant；原始架构 arm64。
- **六维评分**：impact=3，generality=5，readiness=4，validation=4，hardware-independence=5，acceptance=2；总分 23。
- **基线校准**：2025-09 的 v4 提案截至 `2026-07-10` 未进入 mainline/linux-next，也未发现 v5，故严格标为 dormant。
- **精确路径与符号**：`drivers/base/arch_topology.c:466,833`、`CONFIG_ARM64 || CONFIG_RISCV`、`GENERIC_ARCH_TOPOLOGY`、`arch_cpu_is_threaded()`、`parse_acpi_topology()`。
- **RISC-V 缺口**：arm64/RISC-V 已共同选择 `GENERIC_ARCH_TOPOLOGY`，generic core 仍按架构名分支。独立审查确认无需新建 `ARCH_HAS_GENERIC_CPU_TOPOLOGY_MAP`。
- **通用化方案**：直接用现有 `GENERIC_ARCH_TOPOLOGY` 及已有 OF/ACPI 条件表达共享路径；复盘 dormant v4 的 review 反馈，保持现有架构可见集合和初始化时序。
- **首版系列边界**：只替换两个架构名判断并补构建/启动测试；不同时重构 topology ownership、logical-map 或 ACPI/DT parser。
- **阻塞与风险**：`arch_cpu_is_threaded()` fallback、CPU logical map ownership、ACPI/DT 初始化顺序、热插拔。
- **验证**：DT cpu-map、ACPI PPTT、SMT 开关、CPU hotplug、不同 possible/present CPU 集。
- **维护者方向**：driver core/topology、ACPI PPTT、arm64、RISC-V。
- **来源**：[2025-09 v4 提案](https://lore.kernel.org/linux-arm-kernel/20250923015409.15983-2-cuiyunhui@bytedance.com/)。

<a id="gen-15"></a>
### GEN-15：PCI ACPI host 使用现有能力组合门控

- **注册表归属**：`GEN:HC-21`；G2；P1；unclaimed；原始架构 arm64。
- **六维评分**：impact=3，generality=5，readiness=4，validation=4，hardware-independence=5，acceptance=2；总分 23。
- **基线校准**：`drivers/pci/pci-acpi.c` 仍使用 `CONFIG_ARM64 || CONFIG_RISCV`，linux-next 未变化。
- **精确路径与符号**：`drivers/pci/pci-acpi.c:1538`、`drivers/acpi/pci_root.c`、`PCI_DOMAINS_GENERIC`、`PCI_ECAM`、`ACPI`。
- **RISC-V 缺口**：共享 host bridge 路径以架构名门控，导致具备同一 PCI/ACPI 能力组合的架构无法自然复用。
- **通用化方案**：优先证明 `PCI_DOMAINS_GENERIC && PCI_ECAM && ACPI` 足以表达现有 arm64/RISC-V 路径；只有出现无法表达的反例，才考虑新增 capability。独立审查明确反对未经证明直接引入 `PCI_ACPI_GENERIC_ROOT`。
- **首版系列边界**：先做反例构建矩阵；以现有能力组合替换架构名；保留 GSI/MSI domain、MCFG quirk、segment policy 和资源转换的 override。
- **阻塞与风险**：INTx/GSI、MSI domain、MCFG quirks、多 segment、root-bus resource translation。
- **验证**：多 segment ECAM、MSI、INTx、ACPI hotplug、资源窗口、错误 MCFG 与 quirk 平台。
- **维护者方向**：PCI core、ACPI PCI、arm64、RISC-V。
- **来源**：[ACPI PCI root](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/drivers/acpi/pci_root.c?id=d96fcfe1b7f94ac742984ae7986b94a116abff1b)。

## 6. 共享状态机

<a id="gen-01"></a>
### GEN-01：runtime-const 公共迭代器

- **注册表归属**：`GEN:HC-01`；G2；P1；unclaimed；原始架构 x86+arm64。
- **六维评分**：impact=3，generality=5，readiness=4，validation=4，hardware-independence=5，acceptance=2；总分 23。
- **基线校准**：三架构迭代控制流仍重复；邻近 `runtime_const_mask_32` v5 在 `2026-07-10` 仍活跃，但未抽取公共迭代器。
- **精确路径与符号**：`arch/arm64/include/asm/runtime-const.h:38-90`、`arch/x86/include/asm/runtime-const.h:44-75`、`arch/riscv/include/asm/runtime-const.h:160-270`、`runtime_const_init()`、`runtime_const_fixup()`。
- **RISC-V 缺口**：section 遍历、fixup 调度和 init 控制流重复；架构真正需要拥有的是 instruction encoding、取址、shift 和 text patch。
- **通用化方案**：公共层提供 section 起止、遍历和 callback 调度；架构定义 `runtime_const_ptr()`、`runtime_const_shift_right_32()` 与 `__runtime_fixup_*()`。独立审查将其从 P0 调整为 G2/P1，因为跨三架构 text patch 的协调成本不低。
- **首版系列边界**：等待邻近 v5 稳定；增加 `runtime_const_apply()`；逐架构迁移；最后再考虑 init macro。与 RISC-V IRQ runtime-constant 接线是依赖关系，不与 IRQ 候选合并。
- **阻塞与风险**：section layout、相对偏移类型、模块 policy、text writable 时机、I-cache 同步和 noinstr。
- **验证**：三架构构建/启动；`USER_PTR_MAX` 等 runtime constant；objdump、relocation、模块和 text-patching 测试。
- **维护者方向**：runtime-const/text patching、arm64、x86、RISC-V。
- **来源**：[runtime_const_mask_32 v5 review](https://lore.kernel.org/linux-arm-kernel/178366995930.1208691.2993932866462893112.b4-review@b4/)。

<a id="gen-08"></a>
### GEN-08：统一 `no-steal-acc` 参数与策略所有权

- **注册表归属**：`GEN:HC-09`；G2；P1；unclaimed；原始架构 x86。
- **六维评分**：impact=3，generality=5，readiness=4，validation=4，hardware-independence=5，acceptance=2；总分 23。
- **基线校准**：arm64、RISC-V、x86 KVM、x86 VMware 至少四处注册同名 early parameter；linux-next 未变化。
- **精确路径与符号**：`arch/arm64/kernel/paravirt.c:35`、`arch/riscv/kernel/paravirt.c:27`、`arch/x86/kernel/kvm.c:65`、`arch/x86/kernel/cpu/vmware.c:159`、`kernel/sched/cputime.c`、`paravirt_steal_accounting_enabled()`。
- **RISC-V 缺口**：同一 boot parameter 的解析和策略状态由各后端分别拥有，后续 scheduler accounting 行为可能分叉。
- **通用化方案**：由 scheduler/paravirt core 注册唯一参数并保存全局 policy；架构/backend 查询公共状态。不要让公共层接管各 hypervisor backend 的 enable 时序。
- **首版系列边界**：先只统一参数解析和只读 policy accessor；逐 backend 迁移；确认 x86 KVM 与 VMware 共存语义后再考虑 static key。
- **阻塞与风险**：x86 局部策略所有权、backend 初始化先后、参数 ABI、同时编译多个 backend。
- **验证**：带/不带 `no-steal-acc` 启动；KVM、VMware、arm64、RISC-V；`/proc/stat` steal time 和 scheduler accounting。
- **维护者方向**：scheduler、paravirt、KVM x86、VMware、arm64、RISC-V。
- **来源**：[RISC-V paravirt](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/arch/riscv/kernel/paravirt.c?id=d96fcfe1b7f94ac742984ae7986b94a116abff1b)。

<a id="gen-11"></a>
### GEN-11：ftrace call-ops 选择 helper

- **注册表归属**：`GEN:HC-14`；G2；P1；unclaimed；原始架构 arm64。
- **六维评分**：impact=3，generality=5，readiness=4，validation=4，hardware-independence=5，acceptance=2；总分 23。
- **基线校准**：arm64/RISC-V ops 选择控制流重复；ftrace 邻近 direct-call 工作活跃，但精确 helper 无人认领。
- **精确路径与符号**：`arch/arm64/kernel/ftrace.c:353`、`arch/riscv/kernel/ftrace.c:81`、`kernel/trace/ftrace.c`、`include/linux/ftrace.h`、`ftrace_find_unique_ops()`、`ftrace_rec_set_ops()`。
- **RISC-V 缺口**：根据 `FTRACE_FL_CALL_OPS_EN` 选择 unique ops 或 `ftrace_list_ops` 的状态机重复；真正的架构差异是如何把 ops 指针写入 call-site literal。
- **通用化方案**：ftrace core 提供 `ftrace_rec_get_call_ops()`；arm64/RISC-V 保留 `ftrace_rec_set_ops()` 和 literal patch。公共层不管理指令序列、trampoline 或 module PLT。
- **首版系列边界**：只抽 ops selector；迁移 arm64/RISC-V；nop/update wrapper 是否可共用另案证明。
- **阻塞与风险**：CFI、direct call、multi ops、module trampoline、未来 per-arch flags。
- **验证**：direct call、multi ops、module PLT、动态 enable/disable、CFI/LTO。
- **维护者方向**：ftrace core、arm64、RISC-V。
- **来源**：[arm64 direct calls 邻近系列](https://lore.kernel.org/linux-arm-kernel/20260609-arm64-ftrace-direct-calls-v1-2-4a46f266697f@linux.dev/)。

## 7. 页表与高风险通用化

<a id="gen-16"></a>
### GEN-16：显式 opt-in 的 no-immediate-flush young-bit helper

- **注册表归属**：`GEN:HC-22`；G3；P2；unclaimed；原始架构 arm64。
- **六维评分**：impact=3，generality=3，readiness=2，validation=3，hardware-independence=2，acceptance=2；总分 15。
- **基线校准**：x86/RISC-V 的 `ptep_clear_flush_young()` 都不立即 flush；linux-next RISC-V 页表文件虽有其他变化，该实现仍存在。邻近 MM 系列正在调整 young helper 的返回值/flush contract，但没有认领本候选。
- **精确路径与符号**：`arch/x86/mm/pgtable.c:475`、`arch/riscv/include/asm/pgtable.h:693`、`mm/pgtable-generic.c`、`ptep_clear_flush_young()`、`ptep_test_and_clear_young()`、`ptep_clear_young_no_flush()`。
- **RISC-V 缺口**：代码相同不代表 A-bit、TLB cache 和 stale accessed translation 的硬件契约相同。它不能成为无条件 generic default。
- **通用化方案**：定义显式 opt-in 的 no-immediate-flush primitive，并写清架构合同；generic caller 只有在该能力存在时才能延迟或批量 flush。注册表保留 G3/P2，强调先证明语义再抽 helper。
- **首版系列边界**：先提交契约文档和 selftest/KUnit；再让 x86/RISC-V 显式选择 helper；任何 caller batching 或 arm64 接入必须单独提交。
- **阻塞与风险**：硬件 A-bit 更新、TLB 缓存、THP/NUMA aging、并发清 young、架构内存模型。
- **验证**：page reclaim、idle page tracking、NUMA balancing、THP aging、TLB shootdown、虚拟化压力。
- **维护者方向**：MM/pgtable、x86、RISC-V；arm64 仅作为语义反例和评审者。
- **来源**：[young helper return-value v2 邻近系列](https://lore.kernel.org/linux-arm-kernel/24af5144b96103631594501f77d4525f2475c1be.1774075004.git.baolin.wang@linux.alibaba.com/)。

## 8. 去重归属与审查修正

### 8.1 与 Core/ABI 的唯一归属

以下三个候选在 Genericization 与 Core/ABI 原始报告中重复出现，统一注册表已经合并。最终文档应以本文件的 GEN 卡片为主，Core/ABI 文档只建立交叉引用，不再重复计数：

| 原始候选 | Core/ABI 重复项 | 唯一主 ID | 最终边界 |
|---|---|---|---|
| HC-02 | CAH-04 | GEN-02 | 只抽 `regs_query_register_offset()` 的 offset-only table walker |
| HC-03 | CAH-06 | GEN-03 | 复用 `include/linux/perf_regs.h` 已有 fallback，保留 x86-64 NMI override |
| HC-27 | CAH-05 | GEN-18 | 通用 matcher 数据化，架构保留 compat 判断与 prefix/alias 表 |

### 8.2 从 Genericization 移出的候选

- **HC-19 不计入 18 项**：已并入 `PLAT-02`。该系列不能只替换 `drivers/acpi/numa/srat.c` 的架构条件，还必须覆盖 `drivers/acpi/bus.c` 的 `_OSC` Generic Initiator capability、RISC-V enablement，以及 SRAT/HMAT initiator-only node 测试。
- **HC-28 不计入 18 项**：已并入 `PLAT-03`，由 Platform/ACPI 文档负责 arm64/RISC-V ACPI NUMA CPU 映射骨架。
- **HC-15 删除**：KVM PMI callback 是有意的架构边界，guest PMI/NMI 上下文不等价，一行重复不足以支撑 generic API。
- **HC-24 删除**：bitwise-compatible 页表层级转换不等于语义兼容；folded level、entry width、Svnapot/contpte 和 debug type checking 会因通用化而削弱类型安全。
- **HC-25 删除**：VDSO mremap 只有少量赋值重复，x86 还包含 landing/futex 更新，独立 helper 收益不足。
- **HC-13 降为附带清理**：kprobe nested state 仅 arm64/RISC-V 两字段同构，x86 还保存 flags，不建立完整公共状态机。
- **HC-16 降为工具链观察**：当前不能证明 RISC-V `preserve_most` 的编译器、模块 ABI、unwinder/objtool 合同，不能作为近期 enablement。
- **HC-23 降为局部清理**：`pudp_invalidate()` 虽相似，但 folded level 与硬件失效语义敏感，收益不足以建立复杂 generic API。
- **HC-18 已拆分**：只有机械 `ci_leaf_init()` 进入 GEN-13；`use_arch_cache_info()` 和 DT/PPTT/ISA 来源能力不进入主候选。

## 9. 推荐提交系列

### 第一批：低风险、可独立评审

1. **GEN-02 ptrace offset walker**：小型 API、三架构迁移、KUnit，避免 name lookup。
2. **GEN-03 perf fallback 复用**：删除简单实现，保留 x86-64 NMI override。
3. **GEN-06 generic PCI raw bus lookup**：先 arm64/RISC-V，不碰 x86 legacy。
4. **GEN-09 oldmem copy default**：generic default 加 arm64/RISC-V 迁移。
5. **GEN-13 cacheinfo leaf init**：纯机械重构，不混入 cache 来源策略。

这五个 P0 候选应分别成系列，不应为了减少邮件数量而合并跨子系统补丁。

### 第二批：default 与现有能力清理

1. **GEN-05 ACPI map/unmap default**：map、unmap 分为可独立回退的补丁。
2. **GEN-07 PCI topology opt-in helper**：不改变 asm-generic 默认。
3. **GEN-14 topology 架构条件清理**：先回放 dormant v4 review，再用已有 `GENERIC_ARCH_TOPOLOGY`。
4. **GEN-15 PCI ACPI host 条件清理**：先证明现有能力组合，避免新 Kconfig。
5. **GEN-10 crash/kdump**：必须基于 linux-next 的 `crash_prepare_headers()` 新边界，不能重发旧设计。

### 第三批：tracing 与共享策略

1. **GEN-17 uretprobe liveness**：只抽栈比较。
2. **GEN-18 syscall symbol matcher**：前缀/别名数据化，保留多 ABI 差异。
3. **GEN-11 ftrace ops selector**：公共选择状态，架构保留 literal patch。
4. **GEN-08 no-steal-acc**：先统一参数和只读策略，再讨论 static key。
5. **GEN-01 runtime-const iterator**：等待邻近 v5 稳定后推进，避免与 text-patch 活跃改动冲突。

### 第四批：需要证据先行

1. **GEN-12 LZO**：先建立跨平台性能与 trap 数据，再单独启用 RISC-V。
2. **GEN-16 young-bit no-flush**：先定义契约和测试，后抽 helper；不得把它做成默认页表行为。
3. **GEN-04 ptdump callback**：适合作为正在进行的 ptdump 系列附带清理，不建议单独发大型抽象系列。

## 10. 避免过度抽象

1. **只下沉已重复的控制流**：公共层处理遍历、默认调用和策略查询；指令编码、异常入口、页表位语义、固件 ID 解码留在架构侧。
2. **先证明现有 capability 不够**：GEN-14、GEN-15 优先复用现有 Kconfig；不得为了消除一个 `#ifdef` 自动增加新能力名。
3. **default 必须可显式 override**：ACPI early map、oldmem copy、crash hooks 都存在真实架构例外；不要用 weak symbol 隐藏链接或配置错误。
4. **重构与 RISC-V enablement 分开**：第一步保持 arm64/x86/RISC-V 当前可见配置和行为不变，第二步才增加新架构选择或快路径。
5. **不以代码相同推导硬件语义相同**：页表、TLB、NMI、cacheability、未对齐访问必须由架构合同和测试证明。
6. **不统一低价值的一行 wrapper**：HC-15、HC-25 已因收益不足删除；类似候选只有在能减少真实维护分叉时才值得进入 generic core。
7. **不把活跃邻近工作误标为精确候选已认领**：17 项仍是 unclaimed；GEN-14 因已有停滞提案严格标为 dormant。
8. **每个系列保留最小回退边界**：map/unmap、RAM walk/parser、helper/enablement 分拆，确保 review 能分别验证行为等价和新能力正确性。

## 11. 最低验证矩阵

- **构建**：arm64 defconfig/allmodconfig/64K page/KVM/ACPI；x86_64、i386、KVM、NUMA、ACPI；RISC-V rv64、rv32、KVM、ACPI；GCC 与 Clang。
- **tracing/perf**：kprobes、uprobes、ftrace direct/multi ops、perf user regs、native/compat syscall trace、LTO/CFI。
- **ACPI/PCI**：RSDP/XSDT/MADT/SRAT/PPTT/MCFG、多 segment ECAM、MSI/INTx、PCI hotplug、NUMA affinity。
- **crash/kdump**：`/proc/vmcore`、crash hotplug、memory hotplug、`crashkernel=`/`,high`/`,low`。
- **MM 高风险项**：page reclaim、idle page tracking、NUMA balancing、THP aging、TLB shootdown。
- **等价性检查**：objdump、section/relocation、sysfs/cache/topology 输出，以及迁移前后 debugfs/tracefs 文本逐项比较。

最终目标不是为 RISC-V 创建第三份 arm64/x86 代码，而是让新架构接入变成“选择已定义能力、复用默认实现、只实现最小硬件动作”。18 个候选中，五个 P0 项适合近期独立投稿；其余项目应严格遵守能力证明、override 和分阶段迁移边界。
