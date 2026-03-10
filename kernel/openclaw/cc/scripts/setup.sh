#!/bin/bash
# 环境准备脚本
# 用于设置RISC-V差距分析工作流所需的环境

set -e

echo "=========================================="
echo "RISC-V差距分析工作流 - 环境设置"
echo "=========================================="

# 检查Python版本
echo "检查Python版本..."
python3 --version

# 安装Python依赖
echo "安装Python依赖..."
pip3 install pyyaml requests

# 配置Git
echo "配置Git..."
read -p "请输入您的Git用户名: " GIT_NAME
read -p "请输入您的Git邮箱: " GIT_EMAIL

git config --global user.name "$GIT_NAME"
git config --global user.email "$GIT_EMAIL"

# 配置GitHub
echo ""
echo "配置GitHub访问..."
read -p "请输入GitHub Token (可选，直接回车跳过): " GH_TOKEN
if [ -n "$GH_TOKEN" ]; then
    export GITHUB_TOKEN="$GH_TOKEN"
    echo "export GITHUB_TOKEN='$GH_TOKEN'" >> ~/.bashrc
fi

# 克隆Linux内核仓库
echo ""
read -p "是否克隆Linux内核仓库? (y/n): " CLONE_LINUX
if [ "$CLONE_LINUX" = "y" ]; then
    LINUX_PATH=${HOME}/linux
    if [ -d "$LINUX_PATH" ]; then
        echo "Linux仓库已存在于 $LINUX_PATH"
    else
        echo "克隆Linux内核仓库..."
        git clone https://github.com/torvalds/linux.git "$LINUX_PATH"
    fi
    export LINUX_REPO_PATH="$LINUX_PATH"
    echo "export LINUX_REPO_PATH='$LINUX_PATH'" >> ~/.bashrc
fi

# 克隆RISC-V文档仓库
echo ""
read -p "是否克隆linux-riscv-docs仓库? (y/n): " CLONE_DOCS
if [ "$CLONE_DOCS" = "y" ]; then
    DOCS_PATH=${HOME}/linux-riscv-docs
    if [ -d "$DOCS_PATH" ]; then
        echo "文档仓库已存在于 $DOCS_PATH"
    else
        echo "克隆RISC-V文档仓库..."
        git clone https://github.com/zcxGGmu/linux-riscv-docs.git "$DOCS_PATH"
    fi
fi

# 安装RISC-V交叉编译工具链
echo ""
read -p "是否安装RISC-V交叉编译工具链? (y/n): " INSTALL_TOOLCHAIN
if [ "$INSTALL_TOOLCHAIN" = "y" ]; then
    echo "安装RISC-V工具链..."
    sudo apt-get update
    sudo apt-get install -y gcc-riscv64-linux-gnu g++-riscv64-linux-gnu

    # 验证安装
    echo "验证工具链..."
    riscv64-linux-gnu-gcc --version
fi

# 安装邮件发送工具
echo ""
read -p "是否安装邮件发送工具? (y/n): " INSTALL_EMAIL
if [ "$INSTALL_EMAIL" = "y" ]; then
    echo "安装邮件工具..."
    sudo apt-get install -y git-email

    # 配置SMTP
    echo ""
    echo "配置SMTP邮件发送..."
    read -p "SMTP服务器: " SMTP_SERVER
    read -p "SMTP端口: " SMTP_PORT
    read -p "SMTP用户名: " SMTP_USER
    read -p "SMTP密码: " -s SMTP_PASS

    export SMTP_SERVER="$SMTP_SERVER"
    export SMTP_USERNAME="$SMTP_USER"
    export SMTP_PASSWORD="$SMTP_PASS"

    cat >> ~/.bashrc << EOF
export SMTP_SERVER='$SMTP_SERVER'
export SMTP_USERNAME='$SMTP_USER'
export SMTP_PASSWORD='$SMTP_PASS'
EOF
fi

echo ""
echo "=========================================="
echo "环境设置完成!"
echo "=========================================="
echo ""
echo "下一步操作:"
echo "1. 运行: python3 -m workflows.riscv_gap_analysis"
echo "2. 或查看帮助: python3 -m workflows.riscv_gap_analysis --help"
