# RISC-V KVM 缺失特性：PV Time / Stolen Time（半虚拟化时间）

## 差异概述
arm64 KVM 实现了 PV time（偷取时间）机制：guest 可通过 SMCCC hypercall 启用，KVM 更新共享页中的 stolen time，配套的 guest 侧 paravirt 代码消费该信息；RISC-V KVM 未实现类似机制，也没有 pvclock ABI 定义。

## arm64 现状（实现要点）
- PV time 数据结构与更新：`arch/arm64/kvm/pvtime.c`
  - `kvm_update_stolen_time()` 在 vcpu 运行时更新共享页中的 stolen_time。
  - `kvm_init_stolen_time()` 初始化共享页。
- 启用/查询入口：`arch/arm64/kvm/guest.c` 中的 `kvm_arm_pvtime_set_attr()/get_attr()`。
- hypercall 入口：`arch/arm64/kvm/hypercalls.c` 中处理 `ARM_SMCCC_HV_PV_TIME_*`。
- guest 侧消费：`arch/arm64/kernel/paravirt.c` 使用 `asm/pvclock-abi.h`。

参考代码片段（arm64）：
```c
// arch/arm64/kvm/pvtime.c
void kvm_update_stolen_time(struct kvm_vcpu *vcpu) { ... }
```

```c
// arch/arm64/kvm/hypercalls.c
case ARM_SMCCC_HV_PV_TIME_FEATURES:
case ARM_SMCCC_HV_PV_TIME_ST:
    return test_bit(KVM_REG_ARM_STD_HYP_BIT_PV_TIME, ...);
```

## RISC-V 现状（缺失与证据）
- arch/riscv 下无 pvtime/pvclock 相关实现与 ABI 头文件（`arch/riscv/include/asm/` 中也无 `pvclock-abi.h`）。
- `arch/riscv/kvm` 中未见 PV time 相关 set/get attr 或 hypercall 路径。

## 缺失影响
- 在高超配或频繁调度场景下，guest 无法获取“被剥夺的 CPU 时间”，会影响负载评估与时间统计精度。
- 与 x86/arm64 的行为不一致，影响跨架构的 guest 行为一致性。

## 可支持性分析（RISC-V 侧）
- PV time 是纯软件 ABI，与 ISA 强依赖较弱。
- RISC-V 可通过新增 KVM/RISC-V 专用的 PV time ABI 或 SBI 扩展来实现。
- 共享页机制与 stolen time 的更新逻辑可直接借鉴 arm64 实现。

## 设计/实现路径建议
1. **定义 RISC-V PV time ABI**
   - 方式 A：新增 KVM ioctls / KVM device attr 绑定 PV time 页。
   - 方式 B：新增 SBI 扩展（类似 ARM 的 SMCCC PV time），但需固件与用户态协作。
2. **共享页与 stolen time 更新**
   - 复用 `pvclock_vcpu_stolen_time` 结构（可放入 `arch/riscv/include/asm/pvclock-abi.h`）。
   - 在 vcpu 运行/退出处更新 stolen_time（类似 `kvm_update_stolen_time()`）。
3. **Guest 侧 paravirt 接口**
   - 新增 `arch/riscv/kernel/paravirt.c`，提供 stolen time 读取 API。

## 关键难点
- ABI 选择（KVM 私有 vs SBI 标准）与兼容性策略。
- guest 与 host 的页共享与一致性（需要严格对齐与同步约束）。

## 参考文件（建议阅读）
- `arch/arm64/kvm/pvtime.c`
- `arch/arm64/kvm/hypercalls.c`
- `arch/arm64/kvm/guest.c`
- `arch/arm64/kernel/paravirt.c`
