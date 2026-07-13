# docs-tooling 可移植性分析（linux-arm-kernel → RISC-V）

> 输入：`data/by_category/docs-tooling.jsonl`（208 条系列，全部 tier=A / kind=signal）。
> 基线树：Linux v7.2.0-rc3（`/Users/zq/Desktop/patch-work/linux-riscv`），所有 riscv 落点均已 Grep/ls 核对存在。
> 类别性质：Documentation / selftests / kselftest / tools / kunit / lib——**Tier A 通用层**。判定纪律：通用测试框架/kselftest 基础设施/通用文档改进 → PORTABLE；arm64 专属文档/selftest → N-A；跨架构 selftest/lib 改进 → PORTABLE。

## 摘要

- **系列总数：208**
- **四态计数**：ALREADY 0 ｜ **PORTABLE 39** ｜ **PATTERN 2** ｜ N-A 167
- **N-A 构成**（同质，合并成组）：MAINTAINERS/mailmap 人事变更 51、通用/SoC 设备驱动 48、KVM-arm64 专属 selftest/特性 25、arm64 专属 selftest 15、iommufd HW 虚拟化 8、resctrl/MPAM(ARM) 8、arm64 专属文档 5、arm64 ISA/sysreg 3、arm64 tools 头文件同步 3、KVM-x86 1。
- 本类**绝大多数无 riscv 架构缺口价值**：人事变更、arm 设备驱动、arm64 硬件专属测试占 155/208。真正有价值的是**通用 lib/crypto、跨架构测试框架、KUnit、文档构建工具**这几簇。

### 本类 Top 候选（按价值排序）

1. **Add support for suppressing warning backtraces**（PORTABLE，KUnit 基础设施）— `lib/kunit/bug.c`+`include/kunit/bug.h`，riscv KUnit 直接受益。
2. **lib/crypto 算法库批次**（SHA-3 / BLAKE2b / POLYVAL / NH-Adiantum / AES-CMAC / Curve25519，6 条，PORTABLE）— 纯 `lib/crypto/*.c`，全架构共享；riscv 可后续加 Zvk* 向量加速。
3. **raid6: 用户态测试改 kunit + 重构**（PORTABLE）— `lib/raid/raid6/`（含 `riscv/recov_rvv.c`）+ `tests/raid6_kunit.c`，diff 显式含 riscv 路径。
4. **KVM selftests 框架/类型清理**（runner、kernel-style types、binary stats 等 8 条，PORTABLE）— `tools/testing/selftests/kvm/`，`riscv/` 子目录已存在，直接惠及 riscv KVM 测试。
5. **exec: Remove AT_VECTOR_SIZE_ARCH from UAPI**（PATTERN）— treewide UAPI 清理；riscv `auxvec.h` 亦定义该宏，需同步。
6. **文档构建工具**（automarkup ABI 符号、coccinelle field_modify，PORTABLE）— `Documentation/sphinx/automarkup.py`、`scripts/coccinelle/`，全树受益。
7. **arm64: Use generic TIF bits**（PATTERN）— riscv `thread_info.h` 可同样采用 asm-generic TIF 编号。

## Top 可移植候选（深度）

### 1. Add support for suppressing warning backtraces —— PORTABLE
- **原补丁**：`Add support for suppressing warning backtraces`（arm，14 patches，state=new）
  https://patchwork.kernel.org/project/linux-arm-kernel/patch/20250313114329.284104-3-acarmina@redhat.com/
- **可移植点**：为 KUnit 增加「预期告警 backtrace 抑制/计数」通用机制，使测试触发 `WARN*` 时不污染日志且可断言。curl 核对补丁 02/14 改动 `include/kunit/bug.h` + `lib/kunit/bug.c`——纯通用测试框架代码，无 arch 依赖。
- **riscv 落点**：无需 riscv 侧改动即自动生效；`include/kunit/bug.c`、`lib/kunit/bug.c` 已存在于树中（`__WARN_FLAGS`/kunit hooks 走 `include/asm-generic/bug.h`，riscv 复用 asm-generic bug）。
- **判定**：**PORTABLE** —— 通用 KUnit 基础设施，riscv 的 KUnit 测试直接受益。

### 2. lib/crypto 算法库批次（SHA-3 / BLAKE2b / POLYVAL / NH / AES-CMAC / Curve25519）—— PORTABLE
- **原补丁**：`SHA-3 library`（arm，15 patches）
  https://patchwork.kernel.org/project/linux-arm-kernel/patch/20251026055032.1413733-4-ebiggers@kernel.org/ ；同簇另 5 条见全量表。
- **可移植点**：curl 核对 `lib/crypto: sha3: Add SHA-3 support` 仅动 `lib/crypto/sha3.c`、`include/crypto/sha3.h`、`lib/crypto/{Kconfig,Makefile}`、`Documentation/crypto/sha3.rst`——纯架构无关 C 实现。
- **riscv 落点**：`lib/crypto/`（`sha3.c`、`blake2b.c`、`curve25519.c` 等已在树中，全架构共享）。riscv 已有 `lib/crypto/riscv/`（aes/sha256/sha512/chacha/sm3 的 Zvk* 向量加速），可循同一框架为新算法补向量后端——但**通用 C 实现本身对 riscv 立即可用**。
- **判定**：**PORTABLE** —— `lib/crypto` 通用层，无 arch 门槛。

### 3. raid6: 用户态测试改 kunit + 内部化重构 —— PORTABLE
- **原补丁**：`[01/18] raid6: turn the userspace test harness into a kunit test`（generic，18 patches）
  https://patchwork.kernel.org/project/linux-arm-kernel/patch/20260518051804.462141-10-hch@lst.de/
- **可移植点**：将 raid6 用户态测试转为 KUnit，并重构 `lib/raid/raid6/` 目录布局。curl 核对补丁 09/18 diff **显式包含 `lib/raid/raid6/riscv/recov_rvv.c`、`lib/raid/raid6/riscv/rvv.h`**——即 riscv RVV 后端也在此重构范围内。
- **riscv 落点**：`lib/raid/raid6/riscv/`（已存在，riscv 已有 RVV raid6 加速）+ `lib/raid/raid6/tests/raid6_kunit.c`（已存在）。
- **判定**：**PORTABLE** —— 通用 lib/ 重构 + KUnit，且改动直接覆盖 riscv 现有代码。

### 4. KVM selftests 框架/类型清理（8 条）—— PORTABLE
- **原补丁**（代表）：`KVM: selftests: Use kernel-style integer and g[vp]a_t types`（generic，17 patches）
  https://patchwork.kernel.org/project/linux-arm-kernel/patch/20260420212004.3938325-11-seanjc@google.com/ ；`Add KVM Selftests runner`、`KVM: selftests: Binary stats fixes and infra updates`、`Convert to kernel-style types`、`Drop vm_dead pivot on vm_bugged`、`Add eventfd+VFIO IRQ test` 等见全量表。
- **可移植点**：selftest 公共库（`tools/testing/selftests/kvm/lib/`、`include/`）的类型规范化、runner、二进制统计基础设施——跨架构，riscv KVM selftest 复用同一 harness。
- **riscv 落点**：`tools/testing/selftests/kvm/`（`riscv/` 子目录已存在：`arch_timer.c`/`ebreak_test.c`/`get-reg-list.c`/`sbi_pmu_test.c`）；公共库改动自动惠及 riscv。
- **判定**：**PORTABLE** —— 跨架构 KVM selftest 框架层。（注：涉及 GIC/GICR/vLPI/arm64 sysreg 的 KVM selftest 系列已归 N-A。）

### 5. exec: Remove AT_VECTOR_SIZE_ARCH from UAPI —— PATTERN
- **原补丁**：`exec: Remove AT_VECTOR_SIZE_ARCH from UAPI`（arm，15 patches）
  https://patchwork.kernel.org/project/linux-arm-kernel/patch/20260302-at-vector-size-arch-v1-4-a11f03ba2ca8@linutronix.de/
- **可移植点**：treewide 清理——各架构删除自定义 `asm/auxvec.h` 里的 `AT_VECTOR_SIZE_ARCH`，收敛到通用定义。curl 核对补丁 04/15 即 `ARM: drop custom asm/auxvec.h`（逐架构删除）。
- **riscv 落点**：`arch/riscv/include/uapi/asm/auxvec.h:37`（`#define AT_VECTOR_SIZE_ARCH 10`，已核对存在）——riscv 需同样的删除/收敛改动。
- **判定**：**PATTERN** —— 通用机制、treewide，riscv 侧需一处对称清理。

### 6. 文档构建/静态分析工具（automarkup、coccinelle）—— PORTABLE
- **原补丁**：`Extend automarkup support for ABI symbols`（generic）
  https://patchwork.kernel.org/project/linux-arm-kernel/patch/0a989eea90e5d03a36a07760f8b505e074e85c03.1739254867.git.mchehab+huawei@kernel.org/ ；`[v7] coccinelle: misc: Add field_modify script`
  https://patchwork.kernel.org/project/linux-arm-kernel/patch/20250701-field_modify-v7-1-eacf13f215b4@quicinc.com/
- **可移植点**：Sphinx automarkup 交叉引用增强 / coccinelle 语义补丁脚本——文档与代码质量工具，全树通用。
- **riscv 落点**：`Documentation/sphinx/automarkup.py`（已核对存在）、`scripts/coccinelle/misc/`（已核对存在）；无 arch 依赖，riscv 文档/代码自动受益。
- **判定**：**PORTABLE** —— 通用 docs/tooling。

### 7. arm64: Use generic TIF bits for common thread flags —— PATTERN
- **原补丁**：`arm64: Use generic TIF bits for common thread flags`（arm，4 patches）
  https://patchwork.kernel.org/project/linux-arm-kernel/patch/20260320104222.1381274-5-ruanjinjie@huawei.com/
- **可移植点**：将公共线程标志（`TIF_NOTIFY_RESUME`/`TIF_SIGPENDING` 等）迁移到 asm-generic 统一编号，减少各 arch 重复定义。
- **riscv 落点**：`arch/riscv/include/asm/thread_info.h`（已核对：目前 riscv 自行定义 `TIF_32BIT=16`、`TIF_RISCV_V_DEFER_RESTORE=17` 等），可循同一模式采用 generic TIF 编号。
- **判定**：**PATTERN** —— arch 专属实现，机制通用，riscv 侧可对称清理。

## 全量判定表

### PORTABLE / PATTERN（逐条，41 条）

| 系列 | arch | 判定 | 可移植点 | riscv 落点 | web_url |
|---|---|---|---|---|---|
| exec: Remove AT_VECTOR_SIZE_ARCH from UAPI | arm | PATTERN | treewide UAPI 清理，riscv 亦定义该宏需同步移除 | arch/riscv/include/uapi/asm/auxvec.h (AT_VECTOR_SIZE_ARCH=10) | https://patchwork.kernel.org/project/linux-arm-kernel/patch/20260302-at-vector-size-arch-v1-4-a11f03ba2ca8@linutronix.de/ |
| arm64: Use generic TIF bits for common thread flags | arm | PATTERN | 采用 asm-generic TIF 编号，riscv 可同样清理 | arch/riscv/include/asm/thread_info.h | https://patchwork.kernel.org/project/linux-arm-kernel/patch/20260320104222.1381274-5-ruanjinjie@huawei.com/ |
| SHA-3 library | arm | PORTABLE | 通用 lib/crypto C 实现，全架构共享 | lib/crypto/sha3.c (+ 可选 arch/riscv/crypto Zvk*) | https://patchwork.kernel.org/project/linux-arm-kernel/patch/20251026055032.1413733-4-ebiggers@kernel.org/ |
| BLAKE2b library API | generic | PORTABLE | 通用 lib/crypto C 实现 | lib/crypto/blake2b.c | https://patchwork.kernel.org/project/linux-arm-kernel/patch/20251018043106.375964-11-ebiggers@kernel.org/ |
| POLYVAL library | arm | PORTABLE | 通用 lib/crypto C 实现 | lib/crypto/ | https://patchwork.kernel.org/project/linux-arm-kernel/patch/20251109234726.638437-9-ebiggers@kernel.org/ |
| NH library and Adiantum cleanup | arm | PORTABLE | 通用 lib/crypto C 实现 | lib/crypto/nh.c | https://patchwork.kernel.org/project/linux-arm-kernel/patch/20251211011846.8179-2-ebiggers@kernel.org/ |
| AES-CMAC library | arm | PORTABLE | 通用 lib/crypto C 实现 | lib/crypto/ | https://patchwork.kernel.org/project/linux-arm-kernel/patch/20260218213501.136844-14-ebiggers@kernel.org/ |
| Curve25519 cleanup | other | PORTABLE | 通用 lib/crypto C 实现 | lib/crypto/curve25519.c | https://patchwork.kernel.org/project/linux-arm-kernel/patch/20250906213523.84915-9-ebiggers@kernel.org/ |
| Add support for suppressing warning backtraces | arm | PORTABLE | 通用 KUnit 测试基础设施 | lib/kunit/bug.c, include/kunit/bug.h | https://patchwork.kernel.org/project/linux-arm-kernel/patch/20250313114329.284104-3-acarmina@redhat.com/ |
| [01/18] raid6: turn the userspace test harness into a kunit test | generic | PORTABLE | 通用 lib 重构 + KUnit（diff 含 riscv 路径） | lib/raid/raid6/riscv/, lib/raid/raid6/tests/raid6_kunit.c | https://patchwork.kernel.org/project/linux-arm-kernel/patch/20260518051804.462141-10-hch@lst.de/ |
| Add KVM Selftests runner | generic | PORTABLE | 跨架构 KVM selftest 框架 | tools/testing/selftests/kvm/ (riscv/ 已存在) | https://patchwork.kernel.org/project/linux-arm-kernel/patch/20250606235619.1841595-2-vipinsh@google.com/ |
| Add KVM selftest runner | generic | PORTABLE | 跨架构 KVM selftest 框架 | tools/testing/selftests/kvm/ | https://patchwork.kernel.org/project/linux-arm-kernel/patch/20250222005943.3348627-3-vipinsh@google.com/ |
| KVM: selftests: Use kernel-style integer and g[vp]a_t types | generic | PORTABLE | selftest 公共库类型规范化 | tools/testing/selftests/kvm/lib/, include/ | https://patchwork.kernel.org/project/linux-arm-kernel/patch/20260420212004.3938325-11-seanjc@google.com/ |
| KVM: selftests: Convert to kernel-style types | generic | PORTABLE | selftest 公共库类型规范化 | tools/testing/selftests/kvm/ | https://patchwork.kernel.org/project/linux-arm-kernel/patch/20250501183304.2433192-11-dmatlack@google.com/ |
| KVM: selftests: Binary stats fixes and infra updates | generic | PORTABLE | selftest 二进制统计基础设施 | tools/testing/selftests/kvm/ | https://patchwork.kernel.org/project/linux-arm-kernel/patch/20250111005049.1247555-7-seanjc@google.com/ |
| KVM: selftests: Add eventfd+VFIO IRQ test | generic | PORTABLE | 通用 eventfd/VFIO irqfd 测试 | tools/testing/selftests/kvm/ | https://patchwork.kernel.org/project/linux-arm-kernel/patch/20260626213534.3866178-4-seanjc@google.com/ |
| KVM: selftests: Fix a couple "prio" signedness bugs | generic | PORTABLE | selftest 公共库修复 | tools/testing/selftests/kvm/ | https://patchwork.kernel.org/project/linux-arm-kernel/patch/ca579322-dc9d-4300-bd74-7e9240e930c7@stanley.mountain/ |
| KVM: Drop vm_dead, pivot on vm_bugged for -EIO | generic | PORTABLE | 通用 KVM core (virt/kvm/) | virt/kvm/ (arch 无关) | https://patchwork.kernel.org/project/linux-arm-kernel/patch/20250729193341.621487-6-seanjc@google.com/ |
| KVM: Add a kvm_run flag to signal need for completion | other | PORTABLE | 通用 KVM core / uAPI | include/uapi/linux/kvm.h, virt/kvm/ | https://patchwork.kernel.org/project/linux-arm-kernel/patch/20250111012450.1262638-2-seanjc@google.com/ |
| Documentation: KVM: Document guest-visible compatibility expectations | generic | PORTABLE | 通用 KVM 文档 | Documentation/virt/kvm/ | https://patchwork.kernel.org/project/linux-arm-kernel/patch/6856b269d2af706eae397e0cf9c1231f89d9a932.camel@infradead.org/ |
| Extend automarkup support for ABI symbols | generic | PORTABLE | 通用文档构建工具 | Documentation/sphinx/automarkup.py | https://patchwork.kernel.org/project/linux-arm-kernel/patch/0a989eea90e5d03a36a07760f8b505e074e85c03.1739254867.git.mchehab+huawei@kernel.org/ |
| [v7] coccinelle: misc: Add field_modify script | generic | PORTABLE | 通用静态分析脚本 | scripts/coccinelle/misc/ | https://patchwork.kernel.org/project/linux-arm-kernel/patch/20250701-field_modify-v7-1-eacf13f215b4@quicinc.com/ |
| tools/nolibc: reduce __nolibc_enosys() fallbacks | arm | PORTABLE | 通用 nolibc，riscv 已支持 | tools/include/nolibc/ (arch-riscv.h 已存在) | https://patchwork.kernel.org/project/linux-arm-kernel/patch/20250821-nolibc-enosys-v1-7-4b63f2caaa89@weissschuh.net/ |
| [RESEND] selftests/pidfd: align stack to fix SP alignment exception | generic | PORTABLE | 通用 pidfd selftest | tools/testing/selftests/pidfd/ | https://patchwork.kernel.org/project/linux-arm-kernel/patch/20250616050648.58716-1-xueshuai@linux.alibaba.com/ |
| [01/19] btrfs: require at least 4 devices for RAID 6 | generic | PORTABLE | 通用文件系统修复 | fs/btrfs/ (arch 无关) | https://patchwork.kernel.org/project/linux-arm-kernel/patch/20260512052230.2947683-10-hch@lst.de/ |
| [linus:master,crypto] UBSAN overflow in chacha20poly1305-selftest.c | generic | PORTABLE | 通用 lib/crypto selftest 修复 | lib/crypto/chacha20poly1305-selftest.c | https://patchwork.kernel.org/project/linux-arm-kernel/patch/202505281024.f42beaa7-lkp@intel.com/ |
| Fix spelling typo in tools/perf | arm | PORTABLE | 通用 tools/perf 修复 | tools/perf/ | https://patchwork.kernel.org/project/linux-arm-kernel/patch/20251103014633.1213-2-chuguangqing@inspur.com/ |
| [1/1] tools: use basename to identify file in gen-mach-types | generic | PORTABLE | 通用 tools 脚本修复 | tools/ | https://patchwork.kernel.org/project/linux-arm-kernel/patch/20250826142518.2583999-1-alexander.stein@ew.tq-group.com/ |
| tools: Fix typo error in json file | generic | PORTABLE | 通用 tools json 修复 | tools/ | https://patchwork.kernel.org/project/linux-arm-kernel/patch/20251031031729.2304-1-chuguangqing@inspur.com/ |
| Documentation: treewide: Replace marc.info links with lore | generic | PORTABLE | 通用文档链接修复 | Documentation/ (treewide) | https://patchwork.kernel.org/project/linux-arm-kernel/patch/20251031043358.23709-1-bagasdotme@gmail.com/ |
| [v2] Documentation: Fix typos and grammatical errors | generic | PORTABLE | 通用文档修复 | Documentation/ | https://patchwork.kernel.org/project/linux-arm-kernel/patch/20260112091659.12316-1-officialnaumansabir@gmail.com/ |
| v2 Documentation: arch: fix brackets | generic | PORTABLE | 通用文档修复 | Documentation/arch/ | https://patchwork.kernel.org/project/linux-arm-kernel/patch/20260612095432.177759-2-manuelebner@mailbox.org/ |
| Documentation: parport-lowlevel: Fix curly bracket | generic | PORTABLE | 通用文档修复 | Documentation/ | https://patchwork.kernel.org/project/linux-arm-kernel/patch/20260627092359.30044-3-manuelebner@mailbox.org/ |
| Documentation: parport-lowlevel: Separate function listing code blocks | generic | PORTABLE | 通用文档修复 | Documentation/ | https://patchwork.kernel.org/project/linux-arm-kernel/patch/20251105124947.45048-1-bagasdotme@gmail.com/ |
| Documentation: ABI: sysfs-class-reboot-mode: fix doc warnings | generic | PORTABLE | 通用 ABI 文档修复 | Documentation/ABI/ | https://patchwork.kernel.org/project/linux-arm-kernel/patch/20260426232705.422938-1-rdunlap@infradead.org/ |
| [1/2] Documentation/process: maintainer-soc: Trim from trivial ask-DT | generic | PORTABLE | 通用流程文档 | Documentation/process/ | https://patchwork.kernel.org/project/linux-arm-kernel/patch/20260413074401.27282-3-krzysztof.kozlowski@oss.qualcomm.com/ |
| [net-next] Documentation: networking: devlink: stmmac: fix typo in phc_coarse_adj | generic | PORTABLE | 通用网络文档修复 | Documentation/networking/ | https://patchwork.kernel.org/project/linux-arm-kernel/patch/20260512133214.1773502-1-avinash.duduskar@gmail.com/ |
| [net] docs: networking: timestamping: improve stacked PHC sentence | generic | PORTABLE | 通用网络文档修复 | Documentation/networking/ | https://patchwork.kernel.org/project/linux-arm-kernel/patch/20250512131751.320283-1-vladimir.oltean@nxp.com/ |
| [net-next] net: stmmac: remove excess documentation parameter | generic | PORTABLE | 通用 kernel-doc 修复 | drivers/net/ (kernel-doc) | https://patchwork.kernel.org/project/linux-arm-kernel/patch/E1v38Y7-00000008UCQ-3w27@rmk-PC.armlinux.org.uk/ |
| remoteproc: imx_dsp_rproc: Document run_stall struct member | generic | PORTABLE | 通用 kernel-doc 修复 | drivers/remoteproc/ (kernel-doc) | https://patchwork.kernel.org/project/linux-arm-kernel/patch/20250314151720.1793719-1-daniel.baluta@nxp.com/ |
| rtc: pl031: document struct pl031_vendor_data members | generic | PORTABLE | 通用 kernel-doc 修复 | drivers/rtc/ (kernel-doc) | https://patchwork.kernel.org/project/linux-arm-kernel/patch/20250305221659.1153495-1-alexandre.belloni@bootlin.com/ |

> 说明：上表末尾多条 `Documentation:` / kernel-doc 修复为**平凡通用文档补丁**——技术上全树适用（PORTABLE），但对 riscv 架构能力无实质影响，价值极低，仅为完整性列出。真正有 riscv 价值的是前 22 行（crypto lib / KUnit / raid6 / KVM selftest 框架 / 文档工具 / nolibc / TIF / auxvec）。

### N-A（同质合并成组，167 条）

| 组 | 条数 | 说明 / 依赖的 ARM 专属物 | 代表系列 |
|---|---|---|---|
| MAINTAINERS / mailmap 变更 | 51 | 维护者/邮箱/文件归属条目，纯元数据，无可移植代码 | `MAINTAINERS: add Raspberry Pi RP1 section`；`MAINTAINERS: Change Linus Walleij mail address`；`soc: officially expand maintainership team` |
| 通用/SoC 设备驱动 | 48 | arch 无关驱动经 arm 列表流入本桶；可在 riscv 编译但非架构缺口 | `net: wwan: t9xx (MediaTek)`；`PCI: endpoint: Add BAR_DISABLED support`；`media: Add support for multi-context operations`；`net: stmmac: remove mac_interface` |
| KVM-arm64 专属 selftest/特性 | 25 | 依赖 arm64 sysreg/嵌套虚拟化/GIC/GICR/vLPI/pKVM/SEA/SCTLR2 | `KVM: arm64: selftests: Basic nested guest support`；`KVM: arm64: Add KVM_PRE_FAULT_MEMORY support`；`kvm,selftests: MSIs as software-bypassing vLPIs` |
| arm64 专属 selftest | 15 | arm64 SVE/SME/tpidr2/FPMR/zt 等硬件专属测试的修复/清理 | `[v2] kselftest/arm64: Fix build failure with GCC-15`；`kselftest/arm64: Convert tpidr2 test to use kselftest.h`；`selftests/arm64: fix spelling errors` |
| iommufd HW 虚拟化 | 8 | vIOMMU/HW-QUEUE/vCMDQ 面向 arm SMMUv3 命令队列直通（框架通用但改动 HW 专属） | `iommufd: Add vIOMMU infrastructure (Part-4 HW QUEUE)`；`iommufd: Prepare for IOMMUFD_OBJ_HW_QUEUE` |
| resctrl / MPAM (ARM) | 8 | riscv 无 resctrl/MPAM 子系统 | `arm_mpam: resctrl: Counter Assignment (ABMC)`；`[RFC] kselftest/resctrl: Enable CAT on ARM`；`selftests/resctrl: IMC counters 链表管理` |
| arm64 专属文档 | 5 | arm64/arm 平台专属 .rst | `arm64: Fixes for cpu-feature-registers.rst`；`docs: arm64: Document text_offset is always 0`；`docs: arm: stm32 typo` |
| arm64 ISA / sysreg | 3 | arm64 专有 ISA/寄存器 | `arm64: Support FEAT_LSFE`；`Use __u128 in arm64 UAPI headers`；`arm64/debug: Drop DBG_MDSCR_* macros` |
| arm64 tools 头文件同步 | 3 | 同步 arm64 cputype.h / Cortex 型号定义 | `REQUEST: Syncing tools/arch/arm64/include/asm/cputype.h`；`tools: arm64: Add Cortex-A720AE` |
| KVM-x86 专属 | 1 | x86 APERF/MPERF 拦截 cap | `KVM: x86: Provide a cap to disable APERF/MPERF read intercepts` |

## 方法与验证说明
- 深挖 6 条候选（`curl -sL --retry 3 <mbox>` 取全文核对 diffstat）：backtrace（确认 `lib/kunit/bug.c`）、AT_VECTOR_SIZE（确认 treewide 逐 arch 删 auxvec.h）、SHA-3（确认纯 `lib/crypto/sha3.c`）、raid6（确认 diff 含 `lib/raid/raid6/riscv/*`）、TIF-bits、automarkup。
- riscv 落点均以本地树 v7.2.0-rc3 `ls`/`grep` 核对存在：`arch/riscv/include/uapi/asm/auxvec.h:37`、`arch/riscv/include/asm/thread_info.h`、`lib/crypto/{sha3,blake2b,curve25519}.c`、`lib/crypto/riscv/`、`lib/raid/raid6/riscv/` + `tests/raid6_kunit.c`、`tools/include/nolibc/arch-riscv.h`、`tools/testing/selftests/kvm/riscv/`、`Documentation/sphinx/automarkup.py`、`scripts/coccinelle/misc/`。
- 注：两条候选（TIF-bits、automarkup）的 mbox 链接指向其邮件线程中的相邻/关联补丁（分别为 sud_test、arm64 asymmetric-32bit 文档），故按系列标题意图 + 已核对的树内文件判定，未以该 mbox diff 为准。
