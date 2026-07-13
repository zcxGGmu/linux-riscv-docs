# vector-fp 可移植性分析（linux-arm-kernel → RISC-V）

> 类别：SVE/SME/NEON/FP-SIMD 上下文 / ptrace / signal / kernel-mode SIMD / lib crypto+crc。
> 判定纪律：**SVE→RVV** 上下文/ABI/selftest 补丁 → PATTERN（落点 `arch/riscv/kernel/{vector,kernel_mode_vector,signal,ptrace}.c`）；
> **SME（可伸缩矩阵 / streaming / ZA / TPIDR2 / FPMR）无 riscv 对应 → N-A**；
> **KVM arm64（host save/flush、CPTR traps、pKVM、nested、稳定分支 backport）EL2/hyp 专属 → N-A**；
> **FP-SIMD / lib-crypto / lib-crc 通用框架 → PORTABLE**（riscv 加速实现多已存在，属 ALREADY）。

## 摘要

- **系列总数：60**
- **判定计数**：ALREADY = 2 ｜ PORTABLE = 6 ｜ PATTERN = 15 ｜ N-A = 37
- 关键基线核对（本地树 v7.2.0-rc3，均已确认存在）：
  - `arch/riscv/kernel/kernel_mode_vector.c`：`kernel_vector_begin/end()` + `BUG_ON(!may_use_simd())`。
  - `arch/riscv/include/asm/simd.h`：`may_use_simd()` **已拒绝** `in_hardirq()/in_nmi()`、`irqs_disabled()`、`RISCV_KERNEL_MODE_V`（含 bh/lockdep 注释）——**无** `scoped_ksimd()` 抽象。
  - `arch/riscv/kernel/ptrace.c`：`REGSET_V` + `riscv_vr_get/set`（set 路径**已用 `&target->thread.vstate`**）。
  - `lib/crc/riscv/`（crc32/64 clmul）、`lib/crypto/riscv/`（aes/chacha/**ghash-zvkg**/poly1305/sha/sm3 Zvk*）、`lib/crypto/gf128hash.c`（通用）均存在。
  - **无** `arch/riscv/include/asm/xor.h`（RVV RAID/xor 加速缺口）。

### 本类 Top 候选（按价值排序）

1. **#22 arm64: Move kernel mode FPSIMD buffer to the stack**（scoped `ksimd` guard API）→ **PATTERN**，`arch/riscv/include/asm/simd.h`
2. **#13 GHASH library**（`lib/crypto` gf128hash 通用化）→ **PORTABLE**，`lib/crypto/gf128hash.c`
3. **#34 lib/crypto: Poly1305 fixes**（no-SIMD 上下文寄存器损坏修复）→ **PORTABLE**，`lib/crypto/riscv/poly1305*`
4. **#7 arm64/fpsimd: ptrace: zero target's fpsimd_state**（tracer↔tracee 混淆）→ **PATTERN（审计）**，`arch/riscv/kernel/ptrace.c`
5. **#8/#11/#12 crc64 NEON intrinsics → 通用 lib/crc**（公共代码重构）→ **PORTABLE**，`lib/crc/`
6. **#48/#50 crypto: arm - drop dependency on SIMD helper**（arch=generic，crypto 框架）→ **PORTABLE**，`crypto/`
7. **#21 arm64: NEON based copy to/from user**（SIMD 加速 uaccess）→ **PATTERN**，`arch/riscv/lib/`
8. **#25 RFC arm64/fpsimd: strict mode for kernel mode SIMD**（内核 SIMD 校验）→ **PATTERN**，`arch/riscv/kernel/kernel_mode_vector.c`

---

## Top 可移植候选（深度，已 curl/Grep 核对）

### #22 — arm64: Move kernel mode FPSIMD buffer to the stack（scoped `ksimd` guard API）
- **原补丁**：`arm64: Move kernel mode FPSIMD buffer to the stack`（v4，21 patches）
  <https://patchwork.kernel.org/project/linux-arm-kernel/patch/20251031103858.529530-30-ardb+git@google.com/> 状态=new
- **可移植点**：引入 `scoped_ksimd()` / `ksimd_begin()` 抽象（`<asm/simd.h>`），替换 `kernel_neon_begin()/end()` 的裸调用，使
  `lib/raid6/neon.c`、`lib/crc/*`、`crypto/aegis128` 等**跨架构共享代码**不再直接耦合各 arch 的 kernel-mode SIMD API。
  curl 全文确认 07/21 把 `lib/raid6/{neon,recov_neon}.c` 从 `kernel_neon_begin/end` 迁移到 `scoped_ksimd()`（作用域守卫，自动配对 begin/end）。
- **riscv 落点**：`arch/riscv/include/asm/simd.h` —— 现仅有 `may_use_simd()`，**尚无 `scoped_ksimd()`**（Grep 全树为空）。
  riscv 需提供 `scoped_ksimd()`（包 `kernel_vector_begin()`/`kernel_vector_end()`，见 `kernel_mode_vector.c:207/237`）。
- **判定**：**PATTERN**。守卫本体是 arch 专属（riscv 用 vector 而非 NEON），但抽象一旦落地，riscv 即自动复用 `lib/raid6`、`lib/crc`、`lib/crypto` 内核态 SIMD 路径——本类最高价值项。

### #13 — GHASH library（lib/crypto gf128hash 通用化）
- **原补丁**：`GHASH library`（19 patches）
  <https://patchwork.kernel.org/project/linux-arm-kernel/patch/20260319061723.1140720-4-ebiggers@kernel.org/> 状态=new
- **可移植点**：把 polyval 模块重命名为 `gf128hash`、加入通用 GHASH 支持与 KUnit 测试（`lib/crypto/gf128hash.c` + tests），再按 arch 接线。核心库层与架构无关。
- **riscv 落点**：`lib/crypto/gf128hash.c`（通用，已存在）；riscv 接线已就位——`lib/crypto/riscv/ghash-riscv64-zvkg.S` + `lib/crypto/riscv/gf128hash.h`（Grep 确认）。
- **判定**：**PORTABLE**（通用库框架，直接适用）；riscv 的 Zvkg 加速实现属 **ALREADY**，仅需跟随 gf128hash 重命名/接口调整。

### #34 — lib/crypto: Poly1305 fixes（no-SIMD 上下文寄存器损坏）
- **原补丁**：`lib/crypto: Poly1305 fixes`（5 patches；含 arm/arm64/x86）
  <https://patchwork.kernel.org/project/linux-arm-kernel/patch/20250706231100.176113-2-ebiggers@kernel.org/> 状态=new
- **可移植点**：删除多余 `__weak poly1305_blocks_neon()` 空桩、修复无 SIMD 上下文下的寄存器损坏（curl 确认 diff 在 `lib/crypto/arm/poly1305-glue.c`）。属 `lib/crypto` per-arch glue 一致性修复，思想通用。
- **riscv 落点**：`lib/crypto/riscv/poly1305-riscv.pl` + `lib/crypto/riscv/poly1305.h`（存在）——应审计 riscv glue 是否有同类 no-SIMD 回退/桩问题。
- **判定**：**PORTABLE**（通用库 glue 模式；riscv poly1305 需同步审计）。

### #7 — arm64/fpsimd: ptrace: zero target's fpsimd_state, not the tracer's
- **原补丁**：单补丁 <https://patchwork.kernel.org/project/linux-arm-kernel/patch/20260505-fix_ptrace-v1-1-36ac1f6d0bfb@debian.org/> 状态=new
- **可移植点**：`PTRACE_SETREGSET(NT_ARM_SVE/SSVE)` 后端把 `memset` 误指向 `current`（tracer）而非 `target`（tracee），静默损坏 tracer 的 V/FPSR/FPCR 影子。curl 确认修复即 `current→target` 两处。**类=惰性 save/restore 下 tracer↔tracee 状态混淆**。
- **riscv 落点**：`arch/riscv/kernel/ptrace.c` `riscv_vr_set()`——Grep 确认已用 `&target->thread.vstate`（**当前未见同类 bug**）。价值在于：以此为对照**审计 riscv REGSET_V/F set 路径**是否存在 current-vs-target 混淆。
- **判定**：**PATTERN（审计）**。riscv 大概率不受影响，但同类惰性 vstate 语义值得回归确认。

### #8 / #11 / #12 — crc64 NEON intrinsics → 通用 lib/crc
- **原补丁**：`ARM crc64 and XOR using NEON intrinsics`（8）<https://patchwork.kernel.org/project/linux-arm-kernel/patch/20260422171655.3437334-18-ardb+git@google.com/>；
  `crc64: Tweak intrinsics code and enable it for ARM`（5）<https://patchwork.kernel.org/project/linux-arm-kernel/patch/20260330144630.33026-10-ardb@kernel.org/>；
  `lib/crc: arm64: NEON CRC64-NVMe`（1）<https://patchwork.kernel.org/project/linux-arm-kernel/patch/20260329074338.1053550-1-demyansh@gmail.com/> 状态=new
- **可移植点**：把 crc64 NEON intrinsics 实现**下沉为 lib/crc 公共代码**（`lib/crc: Turn NEON intrinsics crc64 into common code`），arm/arm64 共享。公共层与架构无关。
- **riscv 落点**：`lib/crc/`（通用重构 PORTABLE）；riscv 已有 `lib/crc/riscv/`（clmul 版 crc32/64，`crc-clmul-*`）——**加速实现属 ALREADY**，无需搬 NEON。
- **判定**：**PORTABLE**（仅公共代码重构部分；NEON 加速对 riscv 不适用，riscv 用 Zbc clmul）。

### #48 / #50 — crypto: arm - drop dependency on SIMD helper（arch=generic）
- **原补丁**：<https://patchwork.kernel.org/project/linux-arm-kernel/patch/20250403071953.2296514-6-ardb+git@google.com/>（3）；
  <https://patchwork.kernel.org/project/linux-arm-kernel/patch/20250402070251.1762692-3-ardb+git@google.com/>（2）状态=new
- **可移植点**：停止使用 `crypto/simd.c` 异步包装 helper，并移除未用的 `crypto_ctr_encrypt_walk()`（通用 crypto 框架）。`arch=generic`，纪律优先 PORTABLE。
- **riscv 落点**：`crypto/`（通用框架）+ riscv crypto 驱动（若跟随同模式）。通用 ctr 清理直接适用。
- **判定**：**PORTABLE**（通用 crypto 框架变更；arm 驱动侧改动对 riscv 仅为模式参考）。

---

## 全量判定表（覆盖全部 60 条）

| # | 系列 | arch | 判定 | 可移植点(若有) | riscv落点(若有) | web_url |
|---|---|---|---|---|---|---|
| 1 | kselftest: signal skip SVE if not enough VLs | arm | PATTERN(低) | 向量 signal selftest 跳过逻辑 | `tools/testing/selftests/riscv/vector/` | [link](https://patchwork.kernel.org/project/linux-arm-kernel/patch/20260627032259.2086191-1-wangyijia.yeah@bytedance.com/) |
| 2 | selftests: signal skip SVE VL change single VL | arm | PATTERN(低) | 同上 VL 变更跳过 | `selftests/riscv/vector/` | [link](https://patchwork.kernel.org/project/linux-arm-kernel/patch/20260626-b4-arm64-515-preview-clean-v1-1-ad19e286e322@bytedance.com/) |
| 3 | Avoid eager DVMSync reclaim w/ C1-Pro SME erratum | arm | N-A | SME 硬件 erratum + DVMSync 广播 | — | [link](https://patchwork.kernel.org/project/linux-arm-kernel/patch/20260610104829.1157497-1-catalin.marinas@arm.com/) |
| 4 | arm64+KVM: FPSIMD/SVE/SME cleanups | arm | N-A | KVM hyp + SME + arm64 寄存器布局修复 | — | [link](https://patchwork.kernel.org/project/linux-arm-kernel/patch/20260603110630.1027435-13-mark.rutland@arm.com/) |
| 5 | Document SVE constraints on new hwcaps | arm | N-A | arm64 hwcap 专属文档 | (riscv hwprobe 文档另立) | [link](https://patchwork.kernel.org/project/linux-arm-kernel/patch/20260522-arm64-elf-hwcaps-sve-cleanup-v1-1-07b0cedfc6fa@kernel.org/) |
| 6 | KVM nv: Reduce FP/SVE overhead on exception | arm | N-A | KVM 嵌套虚拟化 (NV) EL2 | — | [link](https://patchwork.kernel.org/project/linux-arm-kernel/patch/20260520085036.541666-2-maz@kernel.org/) |
| 7 | ptrace: zero target's fpsimd_state, not tracer's | arm | **PATTERN** | tracer↔tracee 状态混淆审计 | `arch/riscv/kernel/ptrace.c` `riscv_vr_set` | [link](https://patchwork.kernel.org/project/linux-arm-kernel/patch/20260505-fix_ptrace-v1-1-36ac1f6d0bfb@debian.org/) |
| 8 | ARM crc64 and XOR using NEON intrinsics | arm | **PORTABLE** | lib/crc crc64 公共代码下沉 | `lib/crc/`（riscv clmul 已有=ALREADY） | [link](https://patchwork.kernel.org/project/linux-arm-kernel/patch/20260422171655.3437334-18-ardb+git@google.com/) |
| 9 | perf arm_spe: Extend SIMD operations | arm | N-A | SPE 统计采样（riscv 无对应） | — | [link](https://patchwork.kernel.org/project/linux-arm-kernel/patch/20260410-perf_support_arm_spev1-3-v6-1-3c6f2dfe2cd3@arm.com/) |
| 10 | xor/arm: Replace vectorized version w/ intrinsics | arm | PATTERN | RVV RAID/xor（riscv 无 asm/xor.h） | `arch/riscv/include/asm/xor.h`(新) + `lib/raid6/` | [link](https://patchwork.kernel.org/project/linux-arm-kernel/patch/20260331074940.55502-12-ardb+git@google.com/) |
| 11 | crc64: Tweak intrinsics, enable for ARM | arm | **PORTABLE** | lib/crc 公共代码简化 | `lib/crc/`（riscv clmul=ALREADY） | [link](https://patchwork.kernel.org/project/linux-arm-kernel/patch/20260330144630.33026-10-ardb@kernel.org/) |
| 12 | lib/crc: arm64 NEON CRC64-NVMe | arm | PATTERN | lib/crc 新增 crc64 变体 | `lib/crc/riscv/`（可加 clmul 变体） | [link](https://patchwork.kernel.org/project/linux-arm-kernel/patch/20260329074338.1053550-1-demyansh@gmail.com/) |
| 13 | GHASH library | arm | **PORTABLE** | lib/crypto gf128hash 通用化+GHASH+KUnit | `lib/crypto/gf128hash.c`（riscv zvkg 已接线） | [link](https://patchwork.kernel.org/project/linux-arm-kernel/patch/20260319061723.1140720-4-ebiggers@kernel.org/) |
| 14 | arm64: lib: xor-neon comment/spacing | arm | N-A | 琐碎注释/指针空格 | — | [link](https://patchwork.kernel.org/project/linux-arm-kernel/patch/20260301152820.2589291-1-objecting@objecting.org/) |
| 15 | kselftest: fp-pidbench enhancements | arm | PATTERN(低) | 向量上下文切换基准 | `selftests/riscv/vector/` | [link](https://patchwork.kernel.org/project/linux-arm-kernel/patch/20260127-arm64-selftests-fp-pidbench-post-sve-v1-1-3c78eda0d58b@kernel.org/) |
| 16 | arm64/fpsimd: State management fixes | arm | PATTERN(部分) | SVE signal/ptrace 上下文恢复正确性 | `arch/riscv/kernel/{signal,ptrace}.c`（SSVE/ZA 部分 N-A） | [link](https://patchwork.kernel.org/project/linux-arm-kernel/patch/20260120145107.1278972-2-mark.rutland@arm.com/) |
| 17 | KVM: arm64: Trivial FPSIMD cleanups | arm | N-A | KVM arm64 hyp 清理 | — | [link](https://patchwork.kernel.org/project/linux-arm-kernel/patch/20260106173707.3292074-3-mark.rutland@arm.com/) |
| 18 | crypto: arm64/ghash - Fix ghash-neon output | arm | N-A | arm64 NEON 实现 bug（riscv 用 zvkg） | — | [link](https://patchwork.kernel.org/project/linux-arm-kernel/patch/20251209223417.112294-1-ebiggers@kernel.org/) |
| 19 | arm64/simd: Avoid pointless clearing of FP buffer | arm | N-A | arm64 fpsimd 微优化 | — | [link](https://patchwork.kernel.org/project/linux-arm-kernel/patch/20251209054848.998878-2-ardb@kernel.org/) |
| 20 | efi/arm64: Simplify SVE/SME preserve/restore | arm | N-A | arm64 EFI + SME 状态保存 | — | [link](https://patchwork.kernel.org/project/linux-arm-kernel/patch/20251206190114.892262-6-ardb@kernel.org/) |
| 21 | arm64: NEON based copy to/from user | arm | PATTERN | RVV 加速 uaccess（copy_to/from_user） | `arch/riscv/lib/` + `kernel_mode_vector.c` | [link](https://patchwork.kernel.org/project/linux-arm-kernel/patch/20251129065846.1656987-1-tujinjiang@huawei.com/) |
| 22 | arm64: Move kernel mode FPSIMD buffer to stack | arm | **PATTERN** | `scoped_ksimd()` 跨架构守卫抽象 | `arch/riscv/include/asm/simd.h`（新增 scoped_ksimd） | [link](https://patchwork.kernel.org/project/linux-arm-kernel/patch/20251031103858.529530-30-ardb+git@google.com/) |
| 23 | arm64/sme: disable streaming via ptrace (SME only) | arm | N-A | SME streaming mode | — | [link](https://patchwork.kernel.org/project/linux-arm-kernel/patch/20251015-arm64-sme-ptrace-sme-only-v2-2-33c7b2f27cbf@kernel.org/) |
| 24 | KVM: arm64: Fix softirq masking in FPSIMD save | arm | N-A | KVM arm64 fpsimd 保存序列 | — | [link](https://patchwork.kernel.org/project/linux-arm-kernel/patch/20251003184054.4286-1-will@kernel.org/) |
| 25 | RFC arm64/fpsimd: strict mode for kernel SIMD | arm | PATTERN | 内核态 SIMD 使用校验/调试模式 | `arch/riscv/kernel/kernel_mode_vector.c` | [link](https://patchwork.kernel.org/project/linux-arm-kernel/patch/20251003162120.2672780-2-ardb+git@google.com/) |
| 26 | arm64/fpsimd: simplify sme_setup() | arm | N-A | SME 初始化 | — | [link](https://patchwork.kernel.org/project/linux-arm-kernel/patch/20250913000906.67086-1-yury.norov@gmail.com/) |
| 27 | STABLE KVM: fix BUG from bad SVE/SME backport | arm | N-A | KVM arm64 backport | — | [link](https://patchwork.kernel.org/project/linux-arm-kernel/patch/20250822140402.2688-1-will@kernel.org/) |
| 28 | kselftest: Log error codes in sve-ptrace | arm | PATTERN(低) | 向量 ptrace selftest 日志 | `selftests/riscv/vector/` | [link](https://patchwork.kernel.org/project/linux-arm-kernel/patch/20250812-arm64-fp-ptrace-perror-v1-1-7ce62d33709d@kernel.org/) |
| 29 | arm64/sme: Drop doc of streaming mode switches | arm | N-A | SME 文档 | — | [link](https://patchwork.kernel.org/project/linux-arm-kernel/patch/20250723-arm64-sme-mode-switch-doc-v1-1-702bb484b4f4@kernel.org/) |
| 30 | kselftest: fp-ptrace fixes for SME only systems | arm | N-A | SME-only selftest | — | [link](https://patchwork.kernel.org/project/linux-arm-kernel/patch/20250718-arm64-fp-ptrace-sme-only-v1-1-3b96dd19a503@kernel.org/) |
| 31 | kselftest: FPSIMD writes via NT_ARM_SVE | arm | PATTERN(低) | FPSIMD-格式经向量 regset 写入 selftest | `selftests/riscv/vector/*ptrace*` | [link](https://patchwork.kernel.org/project/linux-arm-kernel/patch/20250718-arm64-fp-ptrace-sve-fpsimd-v1-1-7ecda32aa297@kernel.org/) |
| 32 | kselftest: sve-ptrace on SME only systems | arm | N-A | SME-only selftest | — | [link](https://patchwork.kernel.org/project/linux-arm-kernel/patch/20250718-arm64-sve-ptrace-sme-only-v1-1-2a1121e51b1d@kernel.org/) |
| 33 | arm64: Filter out SME hwcaps when !FEAT_SME | arm | N-A | SME hwcap 过滤 | — | [link](https://patchwork.kernel.org/project/linux-arm-kernel/patch/20250716-stable-6-6-sme-feat-filt-v1-1-151d319dc41e@kernel.org/) |
| 34 | lib/crypto: Poly1305 fixes | arm | **PORTABLE** | no-SIMD 上下文寄存器损坏修复(通用 glue) | `lib/crypto/riscv/poly1305*` | [link](https://patchwork.kernel.org/project/linux-arm-kernel/patch/20250706231100.176113-2-ebiggers@kernel.org/) |
| 35 | KVM: arm64: trap fixes and cleanup | arm | N-A | KVM CPTR/EL2 陷阱 | — | [link](https://patchwork.kernel.org/project/linux-arm-kernel/patch/20250617133718.4014181-7-mark.rutland@arm.com/) |
| 36 | kselftest: Update sve-ptrace for ABI changes | arm | PATTERN(部分) | 向量 ptrace ABI selftest（streaming 部分 N-A） | `selftests/riscv/vector/*ptrace*` | [link](https://patchwork.kernel.org/project/linux-arm-kernel/patch/20250609-kselftest-arm64-ssve-fixups-v2-1-998fcfa6f240@kernel.org/) |
| 37 | arm64: FPSIMD/SVE/SME fixes + re-enable SME (24) | arm | PATTERN(部分) | SVE signal/ptrace 部分写/格式切换正确性 | `arch/riscv/kernel/{signal,ptrace,vector}.c`（SME 部分 N-A） | [link](https://patchwork.kernel.org/project/linux-arm-kernel/patch/20250508132644.1395904-9-mark.rutland@arm.com/) |
| 38 | arm64: FPSIMD/SVE/SME fixes + re-enable SME (20) | arm | PATTERN(部分) | 同 #37（早版本） | 同 #37 | [link](https://patchwork.kernel.org/project/linux-arm-kernel/patch/20250506152523.1107431-9-mark.rutland@arm.com/) |
| 39 | arm64/fpsimd: hide unused sve_to_fpsimd() | arm | N-A | 琐碎 build 警告修复 | — | [link](https://patchwork.kernel.org/project/linux-arm-kernel/patch/20250503140514.487947-1-arnd@kernel.org/) |
| 40 | arm64/fpsimd: Avoid warning sve_to_fpsimd unused | arm | N-A | 琐碎 build 警告 | — | [link](https://patchwork.kernel.org/project/linux-arm-kernel/patch/20250430173240.4023627-1-mark.rutland@arm.com/) |
| 41 | arm64/fpsimd: signal: Clear TPIDR2 on signals | arm | N-A | TPIDR2（SME ZA 专属） | — | [link](https://patchwork.kernel.org/project/linux-arm-kernel/patch/20250417190113.3778111-1-mark.rutland@arm.com/) |
| 42 | KVM: selftests: test for SVE host corruption | arm | N-A | KVM arm64 selftest | — | [link](https://patchwork.kernel.org/project/linux-arm-kernel/patch/20250417-kvm-selftest-sve-signal-v1-1-6330c2f3da0c@kernel.org/) |
| 43 | Move pKVM ownership state to hyp_vmemmap | arm | N-A | pKVM hyp 内存/SVE 状态 | — | [link](https://patchwork.kernel.org/project/linux-arm-kernel/patch/20250416152648.2982950-6-qperret@google.com/) |
| 44 | arm64: Preparatory FPSIMD/SVE/SME fixes (13) | arm | N-A(SME 为主) | SME 陷阱处理/FPMR（少量 SVE PATTERN） | (SVE 部分→`signal.c`；SME→无) | [link](https://patchwork.kernel.org/project/linux-arm-kernel/patch/20250409164010.3480271-9-mark.rutland@arm.com/) |
| 45 | KVM: arm64: Get rid of host SVE tracking (5.15) | arm | N-A | KVM arm64 backport | — | [link](https://patchwork.kernel.org/project/linux-arm-kernel/patch/20250408-stable-sve-5-15-v3-11-ca9a6b850f55@kernel.org/) |
| 46 | Documentation (arm64): Advanced SIMD/FP condition | arm | N-A | arm64 SIMD/FP 文档 | — | [link](https://patchwork.kernel.org/project/linux-arm-kernel/patch/20250408031309.2095-1-zhangxiquan@hisilicon.com/) |
| 47 | KVM: arm64: Backport of SVE fixes to v6.1 | arm | N-A | KVM arm64 backport | — | [link](https://patchwork.kernel.org/project/linux-arm-kernel/patch/20250404-stable-sve-6-1-v1-9-cd5c9eb52d49@kernel.org/) |
| 48 | crypto: arm - drop dependency on SIMD helper | generic | **PORTABLE** | 通用 crypto 框架（去 simd helper + ctr 清理） | `crypto/` | [link](https://patchwork.kernel.org/project/linux-arm-kernel/patch/20250403071953.2296514-6-ardb+git@google.com/) |
| 49 | KVM: arm64: Backport of SVE fixes to v5.15 | arm | N-A | KVM arm64 backport | — | [link](https://patchwork.kernel.org/project/linux-arm-kernel/patch/20250403-stable-sve-5-15-v2-10-30a36a78a20a@kernel.org/) |
| 50 | crypto: arm/aes-ce - stop using SIMD helper | generic | **PORTABLE** | 通用 crypto 框架模式 | `crypto/` + riscv crypto 驱动(模式参考) | [link](https://patchwork.kernel.org/project/linux-arm-kernel/patch/20250402070251.1762692-3-ardb+git@google.com/) |
| 51 | ARM: Disallow kernel mode NEON when IRQs disabled | arm | **ALREADY** | riscv `may_use_simd()` 已拒绝 irqs_disabled+bh(lockdep) | `arch/riscv/include/asm/simd.h:47-52` | [link](https://patchwork.kernel.org/project/linux-arm-kernel/patch/20250324185927.1024543-2-ardb+git@google.com/) |
| 52 | KVM: arm64: Backport of SVE fixes to v6.6 | arm | N-A | KVM arm64 backport | — | [link](https://patchwork.kernel.org/project/linux-arm-kernel/patch/20250321-stable-sve-6-6-v1-6-0b3a6a14ea53@kernel.org/) |
| 53 | KVM: arm64: Backport of SVE fixes to v6.12 | arm | N-A | KVM arm64 backport | — | [link](https://patchwork.kernel.org/project/linux-arm-kernel/patch/20250321-stable-sve-6-12-v2-6-417ca2278d18@kernel.org/) |
| 54 | KVM: arm64: Backport of SVE fixes to v6.13 | arm | N-A | KVM arm64 backport | — | [link](https://patchwork.kernel.org/project/linux-arm-kernel/patch/20250321-stable-sve-6-13-v2-6-3150e3370c40@kernel.org/) |
| 55 | arm64/fpsimd: Avoid per-CPU buffers for EFI calls | arm | N-A | arm64 EFI fpsimd 缓冲优化（关联 #22） | (→`arch/riscv/kernel/efi*` 可选) | [link](https://patchwork.kernel.org/project/linux-arm-kernel/patch/20250318132421.3155799-2-ardb+git@google.com/) |
| 56 | arm64/fpsimd: Remove unused fpsimd_kvm_prepare() | arm | N-A | 琐碎清理 | — | [link](https://patchwork.kernel.org/project/linux-arm-kernel/patch/20250309070723.1390958-1-yuehaibing@huawei.com/) |
| 57 | KVM: arm64: doc fix for pKVM SME assert | arm | N-A | pKVM/SME 文档 | — | [link](https://patchwork.kernel.org/project/linux-arm-kernel/patch/20250212-kvm-arm64-sme-assert-v7-1-0f786db838d3@kernel.org/) |
| 58 | KVM: arm64: FPSIMD/SVE/SME fixes (8) | arm | N-A | KVM arm64 host save/flush+CPACR | — | [link](https://patchwork.kernel.org/project/linux-arm-kernel/patch/20250210195226.1215254-7-mark.rutland@arm.com/) |
| 59 | KVM: arm64/sve: Ensure SVE trapped after guest exit | arm | N-A | KVM arm64 SVE 陷阱 | — | [link](https://patchwork.kernel.org/project/linux-arm-kernel/patch/20250121100026.3974971-1-mark.rutland@arm.com/) |
| 60 | arm64: Filter out SVE hwcaps when !FEAT_SVE | arm | ALREADY(近似) | riscv 按 isa_ext 探测天然门控 RVV hwprobe | `arch/riscv/kernel/cpufeature.c`, `sys_hwprobe.c` | [link](https://patchwork.kernel.org/project/linux-arm-kernel/patch/20250106174020.1793678-1-maz@kernel.org/) |

---

## 判定要点小结

- **N-A 主体（37 条）**：三大来源——(a) **KVM arm64**（host save/flush、CPTR/CPACR 陷阱、pKVM、nested、5.15/6.1/6.6/6.12/6.13 稳定分支 backport）≈18 条；(b) **SME 专属**（streaming/ZA/TPIDR2/FPMR/sme_setup/DVMSync erratum/SME hwcap 过滤）≈9 条；(c) **arm64 arch 内部**（琐碎 build/注释清理、NEON 实现 bug、EFI/percpu 微优化、arm64 文档、SPE perf 工具）≈10 条。均无 riscv 对应或不扩展通用底座。
- **PATTERN 主体（15 条）**：最有价值是 **#22 `scoped_ksimd()` 守卫抽象**（落 `asm/simd.h`，一次落地即复用 lib/raid6+lib/crc+lib/crypto 内核态 SIMD 路径）；其次 **#21 RVV uaccess**、**#25 内核 SIMD strict 模式**、**#10 RVV RAID/xor**（riscv 无 `asm/xor.h` 缺口）；以及一批 **SVE signal/ptrace 正确性/selftest**（#7/#16/#37/#38 及低价值 selftest #1/2/15/28/31/36），落 `arch/riscv/kernel/{signal,ptrace,vector}.c` 与 `selftests/riscv/vector/`，其 SME/streaming 子集判 N-A。
- **PORTABLE（6 条）**：均为 **lib 层通用框架**——#13 gf128hash/GHASH、#34 Poly1305 glue、#8/#11 crc64 公共代码下沉、#48/#50 crypto 去 SIMD-helper。riscv 加速实现（clmul crc、Zvk* crypto）**多已存在（ALREADY）**，仅需跟随通用层接口。
- **ALREADY（2 条）**：#51（内核态 SIMD 于 IRQ-disabled 的 bh/lockdep 规则——riscv `may_use_simd()` 已内建，见 simd.h:47-52 注释）；#60（RVV hwprobe 天然按 `riscv_isa_extension_available` 门控，无 arm64 那类「特性缺失仍暴露 hwcap」bug）。
