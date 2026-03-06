#!/bin/bash
# Docker容器启动脚本
# 同时启动FastAPI服务和定时任务调度器

set -e

echo "=========================================="
echo "Docker容器启动脚本"
echo "=========================================="

# 创建logs目录
mkdir -p logs

# ==========================================
# SSH 配置检查与密钥生成
# ==========================================
echo ""
echo "检查 SSH 配置..."

if [ ! -d ~/.ssh ]; then
    echo "生成 SSH 密钥对..."
    mkdir -p ~/.ssh
    chmod 700 ~/.ssh
    
    # 生成无密码 RSA 密钥
    ssh-keygen -t rsa -b 4096 -C "huangwensen@baidu.com" -N "" -f ~/.ssh/id_rsa
    
    echo ""
    echo "✅ SSH 密钥已生成，公钥内容："
    echo "=========================================="
    cat ~/.ssh/id_rsa.pub
    echo "=========================================="
    echo ""
    echo "请将以上公钥添加到 Git 服务器（如：GitLab、GitHub）的部署密钥中。"
    echo "后续即可直接在容器内使用 git clone 等操作。"
else
    echo "✅ 已存在 SSH 配置"
fi

# 设置权限
chmod 600 ~/.ssh/id_rsa 2>/dev/null || true
chmod 644 ~/.ssh/id_rsa.pub 2>/dev/null || true

echo ""
echo "启动定时任务调度器..."

# 后台运行定时任务调度器
./run_scheduler.sh  2>&1 &
SCHEDULER_PID=$!

echo "✅ 调度器已启动 (PID: $SCHEDULER_PID)"
echo "   日志文件: logs/scheduler.log"

echo ""
echo "启动FastAPI服务..."
echo "   服务地址: http://0.0.0.0:8899"
echo ""

# 启动FastAPI服务（前台）
trap "echo '正在停止调度器...'; kill $SCHEDULER_PID 2>/dev/null || true; exit 0" EXIT INT TERM

# 启动FastAPI
python run.py
