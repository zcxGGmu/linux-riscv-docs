# RISC-V vs ARM/x86 Linux内核差距分析工作流

基于多Agent系统的自动化工作流，用于分析RISC-V与ARM/x86在Linux内核支持上的差距，并生成可提交的Patch。

## 项目结构

```
cc/
├── agents/              # Agent定义
│   └── definitions.py  # Agent任务定义
├── config/             # 配置文件
│   └── workflow.yaml   # 工作流配置
├── lib/                # 核心库
│   ├── agent_manager.py      # Agent管理
│   ├── github_client.py      # GitHub API
│   ├── kernel_analyzer.py    # 内核分析
│   └── mail_client.py        # 邮件发送
├── scripts/            # 执行脚本
│   ├── setup.sh              # 环境设置
│   ├── create_issues.py      # Issue创建
│   ├── code_development.py   # 代码开发
│   └── patch_utils.py        # Patch生成
├── templates/          # 模板
│   ├── issue-template.md
│   └── design-template.md
├── workflows/          # 工作流编排
│   └── riscv_gap_analysis.py
├── reports/            # 分析报告
│   └── gap-analysis-report.md
└── main.py             # CLI入口
```

## 快速开始

### 1. 环境设置

```bash
# 安装依赖
pip install -r requirements.txt

# 运行设置脚本
bash scripts/setup.sh
```

### 2. 运行工作流

```bash
# 运行完整工作流
python main.py

# 运行特定步骤
python main.py --step 1  # 探索研究
python main.py --step 2  # Issue创建
python main.py --step 3  # 开发方案设计
python main.py --step 4  # 代码开发
python main.py --step 5  # Patch生成
```

### 3. 单独使用各个模块

```bash
# 创建Issue
python scripts/create_issues.py --list          # 列出预设差距
python scripts/create_issues.py --dry-run       # 模拟运行
python scripts/create_issues.py --token YOUR_TOKEN

# 代码开发
python scripts/code_development.py --compile    # 编译
python scripts/code_development.py --test       # 测试

# Patch管理
python scripts/patch_utils.py format            # 生成patch
python scripts/patch_utils.py send patch.patch  # 发送patch
```

## 工作流说明

### Step 1: 探索研究
- Agent-1: 分析Linux内核代码差异
- Agent-2: 挖掘KVM邮件列表
- Agent-3: 分析现有文档

### Step 2: Issue创建
基于分析结果自动创建GitHub Issue

### Step 3: 开发方案设计
为每个差距项生成技术设计文档

### Step 4: 代码开发循环
- Codex编写代码
- 构建验证
- 测试运行
- 代码审查

### Step 5: Patch生成与发送
- 生成patch
- 格式校验
- 发送到KVM邮件列表

## 配置

编辑 `config/workflow.yaml` 修改:
- GitHub仓库配置
- Linux仓库路径
- 邮件服务器配置
- 检查点设置

## 已知差距项

| 优先级 | 功能 |
|-------|------|
| P0 | VMID分配器优化 |
| P0 | PV Time实现 |
| P1 | 嵌套虚拟化 |
| P1 | AIA/IMSIC虚拟化 |
| P2 | 硬件断点支持 |
| P2 | PMU虚拟化 |

## 环境变量

- `GITHUB_TOKEN`: GitHub访问令牌
- `GITHUB_OWNER`: 仓库所有者
- `GITHUB_REPO`: 仓库名
- `LINUX_REPO_PATH`: Linux内核仓库路径
- `SMTP_*`: 邮件服务器配置
