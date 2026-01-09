# RISC-V KVM 缺失特性：受保护虚拟化（pKVM 类隔离）

## 差异概述
arm64 已具备 pKVM（protected KVM）体系：将关键 hypervisor 逻辑放入受保护的 nVHE EL2 代码区，使用独立的内存与页表，隔离宿主内核与来宾；RISC-V KVM 当前没有类似的“受保护 hypervisor”框架，仍是典型的 HS-mode 内核内嵌虚拟化。

## arm64 现状（实现要点）
- pKVM 主流程与资源预留：`arch/arm64/kvm/pkvm.c`
  - `kvm_hyp_reserve()` 预留受保护 hypervisor 内存。
  - `pkvm_create_hyp_vm()`/`__pkvm_create_hyp_vm()` 创建 hyp 侧 VM/VCPU 对象。
- nVHE 受保护 hypervisor 代码与内存保护：`arch/arm64/kvm/hyp/nvhe/`
  - `mem_protect.c` 构建 host stage-2 与 hyp 页表隔离。
  - `hyp-main.c`/`hyp-init.S` 等承载 hyp 侧生命周期。

参考代码片段（arm64）：
```c
// arch/arm64/kvm/pkvm.c
void __init kvm_hyp_reserve(void) { ... }
int pkvm_create_hyp_vm(struct kvm *kvm) { ... }
```

```c
// arch/arm64/kvm/hyp/nvhe/mem_protect.c
int kvm_host_prepare_stage2(void *pgt_pool_base) { ... }
```

## RISC-V 现状（缺失与证据）
- arch/riscv/kvm 下无 pkvm.* 或 hyp 子系统实现，缺少独立 hypervisor 实体。
- 现有 `arch/riscv/kvm/nacl.c` 仅提供 SBI NACL 加速与共享内存接口，不提供 host/guest 的安全隔离能力。

## 缺失影响
- 无法在宿主内核被攻破时保护 guest 机密性与完整性。
- 无法提供“受保护/可信 VM”能力（类似 arm64 pKVM 的“host/guest 双向隔离”）。

## 可支持性分析（RISC-V 侧）
- RISC-V 具备 HS-mode 虚拟化扩展，且 M-mode 固件可以扮演安全监控或更高特权隔离层。
- 通过引入“更小的受保护 hypervisor 实体（类 pKVM）+ host stage-2 隔离”，理论上可在 RISC-V 上实现类似 pKVM 的安全边界。

## 设计/实现路径建议
1. **受保护 hypervisor 载入与内存隔离**
   - 引入独立的 hyp 镜像区域（可能位于 M-mode 管理的保护区或 HS-mode 独立页表域）。
   - 分离 host 与 hyp 的页表，并建立 host stage-2 保护，类似 arm64 `mem_protect.c`。
2. **VM/VCPU 结构体下沉至 hyp**
   - 参照 arm64 `__pkvm_create_hyp_vm()`，将关键 VM/VCPU 元数据移入 hyp 内存区。
3. **受保护 API 与对象生命周期**
   - 建立 host→hyp 的安全调用接口（类似 arm64 的 `kvm_call_hyp_nvhe()`），用于创建/销毁 VM/VCPU、更新页表等。
4. **与 SBI/固件协作**
   - 需要 SBI 或 M-mode 扩展用于保护内存范围与禁止 host 访问 hyp 内存。

## 关键难点
- RISC-V 平台当前缺乏通用、标准化的“隔离 hypervisor”固件接口。
- 需要处理 host 与 hyp 之间的上下文切换、性能开销与调试复杂度。
- 需要新的威胁模型与密钥/测量路径（若面向机密计算场景）。

## 参考文件（建议阅读）
- `arch/arm64/kvm/pkvm.c`
- `arch/arm64/kvm/hyp/nvhe/mem_protect.c`
- `arch/arm64/kvm/hyp/nvhe/hyp-main.c`
- `arch/riscv/kvm/nacl.c`
