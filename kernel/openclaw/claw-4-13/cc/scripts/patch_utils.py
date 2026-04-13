#!/usr/bin/env python3
"""
Patch生成与发送脚本
"""
import os
import sys
import subprocess
import argparse
from typing import List, Optional


class PatchGenerator:
    """Patch生成器"""

    def __init__(self, repo_path: str = None):
        self.repo_path = repo_path or os.getcwd()

    def format_patch(
        self,
        commits: str = 'HEAD~1..HEAD',
        version: int = 1,
        cover_letter: bool = True
    ) -> List[str]:
        """生成patch"""
        print(f"生成patch: {commits}")

        cmd = ['git', 'format-patch']

        if cover_letter:
            cmd.extend(['--cover-letter'])

        cmd.extend(['-v', str(version)])
        cmd.append(commits)

        try:
            result = subprocess.run(
                cmd,
                cwd=self.repo_path,
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                files = result.stdout.strip().split('\n')
                print(f"生成了 {len(files)} 个patch文件")
                return files
            else:
                print(f"生成失败: {result.stderr}")
                return []
        except Exception as e:
            print(f"执行失败: {e}")
            return []

    def generate_diffstat(self) -> str:
        """生成diffstat"""
        cmd = ['git', 'diff', '--stat']
        try:
            result = subprocess.run(
                cmd,
                cwd=self.repo_path,
                capture_output=True,
                text=True
            )
            return result.stdout
        except Exception:
            return ""


class PatchSender:
    """Patch发送器"""

    def __init__(self, repo_path: str = None):
        self.repo_path = repo_path or os.getcwd()

    def send_email(
        self,
        patch_file: str,
        to: str,
        cc: List[str] = None,
        dry_run: bool = False
    ) -> bool:
        """使用git send-email发送patch"""
        cmd = ['git', 'send-email', patch_file, '--to', to]

        if cc:
            for addr in cc:
                cmd.extend(['--cc', addr])

        if dry_run:
            cmd.append('--dry-run')

        print(f"发送命令: {' '.join(cmd)}")

        try:
            result = subprocess.run(
                cmd,
                cwd=self.repo_path,
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                print("发送成功!")
                return True
            else:
                print(f"发送失败: {result.stderr}")
                return False
        except Exception as e:
            print(f"执行失败: {e}")
            return False

    def send_series(
        self,
        patch_dir: str,
        to: str,
        cc: List[str] = None,
        dry_run: bool = False
    ) -> bool:
        """发送补丁系列"""
        cmd = ['git', 'send-email', patch_dir, '--to', to]

        if cc:
            for addr in cc:
                cmd.extend(['--cc', addr])

        if dry_run:
            cmd.append('--dry-run')

        try:
            result = subprocess.run(
                cmd,
                cwd=self.repo_path,
                capture_output=True,
                text=True
            )
            return result.returncode == 0
        except Exception:
            return False


# KVM邮件列表常量
KVM_LIST = 'kvm@vger.kernel.org'
LINUX_RISC_V_LIST = 'linux-riscv@lists.infradead.org'


def main():
    parser = argparse.ArgumentParser(description='Patch生成与发送')
    subparsers = parser.add_subparsers(dest='command')

    # format子命令
    format_parser = subparsers.add_parser('format', help='生成patch')
    format_parser.add_argument('--commits', default='HEAD~1..HEAD',
                               help='提交范围')
    format_parser.add_argument('--version', type=int, default=1,
                               help='版本号')
    format_parser.add_argument('--no-cover', action='store_true',
                               help='不生成cover letter')

    # send子命令
    send_parser = subparsers.add_parser('send', help='发送patch')
    send_parser.add_argument('patch', help='patch文件或目录')
    send_parser.add_argument('--to', default=KVM_LIST,
                             help='收件人')
    send_parser.add_argument('--cc', nargs='+',
                             help='抄送人')
    send_parser.add_argument('--dry-run', action='store_true',
                             help='模拟运行')

    # diffstat子命令
    stat_parser = subparsers.add_parser('stat', help='生成diffstat')

    args = parser.parse_args()

    generator = PatchGenerator()
    sender = PatchSender()

    if args.command == 'format':
        files = generator.format_patch(
            args.commits,
            args.version,
            not args.no_cover
        )
        for f in files:
            print(f)

    elif args.command == 'send':
        sender.send_email(
            args.patch,
            args.to,
            args.cc,
            args.dry_run
        )

    elif args.command == 'stat':
        print(generator.generate_diffstat())

    else:
        parser.print_help()


if __name__ == '__main__':
    main()
