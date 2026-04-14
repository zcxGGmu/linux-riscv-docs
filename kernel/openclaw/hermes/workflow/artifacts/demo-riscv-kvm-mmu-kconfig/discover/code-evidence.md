# Code Evidence

## Role
Scout-Code

## Objective
确认该 demo issue 是否能被定义为一个窄范围、低风险、可通过配置/编译验证的 Kconfig 一致性问题。

## Inputs
- state/issue-brief.md
- state/keywords.txt
- state/subsystem-paths.txt

## Actions
- 以 Linux 内核常见目录布局为参照，检查 `arch/riscv/kvm/` 与 RISC-V Kconfig 层的关系
- 以“host KVM 需要 MMU”这一架构语义为前提，整理与配置呈现相关的文件级证据
- 标记只适合做帮助文本/依赖约束修复，不适合扩展为运行时逻辑改造

## Findings / Results
- 目标文件可聚焦为：`arch/riscv/kvm/Kconfig`
- 相关上游语义背景位于：
  - `arch/riscv/kvm/` 下 host KVM 代码组织
  - `arch/riscv/Kconfig` 中 RISC-V 平台能力相关约束
- 从工程语义看，host KVM 在 RISC-V 上依赖 MMU 是合理且稳定的前提；因此如果 Kconfig 依赖表达或帮助文本未显式体现，就属于“呈现层与实现前提不一致”问题
- 这是一个适合做最小修复的议题，因为：
  1. 只需触及 Kconfig 文本/依赖
  2. 不需要修改运行时代码
  3. 可以通过 `olddefconfig`/`allnoconfig` 风格的配置验证和架构编译检查评估结果

## Candidate file list
- Primary:
  - `arch/riscv/kvm/Kconfig`
- Reference only:
  - `arch/riscv/Kconfig`
  - `arch/riscv/configs/defconfig`
  - `Documentation/virt/kvm/`

## Scope boundary
- In scope:
  - `CONFIG_RISCV_KVM` 依赖表达
  - `CONFIG_RISCV_KVM` help text
- Out of scope:
  - KVM runtime logic
  - SBI / AIA / IRQCHIP feature support
  - 用户空间 API
  - 广泛文档重写

## Confidence
high

## Decision
PASS

## Next Recommended Step
进入历史/讨论探索，确认类似 Kconfig 澄清修复在上游是否通常可接受，以及是否存在已有讨论/在途 patch。
