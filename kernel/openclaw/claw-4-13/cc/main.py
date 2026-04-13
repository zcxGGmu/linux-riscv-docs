#!/usr/bin/env python3
"""
RISC-V差距分析工作流 - CLI入口
"""
import os
import sys

# 添加当前目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from workflows.riscv_gap_analysis import main

if __name__ == '__main__':
    main()
