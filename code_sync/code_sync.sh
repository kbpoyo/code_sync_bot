#!/bin/bash
# code_sync.sh - 拉取代码并执行同步检查

set -e

#===========================================
# 环境变量配置
#===========================================
export REPO_URL="${REPO_URL:-ssh://huangwensen@icode.baidu.com:8235/baidu/xpu/XMLIR}"  # 需要更改到QA的链接
export REPO_DIR="${REPO_DIR:-./XMLIR}"
# master 和 v2.9.0 使用不同的同步基准点
export MASTER_SYNC_BASE="${MASTER_SYNC_BASE:-751a09f017226309e8c670f76665745701ebb469}"
export TARGET_SYNC_BASE="${TARGET_SYNC_BASE:-c26bf6059f52c0c4768e22b0ddde34321cdd0b4d}"
export MASTER_BRANCH="${MASTER_BRANCH:-origin/v2.9.0}"
export TARGET_BRANCH="${TARGET_BRANCH:-origin/v2.5.1}"
export WHITELIST_FILE="${WHITELIST_FILE:-./whitelist.yaml}"
export OUTPUT_FORMAT="${OUTPUT_FORMAT:-text}"
export OUTPUT_FILE="${OUTPUT_FILE:-}"  # JSON 输出文件路径，为空则输出到终端

#===========================================
# 脚本目录
#===========================================
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

#===========================================
# 拉取/更新代码
#===========================================
echo "[INFO] 开始同步检查..."
echo "[INFO] MASTER_SYNC_BASE: ${MASTER_SYNC_BASE}"
echo "[INFO] TARGET_SYNC_BASE: ${TARGET_SYNC_BASE}"
echo "[INFO] MASTER_BRANCH: ${MASTER_BRANCH}"
echo "[INFO] TARGET_BRANCH: ${TARGET_BRANCH}"

if [ -d "${REPO_DIR}/.git" ]; then
    echo "[INFO] 仓库已存在，更新中..."
    cd "${REPO_DIR}"
    git fetch --all --prune
else
    echo "[INFO] 克隆仓库..."
    # 自动获取SSH主机密钥（无需手动确认）
    mkdir -p ~/.ssh
    chmod 700 ~/.ssh

    # 从URL提取主机和端口: ssh://user@host:port/path
    GIT_HOST=$(echo "${REPO_URL}" | sed -n 's|.*@\([^:]*\):\([0-9]*\)/.*|\1|p')
    GIT_PORT=$(echo "${REPO_URL}" | sed -n 's|.*@\([^:]*\):\([0-9]*\)/.*|\2|p')

    if [ -n "${GIT_HOST}" ]; then
        echo "[INFO] 自动获取主机密钥: ${GIT_HOST}:${GIT_PORT:-22}"
        # 扫描指定端口的主机密钥
        if [ -n "${GIT_PORT}" ]; then
            ssh-keyscan -p "${GIT_PORT}" -t rsa "${GIT_HOST}" >> ~/.ssh/known_hosts 2>/dev/null
        else
            ssh-keyscan -t rsa "${GIT_HOST}" >> ~/.ssh/known_hosts 2>/dev/null
        fi
        chmod 644 ~/.ssh/known_hosts
        echo "[INFO] 主机密钥已自动添加到 ~/.ssh/known_hosts"
    fi

    # 执行克隆
    git clone "${REPO_URL}" "${REPO_DIR}"
    cd "${REPO_DIR}"
fi

#===========================================
# 验证分支和 commit 是否存在
#===========================================
echo "[INFO] 验证引用..."
if ! git rev-parse --verify "${MASTER_SYNC_BASE}" >/dev/null 2>&1; then
    echo "[ERROR] MASTER_SYNC_BASE '${MASTER_SYNC_BASE}' 不存在"
    exit 1
fi

if ! git rev-parse --verify "${TARGET_SYNC_BASE}" >/dev/null 2>&1; then
    echo "[ERROR] TARGET_SYNC_BASE '${TARGET_SYNC_BASE}' 不存在"
    exit 1
fi

if ! git rev-parse --verify "${MASTER_BRANCH}" >/dev/null 2>&1; then
    echo "[ERROR] MASTER_BRANCH '${MASTER_BRANCH}' 不存在"
    exit 1
fi

if ! git rev-parse --verify "${TARGET_BRANCH}" >/dev/null 2>&1; then
    echo "[ERROR] TARGET_BRANCH '${TARGET_BRANCH}' 不存在"
    exit 1
fi

echo "[INFO] 所有引用验证通过"

cd ..
#===========================================
# 调用 Python diff 脚本
#===========================================
echo "[INFO] 执行 diff 比较..."
python3 "${SCRIPT_DIR}/commit_diff.py"

echo "[INFO] 代码已同步完成"
