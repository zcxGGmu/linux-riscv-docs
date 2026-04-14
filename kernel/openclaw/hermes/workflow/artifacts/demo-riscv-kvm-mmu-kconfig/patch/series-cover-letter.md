Subject: [PATCH 0/1] riscv/kvm: clarify MMU requirement in Kconfig

This demo series contains a single low-risk Kconfig consistency fix for RISC-V host KVM.

The change does not alter runtime behavior. It only makes the MMU requirement explicit in
`CONFIG_RISCV_KVM` dependency/help text so the configuration surface matches the expected host
KVM assumptions more clearly, especially when exploring non-MMU configurations.

Demo validation performed:
- simulated `make ARCH=riscv allnoconfig`
- simulated `make ARCH=riscv olddefconfig`
- simulated `make ARCH=riscv defconfig`
- simulated checkpatch clean run

This artifact is for workflow demonstration only and still requires human Gate-3 review.
