# RISC-V / ARM 虚拟化性能测试方案（全生命周期覆盖）

## 1. 文档目的

本方案用于评估 RISC-V 与 ARM 在虚拟化场景下的性能开销，并且覆盖虚拟机从创建到销毁的完整生命周期。输出目标是：

- 建立可重复、可审计、可回归的测试流程。
- 量化各生命周期阶段的开销构成。
- 形成跨架构可比的性能基线与回归阈值。

适用范围：

- RISC-V：以 `H` 扩展为核心，联合 `Sstc`、`Svnapot` 等可选特性分组评估。
- ARM：以 `FEAT_VHE` 与 Generic Timer 为核心分组评估。

---

## 2. 评估对象与边界

评估对象：

- Hypervisor/KVM 内核路径开销。
- VMM（QEMU）管理路径开销。
- VM 生命周期管理（libvirt/virsh）开销。
- Guest 可感知业务性能开销。

不在本方案中的内容：

- 功能正确性细节（仅作为前置门槛，不展开功能测试设计）。
- 单一设备驱动的微观调优（可在专项方案中追加）。

---

## 3. 生命周期阶段定义

本方案统一采用 11 阶段生命周期模型：

| 阶段ID | 阶段名称 | 起止定义 |
|---|---|---|
| 0 | 准备/定义 | 镜像准备、`virsh define` 开始到定义完成 |
| 1 | 创建/启动 | `virsh start/create` 到 QEMU 进程稳定运行 |
| 2 | 引导就绪 | 启动后到 guest 健康探针首次成功 |
| 3 | 空闲运行 | 无业务负载，维持稳定 5-10 分钟 |
| 4 | 负载运行 | CPU/内存/网络/存储负载执行窗口 |
| 5 | 动态变更 | vCPU/memory hotplug、balloon、memslot 变化 |
| 6 | 快照 | snapshot 创建与回滚窗口 |
| 7 | 实时迁移 | 迁移启动到目标端服务恢复 |
| 8 | 暂停/恢复 | suspend 到 resume 完成 |
| 9 | 重启 | reboot 命令发起到服务恢复 |
| 10 | 关机/销毁 | shutdown/destroy 到资源回收完毕 |

---

## 4. 测试矩阵设计

### 4.1 架构维度

RISC-V 分组：

- `H=on` vs `H=off`（硬件允许时）。
- `Sstc=on` vs `Sstc=off`。
- `Svnapot=on` vs `Svnapot=off`。

ARM 分组：

- `VHE=on` vs `VHE=off`。
- Generic Timer 默认配置作为统一基线。

### 4.2 资源规格维度

- 小规格：`2 vCPU / 4G RAM / 20G disk`
- 中规格：`4 vCPU / 8G RAM / 50G disk`
- 大规格：`8 vCPU / 16G RAM / 100G disk`

### 4.3 负载维度

- CPU：`stress-ng`, 内核编译。
- 内存：`stream`, pointer-chasing。
- 存储：`fio`（randread/randwrite/sequential）。
- 网络：`iperf3`（单流、多流）。
- 混合：`hackbench` 或业务混合流量回放。

---

## 5. 每阶段指标、工具与判定标准

| 阶段 | 核心指标 | 采集工具 | 建议回归阈值 |
|---|---|---|---|
| 0 准备/定义 | define latency、失败率 | `virsh`, libvirt 事件日志 | 时延回退 > 5% 告警 |
| 1 创建/启动 | create latency、QEMU 初始化时延 | `virsh`, `journalctl`, QMP | 时延回退 > 5% 告警 |
| 2 引导就绪 | boot-to-ready、固件到内核切换时长 | serial log、agent/SSH 探针 | 时延回退 > 5% 告警 |
| 3 空闲运行 | host CPU%、VM-exit/s、RSS | `kvm_stat`, `perf`, `pidstat` | VM-exit/s 增长 > 8% 告警 |
| 4 负载运行 | 吞吐、P99 延迟、overhead% | `fio`, `iperf3`, `perf stat` | 吞吐下降 > 5% 告警 |
| 5 动态变更 | hotplug latency、性能跌落窗口 | `virsh`, `KVM selftests` | 热插拔时延 > 10% 告警 |
| 6 快照 | snapshot latency、stun time | `virsh snapshot-*`, QMP | stun 增长 > 10% 告警 |
| 7 实时迁移 | total time、downtime、收敛轮次 | `virsh migrate`, KVM 日志 | downtime 增长 > 10% 告警 |
| 8 暂停/恢复 | suspend/resume latency、恢复抖动 | `virsh`, 业务探针 | 恢复抖动 > 10% 告警 |
| 9 重启 | reboot-to-ready | `virsh`, guest 探针 | 时延回退 > 5% 告警 |
| 10 关机/销毁 | shutdown/destroy latency、回收滞后 | `virsh`, cgroup/procfs | 回收滞后 > 10% 告警 |

说明：

- 阈值可按团队历史基线调整，首次建立基线时建议使用宽阈值（5%/8%/10%）。
- 对迁移和快照类操作，优先看 P99 与最坏值，不只看均值。

---

## 6. 权威测试套件组合

不存在单一套件覆盖全生命周期，建议如下组合：

- 生命周期状态机与管理面：`libvirt TCK`。
- VMM 启动/设备/迁移路径：`QEMU tests/functional`。
- KVM 内核关键路径：`Linux KVM selftests`。
- Guest 架构行为与陷入路径：`kvm-unit-tests`。
- 系统侧通用回归：`Linux kselftest`。
- RISC-V ISA 前置门槛：`riscv-arch-test + RISCOF`。
- ARM 平台能力前置门槛：`sysarch-acs`。

---

## 7. 测试执行流程

### 7.1 前置门槛

1. 记录软硬件版本：BIOS/固件、内核、QEMU、libvirt、toolchain。
2. 完成前置合规门槛：
   - RISC-V：`RISCOF` 与 `riscv-arch-test`。
   - ARM：`sysarch-acs`。
3. 固定测试环境：
   - CPU governor 固定。
   - 绑核与隔离（避免噪声）。
   - 关闭无关后台任务。

### 7.2 生命周期用例编排

1. `define -> start -> ready`。
2. idle 观测。
3. 注入负载窗口（CPU/内存/IO/网络）。
4. 执行 hotplug/balloon/memslot 变更。
5. 执行 snapshot 与 rollback。
6. 执行 live migration（pre-copy + post-copy 可分开）。
7. 执行 suspend/resume。
8. 执行 reboot。
9. 执行 shutdown/destroy/undefine。

### 7.3 统计规则

- 每个 case 至少 30 次独立重复。
- 输出：P50/P95/P99、均值、标准差、95% CI。
- 同时保留原始事件时间戳，支持离线重算。

---

## 8. 数据采集规范

建议统一输出 CSV/JSON 字段：

| 字段 | 示例 |
|---|---|
| arch | `riscv64` / `arm64` |
| profile | `H_on_Sstc_on` / `VHE_on` |
| vm_size | `small` / `medium` / `large` |
| lifecycle_stage | `boot_ready` |
| metric_name | `latency_ms` |
| metric_value | `842.31` |
| run_id | `20260212-001` |
| host_kernel | `6.12.x` |
| qemu_ver | `9.x` |
| libvirt_ver | `10.x` |
| timestamp | ISO8601 |

统一原则：

- 时钟统一：host NTP 同步，guest 仅用于辅助观察，不作为唯一时间源。
- 指标以 host 侧为主，guest 侧用于补充业务可感知数据。

---

## 9. 自动化落地建议

建议建立三层流水线：

1. `L1-门槛层`：合规/功能门槛（失败即终止）。
2. `L2-微基准层`：KVM/selftests/kvm-unit-tests。
3. `L3-生命周期层`：libvirt + QEMU + 宏基准混合回归。

建议目录结构：

```text
perf-lifecycle/
  scripts/
    run_lifecycle.sh
    collect_metrics.sh
    analyze_regression.py
  configs/
    riscv64-h-on.yaml
    arm64-vhe-on.yaml
  reports/
    raw/
    summary/
```

建议 gating 规则：

- 任一关键指标超过阈值直接 `FAIL`。
- 连续 3 次波动接近阈值标记 `UNSTABLE` 并要求复测。

---

## 10. 示例命令模板

```bash
# 1) 定义并启动
virsh define vm.xml
virsh start vm-test

# 2) 等待就绪（示例）
until ssh -o ConnectTimeout=2 guest "true"; do sleep 1; done

# 3) 运行负载
ssh guest "fio /opt/cases/randread.fio --output=/tmp/fio.json"
ssh guest "iperf3 -c <server_ip> -t 60 -J > /tmp/iperf.json"

# 4) 热插拔与快照
virsh setvcpus vm-test 6 --live
virsh snapshot-create-as vm-test snap1 --disk-only --atomic

# 5) 迁移
virsh migrate --live vm-test qemu+ssh://dst/system

# 6) 暂停恢复/重启/关机
virsh suspend vm-test
virsh resume vm-test
virsh reboot vm-test
virsh shutdown vm-test
virsh destroy vm-test
```

---

## 11. 输出物与验收标准

输出物：

- 生命周期阶段性能总表（跨架构对比）。
- 关键指标趋势图（P50/P95/P99）。
- 回归告警列表（含根因定位线索）。
- 复现实验包（配置、脚本、原始数据）。

验收标准：

- 生命周期 11 阶段全部可自动执行且有数据。
- RISC-V 与 ARM 至少各 2 组配置完成可比测试。
- 报告可复现，任意指标可追溯到原始日志。

---

## 12. 风险与规避

- 风险：平台负载噪声导致误判。  
  规避：绑核、隔离、重复采样、看 P99 与 CI。
- 风险：迁移网络抖动掩盖架构差异。  
  规避：专用迁移网络、固定带宽与时延。
- 风险：不同固件/内核版本引入隐性差异。  
  规避：版本锁定，报告中强制记录版本指纹。

---

## 13. 参考

1. RISC-V Hypervisor Extension  
   https://docs.riscv.org/reference/isa/priv/hypervisor.html
2. RISC-V Sstc  
   https://docs.riscv.org/reference/isa/priv/sstc.html
3. Linux KVM review checklist（含 selftests / kvm-unit-tests）  
   https://docs.kernel.org/6.17/virt/kvm/review-checklist.html
4. Linux kselftest  
   https://docs.kernel.org/dev-tools/kselftest.html
5. kvm-unit-tests  
   https://github.com/kvm-unit-tests/kvm-unit-tests
6. libvirt testing（TCK）  
   https://libvirt.org/testing.html
7. virsh manual  
   https://www.libvirt.org/manpages/virsh.html
8. QEMU functional tests  
   https://www.qemu.org/docs/master/devel/testing/functional.html
9. Arm System Architecture ACS  
   https://github.com/ARM-software/sysarch-acs

---

*文档版本：1.0*  
*日期：2026-02-12*
