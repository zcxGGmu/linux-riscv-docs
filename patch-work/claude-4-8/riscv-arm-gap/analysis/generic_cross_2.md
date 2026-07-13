# generic-cross（第2片）可移植性分析（linux-arm-kernel → RISC-V）

> 输入：`data/by_category/generic-cross.1.jsonl`（235 条系列，全部 `arch=generic` / Tier A）。
> 纪律：落在通用代码（`kernel/`、`mm/`、`lib/`、`include/linux/`、`drivers/base|of|pci|iommu` 框架、`fs/` core、
> `virt/kvm`、`net/core`、`tools/`、`scripts/`）且架构无关的改动 → **PORTABLE**（riscv 自动/近自动适用）；
> 单一设备驱动 / 厂商 SoC / staging / 板级 / arch=arm 专属 / 讨论帖 / pull-request → **N-A 噪声**（riscv 无可移植信号）。
> 本片主体是驱动子系统噪声，真正对 arch 有意义的通用改动约 20 余条，其余同质噪声合并成组。

## 摘要

- **系列总数**：235
- **四态计数**：ALREADY 0 ／ **PORTABLE 56** ／ PATTERN 1 ／ **N-A 178**
- PORTABLE 主体为「通用内核 core/基础设施改动」；N-A 主体为「特定设备驱动 + ARM MPAM 硬件驱动 + arch=arm 专属 + 空/pull/讨论帖」。

### 本类 Top 候选（按 arch 价值排序）

1. **arch_topology: move parse_acpi_topology() to common code** — 补丁自述即「为 RISC-V 复用」，最强。
2. **cacheinfo 通用助手**（cache-id / cache-size-by-level / DT l1 entry）— `drivers/base/cacheinfo.c`，riscv 直接受益。
3. **bits: split/unify GENMASK\*()** — 核心头 `include/linux/bits.h`，全架构。
4. **fs/dax: Fix ZONE_DEVICE page reference counts** — 20 补丁 MM/fs core。
5. **dma/pool: DMA_DIRECT_REMAP allocations decrypted** — `kernel/dma/pool.c`，机密计算相关。
6. **kcov: add unique cover/edge/cmp modes** — `kernel/kcov.c` 覆盖率基础设施（对应 sanitizer 缺口）。
7. **KVM: Make irqfd registration globally unique** — `virt/kvm` core（+ `sched/wait`），riscv KVM 受益。
8. **of/irq + PCI/MSI**（of_msi_xlate / MSI domain sizing）— 通用 OF/PCI-MSI 框架。

---

## Top 可移植候选（深度）

### 1. arch_topology: move parse_acpi_topology() to common code ★
- **原补丁**：L4 `[v4,1/1]`（https://patchwork.kernel.org/project/linux-arm-kernel/patch/20250923015409.15983-2-cuiyunhui@bytedance.com/）；早版 L8 `[v2]`。状态=new
- **可移植点**：curl 全文确认——将 `parse_acpi_topology()` 从 `arch/arm64/kernel/topology.c` 上移到 `drivers/base/arch_topology.c` + `include/linux/arch_topology.h`。提交信息原文：「Currently, RISC-V lacks arch-specific registers for CPU topology properties and must get them from ACPI. Thus, parse_acpi_topology() is moved from arm64/ to drivers/ for RISC-V reuse.」
- **riscv 落点**：`drivers/base/arch_topology.c`（通用，改动直接生效）；riscv 侧 `arch/riscv/kernel/smpboot.c` / `arch/riscv/include/asm/topology.h`（已 `#include <linux/arch_topology.h>`，本地核对存在）在 ACPI 路径调用即可。
- **判定**：**PORTABLE**。补丁本身就是为 riscv 做的通用化重构，零重写。

### 2. cacheinfo 通用助手（cache-id / cache-size / DT l1）
- **原补丁**：L35 `[01/33] cacheinfo: Expose the code to generate a cache-id from a device_node`、L34 `[02/33] cacheinfo: Add helper to find the cache size from cpu+level`（https://patchwork.kernel.org/project/linux-arm-kernel/patch/20250822153048.2287-36-james.morse@arm.com/）；L203 `base/of/cacheinfo: support l1-cache entry in dt`。状态=new
- **可移植点**：curl 确认改动落在 `drivers/base/cacheinfo.c` + `include/linux/cacheinfo.h`（通用），导出 `cache_of_calc_id()` 类助手、按 cpu+level 查 cache size。虽随 ARM MPAM 系列提交，但这两条是纯通用 cacheinfo 基础设施。
- **riscv 落点**：`arch/riscv/kernel/cacheinfo.c`（本地核对存在）+ `drivers/base/cacheinfo.c`。riscv 走 DT/ACPI cacheinfo，直接可用这些助手。
- **判定**：**PORTABLE**（generic cacheinfo 框架增强）。

### 3. bits: split and unify GENMASK*() ★
- **原补丁**：L108 `[v2,1..3/3] bits: split/unify GENMASK*() + test_bits`（https://patchwork.kernel.org/project/linux-arm-kernel/patch/20250609-consolidate-genmask-v2-2-b8cce8107e49@wanadoo.fr/）。状态=new
- **可移植点**：curl 确认仅改 `include/linux/bits.h`（拆分 asm/非-asm `GENMASK`，统一定义）+ `lib/test_bits.c`。纯核心头，全架构编译期受益。
- **riscv 落点**：`include/linux/bits.h`（通用，无 arch 依赖）；riscv 汇编/C 皆使用 GENMASK。
- **判定**：**PORTABLE**。

### 4. fs/dax: Fix ZONE_DEVICE page reference counts
- **原补丁**：L187 `[v9,01..20/20]`（https://patchwork.kernel.org/project/linux-arm-kernel/patch/67055d772e6102accf85161d0b57b0b3944292bf.1740713401.git-series.apopple@nvidia.com/）。状态=new
- **可移植点**：20 补丁重做 `fs/dax.c` + `mm/`（ZONE_DEVICE / DAX layout / page refcount），架构无关的 MM/文件系统 core。
- **riscv 落点**：`fs/dax.c`、`mm/memremap.c`、`mm/`（通用）。riscv 支持 ZONE_DEVICE/DAX，直接受益。
- **判定**：**PORTABLE**（MM/fs 核心，改动量大但零 arch 重写）。

### 5. dma/pool: Ensure DMA_DIRECT_REMAP allocations are decrypted ★
- **原补丁**：L51 `[v2] dma/pool`（https://patchwork.kernel.org/project/linux-arm-kernel/patch/20250811181759.998805-1-sdonthineni@nvidia.com/）。状态=new
- **可移植点**：curl 确认仅改 `kernel/dma/pool.c`——保证 DMA_DIRECT_REMAP 池分配在建立映射时解密（confidential/CoCo 场景）。通用 dma-direct 逻辑。
- **riscv 落点**：`kernel/dma/pool.c`（通用）；riscv 使用 dma-direct/`swiotlb`，与机密计算底座（`_baseline` §confidential 相关）契合。
- **判定**：**PORTABLE**。

### 6. kcov: add unique cover, edge, and cmp modes ★
- **原补丁**：L230（https://patchwork.kernel.org/project/linux-arm-kernel/patch/20250110073056.2594638-1-quic_jiangenj@quicinc.com/）。状态=new
- **可移植点**：curl 确认主体在 `kernel/kcov.c` + `include/linux/kcov.h` + `include/uapi/linux/kcov.h` + `lib/`（新增 unique 覆盖模式）；另含 `arch/arm64` percpu/irqflags 小优化钩子。
- **riscv 落点**：`kernel/kcov.c`（通用）；riscv 有 `ARCH_HAS_KCOV`（本地核对 `arch/riscv/Kconfig:38`）。core 直接受益，arm64 侧小钩子为可选优化，riscv 可后补。
- **判定**：**PORTABLE**（通用覆盖率基础设施；呼应 sanitizer 缺口）。

### 7. KVM: Make irqfd registration globally unique
- **原补丁**：L122 `[v3,01..13/13]`（https://patchwork.kernel.org/project/linux-arm-kernel/patch/20250522235223.3178519-8-seanjc@google.com/）。状态=new
- **可移植点**：`virt/kvm/eventfd.c` irqfd 注册去重 + `sched/wait` 的 `add_wait_queue_priority()` 通用调整。架构无关 KVM core。
- **riscv 落点**：`virt/kvm/`（通用）；riscv KVM 存在（本地核对 `arch/riscv/kvm/` 含 aia/imsic），irqfd 走通用路径，直接受益。
- **判定**：**PORTABLE**。

### 8. of/irq of_msi_xlate + PCI/MSI domain sizing
- **原补丁**：L11 `of/irq: Add msi-parent check to of_msi_xlate()`、L56 `of/irq: Convert of_msi_map_id() callers to of_msi_xlate()`（https://patchwork.kernel.org/project/linux-arm-kernel/patch/20250916091858.257868-1-lpieralisi@kernel.org/）；L113 `PCI/MSI: Size device MSI domain with the maximum number of vectors`。状态=new
- **可移植点**：`drivers/of/irq.c` 的 MSI id 翻译统一、`drivers/pci/msi/` 域尺寸计算。通用 OF/PCI-MSI 框架。
- **riscv 落点**：`drivers/of/irq.c`、`drivers/pci/msi/`（通用）；riscv 走 DT + AIA(IMSIC/APLIC) MSI，通用 OF/MSI 层直接受益。
- **判定**：**PORTABLE**。

---

## 全量判定表

> PORTABLE / PATTERN 逐条列出；N-A 噪声按主题合并成组（给代表 web_url + 行号）。

### PORTABLE（通用 core/基础设施，riscv 自动或近自动适用）

| 行 | 系列 | 判定 | 可移植点 / riscv落点 | web_url |
|---|---|---|---|---|
| L4/L8 | arch_topology: parse_acpi_topology → common | PORTABLE★ | `drivers/base/arch_topology.c`（为 riscv 而做）| .../20250923015409.15983-2-cuiyunhui@… |
| L34/L35 | cacheinfo: cache-id / cache-size helpers | PORTABLE★ | `drivers/base/cacheinfo.c` → riscv `kernel/cacheinfo.c` | .../20250822153048.2287-36-james.morse@… |
| L203 | base/of/cacheinfo: l1-cache entry in DT | PORTABLE | `drivers/base|of` cacheinfo，riscv DT cacheinfo | .../20250129164855.676-2-alireza.sanaee@… |
| L108 | bits: split/unify GENMASK\*() | PORTABLE★ | `include/linux/bits.h` 核心头 | .../20250609-consolidate-genmask-v2-2-… |
| L187 | fs/dax: Fix ZONE_DEVICE page refcounts | PORTABLE★ | `fs/dax.c` + `mm/` core | .../67055d772e…apopple@nvidia.com |
| L51 | dma/pool: DMA_DIRECT_REMAP decrypted | PORTABLE★ | `kernel/dma/pool.c` | .../20250811181759.998805-1-sdonthineni@… |
| L230 | kcov: unique cover/edge/cmp modes | PORTABLE★ | `kernel/kcov.c`（riscv ARCH_HAS_KCOV）| .../20250110073056.2594638-1-quic_jiangenj@… |
| L122 | KVM: irqfd registration globally unique | PORTABLE | `virt/kvm` + `sched/wait`（riscv KVM）| .../20250522235223.3178519-8-seanjc@… |
| L11 | of/irq: msi-parent check in of_msi_xlate | PORTABLE | `drivers/of/irq.c` | .../20250916091858.257868-1-lpieralisi@… |
| L56 | of/irq: convert of_msi_map_id → of_msi_xlate | PORTABLE | `drivers/of/irq.c` | .../20250805133443.936955-1-lpieralisi@… |
| L113 | PCI/MSI: size device MSI domain by max vectors | PORTABLE | `drivers/pci/msi/` | .../20250603141801.915305-1-maz@… |
| L109 | PCI/ASPM: disable L1 before L1 PM substates | PORTABLE(low) | `drivers/pci/pcie/aspm.c` | .../20250606015738.2724220-1-macpaul.lin@… |
| L2 | cpu: fix hard lockup from printk in sched ctx | PORTABLE | `kernel/` printk/cpu | .../20250924123247.807-1-shechenglong@… |
| L81 | kernel/cpu: freeze_secondary_cpus primary domain | PORTABLE | `kernel/cpu.c` | .../20250630082103.829352-1-shashank…@sony |
| L128 | list_add corruption during CPU hotplug | PORTABLE | `kernel/cpu.c` hotplug | .../20250521064238.3173224-1-kuyo.chang@… |
| L149 | exit: skip panic in do_exit() during poweroff | PORTABLE | `kernel/exit.c` | .../20250410143937.1829272-1-Tze-nan.Wu@… |
| L70 | rcu: fix delayed execution of hurry callbacks | PORTABLE | `kernel/rcu/` | .../20250717055341.246468-1-Tze-nan.Wu@… |
| L86 | tracing: fix irq tracking on NMIs | PORTABLE | `kernel/trace/` | .../20250625120823.60600-1-gmonaco@… |
| L118 | stop_machine: fix migrate_swap vs balance_push | PORTABLE | `kernel/stop_machine.c`/`sched` | .../20250529084614.885184-1-kuyo.chang@… |
| L115 | sched/core: fix migrate_swap vs hotplug | PORTABLE | `kernel/sched/core.c` | .../20250602072242.1839605-1-kuyo.chang@… |
| L55 | sched/deadline: DL server activated message | PORTABLE | `kernel/sched/deadline.c` | .../20250805155347.1693676-1-kuyo.chang@… |
| L78 | sched/deadline: fix dl_server runtime formula | PORTABLE | `kernel/sched/deadline.c` | .../20250702021440.2594736-1-kuyo.chang@… |
| L100 | sched/deadline: fix RT starvation on expiry | PORTABLE | `kernel/sched/deadline.c` | .../20250615131129.954975-1-kuyo.chang@… |
| L102 | sched/deadline: fix fair_server runtime formula | PORTABLE | `kernel/sched/deadline.c` | .../20250614020524.631521-1-kuyo.chang@… |
| L196 | sched: move PLACE_LAG/RUN_TO_PARITY to sysctl | PORTABLE | `kernel/sched/` | .../20250212053644.14787-1-cpru@amazon.com |
| L157 | genirq/migration: use irqd_get_parent_data() | PORTABLE | `kernel/irq/migration.c` | .../87h634ugig.ffs@tglx |
| L198 | genirq: clear IRQS_PENDING in irq descriptor | PORTABLE | `kernel/irq/` | .../20250211023040.180330-1-bo.ye@… |
| L24 | time: introduce BOOT_TIME_TRACKER (RFC) | PORTABLE(low) | `kernel/time/` | .../20250823044034.189939-1-v-singh1@ti |
| L9 | kbuild: disable CC_HAS_ASM_GOTO_OUTPUT clang<17 | PORTABLE | 顶层 Kconfig/kbuild | .../87frcm9kvv.ffs@tglx |
| L199 | kbuild: rust rustc-min-version support fn | PORTABLE(low) | `scripts/`/kbuild | .../20250210164245.282886-1-ojeda@… |
| L229 | treewide: const qualify ctl_tables | PORTABLE | 通用 sysctl（含 arch）| .../20250110-jag-ctl_table_const-v2-1-… |
| L1 | driver core: fw_devlink don't warn | PORTABLE(low) | `drivers/base/core.c` | .../20250925115924.188257-1-ulf.hansson@… |
| L83 | kmap: fix header include path | PORTABLE(trivial) | `include/linux/` | .../20250627153259.301946-1-aurabindo… |
| L179 | clkdev: mark functions with __printf() | PORTABLE(trivial) | `drivers/clk/clkdev.c` | .../20250312194921.103004-1-andriy… |
| L6 | scripts/make_fit: support initial ramdisk + speedup | PORTABLE(low) | `scripts/make_fit.py` | .../20250919224639.1122848-2-sjg@chromium |
| L200 | scripts/make_fit: print DT name before libfdt err | PORTABLE(low) | `scripts/make_fit.py` | .../20250209-makefit-v1-1-bfe6151e8f0a@… |
| L16 | ALSA compress_offload: 64-bit safe timestamp API | PORTABLE(low) | `sound/core/compress_offload.c`（32/64 ABI）| .../20250905091301.2711705-4-verhaegen@… |
| L17 | char: list_del_init() in misc_deregister() | PORTABLE(low) | `drivers/char/misc.c` | .../20250904063714.28925-2-xion.wang@… |
| L15 | stm class: memdup_user() cleanup | PORTABLE(low) | `drivers/hwtracing/stm/` | .../20250909102512.694203-2-thorsten.blum@… |
| L92 | tpm: sync send() support (ftpm/svsm) | PORTABLE(low) | `drivers/char/tpm/` core | .../20250620130810.99069-5-sgarzare@… |
| L185 | iommufd: set domain->iommufd_hwpt in allocators | PORTABLE(low) | `drivers/iommu/iommufd/` | .../20250305211800.229465-1-nicolinc@… |
| L195 | dm: inline crypto passthrough for striped target | PORTABLE(low) | `drivers/md/dm-*` | .../20250216144224.1702385-2-ed.tsai@… |
| L205 | page_pool: introduce page_pool_get_pp() API | PORTABLE(low) | `net/core/page_pool.c` | .../20250127025734.3406167-2-linyunsheng@… |
| L75 | wireless: use of_reserved_mem_region_to_resource | PORTABLE(low) | `drivers/of` + net | .../20250703183502.2074538-1-robh@… |
| L193 | pstore: directly mapped regions (RFC) | PORTABLE(low) | `fs/pstore/` core（qcom smem 后端 N-A）| .../20250217101706.2104498-5-eugen.hristev@… |
| L80 | crypto/sm2 + lib/mpi reintroduce | PORTABLE(low) | `crypto/` + `lib/mpi/` | .../20250630133934.766646-4-gubowen5@… |
| L153 | crypto/testmgr: fix acomp_req leak | PORTABLE(low) | `crypto/testmgr.c` | .../20250408041647.88489-1-lizhijian@… |
| L64 | fbdev: check fb_add_videomode null-ptr | PORTABLE(low) | `drivers/video/fbdev/core/` | .../20250724032534.1638187-1-chenyuan0y@… |
| L85 | fbdev: remove fb_notify support | PORTABLE(low) | `drivers/video/fbdev/core/` | .../20250625131511.3366522-1-arnd@… |
| L105 | fbdev: fix <linux/export.h> warnings (14) | PORTABLE(low) | `drivers/video/fbdev/` core | .../20250612081738.197826-12-tzimmermann@… |
| L5 | perf sample: fix wrong format specifier | PORTABLE(low) | `tools/perf/` | .../20250922095057.3136-1-liujing@… |
| L173 | perf cpumap: increment refcount for online cpumap | PORTABLE(low) | `tools/perf/` | .../20250318171914.145616-1-irogers@… |
| L178 | perf libunwind: fixup user_regs pointer | PORTABLE(low) | `tools/perf/` | .../20250313033121.758978-1-irogers@… |
| L180 | perf script: fix typo in branch event mask | PORTABLE(low) | `tools/perf/` | .../20250312075636.429127-1-yujie.liu@… |
| L227 | perf sample: make user_regs/intr_regs optional | PORTABLE(low) | `tools/perf/` | .../20250113194345.1537821-1-irogers@… |

### PATTERN

| 行 | 系列 | 判定 | 可移植点 / riscv落点 | web_url |
|---|---|---|---|---|
| L98 | ARM/dma-mapping: invalidate caches on arch_dma_prep_coherent | PATTERN（riscv 多半 ALREADY）| 概念=coherent 分配前清/无效缓存；riscv 落点 `arch/riscv/mm/dma-noncoherent.c`（已有 CMO clean/inval）| .../43a834c8f871…camel@gmail.com |

### N-A 噪声（合并成组，riscv 无可移植信号）

| 组 | 行号（示例）| 判定 | 理由 |
|---|---|---|---|
| **ARM MPAM 硬件驱动 + fs/resctrl**（~35 条）| L10, L25–L33, L36–L47, L213–L224, L235 | N-A | ARM MPAM MSC 硬件（内存分区/QoS 寄存器、msmon、PARTID/PMG）；riscv 无对应 QoS 硬件/resctrl 支持。注：`fs/resctrl` arch-hook（L220）为通用薄层，但整体依赖 ARM MPAM，暂无 riscv 落点。代表 .../20250822153048.2287-*-james.morse@… |
| **arch=arm 专属**（~12 条）| L14(HIGHPTE), L61(kstack_erase arm boot), L152(ARM_SSP_PER_TASK plugin), L167(arm crc-t10dif), L145/L147(arm memremap), L190(arm delay.c), L209(arm32 boot vis), L154(ARM locomo), L97(arch/arm as-instr), L142(arm64 KVM cache flush) | N-A | 落在 `arch/arm[64]`，riscv 无对应或已另有实现 |
| **USB 驱动/gadget/chipidea/dwc3/musb/xhci/ucsi**（~22 条）| L12,L21,L84,L96,L99,L101,L107,L111,L112,L129,L140,L156,L165,L174,L175,L177,L182,L183,L188,L201,L212,L225,L232 | N-A | 单一 USB 设备驱动修复/清理；riscv 仅在用到该驱动时受益，无 arch 信号 |
| **Bluetooth 子系统/驱动**（~9 条）| L22,L73,L76,L77,L89,L155,L172,L226,L234 | N-A | BT 驱动 typo/leak/quirk；无 arch 信号 |
| **staging vc04/vchiq/bcm2835**（~11 条）| L3,L7,L20,L50,L71,L139,L146,L169,L181,L184,L211 | N-A | 树莓派 staging 驱动 |
| **PM/devfreq（SoC）**（~7 条）| L18,L54,L91,L117,L130,L132,L228 | N-A | mtk-cci/sun8i/rockchip/hisilicon/exynos devfreq 驱动 |
| **clocksource/timer（SoC 驱动）**（~6 条）| L48,L62,L72,L79,L114,L131 | N-A | arm_global_timer/exynos_mct/nxp/模块化；SoC 定时器驱动（riscv 用 riscv-timer/SBI） |
| **无线/网卡（mt76/at76/stmmac）**（~6 条）| L53,L141,L161,L164,L192,L194 | N-A | 厂商 wifi/网卡驱动 |
| **i.MX/media/ISI/RKISP1/spi**（~11 条）| L49,L58,L133,L134,L135,L136,L151,L158,L171,L191,L233 | N-A | NXP/rockchip 媒体/SoC 驱动、板级、bug 报告 |
| **hwrng / crypto 硬件驱动**（~3 条）| L82,L148,L202 | N-A | mtk/imx/npcm RNG 驱动 |
| **ALSA 声卡驱动**（~3 条）| L94,L103,L123 | N-A | hda-realtek/usb-audio/atmel 驱动 |
| **其它单一驱动/SoC**（~20 条）| L52(peci),L57(aspeed soc),L65(atmel fb),L68(ste_dma40),L74(EDAC),L87/L168(sun4i dma),L90(sun50i iommu),L116(gpiolib),L121(xilinx ATB),L137/L143(HID),L138(phy-zynqmp),L144(mxser),L150(coresight ETE),L159/L160/L163/L166(dev_err_probe/component),L162(tx2 pmu),L186(imx-irqsteer),L204(ahci pm 14条),L210(hisilicon L3),L231(ahci st) | N-A | 均为具体设备/SoC 驱动，无 arch 可移植信号 |
| **DRM dyndbg（58 条）**| L59 | N-A | 主体为 DRM 驱动 dynamic-debug 适配；`lib/dynamic_debug.c` core 通用但被 DRM 驱动 |
| **hyperv 根分区**（2 条）| L189,L197 | N-A | x86/arm64 Hyper-V 根分区，riscv 无 Hyper-V |
| **固件 blob / boot-wrapper**（~3 条）| L93(mtk scp fw),L127(rpi fw timeout),L131(boot-wrapper) | N-A | 固件/引导包装工具 |
| **x86 perf vendor events / arm64 selftest**（2 条）| L69(Intel TMA),L13(PMCR_EL0 selftest) | N-A | x86 事件表 / arm64 sysreg 自测 |
| **pull-request / linux-next 合并 / 讨论帖 / 空标题**（~15 条）| L19,L60,L63,L67,L106,L119,L120,L124,L125,L170,L172,L176,L206,L207,L208 | N-A | 非补丁（PR/merge notice/问题帖/空 series） |
| **其它 driver 清理**（floppy/fsl 头等）| L23,L95,L126 | N-A | floppy 清理/CROSS_64K 宏移除、fsl_devices.h 头清理 |

> 说明：N-A 组内偶有单文件 `lib/`/`drivers/base` 通用触点（如 dyndbg core、floppy 移除 arch 宏），但整条系列以驱动/子系统为主，无独立 arch 移植价值，故计 N-A。
