#!/bin/bash
# Docker容器启动脚本
# 同时启动FastAPI服务和定时任务调度器

set -e

echo "=========================================="
echo "Docker容器启动脚本"
echo "=========================================="

# 创建logs目录
mkdir -p logs

echo ""
echo "启动定时任务调度器..."

# 后台运行定时任务调度器
./run_scheduler.sh  2>&1 &
SCHEDULER_PID=$!

echo "✅ 调度器已启动 (PID: $SCHEDULER_PID)"
echo "   日志文件: logs/scheduler.log"

echo ""
echo "启动FastAPI服务..."
echo "   服务地址: http://0.0.0.0:8888"
echo ""

# 启动FastAPI服务（前台）
trap "echo '正在停止调度器...'; kill $SCHEDULER_PID 2>/dev/null || true; exit 0" EXIT INT TERM

# 启动FastAPI
python run.py