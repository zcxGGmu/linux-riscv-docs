#!/bin/bash
# Script to apply the VDSO time cache fix
#
# This script applies the fix for the VDSO time cache SIGSEGV issue
# that causes kernel panic on boot (exitcode=0x0000000b)

set -e

LINUX_SRC="/home/zcxggmu/workspace/patch-work/linux"
PATCH_DIR="/home/zcxggmu/workspace/patch-work/linux-riscv-docs/kernel/vdso/docs/riscv-vdso-cache-patch-fix"

echo "=============================================="
echo "VDSO Time Cache Fix Application Script"
echo "=============================================="
echo ""
echo "This will fix the kernel panic caused by the"
echo "VDSO time cache writing to read-only VVAR page."
echo ""

cd "$LINUX_SRC"

echo "Step 1: Checking current state..."
if git diff --quiet arch/riscv/include/asm/vdso/gettimeofday.h; then
    echo "  No uncommitted changes in VDSO files"
else
    echo "  WARNING: Uncommitted changes detected!"
    echo "  Consider stashing or committing first."
    echo ""
    read -p "Continue anyway? (y/N) " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

echo ""
echo "Step 2: Reverting original broken patches..."
# First, revert the original patches if they were applied
if [ -f .git/REVERT_HEAD ]; then
    git reset --hard HEAD
fi

echo ""
echo "Step 3: Applying the TLS-based fix..."
if patch -p1 --dry-run --reverse < /dev/null 2>/dev/null; then
    echo "  No patches to revert"
fi

# Apply the fix
patch -p1 < "$PATCH_DIR/0001-riscv-vdso-fix-time-cache-use-TLS-instead-of-VVAR-write.patch"

echo ""
echo "Step 4: Verifying the fix..."
if grep -q "__vdso_time_cache_tls" arch/riscv/include/asm/vdso/gettimeofday.h; then
    echo "  ✓ Fix applied successfully!"
else
    echo "  ✗ Fix may not have applied correctly"
    exit 1
fi

echo ""
echo "Step 5: Recompiling kernel..."
echo ""
echo "Please run the following commands to rebuild the kernel:"
echo ""
echo "  cd $LINUX_SRC"
echo "  make -j\$(nproc)"
echo "  # Install and reboot"
echo ""
echo "Or to quickly disable the feature entirely:"
echo "  make menuconfig  # Platform type -> RISC-V VDSO time caching = N"
echo "  make -j\$(nproc)"
echo ""
echo "=============================================="
echo "Fix application complete!"
echo "=============================================="
