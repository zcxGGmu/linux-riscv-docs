# issue-1 iter-2 log

## Summary
本轮完成了 RISC-V KVM nested virtualization 的 **VM/VCPU 生命周期骨架接入**，并保持默认行为不变（state-only scaffold）。

## Code changes
- `arch/riscv/kvm/nested.c`（新增）
  - `kvm_riscv_nested_vm_init/deinit`
  - `kvm_riscv_nested_vcpu_init/reset/deinit`
- `arch/riscv/include/asm/kvm_host.h`
  - 新增 `struct kvm_riscv_nested_vm`
  - 新增 `struct kvm_riscv_nested_vcpu`
  - 在 `struct kvm_arch` / `struct kvm_vcpu_arch` 挂接 nested state
  - 新增 nested API 声明
- `arch/riscv/kvm/vm.c`
  - `kvm_arch_init_vm()` 接入 `kvm_riscv_nested_vm_init()`
  - `kvm_arch_destroy_vm()` 接入 `kvm_riscv_nested_vm_deinit()`
- `arch/riscv/kvm/vcpu.c`
  - `kvm_arch_vcpu_create()` 接入 `kvm_riscv_nested_vcpu_init()`
  - `kvm_riscv_reset_vcpu()` 接入 `kvm_riscv_nested_vcpu_reset()`
  - `kvm_arch_vcpu_destroy()` 接入 `kvm_riscv_nested_vcpu_deinit()`
- `arch/riscv/kvm/Makefile`
  - 新增 `kvm-y += nested.o`

## Build check
- Command: `make ARCH=riscv M=arch/riscv/kvm -j4`
- Result: failed
- Root cause: kernel tree 未 prepare，缺失：
  - `include/generated/autoconf.h`
  - `include/generated/rustc_cfg`
  - `include/config/auto.conf`

## Next step (iter-3)
1. 增加 feature gate（module param 或 capability），确保 nested path 可控启停。
2. 在 trap/exit 关键路径预留最小 hook（不改变现有执行语义）。
3. 在可编译环境完成 `make prepare` 后做编译与最小 kselftest/kvm-unit-tests 计划验证。
