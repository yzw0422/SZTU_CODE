#!/usr/bin/env bash
# SZTU_Code 一键配置脚本 (Linux / macOS)
# 用法: bash setup.sh

set -e
PROJECT_ROOT="$(cd "$(dirname "$0")" && pwd)"

echo ""
echo "  SZTU_Code  v0.2.0  -  一键配置"
echo "====================================="
echo ""

# ---------- 1. 检查 Python ----------
printf "[1/4] 检查 Python... "
if ! command -v python3 &>/dev/null && ! command -v python &>/dev/null; then
    echo ""
    echo " 错误: 未找到 Python，请先安装 Python 3.10+"
    echo " macOS: brew install python"
    echo " Ubuntu: sudo apt install python3 python3-pip"
    exit 1
fi
PY=$(command -v python3 || command -v python)
PYVER=$($PY --version 2>&1)
echo "OK ($PYVER)"

# ---------- 2. pip install ----------
printf "[2/4] 安装依赖 (pip install -e .)... "
cd "$PROJECT_ROOT"
$PY -m pip install -e . --quiet 2>&1
echo "OK"

# ---------- 3. 配置文件 ----------
CONFIG_PATH="$PROJECT_ROOT/.sztu_code"
HOME_CONFIG="$HOME/.sztu_code"

printf "[3/4] 检查配置文件... "
if [ ! -f "$CONFIG_PATH" ] && [ ! -f "$HOME_CONFIG" ]; then
    echo ""
    echo ""
    echo " 未找到 .sztu_code 配置文件"
    echo ""
    echo " 请选择 API Provider:"
    echo "   1. DeepSeek (deepseek-v4-flash)"
    echo "   2. OpenAI (gpt-4o-mini)"
    echo "   3. 手动输入"
    echo ""
    read -p " 请输入选项 (1/2/3): " choice
    echo ""

    case "$choice" in
        1)
            read -p " 请输入 DeepSeek API Key: " api_key
            model="deepseek-v4-flash"
            type="deepseek"
            base_url="https://api.deepseek.com/v1"
            ;;
        2)
            read -p " 请输入 OpenAI API Key: " api_key
            model="gpt-4o-mini"
            type="openai"
            base_url="https://api.openai.com/v1"
            ;;
        *)
            read -p " Provider 类型: " type
            read -p " 模型名: " model
            read -p " API Key: " api_key
            read -p " API Base URL: " base_url
            ;;
    esac

    cat > "$CONFIG_PATH" << EOF
[provider]
type = "$type"
api_key = "$api_key"
model = "$model"
base_url = "$base_url"

[agent]
max_turns = 25
max_tokens = 4096
EOF
    echo ""
    echo " 已创建配置文件: $CONFIG_PATH"
else
    echo "OK (已存在)"
fi

# ---------- 4. 验证 ----------
printf "[4/4] 验证安装... "
if command -v sztu-code &>/dev/null; then
    echo "OK ($(command -v sztu-code))"
else
    echo ""
    echo " 错误: 未找到 sztu-code 命令"
    echo " 请尝试: source ~/.bashrc  或重新打开终端"
    exit 1
fi

# ---------- 完成 ----------
echo ""
echo "====================================="
echo "  配置完成! 现在可以运行:"
echo ""
echo "    sztu-code"
echo ""
echo "====================================="
echo ""