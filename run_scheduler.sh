#!/bin/bash
# 启动定时任务调度器

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "=========================================="
echo "启动定时任务调度器"
echo "=========================================="
echo ""

# 切换到项目目录
cd "$SCRIPT_DIR" || exit 1

echo "启动调度器..."
python -m app.run_scheduler
