# Linux arm64 vs riscv Kconfig 差异分析 TODO（规划版）

## 0. 目标与交付边界
- 目标：基于 `arch/arm64/Kconfig` 对照 `arch/riscv/Kconfig`，系统识别 riscv 缺失的内核配置能力，并给出：
  - 不支持原因（技术根因）
  - 可支持性评估（是否可移植、依赖什么前置条件）
  - arm64 对应特性的提交描述与 Linux 补丁/提交链接
  - 按模块归类的 gap 清单（内存、调度、SIMD 等）
- 输出风格：证据链可追溯（`Kconfig符号 -> 代码位置 -> 提交 -> patch链接`）。

## 1. 前置约束与分析口径（执行前锁定）
- [ ] 锁定基线内核版本（建议双轨）  
  1. 主分析版本：一个固定稳定 tag（例如 `v6.x`）  
  2. 补充趋势版本：最新主线 tag（用于观察“已在路上”的补齐项）
- [ ] 锁定“缺失”定义（3 类）  
  1. `ABSENT`：arm64 可见/可配，riscv 无该配置符号  
  2. `UNREACHABLE`：riscv 有符号但依赖不可满足，实际不可启用  
  3. `NO_BACKEND`：符号存在但实现能力缺失或仅 stub
- [ ] 锁定分析范围  
  - 主范围：`arch/arm64/Kconfig` 与其 include 链 vs `arch/riscv/Kconfig` 与其 include 链  
  - 扩展范围：必要时追踪到 `drivers/`, `kernel/`, `mm/`, `virt/` 的依赖符号

## 2. 数据采集与自动化框架
- [ ] 准备数据源
  - Linux 主线源码（带完整 git 历史）
  - 本地分析仓库下新建结果目录：`work/kconfig-gap/`
- [ ] 编写符号提取脚本（推荐 Python + Kconfiglib）
  - 输出 `arm64_symbols.csv`、`riscv_symbols.csv`
  - 字段：`symbol,type,prompt,file,depends_on,selects,implies,default,visible_if`
- [ ] 构建可比对基线
  - 同一版本、同一工具链口径下提取
  - 记录提取命令和环境信息（保证可复现）
- [ ] 生成原始差异
  - 输出 `arm64_only.csv`（arm64 支持、riscv 不支持）
  - 输出 `riscv_blocked.csv`（riscv 存在但不可达）

## 3. 差异项逐条深挖（核心分析）
- [ ] 为每个差异符号建立分析卡片（单条记录）
  - `符号名`
  - `arm64侧功能定义`
  - `riscv侧状态(ABSENT/UNREACHABLE/NO_BACKEND)`
  - `不支持根因分类`
  - `是否可支持(Yes/Partial/No)`
  - `支持前置条件(ISA扩展/硬件能力/固件接口/子系统重构)`
  - `风险与工作量(低/中/高)`
- [ ] 根因分类标准（统一口径）
  - ISA/特权架构差异
  - MMU/页表/异常模型差异
  - 中断/计时器/拓扑差异
  - 虚拟化模型差异（KVM/Guest/Hypervisor）
  - 固件与引导链差异（ACPI/EFI/SMBIOS/SBI）
  - 厂商绑定或平台专有能力
  - 上游尚未移植（工程债务/维护资源）
- [ ] 可支持性判断规则
  - `Yes`：已有硬件与ISA基础，仅缺内核实现
  - `Partial`：部分平台可做，存在生态限制
  - `No`：与 riscv 当前架构目标冲突或无现实需求

## 4. 提交与补丁证据链（满足你的第2条要求）
- [ ] 为每个差异符号追踪 arm64 对应特性提交
  - 优先找“首次引入功能”的提交
  - 次选“关键使能提交”（若首次提交仅框架）
- [ ] 固化每条证据字段
  - `commit_hash`
  - `commit_title`
  - `commit_message_summary(2~4行)`
  - `kernel.org commit link`
  - `patch link`（lore/patchwork/kernel.org patch）
  - `是否为该功能主提交(Yes/No)`
- [ ] 证据质量规则
  - 链接必须可打开
  - 提交描述必须与该符号功能直接相关
  - 若无单一补丁可对应，标注“补丁集”并列出主链接

## 5. 模块化归类（满足你的第3条要求）
- [ ] 定义模块分类字典（主类+次类）
  - 内存/MMU
  - 调度/拓扑/CPUfreq/能耗模型
  - SIMD/向量/加密
  - 虚拟化（KVM/Guest/嵌套）
  - 中断/定时器/时钟源
  - 安全/隔离/硬化
  - 启动与固件（ACPI/EFI/SBI）
  - RAS/诊断/trace/perf
  - IOMMU/IO子系统
- [ ] 每个 gap 至少归入一个主模块
- [ ] 生成模块视图
  - `module_gap_summary.md`：按模块列出缺失项与优先级
  - `module_gap_count.csv`：模块统计计数与占比

## 6. 增强项（在基础要求上扩展）
- [ ] Gap 优先级评分（建议）
  - 维度：业务影响、实现难度、上游活跃度、硬件可得性
  - 产出：`P0/P1/P2` 优先级队列
- [ ] 时间维度趋势分析（建议）
  - 对比两个版本，区分：
    - 已补齐
    - 新增差距
    - 长期未动差距
- [ ] 上游状态补充（建议）
  - 标注是否已有 RFC/patchset 正在推进

## 7. 结果文件清单（执行阶段的目标产物）
- [ ] `work/kconfig-gap/raw/arm64_symbols.csv`
- [ ] `work/kconfig-gap/raw/riscv_symbols.csv`
- [ ] `work/kconfig-gap/raw/arm64_only.csv`
- [ ] `work/kconfig-gap/raw/riscv_blocked.csv`
- [ ] `work/kconfig-gap/evidence/arm64_feature_commits.csv`
- [ ] `work/kconfig-gap/report/riscv_gap_by_module.md`
- [ ] `work/kconfig-gap/report/riscv_gap_master_table.md`
- [ ] `work/kconfig-gap/report/executive_summary.md`

## 8. 主报告模板（最终交付结构）
- [ ] 摘要：结论、风险、优先级路线图
- [ ] 方法：数据来源、版本、判定标准
- [ ] 全量差异表：逐条符号分析
- [ ] 模块视图：内存/调度/SIMD/虚拟化等章节
- [ ] 证据附录：commit 与 patch 链接索引
- [ ] 误差与限制：无法精确映射项、争议项说明

## 9. 验收标准（完成判定）
- [ ] arm64 相对 riscv 的缺失项覆盖率 >= 95%（Kconfig层面）
- [ ] 每个缺失项都包含“原因 + 可支持性 + 证据链接”
- [ ] 每个缺失项都完成模块归类
- [ ] 抽样复核（>= 20 项）无明显误判
- [ ] 全部链接有效且可追溯

## 10. 执行节奏建议（确认后实施）
- 阶段A（数据抽取与初筛）：1~2 天
- 阶段B（逐条深挖与证据链）：2~4 天
- 阶段C（模块报告与优先级）：1~2 天
- 阶段D（复核与收敛）：1 天

---

## 待你确认的3个关键决策（确认后开始执行）
- [ ] 使用哪个主分析版本（固定 tag）？
- [ ] 报告输出语言是否统一为中文（含 commit 摘要）？
- [ ] 是否开启增强项（优先级评分 + 趋势分析 + 上游状态）？
