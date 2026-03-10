# RV-KVM-NESTED-001: RISC-V KVM 嵌套虚拟化实现计划

## Issue 概述

| 属性 | 值 |
|------|-----|
| Gap ID | RV-KVM-NESTED-001 |
| 类型 | feature (功能实现) |
| 严重等级 | P0 |
| 置信度 | high |
| 验收标准 | 具备可验证的 nested guest 运行能力，最小通过 kvm-unit-tests nested 场景并补充自测脚本 |

**摘要**: RISC-V KVM 缺少与 ARM64/x86 对齐的完整嵌套虚拟化能力（L2 guest execution 路径未完整实现）

---

## 1. 现状分析

### 1.1 当前 RISC-V KVM 状态

- ✅ 已支持 Hypervisor 扩展 (H-extension)
- ✅ 已支持 G-stage (Stage-2) 页表
- ✅ 已支持 VMID (Virtual Machine ID)
- ✅ 已支持 SBI HFENCE 调用 (TLB flush)
- ❌ **嵌套虚拟化 (Nested Virtualization) 未实现**
- ❌ **SBI HFENCE 调用返回 NOT_SUPPORTED** (见 vcpu_sbi_replace.c:130)

### 1.2 ARM64/x86 对齐参考

| 功能 | ARM64 | x86 (VMX/SVM) | RISC-V (当前) |
|------|-------|---------------|---------------|
| Nested vCPU 初始化 | kvm_vcpu_init_nested() | VMX/SVM 各自实现 | ❌ 无 |
| Shadow Stage-2 MMU | 完整支持 | 完整支持 | ❌ 无 |
| VNCR_EL2 存储 | 完整支持 | N/A | ❌ 无 |
| L2 退出处理 | 完整支持 | 完整支持 | ❌ 无 |
| Hypervisor 调用转发 | 完整支持 | 完整支持 | 部分 (HFENCE 未实现) |

---

## 2. File-Level Design

### 2.1 新增文件结构

```
arch/riscv/kvm/
├── nested.c              # [NEW] 嵌套虚拟化核心逻辑
├── nested.h              # [NEW] 嵌套虚拟化头文件
├── vcpu_nested.c         # [NEW] vCPU 嵌套状态管理
├── vcpu_nested.h         # [NEW] vCPU 嵌套头文件
├── Makefile              # [MOD] 添加 nested.o 编译```

### 2
.2 核心数据结构设计

#### 2.2.1 嵌套 vCPU 状态结构 (`arch/riscv/include/asm/kvm_nested.h`)

```c
struct kvm_riscv_nested_vcpu {
    /* L2 (nested) vCPU 状态 */
    bool                enabled;           /* 嵌套模式是否启用 */
    unsigned long       vmid;              /* L2 VMID */
    unsigned long       hgatp;              /* L2 HGATP CSR */
    unsigned long       vsatp;              /* L2 VSATP CSR (Sv39/48/57) */

    /* 嵌套阶段-2 页表 (Shadow S2) */
    struct kvm_s2_mmu   *s2_mmu;           /* shadow MMU 指针 */

    /* L1/L2 寄存器状态转换 */
    struct kvm_cpu_context  guest_ctxt;    /* L2 guest 上下文 */
    struct kvm_cpu_context  host_ctxt;     /* L1 hypervisor 上下文 */

    /* L2 执行统计 */
    atomic64_t          l2_run_count;       /* L2 运行次数 */
    atomic64_t          l2_exit_count;     /* L2 退出次数 */
};

struct kvm_riscv_nested_state {
    /* VM 级别嵌套状态 */
    struct kvm_s2_mmu   **nested_mmus;      /* L2 MMU 数组 */
    u32                 nested_mmus_size;  /* MMU 数组大小 */
    unsigned long       nested_vmid_next;  /* 下一个可用 VMID */

    /* 嵌套配置 */
    bool                nested_enabled;    /* VM 嵌套支持标志 */
};
```

#### 2.2.2 新增 KVM_RUN 标志 (`uapi/asm/kvm.h`)

```c
/* arch/riscv/include/uapi/asm/kvm.h */
#define KVM_RUN_NESTED            0x00000001  /* 运行 L2 guest */
```

### 2.3 核心函数接口

#### 2.3.1 VM 级别接口 (`nested.c`)

```c
/* VM 嵌套初始化/清理 */
int  kvm_riscv_nested_init(struct kvm *kvm);
void kvm_riscv_nested_destroy(struct kvm *kvm);

/* L2 MMU 管理 */
int  kvm_riscv_nested_init_s2_mmu(struct kvm *kvm, struct kvm_s2_mmu *mmu);
void kvm_riscv_nested_destroy_s2_mmu(struct kvm *kvm, struct kvm_s2_mmu *mmu);

/* VMID 分配/释放 */
u16  kvm_riscv_nested_alloc_vmid(struct kvm *kvm);
void kvm_riscv_nested_free_vmid(struct kvm *kvm, u16 vmid);
```

#### 2.3.2 vCPU 级别接口 (`vcpu_nested.c`)

```c
/* vCPU 嵌套初始化/清理 */
int  kvm_riscv_vcpu_init_nested(struct kvm_vcpu *vcpu);
void kvm_riscv_vcpu_destroy_nested(struct kvm_vcpu *vcpu);

/* 嵌套模式控制 */
int  kvm_riscv_vcpu_set_nested(struct kvm_vcpu *vcpu,
                               struct kvm_nested_state *state);
int  kvm_riscv_vcpu_get_nested(struct kvm_vcpu *vcpu,
                               struct kvm_nested_state *state);

/* L2 运行入口 */
int  kvm_riscv_vcpu_run_nested(struct kvm_vcpu *vcpu, struct kvm_run *run);

/* L2 退出处理 */
int  kvm_riscv_handle_nested_exit(struct kvm_vcpu *vcpu,
                                  struct kvm_run *run,
                                  struct kvm_cpu_trap *trap);
```

### 2.4 SBI HFENCE 转发实现

#### 修改 `vcpu_sbi_replace.c`

```c
// 当前代码 (line 130-133):
/*
 * Until nested virtualization is implemented, the
 * SBI HFENCE calls should return not supported
 * hence fallthrough.
 */

// 修改后:
case SBI_EXT_RFENCE_REMOTE_HFENCE_GVMA:
case SBI_EXT_RFENCE_REMOTE_HFENCE_GVMA_VMID:
case SBI_EXT_RFENCE_REMOTE_HFENCE_VVMA:
case SBI_EXT_RFENCE_REMOTE_HFENCE_VVMA_ASID:
    ret = kvm_riscv_nested_hfence转发(vcpu, &param);
    break;
```

#### 新增 `nested_sbi.c` (SBI 嵌套转发)

```c
int kvm_riscv_nested_sbi_hfence_gvma(struct kvm_vcpu *vcpu,
                                      unsigned long hbase,
                                      unsigned long hmask,
                                      unsigned long gpa,
                                      unsigned long gva,
                                      unsigned long vmid);

int kvm_riscv_nested_sbi_hfence_vvma(struct kvm_vcpu *vcpu,
                                      unsigned long hbase,
                                      unsigned long hmask,
                                      unsigned long gva,
                                      unsigned long asid,
                                      unsigned long vmid);
```

### 2.5 Exit 处理流程

```
L1 Guest Exit
    │
    ├─── HVC/SBI Call ───> kvm_riscv_vcpu_run()
    │                          │
    │                          ├── 嵌套启用? ──YES──> run_nested()
    │                          │                        │
    │                          │                        ├── 加载 L2 上下文
    │                          │                        ├── 设置 HGATP = L2's hgatp
    │                          │                        ├── 执行 HFENCE
    │                          │                        └── 进入 L2 guest
    │                          │
    │                          NO (标准路径)
    │
    ├─── Stage-2 Page Fault ──> kvm_riscv_gstage_map()
    │                               │
    │                               ├── 嵌套启用? ──YES──> nested_gstage_map()
    │                               │                        (需处理 L2 页表映射)
    │                               │
    │                               NO (标准 gstage map)
    │
    └─── Other Exits ──────────> kvm_riscv_handle_exit()
```

---

## 3. Test Matrix

### 3.1 kselftest 测试

**目标**: 验证 KVM API 和 SBI 接口正确性

| 测试用例 | 描述 | 预期结果 |
|---------|------|----------|
| `kvm_riscv_nested_vmid` | VMID 分配/释放正确性 | 正确分配唯一 VMID |
| `kvm_riscv_nested_sbi_hfence` | SBI HFENCE 调用转发 | 正确转发到 L2 hypervisor |
| `kvm_riscv_nested_state_set` | 嵌套状态设置/获取 | 状态正确保存/恢复 |
| `kvm_riscv_nested_run` | KVM_RUN_NESTED 标志 | L2 guest 可启动 |
| `kvm_riscv_nested_invalid` | 无效嵌套配置 | 返回正确错误码 |

**位置**: `tools/testing/selftests/kvm/riscv/nested.c`

### 3.2 kvm-unit-tests

**目标**: 端到端验证 L2 guest 执行

| 测试用例 | 描述 | 验收标准 |
|---------|------|----------|
| `nested_guest_boot` | L2 guest 启动 | L2 kernel 成功 boot 到 userspace |
| `nested_guest_run` | L2 guest 运行 | L2 guest 可执行基本指令 |
| `nested_guest_exit` | L2 guest 退出 | L2 exit 正确触发并处理 |
| `nested_sbi_hfence` | SBI HFENCE 转发 | L1 hypervisor 收到 HFENCE |
| `nested_mmio` | L2 MMIO | MMIO 正确路由到 L1 |
| `nested_page_fault` | L2 页 Fault | gstage/nested gstage 正确处理 |

**位置**: `arch/riscv/kvm/nested.c` (已有框架) 或新建 `arch/riscv/kvm/unit-tests/nested.c`

### 3.3 perf 测试

**目标**: 性能基准测试

| 测试项 | 指标 | 说明 |
|--------|------|------|
| `nested_vmentry_latency` | L2 vmentry 延迟 | < 10us (vs baseline) |
| `nested_exit_latency` | L2 exit 延迟 | < 5us (vs baseline) |
| `hfence_overhead` | HFENCE 转发开销 | 可忽略 (< 1%) |
| `nested_tlb_miss` | L2 TLB miss 率 | vs 非嵌套 baseline |

**脚本**: `tools/perf/bench/kvm-riscv-nested.sh`

### 3.4 手动测试 Checkpoint

```bash
# 1. QEMU 启动 (需要支持 nested 的 QEMU)
qemu-system-riscv64 \
    -machine virt \
    -cpu rv64gc_zicsr_zifencei_zihintntl,sv57 \
    -enable-kvm \
    -kernel Image \
    -append "console=hvc0 root=/dev/vda" \
=rootfs.img    -drive file,format=raw,id=hd0 \
    -netdev user,id=net0 -device virtio-net-pci,netdev=net0

# 2. L1 KVM 加载
modprobe kvm
modprobe kvm_riscv

# 3. 嵌套测试
# 运行 nested selftest
./kvm_riscv_nested_vmid
./kvm_riscv_nested_state_set
# 运行 unit test
./nested_guest_boot
./nested_guest_run
```

---

## 4. Rollback & Risk Notes

### 4.1 回滚方案

#### 4.1.1 快速回滚 (代码级)

```bash
# 如果发现严重问题，使用以下命令回滚
git revert <commit_hash>
# 或
git checkout <previous_tag>
```

#### 4.1.2 功能开关回滚

新增内核启动参数:

```
kvm_riscv.nested=off  # 禁用嵌套虚拟化
```

在 `kvm_riscv_nested_init()` 中检查:

```c
static bool nested_enabled = true;

static int __init kvm_riscv_nested_setup(char *s)
{
    if (!s || strcmp(s, "off") == 0)
        nested_enabled = false;
    return 1;
}
__setup("kvm_riscv.nested=", kvm_riscv_nested_setup);
```

#### 4.1.3 SBI 降级

如果 SBI HFENCE 转发导致问题，恢复原有行为:

```c
case SBI_EXT_RFENCE_REMOTE_HFENCE_GVMA:
    if (!nested_enabled) {
        retdata->err_val = SBI_ERR_NOT_SUPPORTED;
        break;
    }
    // 新逻辑
    ret = kvm_riscv_nested_sbi_hfence(...);
    break;
```

### 4.2 风险分析

| 风险项 | 严重度 | 概率 | 缓解措施 |
|--------|--------|------|----------|
| **VMID 资源耗尽** | HIGH | 中 | 实现 VMID 回收机制，超限返回错误 |
| **Shadow S2 MMU 内存泄漏** | HIGH | 低 | 严格审查 gstage.c 中的 MMU 生命周期管理 |
| **L2 Exit 处理遗漏** | HIGH | 中 | 分阶段实现，优先覆盖常见 exit 类型 (PF, MMIO, HVC) |
| **与现有 H-extension 冲突** | MEDIUM | 低 | 详细审查 hypervisor.hypermode 相关代码 |
| **性能退化** | MEDIUM | 中 | 实现前后对比 perf test，退化 > 10% 需优化 |
| **ABI 不兼容** | MEDIUM | 低 | 与 ARM64/x86 保持 API 对齐，审查 KVM_GET/SET_SREGS |
| **QEMU 未支持** | LOW | 中 | 验证 upstream QEMU 支持情况，必要时提供 patch |

### 4.3 实现阶段风险控制

| 阶段 | 目标 | 风险级别 | 门禁 |
|------|------|----------|------|
| Phase 1 | VMID + S2 MMU 基础 | LOW | 编译通过 + 基本单元测试 |
| Phase 2 | vCPU 嵌套状态 | MEDIUM | kselftest 通过 |
| Phase 3 | SBI HFENCE 转发 | MEDIUM | SBI 测试通过 |
| Phase 4 | Exit 处理 | HIGH | kvm-unit-tests 通过 |
| Phase 5 | 完整集成 | HIGH | 手动验证 + perf baseline |

---

## 5. Upstreaming Strategy

### 5.1 补丁系列规划

建议按以下顺序发送补丁系列:

| Patch # | 描述 | 依赖 |
|---------|------|------|
| 1/10 | Add KVM nested structures (kvm_nested.h) | 无 |
| 2/10 | Add KVM nested MMU support | #1 |
| 3/10 | Add VMID allocation for nested | #2 |
| 4/10 | Add vCPU nested state management | #1, #3 |
| 5/10 | Implement kvm_riscv_nested_init/destroy | #1-4 |
| 6/10 | Implement kvm_riscv_vcpu_run_nested() | #4-5 |
| 7/10 | Add SBI HFENCE forwarding | #5 |
| 8/10 | Handle L2 exits (PF/MMIO) | #6 |
| 9/10 | Add kselftests | #1-8 |
| 10/10 | Add kvm-unit-tests | #1-9 |

### 5.2 邮件列表提交

**To**: kvm@vger.kernel.org, linux-riscv@lists.infradead.org
**Cc**: Anup Patel <anup.patel@wdc.com>, Atish Patra <atish.patra@wdc.com>
**Subject**: [RFC PATCH 0/10] RISC-V KVM nested virtualization support

### 5.3 Upstream 里程碑

```
Milestone 1: [v1] RFC - 架构设计和基础结构
    ↓
Milestone 2: [v2] 基础 VMID + MMU 支持
    ↓
Milestone 3: [v3] vCPU 嵌套运行 + SBI HFENCE
    ↓
Milestone 4: [v4] Exit 处理 + 测试
    ↓
Milestone 5: [v5] 完整功能 + 性能优化 → Merged!
```

### 5.4 审查关注点

发送给 upstream 时需准备回复:

1. **为什么不用 ARM64 的方式?**
   - 答: 保持与 RISC-V Hypervisor 扩展 (H-extension) 一致，使用 SBI 作为 L1/L2 接口

2. **VMID 空间规划?**
   - 答: 使用 16-bit VMID，与 G-stage 保持一致，支持 65536 个嵌套 VM

3. **性能考虑?**
   - 答: 使用 vCPU-specific shadow MMU，与 ARM64 相同策略

4. **测试覆盖?**
   - 答: 提供 kselftest + kvm-unit-tests + perf benchmarks

---

## 6. 实现时间线估算

| 阶段 | 工作量 | 预计时间 | 交付物 |
|------|--------|----------|--------|
| 架构设计 | 2-3 人日 | 1 周 | 本文档 |
| Phase 1 | 5-7 人日 | 2 周 | nested.c 基础框架 |
| Phase 2 | 5-7 人日 | 2 周 | vCPU 嵌套状态 |
| Phase 3 | 3-5 人日 | 1 周 | SBI HFENCE |
| Phase 4 | 7-10 人日 | 3 周 | Exit 处理 |
| 测试 | 5-7 人日 | 2 周 | kselftest + unit tests |
| **总计** | **27-39 人日** | **~11-13 周** | **功能可用** |

---

## 7. 参考资料

- [LORE: riscv nested kvm](https://yhbt.net/lore/kvm/?q=riscv+nested)
- ARM64 KVM Nested: `arch/arm64/kvm/nested.c`
- x86 KVM Nested: `arch/x86/kvm/vmx/nested.c`
- RISC-V Hypervisor Spec: [RISC-V Hypervisor Extension](https://github.com/riscv/riscv-hypervisor)
- KVM API Documentation: Documentation/virt/kvm/api.rst
