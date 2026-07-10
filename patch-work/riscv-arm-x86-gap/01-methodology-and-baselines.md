# 研究方法与固定基线

## 目标

本研究寻找三类可执行贡献：

1. arm64/x86 已实现、RISC-V 可直接接入的稳定架构接口；
2. arm64、x86、RISC-V 之间存在重复实现，可下沉到 generic core 的公共逻辑；
3. 公共接口已经进入 mainline 或 linux-next，但 RISC-V 仍缺后端、测试或 enablement。

不纳入 DTS-only、单一 SoC 寄存器支持、纯规范设想，以及没有 Linux 调用者或补丁边界的功能愿望。

## 固定基线

| 基线 | 提交 | 日期/版本 |
|---|---|---|
| Torvalds mainline | `d96fcfe1b7f94ac742984ae7986b94a116abff1b` | 2026-07-10，Linux 7.2-rc2 |
| linux-next | `bee763d5f341b99cf472afeb508d4988f62a6ca1` | next-20260710 |
| 补丁讨论窗口 | `2025-01-01` 至 `2026-07-10` | Linux ARM、KVM、RISC-V 及相关子系统 |

本地源码树是固定提交的浅克隆。较早历史通过固定 commit 链接、邮件归档和已有研究索引补充核验。

## 三层研究流程

### 1. 静态接口清单

- 比较 `arch/{riscv,arm64,x86}/include/asm` 的函数、宏、类型和同名 header；
- 比较 Kconfig 能力、asm-generic fallback 与架构 override；
- 搜索 generic code 中直接使用 `CONFIG_RISCV`、`CONFIG_ARM64`、`CONFIG_X86` 的条件；
- 对 mainline 与 linux-next 的相关文件做差分，避免把已进入 next 的工作标成未实现。

### 2. 调用链与历史验证

- 从 generic caller 追踪到架构 backend；
- 检查接口是否有隐藏的内存序、异常、NMI、ABI、cacheability 或虚拟化语义；
- 使用 2025-2026 邮件索引识别 active RFC、dormant、rejected 和 unclaimed；
- 将已由 generic fallback 覆盖的能力标为伪差距或测试机会。

### 3. 人工可行性审查

每项候选必须回答：精确修改位置、第一版系列边界、阻塞条件、验证方法、维护者路由。
仅有“arm64/x86 有、RISC-V 没有”的条目不能进入主清单。

## G 分类

- **G0 Shared now：** generic/mainline/next 已覆盖主体，只剩 RISC-V enablement、cleanup 或测试。
- **G1 Direct port：** 已有稳定 generic hook，可直接实现 RISC-V backend。
- **G2 Genericize：** 两个或更多架构重复实现，适合下沉公共 helper 或状态机。
- **G3 Architecture proof：** fallback 可用，但 RISC-V 快路径或语义必须重新证明。
- **G4 Foundation-dependent：** 依赖硬件、固件、UAPI 或另一个未完成基础设施。

## 评分与优先级

六个维度分别 0-5 分：upstream impact、architectural generality、implementation readiness、validation feasibility、hardware independence、maintainer acceptance。

- **P0：24-30 分。** 边界明确、验证可行、无根本依赖。
- **P1：18-23 分，或高分候选仍有一个有界依赖。** 适合中期系列。
- **P2：12-17 分，或候选需要实质架构证明、规范/硬件依赖或测试基础设施。**

优先级不是机械分桶：24 分候选存在有界依赖时可降为 P1，18 分候选需要实质架构证明时可降为 P2；不得仅凭总分忽略阻塞条件。

统一注册表共有 90 项，且每项记录六维分数和总分。

## 状态定义

- **mainline：** RISC-V 工作本身已在固定 mainline；本研究主清单中为 0。
- **next：** RISC-V 主体已进入固定 linux-next，只剩明确后续。
- **active RFC：** 2025-2026 窗口内存在活跃修订或评审。
- **dormant：** 有历史系列，但长期无新版本且未进入固定树。
- **unclaimed：** 未发现对应 RISC-V 实现系列。

公共前置已合入、但 RISC-V 后端仍缺失时，状态仍记为 `unclaimed`，并在候选的基线校准中说明前置提交。

## 候选证据契约

每项主候选包含：

- 固定 mainline/next 状态；
- G0-G4、P0-P2 和六维评分；
- 原始架构和源报告映射；
- 精确路径、函数、宏、Kconfig 或 callback；
- RISC-V 现状和缺口；
- direct port 或 genericize 方案；
- 第一版补丁系列边界；
- 阻塞、验证、维护者与权威来源。

## 去重与反证

127 个领域原始候选经邮件校准和独立审查后，114 个有效源候选发生 24 次跨报告合并，形成 90 个主候选；13 个源候选被删除或降为观察项。典型伪差距包括已经存在的 parallel CPU bring-up、context tracking、IMSIC effective affinity、KVM G-stage batching 和 RISC-V IOMMU 基础 paging driver。

## 限制

- 这是固定快照上的源码和邮件研究，不替代开工前再次检查 maintainer tree。
- 多数候选尚未完成 QEMU、真实硬件、性能或破坏性 hotplug 验证。
- G4/P2 条目只能说明 Linux 接口和依赖边界清楚，不说明规范或硬件已经成熟。
