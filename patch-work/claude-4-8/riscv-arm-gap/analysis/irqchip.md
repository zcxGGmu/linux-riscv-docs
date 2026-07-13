# irqchip 可移植性分析（linux-arm-kernel → RISC-V）

> 输入：`data/by_category/irqchip.jsonl`（192 条系列，tier=C）。
> 纪律：GIC/GICv3/ITS/GICv4/GICv5/vgic/pKVM = ARM 中断控制器硬件/KVM 内部 → **N-A**（riscv 用 AIA=APLIC/IMSIC，`drivers/irqchip/irq-riscv-*`）；
> **通用 irqdomain / genirq-MSI / msi-lib / of-irq / KVM 核心** 改动 → **PORTABLE**（`kernel/irq`、`drivers/irqchip` 通用层、`drivers/of/irq.c`、`virt/kvm`）。
> 全部落点均已在本地内核树 `linux-riscv`（v7.2.0-rc3）核对存在。

## 摘要

- **系列总数**：192
- **四态计数**：
  - **N-A ≈ 169**（GIC/ITS/GICv4/v5 硬件、vgic/KVM-arm64、pKVM、arm64 idreg/EL2、各家 SoC/GPIO/PCI/mfd 驱动、net-stmmac EEE、误分类 "its"/"LPI" 噪声、DTS/bootwrapper/selftests）
  - **PORTABLE = 20**（通用 genirq-MSI / msi-lib / irqdomain / of-irq / KVM 核心 / syscore / gfp / iommu-dma-MSI / PCI-EP 框架；多数为「通用核心 PORTABLE + arch 消费者 N-A」的部分可移植）
  - **PATTERN = 2**（arm64 feature-config 思想；GICv4 直注 vs IMSIC 直注思想类比）
  - **ALREADY = 1**（#180 RISC-V IMSIC 系列本身——已合入 riscv）

- **本类 Top 候选**（按价值排序，全部为通用 irq/MSI 基础设施）：
  1. **irqchip: MSI cleanup + 转 MSI-parent domain**（#145）——`irqdomain` 核心 + **直接转换 `irq-riscv-imsic` / `irq-sg2042-msi`**。PORTABLE（已落地 riscv）。
  2. **irqchip: MSI parent cleanup + genirq/msi 助手**（#161）——`msi_create_parent_irq_domain()` 落 `kernel/irq/msi.c`；`irq-msi-lib.h` 迁至 `include/linux/irqchip/`。PORTABLE（已落地）。
  3. **genirq/msi: device MSI prepare/alloc 时序修复**（#162）——`.msi_teardown()` 回调落 `kernel/irq/msi.c`。PORTABLE（已落地）。
  4. **of/irq: msi-parent 处理修复/清理**（#101）——纯 `drivers/of/irq.c`（`of_msi_xlate`/`of_msi_get_domain`）。PORTABLE。
  5. **iommu: MSI mapping w/ nested SMMU（Part-1 核心）**（#179/#183）——`genirq/msi` + `iommu-dma` MSI 通用化 + `IRQ_MSI_IOMMU`。PORTABLE（核心部分）。
  6. **irqchip/msi-lib 两则**（#131 fwnode refcount / #158 MASK_PARENT flag）——纯 `drivers/irqchip/irq-msi-lib.c`。PORTABLE。
  7. **RISC-V IMSIC driver improvements**（#180）——riscv 原生 + 通用 `irq_force_complete_move()` / `GENERIC_PENDING_IRQ`。ALREADY。

---

## Top 可移植候选（深度）

### 1. irqchip: MSI cleanup and conversion to MSI parent domain（#145）
- **原补丁**：`irqchip: MSI cleanup and conversion to MSI parent domain`（12 patches，namcao@linutronix.de）
  <https://patchwork.kernel.org/project/linux-arm-kernel/patch/ff2c9460d03e44cb2946521dbae5ce800d34523e.1750860131.git.namcao@linutronix.de/> 状态=new
- **可移植点**：patch 1 `irqdomain: Add device pointer to irq_domain_info and msi_domain_info`（通用 genirq）；随后把各 MSI 控制器转到 `msi_create_parent_irq_domain()`——**patch 3 = `irqchip/riscv-imsic`**，patch 6 = `irqchip/sg2042-msi`（均为 RISC-V 驱动）。
- **riscv 落点**：`drivers/irqchip/irq-riscv-imsic-platform.c`、`drivers/irqchip/irq-sg2042-msi.c`——**已核对：二者均已调用 `msi_create_parent_irq_domain` 且 `#include` 迁移后的 `include/linux/irqchip/irq-msi-lib.h`**。
- **判定**：**PORTABLE（已落地 riscv）**——通用 MSI-parent 框架重构，RISC-V 驱动是一等消费者。

### 2. irqchip: MSI parent cleanup and PCI host driver conversion（#161）
- **原补丁**：`irqchip: MSI parent cleanup and PCI host driver conversion`（9 patches，maz@kernel.org）
  <https://patchwork.kernel.org/project/linux-arm-kernel/patch/20250513172819.2216709-2-maz@kernel.org/> 状态=new
- **可移植点**：patch 1 把 `irq-msi-lib.h` 提升为全局头（`{drivers => include/linux}/irqchip/irq-msi-lib.h`，同一 diff 触及 `irq-riscv-imsic-platform.c` 与 `irq-sg2042-msi.c`）；patch 2 `genirq/msi: Add helper for creating MSI-parent irq domains`（`msi_create_parent_irq_domain()`，落 `kernel/irq/msi.c`）。
- **riscv 落点**：`kernel/irq/msi.c`、`include/linux/irqchip/irq-msi-lib.h`（**已核对存在**）；riscv-imsic/sg2042 直接受益。
- **判定**：**PORTABLE（已落地）**——纯通用 genirq/msi 核心助手。

### 3. genirq/msi: Fix device MSI prepare/alloc sequencing（#162）
- **原补丁**：`genirq/msi: Fix device MSI prepare/alloc sequencing`（5 patches，maz@kernel.org）
  <https://patchwork.kernel.org/project/linux-arm-kernel/patch/20250513163144.2215824-3-maz@kernel.org/> 状态=new
- **可移植点**：新增 `.msi_teardown()` 作为 `.msi_prepare()` 的逆操作，把 prepare() 调用移到 per-device 分配路径——纯通用 MSI domain 生命周期修复；gic-v3-its 仅为消费者。
- **riscv 落点**：`kernel/irq/msi.c`——**已核对：`msi_domain_ops_teardown` / `.msi_teardown` 已在 `kernel/irq/msi.c:828/1127` 落地**；任何 riscv MSI 域（IMSIC/APLIC-MSI/RPMI-sysmsi）走同一核心路径。
- **判定**：**PORTABLE（已落地）**。

### 4. of/irq: Misc msi-parent handling fixes/clean-ups（#101）
- **原补丁**：`of/irq: Misc msi-parent handling fixes/clean-ups`（5 patches，lpieralisi@kernel.org）
  <https://patchwork.kernel.org/project/linux-arm-kernel/patch/20251021124103.198419-2-lpieralisi@kernel.org/> 状态=new
- **可移植点**：patch 1 仅改 `drivers/of/irq.c`（+36/-3），修 `of_msi_xlate()` 的 msi-parent 检查、`of_msi_get_domain()` 的 OF node refcount、导出 `of_msi_xlate()`。纯 DT/irq 通用层。
- **riscv 落点**：`drivers/of/irq.c`——**已核对：`of_msi_xlate`/`of_msi_get_domain` 存在（8 处）**。riscv 走 DT 启动，MSI 父域解析共用此码。
- **判定**：**PORTABLE**（gic-its 的 patch 5 为 N-A 消费者）。

### 5. iommu: Add MSI mapping support with nested SMMU — Part-1 核心（#179，及 v1 #183）
- **原补丁**：`iommu: Add MSI mapping support with nested SMMU (Part-1 core)`（7 patches，nicolinc@nvidia.com）
  <https://patchwork.kernel.org/project/linux-arm-kernel/patch/e13d23eeacd67c0a692fc468c85b483f4dd51c57.1740014950.git.nicolinc@nvidia.com/> 状态=new
- **可移植点**：`genirq/msi: Store IOMMU IOVA directly in msi_desc`、`iommu: Make iommu_dma_prepare_msi() into a generic operation`、`irqchip: Have CONFIG_IRQ_MSI_IOMMU be selected by irqchips that need it`——通用 genirq/msi + iommu-dma MSI 映射底座。
- **riscv 落点**：`include/linux/msi.h`（`iommu_dma_prepare_msi`/`msi_msg_set_addr` 已引用）、`kernel/irq/Kconfig:92`（`IRQ_MSI_IOMMU` 已存在）。riscv IOMMU + AIA 若做 MSI 重映射走此通用底座。
- **判定**：**PORTABLE（核心部分）**；nested-SMMU / iommufd 的 ARM 专属部分 N-A。

### 6. irqchip/msi-lib 两则（#131 / #158）
- **#131** `irqchip/msi-lib: Fix fwnode refcount in msi_lib_irq_domain_select()`（+3/-3，仅 `irq-msi-lib.c`）
  <https://patchwork.kernel.org/project/linux-arm-kernel/patch/20250804145553.795065-1-lpieralisi@kernel.org/>
- **#158** `irqchip/msi-lib: Honor the MSI_FLAG_PCI_MSI_MASK_PARENT flag`（仅 `irq-msi-lib.c`）
  <https://patchwork.kernel.org/project/linux-arm-kernel/patch/20250517103011.2573288-1-maz@kernel.org/>
- **riscv 落点**：`drivers/irqchip/irq-msi-lib.c`（**已核对存在**）；被 `irq-riscv-imsic-platform.c`、`irq-sg2042-msi.c` `#include` 使用。
- **判定**：**PORTABLE**——通用 MSI-lib 修复，直接惠及 riscv MSI 驱动。

### 附：RISC-V 原生参照（#180）
- **原补丁**：`RISC-V IMSIC driver improvements`（10 patches，apatel@ventanamicro.com，arch=other）
  <https://patchwork.kernel.org/project/linux-arm-kernel/patch/20250217085657.789309-7-apatel@ventanamicro.com/>
- 本系列即 RISC-V 侧：`irqchip/riscv-imsic: Move to common MSI lib`、`RISC-V: Select GENERIC_PENDING_IRQ`（patch 6 = `arch/riscv/Kconfig +1`）、并把 `irq_force_complete_move()`/`irq_can_move_in_process_context()` 抽成**通用 genirq**。
- **riscv 落点已核对**：`arch/riscv/Kconfig:123 select GENERIC_PENDING_IRQ if SMP`；`kernel/irq/migration.c:38 irq_force_complete_move`、`:131 irq_can_move_in_process_context`。
- **判定**：**ALREADY**——证明 IMSIC 亲和迁移/MSI-lib 已复用通用 genirq 底座（与 GICv3-ITS 同框架）。

### 其余 PORTABLE（通用但非 irq 核心，多为「部分」）
| # | 系列 | 通用点 | riscv 落点 |
|---|---|---|---|
| #28 | gfp_types: 新增 `GFP_ATOMIC_RT`（gic-its 为消费者）| `include/linux/gfp_types.h` 通用 GFP 标志 | 通用 mm；**尚未合入**（tree 中无 `GFP_ATOMIC_RT`），PORTABLE |
| #98 | syscore: Pass context data to callbacks | `drivers/base/syscore.c`+`include/linux/syscore_ops.h` 通用 | 通用；irq-imx-gpcv2 等为消费者 N-A |
| #116 | KVM: Speed up MMIO registrations（后 2 patch）| `virt/kvm/kvm_main.c`（SRCU 屏障、免 `synchronize_srcu()`）| 通用 KVM；riscv KVM 共用（vgic-init 前 2 patch N-A）|
| #149 | KVM: Add arch hooks for KVM syscore ops（patch 1）| `virt/kvm/kvm_main.c` 通用 arch hook | 通用 KVM；vgic-its patch 2 N-A |
| #141 | PCI EP RC-to-EP doorbell w/ platform MSI | `drivers/pci/endpoint/` + `pci-ep-msi` 通用框架 | 通用 PCI-EP；riscv 可用 |
| #189 | PCI: enable/disable_device() bridge hook（patch 1）| `drivers/pci/` 通用桥回调 | 通用 PCI；i.MX95 ITS-MSI patch 2 N-A |
| #65/#66 | fsl-mc: 转 device MSI 基础设施（核心）| `drivers/base/platform-msi` + `genirq/msi` device-MSI 通用化 | 通用 device-MSI；fsl-mc + gic-its 部分 N-A（riscv-rpmi-sysmsi 已重度用 MSI）|
| #171 | irqdomain: Switch to of_fwnode_handle()/irq_domain_create_* | 通用 irqdomain API 迁移（`kernel/irq/irqdomain.c`）| riscv irqchip 驱动随同迁移 |
| #29 | iommu: 设备自有 PASID 空间 for SVA | `drivers/iommu` 通用核心 | 通用 iommu（越 irq 桶）|
| #42 | swiotlb/dma-direct host page-size 对齐（前 2 patch）| `kernel/dma/` 通用 swiotlb/dma-direct | 通用 dma；coco/RHI arm64 patch 3 N-A（越桶）|
| #54 | SM3 library | `lib/crypto/` 通用库 | 通用 lib（**误分类**，越 irq 桶）|

---

## 全量判定表

> 同质 N-A 系列按主题合并成组（覆盖输入每一条）；PORTABLE/PATTERN/ALREADY 逐条列 web_url。

### PORTABLE / ALREADY / PATTERN（逐条）

| # 行 | 系列 | arch | 判定 | 可移植点 | riscv 落点 | web_url |
|---|---|---|---|---|---|---|
| 145 | irqchip: MSI cleanup + 转 MSI-parent domain | other | **PORTABLE** | irqdomain 核心+转 riscv-imsic/sg2042 | `irq-riscv-imsic-platform.c`,`irq-sg2042-msi.c`,`kernel/irq/msi.c` | [link](https://patchwork.kernel.org/project/linux-arm-kernel/patch/ff2c9460d03e44cb2946521dbae5ce800d34523e.1750860131.git.namcao@linutronix.de/) |
| 161 | irqchip: MSI parent cleanup + PCI host 转换 | generic | **PORTABLE** | `msi_create_parent_irq_domain()`；msi-lib.h 全局化 | `kernel/irq/msi.c`,`include/linux/irqchip/irq-msi-lib.h` | [link](https://patchwork.kernel.org/project/linux-arm-kernel/patch/20250513172819.2216709-2-maz@kernel.org/) |
| 162 | genirq/msi: device MSI prepare/alloc 时序 | generic | **PORTABLE** | `.msi_teardown()` 通用回调 | `kernel/irq/msi.c` | [link](https://patchwork.kernel.org/project/linux-arm-kernel/patch/20250513163144.2215824-3-maz@kernel.org/) |
| 101 | of/irq: msi-parent 处理修复/清理 | generic | **PORTABLE** | `of_msi_xlate`/`of_msi_get_domain` | `drivers/of/irq.c` | [link](https://patchwork.kernel.org/project/linux-arm-kernel/patch/20251021124103.198419-2-lpieralisi@kernel.org/) |
| 179 | iommu: MSI mapping w/ nested SMMU (core) | arm | **PORTABLE**(核心) | genirq/msi+iommu-dma MSI 通用化 | `include/linux/msi.h`,`kernel/irq/Kconfig:92` | [link](https://patchwork.kernel.org/project/linux-arm-kernel/patch/e13d23eeacd67c0a692fc468c85b483f4dd51c57.1740014950.git.nicolinc@nvidia.com/) |
| 183 | iommu: MSI mapping w/ nested SMMU (v1) | arm | **PORTABLE**(核心) | 同 #179 | 同上 | [link](https://patchwork.kernel.org/project/linux-arm-kernel/patch/98233d5817e66bb7363090526b53422436894051.1739005085.git.nicolinc@nvidia.com/) |
| 131 | irqchip/msi-lib: fwnode refcount | generic | **PORTABLE** | msi-lib refcount 修复 | `drivers/irqchip/irq-msi-lib.c` | [link](https://patchwork.kernel.org/project/linux-arm-kernel/patch/20250804145553.795065-1-lpieralisi@kernel.org/) |
| 158 | irqchip/msi-lib: MASK_PARENT flag | generic | **PORTABLE** | msi-lib flag 处理 | `drivers/irqchip/irq-msi-lib.c` | [link](https://patchwork.kernel.org/project/linux-arm-kernel/patch/20250517103011.2573288-1-maz@kernel.org/) |
| 171 | irqdomain: 转 of_fwnode_handle()/create_* | generic | **PORTABLE** | 通用 irqdomain API 迁移 | `kernel/irq/irqdomain.c` | [link](https://patchwork.kernel.org/project/linux-arm-kernel/patch/20250319092951.37667-8-jirislaby@kernel.org/) |
| 116 | KVM: Speed up MMIO registrations | arm | **PORTABLE**(后2) | `virt/kvm` SRCU/免 synchronize_srcu | `virt/kvm/kvm_main.c` | [link](https://patchwork.kernel.org/project/linux-arm-kernel/patch/20250909100007.3136249-2-keirf@google.com/) |
| 149 | KVM: Add arch hooks for KVM syscore ops | arm | **PORTABLE**(p1) | 通用 KVM syscore hook | `virt/kvm/kvm_main.c` | [link](https://patchwork.kernel.org/project/linux-arm-kernel/patch/20250623132714.965474-1-dwmw2@infradead.org/) |
| 98 | syscore: Pass context data to callbacks | other | **PORTABLE** | 通用 syscore_ops ctx | `drivers/base/syscore.c`,`include/linux/syscore_ops.h` | [link](https://patchwork.kernel.org/project/linux-arm-kernel/patch/20251029163336.2785270-3-thierry.reding@gmail.com/) |
| 28 | gfp_types: 新增 GFP_ATOMIC_RT | generic | **PORTABLE**(p1) | 通用 GFP 标志(未合入) | `include/linux/gfp_types.h` | [link](https://patchwork.kernel.org/project/linux-arm-kernel/patch/20260520204628.933654-1-longman@redhat.com/) |
| 141 | PCI EP RC-to-EP doorbell w/ platform MSI | generic | **PORTABLE**(框架) | PCI-EP + platform-msi 框架 | `drivers/pci/endpoint/` | [link](https://patchwork.kernel.org/project/linux-arm-kernel/patch/20250710-ep-msi-v21-7-57683fc7fb25@nxp.com/) |
| 189 | PCI: enable/disable_device() bridge hook | generic | **PORTABLE**(p1) | 通用 PCI 桥回调 | `drivers/pci/` | [link](https://patchwork.kernel.org/project/linux-arm-kernel/patch/20250114-imx95_lut-v9-2-39f58dbed03a@nxp.com/) |
| 65 | fsl-mc: 转 device MSI 基础设施 | generic | **PORTABLE**(核心) | platform/device-MSI 通用化 | `drivers/base/platform-msi.c`,`kernel/irq/msi.c` | [link](https://patchwork.kernel.org/project/linux-arm-kernel/patch/20260224100936.3752303-7-maz@kernel.org/) |
| 66 | fsl-mc: 转 device MSI（v1）| generic | **PORTABLE**(核心) | 同 #65 | 同上 | [link](https://patchwork.kernel.org/project/linux-arm-kernel/patch/20260218135203.2267907-7-maz@kernel.org/) |
| 29 | iommu: 设备自有 PASID for SVA | generic | **PORTABLE** | 通用 iommu 核心(越桶) | `drivers/iommu/` | [link](https://patchwork.kernel.org/project/linux-arm-kernel/patch/20260520150743.727106-1-joonwonkang@google.com/) |
| 42 | swiotlb/dma host page-size 对齐 | arm | **PORTABLE**(前2) | 通用 swiotlb/dma-direct(越桶) | `kernel/dma/` | [link](https://patchwork.kernel.org/project/linux-arm-kernel/patch/20260427063108.909019-4-aneesh.kumar@kernel.org/) |
| 54 | SM3 library | arm | **PORTABLE** | 通用 lib/crypto(误分类) | `lib/crypto/` | [link](https://patchwork.kernel.org/project/linux-arm-kernel/patch/20260321040935.410034-11-ebiggers@kernel.org/) |
| 180 | RISC-V IMSIC driver improvements | other | **ALREADY** | riscv 原生 + 通用 `irq_force_complete_move`/`GENERIC_PENDING_IRQ` | `arch/riscv/Kconfig:123`,`kernel/irq/migration.c` | [link](https://patchwork.kernel.org/project/linux-arm-kernel/patch/20250217085657.789309-7-apatel@ventanamicro.com/) |
| 62 | arm64: Fully disable configured-out features | arm | **PATTERN**(弱) | idreg「彻底移除已关特性」思想 | `arch/riscv/kernel/cpufeature.c`（ISA 串路径，非 sysreg）| [link](https://patchwork.kernel.org/project/linux-arm-kernel/patch/20260302115653.1517326-12-maz@kernel.org/) |
| — | GICv4/v4.1 直注 VLPI/vSGI（#24,25,112,134,135,159,160）| — | **PATTERN**(思想) | 「设备直注虚拟中断」思想 ≈ riscv IMSIC guest-file 直投；无具体可移植 diff | `drivers/irqchip/irq-riscv-imsic-*` | 见下 N-A 组 |

### N-A 分组（约 169 条，均依赖 ARM 硬件/ISA 或为板级/驱动/噪声，riscv 无可移植价值）

| 组 | 主题 | 行号（示例）| 判定依据 |
|---|---|---|---|
| A. KVM arm64 vgic/vgic-its/vgic-v5 | 虚拟 GIC 分发/重分发/LPI/ITS/IIDR/nASSGIcap/debugfs | 2,4,13,18-23,30-32,34,35,44-46,48,50,51,57,60,63,67,68,79,83,84,92,94,95,99,102-104,106,107,114,134,135,137,140,146,147,150,152,153,155-157,160,169,178,181,192 | vgic = ARM GICv2/v3/v4 虚拟化，riscv 用 AIA 虚拟化（`arch/riscv/kvm/aia*.c`），机制/寄存器全异 |
| B. KVM arm64 pKVM / EL2 / nv / idreg | pKVM vCPU 状态、EL2 世界切换、NV、ID_PFR1.GIC、set_id_regs | 3,7,72,74,90,97,113,117,129,140,163,172 | ARM EL2/pKVM/idreg-sysreg 专属 |
| C. GICv3-ITS 修复/清理/errata/workaround | its_probe_one 泄漏、OF node 泄漏、FIELD_MODIFY、MSI-X、resume、per-device MSI 上限、地址截断、Altera/HIP errata、lockdep | 5,6,8,9,10,12,14,28(p2),37,39,69,76,78,100,115,122,137,143 | ITS = ARM MSI 控制器硬件内部；riscv 用 IMSIC/APLIC-MSI |
| D. GICv5 (irqchip/gic-v5) | iwb/ITS/LPI/IRS/IST/SPI/endianness/CDEOI/拼写 | 1,38,64,71,80,109,111,118,119,125,127,128,133,139 | GICv5 硬件寄存器/指令编码 |
| E. gic-v2m / gic-v4 / gic-v4.1 / gic-v3 通用 warn | v2m 对齐/UAF、v4 VLPI 广告/命令行、v4.1 间接表/VSGI、v3 越界 warn/GICD_CTLR 命名/UBSAN/partition | 24,25,43,53,61,87,112,120,130,138,142,159,167 | GIC 硬件寄存器/命令 |
| F. arm64 KVM GICv3 CPUIF / vgic-v5 host | ICH_HCR/ICC_SRE/ICH_VTR/LR overflow/TWI/CPUIF trap/GICv5 legacy | 79,86,93,94,95,105,107,114 | ARM GIC 系统寄存器陷入 |
| G. SoC/板级 irqchip 驱动 | exynos-combiner,atmel-aic5,mvebu(gicp/icu/sei),stm32-exti,vt8500,davinci,sunxi-nmi,apple-aic,brcmstb-l2,bcm7038-l1,bcm2712-mip,qcom-mpm,mchp-eic,imx-irqsteer,aspeed-scu,samsung-gs101,ti-sci-inta | 27,33,36,41,52,56,59,64,85,96,110,120,124,132,138,143,144,165,166,168,174-176,186-188,191 | 各家 SoC 中断控制器硬件，riscv 无对应 |
| H. GPIO 驱动中断 | rockchip,mxc,brcmstb,stmpe,immutable irq_chip,qe-gpio | 16,26,55,58,70,73,123,144,164,182 | GPIO 驱动专属；immutable irq_chip 为通用模式但逐驱动改 |
| I. PCI host INTx/IRQ-domain 泄漏 | aspeed,xilinx | 49,81,82 | 驱动级泄漏修复，无通用底座改动 |
| J. mfd/serial/misc 驱动 irq | mt6397-irq,stmpe,mxs-auart | 11,15,136 | 驱动专属 |
| K. net-stmmac EEE-LPI（误分类 "LPI"）| stmmac/xpcs/phylink EEE 低功耗 | 91,170,173,177,184,185,190 | LPI=low-power-idle，非中断；与 irq 无关 |
| L. 误分类噪声（"its"/"cc"）| usb-cdns3,drm-rockchip,usb-atmel,drm-panel,net-phy-package,dt-aspeed,ARM-xen,ARM-pxa-gpio | 40,47,77,88,126,148,151,177 | 标题含 "its"/板级，与 irqchip 无关 |
| M. Hyper-V / MSHV / x86 irqdomain | PCI passthru Hyper-V,MSHV arm64 | 75,89 | Hyper-V/x86 hyperv 专属 |
| N. selftests / kvm-unit-tests / bootwrapper / docs | vgic_lpi_stress,VHE-EL2,GICv5 bootwrapper,GICv3 docs | 17,74,90,92,103,104,108,113,156,163 | 测试/引导/文档，ARM GIC 专属 |
| O. 树级清理（触及 arm 驱动）| irqchip int 错误码,dev_fwnode(),__ASSEMBLER__ | 43,121,154 | 机械清理，落在 arm/各家驱动 |

---

## 结论

irqchip 桶 192 条中 **~88% 为 N-A**（ARM GIC 系列硬件 + vgic/KVM-arm64 + 各家 SoC/GPIO/PCI 驱动 + 误分类噪声）。真正对 RISC-V 有价值的是**通用 genirq-MSI / msi-lib / irqdomain / of-irq 基础设施**（20 条 PORTABLE），其中 **MSI-parent domain 重构（#145/#161/#162）与 msi-lib 修复（#131/#158）已实际落地并被 `irq-riscv-imsic`/`irq-sg2042-msi` 使用**——证明 riscv MSI 栈与 GICv3-ITS 共享同一通用 genirq/msi 核心；#180 RISC-V IMSIC 系列本身即 ALREADY 参照。GICv4 设备直注仅与 IMSIC guest-file 直投构成思想类比（PATTERN），无具体可移植 diff。
