# 分类统计概览

- 原始补丁: **21687**
- series 版本: **4510** → 去重逻辑系列: **2578**
- 其中 x86/arm 系列: **1187**

## 全体系列架构分布

| 架构 | 系列数 |
|---|---|
| x86 | 979 |
| common | 936 |
| other | 242 |
| riscv | 213 |
| arm | 194 |
| x86+arm | 14 |

## x86/arm 系列 · 层级分布
| 层级 | 系列数 |
|---|---|
| A | 21 |
| B | 206 |
| C | 526 |
| ? | 282 |

## x86/arm 系列 · 类别分布 (含层级)
| 层级 | 类别 | 系列数 |
|---|---|---|
| - | pull-request | 105 |
| ? | misc | 282 |
| A | guest_memfd | 10 |
| A | docs | 4 |
| A | core | 4 |
| A | io-irq-infra | 3 |
| B | reg-access | 45 |
| B | mmu-stage2 | 44 |
| B | pmu | 34 |
| B | selftests | 31 |
| B | mmio-insn | 19 |
| B | pv-hypercall | 16 |
| B | timer-clock | 13 |
| B | debug-introspect | 4 |
| C | confidential | 229 |
| C | nested | 126 |
| C | irqchip-hw | 74 |
| C | vendor-enlighten | 54 |
| C | x86-legacy | 16 |
| C | hw-virt-engine | 11 |
| C | fpu-xstate | 9 |
| C | arch-infra | 7 |
| T | kvm-unit-tests | 47 |
