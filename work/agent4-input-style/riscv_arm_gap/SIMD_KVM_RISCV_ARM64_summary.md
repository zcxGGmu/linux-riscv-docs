# KVM SIMD 支持差异与改进建议（arm64 vs riscv）整合版

> 本文整合了 SIMD 相关的 6 个细分文档（07–12），面向内核/KVM 视角汇总现状、差异、影响与可改进方向。

## 执行摘要
- **最大结构性差异**：arm64 通过 SVE 提供可协商向量长度与完善 ABI；riscv 的 RVV 仍是宿主镜像暴露、vlenb 固定、扩展不可精细禁用。
- **迁移/快照痛点**：VLEN 与 ZV*/Zfh/Zfbfmin 的不一致会直接导致迁移失败或不兼容。
- **优化优先级**：先做“可禁用子扩展 + per-VM 策略接口 + 按需分配”，再考虑“懒惰切换”和“虚拟 VLEN”。

## 一页对比表（SIMD 相关）
| 维度 | arm64 KVM | riscv KVM | 主要差异/风险 |
|---|---|---|---|
| 向量长度协商 | SVE 可配置 VL（`KVM_CAP_ARM_SVE`） | RVV vlenb 固定、只读 | 迁移同构限制、ABI 不灵活 |
| SIMD 懒惰切换 | EL2 trap + lazy save/restore | 入口/退出强制保存 | 小用量场景性能损失 |
| SIMD 状态分配 | SVE 状态按需分配 | RVV 上下文固定分配 | 内存开销大、无条件分配 |
| ZV* 子扩展 | 可由实现策略决定 | 宿主镜像暴露且不可禁用 | 兼容/策略控制不足 |
| Zfh/Zfbfmin | 可由实现策略决定 | 默认暴露且不可禁用 | 迁移降级困难 |
| 迁移/快照 | 有可变 VL 的 ABI 机制 | vlenb 绑定宿主 | 不同 VLEN 主机无法迁移 |

## 1. 向量长度 ABI 与协商能力（arm64 SVE vs riscv RVV）
### 现状差异
- **arm64**：SVE 支持可配置向量长度（VL），提供 `KVM_CAP_ARM_SVE` 与 `KVM_REG_ARM64_SVE_*` ABI；guest 可协商/限制 VL。
- **riscv**：RVV 的 `vlenb` 固定为宿主 VLEN（`riscv_v_vsize/32`），且 `vlenb` 只读，缺少协商能力。

### 代码证据
- `arch/arm64/kvm/arm.c`：`KVM_CAP_ARM_SVE`
- `arch/arm64/kvm/reset.c`：`kvm_arm_init_sve()` / `kvm_vcpu_finalize_sve()`
- `arch/riscv/kvm/vcpu_vector.c`：`vlenb` 固定 + 只读
- `arch/riscv/kvm/vcpu_onereg.c`：向量寄存器大小依赖 `vlenb`

### 影响
- 迁移与兼容性受限（VLEN 不一致直接失败）。
- 上层管理软件难以做跨平台统一策略。

### 建议
- 引入 `guest_vlenb` 概念与 capability（可选，见第 6 节）。
- 在 KVM 中允许“虚拟 VLEN = 宿主 VLEN 子集”。

## 1.1 RISC-V KVM 的 ISA 掩码控制路径（与 SIMD 直接相关）
### 现状
- KVM 通过 `KVM_REG_RISCV_ISA_EXT`（single/multi）向用户态暴露/设置扩展掩码。
- 扩展可否启用/禁用由 `kvm_riscv_vcpu_isa_enable_allowed()` / `kvm_riscv_vcpu_isa_disable_allowed()` 决定；多数 ZV* 与 Zfh/Zfbfmin **不可禁用**。
- 一旦 vCPU 运行过（`ran_atleast_once`），扩展掩码的修改会返回 `-EBUSY`。

### 代码证据
- `arch/riscv/kvm/vcpu_onereg.c`：
  - `kvm_riscv_vcpu_set_reg_isa_ext()` -> `riscv_vcpu_set_isa_ext_single()`
  - `riscv_vcpu_set_isa_ext_single()` 中若 `ran_atleast_once` 返回 `-EBUSY`
  - `kvm_riscv_vcpu_isa_disable_allowed()` 中包含 ZV*/Zfh/Zfbfmin 的“不可禁用”列表

### 影响
- 用户态只能在 vCPU 首次运行前做一次性配置，且对 ZV*/Zfh/Zfbfmin 无法关闭。

### 建议
- 将 ZV* 与 Zfh/Zfbfmin 从“不可禁用”列表中放开，配合依赖校验逻辑。
- 若要保持向后兼容，可引入 “默认不变但允许显式禁用” 的策略开关。

## 2. SIMD 上下文切换策略：懒惰切换 vs 入口/退出强制保存
### 现状差异
- **arm64**：通过 EL2 trap 实现“首次使用触发 + 懒惰切换”，只有 guest 触发 FP/SIMD/SVE 时才保存/恢复。
- **riscv**：在 `kvm_arch_vcpu_load/put()` 入口/退出路径直接保存/恢复 FP 与向量上下文。

### 代码证据
- `arch/arm64/kvm/hyp/include/hyp/switch.h`：`kvm_hyp_handle_fpsimd()`
- `arch/arm64/kvm/hyp/vhe/switch.c`：EC_FP_ASIMD/EC_SVE trap
- `arch/riscv/kvm/vcpu.c`：`kvm_riscv_vcpu_host_fp_save()`/`guest_fp_restore()` + vector 同步

### 影响
- 当 guest 很少使用 SIMD 时，riscv 仍然有高频保存/恢复开销。

### 建议
- 引入“first-use trap”机制（利用 VS/FS 位与非法指令路径）。
- 只有触发 SIMD 时才保存/恢复 guest 上下文。

## 3. SIMD 状态内存分配策略
### 现状差异
- **arm64**：SVE 状态按需分配，且与 guest 选择的 VL 匹配。
- **riscv**：V 扩展上下文在 vCPU 创建时固定分配两份（host/guest），大小 = `riscv_v_vsize`。

### 代码证据
- `arch/arm64/kvm/reset.c`：`kvm_vcpu_finalize_sve()` 按 VL 分配
- `arch/riscv/kvm/vcpu_vector.c`：`kzalloc(riscv_v_vsize)` 固定分配

### 影响
- VLEN 较大时，每 vCPU 内存占用大。
- 未启用 RVV 的 guest 也被迫分配向量状态。

### 建议
- 只在确认 guest 启用 V 时分配向量状态。
- 若实现 `guest_vlenb`，按 guest VLEN 精确分配。

## 4. RVV 子扩展（ZV*）的默认暴露策略
### 现状
- KVM 将 ZV* 扩展映射到 ISA mask 中，并默认“宿主有即暴露给 guest”。
- 多数 ZV* 扩展 **不可禁用**（`kvm_riscv_vcpu_isa_disable_allowed()` 返回 false）。

### 代码证据
- `arch/riscv/kvm/vcpu_onereg.c`：`kvm_isa_ext_arr[]` 包含 ZV*；禁用列表包含 ZV*。
- `arch/riscv/kernel/cpufeature.c`：ZV* 的依赖校验与 bundled 扩展逻辑。

### 影响
- 迁移场景无法用“guest 屏蔽 ZV*”来实现兼容。
- 缺少 per-VM 精细策略（安全/一致性控制不足）。

### 建议
- 允许禁用 ZV* 子扩展（调整 disable 规则）。
- 提供 per-VM/ per-vCPU 的扩展策略接口。

## 5. FP16/BF16（Zfh/Zfbfmin）在 guest 侧的暴露与寄存器行为
### 现状
- Zfh/Zfbfmin 纳入 KVM ISA mask，但默认暴露且不可禁用。
- 不新增寄存器文件，仍由 F/D 上下文保存逻辑覆盖。

### 代码证据
- `arch/riscv/kvm/vcpu_onereg.c`：映射 + 不可禁用
- `arch/riscv/kernel/cpufeature.c`：依赖 F 扩展
- `arch/riscv/kvm/vcpu_fp.c`：仅区分 F/D 保存

### 影响
- 迁移场景缺少“降级”手段。
- 用户态无法对 FP16/BF16 精细控制。

### 建议
- 允许禁用 Zfh/Zfbfmin。
- 在迁移策略中显式检查并对齐这些扩展。

## 6. 向量上下文迁移/快照 ABI 策略
### 现状
- `vlenb` 只读且固定为宿主 VLEN；向量寄存器大小依赖 `vlenb`。
- 迁移时若 VLEN 不一致，`KVM_SET_ONE_REG` 会因尺寸不匹配失败。

### 代码证据
- `arch/riscv/kvm/vcpu_vector.c`：`vlenb` 只读
- `arch/riscv/kvm/vcpu_onereg.c`：寄存器 size 依赖 `vlenb`
- `arch/riscv/include/uapi/asm/kvm.h`：向量寄存器 ABI 定义

### 建议的迁移策略
- **策略 A**（现状可用）：严格同构迁移（vlenb 必须一致）。
- **策略 B**（需改动 KVM）：虚拟 VLEN（guest_vlenb <= host_vlenb），以提升兼容性。
- **策略 C**（用户态增强）：快照中记录 vlenb 与向量寄存器 blob，恢复时校验。

## 7. 用户态可操作点（面向管理栈/迁移框架）
### 7.1 读写 ISA 扩展掩码（KVM_REG_RISCV_ISA_EXT）
- **读**：使用 `KVM_REG_RISCV_ISA_EXT` 的 single/multi reg 读取扩展可用位。
- **写**：必须在 vCPU 运行前完成；否则会被 `-EBUSY` 拒绝。
- **限制**：ZV* 与 Zfh/Zfbfmin 当前不可禁用（需内核改动）。

### 7.2 读取向量长度
- 读取 `KVM_REG_RISCV_VECTOR_CSR_REG(vlenb)`。
- 若发现目标主机 `vlenb` 不一致，应拒绝迁移或回退到非向量配置策略。

### 7.3 快照/迁移建议最小字段
- `vlenb`、`V` 扩展开关
- ZV* 子扩展掩码
- Zfh/Zfbfmin 掩码
- 向量寄存器 blob（v0–v31）与 vcsr/vtype/vl/vstart

## 8. 风险与回归点（实现改动时重点关注）
- **依赖一致性**：ZV* 与 Zfh/Zfbfmin 的 disable 必须与 `cpufeature` 依赖逻辑一致，否则可能暴露非法 ISA 组合。
- **ABI 兼容**：虚拟 VLEN 会影响 `KVM_REG_RISCV_VECTOR` 寄存器大小，必须定义清晰的用户态 ABI 版本/协商方式。
- **性能回归**：懒惰切换引入 trap 处理，需评估高 SIMD 负载场景下的开销。
- **安全性**：错误的寄存器保存/恢复可能泄露 host/guest SIMD 状态。

## 9. 测试建议（面向内核/用户态联合验证）
- **功能测试**：创建 vCPU -> 设置 ISA mask -> 运行简单 RVV/FP16/BF16 指令自测。
- **迁移测试**：同构与异构 VLEN 主机间迁移，确认 vlenb 校验与失败行为一致。
- **压力测试**：频繁 vCPU 切换 + SIMD 负载，评估懒惰切换或按需分配的性能差异。
- **兼容性测试**：启用/禁用 ZV*/Zfh/Zfbfmin 后运行向量加密/浮点指令集的用户态基准。

## 推荐的整体改进路线（优先级建议）
1. **允许禁用 ZV* 与 Zfh/Zfbfmin**（最小代价，提升兼容/控制能力）。
2. **引入 per-VM ISA 扩展策略接口**（对齐迁移/安全策略）。
3. **按需分配向量状态**（减少内存开销）。
4. **引入 SIMD “first-use trap” 懒惰切换**（优化性能）。
5. **虚拟 VLEN 支持**（最大收益，但实现复杂度高）。

---

## 相关源码索引
- RISC-V KVM：
  - `arch/riscv/kvm/vcpu_vector.c`
  - `arch/riscv/kvm/vcpu_fp.c`
  - `arch/riscv/kvm/vcpu_onereg.c`
  - `arch/riscv/include/uapi/asm/kvm.h`
- RISC-V ISA/向量子系统：
  - `arch/riscv/kernel/cpufeature.c`
  - `arch/riscv/include/asm/vector.h`
- arm64 KVM（对照）：
  - `arch/arm64/kvm/arm.c`
  - `arch/arm64/kvm/guest.c`
  - `arch/arm64/kvm/reset.c`
  - `arch/arm64/kvm/fpsimd.c`
  - `arch/arm64/kvm/hyp/include/hyp/switch.h`
