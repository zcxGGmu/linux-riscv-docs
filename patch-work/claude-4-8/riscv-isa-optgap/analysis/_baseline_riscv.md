# RISC-V 能力基线（第四轮：判 ALREADY / 排假阳 的依据）

> 内核树：`/Users/zq/Desktop/patch-work/linux-riscv`（Linux v7.2.0-rc3，**只读**）。
> 本轮两路候选来自 **①ISA 批准差集**（RVI 已 ratified/frozen 扩展 ∖ 内核已识别集）与 **②asm-generic 优化差集**（riscv 回退通用 C/标量、arm64/x86 有 ISA 优化汇编）。
> 判定任一候选前先对照本基线：**已识别扩展 / 已优化 asm → ALREADY（scan 误报）**。

## 一、内核已识别扩展集 `riscv_isa_ext[]`（判 ①ALREADY 的硬依据，约 98 项）

来源 `arch/riscv/kernel/cpufeature.c`（`__RISCV_ISA_EXT_*` 宏，含 `BUNDLE` 伪扩展；准确清单以 `scripts/gap_probe.sh` 输出为准）。**任一扩展若在此集内即 ALREADY，不得报为缺口**：

```
a c d f h i m q v
smaia smmpm smnpm smstateen ssaia sscofpmf ssnpm sstc
svade svadu svinval svnapot svpbmt svrsw60t59b svvptc
zaamo zabha zacas zalasr zalrsc zawrs ztso
zba zbb zbc zbkb zbkc zbkx zbs
zca zcb zcd zcf zclsd zcmop zilsd
zfa zfbfmin zfh zfhmin
zicbom zicbop zicboz ziccrse zicfilp zicfiss zicntr zicond zicsr zifencei zihintntl zihintpause zihpm zimop
zk zkn zknd zkne zknh zkr zks zksed zksh zkt
zvbb zvbc zve32f zve32x zve64d zve64f zve64x zvfbfmin zvfbfwma zvfh zvfhmin
zvkb zvkg zvkn zvknc zvkng zvkned zvknha zvknhb zvks zvksc zvksed zvksg zvksh zvkt
```

**hwprobe 暴露面**（`arch/riscv/include/uapi/asm/hwprobe.h`）：`RISCV_HWPROBE_KEY_IMA_EXT_0/1`（两张扩展位图）+ `MISALIGNED_*_PERF` + `ZICBOM/ZICBOP/ZICBOZ_BLOCK_SIZE` + 厂商 `VENDOR_EXT_{MIPS,SIFIVE,THEAD}_0`。已识别但**尚未开 hwprobe 键**的扩展本身是次要缺口（用户态暴露），价值低于「内核根本未识别」的缺口。

**已识别的特权/监督态扩展**（勿与本轮缺口混淆）：`smaia/ssaia`(AIA)、`smstateen`(state-enable，注意仅 Sm 侧)、`sscofpmf`(计数溢出采样)、`sstc`(S 态定时器)、`smmpm/smnpm/ssnpm`(指针掩码)。

## 二、②asm 优化：已优化清单（判 ②ALREADY 的硬依据，勿报为缺口）

- **字符串（已上 Zbb）**：`arch/riscv/lib/strlen.S`、`strcmp.S`、`strncmp.S`、`strnlen.S`。
- **校验和/CRC**：`arch/riscv/lib/csum.c`（Zbb）；`lib/crc/riscv/`（Zbc carry-less）。
- **crypto（已加速，全部 ALREADY）**：
  - `lib/crypto/riscv/`：AES(`aes-riscv64-zvkned.S`)、GHASH(`ghash-riscv64-zvkg.S`, **Zvkg**)、ChaCha(`chacha-riscv64-zvkb.S`)、SHA-256(`…zvknha_or_zvknhb-zvkb.S`)、SHA-512(`…zvknhb-zvkb.S`)、SM3(`…zvksh-zvkb.S`)、Poly1305(`poly1305-riscv.pl`)。
  - `arch/riscv/crypto/`：AES(多 zvkned 变体)、SM4(`…zvksed-zvkb.S`)。
- **页/内存**：`clear_page.S`；`memcpy.S`/`memset.S`/`memmove.S` **存在但纯标量**（非 ALREADY——是"有实现但未优化"的 PATTERN 低优先候选）；向量仅用于 uaccess（`riscv_v_helpers.c`/`uaccess_vector.S`）。

## 三、②asm 真缺口（已只读核实）

- **`memcmp` / `memchr`**：`arch/riscv/include/asm/string.h` **无** `__HAVE_ARCH_MEMCMP`/`__HAVE_ARCH_MEMCHR`，`arch/riscv/lib/` 无对应 `.S` → 退回 `lib/string.c` 泛型 C 字节循环。arm64 有（`arch/arm64/include/asm/string.h`），可用 Zbb `orc.b` 仿 `strlen.S` 实现——**最干净**。
- **`strchr` / `strrchr`**：`arch/riscv/lib/strchr.S`/`strrchr.S` 存在但为**纯字节循环**（未上 Zbb）→ 可优化（PATTERN，中）。
- **crypto `polyval`**：`lib/crypto/` 无 riscv polyval；riscv 已具 **Zvkg**（GHASH 已用）+ 现成 `ghash-riscv64-zvkg.S` 可复用 → PATTERN。
- **crypto `NH`/`Adiantum`**：无 riscv 加速；适配**无 AES 的低端 RV**（Adiantum 场景）→ PATTERN。

## 四、①ISA 批准差集：真缺口清单（arch/riscv 内零匹配，已核实）

| 扩展 | 类别 | 内核工作 / 大致落点 | 倾向 |
|---|---|---|---|
| **Ssqosid** | QoS(≈RDT/MPAM) | `srmcfg` 随任务上下文切换 + 接通用 `fs/resctrl/` + `select ARCH_HAS_CPU_RESCTRL`；cpufeature | **PORTABLE/PATTERN** |
| **Ssctr/Smctr** | 分支记录(≈LBR/BRBE) | perf branch-stack + CSR 上下文切换 + Ssstateen 门；`drivers/perf/` | PATTERN |
| **Smcdeleg/Ssccfg** | 计数器委派 | S 态直读 HPM 免 SBI 陷入；`drivers/perf/riscv_pmu*` | PATTERN |
| **Smcsrind/Sscsrind** | 间接 CSR | 上两者依赖门；`sireg` 现仅 KVM-AIA 用；cpufeature | PATTERN |
| **Ssdbltrp/Smdbltrp** | 双陷入 RAS | traps/entry 处理 + KVM `henvcfg.DTE` | PATTERN |
| **Sdtrig** | 硬件断点/观察点 | **全新** `arch/riscv/kernel/hw_breakpoint.c`，接 perf/ptrace/kgdb（即 `HAVE_HW_BREAKPOINT`） | PATTERN |
| **Smcntrpmf** | 计数器按特权模式过滤 | `drivers/perf/riscv_pmu_sbi.c` | PATTERN(低) |

## 五、无 OS 语义 / 纯 M 态 / draft → N-A（不误报为可移植）

- **纯 M 态**：`Smrnmi`(可恢复 NMI，M 态)、`Smepmp`(M 态 PMP 增强) → S 态内核无直接工作。
- **仍 draft/未冻结**：`Svukte` 等 → 未定型不宜实现，N-A（注明"draft"）。
- **纯计算扩展无 OS 语义**：多数 Zb*/Zvk*/Zfa 类算术扩展内核只需 cpufeature 识别（多已在集内）；无上下文/陷入语义者不作独立贡献点。

## 六、重要修正（推翻第三轮 `riscv-contrib-scan` 基线）

- **resctrl/MPAM 曾判 N-A「无硬件」——错**。**`Ssqosid`（2024 已批准）即 RISC-V 的 QoS 硬件**（≈x86 RDT / arm64 MPAM）；通用 `fs/resctrl/` 已在树内，riscv 仅未 `select ARCH_HAS_CPU_RESCTRL` + 未做 `srmcfg` 上下文切换 → **明确高价值可动作缺口，不再是 N-A**。
- **`HAVE_HW_BREAKPOINT` 缺口的 ISA 名 = `Sdtrig`**（sdtrig 调试触发器规范）。轮3 曾记「debug trigger 未接框架」，本轮给出规范名与全新落点 `hw_breakpoint.c`。

## 七、假阳纪律（本轮两路各一条硬规则）

1. **①** 判某扩展为缺口前，**必**在上文 §一 的 `riscv_isa_ext[]` 集内查一遍（`grep -w <ext> cpufeature.c`）；在集内即 ALREADY。
2. **②** 判某例程为缺口前，**必**查 `arch/riscv/include/asm/string.h` 的 `__HAVE_ARCH_*` 与 `arch/riscv/lib/`、`lib/crypto/riscv/`、`arch/riscv/crypto/` 是否已有 `.S`；已有 ISA 优化实现即 ALREADY（strchr/strrchr 例外：有 `.S` 但未上 Zbb，属"可优化"而非 ALREADY）。
