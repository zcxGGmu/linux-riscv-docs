# 寄存器访问 ABI（reg-access, Tier B）可移植性分析

> 输入：`kvm-riscv/data/by_category/B_reg-access.jsonl`（45 条系列）
> 判定依据：`_baseline_riscv.md` + 本地内核树 `/Users/zq/Desktop/patch-work/linux-riscv`
> 覆盖：ONE_REG / sys_reg / cpuid / get-reg-list / MSR-filter / vcpu-attribute

## 摘要

**四态计数（45 条）**
| 判定 | 计数 | 说明 |
|---|---|---|
| ALREADY | 1 | x86 CET 系列首次为 x86 引入 ONE_REG uAPI —— riscv/arm 早已具备 |
| PORTABLE | 1 | s390 系列前置的 KVM↔VFIO 模块引用解耦（通用 `virt/kvm/vfio.c`） |
| PATTERN | 11 | arm64 sysreg 净化框架族 + get-reg-list 测试纪律 + SME 扩展寄存器态模板 |
| N-A | 32 | 绝大多数是 x86 CPUID 琐碎（厂商位/cache 模型/QEMU 用户态）、NV、FGT、resctrl、FRED、CET-HW |

**核心结论**：本类是 45 条里「可移植密度最低」的类别之一。riscv KVM 的 ONE_REG 基础设施**已经成熟**——`vcpu_onereg.c`（1076 行，10 大类）+ `isa.c`（~90 个 ISA 扩展、含依赖门控 `kvm_riscv_isa_enable_allowed/disable_allowed` + host 能力门控 `__kvm_riscv_isa_check_host`）+ 共享的 `get-reg-list.c` 回归框架 + riscv 专属 blessed-list。x86 的 CPUID 工作几乎全是架构专有 ABI（riscv 无 CPUID 概念），arm64 的 sys_reg 工作大量是 NV/FGT 硬件陷阱或 RES0/RES1 逐位净化框架——riscv 的寄存器模型远比 arm64 简单，这类框架**思想可借鉴但价值不高**。真正有实操价值的是 **get-reg-list 测试纪律**和 **KVM↔VFIO 解耦**。

**Top 候选（按对 riscv 的实操价值排序）**
1. **get-reg-list blessed-list 纪律**（#25 SCTLR2_EL2、#26 ZCR_EL2 filter）— PATTERN，最高实操价值
2. **KVM↔VFIO 模块引用解耦**（#38 前置 patch 01-03，Paolo Bonzini 署名）— PORTABLE，通用底座自动生效
3. **x86 CET 引入 ONE_REG uAPI**（#24 patch 01）— ALREADY，反向印证 riscv 领先
4. **ID/feature 净化 + 迁移一致性**（#11 MTE_frac）— PATTERN，映射 riscv ISA-ext 暴露一致性
5. **feature-dependency / RESx 净化框架族**（#16、#30、#33）— PATTERN（框架思想，低优先）
6. **扩展寄存器态启用模板 SME**（#5、#45）— PATTERN，riscv Vector→未来矩阵扩展的同款模板
7. **「向用户态广告新 ISA 特性位」模式**（#27）— PATTERN（概念级）

---

## Top 可移植候选（深度）

### 1. get-reg-list blessed-list 回归纪律 — #25 / #26 — PATTERN
- **原补丁**：
  - `KVM: arm64: selftests: Add SCTLR2_EL2 to get-reg-list`（https://patchwork.kernel.org/project/kvm/patch/20251023-b4-kvm-arm64-get-reg-list-sctlr-el2-v1-1-088f88ff992a@kernel.org/）状态=new
  - `KVM: arm64: selftests: Filter ZCR_EL2 in get-reg-list`（https://patchwork.kernel.org/project/kvm/patch/20251024-kvm-arm64-get-reg-list-zcr-el2-v1-1-0cd0ff75e22f@kernel.org/）状态=new
- **可移植点**：get-reg-list 采用「blessed 列表 vs 内核实际列表」双向 diff 检测迁移回归——新增内核寄存器却漏加 blessed 列表会报 *missing register*（源 host 有、目的 host 无 = 迁移回归）。curl 确认 #25 commit msg 原文：「We recently added support for SCTLR2_EL2 to the kernel but did not add it to get-reg-list, resulting in it reporting the missing register」。#26 则示范用 `filter_reg()` 过滤条件性寄存器。这是一条**跨架构共享**的测试纪律，而非 arm 专有代码。
- **riscv 落点**：`tools/testing/selftests/kvm/riscv/get-reg-list.c`（已存在，58KB）——含 `base_regs[]`/`sbi_base_regs[]` blessed 数组、`filter_reg()`、`check_reject_set()`、`vcpu_configs[]`；共享通用框架 `tools/testing/selftests/kvm/get-reg-list.c`（`for_each_missing_reg`/`for_each_new_reg` 机制，本地已核对）。
- **判定**：PATTERN。riscv 每次向 `isa.c:kvm_isa_ext_arr[]` / `vcpu_onereg.c` 新增 ISA 扩展或 CSR，都**必须**同步更新 blessed 列表，否则触发同款 missing-register 失败；这两条补丁是 riscv 侧维护该测试的直接范式。

### 2. KVM↔VFIO 模块引用解耦 — #38（前置 patch 01-03）— PORTABLE
- **原补丁**：`KVM: s390: Introduce arm64 KVM - using symlinks`（https://patchwork.kernel.org/project/kvm/patch/20260428160527.1378085-18-seiden@linux.ibm.com/）状态=new
- **可移植点**：curl 核对该系列**前 3 条**（Paolo Bonzini / Alex Williamson 署名）是纯通用底座清理，与 s390/arm64 实验无关：
  - patch 01「VFIO: take reference to the KVM module」——改 `drivers/vfio/{device_cdev,group,vfio_main}.c`、`include/linux/vfio.h`、`virt/kvm/vfio.c`，用 `module_get/put` 显式持有 KVM 模块引用。
  - patch 02「remove symbol_get(kvm_get_kvm_safe) from vfio」——改 `virt/kvm/kvm_main.c`、`include/linux/kvm_host.h`、`include/linux/kvm_types.h`，移除 `symbol_get/put` 隐式耦合。
- **riscv 落点**：`virt/kvm/vfio.c` + `virt/kvm/kvm_main.c`（**架构无关**，riscv KVM 同样经此路径与 VFIO 集成，改动自动生效）。
- **判定**：PORTABLE（仅前置 3 条）。系列其余 patch 04-28（为 s390 host 提供 arm64 UAPI/sysreg）属实验性跨架构，riscv N-A。

### 3. x86 CET 首次引入 ONE_REG uAPI — #24（patch 01）— ALREADY
- **原补丁**：`Enable CET Virtualization`（https://patchwork.kernel.org/project/kvm/patch/20250909093953.202028-14-chao.gao@intel.com/）状态=new
- **可移植点/反向印证**：patch 01 标题「KVM: x86: Introduce KVM_{G,S}ET_ONE_REG uAPIs support」——x86 到 2025 年才把 `KVM_GET/SET_ONE_REG` 引入自身。riscv **自诞生即以 ONE_REG 为主寄存器 ABI**（`vcpu_onereg.c`，10 大类 + config/CSR/FP/Vector/ISA-ext/SBI-ext 全覆盖）。
- **riscv 落点**：`arch/riscv/kvm/vcpu_onereg.c` + `isa.c`（已实现）。
- **判定**：ALREADY（ONE_REG 基础设施）；CET 本体（`XSS`/影子栈/`MSR_IA32_U_CET`）依赖 x86 硬件 → N-A。价值在于确认 riscv 在通用寄存器 ABI 上**领先** x86，无需移植。

### 4. ID/feature 净化 + 迁移一致性 — #11 — PATTERN
- **原补丁**：`KVM: arm64: Don't claim MTE_ASYNC if not supported`（https://patchwork.kernel.org/project/kvm/patch/20250512114112.359087-2-ben.horgan@arm.com/）状态=new
- **可移植点**：curl 确认核心问题是「KVM 向 guest 暴露 *sanitised* ID 寄存器，却错误地把 `MTE_frac` 强制为 0，使 guest 误以为支持 MTE_ASYNC」。修复思路 = 正确净化 guest 可见 feature 字段 + patch 03 selftest「Confirm exposing MTE_frac does not break migration」验证不破坏迁移。
- **riscv 落点**：`arch/riscv/kvm/isa.c`（`__kvm_riscv_isa_check_host` 已做 host 能力门控、Smnpm→Ssnpm 映射等净化）+ `vcpu_onereg.c`（ISA-ext 暴露）+ `get-reg-list.c`（迁移一致性）。
- **判定**：PATTERN（低-中价值）。概念直接映射，但 riscv 是**按扩展粗粒度**开关，无 arm64 那种逐 ID 字段位净化的复杂度；主要提醒：新增 ISA-ext 暴露时须保证 host 门控 + 迁移一致。

### 5. feature-dependency / RESx 净化框架族 — #16 / #30 / #33 — PATTERN（框架思想）
- **原补丁**：
  - `KVM: arm64: Config driven dependencies for TCR2/SCTLR/MDCR`（https://patchwork.kernel.org/project/kvm/patch/20250714115503.3334242-2-maz@kernel.org/）
  - `KVM: arm64: VTCR_EL2 conversion to feature dependency framework`（https://patchwork.kernel.org/project/kvm/patch/20251210173024.561160-4-maz@kernel.org/）
  - `KVM: arm64: Generalise RESx handling`（https://patchwork.kernel.org/project/kvm/patch/20260202184329.2724080-10-maz@kernel.org/）
- **可移植点**：curl 确认 #33 是把每个 sysreg 的 RES0/RES1 保留位约束（如 `AS_RES1` 表达 `HCR_EL2.RW`）做成**声明式依赖框架**，随特性可用性驱动净化 reset 值与运行时写入。
- **riscv 落点**：`arch/riscv/kvm/isa.c`（当前用 switch-case 的 `enable_allowed/disable_allowed` 表达依赖，如 Sscofpmf 依赖 Ssaia、Svadu 依赖 `arch_has_hw_pte_young()`）+ `vcpu_onereg.c`（CSR 写入校验）。
- **判定**：PATTERN（低价值）。riscv 寄存器模型简单——ISA 扩展基本是独立 on/off，没有 arm64 那种成百 sysreg × 逐位 RES0/RES1 的净化负担。声明式依赖表**可让 isa.c 更整洁**，但非紧迫，收益有限。

### 6. 扩展寄存器态启用模板 SME — #5 / #45 — PATTERN
- **原补丁**：`KVM: arm64: Implement support for SME`（v4: https://patchwork.kernel.org/project/kvm/patch/20250214-kvm-arm64-sme-v4-16-d64a681adcc2@kernel.org/；v12: https://patchwork.kernel.org/project/kvm/patch/20260709-kvm-arm64-sme-v12-16-d0301d79ef58@kernel.org/）状态=new
- **可移植点**：为一类**新的大寄存器态**（矩阵/流式向量）实现：惰性 save/restore、feature enable 门控、通过 ONE_REG 暴露 ZA/ZT0/SVCR、纳入 get-reg-list。这套「新扩展态上车」流程是模板级的。
- **riscv 落点**：`arch/riscv/kvm/vcpu_vector.c` + `vcpu_fp.c`（惰性存取范式已有）+ `vcpu_onereg.c`（ISA-ext 暴露）——riscv 加 Vector 时已走同款流程，未来加矩阵类扩展（如 Zvfbf/未来 AME）可复用。
- **判定**：PATTERN。SME 本体是 arm 专有 ISA（N-A），但**启用范式**与 riscv 现有 Vector 支持同构，属可复用工程模板。

### 7. 「向用户态广告新 ISA 特性位」模式 — #27 — PATTERN（概念级）
- **原补丁**：`KVM: x86: Advertise new instruction CPUIDs for Intel Diamond Rapids`（https://patchwork.kernel.org/project/kvm/patch/20251120050720.931449-2-zhao1.liu@intel.com/）状态=new
- **可移植点**：向 userspace 广告新 ISA 特性（MOVRS/AMX/AVX10）以便为 guest 启用。x86 经 CPUID，riscv 经 `kvm_isa_ext_arr[]` + `KVM_RISCV_ISA_EXT_*`。
- **riscv 落点**：`arch/riscv/kvm/isa.c`（`kvm_isa_ext_arr[]`）+ `uapi/asm/kvm.h`（`KVM_RISCV_ISA_EXT_*` 枚举）。
- **判定**：PATTERN（概念级）。x86 diff 不可复用，但「新 ISA 扩展 → 加枚举 + 门控 → 经 ONE_REG 暴露给 userspace」是 riscv 的高频常规动作，本条是该模式的 x86 镜像。

---

## 全量判定表（45 条）

| # | 系列 | arch | 判定 | 可移植点(若有) | riscv落点(若有) | web_url |
|---|---|---|---|---|---|---|
| 1 | KVM: arm64: nv: Fix sysreg RESx-ication | arm | PATTERN(弱) | sysreg reset 值套用 RESx 净化的思想 | vcpu_onereg.c reset | https://patchwork.kernel.org/project/kvm/patch/20250112165029.1181056-3-maz@kernel.org/ |
| 2 | KVM: x86/cpuid: add type suffix to decimal const 48 | x86 | N-A | 编译告警修复，x86 CPUID 专有 | — | https://patchwork.kernel.org/project/kvm/patch/20250127013837.12983-1-haifeng.zhao@linux.intel.com/ |
| 3 | Add support for the Idle HLT intercept feature | x86 | N-A | SVM 硬件 intercept | — | https://patchwork.kernel.org/project/kvm/patch/20250128124812.7324-4-manali.shukla@amd.com/ |
| 4 | PMU partitioning driver support | arm | N-A | arm64 PMU 硬件分区(HPMN)；riscv 为 SBI-PMU 模型 | (pmu 类；vcpu_pmu.c 思想弱相关) | https://patchwork.kernel.org/project/kvm/patch/20250213180317.3205285-4-coltonlewis@google.com/ |
| 5 | KVM: arm64: SME in non-protected guests (v4) | arm | PATTERN | 新扩展寄存器态：惰性存取+ONE_REG暴露+get-reg-list | vcpu_vector.c/vcpu_fp.c/vcpu_onereg.c | https://patchwork.kernel.org/project/kvm/patch/20250214-kvm-arm64-sme-v4-16-d64a681adcc2@kernel.org/ |
| 6 | KVM: x86: Cleanup CPUID leaf 0x80000022 | x86 | N-A | x86 CPUID 专有 | — | https://patchwork.kernel.org/project/kvm/patch/20250304082314.472202-2-xiaoyao.li@intel.com/ |
| 7 | KVM: x86: zero-initialize on-stack CPUID unions | x86 | N-A | x86 CPUID 编码卫生 | — | https://patchwork.kernel.org/project/kvm/patch/20250315024102.2361628-1-seanjc@google.com/ |
| 8 | i386/cpu: Cache CPUID fixup, Intel cache model | x86 | N-A | QEMU 用户态 i386 | — | https://patchwork.kernel.org/project/kvm/patch/20250423114702.1529340-8-zhao1.liu@intel.com/ |
| 9 | Add support for the Bus Lock Threshold | x86 | N-A | SVM bus-lock 退出硬件 | — | https://patchwork.kernel.org/project/kvm/patch/20250502050346.14274-6-manali.shukla@amd.com/ |
| 10 | KVM: arm64: Revamp Fine Grained Trap handling | arm | N-A | arm64 FGT 硬件陷阱基础设施(净化位为 PATTERN 邻接) | (思想近 isa.c) | https://patchwork.kernel.org/project/kvm/patch/20250506164348.346001-14-maz@kernel.org/ |
| 11 | KVM: arm64: Don't claim MTE_ASYNC if not supported | arm | PATTERN | ID/feature 字段净化 + 迁移一致性 selftest | isa.c/vcpu_onereg.c/get-reg-list.c | https://patchwork.kernel.org/project/kvm/patch/20250512114112.359087-2-ben.horgan@arm.com/ |
| 12 | KVM: arm64: Recursive NV support | arm | N-A | 嵌套虚拟化，riscv 无 | — | https://patchwork.kernel.org/project/kvm/patch/20250514103501.2225951-2-maz@kernel.org/ |
| 13 | x86: Add CPUID properties (kvm-unit-tests) | x86 | N-A | x86 CPUID property 测试框架 | — | https://patchwork.kernel.org/project/kvm/patch/20250610195415.115404-15-seanjc@google.com/ |
| 14 | x86: NMI-source reporting with FRED | x86 | N-A | x86 FRED 硬件 | — | https://patchwork.kernel.org/project/kvm/patch/20250612214849.3950094-6-sohil.mehta@intel.com/ |
| 15 | i386/cpu: Unify cache model in X86CPUState | x86 | N-A | QEMU 用户态 | — | https://patchwork.kernel.org/project/kvm/patch/20250711102143.1622339-6-zhao1.liu@intel.com/ |
| 16 | KVM: arm64: Config-driven deps TCR2/SCTLR/MDCR | arm | PATTERN | 声明式 feature-dependency 净化框架 | isa.c(enable/disable_allowed)/vcpu_onereg.c | https://patchwork.kernel.org/project/kvm/patch/20250714115503.3334242-2-maz@kernel.org/ |
| 17 | x86: Disentangle processor.h from CPUID headers | x86 | N-A | x86 头文件清理 | — | https://patchwork.kernel.org/project/kvm/patch/20250724193706.35896-4-darwi@linutronix.de/ |
| 18 | KVM: x86: expose CPUID 0xC000_0000 Zhaoxin | x86 | N-A | x86 厂商 CPUID | — | https://patchwork.kernel.org/project/kvm/patch/20250811013558.332940-1-ewanhai-oc@zhaoxin.com/ |
| 19 | Support "generic" CPUID timing leaf (v1) | x86 | N-A | 经 x86 CPUID 传 TSC 频率；riscv 用 DT/SBI | — | https://patchwork.kernel.org/project/kvm/patch/20250814120237.2469583-2-dwmw2@infradead.org/ |
| 20 | Support "generic" CPUID timing leaf (v2) | x86 | N-A | 同上 | — | https://patchwork.kernel.org/project/kvm/patch/20250816101308.2594298-2-dwmw2@infradead.org/ |
| 21 | KVM: arm64: Live system register access fixes | arm | PATTERN(弱) | on-CPU vs in-memory 寄存器访问器正确性 | vcpu.c/vcpu_onereg.c 访问器 | https://patchwork.kernel.org/project/kvm/patch/20250817121926.217900-4-maz@kernel.org/ |
| 22 | KVM: x86: allow CPUID 0xC000_0000 Zhaoxin (v2) | x86 | N-A | x86 厂商 CPUID | — | https://patchwork.kernel.org/project/kvm/patch/20250818083034.93935-1-ewanhai-oc@zhaoxin.com/ |
| 23 | x86/cpu/topology: APIC ID parsing AMD/Hygon | x86 | N-A | x86 拓扑/APIC ID | — | https://patchwork.kernel.org/project/kvm/patch/20250901170418.4314-4-kprateek.nayak@amd.com/ |
| 24 | Enable CET Virtualization | x86 | ALREADY | patch01 首为 x86 引入 KVM_{G,S}ET_ONE_REG(riscv 早有)；CET 本体 N-A | vcpu_onereg.c/isa.c(已有) | https://patchwork.kernel.org/project/kvm/patch/20250909093953.202028-14-chao.gao@intel.com/ |
| 25 | KVM: arm64: selftests: Add SCTLR2_EL2 to get-reg-list | arm | PATTERN | blessed-list 回归纪律：新增寄存器须同步 | tools/.../riscv/get-reg-list.c | https://patchwork.kernel.org/project/kvm/patch/20251023-b4-kvm-arm64-get-reg-list-sctlr-el2-v1-1-088f88ff992a@kernel.org/ |
| 26 | KVM: arm64: selftests: Filter ZCR_EL2 in get-reg-list | arm | PATTERN | filter_reg() 过滤条件性寄存器 | riscv/get-reg-list.c filter_reg() | https://patchwork.kernel.org/project/kvm/patch/20251024-kvm-arm64-get-reg-list-zcr-el2-v1-1-0cd0ff75e22f@kernel.org/ |
| 27 | KVM: x86: Advertise new CPUIDs Diamond Rapids | x86 | PATTERN(概念) | 向 userspace 广告新 ISA 特性位 | isa.c(kvm_isa_ext_arr[])/uapi kvm.h | https://patchwork.kernel.org/project/kvm/patch/20251120050720.931449-2-zhao1.liu@intel.com/ |
| 28 | i386: CPUID 0x80000026 and Bus Lock Detect | x86 | N-A | QEMU 用户态 i386 | — | https://patchwork.kernel.org/project/kvm/patch/20251121083452.429261-2-shivansh.dhiman@amd.com/ |
| 29 | KVM: x86: runtime updates during KVM_SET_CPUID2 | x86 | N-A | x86 CPUID 运行时重算，riscv ISA-ext 静态 | — | https://patchwork.kernel.org/project/kvm/patch/20251202015049.1167490-2-seanjc@google.com/ |
| 30 | KVM: arm64: VTCR_EL2 → feature dependency framework | arm | PATTERN | 声明式 feature-dependency 净化框架 | isa.c/vcpu_onereg.c | https://patchwork.kernel.org/project/kvm/patch/20251210173024.561160-4-maz@kernel.org/ |
| 31 | i386: Support CET for KVM | x86 | N-A | QEMU 用户态 CET | — | https://patchwork.kernel.org/project/kvm/patch/20251211060801.3600039-13-zhao1.liu@intel.com/ |
| 32 | KVM: x86: Disallow setting CPUID/MSRs if L2 active | x86 | N-A | 嵌套(L2)守卫，riscv 无 nested | — | https://patchwork.kernel.org/project/kvm/patch/20251230205641.4092235-1-seanjc@google.com/ |
| 33 | KVM: arm64: Generalise RESx handling | arm | PATTERN | 声明式 RES0/RES1 逐位约束框架 | vcpu_onereg.c 写入校验/isa.c | https://patchwork.kernel.org/project/kvm/patch/20260202184329.2724080-10-maz@kernel.org/ |
| 34 | KVM: x86: synthesize TSA CPUID via SCATTERED_F() | x86 | N-A | x86 CPUID 合成宏 | — | https://patchwork.kernel.org/project/kvm/patch/20260208164233.30405-1-clopez@suse.de/ |
| 35 | KVM: x86: synthesize CPUID only if CPU cap set (v2) | x86 | N-A | 「有 host 能力才广告」；riscv isa.c 已经门控 | (概念已有:__kvm_riscv_isa_check_host) | https://patchwork.kernel.org/project/kvm/patch/20260209153108.70667-2-clopez@suse.de/ |
| 36 | KVM: x86: KVM-only CPUID.0xC0000001:EDX bits | x86 | N-A | x86 厂商 CPUID | — | https://patchwork.kernel.org/project/kvm/patch/20260305110519.308860-1-ewanhai-oc@zhaoxin.com/ |
| 37 | fs,x86/resctrl: kernel-mode (PLZA) support | x86 | N-A | resctrl 子系统(非 KVM)+x86 硬件 | — | https://patchwork.kernel.org/project/kvm/patch/6cc46ecf2a9ba759cd4de12bed3e9b898468d976.1773347820.git.babu.moger@amd.com/ |
| 38 | KVM: s390: Introduce arm64 KVM - using symlinks | arm | PORTABLE(前3条) | patch01-03 通用 KVM↔VFIO 模块引用解耦(Paolo)；余 N-A | virt/kvm/vfio.c + virt/kvm/kvm_main.c | https://patchwork.kernel.org/project/kvm/patch/20260428160527.1378085-18-seiden@linux.ibm.com/ |
| 39 | KVM: x86: Virtualize AMD CPUID faulting | x86 | N-A | CPUID faulting 硬件，riscv 无 CPUID | — | https://patchwork.kernel.org/project/kvm/patch/20260508170714.489136-3-jmattson@google.com/ |
| 40 | KVM: arm64 on s390 System Register Handling | arm | N-A | 实验性跨架构；arm 内部 feature-helper 泛化重构 | — | https://patchwork.kernel.org/project/kvm/patch/20260529155601.2927240-19-seiden@linux.ibm.com/ |
| 41 | KVM: x86: Fix emulated CPUID wrong sub-leaf | x86 | N-A | x86 CPUID bugfix | — | https://patchwork.kernel.org/project/kvm/patch/20260609075748.612704-1-binbin.wu@linux.intel.com/ |
| 42 | KVM: x86: Expose Zhaoxin CPUID crypto features | x86 | N-A | x86 厂商 CPUID 加密位 | — | https://patchwork.kernel.org/project/kvm/patch/20260610023512.3690734-2-ewanhai-oc@zhaoxin.com/ |
| 43 | KVM: arm64: Add support for FEAT_NV2p1 and FEAT_NV3 | arm | N-A | 嵌套虚拟化，riscv 无 | — | https://patchwork.kernel.org/project/kvm/patch/20260702160248.1377250-13-maz@kernel.org/ |
| 44 | target/i386: Fix Hygon vendor-specific CPU behavior | x86 | N-A | QEMU 用户态 i386 Hygon | — | https://patchwork.kernel.org/project/kvm/patch/20260706055530.1752094-2-zhang_wei@open-hieco.net/ |
| 45 | KVM: arm64: Implement support for SME (v12) | arm | PATTERN | 同#5：扩展寄存器态启用模板 | vcpu_vector.c/vcpu_fp.c/vcpu_onereg.c | https://patchwork.kernel.org/project/kvm/patch/20260709-kvm-arm64-sme-v12-16-d0301d79ef58@kernel.org/ |

---

## 附：riscv 基线核对结论（本地源码验证）

- **ONE_REG 成熟**：`arch/riscv/kvm/vcpu_onereg.c`（1076 行）、`isa.c`（253 行，`kvm_isa_ext_arr[]` 约 90 项 + `kvm_riscv_isa_enable_allowed/disable_allowed` + `__kvm_riscv_isa_check_host` host 门控）。→ x86/arm 的 ONE_REG-uAPI 引入类补丁对 riscv 判 ALREADY。
- **get-reg-list 已有**：`tools/testing/selftests/kvm/riscv/get-reg-list.c`（58KB，`base_regs[]`/`sbi_base_regs[]`/`filter_reg()`/`check_reject_set()`/`vcpu_configs[]`）+ 共享通用框架 `tools/testing/selftests/kvm/get-reg-list.c`（`for_each_missing_reg`/`for_each_new_reg` blessed-list 双向 diff）。→ arm64 get-reg-list 补丁判 PATTERN（同款纪律，寄存器名不同）。
- **无 CPUID / 无 MSR-filter 概念**：riscv 特性发现走 ISA-ext 枚举 + SBI，无 CPUID leaf、无 MSR，也无 MSR-filter 对应物。→ 绝大多数 x86 CPUID / MSR 系列判 N-A。
- **寄存器净化模型更简单**：riscv 无 arm64 那种成百 sysreg × 逐位 RES0/RES1；依赖关系少且用 switch-case 表达即可。→ arm64 RESx/feature-dependency 框架判 PATTERN 但价值不高。
