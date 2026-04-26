# RISC-V / ARM 虚拟化性能折损评估方案（基于 SPEC CPU2006）

## 1. 目标与结论口径

本方案用于回答两个问题：

1. 在同一架构内（RISC-V 或 ARM），虚拟化带来的性能折损有多大？
2. 在相同测试方法下，RISC-V 与 ARM 的虚拟化折损谁更高？

核心结论不直接比较跨 ISA 的绝对跑分，而比较“虚拟化折损率”：

- `VirtEff = Score_VM / Score_Host`
- `VirtLoss = 1 - VirtEff`

跨架构比较指标：

- `Delta = VirtLoss_RISCV - VirtLoss_ARM`
- `Delta > 0`：RISC-V 折损更高；`Delta < 0`：ARM 折损更高。

---

## 2. 适用范围与边界

适用范围：

- 测试对象：KVM + QEMU（可选 libvirt/virsh 管理）。
- 基准套件：SPEC CPU2006（SPECint2006 + SPECfp2006）。
- 运行位置：Host（裸机）与 Guest（虚拟机）分别执行同一套测试。

边界说明：

- SPEC CPU2006 已于 **2018-01-09** 退役，不再接受官方提交通道；可用于内部研究与回归。
- 若结果对外发布，需遵守 SPEC Fair Use 与 Run Rules，并明确“CPU2006 已退役”。
- 本方案重点是“运行阶段”虚拟化折损，不覆盖完整生命周期（创建/迁移/销毁）；完整生命周期请参考单独文档。

---

## 3. 测试设计原则（保证可比性）

### 3.1 同架构 Host vs VM 公平性

- Host 与 VM 使用相同版本编译器、相同 SPEC config 文件。
- 使用相同 `--tune`（建议先 `base`）和相同 `--size=ref`。
- VM 配置固定：vCPU、内存、磁盘、NUMA 绑定一致。
- 固定频率策略（performance），避免动态频率干扰。
- vCPU 与 pCPU 1:1 绑核，禁止 overcommit（基础方案阶段）。

### 3.2 跨架构对比公平性

- 先在各自架构内计算 `VirtLoss`，再比较 `VirtLoss`，不比较裸分高低。
- 两个架构使用一致的方法学：相同重复次数、相同统计口径、相同阈值规则。
- 记录完整版本指纹：kernel/QEMU/libvirt/toolchain/SPEC v1.2。

---

## 4. 测试矩阵

### 4.1 架构矩阵

- `riscv64`
- `arm64`

### 4.2 运行形态矩阵

- `Host`（裸机）
- `VM`（KVM 虚拟机）

### 4.3 SPEC 维度矩阵

- 套件：`int`、`fp`
- 模式：
  - `SPECspeed`（单副本，单任务时延能力）
  - `SPECrate`（多副本，吞吐能力）
- 副本：
  - `1`
  - `N/2`
  - `N`（N 为分配给测试的物理核数）

### 4.4 重复策略

- 每个 case 至少 `5` 次独立重复（建议）。
- 执行顺序采用交错：`Host -> VM -> Host -> VM`，减小温漂与背景负载偏置。

---

## 5. 环境准备

### 5.1 软件版本（需在报告中固化）

- Host kernel 版本
- QEMU 版本
- KVM 能力（含架构相关特性）
- libvirt/virsh 版本（若使用）
- GCC/LLVM 版本
- SPEC CPU2006 版本（建议 v1.2）

### 5.2 系统设置

- CPU governor 固定为 `performance`。
- 关闭不必要后台服务与定时任务。
- 使用 `isolcpus` 或 cpuset 保证测试核隔离（可选但推荐）。
- VM 使用固定内存（禁止自动 balloon）和固定 vCPU 拓扑。

### 5.3 许可与合规

- 确认 SPEC CPU2006 许可证满足内部测试使用。
- 对外报告时附带 run rules/fair use 合规声明。

---

## 6. 执行步骤（可直接落地）

### 6.1 Host 基线跑分

建议命令模板（示例）：

```bash
# SPECspeed: int/fp
runspec --config=baseline.cfg --tune=base --size=ref --noreportable \
        --iterations=3 --output_format=raw,csv int
runspec --config=baseline.cfg --tune=base --size=ref --noreportable \
        --iterations=3 --output_format=raw,csv fp

# SPECrate: copies=N
runspec --config=baseline.cfg --tune=base --size=ref --rate N --noreportable \
        --iterations=3 --output_format=raw,csv int
runspec --config=baseline.cfg --tune=base --size=ref --rate N --noreportable \
        --iterations=3 --output_format=raw,csv fp
```

说明：

- 研究型评估推荐 `--noreportable`，效率更高；
- 若需要完全“可公开规则”结果，按 run rules 切换 `--reportable` 与完整约束。

### 6.2 VM 跑分

- Guest 内执行与 Host **完全相同**的 runspec 参数和 config。
- 仅允许 VM 相关差异（虚拟 CPU、虚拟设备、虚拟中断等），其余参数保持一致。

### 6.3 同步采集虚拟化开销指标（Host 侧）

- `kvm_stat`：VM-exit 相关统计。
- `perf stat`：`cycles/instructions/cache-misses/dTLB-load-misses/branch-misses`。
- `pidstat`/`mpstat`：QEMU 进程与系统级 CPU 占用。

目的：

- 当某些 benchmark 折损异常时，可回溯到 VM-exit 密度、TLB 行为或缓存行为变化。

---

## 7. 数据处理与统计

### 7.1 单项折损

对每个 benchmark `b`：

- `VirtEff_b = Score_VM_b / Score_Host_b`
- `VirtLoss_b = 1 - VirtEff_b`

### 7.2 套件级折损

使用几何平均（geomean）聚合：

- `GM_Host = geomean(Score_Host_b)`
- `GM_VM   = geomean(Score_VM_b)`
- `VirtEff_suite = GM_VM / GM_Host`
- `VirtLoss_suite = 1 - VirtEff_suite`

分别对 `SPECint2006` 和 `SPECfp2006` 计算。

### 7.3 置信区间与显著性

- 每 case 输出：均值、标准差、P50/P95/P99。
- 建议使用 bootstrap 计算 95% CI。
- 若两架构 `VirtLoss` 的 CI 大量重叠，不给“显著优劣”结论。

---

## 8. 报告模板（建议）

### 8.1 表格

- 表1：Host/VM 原始分数（每个 benchmark，按架构分组）。
- 表2：`VirtEff_b` 与 `VirtLoss_b`（每个 benchmark）。
- 表3：`VirtLoss_suite`（int/fp/speed/rate）。
- 表4：跨架构 `Delta` 与 CI。

### 8.2 图形

- 图1：各 benchmark 折损柱状图（RISC-V vs ARM）。
- 图2：套件级折损对比图（int/fp 分开）。
- 图3：`VirtLoss_b` vs VM-exit/s 散点图（解释性分析）。

### 8.3 结论写法

- 主结论：哪个架构虚拟化折损更低（按 int/fp、speed/rate 分别给结论）。
- 次结论：折损来源（exit、TLB、缓存）与可能优化方向。
- 限制项：硬件代际差异、编译器成熟度、Guest 内核差异。

### 8.4 可直接填报的数据表模板（未来测试结果）

#### 表A：测试环境与版本指纹（每轮测试一份）

| run_id | 日期 | 架构 | 平台型号 | Host Kernel | QEMU | KVM 能力摘要 | 编译器 | SPEC 版本 | 备注 |
|---|---|---|---|---|---|---|---|---|---|
| 2026xxxx-001 | TBD | riscv64 | TBD | TBD | TBD | H=on,Sstc=on,Svnapot=on | GCC/LLVM TBD | CPU2006 v1.2 | TBD |
| 2026xxxx-002 | TBD | arm64 | TBD | TBD | TBD | VHE=on | GCC/LLVM TBD | CPU2006 v1.2 | TBD |

#### 表B：原始跑分记录（benchmark 级，Host/VM 对照）

| run_id | 架构 | 模式 | 套件 | benchmark | Host 分数 | VM 分数 | VirtEff | VirtLoss | 备注 |
|---|---|---|---|---|---:|---:|---:|---:|---|
| TBD | riscv64 | speed | int | 400.perlbench | TBD | TBD | TBD | TBD | |
| TBD | riscv64 | speed | int | 401.bzip2 | TBD | TBD | TBD | TBD | |
| TBD | riscv64 | speed | int | 403.gcc | TBD | TBD | TBD | TBD | |
| TBD | arm64 | speed | int | 400.perlbench | TBD | TBD | TBD | TBD | |
| TBD | arm64 | speed | int | 401.bzip2 | TBD | TBD | TBD | TBD | |
| TBD | arm64 | speed | int | 403.gcc | TBD | TBD | TBD | TBD | |

说明：完整测试时请覆盖全部 int/fp 子项；此表仅示例前几项格式。

#### 表C：重复试验统计（case 级，建议 5 次以上）

| case_id | 架构 | Host/VM | 模式 | 套件 | 次数N | 均值 | stddev | P50 | P95 | P99 | 95% CI |
|---|---|---|---|---|---:|---:|---:|---:|---:|---:|---|
| riscv64-speed-int-host | riscv64 | Host | speed | int | TBD | TBD | TBD | TBD | TBD | TBD | [TBD, TBD] |
| riscv64-speed-int-vm | riscv64 | VM | speed | int | TBD | TBD | TBD | TBD | TBD | TBD | [TBD, TBD] |
| arm64-speed-int-host | arm64 | Host | speed | int | TBD | TBD | TBD | TBD | TBD | TBD | [TBD, TBD] |
| arm64-speed-int-vm | arm64 | VM | speed | int | TBD | TBD | TBD | TBD | TBD | TBD | [TBD, TBD] |

#### 表D：套件级汇总（几何平均）

| 架构 | 模式 | 套件 | GM_Host | GM_VM | VirtEff_suite | VirtLoss_suite |
|---|---|---|---:|---:|---:|---:|
| riscv64 | speed | int | TBD | TBD | TBD | TBD |
| riscv64 | speed | fp | TBD | TBD | TBD | TBD |
| riscv64 | rate | int | TBD | TBD | TBD | TBD |
| riscv64 | rate | fp | TBD | TBD | TBD | TBD |
| arm64 | speed | int | TBD | TBD | TBD | TBD |
| arm64 | speed | fp | TBD | TBD | TBD | TBD |
| arm64 | rate | int | TBD | TBD | TBD | TBD |
| arm64 | rate | fp | TBD | TBD | TBD | TBD |

#### 表E：跨架构折损差值（最终对比核心表）

| 模式 | 套件 | VirtLoss_RISCV | VirtLoss_ARM | Delta (RISCV-ARM) | 结论 |
|---|---|---:|---:|---:|---|
| speed | int | TBD | TBD | TBD | TBD |
| speed | fp | TBD | TBD | TBD | TBD |
| rate | int | TBD | TBD | TBD | TBD |
| rate | fp | TBD | TBD | TBD | TBD |

结论字段建议：

- `RISC-V 折损更低`
- `ARM 折损更低`
- `差异不显著（CI 重叠）`

#### 表F：开销归因关联（辅助解释）

| 架构 | benchmark | VirtLoss | VM-exit/s | cycles | instructions | dTLB-load-misses | cache-misses | 归因备注 |
|---|---|---:|---:|---:|---:|---:|---:|---|
| riscv64 | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |
| arm64 | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |

#### 表G：发布版摘要（用于报告首页）

| 指标 | riscv64 | arm64 | 备注 |
|---|---:|---:|---|
| VirtLoss(speed,int) | TBD | TBD | |
| VirtLoss(speed,fp) | TBD | TBD | |
| VirtLoss(rate,int) | TBD | TBD | |
| VirtLoss(rate,fp) | TBD | TBD | |
| 平均折损（四项均值） | TBD | TBD | 可选指标 |
| 最差单项折损 | TBD | TBD | 指明 benchmark |

---

## 9. 风险与规避

- 风险：Host/VM 资源争用污染结果。  
  规避：专机测试、绑核、固定内存。
- 风险：热管理导致后半程降频。  
  规避：交错执行 + 记录温度与频率。
- 风险：仅看均值掩盖尾部退化。  
  规避：强制输出 P95/P99 与 CI。
- 风险：跨 ISA 误用“绝对分数”比较。  
  规避：只比较 `VirtLoss`，不比较裸分高低。

---

## 10. 与全生命周期方案的关系

本方案是“生命周期第 4 阶段（负载运行）”的专项量化方法。  
如果要做完整虚拟化评估，应与以下阶段联动：

- 创建/启动时延
- 快照/迁移开销
- 暂停恢复抖动
- 关机销毁与资源回收

建议将本方案输出的 `VirtLoss` 作为生命周期总评中的“运行效率分项”。

---

## 11. 交付清单

- `spec2006_raw/`：每次 runspec 生成的 `*.rsf` 与 `*.csv`
- `metrics_raw/`：`kvm_stat/perf/pidstat` 原始日志
- `summary.csv`：标准化聚合结果
- `report.md`：含图表与结论

---

## 12. 参考资料

1. SPEC CPU2006 首页（退役声明与说明）  
   https://www.spec.org/cpu2006/
2. SPEC CPU2006 Run Rules  
   https://www.spec.org/cpu2006/Docs/runrules.html
3. runspec 使用文档  
   https://www.spec.org/cpu2006/docs/runspec.html
4. Linux KVM review checklist（测试套件建议）  
   https://docs.kernel.org/6.17/virt/kvm/review-checklist.html
5. Linux kselftest 文档  
   https://docs.kernel.org/dev-tools/kselftest.html
6. QEMU functional tests  
   https://www.qemu.org/docs/master/devel/testing/functional.html

---

*文档版本：1.0*  
*日期：2026-02-12*  
*备注：若需要对外发布结果，请额外附带 SPEC fair use 合规声明与退役披露。*
