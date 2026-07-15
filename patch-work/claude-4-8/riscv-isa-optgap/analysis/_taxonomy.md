# 分类法与四态判定（第四轮：ISA 批准差集 + asm 优化差集）

> 本轮候选 = 两路**源码/规范静态信号**：
> - **①** RVI 已 **ratified/frozen** 的扩展 ∖ 内核已识别集 `riscv_isa_ext[]`(92 项，见 `_baseline_riscv.md §一`)。
> - **②** riscv 回退**通用 C / 纯标量**、而 arm64/x86 有 **ISA 优化汇编**的例程（字符串/内存/校验/crypto）。
>
> 判定语义：**「该缺口是否值得且可行地在 riscv 补上」**。

## 四态 rubric

| 判定 | 含义 | 证据要求 |
|---|---|---|
| **ALREADY** | ① 已在 `riscv_isa_ext[]`/hwprobe；② 已有 arch ISA 优化汇编 | 引 `_baseline_riscv.md` 或源码 `文件:行`（假阳） |
| **PORTABLE** | 主要补**通用层**或直接 `select`（arch 侧仅少量 glue） | 说明通用侧已在树内（如 `fs/resctrl/`），arch 只需接线 |
| **PATTERN** | 需在 `arch/riscv/*` 实现 arch 专属部分 | **给具体 riscv 落点文件** + arm64/x86 对端参照 + 使能 ext |
| **N-A** | 无 OS 语义 / 纯 M 态 / 仍 draft / 无对应需求 | 点名理由（Smrnmi/Smepmp 属 M 态；Svukte 属 draft） |

## ① 判法：ratified ↔ recognized 差集

1. **取差集**：候选 = 已批准/冻结扩展 − §一 的 92 项已识别集。（web 确认 ratified/frozen 状态与批准年份。）
2. **按 OS 相关性归类**：
   - 有**探测 + hwprobe 键 + 子系统集成**语义（perf/QoS/RAS/调试/上下文切换）→ **PATTERN**（给落点）。
   - 通用侧**已在树内、arch 仅接线**（resctrl：`fs/resctrl/` 已在）→ **PORTABLE/PATTERN**。
   - 纯 M 态 / draft / 纯计算无 OS 语义 → **N-A**。
3. **greenfield 度**：这些是热点，**须 web 查 lore/patchwork 是否已有在途 RFC**，并在判定里注明「真缺口但已有在途工作/无人认领」。

## ② 判法：generic-fallback ↔ arch-optimized 差集

某例程记为**缺口**当且仅当：
- (a) riscv **缺** `__HAVE_ARCH_*`（退回 `lib/string.c`/`lib/` 泛型 C），**或** 有 `.S` 但为**纯标量/字节循环**（未用相关 ISA ext）；**且**
- (b) arm64/x86 有 **ISA 优化**对端实现；**且**
- (c) 存在**使能优化的 RV 扩展**（`Zbb orc.b` 用于字节搜索、`Zbc` carry-less、`Zvkg` 用于 GF 乘、`Zvkb/RVV` 用于 crypto）。

三者缺一即非本轮候选（缺 (c) → 无优化手段，可 N-A）。

## ① 对端机制 ↔ riscv 落点 速查表

| 对端机制(arm64/x86) | riscv 扩展 | riscv 落点 | 判定倾向 |
|---|---|---|---|
| RDT / MPAM (resctrl) | **Ssqosid** | cpufeature + `switch_to`(`srmcfg`) + `select ARCH_HAS_CPU_RESCTRL`（通用 `fs/resctrl/` 已在） | PORTABLE/PATTERN |
| LBR / BRBE 分支记录 | **Ssctr/Smctr** | `drivers/perf/` + perf branch-stack + Ssstateen 门 | PATTERN |
| 计数器直读/委派 | **Smcdeleg/Ssccfg** | `drivers/perf/riscv_pmu_*`（S 态免 SBI 陷入） | PATTERN |
| 间接 CSR 访问 | **Smcsrind/Sscsrind** | cpufeature（上两者依赖门；`sireg` 现仅 KVM-AIA） | PATTERN |
| 双重故障 / RAS | **Ssdbltrp/Smdbltrp** | `arch/riscv/kernel/traps.c`/entry + KVM `henvcfg.DTE` | PATTERN |
| HW breakpoint(arm64 `hw_breakpoint.c`) | **Sdtrig** | **新** `arch/riscv/kernel/hw_breakpoint.c`（perf/ptrace/kgdb） | PATTERN |
| 计数器特权过滤 | **Smcntrpmf** | `drivers/perf/riscv_pmu_sbi.c` | PATTERN(低) |
| 可恢复 NMI / M 态 PMP | Smrnmi / Smepmp | —（M 态） | N-A |

## ② 对端机制 ↔ riscv 落点 速查表

| 对端(arm64/x86) | riscv 现状 | riscv 落点 | 使能 ext | 判定倾向 |
|---|---|---|---|---|
| `memcmp` 优化(arm64) | 缺 `__HAVE_ARCH_MEMCMP`→泛型 C | `arch/riscv/lib/memcmp.S`(新) + `asm/string.h` | Zbb `orc.b` | PATTERN（最干净） |
| `memchr` 优化(arm64) | 缺 `__HAVE_ARCH_MEMCHR`→泛型 C | `arch/riscv/lib/memchr.S`(新) + `asm/string.h` | Zbb `orc.b` | PATTERN |
| `strchr/strrchr` 优化 | 有 `.S` 但纯字节循环 | `arch/riscv/lib/strchr.S`/`strrchr.S`(改) | Zbb | PATTERN(中) |
| `memcpy/memset/memmove` | 有 `.S` 但纯标量 | `arch/riscv/lib/`(改) | RVV(向量) | PATTERN(低，in-kernel 向量化有争议) |
| `polyval`(arm64 `polyval-ce`) | 无 | `lib/crypto/riscv/polyval-*.S`(新) | Zvkg（复用 ghash） | PATTERN |
| `NH/Adiantum`(arm64 `nh-neon`) | 无 | `lib/crypto/`/`crypto/` | RVV/Zvkb | PATTERN |
| AES/GHASH/ChaCha/SHA/SM3/SM4 | 已加速 | — | — | **ALREADY（勿报）** |
| SHA-1 / SHA-3 | 废弃 / 无对应 ext | — | — | N-A |

## 判定纪律（与 `_baseline_riscv.md §七` 一致）

1. **①** 判缺口前必在 §一 92 项已识别集内 `grep -w <ext>`；在集内即 ALREADY。
2. **②** 判缺口前必查 `asm/string.h` 的 `__HAVE_ARCH_*` 与 `arch/riscv/lib/`、`lib/crypto/riscv/`、`arch/riscv/crypto/` 现有 `.S`；已有 ISA 优化即 ALREADY。
3. 纯 M 态(Smrnmi/Smepmp)/draft(Svukte)/纯计算无 OS 语义 → N-A 并注明。
4. **resctrl 修正**：Ssqosid 是真缺口（推翻轮3 N-A），须在结论显著标注。
5. ① 候选**必注 greenfield 度**（是否已有在途 RFC）。

## 两路信号 → 子代理 → 输出文件

| 信号路 | 子代理 | 输出 |
|---|---|---|
| ① 特权/RAS/QoS/调试（Ssqosid/Ssdbltrp/Smdbltrp/Sdtrig/state-enable 束） | `isa_priv_ras_qos` | `analysis/isa_priv_ras_qos.md` |
| ① perf/计数器（Ssctr/Smctr、Smcdeleg/Ssccfg、Smcsrind/Sscsrind、Smcntrpmf） | `isa_perf_counters` | `analysis/isa_perf_counters.md` |
| ② 字符串/内存（memcmp/memchr、strchr/strrchr、memcpy/memset/memmove） | `asm_string` | `analysis/asm_string.md` |
| ② crypto（polyval、NH/Adiantum、覆盖对比） | `asm_crypto` | `analysis/asm_crypto.md` |
