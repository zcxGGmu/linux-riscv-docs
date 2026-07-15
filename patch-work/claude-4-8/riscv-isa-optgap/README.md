# RISC-V 内核贡献点挖掘 · 第四轮：ISA 批准差集 + asm-generic 优化差集

> 系列第四轮。前三轮：`kvm-riscv/`、`riscv-arm-gap/`（**补丁邮件列表**路径）、`riscv-contrib-scan/`（**静态树扫描**路径）。
> 本轮换用**两条正交的新可靠信号源**，对只读内核树 `/Users/zq/Desktop/patch-work/linux-riscv`（Linux **v7.2.0-rc3**）做静态甄别，四态判定 = **ALREADY / PORTABLE / PATTERN / N-A**。
> 明细见 `analysis/`，复现见 `scripts/gap_probe.sh`。

---

## TL;DR

- **两条新路径，产出相反的 greenfield 画像**——这是本轮最核心的结论：
  - **① ISA 批准差集**（RVI 已批准扩展 ∖ 内核已识别的 98 项 `riscv_isa_ext[]`）：**最 RISC-V 专属、假阳为零**，8 个可动作缺口（1 PORTABLE + 7 PATTERN）。**但几乎每一个都已有活跃在途上游系列**（Rivos / Ventana / BayLibre）——贡献姿势是**接力 / 评审 / 测试**，而非从零。
  - **② asm-generic 优化差集**（riscv 回退通用 C/标量、arm64/x86 有 ISA 优化汇编）：单点"光环"低些，但**真正 greenfield**——`memcmp`/`memchr`、`polyval`、`NH/Adiantum` 内核侧**均无在途补丁**，是想**独立落地一个新补丁**的最佳切入。
- **最干净的独立落地点（greenfield，推荐新贡献者）**：`memcmp`+`memchr`（新增 `arch/riscv/lib/*.S`，Zbb `rev8`/`orc.b`，可整段复用现有 `strcmp.S`/`strnlen.S`）；`polyval`（补 `lib/crypto/riscv/gf128hash.h` 三钩子，复用已在树的 `ghash_zvkg`）。
- **最高价值的 ISA 缺口（但需接力在途）**：`Ssqosid`/resctrl（QoS）、`Ssctr/Smctr`（perf 分支记录）、`Sdtrig`（硬件断点）。
- **重要修正（推翻第三轮）**：第三轮把 resctrl/MPAM 判 N-A「无硬件」是**错的**——`Ssqosid`（2024 批准）即 RISC-V 的 QoS 硬件，通用 `fs/resctrl/` 已**整树在内核里**，riscv 独缺一行 `select ARCH_HAS_CPU_RESCTRL`。详见 §7。
- **四态计数**：ALREADY 13 · PORTABLE 1 · **PATTERN 17** · N-A 6（跨两路合计）。

---

## §1 方法论：两条新可靠信号源

### 为什么可靠

| 路径 | 信号 | 为何可靠 | 假阳来源与对策 |
|---|---|---|---|
| **① ISA 批准差集** | RVI 已 ratified/frozen 扩展 ∖ 内核 `riscv_isa_ext[]`(98)/hwprobe | 规范权威、差集客观——"在表=ALREADY，缺=真缺口"是硬事实，信噪比高于轮3 的 Kconfig-select 与代码-TODO 两法 | 纯 M 态(Smrnmi/Smepmp)、draft(Svukte)、纯计算无 OS 语义 → 判 N-A；判缺口前 `grep -w <ext> cpufeature.c` |
| **② asm 优化差集** | riscv 退回通用 C/纯标量、arm64/x86 有 ISA 优化汇编 | 差集可核实（缺 `__HAVE_ARCH_*` 或标量 `.S`）、与轮3 Kconfig 差集**零重叠** | 已上 Zbb/Zvk 的例程（strlen/strcmp/csum/AES/GHASH…）判 ALREADY；缺"使能优化的 RV 扩展"者判 N-A（如 SHA-3） |

### 四态 rubric（本轮语义：该缺口是否值得且可行地在 riscv 补上）

- **ALREADY** — ① 已在 `riscv_isa_ext[]`/hwprobe；② 已有 arch ISA 优化汇编（假阳，引源码行号）。
- **PORTABLE** — 主要补**通用层**或直接 `select`，arch 侧仅少量 glue（本轮仅 Ssqosid）。
- **PATTERN** — 需在 `arch/riscv/*` 实现 arch 专属部分（给具体落点文件 + arm64/x86 对端 + 使能 ext）。本轮主体。
- **N-A** — 无 OS 语义 / 纯 M 态 / draft / 无使能扩展。

判定纪律与两张「对端↔落点速查表」见 `analysis/_taxonomy.md`；判 ALREADY/排假阳的能力基线见 `analysis/_baseline_riscv.md`。

---

## §2 ① ISA 批准差集总览

内核已识别 **98** 项扩展（`riscv_isa_ext[]`，含 `zvkn/zvks` BUNDLE 伪扩展；`scripts/gap_probe.sh` 可复现全表）。已识别的特权/监督态扩展：`smaia/ssaia`(AIA)、`smstateen`、`sscofpmf`、`sstc`、`smmpm/smnpm/ssnpm`(指针掩码)。本轮 7 个 ISA 真缺口在全 `arch/riscv` 树**零匹配**（无假阳）：

| 缺口(扩展) | 类别 | RISC-V 落点 | 判定·greenfield | 在途系列 |
|---|---|---|---|---|
| **Ssqosid** | QoS(≈RDT/MPAM) | `select ARCH_HAS_CPU_RESCTRL` + cpufeature + 新 `asm/resctrl.h`（sched-in 写 `srmcfg`）+ CBQRI 控制器驱动 | **PORTABLE**·在途 | Drew Fustini，RFC v2 **17 补丁**（LKML 2026-02） |
| **Ssctr/Smctr** | 分支记录(≈LBR/BRBE) | 新 `drivers/perf/riscv_ctr.c` + CTR CSR 入 `csr.h` + 解除 `riscv_pmu.c:312` 的 branch-stack 拒绝 | **PATTERN**·在途 | Rajnesh Kanwal v3（2025-05，7 补丁；QEMU/OpenSBI 已合、内核未合） |
| **Sdtrig** | 硬件断点/观察点 | **全新** `arch/riscv/kernel/hw_breakpoint.c`（经 SBI Debug Trigger 接 perf/ptrace/kgdb）+ ptrace regset | **PATTERN**·在途 | Chauhan+Taube 8 补丁（2025-08） |
| **Smcdeleg/Ssccfg** | 计数器委派 | `drivers/perf/riscv_pmu_sbi.c` 重构为「SBI 路 + ISA 委派路」双后端（S 态直起停免 SBI 陷入） | **PATTERN**·在途 | Atish Patra 委派大系列（RFC 00/20→v4/v5） |
| **Ssdbltrp** | 双陷入 RAS | `csr.h` 加 `ENVCFG_DTE`/`SSTATUS_SDT` + `traps.c`/entry 的 SDT 状态机 + KVM（FWFT 底座 `sbi.h:429` **已在树**） | **PATTERN**·在途 | Clément Léger 系列（分步落地中） |
| **Smcsrind/Sscsrind** | 间接 CSR(公共门) | cpufeature + `sireg2..6` 扩展窗口（现 `sireg/siselect` 仅 AIA IMSIC 用） | **PATTERN**·在途 | 随 Atish 委派系列（ratified 2024-02） |
| **Smcntrpmf** | 计数器特权过滤 | `riscv_pmu_sbi.c`（仅委派直配路径受益；SBI 路已覆盖过滤语义） | **PATTERN·低**·在途 | 随 Atish 委派系列 |

外加 **Ssstateen**（PATTERN·低，state-enable 门控用途，`smstateen` 已识别故价值低）。
**N-A**：`Smdbltrp`（M 态双陷入→固件/OpenSBI）、`Smrnmi`（M 态可恢复 NMI）、`Smepmp`（M 态 PMP）。

依赖链（perf 簇核心）：`Sscsrind`（公共门）→ `Smcdeleg/Ssccfg` → `Smcntrpmf`；`Sscsrind + smstateen[54] + Sscofpmf` → `Ssctr`。明细见 `analysis/isa_perf_counters.md` / `analysis/isa_priv_ras_qos.md`。

---

## §3 ② asm-generic 优化差集总览

### 字符串/内存（`analysis/asm_string.md`）

已上 Zbb 者判 ALREADY 勿报：`strlen`/`strcmp`/`strncmp`/`strnlen`（`orc.b`/`rev8`）、`csum`。真缺口：

| 缺口 | 现状(文件:行) | RISC-V 落点 | 使能 ext | 判定·greenfield |
|---|---|---|---|---|
| **memcmp** | 缺 `__HAVE_ARCH_MEMCMP`→退 `lib/string.c:655` 逐字节 C | 新 `arch/riscv/lib/memcmp.S`（抄 `strcmp.S:73-94`）+ 补宏 | **Zbb `rev8`** | **PATTERN·greenfield** ★最干净 |
| **memchr** | 缺 `__HAVE_ARCH_MEMCHR`→退 `lib/string.c:787` 逐字节 C | 新 `arch/riscv/lib/memchr.S`（复用 `strnlen.S`）+ 补宏 | **Zbb `orc.b`** | **PATTERN·greenfield** ★ |
| **strchr/strrchr** | 有 `.S` 但纯字节循环（作者明示留作 Zbb 基线） | 改 `arch/riscv/lib/strchr.S`/`strrchr.S` 加 Zbb 变体 | Zbb | PATTERN·中·greenfield |
| memcpy/memset/memmove | 有 `.S` 但纯标量 | 改 `arch/riscv/lib/*.S`（RVV） | RVV | PATTERN·低·**有争议**（in-kernel 向量化） |

> 落地提示：新增 `memcmp/memchr` 须处理 KASAN 门（仿 arm64 `EXPORT_SYMBOL_NOKASAN` 或置 `#if !KASAN`）+ 提供 `__pi_` PIE 别名。内核侧无在途补丁（仅 GCC `cmpmemsi`、glibc IFUNC 脚手架，均非内核）。

### crypto（`analysis/asm_crypto.md`）

**结构性事实**：本树已 crypto 库化——`polyval`/`nh` 在 `lib/crypto/`（非 `arch/*/crypto/`），GHASH+POLYVAL 统一到 `lib/crypto/gf128hash.c`。已加速者（AES/GHASH/ChaCha/SHA-256/512/SM3/SM4 单块/Poly1305/CRC）判 ALREADY。真缺口：

| 缺口 | 现状 | RISC-V 落点 | 使能 ext | 判定·greenfield |
|---|---|---|---|---|
| **polyval** | `riscv/gf128hash.h` 仅 ghash 钩子、无 polyval 钩子→纯标量 C | 补 `lib/crypto/riscv/gf128hash.h` 三钩子，**复用已在树的 `ghash_zvkg`+转换 helper** | **Zvkg**(+Zvkb) | **PATTERN·greenfield** ★最高性价比 |
| **NH/Adiantum** | 无 `riscv/nh.h`→标量（arm/arm64/x86 三家都有） | 新 `lib/crypto/riscv/{nh.h,nh-riscv64-rvv.S}` | **基线 RVV `V`**（`vwmaccu.vv`↔`umlal`，无需 crypto 扩展） | PATTERN·greenfield（无-AES 低端盘加密） |
| SM4 bulk 模式 | 仅注册单块 cipher，模式经通用模板逐块 | 扩 `sm4-riscv64-glue.c` + bulk `.S` | zvksed | PATTERN·低 |

**N-A**：`SHA-1`（废弃）、`SHA-3/Keccak`（RV 向量无对应 ext=缺使能手段）、`aes-neonbs` 位切片（RV 无-AES 的正解是 Adiantum→NH）。澄清非缺口：CRC-t10dif（`lib/crc/riscv/` 已覆盖，比 arm64 更全）、GCM/CCM（库化后由通用层组合已加速原语）。

---

## §4 Top 候选（分级 · 综合价值 × greenfield × 可行性）

### P1 旗舰

| 候选 | 缺口性质 | RISC-V 落点 | 判定 | 来源 / greenfield |
|---|---|---|---|---|
| **memcmp + memchr** | 缺 `__HAVE_ARCH_*`→逐字节 C；arm64 有 | 新 `arch/riscv/lib/{memcmp,memchr}.S`（Zbb，复用 `strcmp.S`/`strnlen.S`）+ 补宏 | PATTERN | ②·`string.h`/`lib/`·**greenfield**（内核无在途） |
| **polyval** | GHASH 已加速、POLYVAL 掉队；HCTR2 在树 | 补 `lib/crypto/riscv/gf128hash.h` 三钩子，复用 `ghash_zvkg` | PATTERN | ②·`gf128hash.h`·**greenfield** |
| **Ssqosid / resctrl** | 通用 `fs/resctrl/` 整树在，独缺 riscv `select` | `select ARCH_HAS_CPU_RESCTRL` + `srmcfg` sched-in + CBQRI 驱动 | **PORTABLE** | ①·**推翻轮3 N-A**·在途(Fustini 17 补丁) |
| **Ssctr/Smctr** | riscv perf 完全无 branch-stack | 新 `drivers/perf/riscv_ctr.c` + 解除 `riscv_pmu.c:312` | PATTERN | ①·用户价值最高(`perf -b`/AutoFDO)·在途 |

### P2 高价值

| 候选 | 缺口性质 | RISC-V 落点 | 判定 | 来源 / greenfield |
|---|---|---|---|---|
| **Sdtrig** | 硬件断点框架全缺 | 全新 `arch/riscv/kernel/hw_breakpoint.c`（SBI 中介） | PATTERN | ①·arm64 对端 1021 行·在途(8 补丁) |
| **NH/Adiantum** | 无 `nh.h`→标量 | 新 `lib/crypto/riscv/{nh.h,nh-riscv64-rvv.S}` | PATTERN | ②·基线 RVV·**greenfield** |
| **Smcdeleg/Ssccfg** | PMU 全走 SBI 陷入 | `riscv_pmu_sbi.c` 双后端重构 | PATTERN | ①·性能收益明确·在途(Atish) |
| **strchr/strrchr** | 有 `.S` 但字节循环 | 改 `arch/riscv/lib/strchr.S`/`strrchr.S` 加 Zbb | PATTERN·中 | ②·作者预留·**greenfield** |

### P3 机会

| 候选 | 判定 | 说明 |
|---|---|---|
| **Ssdbltrp** | PATTERN | 双陷入 RAS，FWFT 底座已在树，在途(Léger) |
| **Smcsrind/Sscsrind** | PATTERN | 间接 CSR 公共门，独立价值低、依赖价值高 |
| **Smcntrpmf** | PATTERN·低 | SBI 路已覆盖过滤语义，仅委派路径受益 |
| **Ssstateen** | PATTERN·低 | state-enable 门控，`smstateen` 已识别 |
| **SM4 bulk** | PATTERN·低 | 商密、场景细分 |
| **memcpy/memset/memmove** | PATTERN·低 | RVV 化，in-kernel 向量化有争议，长期议题 |

---

## §5 四态计数汇总

| 路径 | ALREADY | PORTABLE | PATTERN | N-A | 可动作(P+P) |
|---|---:|---:|---:|---:|---:|
| ① ISA 批准差集 | 0 | 1 | 7 | 3 | **8** |
| ② asm 优化差集 | 13 | 0 | 10 | 3 | **10** |
| **合计** | **13** | **1** | **17** | **6** | **18** |

> ① PATTERN 7 = perf 簇 4（Ssctr/Smcdeleg/Smcsrind/Smcntrpmf）+ priv 簇 3（Sdtrig/Ssdbltrp/Ssstateen；Ssqosid 计入 PORTABLE）。② ALREADY 13 = 字符串 4 + crypto 9 簇。
> **可动作 18 项中，真 greenfield（内核无在途补丁）仅 6 项**：memcmp、memchr、strchr、strrchr、polyval、NH/Adiantum——全部落在 ②。

---

## §6 结论与贡献路线

1. **想独立落地一个新补丁（greenfield，低风险）→ 走 ②**：
   - 首选 **`memcmp`+`memchr`**：新增两个 `.S`、Zbb 使能、可整段复用 `strcmp.S`/`strnlen.S`，不改现有语义，内核无在途竞品。
   - 次选 **`polyval`**：纯 `lib/crypto` glue，复用已在树的 `ghash_zvkg`，无需改 cpufeature；再次 **`NH/Adiantum`**（基线 RVV）、**strchr/strrchr Zbb**。
2. **想参与高价值 ISA 特性 → 走 ①，但姿势是接力/评审/测试**（几乎都有活跃在途系列）：
   - `Ssqosid/resctrl`（Fustini 17 补丁）、`Ssctr/Smctr`（Kanwal v3）、`Sdtrig`（Chauhan/Taube 8 补丁）、计数器委派（Atish 系列）——贡献动作宜为复审、补虚拟化/内核态待办块、跑测试，而非另起炉灶。
3. **明确不追**：M 态扩展（Smrnmi/Smepmp/Smdbltrp）、SHA-1/SHA-3/aes-neonbs、GCM/CCM 融合、memcpy/memset RVV 化（争议大）。

---

## §7 重要修正：resctrl / Ssqosid（推翻第三轮 N-A）

第三轮 `riscv-contrib-scan` 基线把 resctrl/MPAM 判为 N-A「RISC-V 无对应硬件」——**该结论错误，本轮予以推翻**（已只读核实）：

1. **硬件存在**：`Ssqosid`（QoS Identifiers，v1.0 批准）即 RISC-V 的 QoS 硬件对端（≈x86 RDT / arm64 MPAM），提供 `srmcfg` CSR 承载 RCID+MCID。
2. **通用层已整树在**：`fs/resctrl/`（`rdtgroup.c`/`monitor.c`/`ctrlmondata.c`/`pseudo_lock.c`/`Kconfig`）——从 x86 抽出的**架构无关 resctrl 文件系统**——**已在内核树内**。
3. **别家已接线，唯 riscv 缺**：`ARCH_HAS_CPU_RESCTRL` 在 `arch/Kconfig` 定义、`arch/x86` + `arch/arm64` 均 `select`（arm64 `ARM64_MPAM` `Kconfig:2053-2056` 为先例），**独缺 `arch/riscv`**。`fs/resctrl/Kconfig` 的 `RESCTRL_FS depends on ARCH_HAS_CPU_RESCTRL`——riscv 只要 `select` 即可点亮整套 resctrl ABI。

**结论**：Ssqosid/resctrl 是明确高价值、可动作的缺口，**不再是 N-A**。附带修正：第三轮所记「debug trigger 未接框架」的 `HAVE_HW_BREAKPOINT` 缺口，其 ISA 名即 **`Sdtrig`**，全新落点 `arch/riscv/kernel/hw_breakpoint.c`。

---

## 附录

### A. 目录结构

```
riscv-isa-optgap/
  README.md                      # 本文（甄别版交付物）
  analysis/
    _baseline_riscv.md           # 能力基线：98 项已识别扩展集 + 已优化 asm 清单 + resctrl 修正 + 假阳纪律
    _taxonomy.md                 # 四态 rubric + 两路判法 + 两张对端↔落点速查表
    _agent_instructions.md       # 子代理 6 步模板
    isa_priv_ras_qos.md          # ① Ssqosid/Sdtrig/Ssdbltrp/Ssstateen（含 resctrl 修正详证）
    isa_perf_counters.md         # ① Ssctr/Smctr、Smcdeleg/Ssccfg、Smcsrind/Sscsrind、Smcntrpmf（含依赖链）
    asm_string.md                # ② memcmp/memchr/strchr/strrchr/memcpy/memset/memmove
    asm_crypto.md                # ② polyval/NH/Adiantum + arm64↔riscv crypto 覆盖对比
  scripts/
    gap_probe.sh                 # 只读复现探针（两路信号）
```

### B. 复现

```sh
# 默认 TREE=/Users/zq/Desktop/patch-work/linux-riscv（只读）
bash riscv-isa-optgap/scripts/gap_probe.sh
```
输出：① 内核已识别扩展集 + hwprobe 键 + 目标缺口零匹配校验 + hw_breakpoint/resctrl 缺失校验；② `asm/string.h` 的 `__HAVE_ARCH_*`（缺 MEMCMP/MEMCHR）+ `lib/` 汇编清单 + 已加速 crypto 清单。

### C. 局限与口径

- **① 热点多有在途 RFC**：本轮 ① 候选几乎都有活跃上游系列，greenfield 低——价值真实，但贡献姿势是接力而非首创（每条已注在途主推者）。ratified 状态与在途进度以 **2026-07 / v7.2.0-rc3** 为时点，会随时间变化。
- **② 向量化争议**：`memcpy/memset/memmove` 的 RVV 化在社区存分歧（内核态用 V 的保存/恢复开销），列为低优先长期议题，未深挖。
- **抽样口径**：① 聚焦**有 OS 语义**的批准扩展，未穷举纯计算/仅需 cpufeature 识别的算术扩展；② 聚焦 string/mem + crypto 两簇，未覆盖其他 `lib/`（如 raid6、xor）。
- **与前三轮的关系**：② 与轮3 Kconfig-select 差集**零重叠**（轮3 看不到"有实现但退回泛型/未上 ISA 扩展"）；① 的 `Ssctr`/计数器委派与 `kvm-riscv/` 轮的 PMU 虚拟化、`Sdtrig` 与调试主题**互补**，判定不冲突。
```
