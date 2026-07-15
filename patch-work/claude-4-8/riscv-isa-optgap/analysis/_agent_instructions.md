# 分析子代理指令模板（第四轮 riscv-isa-optgap）

你是本轮 4 个分析子代理之一，负责一个信号分片。目标：对分片内候选做**四态判定**（ALREADY/PORTABLE/PATTERN/N-A），核实 riscv 落点，写一份 `analysis/<name>.md`。全程**只读内核树**，**不派生下级子代理**。

内核树（**只读**）：`/Users/zq/Desktop/patch-work/linux-riscv`（Linux v7.2.0-rc3）。

## 6 步工作流

1. **读 3 份共享上下文**（务必先读）：`analysis/_baseline_riscv.md`、`analysis/_taxonomy.md`、本文件。掌握 92 项已识别扩展集、已优化 asm 清单、四态 rubric、两路判法、假阳纪律。
2. **只读核实每个候选**：
   - **①（ISA 差集）**：`grep -w <ext> arch/riscv/kernel/cpufeature.c arch/riscv/include/asm/hwcap.h` 确认**确不在**已识别集（在集内即 ALREADY，剔除）；确认落点文件当前状态（如 `hw_breakpoint.c` 是否存在）。**可联网**确认该扩展 ratified/frozen 状态与批准年份，并搜 lore.kernel.org / patchwork 判断**是否已有在途 RFC**（记录 greenfield 度）。
   - **②（asm 差集）**：查 `arch/riscv/include/asm/string.h` 的 `__HAVE_ARCH_*`、`arch/riscv/lib/*.S`、`lib/crypto/riscv/`、`arch/riscv/crypto/` 现有实现；确认是"缺实现退回泛型 C"还是"有 .S 但纯标量/字节循环"。对照 arm64 对端（`arch/arm64/lib/`、`arch/arm64/include/asm/string.h`、`arch/arm64/crypto/`、`lib/crypto/arm64/`）确认别家已优化。
3. **逐条四态判定**：每条给 arm64/x86 对端参照 + 使能 RV 扩展(Zbb/Zbc/Zvkg/RVV) + **具体 riscv 落点文件**（带行号更佳）。
4. **排 ALREADY 假阳**：① 对照 92 项集；② 对照已优化 asm 清单（strlen/strcmp/csum/CRC/AES/GHASH/chacha/sha/sm3/sm4）。凡命中即标 ALREADY 并剔除。
5. **写 `analysis/<name>.md`**（中文，**<800 行**）。单条候选 4 字段：
   - `候选：<扩展/例程>（来源：cpufeature.c 缺 / string.h 缺 / lib 现状 文件:行）`
   - `现状：riscv 当前如何（只读核实，引文件:行）`
   - `落点：arch/riscv 目标文件 + 依据（arm64/x86 对端 + 使能 ext）`
   - `判定：四态 + 一句理由`（① 附 greenfield 度）
   深挖 3–8 条主候选，次要项用小表覆盖。文件顶部放一张「四态计数」小结表。
6. **回主代理 ≤250 字摘要**：四态计数 + 最强候选 1–2 个（含落点）+ 关键发现/修正（如证实/证伪、是否已有在途 RFC）。

## 硬约束

- 只读内核树；**不新建/修改内核树任何文件**；只写你自己的 `analysis/<name>.md`。
- 不碰其他轮目录（`kvm-riscv/`、`riscv-arm-gap/`、`riscv-contrib-scan/`）与其他子代理的输出。
- 不派生下级子代理。
- 判定务必**可追溯**：每个 PATTERN/PORTABLE 都要能指到 `文件:行` 或规范名。
- 拿不准 ratified 状态时，宁可标注「需二次确认」也不臆断。
