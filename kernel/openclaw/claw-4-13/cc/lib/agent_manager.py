"""
Agent管理器 - 负责创建和管理多Agent团队
"""
import os
import json
import subprocess
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from datetime import datetime


@dataclass
class AgentConfig:
    """Agent配置"""
    name: str
    agent_type: str
    model: str
    max_iterations: int
    description: str
    tools: List[str]


@dataclass
class TaskResult:
    """任务结果"""
    agent_name: str
    status: str  # success, failed, pending
    output: Dict[str, Any]
    errors: List[str]
    start_time: datetime
    end_time: Optional[datetime] = None


class AgentManager:
    """Agent管理器"""

    def __init__(self, config_path: str = None):
        self.config_path = config_path or self._get_default_config()
        self.config = self._load_config()
        self.tasks: Dict[str, TaskResult] = {}
        self.team_id = None

    def _get_default_config(self) -> str:
        """获取默认配置路径"""
        base_dir = os.path.dirname(os.path.abspath(__file__))
        return os.path.join(os.path.dirname(base), "config", "workflow.yaml")

    def _load_config(self) -> Dict[str, Any]:
        """加载配置"""
        import yaml
        with open(self.config_path, 'r') as f:
            return yaml.safe_load(f)

    def create_team(self, team_name: str) -> str:
        """创建Agent团队"""
        self.team_id = team_name
        return team_name

    def spawn_agent(
        self,
        agent_type: str,
        name: str,
        prompt: str,
        model: str = None,
        isolation: str = None
    ) -> Dict[str, Any]:
        """生成Agent执行任务"""
        from anthropic import Anthropic

        config = self.config.get('agents', {}).get(agent_type, {})
        model = model or config.get('model', 'sonnet')

        # 使用Claude Code的Agent功能
        agent_config = {
            'subagent_type': agent_type,
            'name': name,
            'prompt': prompt,
            'model': model
        }

        if isolation:
            agent_config['isolation'] = isolation

        # 这里应该调用实际的Agent执行
        # 由于这是工作流定义，我们返回配置而不是执行
        return {
            'status': 'configured',
            'agent_config': agent_config,
            'task': prompt
        }

    def run_parallel_agents(
        self,
        agent_configs: List[Dict[str, str]]
    ) -> List[Dict[str, Any]]:
        """并行运行多个Agent"""
        results = []
        for config in agent_configs:
            result = self.spawn_agent(
                agent_type=config['agent_type'],
                name=config['name'],
                prompt=config['prompt'],
                model=config.get('model')
            )
            results.append(result)
        return results

    def get_agent_definition(self, agent_type: str) -> Dict[str, Any]:
        """获取Agent定义"""
        definitions = {
            'explorer': {
                'description': '探索Agent，用于代码仓库和文档分析',
                'tools': ['Read', 'Grep', 'Glob', 'WebFetch'],
                'model': 'haiku'
            },
            'codex': {
                'description': '代码编写Agent',
                'tools': ['Write', 'Edit', 'Bash'],
                'model': 'sonnet'
            },
            'code-reviewer': {
                'description': '代码审查Agent',
                'tools': ['Read', 'Grep', 'Glob', 'Bash'],
                'model': 'sonnet'
            },
            'security-reviewer': {
                'description': '安全审查Agent',
                'tools': ['Read', 'Grep', 'Glob'],
                'model': 'sonnet'
            },
            'tdd-guide': {
                'description': 'TDD指导Agent',
                'tools': ['Read', 'Write', 'Edit', 'Bash'],
                'model': 'sonnet'
            }
        }
        return definitions.get(agent_type, {})


# Agent通信协议
class AgentProtocol:
    """Agent通信协议"""

    @staticmethod
    def create_message(
        sender: str,
        recipient: str,
        content: str,
        message_type: str = 'message'
    ) -> Dict[str, Any]:
        """创建消息"""
        return {
            'type': message_type,
            'sender': sender,
            'recipient': recipient,
            'content': content,
            'timestamp': datetime.now().isoformat()
        }

    @staticmethod
    def create_status_update(
        agent: str,
        status: str,
        progress: float,
        message: str
    ) -> Dict[str, Any]:
        """创建状态更新"""
        return {
            'type': 'status',
            'agent': agent,
            'status': status,
            'progress': progress,
            'message': message,
            'timestamp': datetime.now().isoformat()
        }

    @staticmethod
    def create_approval_request(
        from_agent: str,
        checkpoint: str,
        details: Dict[str, Any]
    ) -> Dict[str, Any]:
        """创建审批请求"""
        return {
            'type': 'approval',
            'from': from_agent,
            'checkpoint': checkpoint,
            'details': details,
            'timestamp': datetime.now().isoformat()
        }


# 人类审核节点管理
class CheckpointManager:
    """检查点管理器"""

    def __init__(self, config: Dict[str, Any]):
        self.checkpoints = config.get('checkpoints', [])
        self.completed_checkpoints: List[str] = []

    def get_checkpoint(self, name: str) -> Optional[Dict[str, Any]]:
        """获取检查点配置"""
        for cp in self.checkpoints:
            if cp['name'] == name:
                return cp
        return None

    def requires_human_approval(self, name: str) -> bool:
        """检查是否需要人类审核"""
        checkpoint = self.get_checkpoint(name)
        if checkpoint:
            return checkpoint.get('human_approval', False)
        return False

    def mark_completed(self, name: str):
        """标记检查点完成"""
        if name not in self.completed_checkpoints:
            self.completed_checkpoints.append(name)

    def is_completed(self, name: str) -> bool:
        """检查检查点是否完成"""
        return name in self.completed_checkpoints

    def get_pending_checkpoints(self) -> List[str]:
        """获取待完成的检查点"""
        return [cp['name'] for cp in self.checkpoints
                if cp['name'] not in self.completed_checkpoints]
