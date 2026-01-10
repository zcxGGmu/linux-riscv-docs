#!/bin/bash
# Apply RISC-V VDSO time caching patches to Linux kernel
#
# Usage: ./apply-patches.sh <kernel-source-directory>

set -e

KERNEL_DIR="${1:-/home/zcxggmu/workspace/patch-work/linux}"
PATCH_DIR="$(dirname "$0")"

echo "Applying RISC-V VDSO time caching patches to ${KERNEL_DIR}..."
echo ""

# Check kernel directory exists
if [ ! -d "${KERNEL_DIR}" ]; then
    echo "Error: Kernel directory ${KERNEL_DIR} does not exist"
    exit 1
fi

# Check if it's a kernel source tree
if [ ! -f "${KERNEL_DIR}/README" ]; then
    echo "Error: ${KERNEL_DIR} does not appear to be a kernel source tree"
    exit 1
fi

cd "${KERNEL_DIR}"

# Apply patches in order
for patch in "${PATCH_DIR}"/0*.patch; do
    if [ -f "${patch}" ]; then
        echo "Applying: $(basename "${patch}")"
        patch -p1 < "${patch}"
        if [ $? -eq 0 ]; then
            echo "  ✓ Success"
        else
            echo "  ✗ Failed"
            echo ""
            echo "You may need to resolve conflicts manually."
            echo "After resolving, run:"
            echo "  git add -u"
            echo "  git am --continue"
            exit 1
        fi
    fi
done

echo ""
echo "All patches applied successfully!"
echo ""
echo "Next steps:"
echo "  1. make defconfig (or your preferred config)"
echo "  2. Search for CONFIG_RISCV_VDSO_TIME_CACHE and enable it"
echo "  3. make -j$(nproc)"
echo "  4. Boot and test with the benchmark program"
