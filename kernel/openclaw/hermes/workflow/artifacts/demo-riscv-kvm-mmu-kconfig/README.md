# Demo issue: RISC-V KVM MMU Kconfig consistency

这是一个“示例 issue 工件集”，用于演示多智能体内核工作流如何从探索推进到 patch-ready。

重要说明：
- 该 issue 是为工作流演示而构造的“现实感较强”的样例，不是声称它一定对应当前 Linux 主线中的真实未修复问题。
- 重点在于展示工件、阶段切换、生成-审核-调试-再审核闭环。
- 文件路径和推理风格尽量贴近 Linux 内核/RISC-V/KVM 场景。

本样例的问题定义：
- `CONFIG_RISCV_KVM` 的依赖约束与 help 文本没有把 “host KVM 依赖 MMU” 说清，导致 non-MMU 配置探索时容易误判为可启用项。
- 规划目标是做一个低风险、可验证、可回滚的 Kconfig 一致性修复。
