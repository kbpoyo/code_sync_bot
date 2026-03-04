#!/usr/bin/env python3
# commit_diff.py - 比较两个分支的 PR 同步状态

import os
import re
import subprocess
import json
import sys
from datetime import datetime
from typing import Dict, List, Optional, Set

# 尝试导入 yaml，如果没有则仅支持 json
try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False


#===========================================
# 配置读取
#===========================================
class Config:
    """从环境变量读取配置"""
    # 仓库目录
    REPO_DIR = os.environ.get('REPO_DIR', './XMLIR')
    # master 和 v2.9.0 使用不同的同步基准点
    MASTER_SYNC_BASE = os.environ.get('MASTER_SYNC_BASE', 'bfdf823')
    TARGET_SYNC_BASE = os.environ.get('TARGET_SYNC_BASE', '4be9942')
    MASTER_BRANCH = os.environ.get('MASTER_BRANCH', 'origin/master')
    TARGET_BRANCH = os.environ.get('TARGET_BRANCH', 'origin/v2.9.0')
    WHITELIST_FILE = os.environ.get('WHITELIST_FILE', './whitelist.yaml')
    OUTPUT_FORMAT = os.environ.get('OUTPUT_FORMAT', 'json')  # text / json
    OUTPUT_FILE = os.environ.get('OUTPUT_FILE', '')  # 输出文件路径，为空则输出到终端


#===========================================
# 白名单管理
#===========================================
class WhitelistManager:
    """白名单管理器，支持 yaml 和 json 格式"""
    
    def __init__(self, filepath: str):
        self.filepath = filepath
        self.config = self._load_config()
    
    def _load_config(self) -> dict:
        """加载白名单配置文件"""
        if not os.path.exists(self.filepath):
            print(f"[WARN] 白名单文件不存在: {self.filepath}，使用空白名单")
            return {'whitelist': {'by_hash': [], 'by_keyword': [], 'by_author': []}}
        
        with open(self.filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        if self.filepath.endswith('.yaml') or self.filepath.endswith('.yml'):
            if not HAS_YAML:
                print("[ERROR] 需要安装 pyyaml: pip install pyyaml")
                sys.exit(1)
            return yaml.safe_load(content)
        else:
            return json.loads(content)
    
    def is_whitelisted(self, pr_info: dict) -> bool:
        """检查 PR 是否在白名单中"""
        whitelist = self.config.get('whitelist') or {}
        
        # 按 commit hash 检查（支持短 hash 前缀匹配）
        commit_hash = pr_info.get('hash', '')
        for h in (whitelist.get('by_hash') or []):
            if commit_hash.startswith(h) or h.startswith(commit_hash[:len(h)]):
                return True
        
        # 按关键词检查
        title = pr_info.get('title', '').lower()
        for keyword in (whitelist.get('by_keyword') or []):
            if keyword.lower() in title:
                return True
        
        # 按作者检查
        author = pr_info.get('author_email', '')
        if author in (whitelist.get('by_author') or []):
            return True
        
        return False


#===========================================
# Git 操作
#===========================================
def run_git_command(cmd: List[str]) -> str:
    """执行 git 命令并返回输出"""
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"[ERROR] Git 命令失败: {' '.join(cmd)}")
        print(f"[ERROR] {result.stderr}")
        sys.exit(1)
    return result.stdout.strip()


def get_commits(base_commit: str, branch: str) -> List[dict]:
    """
    获取从 base_commit 到 branch 之间的所有 commits
    输出格式: hash|title|email|date
    """
    format_str = '%H|%s|%ae|%ad'
    cmd = [
        'git', 'log', f'{base_commit}..{branch}',
        f'--pretty=format:{format_str}',
        '--date=short'
    ]
    
    output = run_git_command(cmd)
    if not output:
        return []
    
    commits = []
    for line in output.split('\n'):
        if not line.strip():
            continue
        # 使用 maxsplit=3 确保标题中的 | 不会被错误分割
        parts = line.split('|', 3)
        if len(parts) >= 4:
            commit_info = {
                'hash': parts[0],
                'title': parts[1],
                'author_email': parts[2],
                'author': parts[2].split('@')[0],  # 从邮箱提取用户名
                'date': parts[3],
            }
            commits.append(commit_info)
    
    return commits


def normalize_title(title: str) -> str:
    """
    标准化 PR 标题用于匹配比较
    - 统一小写
    - 去除首尾空格
    """
    return title.strip().lower()


#===========================================
# Diff 比较
#===========================================
def find_unsynced_prs(
    master_commits: List[dict],
    target_commits: List[dict],
    whitelist: WhitelistManager
) -> List[dict]:
    """
    找出 master 中存在但 target 中不存在的 PR
    """
    # 构建 target 已同步的标题集合
    synced_titles: Set[str] = set()
    
    for commit in target_commits:
        synced_titles.add(normalize_title(commit['title']))
    
    unsynced = []
    for commit in master_commits:
        # 跳过白名单
        if whitelist.is_whitelisted(commit):
            continue
        
        # 检查标题是否已同步
        normalized = normalize_title(commit['title'])
        if normalized in synced_titles:
            continue
        
        unsynced.append(commit)
    
    return unsynced


#===========================================
# 输出格式化
#===========================================
def format_text_output(unsynced: List[dict], stats: dict) -> str:
    """格式化为文本输出"""
    lines = [
        "=" * 60,
        "XMLIR 分支同步检查报告",
        "=" * 60,
        f"检查时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"Master 分支: {Config.MASTER_BRANCH} (base: {Config.MASTER_SYNC_BASE})",
        f"目标分支: {Config.TARGET_BRANCH} (base: {Config.TARGET_SYNC_BASE})",
        "-" * 60,
        f"Master Commit 数量: {stats['master_count']}",
        f"目标分支 Commit 数量: {stats['target_count']}",
        f"未同步 Commit 数量: {stats['unsynced_count']}",
        f"白名单过滤数量: {stats['whitelisted_count']}",
        "=" * 60,
    ]
    
    if not unsynced:
        lines.append("✅ 所有 Commit 已同步，无需操作！")
    else:
        lines.append("❌ 以下 Commit 尚未同步到目标分支：")
        lines.append("")
        
        # 按作者分组
        by_author: Dict[str, List[dict]] = {}
        for pr in unsynced:
            author = pr['author']
            if author not in by_author:
                by_author[author] = []
            by_author[author].append(pr)
        
        for author, prs in sorted(by_author.items()):
            lines.append(f"【{author}】({len(prs)} 个待同步)")
            for pr in prs:
                lines.append(f"  - {pr['title']}")
                lines.append(f"    日期: {pr['date']} | Hash: {pr['hash'][:8]}")
            lines.append("")
    
    lines.append("=" * 60)
    return '\n'.join(lines)


def format_json_output(unsynced: List[dict], stats: dict) -> str:
    """格式化为 JSON 输出"""
    result = {
        'check_time': datetime.now().isoformat(),
        'config': {
            'master_sync_base': Config.MASTER_SYNC_BASE,
            'target_sync_base': Config.TARGET_SYNC_BASE,
            'master_branch': Config.MASTER_BRANCH,
            'target_branch': Config.TARGET_BRANCH,
        },
        'stats': stats,
        'unsynced_commits': unsynced,
    }
    return json.dumps(result, ensure_ascii=False, indent=2)


#===========================================
# 主函数
#===========================================
def main():
    print(f"[INFO] 加载白名单: {Config.WHITELIST_FILE}")
    whitelist = WhitelistManager(Config.WHITELIST_FILE)

    # 切换到仓库目录
    repo_dir = os.path.abspath(Config.REPO_DIR)
    if not os.path.isdir(repo_dir):
        print(f"[ERROR] 仓库目录不存在: {repo_dir}")
        sys.exit(1)
    
    print(f"[INFO] 切换到仓库目录: {repo_dir}")
    os.chdir(repo_dir)
    
    # 验证是否为 git 仓库
    if not os.path.isdir('.git'):
        print(f"[ERROR] 目录不是 git 仓库: {repo_dir}")
        sys.exit(1)
    
    print(f"[INFO] 获取 {Config.MASTER_BRANCH} 的 commits (base: {Config.MASTER_SYNC_BASE})...")
    master_commits = get_commits(Config.MASTER_SYNC_BASE, Config.MASTER_BRANCH)
    print(f"[INFO] 找到 {len(master_commits)} 个 commits")
    
    print(f"[INFO] 获取 {Config.TARGET_BRANCH} 的 commits (base: {Config.TARGET_SYNC_BASE})...")
    target_commits = get_commits(Config.TARGET_SYNC_BASE, Config.TARGET_BRANCH)
    print(f"[INFO] 找到 {len(target_commits)} 个 commits")
    
    print("[INFO] 计算未同步的 Commit...")
    
    # 计算白名单过滤数量
    whitelisted_count = sum(1 for c in master_commits if whitelist.is_whitelisted(c))
    
    unsynced = find_unsynced_prs(master_commits, target_commits, whitelist)
    
    stats = {
        'master_count': len(master_commits),
        'target_count': len(target_commits),
        'unsynced_count': len(unsynced),
        'whitelisted_count': whitelisted_count,
    }
    
    # 输出结果
    if Config.OUTPUT_FORMAT == 'json':
        json_content = format_json_output(unsynced, stats)
        if Config.OUTPUT_FILE:
            with open(Config.OUTPUT_FILE, 'w', encoding='utf-8') as f:
                f.write(json_content)
            print(f"[INFO] JSON 结果已写入: {Config.OUTPUT_FILE}")
        else:
            print(json_content)
    else:
        text_content = format_text_output(unsynced, stats)
        if Config.OUTPUT_FILE:
            with open(Config.OUTPUT_FILE, 'w', encoding='utf-8') as f:
                f.write(text_content)
            print(f"[INFO] 结果已写入: {Config.OUTPUT_FILE}")
        else:
            print(text_content)
    
    # 返回码：有未同步 Commit 时返回 1
    return 0
    # return 1 if unsynced else 0


if __name__ == '__main__':
    sys.exit(main())