# Issue Brief

Issue ID: demo-riscv-kvm-mmu-kconfig
Title: riscv/kvm: make MMU dependency explicit in Kconfig dependency/help text
Type: low-risk Kconfig consistency fix
Subsystem: RISC-V / KVM
Priority: medium
Confidence target: high

Problem statement:
当前示例议题假设 `CONFIG_RISCV_KVM` 在代码语义上要求 MMU，但 Kconfig 呈现层面对该约束表达不够显式，导致在探索 non-MMU 配置或阅读帮助文本时，容易把它误解为一般性的 RISC-V 虚拟化开关。

Why this is a good demo issue:
- 范围窄
- 不涉及 UAPI/ABI
- 可通过配置/编译检查验证
- 足以演示一轮实现被审查驳回、进入 debug、修复后再审核通过

Desired outcome:
- 让 Kconfig dependency/help text 与实际 host KVM 语义保持一致
- 保持改动最小，只触及 Kconfig/帮助文本
- 产出 patch-ready 材料，但不自动发送
