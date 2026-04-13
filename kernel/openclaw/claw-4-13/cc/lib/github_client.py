"""
GitHub API 客户端 - 用于Issue管理和自动化操作
"""
import os
import json
import requests
from typing import Dict, List, Any, Optional
from dataclasses import dataclass


@dataclass
class Issue:
    """GitHub Issue"""
    number: int
    title: str
    body: str
    labels: List[str]
    state: str
    html_url: str
    created_at: str


class GitHubClient:
    """GitHub API 客户端"""

    def __init__(self, token: str = None, owner: str = None, repo: str = None):
        self.token = token or os.environ.get('GITHUB_TOKEN')
        self.owner = owner or os.environ.get('GITHUB_OWNER', 'zcxGGmu')
        self.repo = repo or os.environ.get('GITHUB_REPO', 'linux-riscv-docs')
        self.base_url = 'https://api.github.com'
        self.headers = {
            'Authorization': f'token {self.token}',
            'Accept': 'application/vnd.github.v3+json'
        }

    def _make_request(self, method: str, endpoint: str, data: Dict = None) -> Dict:
        """发送API请求"""
        url = f'{self.base_url}{endpoint}'
        response = requests.request(method, url, headers=self.headers, json=data)
        response.raise_for_status()
        return response.json() if response.content else {}

    # Issue操作
    def create_issue(
        self,
        title: str,
        body: str,
        labels: List[str] = None,
        milestone: str = None
    ) -> Issue:
        """创建Issue"""
        data = {
            'title': title,
            'body': body,
            'labels': labels or []
        }
        if milestone:
            data['milestone'] = milestone

        result = self._make_request('POST', f'/repos/{self.owner}/{self.repo}/issues', data)
        return Issue(
            number=result['number'],
            title=result['title'],
            body=result['body'],
            labels=[l['name'] for l in result.get('labels', [])],
            state=result['state'],
            html_url=result['html_url'],
            created_at=result['created_at']
        )

    def get_issue(self, issue_number: int) -> Issue:
        """获取Issue"""
        result = self._make_request(
            'GET',
            f'/repos/{self.owner}/{self.repo}/issues/{issue_number}'
        )
        return Issue(
            number=result['number'],
            title=result['title'],
            body=result['body'],
            labels=[l['name'] for l in result.get('labels', [])],
            state=result['state'],
            html_url=result['html_url'],
            created_at=result['created_at']
        )

    def list_issues(self, state: str = 'open', labels: List[str] = None) -> List[Issue]:
        """列出Issue"""
        params = {'state': state}
        if labels:
            params['labels'] = ','.join(labels)

        result = self._make_request(
            'GET',
            f'/repos/{self.owner}/{self.repo}/issues',
            params
        )
        return [
            Issue(
                number=item['number'],
                title=item['title'],
                body=item['body'],
                labels=[l['name'] for l in item.get('labels', [])],
                state=item['state'],
                html_url=item['html_url'],
                created_at=item['created_at']
            )
            for item in result if 'pull_request' not in item
        ]

    def update_issue(
        self,
        issue_number: int,
        title: str = None,
        body: str = None,
        state: str = None,
        labels: List[str] = None
    ) -> Issue:
        """更新Issue"""
        data = {}
        if title:
            data['title'] = title
        if body:
            data['body'] = body
        if state:
            data['state'] = state
        if labels:
            data['labels'] = labels

        result = self._make_request(
            'PATCH',
            f'/repos/{self.owner}/{self.repo}/issues/{issue_number}',
            data
        )
        return self.get_issue(issue_number)

    def add_comment(self, issue_number: int, body: str) -> Dict:
        """添加评论"""
        return self._make_request(
            'POST',
            f'/repos/{self.owner}/{self.repo}/issues/{issue_number}/comments',
            {'body': body}
        )

    def assign_issue(self, issue_number: int, assignees: List[str]) -> Issue:
        """分配Issue"""
        result = self._make_request(
            'POST',
            f'/repos/{self.owner}/{self.repo}/issues/{issue_number}/assignees',
            {'assignees': assignees}
        )
        return self.get_issue(issue_number)

    # Issue模板生成
    def generate_issue_body(
        self,
        feature_name: str,
        description: str,
        arm_x86_status: str,
        riscv_status: str,
        impact_analysis: str,
        priority: str,
        related_resources: List[str] = None
    ) -> str:
        """生成Issue body"""
        resources = '\n'.join([f'- {r}' for r in (related_resources or [])])
        return f"""## 描述
{description}

## ARM/x86现状
{arm_x86_status}

## RISC-V当前状态
{riscv_status}

## 影响分析
{impact_analysis}

## 优先级
{priority}

## 相关资源
{resources}
"""

    def create_feature_gap_issue(
        self,
        feature_name: str,
        description: str,
        arm_x86_status: str,
        riscv_status: str,
        impact_analysis: str,
        priority: str,
        labels: List[str] = None
    ) -> Issue:
        """创建功能差距Issue"""
        title = f"[RISC-V Feature Gap] {feature_name}"
        body = self.generate_issue_body(
            feature_name=feature_name,
            description=description,
            arm_x86_status=arm_x86_status,
            riscv_status=riscv_status,
            impact_analysis=impact_analysis,
            priority=priority
        )
        default_labels = ['riscv', 'feature-gap', priority]
        if labels:
            default_labels.extend(labels)

        return self.create_issue(title, body, default_labels)


# 优先级映射
PRIORITY_MAP = {
    'P0': 'priority/P0',
    'P1': 'priority/P1',
    'P2': 'priority/P2',
    'P3': 'priority/P3'
}
