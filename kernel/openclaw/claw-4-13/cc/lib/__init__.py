"""
工作流核心库初始化
"""
from .agent_manager import AgentManager, AgentProtocol, CheckpointManager
from .github_client import GitHubClient, PRIORITY_MAP
from .mail_client import MailClient, GitSendEmailClient, KVM_LIST, create_patch_email
from .kernel_analyzer import KernelAnalyzer, FeatureGap, AnalysisResult, export_gap_report

__all__ = [
    'AgentManager',
    'AgentProtocol',
    'CheckpointManager',
    'GitHubClient',
    'PRIORITY_MAP',
    'MailClient',
    'GitSendEmailClient',
    'KVM_LIST',
    'create_patch_email',
    'KernelAnalyzer',
    'FeatureGap',
    'AnalysisResult',
    'export_gap_report'
]
