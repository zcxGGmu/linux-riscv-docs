# ②asm-generic 优化差集 —— crypto 簇（asm_crypto）

> 内核树（**只读**）：`/Users/zq/Desktop/patch-work/linux-riscv`（Linux v7.2.0-rc3）。
> 分片：riscv 回退**通用标量 C**、而 arm64/x86 有 **ISA 优化汇编**的 crypto 例程。
> 判定语义：**「该 crypto 缺口是否值得且可行地在 riscv 补上」**。
> 已加速清单对照 `_baseline_riscv.md §二`（AES/GHASH/ChaCha/SHA-256/512/SM3/SM4/Poly1305/CRC 一律 ALREADY，勿报）。

## 重要结构性发现（先读）

本树已完成 crypto **库化重构**（library-ification）：`polyval`、`nh` 等原语已从 `arch/*/crypto/`
迁入 **`lib/crypto/`**。因此我的候选对端文件位置**与任务书假设不同**：

| 任务书假设位置 | 本树实际位置 |
|---|---|
| `arch/arm64/crypto/polyval-ce-*` | **`lib/crypto/arm64/polyval-ce-core.S`** + 统一到 `lib/crypto/arm64/gf128hash.h` |
| `arch/arm64/crypto/nh-neon-core.S` | **`lib/crypto/arm64/nh-neon-core.S`** + `lib/crypto/arm64/nh.h` |

且 **GHASH 与 POLYVAL 已被统一到 `lib/crypto/gf128hash.c` + 各 arch 的 `gf128hash.h`**（同一套 GF(2¹²⁸) 机制）。
这直接决定了 polyval 缺口的性质（见 §1）。

## 四态计数小结

| 判定 | 数 | 候选 |
|---|---|---|
| **PATTERN** | 3 | **polyval**（HCTR2/GCM-SIV，最强）、**NH/Adiantum**（低端无 AES 盘加密，次强）、SM4 bulk 模式（低） |
| **N-A** | 3 | SHA-1（废弃）、SHA-3/Keccak（无对应 RV 向量 ext）、aes-neonbs 位切片（Adiantum 才是 RV 的无-AES 正解） |
| **ALREADY** | 9 簇 | AES(ECB/CBC/CTS/CTR/XTS)、GHASH、ChaCha、SHA-256、SHA-512、SM3、SM4(单块)、Poly1305、CRC(32/t10dif/64/16)；GCM/CCM 由通用层组合已加速原语 |
| **PORTABLE** | 0 | crypto 无「纯通用层即可」项——均需 arch 汇编 |

**最强候选**：`polyval`（PATTERN）——落点 `lib/crypto/riscv/gf128hash.h`，复用**已在树内**的 `ghash_zvkg` + polyval↔ghash 转换 helper，**复用成本极低**。
**次强候选**：`NH/Adiantum`（PATTERN）——落点新增 `lib/crypto/riscv/nh.h` + `nh-riscv64-rvv.S`，仅需**基线 RVV `V`**（无需任何 crypto 扩展），服务无 Zvkned 低端核。
**greenfield**：polyval、NH 在 riscv **均无在途补丁**（历史向量 crypto 系列只做了 AES/ChaCha/GHASH/SHA-2/SM3/SM4）。

---

## §1 polyval —— 最强候选（PATTERN，高价值 / 低成本）

**候选**：`polyval`（来源：`lib/crypto/riscv/gf128hash.h` **仅定义 ghash 钩子、无 polyval 钩子**；对端 `lib/crypto/arm64/gf128hash.h:24-111` + `lib/crypto/arm64/polyval-ce-core.S`、`lib/crypto/x86/polyval-pclmul-avx.S`）。

**现状**（只读核实）：
- 通用层 `lib/crypto/gf128hash.c` 用弱钩子暴露 polyval 加速点：
  - `polyval_preparekey_arch`（`gf128hash.c:345`，缺则通用 key-power 预计算）
  - `polyval_mul_arch`（`:363`，缺则退 `polyval_mul_generic`，`:166`）
  - `polyval_blocks_arch`（`:378`，缺则退 `polyval_blocks_generic`，`:229` —— 纯标量 GF(2¹²⁸) 位运算）
- **riscv `lib/crypto/riscv/gf128hash.h` 只定义了 `ghash_preparekey_arch`(:19-28) 与 `ghash_blocks_arch`(:30-49)，polyval 三个钩子一个都没有** → riscv 上 **polyval = 100% 通用标量 C**，即便硬件有 Zvkg。
- arm64 `gf128hash.h` 则把 ghash **和** polyval 全部钩子经 pmull 原生实现（`polyval_blocks_pmull`/`polyval_mul_pmull`）。riscv 是 GHASH 已加速、POLYVAL 掉队的**半吊子**状态。

**关键杠杆**：riscv 的 `ghash_blocks_arch`（`gf128hash.h:31-49`）**已经在做 polyval↔ghash 转换再喂给 zvkg**：
```
polyval_acc_to_ghash(acc, ghash_acc);      // gf128hash.c:255
ghash_zvkg(ghash_acc, key->h_raw, data, nblocks);  // ghash-riscv64-zvkg.S:60
ghash_acc_to_polyval(ghash_acc, acc);      // gf128hash.c:263
```
且 `ghash_preparekey_arch` 里用 `ghash_key_to_polyval`（`gf128hash.c:241`）以 polyval 格式存 key。
**转换 helper 与 `ghash_zvkg` 汇编全部已在树内** → 补 polyval 是纯粹「把已有零件接到 polyval 钩子上」。

**落点**：`lib/crypto/riscv/gf128hash.h`（补 `polyval_blocks_arch`/`polyval_mul_arch`/`polyval_preparekey_arch`）。两条实现路线：
- **路线 A（复用 Zvkg，成本最低）**：polyval 钩子里做与现有 ghash 钩子对称的转换 + 调 `ghash_zvkg`。注意 POLYVAL 与 GHASH 的数据块字节序不同（RFC 8452 附录 A），每块需 `vrev8.v`（Zvkb）字节翻转；acc/key 转换 helper 已有。使能 ext = **Zvkg**（+ Zvkb 做字节翻转），**均已在识别集**（`cpufeature.c` zvkg/zvkb）。
- **路线 B（Zvbc `vclmul` 原生，吞吐更高）**：完全对标 arm64 的 pmull——`vclmul.vv`/`vclmulh.vv` 直接算 polyval 域乘，无需转换，配 NUM_H_POWERS 聚合。使能 ext = **Zvbc**（已在识别集）。
  - 语境提示：社区曾争论移除 Zvbc，理由正是「Zvkg 已能高效实现 GHASH」——**路线 A（Zvkg 复用）更贴合 RV 主流意图**，建议作首选，路线 B 备选。

**消费者（证缺口非空谈）**：`crypto/hctr2.c`（HCTR2 宽块保长密码，`:44` `poly_key`、`:86-90` `polyval_init/update/export`）——**在树内、真实**，用于 fscrypt 文件名/磁盘加密；POLYVAL 亦是 AES-GCM-SIV(RFC 8452) 的哈希。加速 polyval 即直接提速 HCTR2。

**判定**：**PATTERN**。基础设施（统一 gf128hash、转换 helper、`ghash_zvkg`）**全部已在 riscv**，是本轮 crypto 复用成本最低、语义最干净的可动作缺口。
**greenfield 度**：**真空档，无在途补丁**——历史 RV 向量 crypto 系列（Heiko Stübner/VRULL、Jerry Shih/SiFive）覆盖 AES/ChaCha/GHASH(Zvkg)/SHA-2/SM3/SM4，**未含 polyval**（web 核实，见文末）。

---

## §2 NH / Adiantum —— 次强候选（PATTERN，低端无-AES 盘加密）

**候选**：`nh`（来源：riscv **无** `lib/crypto/riscv/nh.h`；对端 `lib/crypto/arm64/nh.h` + `lib/crypto/arm64/nh-neon-core.S`，另有 `lib/crypto/arm/nh.h`、`lib/crypto/x86/nh.h`——**arm/arm64/x86 三家都有，riscv 独缺**）。

**现状**（只读核实）：
- 通用层 `lib/crypto/nh.c` 钩子干净：`#ifdef CONFIG_CRYPTO_LIB_NH_ARCH` 则 `#include "nh.h"`（各 arch），否则 `nh_arch()` 返回 false 退标量（`nh.c:20-28`）。
- 标量回退（`nh.c:41-58`）是 **4 pass × 32×32→64 乘累加** 循环——**教科书级可向量化**内核，无任何数据依赖障碍。
- riscv 无 nh.h → NH 走标量。arm64 `nh.h:14-27` 用 `nh_neon` + `nh-neon-core.S` 的 `umlal`（无符号 32×32→64 乘累加长指令）4 pass 并行。

**落点**：新增 `lib/crypto/riscv/nh.h`（`nh_arch` + `nh_mod_init_arch`）+ `lib/crypto/riscv/nh-riscv64-rvv.S`；Kconfig `select CRYPTO_LIB_NH_ARCH`。
**使能 ext = 基线 RVV `V`（或 `Zve32x`/`Zve64x`）**——`vwmaccu.vv`（向量加宽无符号乘累加 32×32→64）**直接镜像 arm64 `umlal`**。
**关键点：不需要任何 vector-crypto 扩展**（Zvkned/Zvkg 等都不需要）。

**为何有价值**：NH 唯一消费者是 **Adiantum**（`crypto/adiantum.c`，另 `crypto/essiv.c` 引用）——XChaCha12 + NH + Poly1305 的宽块保长密码，专为**无硬件 AES 的低端设备**磁盘/文件加密设计（ARM 当年正是为 ARMv7 无 Crypto Ext 设备做的）。RV 对应场景：**有 RVV `V` 但无 Zvkned** 的核——此时 AES-XTS 慢，Adiantum 是更优盘加密选择。riscv 已有 ChaCha(zvkb)/Poly1305(标量)，**NH 是 Adiantum 热路径上唯一未向量化的一环**。补上即让 Adiantum 在 RV 上整链加速。

**判定**：**PATTERN**。基线向量即可、无转换字节序陷阱、对标清晰（`vwmaccu.vv`↔`umlal`）、消费者在树。价值略低于 polyval（Adiantum 场景比 HCTR2 更细分），但实现最直白。
**greenfield 度**：**真空档**——web 核实无 RV NH/Adiantum 向量补丁，NH 加速仅 ARM/arm64/x86 有。

---

## §3 arm64 ↔ riscv crypto 覆盖对比（捞漏网 + 排 ALREADY）

系统对比 `arch/arm64/crypto/` + `lib/crypto/arm64/` vs riscv 全部条目：

| 算法 | arm64 | riscv 现状（文件:行） | 判定 |
|---|---|---|---|
| **polyval** | `lib/crypto/arm64/{gf128hash.h,polyval-ce-core.S}` | 缺 polyval 钩子（`riscv/gf128hash.h` 仅 ghash） | **PATTERN**（§1，最强） |
| **NH** | `lib/crypto/arm64/{nh.h,nh-neon-core.S}` | 无 `riscv/nh.h` → 标量 | **PATTERN**（§2，次强） |
| **SM4 bulk 模式** | `arch/arm64/crypto/sm4-ce-{core,gcm,ccm}` ECB/CBC/CTR/XTS/GCM/CCM 融合 | **仅注册单块 `sm4` cipher**（`sm4-riscv64-glue.c:69-84`，`CRYPTO_ALG_TYPE_CIPHER`）→ 模式经通用模板逐块调用（慢） | **PATTERN（低）** |
| AES ECB/CBC/CTS/CTR/XTS | ✓ | ✓ `aes-riscv64-glue.c:424-494`（zvkned/zvbb/zvkg/zvkb） | **ALREADY** |
| AES-GCM / AES-CCM | 融合 `aes-ce-ccm`、`ghash-ce` | 无融合；由通用 `crypto/{gcm,ccm}.c` 组合 accel `ctr(aes)`+accel `ghash` | **ALREADY**（组合已加速，融合仅边际收益，低价值） |
| **aes-neonbs（位切片）** | `arch/arm64/crypto/aes-neonbs-*`（恒时、无 HW-AES 时的 CTR/XTS） | 无 | **N-A**：RV 无-Zvkned 的正解是 **Adiantum**（→§2 NH），位切片 AES 为大工程且细分 |
| GHASH | `lib/crypto/arm64/ghash-neon-core.S` | ✓ `ghash-riscv64-zvkg.S`（Zvkg） | **ALREADY** |
| ChaCha | `lib/crypto/arm64/chacha-neon-core.S` | ✓ `chacha-riscv64-zvkb.S` | **ALREADY** |
| Poly1305 | `lib/crypto/arm64/poly1305-armv8.pl` | ✓ `poly1305-riscv.pl` | **ALREADY** |
| SHA-256 / SHA-512 | `sha256-ce.S`/`sha512-ce-core.S` | ✓ `sha256-…zvknha_or_zvknhb-zvkb.S`、`sha512-…zvknhb-zvkb.S` | **ALREADY** |
| SM3 | `sm3-ce-core.S`/`sm3-neon-core.S` | ✓ `sm3-riscv64-zvksh-zvkb.S` | **ALREADY** |
| **SHA-1** | `lib/crypto/arm64/sha1-ce-core.S` | 无 | **N-A**（SHA-1 已废弃，不新做加速） |
| **SHA-3 / Keccak** | `lib/crypto/arm64/sha3-ce-core.S` | 无 | **N-A**（RV 向量无 Keccak/SHA-3 对应 ext，无使能手段=缺 (c)） |
| **CRC 簇**（crc32/t10dif/crc64） | `lib/crc/arm64/*`（crc32/t10dif/crc64-neon） | ✓ `lib/crc/riscv/`（clmul 模板 + crc32/**t10dif**/crc64/crc16，Zbc）**比 arm64 更全** | **ALREADY** |

**漏网核查结论**：除 polyval、NH（两大主候选）与 SM4 bulk（低）外，**无其他遗漏加速项**。特别澄清：
- **CRC-T10DIF 不是缺口**——riscv `lib/crc/riscv/crc-t10dif.h` + clmul 模板已覆盖（任务书曾疑此项）。
- **GCM/CCM 不是缺口**——库化后由通用层组合 riscv 已加速的 `ctr(aes)` + `ghash`，功能上已加速；arm64 的融合汇编仅边际吞吐收益，价值低。

### SM4 bulk 模式（PATTERN 低，附注）
riscv 只把 SM4 **单块**原语上了 zvksed（`sm4-riscv64-glue.c` 注册 `CRYPTO_ALG_TYPE_CIPHER`），CBC/CTR/XTS 等经通用模板逐块回调，无批量向量化；arm64 有融合 bulk 模式（`sm4-ce-core.S` 等）。可扩展 `sm4-riscv64-glue.c` + 新增 bulk `.S`（复用现有 zvksed+zvkb 单块汇编）。**判 PATTERN(低)**：SM4 属中国商密、场景细分，优先级低于 polyval/NH。

---

## §4 N-A 明细（不误报为可移植）

- **SHA-1**（arm64 `sha1-ce-core.S`）：密码学已废弃，内核不为其新增 arch 加速 → N-A。
- **SHA-3 / Keccak**（arm64 `sha3-ce-core.S`）：RISC-V 向量 crypto 谱系**无 Keccak/SHA-3 对应扩展**（无 Zvk* 覆盖），缺「使能优化的 RV 扩展」(判法条件 c) → N-A。
- **aes-neonbs 位切片 AES**（arm64 `aes-neonbs-*`）：确是 arm64 有、riscv 无的加速，但 (a) RV 无-Zvkned 的内核既定路径是 **Adiantum**（本文 §2 NH 才是对口贡献），(b) 向量位切片 AES 为大型 greenfield 且细分 → 记 **N-A（低优先，非本轮推荐）**，非「必须补」缺口。

---

## §5 greenfield 与联网核实

- **polyval@riscv**：web 核实无在途补丁。历史 RV 向量 crypto 系列（Heiko Stübner/VRULL、Jerry Shih/SiFive，2023-2024）覆盖 AES/ChaCha/GHASH(Zvkg)/SHA-2/SM3/SM4，POLYVAL 未作为独立 RV `lib/crypto` 补丁出现。**真空档**。
- **NH/Adiantum@riscv**：web 核实无 RV NH 向量补丁；NH 加速仅 ARM/arm64/x86。**真空档**。
- **语境**：社区曾争论移除 `Zvbc`，理由「Zvkg 已能高效实现 GHASH」——佐证 polyval 首选**路线 A（Zvkg 复用）**。Zvbc/Zvkg/Zvkb/Zvbb 均已在 `cpufeature.c` 识别集 → 两大候选**无需任何 cpufeature 改动，纯 lib-crypto arch glue**。

**联网来源**：
- [RISC-V vector crypto accel (LWN 953765)](https://lwn.net/Articles/953765/)
- [v4 07/12 Zvkg GCM GHASH (Patchwork)](https://patchwork.kernel.org/project/linux-crypto/patch/20230711153743.1970625-8-heiko@sntech.de/)
- [RISC-V vector crypto spec freeze (FPRox)](https://fprox.substack.com/p/risc-v-vector-crypto-spec-freeze)
- [crypto: Adiantum support (LWN 772378)](https://lwn.net/Articles/772378/)
- [PATCH v4 00/12 RISC-V crypto (lore)](https://lore.kernel.org/lkml/20231102040333.GC1498@sol.localdomain/T/)

---

## §6 结论与建议排序

1. **polyval（PATTERN，首推）**：落点 `lib/crypto/riscv/gf128hash.h` 补三个 polyval 钩子；路线 A 复用 `ghash_zvkg`+转换 helper（成本极低），路线 B `vclmul` 原生（吞吐高）。消费者 HCTR2 在树、真空档。**本轮 crypto 最高性价比缺口。**
2. **NH/Adiantum（PATTERN，次推）**：新增 `lib/crypto/riscv/{nh.h,nh-riscv64-rvv.S}`，仅需基线 RVV `V`，`vwmaccu.vv`↔`umlal`。服务无-Zvkned 低端核盘加密，真空档。
3. **SM4 bulk 模式（PATTERN，低）**：扩 `sm4-riscv64-glue.c` + bulk `.S`；细分场景，可选。
4. 其余（GCM/CCM 融合、aes-neonbs、SHA-1、SHA-3）：ALREADY 或 N-A，不建议投入。
