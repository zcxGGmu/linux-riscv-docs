# ②asm-generic 优化差集 —— 字符串/内存簇

> 分片：`asm_string`（第四轮 riscv-isa-optgap）
> 内核树（只读）：`/Users/zq/Desktop/patch-work/linux-riscv`（Linux v7.2.0-rc3）
> 判法依据：`_taxonomy.md §②判法`、`_baseline_riscv.md §二/§三/§七`
> 本分片只覆盖 **字符串/内存例程**（crypto 归 `asm_crypto` 分片）。

---

## 四态计数小结

| 判定 | 数量 | 例程 |
|---|---|---|
| **ALREADY**（已上 ISA 优化，勿报） | 4 | strlen / strcmp / strncmp / strnlen（均 Zbb `orc.b`/`rev8`） |
| **PORTABLE** | 0 | —（本簇无"仅接通用层"型缺口） |
| **PATTERN**（arch 侧需实现） | 7 | **memcmp**·**memchr**（新增，最干净）；strchr·strrchr（改 Zbb，中）；memcpy·memset·memmove（RVV，低/有争议） |
| **N-A** | 0 | —（本簇候选均有使能 ext，无纯 draft/M 态项） |

**PATTERN 三档优先级**：
- **高（最干净）**：`memcmp`、`memchr` —— 缺 `__HAVE_ARCH_*` 退回泛型 C，新增 `.S` 即可，Zbb 使能，无副作用，无在途内核补丁（greenfield）。
- **中**：`strchr`、`strrchr` —— 已有 `.S` 但纯字节循环；原作者（Feng Jiang, v7 ~2026-01）明言「留作未来 Zbb 优化的基线」。
- **低（有争议，不深挖）**：`memcpy`、`memset`、`memmove` —— 纯标量；RVV 向量化在内核态需 `kernel_vector_begin/end`，开销与收益争议大。

---

## 一、只读核实证据链（判定前置）

### 1.1 `arch/riscv/include/asm/string.h`（缺口铁证）

| 行 | 宏 | 例程 |
|---|---|---|
| 12 | `__HAVE_ARCH_MEMSET` | memset（有 `.S`） |
| 15 | `__HAVE_ARCH_MEMCPY` | memcpy（有 `.S`） |
| 18 | `__HAVE_ARCH_MEMMOVE` | memmove（有 `.S`） |
| 23–39 | `__HAVE_ARCH_STRCMP/STRLEN/STRNCMP/STRNLEN/STRCHR/STRRCHR`（`#if !KASAN` 内） | str* 六项 |
| **—** | **无 `__HAVE_ARCH_MEMCMP`** | **memcmp → 退回泛型 C** |
| **—** | **无 `__HAVE_ARCH_MEMCHR`** | **memchr → 退回泛型 C** |

对端 `arch/arm64/include/asm/string.h:27` 有 `__HAVE_ARCH_MEMCMP`、`:30` 有 `__HAVE_ARCH_MEMCHR`。

### 1.2 `arch/riscv/lib/` 目录清单

存在：`memcpy.S memmove.S memset.S strchr.S strcmp.S strlen.S strncmp.S strnlen.S csum.c clear_page.S`
**缺失**：`memcmp.S`、`memchr.S`（对端 `arch/arm64/lib/memcmp.S`、`memchr.S` 均在）。

### 1.3 泛型 C 回退落点（`lib/string.c`）

- `lib/string.c:647` `#ifndef __HAVE_ARCH_MEMCMP` → 泛型逐字节 memcmp（`:655`），`EXPORT_SYMBOL(memcmp)`（`:680`）。
- `lib/string.c:777` `#ifndef __HAVE_ARCH_MEMCHR` → 泛型逐字节 memchr（`:787`），`EXPORT_SYMBOL(memchr)`（`:797`）。
- riscv 二者宏均未定义 → 全内核 memcmp/memchr 调用（如 `arch/riscv/net/bpf_jit_comp64.c:872,882`、`kexec_image.c:30`、`vdso.c:50`、`hibernate.c:120`、`kernel/pi/fdt_early.c:67,72`、`purgatory/purgatory.c:32`）走的都是这份**逐字节 C**。

### 1.4 现有 Zbb 惯用法（可直接复用的模板）

- `strlen.S:11` 用 `__ALTERNATIVE_CFG("nop", "j strlen_zbb", …RISCV_ISA_EXT_ZBB…)` 运行时分派；`:81` `orc.b`（非零字节→0xff、NUL→0x00）；`:84` `not`；`:90` `CZ`（LE 用 `ctz`/BE 用 `clz`）定位首个 NUL 字节。
- `strcmp.S:75` `orc.b` 查 NUL；`:86-87` `rev8` 把词转大端序；`:91-93` `sltu`+`neg`+`ori` **无分支**合成 (±1) 结果 —— **memcmp 的现成模板**。
- `strnlen.S:17` 同款分派；`:101` `orc.b`；`:119/:153` `minu a0,a0,a1` 用 maxlen 夹取 —— **memchr（有界搜索）的现成模板**。

---

## 二、主候选深挖（4 字段 + 落点/使能）

### 候选 1：`memcmp`（PATTERN，最干净）★首推

- **候选**：memcmp（来源：`asm/string.h` 缺 `__HAVE_ARCH_MEMCMP`；`arch/riscv/lib/` 无 `memcmp.S`）。
- **现状**：退回 `lib/string.c:655` 泛型**逐字节** C（`#ifndef` 门 `:647`）。riscv 全树 memcmp 调用者（bpf_jit `comp64.c:872,882`、`kexec_image.c:30`、`purgatory.c:32` 等）均受此拖累。
- **落点**：新增 `arch/riscv/lib/memcmp.S` + `asm/string.h` 补 `__HAVE_ARCH_MEMCMP`+extern + `Makefile` 加 `memcmp.o`。
  - **对端**：`arch/arm64/lib/memcmp.S` —— 词粒度 `ldr`/`cmp`，失配时 `rev`(bswap) 两词后无分支 `cset`/`cneg` 出 (−1/0/1)。
  - **使能 ext**：**Zbb `rev8`**。memcmp 结构比 strcmp 更简单（**无 NUL 处理**），可直接抄 `strcmp.S:73-94` 的 Zbb 主循环：对齐后 `REG_L` 双字比较，`bne` 失配即 `rev8` 两词 + `sltu/neg/ori` 出符号；再叠加 strncmp 式的 `count` 递减（词循环剩余不足一词时转字节尾）。非 Zbb 硬件经 `__ALTERNATIVE_CFG` 回落逐字节标量。
- **判定**：**PATTERN**。三要件齐（缺 `__HAVE_ARCH_*` / arm64 有 / Zbb `rev8` 使能）；新增文件不改现有语义，最干净。
  - **greenfield 度：高**。内核侧 `__HAVE_ARCH_MEMCMP` 未见在途补丁（6.3 的 Zbb 串优化仅含 strcmp/strlen/strncmp）。**GCC** 已有 `cmpmemsi` 展开（标量 Zbb `rev8` + 分支less，见 gcc-patches），**glibc** 2025-10 加了 str*/mem* 的 multiarch/IFUNC **脚手架**（含 memcmp，但 resolver 仍选泛型）——两者均**非内核**，内核 asm 落点仍空白。

### 候选 2：`memchr`（PATTERN，最干净）★次推

- **候选**：memchr（来源：`asm/string.h` 缺 `__HAVE_ARCH_MEMCHR`；`arch/riscv/lib/` 无 `memchr.S`）。
- **现状**：退回 `lib/string.c:787` 泛型逐字节 C（`#ifndef` 门 `:777`）。调用者如 `kernel/pi/fdt_early.c:72`。
- **落点**：新增 `arch/riscv/lib/memchr.S` + `asm/string.h` 补 `__HAVE_ARCH_MEMCHR`+extern + `Makefile` 加 `memchr.o`。
  - **对端**：`arch/arm64/lib/memchr.S` —— SWAR：把目标字符 `mul` 广播成 8 字节，与词 `eor`，再经 `(v-0x01..)&~v&0x80..` 判零字节。
  - **使能 ext**：**Zbb `orc.b`**。riscv 更简：将目标字符按 `memset.S:35-43` 方式广播到整词（`andi 0xff`→`slli 8|`→`slli 16|`→64bit `slli 32|`），每词 `xor` 广播值后用 **`orc.b`+`not`+`ctz`**（即 `strlen.S:81-90` 惯用法）定位首个"命中字节"；因 memchr 有界，套 `strnlen.S` 的 `minu` 夹取与 `add t4,a0,a1` 词边界收尾。非 Zbb 回落字节循环。
- **判定**：**PATTERN**。三要件齐（缺宏 / arm64 有 / Zbb `orc.b`）。结构上是"有界 strnlen + 广播 xor"，`strnlen.S` 几乎可整体复用。
  - **greenfield 度：高**。同 memcmp，内核 `__HAVE_ARCH_MEMCHR` 无在途补丁；glibc 脚手架含 memchr 但仍走泛型。

### 候选 3：`strchr`（PATTERN，中）

- **候选**：strchr（来源：`arch/riscv/lib/strchr.S` 有 `.S` 但纯字节循环）。
- **现状**：`strchr.S:23-31` —— `andi a1,a1,0xff` 后 `lbu`/`beq`/`addi`/`bnez` **逐字节** loop，**无 Zbb、无 `__ALTERNATIVE_CFG` 分派**。Copyright 2025 Feng Jiang（新近合入）。
- **落点**：改 `arch/riscv/lib/strchr.S`（加 `strchr_zbb` 变体 + 分派宏），使能 **Zbb**。
  - **对端**：`arch/arm64/lib/strchr.S`（NEON/SWAR）。
  - **思路**：广播目标字符（同 memchr），每词同时用 `orc.b` 检测**命中字符**与 **NUL**（strchr 无界，遇 NUL 即止），`ctz` 取先到者。可与 memchr 共享广播+orc.b 宏。
- **判定**：**PATTERN（中）**。非 ALREADY（`_baseline §七` 明列 strchr/strrchr 例外："有 `.S` 但未上 Zbb"）。改现有文件、需处理 NUL 与命中双条件，略繁于 memchr。
  - **greenfield 度：高（作者已明示为未来工作）**。Feng Jiang 的 "optimize string functions" 系列（v7，~2026-01）合入 strchr/strrchr 字节版时**明确注明**其"作为未来 Zbb 优化的基线"；同系列 strnlen 已上 `orc.b`，strchr/strrchr 的 Zbb 跟进尚未提交。

### 候选 4：`strrchr`（PATTERN，中）

- **候选**：strrchr（来源：`arch/riscv/lib/strrchr.S` 有 `.S` 但纯字节循环）。
- **现状**：`strrchr.S:23-33` —— `lbu`/`bne`/`mv`/`addi`/`bnez` **逐字节**扫到 NUL，记录最后命中地址；无 Zbb。Copyright 2025 Feng Jiang。
- **落点**：改 `arch/riscv/lib/strrchr.S`（加 Zbb 变体）。对端 `arch/arm64/lib/strrchr.S`。
  - **思路**：strrchr 需扫完整串取**最后**一次命中，Zbb 化收益弱于 strchr（无法提前终止），但仍可词粒度 `orc.b` 并行检测命中/NUL、在含 NUL 词内用 `clz`（反向）取最后命中。
- **判定**：**PATTERN（中）**。同 strchr 归因。
  - **greenfield 度：高**（同候选 3，作者预留）。

### 候选 5–7：`memcpy` / `memset` / `memmove`（PATTERN，低；不深挖）

- **候选**：三者来源 = `arch/riscv/lib/memcpy.S`·`memset.S`·`memmove.S` 有 `.S` 但**纯标量**。
- **现状**：
  - `memcpy.S`（2013）：字/双字对齐搬运 + Duff 展开，纯标量（`:43-76` `REG_L`/`REG_S` 批量），无向量。
  - `memset.S`（2013）：广播后 32×`REG_S`/迭代的 Duff 装置（`:66-99`），纯标量。
  - `memmove.S`（2022 M. Kloos）：`:22` 自注"当前仅支持小端"，前/后向标量搬运，无向量。
- **落点**：改 `arch/riscv/lib/*.S`，使能 **RVV（向量）**。对端 `arch/arm64/lib/{memcpy,memset}.S`（含向量/`dc zva`）。
- **判定**：**PATTERN（低，有争议）**。非 ALREADY（`_baseline §二` 明列"存在但纯标量"）。**不深挖**理由：内核态用 V 需 `kernel_vector_begin/end` 保存/恢复向量上下文，短拷贝开销可能反超收益；当前树内向量**仅** uaccess 用（`arch/riscv/lib/uaccess_vector.S`、`riscv_v_helpers.c`，`Makefile:16,23` `lib-$(CONFIG_RISCV_ISA_V)`）。in-kernel 通用 mem* 向量化在社区存分歧（Matteo Croce 2021 系列走的是 C 重写而非向量）。属长期议题，非本轮首推。

---

## 三、ALREADY 排除（假阳纪律，勿报为缺口）

`_baseline_riscv.md §二` 已列，本分片复核确认为已优化，**不得报**：

| 例程 | 证据（本地树） | ISA |
|---|---|---|
| strlen | `lib/strlen.S:11` 分派 + `:81` `orc.b` + `:90` `CZ` | Zbb |
| strcmp | `lib/strcmp.S:11` 分派 + `:75` `orc.b` + `:86` `rev8` | Zbb |
| strncmp | `asm/string.h:29` 有宏 + `lib/strncmp.S`（Zbb 变体） | Zbb |
| strnlen | `lib/strnlen.S:17` 分派 + `:101` `orc.b` + `:119` `minu` | Zbb |
| csum | `lib/csum.c`（Zbb，`_baseline §二`） | Zbb |
| clear_page | `lib/clear_page.S`（`Makefile:21` gate `ZICBOZ`） | Zicboz |

> 注：strncmp.S 未逐行读取，依 `asm/string.h:29` 的 `__HAVE_ARCH_STRNCMP`（`!KASAN` 门内）+ 基线清单判 ALREADY；如需逐指令核实可补读，但不影响本簇缺口结论。

---

## 四、KASAN / 导出 语义提示（落地时须处理，非缺口本身）

- riscv `asm/string.h` 的 **str* 六项在 `#if !KASAN` 门内**（`:22`、`:43`），memcpy/memset/memmove 则**无条件**定义（`:12-20`）。新增 memcmp/memchr 时须择一：
  1. 仿 arm64 用 `EXPORT_SYMBOL_NOKASAN`（arm64 `lib/memcmp.S:139`、`memchr.S:76`），或
  2. 置于 `#if !KASAN` 门内（KASAN 构建退回受插桩的泛型 C）。
- `Makefile`：memcpy/memset/memmove 为无条件 `lib-y`（`:3-5`）；str* 在 `ifeq ($(CONFIG_KASAN_*),)` 门内（`:6-13`）。memcmp/memchr 的 `.o` 放置须与上面 KASAN 决策一致。
- 命名：现有例程均带 `SYM_FUNC_ALIAS(__pi_*)` PIE 别名（如 `strlen.S:132`）；新增 `.S` 应同样提供 `__pi_memcmp`/`__pi_memchr` 以供 purgatory/EFI-stub 等 nommu 环境使用（arm64 memcmp.S 主体符号即 `__pi_memcmp`）。

---

## 五、结论与最强候选

1. **首推 `memcmp` + `memchr`**（PATTERN，最干净）：缺 `__HAVE_ARCH_*` → 退泛型 C（`string.h` 无宏、`lib/` 无 `.S`、`lib/string.c:647/777` 兜底已证），arm64 均有对端，Zbb `rev8`(memcmp)/`orc.b`(memchr) 使能，`strcmp.S`/`strnlen.S` 提供**可整段复用**的 Zbb 模板。落点：新增 `arch/riscv/lib/{memcmp,memchr}.S` + `asm/string.h` 补两宏 + `Makefile` 两 `.o`。**greenfield：内核侧无在途补丁**（仅 GCC `cmpmemsi`、glibc IFUNC 脚手架，均非内核）。
2. **次选 strchr/strrchr Zbb 化**（PATTERN，中）：原作者 2026-01 明示为"未来 Zbb 优化基线"，改现有 `.S` 加 Zbb 变体即可。
3. **memcpy/memset/memmove RVV 化**（PATTERN，低）：in-kernel 向量化有争议，长期议题，不首推。
4. 本簇**无 PORTABLE、无 N-A、无 ALREADY 假阳误报**（str* 四项已正确归 ALREADY）。

---

### 参考（联网核对，仅辅助 greenfield 判断）

- RISC-V Linux 6.3 Zbb 串函数（strcmp/strlen/strncmp）—— Phoronix。
- GCC `cmpmemsi` 展开（标量 Zbb `rev8` + 分支less memcmp）—— gcc-patches mail-archive。
- glibc 2025-10 RISC-V multiarch/IFUNC 脚手架（含 memchr/memcmp，resolver 仍选泛型）—— sourceware libc-alpha。
- Feng Jiang "riscv: optimize string functions and add kunit tests" v5–v7（strnlen 上 `orc.b`；strchr/strrchr 字节版作为未来 Zbb 基线）—— linux-hardening/lkml mail-archive，v7 约 2026-01-30。
