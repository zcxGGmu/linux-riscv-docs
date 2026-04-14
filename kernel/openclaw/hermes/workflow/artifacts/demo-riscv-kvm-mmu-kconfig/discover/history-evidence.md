# History Evidence

## Role
Scout-History

## Objective
为 demo issue 补充“上游是否接受这类修复”的历史语境，确认是否有明显阻塞。

## Inputs
- state/issue-brief.md
- discover/code-evidence.md
- state/keywords.txt

## Actions
- 参考内核邮件列表中对 Kconfig/help text 修复的一般处理习惯，整理此类变更的可接受性判断
- 识别是否存在会让该 issue 升级为高风险议题的典型阻塞信号

## Findings / Results
- 类似“依赖表达更显式”“help text 与实际语义对齐”的 Kconfig 修复，通常属于低风险、维护者易接受的清理类改动
- 这类改动若不触及默认值、可见菜单结构或用户可观察行为的大改动，通常不需要复杂的设计辩护
- 未发现必须扩展为多 patch 系列的迹象；单 patch 处理更符合最小改动原则
- 未发现必须先做运行时修复再做 Kconfig 修复的约束

## Risk signals checked
- existing inflight patch: no evidence in this demo
- prior explicit maintainer rejection: no evidence in this demo
- ABI/UAPI concern: none
- DT concern: none

## Constraint suggestions for planner
- 不要把问题扩展为“重构整个 RISC-V KVM 配置体系”
- 不要顺手修改 defconfig，除非设计中证明它确实受影响
- 变更说明重点放在“让配置语义更准确”，而不是“修复功能 bug”

## Confidence
medium-high (demo reconstruction)

## Decision
PASS

## Next Recommended Step
进入 Planner，输出最小改动路径、测试矩阵和风险清单。
