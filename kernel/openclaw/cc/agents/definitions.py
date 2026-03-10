"""
Agent定义 - 定义各个探索Agent的具体任务
"""

# Agent-1: Linux代码仓库分析
LINUX_CODE_ANALYZER = {
    'name': 'linux-code-analyzer',
    'agent_type': 'Explore',
    'description': '分析RISC-V vs ARM/x86 Linux内核代码差异',
    'prompt': '''分析Linux内核中RISC-V与ARM/x86在KVM虚拟化支持上的差距。

## 分析维度

### 1. KVM支持差异
- arch/arm/kvm/ vs arch/riscv/kvm/
- 缺失的功能对比

### 2. 处理器特性支持
- SVE/SME (ARM) vs RISC-V Vector
- PMU事件支持
- 调试机制

### 3. 虚拟化特性
- 嵌套虚拟化
- 内存管理 (EPT vs Sv39/Sv48/Sv57)
- 中断控制器 (GIC vs AIA)

### 4. 性能特性
- TLB shootdown
- IPI效率
- 调度器优化

请详细列出每个差距项，包括：
- 功能名称
- ARM/x86实现状态
- RISC-V当前状态
- 相关文件路径
- 缺失的函数/特性
'''
}

# Agent-2: KVM邮件列表挖掘
KVM_MAIL_LIST_MINER = {
    'name': 'kvm-mail-list-miner',
    'agent_type': 'Explore',
    'description': '从KVM邮件列表获取最新RISC-V KVM讨论',
    'prompt': '''从KVM邮件列表(https://yhbt.net/lore/kvm/)获取最新的RISC-V KVM讨论信息。

## 任务

1. 搜索关键词: RISC-V, riscv, KVM, virtualization

2. 分析内容:
   - 最近的RISC-V KVM讨论
   - 已知的限制和待解决项
   - 开发者社区反馈
   - 正在进行的工作

3. 提取关键信息:
   - 邮件主题和摘要
   - 参与者
   - 讨论的问题
   - 建议的解决方案

请提供完整的邮件列表分析报告。
'''
}

# Agent-3: 现有文档分析
EXISTING_DOCS_ANALYZER = {
    'name': 'existing-docs-analyzer',
    'agent_type': 'Explore',
    'description': '分析linux-riscv-docs现有文档',
    'prompt': '''分析linux-riscv-docs仓库中的现有文档。

## 检查内容

1. docs/riscv/ 目录结构
2. 现有的差距分析文档
3. 之前创建的Issue状态
4. 已有的工作成果

## 输出要求

- 列出所有相关文档
- 总结已有的差距分析
- 标记已完成和待处理的工作
- 识别文档中的过时信息
'''
}

# Agent定义映射
AGENT_DEFINITIONS = {
    'linux-code-analyzer': LINUX_CODE_ANALYZER,
    'kvm-mail-list-miner': KVM_MAIL_LIST_MINER,
    'existing-docs-analyzer': EXISTING_DOCS_ANALYZER
}


def get_agent_prompt(agent_name: str) -> str:
    """获取Agent的完整提示词"""
    agent = AGENT_DEFINITIONS.get(agent_name)
    if agent:
        return agent['prompt']
    return ''


def get_agent_config(agent_name: str) -> dict:
    """获取Agent配置"""
    return AGENT_DEFINITIONS.get(agent_name, {})
