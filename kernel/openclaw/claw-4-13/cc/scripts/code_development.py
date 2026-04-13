#!/usr/bin/env python3
"""
代码开发循环脚本
包含代码编写、构建验证、测试运行功能
"""
import os
import sys
import subprocess
import argparse
from typing import List, Dict, Any


class CodeDevelopmentLoop:
    """代码开发循环"""

    def __init__(self, linux_repo_path: str = None):
        self.linux_repo_path = linux_repo_path or os.environ.get(
            'LINUX_REPO_PATH',
            os.path.expanduser('~/linux')
        )

    def compile(self, arch: str = 'riscv', config: str = 'defconfig') -> bool:
        """编译内核"""
        print(f"编译 {arch} 架构...")

        make_cmd = [
            'make',
            f'ARCH={arch}',
            config,
            '-j', str(os.cpu_count())
        ]

        try:
            result = subprocess.run(
                make_cmd,
                cwd=self.linux_repo_path,
                capture_output=True,
                text=True
            )
            return result.returncode == 0
        except Exception as e:
            print(f"编译失败: {e}")
            return False

    def run_kselftest(self, arch: str = 'riscv') -> bool:
        """运行kselftest"""
        print(f"运行 kselftest for {arch}...")

        test_cmd = [
            'make',
            f'ARCH={arch}',
            'kselftest',
            '-j', str(os.cpu_count())
        ]

        try:
            result = subprocess.run(
                test_cmd,
                cwd=self.linux_repo_path,
                capture_output=True,
                text=True
            )
            return result.returncode == 0
        except Exception as e:
            print(f"测试运行失败: {e}")
            return False

    def checkpatch(self, patch_file: str) -> bool:
        """运行checkpatch.pl"""
        print(f"检查patch: {patch_file}")

        check_cmd = [
            './scripts/checkpatch.pl',
            patch_file
        ]

        try:
            result = subprocess.run(
                check_cmd,
                cwd=self.linux_repo_path,
                capture_output=True,
                text=True
            )
            if result.returncode != 0:
                print("Checkpatch 警告/错误:")
                print(result.stdout)
                return False
            return True
        except Exception as e:
            print(f"Checkpatch 执行失败: {e}")
            return False


def main():
    parser = argparse.ArgumentParser(description='代码开发循环')
    parser.add_argument('--compile', action='store_true', help='编译内核')
    parser.add_argument('--test', action='store_true', help='运行测试')
    parser.add_argument('--check', metavar='FILE', help='检查patch')
    parser.add_argument('--arch', default='riscv', help='目标架构')

    args = parser.parse_args()

    dev_loop = CodeDevelopmentLoop()

    if args.compile:
        success = dev_loop.compile(args.arch)
        sys.exit(0 if success else 1)

    if args.test:
        success = dev_loop.run_kselftest(args.arch)
        sys.exit(0 if success else 1)

    if args.check:
        success = dev_loop.checkpatch(args.check)
        sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
