# 计划：第四轮 `riscv-isa-optgap` —— ISA 批准差集 + asm-generic 优化差集

## Context（背景与动机）

「内核 → RISC-V 贡献点」系列已完成三轮，各用一类信号源：
- 轮1 `kvm-riscv/`、轮2 `riscv-arm-gap/` —— **补丁邮件列表**（在途补丁的可移植性）。
- 轮3 `riscv-contrib-scan/` —— **静态树扫描**（features 矩阵 TODO / Kconfig select 差集 / 代码 TODO）。

用户问「还有其他可靠路径吗」。经 3 个只读子代理验证，确认**两条正交的新可靠路径**（本轮同时做，用户已选此组合）：
- **① ISA 批准差集**（最 riscv 专属、假阳最低）：RVI 已 **ratified/frozen** 的扩展 ∖ 内核已识别集 `riscv_isa_ext[]`(cpufeature.c，~90 个)/hwprobe。"在表=ALREADY，缺=真缺口"是硬事实，信噪比高于轮3 两法。
- **② asm-generic 优化差集**（greenfield 最高、与轮3 Kconfig 差集**零重叠**）：riscv 回退通用 C/标量、而 arm64/x86 有 ISA 优化汇编处。

**本轮问题**：这两条路径目前只有子代理的口头验证摘要，没有落成与前三轮一致的交付物（`analysis/` 明细 + 四态判定 + Top 候选表 + 甄别后 README）。

**目标**：新建 `riscv-isa-optgap/`，复用前三轮方法论对两路候选做深度甄别与四态判定，核实每个 riscv 落点，产出 `analysis/` 与甄别版 README。**范围严格限制在该新目录内**；内核树只读；不碰其他轮目录；**不提交直到用户明确要求**。

## 已只读核实的锚点（本轮候选据此展开）

**① 确认为真缺口（arch/riscv 内零匹配）**：`Ssqosid`、`Ssctr/Smctr`、`Smcdeleg/Ssccfg`、`Smcsrind/Sscsrind`、`Ssdbltrp/Smdbltrp`、`Sdtrig`、`Smcntrpmf`。佐证：`arch/riscv` 无 `hw_breakpoint*`；`arch/riscv/Kconfig` 未接 resctrl。
**① 确认为 ALREADY（须排除，勿报）**：`zacas/zabha/zawrs/smstateen/zicfilp/zicfiss/zimop/svadu` 均在 `cpufeature.c:506-587` 的 `riscv_isa_ext[]`。
**② 确认为真缺口**：`arch/riscv/include/asm/string.h` 缺 `__HAVE_ARCH_MEMCMP`/`MEMCHR`（→ 退回 `lib/string.c` 泛型 C）；`arch/riscv/lib/strchr.S`/`strrchr.S` 存在但为字节循环（未上 Zbb）；`memcpy/memset/memmove.S` 纯标量。`lib/crypto/riscv/` 无 `polyval`、无 `NH/Adiantum`。
**② 确认为 ALREADY（勿报）**：strlen/strcmp/strncmp/strnlen(Zbb)、`csum.c`(Zbb)、CRC(Zbc `lib/crc/riscv/`)、AES-zvkned、GHASH-zvkg、chacha-zvkb、sha256/512、sm3/sm4。

**重要修正（推翻轮3）**：轮3 基线把 resctrl 判 N-A「无硬件」——错。`Ssqosid`(2024 批准) 即 riscv QoS 硬件，通用 `fs/resctrl/` 已在树内，riscv 仅未 `select ARCH_HAS_CPU_RESCTRL`。`HAVE_HW_BREAKPOINT` 缺口的 ISA 名 = `Sdtrig`。README 须显著标注。

## 四态 rubric（本轮语义：该缺口是否值得且可行地在 riscv 补上）

- **ALREADY** —— ① 已在 `riscv_isa_ext[]`/hwprobe；② 已有 arch 优化汇编。引源码行号为证（假阳）。
- **PORTABLE** —— 主要是补通用层/直接 select（如 resctrl 通用 `fs/resctrl/` 已在，arch 侧仅少量 glue + `select`）。本轮较少。
- **PATTERN** —— 需在 `arch/riscv/*` 实现 arch 专属部分（① cpufeature 探测 + hwprobe 键 + 子系统集成；② arch 汇编例程）。**必须给具体 riscv 落点文件**。本轮主体。
- **N-A** —— 无 OS 语义 / 纯 M 态(Smrnmi/Smepmp) / 仍 draft(Svukte) / 无对应需求。点名理由。

## 目录结构（新建，仿轮3）

```
riscv-isa-optgap/
  analysis/
    _baseline_riscv.md      # 能力基线 + 已识别 ext 集 + 已优化 asm 清单 + 假阳纪律 + resctrl 修正
    _taxonomy.md            # 四态 rubric + ratified↔recognized 判法 + asm 优化判法 + 假阳纪律
    _agent_instructions.md  # 子代理指令模板（读共享上下文→只读核实→四态→写文件→回摘要）
    isa_priv_ras_qos.md     # ① 分片1：Ssqosid(+resctrl 修正/ARCH_HAS_CPU_RESCTRL)、Ssdbltrp/Smdbltrp、Sdtrig(hw_breakpoint.c 全缺)、state-enable 束
    isa_perf_counters.md    # ① 分片2：Ssctr/Smctr(perf branch-stack)、Smcdeleg/Ssccfg(计数器委派)、Smcsrind/Sscsrind(间接 CSR 依赖门)、Smcntrpmf
    asm_string.md           # ② 分片1：memcmp/memchr(Zbb orc.b)、strchr/strrchr(→Zbb)、memcpy/memset/memmove(标量→向量，注争议)
    asm_crypto.md           # ② 分片2：polyval(Zvkg 复用 ghash)、NH/Adiantum(低端无 AES)、crypto 覆盖对比 arm64
  scripts/
    gap_probe.sh            # 小复现脚本：dump 已识别 riscv_isa_ext[] + 列 arch string.h HAVE 宏 + lib/crypto 文件清单
  README.md                 # 甄别版交付物
```

## 执行阶段

### 阶段 A：主代理写 3 份共享上下文 + 复现脚本
`_baseline_riscv.md`（裁剪轮3 基线 + 本轮锚点：已识别 ext 集、已优化 asm 清单、resctrl 修正）、`_taxonomy.md`、`_agent_instructions.md`、`scripts/gap_probe.sh`（把上文只读核实的 grep/ls 命令固化，供"复现"附录）。

### 阶段 B：派 4 个 `general-purpose` 分析子代理（1 波并行）
分片 = `isa_priv_ras_qos` / `isa_perf_counters` / `asm_string` / `asm_crypto`。每个：读 3 份共享上下文 → 到只读内核树核实（① 另可用 web 确认 ratified/frozen 状态；判 ALREADY 前必查 `riscv_isa_ext[]` 与已优化 asm 清单）→ 逐条四态判定（给 `文件:行` 落点）→ 写 `analysis/<name>.md`（<800 行）→ 回 ≤250 字摘要。**不派生下级子代理**。

### 阶段 C：主代理综合成文
汇总 4 份 analysis → 写 `riscv-isa-optgap/README.md`：TL;DR → §1 方法论(两新信号源/为何可靠/四态) → §2 ① ISA 差集总览 → §3 ② asm 差集总览 → §4 Top 候选表(P1/P2/P3；5 列：候选|缺口性质|RISC-V 落点|判定|来源) → §5 四态计数 → §6 结论与路线(近期低风险/中期/明确不追) → §7 重要修正(resctrl/Ssqosid、hw_breakpoint=Sdtrig) → 附录(结构/复现/局限)。

## 子代理分片要点

1. **`isa_priv_ras_qos`**：`Ssqosid`→PATTERN/PORTABLE（通用 `fs/resctrl/` 已在，arch 落点 cpufeature + `switch_to`(`srmcfg` 随任务切换) + `select ARCH_HAS_CPU_RESCTRL`；**显式推翻轮3 N-A**）；`Ssdbltrp/Smdbltrp`→PATTERN（traps/entry + KVM `henvcfg.DTE`）；`Sdtrig`→PATTERN（全新 `arch/riscv/kernel/hw_breakpoint.c`，接 perf/ptrace/kgdb，即 `HAVE_HW_BREAKPOINT`）；state-enable/Ssstateen 束→按覆盖度判(多为低值/部分 ALREADY)。
2. **`isa_perf_counters`**：`Ssctr/Smctr`→PATTERN（perf branch-stack≈LBR/BRBE，CSR 上下文切换 + Ssstateen 门，`drivers/perf/`）；`Smcdeleg/Ssccfg`→PATTERN（S 态直读 HPM 免 SBI 陷入，`drivers/perf/riscv_pmu*`）；`Smcsrind/Sscsrind`→PATTERN（间接 CSR，是前两者依赖门，`sireg` 现仅 KVM-AIA 用）；`Smcntrpmf`→PATTERN（计数器按特权模式过滤）。**注意**：均热点，须 web 查是否已有在途 RFC 并注明 greenfield 度。
3. **`asm_string`**：`memcmp`/`memchr`→PATTERN（`arch/riscv/lib/` 新增 .S，仿 strlen 用 Zbb `orc.b`；`asm/string.h` 补 `__HAVE_ARCH_MEMCMP/MEMCHR`——**最干净**）；`strchr`/`strrchr`→PATTERN（现字节循环，改 Zbb）；`memcpy/memset/memmove`→PATTERN 低（标量→向量，in-kernel 向量化有争议，注 `riscv_v_helpers.c` 现仅 uaccess 用）。
4. **`asm_crypto`**：`polyval`→PATTERN（已具 Zvkg/ghash，复用低，`lib/crypto/riscv/`）；`NH/Adiantum`→PATTERN（适配无 AES 低端 RV）；对比 arm64 crypto 覆盖捞漏，**已做项(AES/GHASH/chacha/sha/sm3/sm4)标 ALREADY 勿报**；SHA-1 废弃/SHA-3 无对应 ext→N-A。

## 验证（完成前自检）

- [ ] 每个 ① 候选：ratified/frozen spec 名（web 确认）+ 确不在 `riscv_isa_ext[]`/hwprobe（`文件:行`）+ 落点已命名。
- [ ] 每个 ② 候选：通用回退已核实（缺 `__HAVE_ARCH_*` 或标量 .S，`文件:行`）+ arm64/x86 优化对端引用 + 使能优化的 RV 扩展(Zbb/Zbc/Zvkg) + 落点文件。
- [ ] **排 ALREADY 假阳**：① 对照已识别 ext 集；② 对照已优化 asm 清单（strlen/strcmp/csum/CRC/AES/GHASH/chacha/sha/sm3/sm4）。
- [ ] draft(Svukte)/纯 M 态(Smrnmi/Smepmp)/纯计算无 OS 语义 → N-A 并注明。
- [ ] resctrl/Ssqosid 修正在 README 显著标注；与前三轮交叉一致（hw_breakpoint 现有 ISA 名 Sdtrig；交叉引用轮3 基线）。
- [ ] ① 热点候选注明「多有在途 RFC、greenfield 度低」。
- [ ] 中文；每文件 <800 行；仅 `riscv-isa-optgap/` 内新建；内核树只读；未提交。

## 约束

- 只在 `riscv-isa-optgap/` 内新建；不碰 `kvm-riscv/`、`riscv-arm-gap/`、`riscv-contrib-scan/`、内核树（只读）。
- 中文成文；提交用 `docs:` 前缀、不加 Co-Authored-By；**仅用户明确要求时** commit/push。
- 子代理只读内核树（① 可 web 查 ratified 状态），不派生下级子代理。
- **② 范围护栏**：聚焦上述 ~5-6 个已验证候选，不穷举所有可能的汇编优化（防发散）；memcpy/memset 向量化标低优先级、不深挖。
