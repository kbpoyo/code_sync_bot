# XMLIR 分支同步检查工具

检查 XMLIR 仓库 master 分支与 v2.9.0 分支之间未同步的 commit，通过对比 commit 标题来识别差异。

## 快速开始

```bash
cd /workspace/code_sync
chmod +x code_sync.sh
./code_sync.sh
```

## 环境变量说明

| 变量名 | 默认值 | 说明 |
|--------|--------|------|
| `REPO_URL` | `ssh://...baidu/xpu/XMLIR` | Git 仓库地址 |
| `REPO_DIR` | `./XMLIR` | 本地仓库目录 |
| `MASTER_SYNC_BASE` | `bfdf823` | master 分支的同步基准 commit |
| `TARGET_SYNC_BASE` | `4be9942` | v2.9.0 分支的同步基准 commit |
| `MASTER_BRANCH` | `origin/master` | master 分支引用 |
| `TARGET_BRANCH` | `origin/v2.9.0` | 目标分支引用 |
| `WHITELIST_FILE` | `./whitelist.yaml` | 白名单配置文件路径 |
| `OUTPUT_FORMAT` | `text` | 输出格式：`text` 或 `json` |
| `OUTPUT_FILE` | 空 | 输出文件路径，为空则输出到终端 |

## 使用示例

### 1. 默认文本输出（终端显示）

```bash
./code_sync.sh
```

### 2. JSON 输出到终端

```bash
export OUTPUT_FORMAT=json
./code_sync.sh
```

### 3. JSON 输出到文件（用于机器人读取）

```bash
export OUTPUT_FORMAT=json
export OUTPUT_FILE=./result.json
./code_sync.sh
```

此方式下：
- 终端显示所有 `[INFO]` 日志
- `result.json` 只包含纯净 JSON 数据

### 4. 自定义分支和基准点

```bash
export MASTER_SYNC_BASE=abc1234
export TARGET_SYNC_BASE=def5678
export TARGET_BRANCH=origin/v2.9.0
./code_sync.sh
```

## 白名单配置

编辑 `whitelist.yaml` 文件，支持三种排除方式：

```yaml
whitelist:
  # 按 commit hash 排除（支持短 hash 前缀匹配）
  by_hash:
    - abc12345

  # 按关键词排除（标题包含这些关键词的 commit 会被跳过）
  by_keyword:
    - "[master-only]"

  # 按作者邮箱排除
  by_author:
    - bot@example.com
```

## 文件结构

```
code_sync/
├── code_sync.sh       # 主入口脚本
├── commit_diff.py     # Python diff 比较程序
├── whitelist.yaml     # 白名单配置
├── readme.md          # 本文档
└── XMLIR/             # 克隆的仓库目录（自动生成）
```

## 输出示例

### 文本格式

```
============================================================
XMLIR 分支同步检查报告
============================================================
检查时间: 2026-02-25 16:30:00
Master 分支: origin/master (base: bfdf823)
目标分支: origin/v2.9.0 (base: 4be9942)
------------------------------------------------------------
Master Commit 数量: 40
目标分支 Commit 数量: 3
未同步 Commit 数量: 39
白名单过滤数量: 1
============================================================
❌ 以下 Commit 尚未同步到目标分支：

【wangxu46】(2 个待同步)
  - [Feature][Infra](XMLIR-8128) support isneginf_out
    日期: 2026-02-02 | Hash: a5d004b2
  - [Fix][API](XMLIR-8045) fix release_install issue
    日期: 2026-01-20 | Hash: 2408368d

============================================================
```

### JSON 格式

```json
{
  "check_time": "2026-02-25T16:30:00.000000",
  "config": {
    "master_sync_base": "bfdf823",
    "target_sync_base": "4be9942",
    "master_branch": "origin/master",
    "target_branch": "origin/v2.9.0"
  },
  "stats": {
    "master_count": 40,
    "target_count": 3,
    "unsynced_count": 39,
    "whitelisted_count": 1
  },
  "unsynced_commits": [
    {
      "hash": "a5d004b292fec...",
      "title": "[Feature][Infra](XMLIR-8128) support isneginf_out",
      "author_email": "wangxu46@baidu.com",
      "author": "wangxu46",
      "date": "2026-02-02"
    }
  ]
}
```

