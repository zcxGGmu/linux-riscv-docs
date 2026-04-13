# issue-1 iter-1 log

## Summary
本轮在 RISC-V KVM 中完成了 **HFENCE_GVMA / HFENCE_GVMA_VMID** 的最小转发实现，作为 nested 路径的第一步打底；未触及完整 L2 运行状态机。

## Code changes
- `arch/riscv/kvm/vcpu_sbi_replace.c`
  - 为 `SBI_EXT_RFENCE_REMOTE_HFENCE_GVMA` 新增实际调用：
    - `kvm_riscv_hfence_gvma_vmid_all`
    - `kvm_riscv_hfence_gvma_vmid_gpa`
  - 为 `SBI_EXT_RFENCE_REMOTE_HFENCE_GVMA_VMID` 新增 `cp->a4` VMID 分支
  - 新增 PMU 计数：
    - `SBI_PMU_FW_HFENCE_GVMA_SENT`
    - `SBI_PMU_FW_HFENCE_GVMA_VMID_SENT`
  - `HFENCE_VVMA/HFENCE_VVMA_ASID` 仍返回 `SBI_ERR_NOT_SUPPORTED`

## Build check
- Command: `make ARCH=riscv M=arch/riscv/kvm -j4`
- Result: failed
- Error: kernel source 未 prepare，缺少：
  - `include/generated/autoconf.h`
  - `include/generated/rustc_cfg`
  - `include/config/auto.conf`
- Suggested fix:
  - 在内核树执行 `make oldconfig && make prepare` 后再做模块编译检查。

## Next step (iter-2)
1. 引入最小 nested state（VM/vCPU 级）骨架，不改变默认行为（feature gate）。
2. 落一个可控开关（module param 或 capability gate）避免影响现有路径。
3. 在可编译环境补齐 `M=arch/riscv/kvm` 编译和最小自测记录。
