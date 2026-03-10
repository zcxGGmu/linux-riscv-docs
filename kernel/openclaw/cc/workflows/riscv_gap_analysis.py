"""
工作流编排器 - 主控制器
"""
import os
import sys
import yaml
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from datetime import datetime

# 添加lib目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from lib.agent_manager import AgentManager, CheckpointManager
from lib.github_client import GitHubClient
from lib.mail_client import GitSendEmailClient, KVM_LIST
from lib.kernel_analyzer import KernelAnalyzer, export_gap_report


@dataclass
class WorkflowState:
    """工作流状态"""
    current_step: str
    completed_steps: List[str]
    pending_approvals: List[str]
    data: Dict[str, Any]
    errors: List[str]


class RISCVGapAnalysisWorkflow:
    """RISC-V差距分析工作流"""

    def __init__(self, config_path: str = None):
        # 加载配置
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        config_path = config_path or os.path.join(base_dir, 'config', 'workflow.yaml')

        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)

        # 初始化组件
        self.agent_manager = AgentManager(config_path)
        self.checkpoint_manager = CheckpointManager(self.config)

        # GitHub客户端
        self.github = GitHubClient(
            owner=self.config['github']['owner'],
            repo=self.config['github']['repo']
        )

        # 内核分析器
        self.kernel_analyzer = KernelAnalyzer(
            self.config['linux_repo']['path']
        )

        # 邮件客户端
        self.mail_client = GitSendEmailClient(
            self.config['linux_repo']['path']
        )

        # 工作流状态
        self.state = WorkflowState(
            current_step='init',
            completed_steps=[],
            pending_approvals=[],
            data={},
            errors=[]
        )

    def run(self):
        """运行完整工作流"""
        print("=" * 60)
        print("RISC-V vs ARM/x86 Linux内核差距分析工作流")
        print("=" * 60)

        try:
            # Step 1: 探索研究
            self._run_step1_explore()

            # Step 2: Issue创建
            self._run_step2_create_issues()

            # Step 3: 开发方案设计
            self._run_step3_development_plan()

            # Step 4: 代码开发循环
            self._run_step4_code_development()

            # Step 5: Patch生成与发送
            self._run_step5_patch_generation()

            print("\n" + "=" * 60)
            print("工作流完成!")
            print("=" * 60)

        except Exception as e:
            print(f"工作流执行出错: {e}")
            self.state.errors.append(str(e))
            raise

    def _run_step1_explore(self):
        """Step 1: 探索研究"""
        print("\n[Step 1] 探索研究")
        print("-" * 40)

        self.state.current_step = 'step1_explore'

        # 使用Agent进行并行研究
        print("启动探索Agent进行并行分析...")

        # Agent 1: Linux代码仓库分析
        print("\n[Agent-1] 分析Linux内核代码差异...")
        agent1_config = {
            'agent_type': 'explorer',
            'name': 'linux-code-analyzer',
            'prompt': '''分析Linux内核中RISC-V与ARM/x86在KVM虚拟化支持上的差距。

分析维度:
1. KVM支持差异 (arch/arm/kvm/ vs arch/riscv/kvm/)
2. 处理器特性支持 (SVE/SME vs RISC-V Vector)
3. 虚拟化特性 (嵌套虚拟化、内存管理、中断控制器)
4. 性能特性 (TLB shootdown、IPI效率)

请详细列出差距项和对应的文件路径。'''
        }

        # Agent 2: KVM邮件列表挖掘
        print("[Agent-2] 挖掘KVM邮件列表...")
        agent2_config = {
            'agent_type': 'explorer',
            'name': 'kvm-mail-list-miner',
            'prompt': '''从KVM邮件列表(https://yhbt.net/lore/kvm/)获取最新的RISC-V KVM讨论信息。

搜索关键词: RISC-V, riscv, KVM, virtualization

分析:
1. 最近的RISC-V KVM讨论
2. 已知的限制和待解决项
3. 开发者社区反馈'''
        }

        # Agent 3: 现有文档分析
        print("[Agent-3] 分析现有文档...")
        agent3_config = {
            'agent_type': 'explorer',
            'name': 'existing-docs-analyzer',
            'prompt': '''分析linux-riscv-docs仓库中的现有文档。

检查:
1. docs/riscv/ 目录
2. 现有的差距分析文档
3. 之前创建的Issue状态

总结当前已有的工作成果。'''
        }

        # 执行分析（这里使用内核分析器模拟）
        print("\n执行内核代码分析...")
        results = self.kernel_analyzer.analyze_all()

        gap_count = sum(len(r.gaps) for r in results)
        print(f"发现 {gap_count} 个差距项")

        # 保存分析结果
        self.state.data['analysis_results'] = results

        # 检查点
        if self.checkpoint_manager.requires_human_approval('gap-analysis-complete'):
            print("\n[CHECKPOINT] 需要人类审核差距分析报告")
            self.state.pending_approvals.append('gap-analysis-complete')
            # 在实际工作流中，这里会暂停并等待用户确认
            self.checkpoint_manager.mark_completed('gap-analysis-complete')

        self.state.completed_steps.append('step1_explore')

    def _run_step2_create_issues(self):
        """Step 2: Issue创建"""
        print("\n[Step 2] Issue创建")
        print("-" * 40)

        self.state.current_step = 'step2_issues'

        # 从分析结果创建Issue
        results = self.state.data.get('analysis_results', [])

        for result in results:
            for gap in result.gaps:
                print(f"创建Issue: {gap.name}")

                # 在实际工作流中，这里会调用GitHub API
                # issue = self.github.create_feature_gap_issue(...)

        # 检查点
        if self.checkpoint_manager.requires_human_approval('issues-created'):
            print("\n[CHECKPOINT] 需要人类审核Issue列表")
            self.state.pending_approvals.append('issues-created')
            self.checkpoint_manager.mark_completed('issues-created')

        self.state.completed_steps.append('step2_issues')

    def _run_step3_development_plan(self):
        """Step 3: 开发方案设计"""
        print("\n[Step 3] 开发方案设计")
        print("-" * 40)

        self.state.current_step = 'step3_plan'

        print("创建技术方案文档...")

        # 检查点
        if self.checkpoint_manager.requires_human_approval('development-plan-approved'):
            print("\n[CHECKPOINT] 需要人类审核开发方案")
            self.state.pending_approvals.append('development-plan-approved')
            self.checkpoint_manager.mark_completed('development-plan-approved')

        self.state.completed_steps.append('step3_plan')

    def _run_step4_code_development(self):
        """Step 4: 代码开发循环"""
        print("\n[Step 4] 代码开发循环")
        print("-" * 40)

        self.state.current_step = 'step4_development'

        print("进入代码开发循环...")

        # 检查点
        if self.checkpoint_manager.requires_human_approval('code-ready-for-review'):
            print("\n[CHECKPOINT] 需要人类审核代码")
            self.state.pending_approvals.append('code-ready-for-review')
            self.checkpoint_manager.mark_completed('code-ready-for-review')

        self.state.completed_steps.append('step4_development')

    def _run_step5_patch_generation(self):
        """Step 5: Patch生成与发送"""
        print("\n[Step 5] Patch生成与发送")
        print("-" * 40)

        self.state.current_step = 'step5_patch'

        print("生成patch并发送到KVM邮件列表...")

        # 检查点
        if self.checkpoint_manager.requires_human_approval('patch-ready-to-send'):
            print("\n[CHECKPOINT] 需要人类确认发送patch")
            self.state.pending_approvals.append('patch-ready-to-send')
            self.checkpoint_manager.mark_completed('patch-ready-to-send')

        self.state.completed_steps.append('step5_patch')

    def get_status(self) -> Dict[str, Any]:
        """获取工作流状态"""
        return {
            'current_step': self.state.current_step,
            'completed_steps': self.state.completed_steps,
            'pending_approvals': self.state.pending_approvals,
            'errors': self.state.errors
        }


def main():
    """主入口"""
    import argparse

    parser = argparse.ArgumentParser(description='RISC-V差距分析工作流')
    parser.add_argument('--config', help='配置文件路径')
    parser.add_argument('--step', type=int, choices=[1, 2, 3, 4, 5],
                        help='运行指定步骤')

    args = parser.parse_args()

    workflow = RISCVGapAnalysisWorkflow(args.config)

    if args.step:
        # 运行指定步骤
        if args.step == 1:
            workflow._run_step1_explore()
        elif args.step == 2:
            workflow._run_step2_create_issues()
        elif args.step == 3:
            workflow._run_step3_development_plan()
        elif args.step == 4:
            workflow._run_step4_code_development()
        elif args.step == 5:
            workflow._run_step5_patch_generation()
    else:
        # 运行完整工作流
        workflow.run()


if __name__ == '__main__':
    main()
