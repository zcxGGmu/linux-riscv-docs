#!/usr/bin/env python3
"""
Issue自动创建脚本
基于差距分析结果自动创建GitHub Issue
"""
import os
import sys
import argparse

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from lib.github_client import GitHubClient


# 预定义的差距Issue列表
DEFAULT_GAPS = [
    {
        'name': 'KVM MMU管理',
        'description': 'RISC-V KVM需要完善Sv39/Sv48/Sv57完整支持',
        'arm_x86_status': '已实现完整的MMU管理，包括EPT/NPT支持',
        'riscv_status': '基础实现，缺少Sv39/Sv48/Sv57完整支持',
        'impact': '影响内存虚拟化性能和安全性',
        'priority': 'P0',
        'files': ['arch/riscv/kvm/mmu.c']
    },
    {
        'name': '嵌套虚拟化支持',
        'description': 'RISC-V需要实现嵌套虚拟化(RISC-V Hypervisor扩展)支持',
        'arm_x86_status': '支持完整的两级虚拟化架构',
        'riscv_status': '缺少嵌套虚拟化支持，返回SBI_ERR_NOT_SUPPORTED',
        'impact': '影响虚拟化测试和分层部署',
        'priority': 'P1',
        'files': ['arch/riscv/kvm/nested.c']
    },
    {
        'name': 'VMID分配器优化',
        'description': '优化VMID分配器，减少IPI开销',
        'arm_x86_status': '使用bitmap + per-CPU active/reserved机制',
        'riscv_status': '全局vmid_next线性分配，回卷时全CPU IPI刷新',
        'impact': '影响多核虚拟化性能',
        'priority': 'P0',
        'files': ['arch/riscv/kvm/vmid.c']
    },
    {
        'name': 'PV Time/Stolen Time',
        'description': '实现PV Time让guest可以获取被调度时间',
        'arm_x86_status': '完整实现',
        'riscv_status': '缺失',
        'impact': '影响guest调度精度',
        'priority': 'P1',
        'files': ['arch/riscv/kvm/pvtime.c']
    },
    {
        'name': 'AIA/IMSIC虚拟化',
        'description': '完善RISC-V AIA中断控制器虚拟化支持',
        'arm_x86_status': '支持GICv3/v4完整虚拟化',
        'riscv_status': 'AIA支持不完整，缺少IMSIC虚拟化',
        'impact': '影响中断处理性能和实时性',
        'priority': 'P1',
        'files': ['arch/riscv/kvm/aia.c', 'arch/riscv/kvm/aia_imsic.c']
    },
    {
        'name': '硬件断点/观察点支持',
        'description': '实现完整的KVM调试支持',
        'arm_x86_status': '支持完整的调试架构，包括硬件断点',
        'riscv_status': '缺少硬件断点/watchpoint支持',
        'impact': '影响调试和分析工具的可用性',
        'priority': 'P2',
        'files': ['arch/riscv/kvm/debug.c']
    },
    {
        'name': 'PMU虚拟化',
        'description': '实现PMU虚拟化支持性能监控',
        'arm_x86_status': '支持完整的PMU虚拟化',
        'riscv_status': '缺少PMU虚拟化支持',
        'impact': '影响性能分析和调优工具',
        'priority': 'P2',
        'files': ['arch/riscv/kvm/pmu.c']
    },
    {
        'name': 'IRQ Bypass',
        'description': '实现IRQ Bypass降低中断延迟',
        'arm_x86_status': '支持HAVE_KVM_IRQ_BYPASS',
        'riscv_status': '未实现',
        'impact': '影响中断延迟',
        'priority': 'P2',
        'files': []
    }
]


def create_issues(
    token: str,
    owner: str,
    repo: str,
    gaps: list = None,
    dry_run: bool = False
):
    """创建Issue"""
    client = GitHubClient(token=token, owner=owner, repo=repo)

    gaps = gaps or DEFAULT_GAPS

    created_issues = []

    for gap in gaps:
        title = f"[RISC-V Feature Gap] {gap['name']}"
        body = f"""## 描述
{gap['description']}

## ARM/x86现状
{gap['arm_x86_status']}

## RISC-V当前状态
{gap['riscv_status']}

## 影响分析
{gap['impact']}

## 优先级
{gap['priority']}

## 相关文件
{chr(10).join(['- ' + f for f in gap.get('files', [])])}
"""

        labels = ['riscv', 'feature-gap', gap['priority'].lower()]

        print(f"\n创建Issue: {title}")
        print(f"标签: {labels}")

        if dry_run:
            print("[DRY RUN] 跳过实际创建")
            created_issues.append({'title': title, 'labels': labels})
        else:
            try:
                issue = client.create_feature_gap_issue(
                    feature_name=gap['name'],
                    description=gap['description'],
                    arm_x86_status=gap['arm_x86_status'],
                    riscv_status=gap['riscv_status'],
                    impact_analysis=gap['impact'],
                    priority=gap['priority']
                )
                print(f"创建成功: #{issue.number}")
                created_issues.append({
                    'number': issue.number,
                    'title': issue.title,
                    'url': issue.html_url
                })
            except Exception as e:
                print(f"创建失败: {e}")

    return created_issues


def main():
    parser = argparse.ArgumentParser(description='创建RISC-V差距Issue')
    parser.add_argument('--token', help='GitHub Token')
    parser.add_argument('--owner', default='zcxGGmu', help='仓库所有者')
    parser.add_argument('--repo', default='linux-riscv-docs', help='仓库名')
    parser.add_argument('--dry-run', action='store_true', help='模拟运行')
    parser.add_argument('--list', action='store_true', help='列出预设差距')

    args = parser.parse_args()

    if args.list:
        print("预设差距列表:")
        for i, gap in enumerate(DEFAULT_GAPS, 1):
            print(f"{i}. [{gap['priority']}] {gap['name']}")
        return

    token = args.token or os.environ.get('GITHUB_TOKEN')
    if not token:
        print("错误: 需要GitHub Token")
        print("使用 --token 或设置 GITHUB_TOKEN 环境变量")
        sys.exit(1)

    create_issues(token, args.owner, args.repo, dry_run=args.dry_run)


if __name__ == '__main__':
    main()
