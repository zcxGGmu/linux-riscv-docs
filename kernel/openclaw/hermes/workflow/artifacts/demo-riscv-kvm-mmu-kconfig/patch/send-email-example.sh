#!/bin/sh
# demo only -- do not run without replacing addresses and validating patch artifacts

git send-email   --to linux-riscv@lists.infradead.org   --to kvm@vger.kernel.org   --subject-prefix='PATCH demo'   ./patches/0000-cover-letter.patch ./patches/0001-riscv-kvm-clarify-mmu-requirement.patch
