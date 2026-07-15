#!/usr/bin/env bash
# gap_probe.sh — 第四轮两路静态信号的只读复现探针
#   ①ISA 批准差集：内核已识别扩展集 vs 目标 ratified 缺口
#   ②asm 优化差集：arch string.h 提供的 __HAVE_ARCH_* / lib 现状 / crypto 覆盖
#
# 用法:  TREE=/path/to/linux ./gap_probe.sh
#   默认 TREE=/Users/zq/Desktop/patch-work/linux-riscv（只读，不修改内核树）
set -euo pipefail
TREE="${TREE:-/Users/zq/Desktop/patch-work/linux-riscv}"
cd "$TREE"

echo "===== 内核版本 ====="
grep -E '^(VERSION|PATCHLEVEL|SUBLEVEL|EXTRAVERSION) ' Makefile | head -4

echo; echo "===== ①内核已识别扩展集 riscv_isa_ext[]（判 ALREADY 依据）====="
grep -oE '__RISCV_ISA_EXT_[A-Z_]*\([a-z0-9_]+' arch/riscv/kernel/cpufeature.c \
  | sed -E 's/.*\(//' | sort -u | tr '\n' ' '; echo
printf 'count = '; grep -cE '__RISCV_ISA_EXT_[A-Z_]*\(' arch/riscv/kernel/cpufeature.c

echo; echo "===== ①hwprobe 暴露的扩展/键 ====="
grep -oE 'RISCV_HWPROBE_(EXT|KEY)_[A-Z0-9_]+' arch/riscv/include/uapi/asm/hwprobe.h | sort -u | tr '\n' ' '; echo

echo; echo "===== ①目标 ratified 缺口是否真缺（期望零匹配 = 真缺口）====="
if grep -rniE 'qosid|ssctr|smctr|smcdeleg|ssccfg|s[ms]csrind|sdtrig|s[ms]dbltrp|smcntrpmf' arch/riscv/ ; then
  echo "  (上有匹配 → 该扩展已被内核触及，需复核)"
else
  echo "  (零匹配 → Ssqosid/Ssctr/Smctr/Smcdeleg/Ssccfg/Sm|Sscsrind/Sdtrig/Ss|Smdbltrp/Smcntrpmf 均为真缺口)"
fi
echo "  hw_breakpoint 落点是否存在："; find arch/riscv -name 'hw_breakpoint*' -print -quit | grep . || echo "    (不存在 → Sdtrig=HAVE_HW_BREAKPOINT 全新落点)"
echo "  resctrl 是否已接："; grep -ni resctrl arch/riscv/Kconfig || echo "    (未接 → Ssqosid/ARCH_HAS_CPU_RESCTRL 缺口)"

echo; echo "===== ②arch string.h 提供的 __HAVE_ARCH_*（缺 MEMCMP/MEMCHR）====="
grep -oE '__HAVE_ARCH_[A-Z]+' arch/riscv/include/asm/string.h | sort -u | tr '\n' ' '; echo

echo; echo "===== ②arch/riscv/lib 汇编例程（strchr/strrchr/memcpy/memset 存在但未优化；无 memcmp/memchr）====="
ls arch/riscv/lib/*.S 2>/dev/null | xargs -n1 basename | tr '\n' ' '; echo

echo; echo "===== ②已加速 crypto（判 ALREADY；缺 polyval / NH / Adiantum）====="
echo "-- lib/crypto/riscv/:"; ls lib/crypto/riscv/ 2>/dev/null | tr '\n' ' '; echo
echo "-- arch/riscv/crypto/:"; ls arch/riscv/crypto/ 2>/dev/null | tr '\n' ' '; echo
