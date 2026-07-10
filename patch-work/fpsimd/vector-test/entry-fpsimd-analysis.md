# entry-fpsimd.S 汇编代码深度分析

> **文件路径**: `arch/arm64/kernel/entry-fpsimd.S` (135 行)
> **头文件**: `arch/arm64/include/asm/fpsimdmacros.h` (358 行)
> **许可证**: GPL-2.0-only
> **作者**: Catalin Marinas <catalin.marinas@arm.com>

---

## 目录

1. [概述](#1-概述)
2. [FPSIMD 基础宏](#2-fpsimd-基础宏)
3. [FPSIMD 保存/恢复](#3-fpsimd-保存恢复)
4. [SVE 指令编码](#4-sve-指令编码)
5. [SVE 保存/恢复](#5-sve-保存恢复)
6. [SME 指令编码](#6-sme-指令编码)
7. [SME 保存/恢复](#7-sme-保存恢复)
8. [宏展开示例](#8-宏展开示例)
9. [内存布局](#9-内存布局)
10. [调用流程](#10-调用流程)

---

## 1. 概述

### 1.1 文件组成

```
entry-fpsimd.S (135 行)
│
├── FPSIMD 函数
│   ├── fpsimd_save_state()      保存 FPSIMD 状态
│   └── fpsimd_load_state()      恢复 FPSIMD 状态
│
├── SVE 函数 (CONFIG_ARM64_SVE)
│   ├── sve_save_state()         保存 SVE 状态
│   ├── sve_load_state()         恢复 SVE 状态
│   ├── sve_get_vl()             读取当前 SVE VL
│   ├── sve_set_vq()             设置 SVE VQ
│   └── sve_flush_live()         清空 SVE 寄存器
│
└── SME 函数 (CONFIG_ARM64_SME)
    ├── sme_get_vl()             读取当前 SME VL
    ├── sme_set_vq()             设置 SME VQ
    ├── sme_save_state()        保存 SME 状态 (ZA/ZT)
    └── sme_load_state()        恢复 SME 状态 (ZA/ZT)

fpsimdmacros.h (358 行)
│
├── FPSIMD 宏
│   ├── fpsimd_save              保存 Q0-Q31 + FPSR + FPCR
│   ├── fpsimd_restore           恢复 Q0-Q31 + FPSR + FPCR
│   └── fpsimd_restore_fpcr      优化 FPCR 恢复
│
├── 检查宏
│   ├── _check_general_reg       检查通用寄存器编号
│   ├── _sve_check_zreg          检查 Z 寄存器编号
│   ├── _sve_check_preg          检查 P 寄存器编号
│   └── _sme_check_wv            检查 Wv 寄存器编号
│
├── SVE 指令编码宏
│   ├── _sve_str_v               STR (vector)
│   ├── _sve_ldr_v               LDR (vector)
│   ├── _sve_str_p               STR (predicate)
│   ├── _sve_ldr_p               LDR (predicate)
│   ├── _sve_rdvl                RDVL
│   ├── _sve_rdffr               RDFFR
│   ├── _sve_wrffr               WRFFR
│   └── _sve_pfalse             PFALSE
│
├── SME 指令编码宏
│   ├── _sme_rdsvl               RDSVL
│   ├── _sme_str_zav             STR ZA[Wv, #offset]
│   ├── _sme_ldr_zav             LDR ZA[Wv, #offset]
│   ├── _ldr_zt                  LDR ZT0
│   └── _str_zt                  STR ZT0
│
├── SVE/SME 状态宏
│   ├── sve_load_vq              设置 ZCR_EL1.LEN
│   ├── sme_load_vq              设置 SMCR_EL1.LEN
│   ├── sve_flush_z              清空 Z 寄存器高位
│   ├── sve_flush_p              清空 P 寄存器
│   ├── sve_flush_ffr            清空 FFR
│   ├── sve_save                 保存完整 SVE 状态
│   ├── sve_load                 恢复完整 SVE 状态
│   ├── sme_save_za              保存 ZA 矩阵
│   └── sme_load_za              恢复 ZA 矩阵
│
└── 辅助宏
    └── __for                    宏循环展开
```

### 1.2 寄存器概述

```
ARM64 FP/SIMD 寄存器:

FPSIMD (固定 128-bit):
┌─────────────────────────────────────────────────────────────┐
│  V0-V31:  32 个 128-bit 向量寄存器                          │
│           也称为 Q0-Q31 (128-bit) 或 D0-D31 (64-bit)        │
│                                                             │
│  FPSR:    浮点状态寄存器 (32-bit)                           │
│  FPCR:    浮点控制寄存器 (32-bit)                           │
└─────────────────────────────────────────────────────────────┘

SVE (可变长度):
┌─────────────────────────────────────────────────────────────┐
│  Z0-Z31:  可变长度向量寄存器 (VL 可为 128-2048 bits)        │
│           Zn 的低 128-bit 与 Vn 共享                        │
│                                                             │
│  P0-P15:  谓词寄存器 (每个 16-bit)                          │
│                                                             │
│  FFR:     第一故障寄存器 (16-bit)                            │
│                                                             │
│  ZCR_EL1: 向量长度控制寄存器                                 │
│           LEN 字段控制当前 VL                                │
└─────────────────────────────────────────────────────────────┘

SME (矩阵扩展):
┌─────────────────────────────────────────────────────────────┐
│  ZA:      矩阵乘累加寄存器 (大小取决于 SME VL)              │
│                                                             │
│  ZT0:     矩阵转置寄存器 (SME2, 512-bit)                    │
│                                                             │
│  SVCR:    流程模式控制寄存器                                 │
│           [0] SM (Streaming 模式)                           │
│           [1] ZA (ZA 使能)                                  │
│                                                             │
│  SMCR_EL1: SME 控制寄存器                                   │
│            LEN 字段控制 Streaming VL                         │
└─────────────────────────────────────────────────────────────┘
```

---

## 2. FPSIMD 基础宏

### 2.1 fpsimd_save 宏

```assembly
/* fpsimdmacros.h: 11-32 行 */
.macro fpsimd_save state, tmpnr
    // 保存 Q0-Q31 (每对 16 字节对齐)
    stp q0,  q1,  [\state, #16 * 0]    // Q0, Q1  → offset 0, 16
    stp q2,  q3,  [\state, #16 * 2]    // Q2, Q3  → offset 32, 48
    stp q4,  q5,  [\state, #16 * 4]    // Q4, Q5  → offset 64, 80
    stp q6,  q7,  [\state, #16 * 6]    // Q6, Q7  → offset 96, 112
    stp q8,  q9,  [\state, #16 * 8]    // Q8, Q9  → offset 128, 144
    stp q10, q11, [\state, #16 * 10]   // Q10, Q11 → offset 160, 176
    stp q12, q13, [\state, #16 * 12]   // Q12, Q13 → offset 192, 208
    stp q14, q15, [\state, #16 * 14]   // Q14, Q15 → offset 224, 240
    stp q16, q17, [\state, #16 * 16]   // Q16, Q17 → offset 256, 272
    stp q18, q19, [\state, #16 * 18]   // Q18, Q19 → offset 288, 304
    stp q20, q21, [\state, #16 * 20]   // Q20, Q21 → offset 320, 336
    stp q22, q23, [\state, #16 * 22]   // Q22, Q23 → offset 352, 368
    stp q24, q25, [\state, #16 * 24]   // Q24, Q25 → offset 384, 400
    stp q26, q27, [\state, #16 * 26]   // Q26, Q27 → offset 416, 432
    stp q28, q29, [\state, #16 * 28]   // Q28, Q29 → offset 448, 464
    stp q30, q31, [\state, #16 * 30]!  // Q30, Q31 → offset 480, 496, 更新 state

    // 保存 FPSR (浮点状态寄存器)
    mrs x\tmpnr, fpsr                 // 读取 FPSR 到临时寄存器
    str w\tmpnr, [\state, #16 * 2]    // 存储 FPSR (32-bit)

    // 保存 FPCR (浮点控制寄存器)
    mrs x\tmpnr, fpcr                 // 读取 FPCR
    str w\tmpnr, [\state, #16 * 2 + 4] // 存储 FPCR (32-bit), offset +4
.endm
```

**关键点**：
- `stp` (Store Pair) 一次存储两个 128-bit 寄存器
- `!` 后缀表示回写基址寄存器
- 16 对 stp 指令 = 32 个 Q 寄存器
- 最后的 `!` 使 `state` 指向 Q30 之后的位置

**内存布局**：
```
state → ┌──────────┐
        │    Q0    │ 16 bytes
        ├──────────┤
        │    Q1    │ 16 bytes
        ├──────────┤
        │    Q2    │ 16 bytes
        ├──────────┤
        │    Q3    │ 16 bytes
        ├──────────┤
        │   ...    │
        ├──────────┤
        │   Q30    │ 16 bytes
        ├──────────┤
        │   Q31    │ 16 bytes
        ├──────────┤
        │   FPSR   │ 4 bytes
        ├──────────┤
        │   FPCR   │ 4 bytes
        └──────────┘
```

### 2.2 fpsimd_restore 宏

```assembly
/* fpsimdmacros.h: 47-68 行 */
.macro fpsimd_restore state, tmpnr
    // 恢复 Q0-Q31
    ldp q0,  q1,  [\state, #16 * 0]
    ldp q2,  q3,  [\state, #16 * 2]
    ldp q4,  q5,  [\state, #16 * 4]
    ldp q6,  q7,  [\state, #16 * 6]
    ldp q8,  q9,  [\state, #16 * 8]
    ldp q10, q11, [\state, #16 * 10]
    ldp q12, q13, [\state, #16 * 12]
    ldp q14, q15, [\state, #16 * 14]
    ldp q16, q17, [\state, #16 * 16]
    ldp q18, q19, [\state, #16 * 18]
    ldp q20, q21, [\state, #16 * 20]
    ldp q22, q23, [\state, #16 * 22]
    ldp q24, q25, [\state, #16 * 24]
    ldp q26, q27, [\state, #16 * 26]
    ldp q28, q29, [\state, #16 * 28]
    ldp q30, q31, [\state, #16 * 30]!

    // 恢复 FPSR
    ldr w\tmpnr, [\state, #16 * 2]
    msr fpsr, x\tmpnr

    // 恢复 FPCR (优化版)
    ldr w\tmpnr, [\state, #16 * 2 + 4]
    fpsimd_restore_fpcr x\tmpnr, \state
.endm
```

### 2.3 FPCR 恢复优化

```assembly
/* fpsimdmacros.h: 34-44 行 */
.macro fpsimd_restore_fpcr state, tmp
    /*
     * FPCR 写入可能是自同步的，
     * 如果值未变化则避免恢复
     */
    mrs \tmp, fpcr          // 读取当前 FPCR
    cmp \tmp, \state        // 与要恢复的值比较
    b.eq 9999f              // 相等则跳过写入
    msr fpcr, \state        // 否则写入新值
9999:
.endm
```

**优化原理**：
- 写入系统寄存器 (`msr`) 可能较慢
- 如果值相同，跳过写入可以节省时间
- FPCR 主要用于控制舍入模式、异常处理等，通常不频繁变化

---

## 3. FPSIMD 保存/恢复

### 3.1 fpsimd_save_state 函数

```assembly
/* entry-fpsimd.S: 19-22 行 */
SYM_FUNC_START(fpsimd_save_state)
    fpsimd_save x0, 8          // x0 = fpsimd_state 指针, x8 = 临时寄存器
    ret
SYM_FUNC_END(fpsimd_save_state)
```

**C 调用约定**：
```
C 代码:
struct user_fpsimd_state *state;
fpsimd_save_state(state);

汇编调用:
x0 = state
bl fpsimd_save_state
```

### 3.2 fpsimd_load_state 函数

```assembly
/* entry-fpsimd.S: 29-32 行 */
SYM_FUNC_START(fpsimd_load_state)
    fpsimd_restore x0, 8        // x0 = fpsimd_state 指针, x8 = 临时寄存器
    ret
SYM_FUNC_END(fpsimd_load_state)
```

---

## 4. SVE 指令编码

### 4.1 手动编码的原因

```assembly
/* fpsimdmacros.h: 102-103 行 */
/*
 * SVE 指令编码 (用于不支持 SVE 的汇编器)
 * (binutils 2.28 之前，所有支持内核的 clang 版本都支持 SVE)
 */
```

对于旧版汇编器，需要手动构建指令编码。

### 4.2 STR (vector) 指令

```assembly
/* fpsimdmacros.h: 106-115 行 */
/* STR Z\nz, [X\nxbase, #\offset, MUL VL] */
.macro _sve_str_v nz, nxbase, offset=0
    _sve_check_zreg \nz         // 检查 Z 寄存器编号 (0-31)
    _check_general_reg \nxbase  // 检查基址寄存器
    _check_num (\offset), -0x100, 0xff  // 检查偏移范围
    .inst 0xe5804000            \
        | (\nz)                 \   // Z 寄存器: [4:0]
        | ((\nxbase) << 5)       \   // 基址寄存器: [9:5]
        | (((\offset) & 7) << 10)\   // 偏移 [2:0]: [12:10]
        | (((\offset) & 0x1f8) << 13) // 偏移 [10:3]: [21:13]
.endm
```

**指令格式**：
```
STR Zz, [Xn, #offset, MUL VL]

31  28  23 20   14 13  10 9    5 4    0
────────────────────────────────────
1110 0101 1000 0100 0000 nz  nnn  offset
     E    5    8    4    0

位域分配:
[4:0]   nz       Z 寄存器
[9:5]   nnn      基址寄存器
[12:10] offset   偏移 [2:0]
[21:13] offset   偏移 [10:3]

实际偏移 = offset * VL (向量长度)
```

**示例**：
```assembly
// 保存 Z0 到 [x1], 偏移 -32 * VL
_sve_str_v 0, x1, -32

// 编码结果:
// Z0 = 0, x1 = 1, offset = -32 = 0xe0
// 0xe5804000 | 0 | (1 << 5) | ((-32 & 7) << 10) | ((-32 & 0x1f8) << 13)
// = 0xe5804020 | (4 << 10) | (0xe0 << 13)
// = 0xe5804020 | 0x1000 | 0x70000
// = 0xe5814020
```

### 4.3 LDR (vector) 指令

```assembly
/* fpsimdmacros.h: 118-127 行 */
/* LDR Z\nz, [X\nxbase, #\offset, MUL VL] */
.macro _sve_ldr_v nz, nxbase, offset=0
    _sve_check_zreg \nz
    _check_general_reg \nxbase
    _check_num (\offset), -0x100, 0xff
    .inst 0x85804000            \   // 基础操作码
        | (\nz)                 \
        | ((\nxbase) << 5)       \
        | (((\offset) & 7) << 10)\
        | (((\offset) & 0x1f8) << 13)
.endm
```

**与 STR 的区别**：
- 操作码不同: `0xe5804000` (STR) vs `0x85804000` (LDR)
- 位域布局相同

### 4.4 RDVL 指令

```assembly
/* fpsimdmacros.h: 153-160 行 */
/* RDVL X\nx, #\imm */
.macro _sve_rdvl nx, imm
    _check_general_reg \nx      // 检查目标寄存器
    _check_num (\imm), -0x20, 0x1f  // 检查立即数范围 [-32, 31]
    .inst 0x04bf5000            \   // 基础操作码
        | (\nx)                 \   // 目标寄存器: [4:0]
        | (((\imm) & 0x3f) << 5)    // 立即数: [10:5]
.endm
```

**功能**：
```
RDVL Xd, #imm
Xd = imm * VL (以 bytes 为单位)

常用于计算缓冲区偏移:
例如: RDVL X0, #-34  → X0 = -34 * VL (跳过最后的 Z 寄存器和谓词区)
```

**在 sve_get_vl 中的应用**：
```assembly
/* entry-fpsimd.S: 60-63 行 */
SYM_FUNC_START(sve_get_vl)
    _sve_rdvl 0, 1     // X0 = 1 * VL = 当前向量长度
    ret
SYM_FUNC_END(sve_get_vl)
```

---

## 5. SVE 保存/恢复

### 5.1 sve_load_vq 宏

```assembly
/* fpsimdmacros.h: 269-277 行 */
.macro sve_load_vq xvqminus1, xtmp, xtmp2
    mrs_s    \xtmp, SYS_ZCR_EL1      // 读取当前 ZCR_EL1
    bic      \xtmp2, \xtmp, ZCR_ELx_LEN_MASK  // 清除 LEN 字段
    orr      \xtmp2, \xtmp2, \xvqminus1       // 设置新 LEN
    cmp      \xtmp2, \xtmp          // 检查是否有变化
    b.eq     921f                   // 无变化则跳过
    msr_s    SYS_ZCR_EL1, \xtmp2   // 写入新值 (自同步)
921:
.endm
```

**ZCR_EL1.LEN 字段**：
```
ZCR_EL1 (SVE 向量长度控制寄存器):

31      16 15    8 7      4 3      0
─────────────────────────────────
│        │  │       │ │  │
│  ...   │  │  EI    │ │  │ LEN  │
│        │  │       │ │  │  │    │
└────────┴──┴────────┴──┴──┴───┴──┘

LEN: 当前向量长度量化值 (VQ - 1)
     VL = (VQ) * 128 bits
     例如: LEN = 0 → VL = 128 bits (VQ = 1)
           LEN = 1 → VL = 256 bits (VQ = 2)
           LEN = 7 → VL = 1024 bits (VQ = 8)
```

**自同步特性**：
- 写入 ZCR_EL1.LEN 后，所有后续 SVE 指令使用新的 VL
- 不需要 ISB 指令同步

### 5.2 sve_save 宏

```assembly
/* fpsimdmacros.h: 306-321 行 */
.macro sve_save nxbase, xpfpsr, save_ffr, nxtmp
    // 保存 Z0-Z31
    // nxbase 指向缓冲区末尾，使用负偏移
    _for n, 0, 31, _sve_str_v \n, \nxbase, \n - 34

    // 保存 P0-P15
    _for n, 0, 15, _sve_str_p \n, \nxbase, \n - 16

    // 处理 FFR (第一故障寄存器)
    cbz \save_ffr, 921f          // 如果 save_ffr = 0，跳过
    _sve_rdffr 0                 // 读取 FFR 到 P0
    b 922f
921:
    _sve_pfalse 0                // 将 P0 设为全零 (FFR 的安全值)
922:
    _sve_str_p 0, \nxbase        // 保存 P0 (FFR 或 0)

    _sve_ldr_p 0, \nxbase, -16   // 恢复 P0 原值 (避免破坏 P0)

    // 保存 FPSR 和 FPCR
    mrs x\nxtmp, fpsr
    str w\nxtmp, [\xpfpsr]       // FPSR
    mrs x\nxtmp, fpcr
    str w\nxtmp, [\xpfpsr, #4]   // FPCR
.endm
```

**_for 宏展开**：
```assembly
// _for n, 0, 31, _sve_str_v \n, x0, \n - 34
// 展开后:

_sve_str_v 0,  x0, 0 - 34    // STR Z0, [x0, #-34, MUL VL]
_sve_str_v 1,  x0, 1 - 34    // STR Z1, [x0, #-33, MUL VL]
_sve_str_v 2,  x0, 2 - 34    // STR Z2, [x0, #-32, MUL VL]
...
_sve_str_v 31, x0, 31 - 34   // STR Z31, [x0, #-3, MUL VL]
```

### 5.3 sve_load 宏

```assembly
/* fpsimdmacros.h: 323-335 行 */
.macro sve_load nxbase, xpfpsr, restore_ffr, nxtmp
    // 恢复 Z0-Z31
    _for n, 0, 31, _sve_ldr_v \n, \nxbase, \n - 34

    // 恢复 P0-P15 (或先恢复 FFR)
    cbz \restore_ffr, 921f
    _sve_ldr_p 0, \nxbase        // 先加载 FFR 到 P0
    _sve_wrffr 0                 // 写入 FFR
921:
    _for n, 0, 15, _sve_ldr_p \n, \nxbase, \n - 16

    // 恢复 FPSR 和 FPCR
    ldr w\nxtmp, [\xpfpsr]
    msr fpsr, x\nxtmp
    ldr w\nxtmp, [\xpfpsr, #4]
    msr fpcr, x\nxtmp
.endm
```

### 5.4 sve_save_state 函数

```assembly
/* entry-fpsimd.S: 43-46 行 */
/*
 * 保存 SVE 状态
 * x0 - 指向状态缓冲区的指针
 * x1 - 指向 FPSR 存储的指针
 * x2 - 如果非零则保存 FFR
 */
SYM_FUNC_START(sve_save_state)
    sve_save 0, x1, x2, 3    // x0 作为基址, x3 作为临时寄存器
    ret
SYM_FUNC_END(sve_save_state)
```

### 5.5 sve_load_state 函数

```assembly
/* entry-fpsimd.S: 55-58 行 */
/*
 * 恢复 SVE 状态
 * x0 - 指向状态缓冲区的指针
 * x1 - 指向 FPSR 存储的指针
 * x2 - 如果非零则恢复 FFR
 */
SYM_FUNC_START(sve_load_state)
    sve_load 0, x1, x2, 4    // x0 作为基址, x4 作为临时寄存器
    ret
SYM_FUNC_END(sve_load_state)
```

### 5.6 sve_flush_live 函数

```assembly
/* entry-fpsimd.S: 79-86 行 */
/*
 * 清零所有 SVE 寄存器的高位 (保留低 128-bit)
 * VQ 必须由调用者预先配置
 *
 * x0 = 是否包含 FFR?
 * x1 = VQ - 1
 */
SYM_FUNC_START(sve_flush_live)
    cbz x1, 1f                 // 如果 VQ-1 = 0 (VL=128), 跳过清零 Z
    sve_flush_z                // 清零 Z0-Z31 的高位
1:
    sve_flush_p                // 清零 P0-P15
    tbz x0, #0, 2f             // 如果 x0[0] = 0, 跳过 FFR
    sve_flush_ffr              // 清零 FFR
2:
    ret
SYM_FUNC_END(sve_flush_live)
```

**sve_flush_z 实现**：
```assembly
/* fpsimdmacros.h: 291-298 行 */
/* 保留 Znz 的低 128-bit，清零高位 */
.macro _sve_flush_z nz
    _sve_check_zreg \nz
    mov v\nz\().16b, v\nz\().16b    // 将低 128-bit 复制到整个向量
.endm

.macro sve_flush_z
    _for n, 0, 31, _sve_flush_z \n  // 对所有 Z 寄存器
.endm
```

**原理**：
```
VL = 256 bits (VQ = 2) 时:

清零前 Z0: [AAAA AAAA] [AAAA AAAA]  (每个 A = 64 bits)
           └──128b──┘ └──128b──┘

执行 mov z0.16b, z0.16b 后:
清零后 Z0: [AAAA AAAA] [0000 0000]
           └──128b──┘ └──高位清零──┘

这确保 SVE 状态中的高位不会泄露旧数据
```

---

## 6. SME 指令编码

### 6.1 RDSVL 指令

```assembly
/* fpsimdmacros.h: 186-193 行 */
/* RDSVL X\nx, #\imm */
.macro _sme_rdsvl nx, imm
    _check_general_reg \nx
    _check_num (\imm), -0x20, 0x1f
    .inst 0x04bf5800            \   // SME 版本操作码
        | (\nx)                 \
        | (((\imm) & 0x3f) << 5)
.endm
```

**与 SVE RDVL 的区别**：
- 操作码不同: `0x04bf5000` (SVE) vs `0x04bf5800` (SME)
- SME 版本读取 Streaming VL (SVL)
- SVE 版本读取正常 VL

### 6.2 STR ZA 指令

```assembly
/* fpsimdmacros.h: 199-207 行 */
/* STR ZA[\nw, #\offset], [X\nxbase, #\offset, MUL VL] */
.macro _sme_str_zav nw, nxbase, offset=0
    _sme_check_wv \nw          // 检查 Wv (12-15)
    _check_general_reg \nxbase
    _check_num (\offset), -0x100, 0xff
    .inst 0xe1200000            \
        | (((\nw) & 3) << 13)   \   // Wv[1:0]: [14:13]
        | ((\nxbase) << 5)      \
        | ((\offset) & 7)           // offset[2:0]: [2:0]
.endm
```

**ZA 矩阵结构**：
```
ZA 是一个二维矩阵寄存器:
┌─────────────────────────────────────────────────────────────┐
│  ZA[SVL x SVL] 矩阵                                         │
│                                                             │
│  例如 SVL = 512 bits (64 bytes):                           │
│  ZA = [64 x 64] bytes = 4096 bytes                         │
│                                                             │
│  通过 Wv 寄存器选择存储:                                    │
│    W12 → ZA[0][0:SVL-1]    (第一行)                         │
│    W13 → ZA[1][0:SVL-1]    (第二行)                         │
│    W14 → ZA[2][0:SVL-1]    (第三行)                         │
│    W15 → ZA[3][0:SVL-1]    (第四行)                         │
│                                                             │
│  每个 Wv 存储 SVL/8 bytes                                  │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 6.3 LDR ZT0 指令

```assembly
/* fpsimdmacros.h: 224-232 行 */
/* LDR ZT0, nx */
.macro _ldr_zt nx
    _check_general_reg \nx
    .inst 0xe11f8000     \
        | (\nx << 5)     // 基址寄存器: [9:5]
.endm
```

**ZT0 寄存器**：
```
ZT0 是 SME2 引入的矩阵转置寄存器:
- 固定大小: 512 bits (64 bytes)
- 用于加速矩阵转置操作
- 通过 LDR/STR 指令加载/存储
```

---

## 7. SME 保存/恢复

### 7.1 sme_load_vq 宏

```assembly
/* fpsimdmacros.h: 280-288 行 */
.macro sme_load_vq xvqminus1, xtmp, xtmp2
    mrs_s    \xtmp, SYS_SMCR_EL1      // 读取 SMCR_EL1
    bic      \xtmp2, \xtmp, SMCR_ELx_LEN_MASK  // 清除 LEN
    orr      \xtmp2, \xtmp2, \xvqminus1
    cmp      \xtmp2, \xtmp
    b.eq     921f
    msr_s    SYS_SMCR_EL1, \xtmp2   // 设置 Streaming VL
921:
.endm
```

**SMCR_EL1.LEN 字段**：
```
SMCR_EL1 (SME 控制寄存器):

31      16 15    8 7      4 3      0
─────────────────────────────────
│        │  │       │ │  │
│  ...   │  │  FA64  │ │  │ LEN  │
│        │  │  EZT0  │ │  │  │    │
└────────┴──┴────────┴──┴──┴───┴──┘

LEN: Streaming 向量长度量化值
     SVL = (VQ) * 128 bits

FA64: 全架构模式支持
EZT0: ZT0 使能
```

### 7.2 sme_save_za 宏

```assembly
/* fpsimdmacros.h: 337-346 行 */
.macro sme_save_za nxbase, xvl, nw
    mov w\nw, #0                 // Wv 计数器 = 0

423:
    _sme_str_zav \nw, \nxbase     // 保存 ZA[Wv] 到 [nxbase]
    add x\nxbase, x\nxbase, \xvl  // nxbase += VL
    add x\nw, x\nw, #1            // Wv++
    cmp \xvl, x\nw                // 检查是否完成
    bne 423b                      // 循环直到保存所有行
.endm
```

**循环结构**：
```
假设 SVL = 512 bits (64 bytes):

nxbase → ┌────────────┐
          │ ZA[0]       │ 64 bytes (W12)
          ├────────────┤
          │ ZA[1]       │ 64 bytes (W13)
          ├────────────┤
          │ ZA[2]       │ 64 bytes (W14)
          ├────────────┤
          │ ZA[3]       │ 64 bytes (W15)
          └────────────┘

循环:
  W12 = 0:
    STR ZA[0], [nxbase], #64
    nxbase += 64
    W12++

  W12 = 1:
    STR ZA[1], [nxbase], #64
    nxbase += 64
    W12++

  ...

  W12 = 3:
    STR ZA[3], [nxbase], #64
    nxbase += 64
    W12++

  比较: 64 == 64, 退出循环
```

### 7.3 sme_load_za 宏

```assembly
/* fpsimdmacros.h: 348-357 行 */
.macro sme_load_za nxbase, xvl, nw
    mov w\nw, #0                 // Wv 计数器 = 0

423:
    _sme_ldr_zav \nw, \nxbase     // 从 [nxbase] 加载 ZA[Wv]
    add x\nxbase, x\nxbase, \xvl
    add x\nw, x\nw, #1
    cmp \xvl, x\nw
    bne 423b
.endm
```

### 7.4 sme_save_state 函数

```assembly
/* entry-fpsimd.S: 108-116 行 */
/*
 * 保存 ZA 和 ZT 状态
 * x0 - 指向状态缓冲区的指针
 * x1 - 要保存的 ZT 寄存器数量 (0 或 1)
 */
SYM_FUNC_START(sme_save_state)
    _sme_rdsvl 2, 1         // x2 = VL / 8
    sme_save_za 0, x2, 12   // 保存 ZA, x0 指向末尾, 使用 w12
                            // x0 现在指向 ZA 之后的区域

    cbz x1, 1f              // 如果 x1 = 0, 跳过 ZT
    _str_zt 0               // STR ZT0, [x0]
1:
    ret
SYM_FUNC_END(sme_save_state)
```

### 7.5 sme_load_state 函数

```assembly
/* entry-fpsimd.S: 124-132 行 */
/*
 * 恢复 ZA 和 ZT 状态
 * x0 - 指向状态缓冲区的指针
 * x1 - 要恢复的 ZT 寄存器数量 (0 或 1)
 */
SYM_FUNC_START(sme_load_state)
    _sme_rdsvl 2, 1         // x2 = VL / 8
    sme_load_za 0, x2, 12   // 恢复 ZA, x0 指向末尾, 使用 w12
                            // x0 现在指向 ZA 之后的区域

    cbz x1, 1f              // 如果 x1 = 0, 跳过 ZT
    _ldr_zt 0               // LDR ZT0, [x0]
1:
    ret
SYM_FUNC_END(sme_load_state)
```

---

## 8. 宏展开示例

### 8.1 fpsimd_save 展开示例

```assembly
// 调用:
fpsimd_save x0, 8

// 展开后:
stp q0,  q1,  [x0, #16 * 0]
stp q2,  q3,  [x0, #16 * 2]
stp q4,  q5,  [x0, #16 * 4]
stp q6,  q7,  [x0, #16 * 6]
stp q8,  q9,  [x0, #16 * 8]
stp q10, q11, [x0, #16 * 10]
stp q12, q13, [x0, #16 * 12]
stp q14, q15, [x0, #16 * 14]
stp q16, q17, [x0, #16 * 16]
stp q18, q19, [x0, #16 * 18]
stp q20, q21, [x0, #16 * 20]
stp q22, q23, [x0, #16 * 22]
stp q24, q25, [x0, #16 * 24]
stp q26, q27, [x0, #16 * 26]
stp q28, q29, [x0, #16 * 28]
stp q30, q31, [x0, #16 * 30]!
mrs  x8, fpsr
str  w8, [x0, #16 * 2]
mrs  x8, fpcr
str  w8, [x0, #16 * 2 + 4]
```

### 8.2 sve_save 展开示例 (简化)

```assembly
// 调用 (VL = 256 bits = VQ 2):
sve_save x0, x1, x2, x3

// Z 寄存器保存部分 (简化):
_sve_str_v 0,  x0, -34    // STR Z0, [x0, #-34, MUL VL]
_sve_str_v 1,  x0, -33    // STR Z1, [x0, #-33, MUL VL]
_sve_str_v 2,  x0, -32    // STR Z2, [x0, #-32, MUL VL]
...
_sve_str_v 31, x0, -3     // STR Z31, [x0, #-3, MUL VL]

// P 寄存器保存部分:
_sve_str_p 0,  x0, -16    // STR P0, [x0, #-16, MUL VL]
_sve_str_p 1,  x0, -15    // STR P1, [x0, #-15, MUL VL]
...
_sve_str_p 15, x0, -1     // STR P15, [x0, #-1, MUL VL]

// FFR 保存:
// 如果 x2 != 0:
_sve_rdffr 0              // RDFFR P0.B
_sve_str_p 0,  x0, 0      // STR P0, [x0]
_sve_ldr_p 0,  x0, -16    // 恢复 P0 原值

// FPSR/FPCR 保存:
mrs x3, fpsr
str w3, [x1]              // FPSR
mrs x3, fpcr
str w3, [x1, #4]          // FPCR
```

### 8.3 _for 宏展开机制

```assembly
// 宏定义 (fpsimdmacros.h: 254-266 行):
.macro _for var:req, from:req, to:req, insn:vararg
    .macro _for__body \var:req
        .noaltmacro
        \insn
        .altmacro
    .endm

    .altmacro
    __for \from, \to
    .noaltmacro

    .purgem _for__body
.endm

// 辅助宏 (245-252 行):
.macro __for from:req, to:req
    .if (\from) == (\to)
        _for__body %\from
    .else
        __for %\from, %((\from) + ((\to) - (\from)) / 2)
        __for %((\from) + ((\to) - (\from)) / 2 + 1), %\to
    .endif
.endm

// 展开示例:
// _for n, 0, 3, _sve_str_v \n, x0, \n

// 第一步: __for 0, 3
//   → __for 0, 1  (中点: (0 + (3-0)/2) = 1)
//   → __for 2, 3  (中点 + 1: 1 + 1 = 2)

// 第二步: __for 0, 1
//   → __for 0, 0  → _for__body 0 → _sve_str_v 0, x0, 0
//   → __for 1, 1  → _for__body 1 → _sve_str_v 1, x0, 1

// 第三步: __for 2, 3
//   → __for 2, 2  → _for__body 2 → _sve_str_v 2, x0, 2
//   → __for 3, 3  → _for__body 3 → _sve_str_v 3, x0, 3

// 最终结果:
_sve_str_v 0, x0, 0
_sve_str_v 1, x0, 1
_sve_str_v 2, x0, 2
_sve_str_v 3, x0, 3
```

---

## 9. 内存布局

### 9.1 FPSIMD 状态布局

```c
// struct user_fpsimd_state (在 asm/fpsimd.h 中定义)

struct user_fpsimd_state {
    __uint128_t vregs[32];  // Z0-Z31 (每个 128-bit)
    uint32_t fpsr;          // 浮点状态寄存器
    uint32_t fpcr;          // 浮点控制寄存器
};

// 内存布局:
// offset 0-511:   vregs[0..31] (32 * 16 = 512 bytes)
// offset 512:     fpsr (4 bytes)
// offset 516:     fpcr (4 bytes)
// 总大小: 516 bytes
```

### 9.2 SVE 状态布局

```c
// SVE 状态存储格式 (在 sigcontext.h 中定义)

struct sve_context {
    struct _aarch64_ctx head;
    __u16 vl;                 // 向量长度 (bytes)
    __u16 __reserved[3];
    __u32 flags;

    // 以下偏移基于 VL
    // zregs: 32 * VL bytes
    // zregs + 32 * VL: P0-P15 (16 bytes)
    // zregs + 32 * VL + 16: FFR (16 bytes)
    // fpsr: 4 bytes
    // fpcr: 4 bytes
};

// 内存布局 (假设 VL = 256 bytes):
// offset 0:          vl
// offset 4:          flags
// offset 8-8191:     Z0-Z31 (32 * 256 = 8192 bytes)
// offset 8192-8207:  P0-P15 (16 * 16 = 256 bytes)
// offset 8208-8223:  FFR (16 bytes)
// offset 8224:       FPSR (4 bytes)
// offset 8228:       FPCR (4 bytes)
```

### 9.3 SME 状态布局

```c
// SME 状态包含:

// 1. SVE 状态 (在非 Streaming 模式)
// 2. Streaming SVE 状态 (在 Streaming 模式)
// 3. ZA 矩阵
// 4. ZT0 (如果 SME2)

// ZA 存储格式:
// ZA 是一个 [SVL x SVL] 的矩阵
// 存储为 SVL/4 个向量 (每个向量 4 * SVL bits)

// 示例 (SVL = 512 bits = 64 bytes):
// ZA = 64 x 64 bytes = 4096 bytes
// 存储为 16 个 256-bit 向量 (16 * 32 = 512 bytes)
// 等等... 实际存储格式:
//
// W12 → ZA[0] → [64 bytes]
// W13 → ZA[1] → [64 bytes]
// W14 → ZA[2] → [64 bytes]
// W15 → ZA[3] → [64 bytes]
// 总计: 4 * 64 = 256 bytes

// ZT0 存储 (SME2):
// ZT0 = 512 bits = 64 bytes (固定大小)
```

---

## 10. 调用流程

### 10.1 FPSIMD 保存流程

```
┌─────────────────────────────────────────────────────────────┐
│                  FPSIMD 保存调用链                           │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  C 代码 (fpsimd.c):                                         │
│    fpsimd_save_state(&task->thread.uw.fpsimd_state);        │
│          │                                                  │
│          ▼                                                  │
│  entry-fpsimd.S:                                            │
│    fpsimd_save_state:                                      │
│      fpsimd_save x0, 8                                     │
│        ├── stp q0-q31, [x0, ...]                           │
│        ├── mrs x8, fpsr                                     │
│        ├── str w8, [x0, #512]                              │
│        ├── mrs x8, fpcr                                     │
│        └── str w8, [x0, #516]                              │
│      ret                                                   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 10.2 SVE 保存流程

```
┌─────────────────────────────────────────────────────────────┐
│                    SVE 保存调用链                            │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  C 代码 (fpsimd.c):                                         │
│    sve_save_state(sve_state, &fpsr, true);                 │
│          │                                                  │
│          ▼                                                  │
│  entry-fpsimd.S:                                            │
│    sve_save_state:                                         │
│      sve_save 0, x1, x2, 3                                 │
│        ├── _for n, 0, 31, _sve_str_v n, x0, n-34           │
│        │     └── STR Zn, [x0, #(n-34), MUL VL]             │
│        ├── _for n, 0, 15, _sve_str_p n, x0, n-16           │
│        │     └── STR Pn, [x0, #(n-16), MUL VL]             │
│        ├── cbz x2, skip_ffr                                │
│        │     ├── RDFFR P0                                  │
│        │     └── STR P0, [x0]                             │
│        ├── skip_ffr:                                        │
│        │     └── PFALSE P0                                 │
│        ├── STR P0, [x0]                                    │
│        ├── LDR P0, [x0, #-16, MUL VL]  // 恢复 P0          │
│        ├── MRS x3, FPSR                                    │
│        ├── STR w3, [x1]                                    │
│        ├── MRS x3, FPCR                                    │
│        └── STR w3, [x1, #4]                                │
│      ret                                                   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 10.3 SME 保存流程

```
┌─────────────────────────────────────────────────────────────┐
│                    SME 保存调用链                            │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  C 代码 (fpsimd.c):                                         │
│    sme_save_state(sme_state, sme2);                        │
│          │                                                  │
│          ▼                                                  │
│  entry-fpsimd.S:                                            │
│    sme_save_state:                                         │
│      _sme_rdsvl x2, x1       // x2 = VL / 8                 │
│      sme_save_za x0, x2, x12                                │
│        ├── mov w12, #0                                     │
│        ├── loop:                                           │
│        │     STR ZA[w12], [x0], x2                         │
│        │     ADD x0, x0, x2                                 │
│        │     ADD w12, w12, #1                               │
│        │     CMP x2, w12                                    │
│        │     BNE loop                                      │
│        └──                                                 │
│      CBZ x1, skip_zt                                       │
│      _str_zt x0               // STR ZT0, [x0]              │
│      skip_zt:                                              │
│      ret                                                   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 10.4 VQ 设置流程

```
┌─────────────────────────────────────────────────────────────┐
│              SVE VQ 设置调用链                               │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  C 代码 (fpsimd.c):                                         │
│    sve_set_vq(vq - 1);                                     │
│          │                                                  │
│          ▼                                                  │
│  entry-fpsimd.S:                                            │
│    sve_set_vq:                                              │
│      sve_load_vq x0, x1, x2                                │
│        ├── MRS x1, ZCR_EL1                                 │
│        ├── BIC x2, x1, ZCR_ELx_LEN_MASK                    │
│        ├── ORR x2, x2, x0                                  │
│        ├── CMP x2, x1                                      │
│        ├── B.EQ skip                                       │
│        ├── MSR ZCR_EL1, x2                                 │
│        └── skip:                                           │
│      ret                                                   │
│                                                             │
│  ZCR_EL1.LEN 设置后:                                        │
│    - 所有后续 SVE 指令使用新的 VL                           │
│    - 不需要 ISB 同步                                        │
│    - VL = (LEN + 1) * 128 bits                             │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 总结

entry-fpsimd.S 和 fpsimdmacros.h 提供了 ARM64 内核中 FP/SIMD 状态保存和恢复的底层实现：

### 核心特点

1. **高度优化的汇编代码**
   - 使用 `stp/ldp` 一次操作两个寄存器
   - FPCR 恢复优化：仅当值变化时写入
   - SVE/SME 使用 MUL VL 寻址模式

2. **宏驱动的代码生成**
   - `_for` 宏实现循环展开
   - 手动指令编码支持旧版汇编器
   - 参数化设计提高灵活性

3. **支持多种扩展**
   - FPSIMD: 基础浮点/向量
   - SVE: 可变长度向量
   - SME: 矩阵扩展 (ZA/ZT)

4. **内存布局优化**
   - 负偏移寻址简化缓冲区管理
   - 寄存器分组存储提高缓存效率

5. **安全性考虑**
   - 寄存器编号范围检查
   - FFR 的安全处理 (PFALSE)
   - Z 寄存器高位清零
