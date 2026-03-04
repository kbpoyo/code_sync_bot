#!/usr/bin/env python3
"""
代码同步检查报告模块
用于执行code_sync.sh脚本并将结果发送给机器人
"""

import os
import subprocess
import json
import tempfile
import sys
from typing import Dict, List, Any, Optional
from datetime import datetime

# 添加父目录到sys.path以便导入app模块
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.webhook import webhook_sender
from app.config import WeChatConfig, MessageType


class CodeSyncReporter:
    """代码同步检查报告器"""
    
    def __init__(self, webhook_url: str = None):
        self.webhook_url = webhook_url or WeChatConfig.WEBHOOK_URL
        self.script_dir = os.path.join(os.path.dirname(__file__), '..', 'code_sync')
        self.code_sync_script = os.path.join(self.script_dir, 'code_sync.sh')
    
    def run_code_sync(self, group_id: str = "12566106") -> Dict[str, Any]:
        """
        运行代码同步检查脚本
        
        Args:
            group_id: 发送消息的群组ID
            
        Returns:
            运行结果字典
        """
        print(f"[INFO] 开始执行代码同步检查脚本: {self.code_sync_script}")  
        try:
            # 设置环境变量，强制输出为JSON格式
            env = os.environ.copy()
            env['OUTPUT_FORMAT'] = 'json'
            
            # 创建临时文件保存JSON输出
            temp_output = tempfile.NamedTemporaryFile(mode='w+', suffix='.json', delete=False)
            env['OUTPUT_FILE'] = temp_output.name
            
            print(f"[INFO] 开始执行代码同步检查脚本: {self.code_sync_script}")
            print(f"[INFO] 输出文件: {temp_output.name}")
            
            # 执行脚本
            process = subprocess.Popen(
                ['bash', self.code_sync_script],
                cwd=self.script_dir,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding='utf-8'
            )
            
            stdout, stderr = process.communicate(timeout=600)  # 10分钟超时
            
            # 收集执行日志
            execution_log = f"执行日志:\n"
            execution_log += f"返回码: {process.returncode}\n"
            
            if stdout:
                execution_log += f"标准输出:\n{stdout[:500]}...\n"
            
            if stderr:
                execution_log += f"错误输出:\n{stderr[:500]}\n"
            
            # 读取JSON输出文件
            if os.path.exists(temp_output.name):
                with open(temp_output.name, 'r', encoding='utf-8') as f:
                    try:
                        json_data = json.load(f)
                    except json.JSONDecodeError as e:
                        print(f"[ERROR] JSON解析失败: {e}")
                        json_data = None
            else:
                print(f"[ERROR] 输出文件不存在: {temp_output.name}")
                json_data = None
            
            # 清理临时文件
            try:
                os.unlink(temp_output.name)
            except OSError:
                pass
            
            # 处理结果
            if process.returncode != 0 and process.returncode != 1:
                # 脚本执行失败
                return self._handle_script_failure(group_id, process.returncode, stderr or stdout)
            
            if json_data:
                # 成功获取结果，发送格式化报告
                return self._send_formatted_report(group_id, json_data, execution_log)
            else:
                # 无JSON数据，使用文本输出
                return self._send_text_report(group_id, stdout or stderr, execution_log)
                
        except subprocess.TimeoutExpired:
            return self._handle_timeout(group_id)
        except Exception as e:
            return self._handle_unexpected_error(group_id, e)
    
    def _send_formatted_report(self, group_id: str, json_data: Dict, execution_log: str) -> Dict[str, Any]:
        """发送格式化的JSON报告"""
        try:
            # 解析JSON数据
            config = json_data.get('config', {})
            stats = json_data.get('stats', {})
            unsynced = json_data.get('unsynced_commits', [])
            
            # 构建消息
            all_messages = []
            
            # 统计信息作为第一条消息
            title = "📊 代码同步检查报告" if not unsynced else "⚠️ 代码同步检查报告（有未同步项）"
            
            # all_messages.append({
            #     "type": MessageType.TEXT,
            #     "content": f"{title}\n"
            #               f"检查时间: {json_data.get('check_time', '未知时间')}\n"
            #               f"Master分支: {config.get('master_branch')}\n"
            #               f"目标分支: {config.get('target_branch')}\n"
            #               f"Master commit数量: {stats.get('master_count', 0)}\n"
            #               f"目标分支 commit数量: {stats.get('target_count', 0)}\n"
            #               f"未同步 commit数量: {stats.get('unsynced_count', 0)}\n"
            #               f"白名单过滤: {stats.get('whitelisted_count', 0)}"
            # })

            check_message = (f"{title}\n"
                            f"检查时间: {json_data.get('check_time', '未知时间')}\n"
                            f"Master分支: {config.get('master_branch')}\n"
                            f"目标分支: {config.get('target_branch')}\n"
                            f"Master commit数量: {stats.get('master_count', 0)}\n"
                            f"目标分支 commit数量: {stats.get('target_count', 0)}\n"
                            f"未同步 commit数量: {stats.get('unsynced_count', 0)}\n"
                            f"白名单过滤: {stats.get('whitelisted_count', 0)}\n")
            
            # 如果有未同步项
            if unsynced:
                # 是否首次发送
                is_first_send = True
                # 按作者分组
                authors = {}
                for commit in unsynced:
                    author = commit.get('author', '未知作者')
                    if author not in authors:
                        authors[author] = []
                    authors[author].append(commit)
                
                # 创建当前消息组
                current_messages = []
                current_message = "📝 未同步 Commit (按作者分组):\n"
                
                # 遍历每个作者
                for author_index, (author, commits) in enumerate(authors.items()):
                    # 构建作者信息
                    author_info = f"👤 {author} ({len(commits)}个):\n"
                    
                    # 构建该作者的commit列表
                    commits_text = ""
                    for commit_index, commit in enumerate(commits):
                        commit_text = f"  • {commit.get('title')}\n"
                        commit_text += f"    日期: {commit.get('date', '未知')} ｜ Hash: {commit.get('hash', '未知')[:8]}\n"
                        commits_text += commit_text
                    
                    # 检查添加后是否超过1500字符
                    candidate_text = current_message + author_info + commits_text
                    if len(candidate_text) > 1800:
                        
                        # 首次发送加上检查信息
                        if is_first_send:
                            current_message = check_message + current_message
                            is_first_send = False
                        # 当前消息已满，保存并开始新消息
                        current_messages.append({
                            "type": MessageType.TEXT,
                            "content": current_message.rstrip()  # 移除末尾换行
                        })
                        
                        # 开始新消息（如果还有更多作者）
                        current_message = "📝 未同步 Commit (按作者分组) 续:\n" + author_info + commits_text
                    else:
                        # 可以添加到当前消息
                        current_message = candidate_text
                
                # 添加最后一个消息
                if current_message and current_message != "📝 未同步 Commit (按作者分组):\n":
                    current_message = current_message +  f"\n✅ 本次同步检查发现 {len(unsynced)} 个未同步commit，共 {len(authors)} 位作者"
                    current_messages.append({
                        "type": MessageType.TEXT,
                        "content": current_message.rstrip()
                    })
                
                # 将所有消息添加到总消息列表
                all_messages.extend(current_messages)
            
            # 分批发送消息，每次最多发送10条
            final_result = {"success": True}
            for message in all_messages:
                send_result = webhook_sender.send_multi_part_message(group_id, [message])
                
                # 只要任何一批失败，整体就视为失败
                if not send_result.get("success", False):
                    final_result["success"] = False
                    final_result["last_failure"] = send_result
            
            # 如果没有消息发送，补充默认成功
            if "success" not in final_result:
                final_result["success"] = True
            
            return {
                "success": final_result["success"],
                "webhook_result": final_result,
                "sync_data": json_data,
                "execution_log": execution_log
            }
            
        except Exception as e:
            print(f"[ERROR] 格式化报告失败: {e}")
            # 回退到发送原始JSON
            return self._send_text_report(group_id, json.dumps(json_data, indent=2, ensure_ascii=False), execution_log)
    
    def _send_text_report(self, group_id: str, text_content: str, execution_log: str) -> Dict[str, Any]:
        """发送文本报告"""
        # 截断过长内容
        if len(text_content) > 2000:
            text_content = text_content[:1997] + "..."
        
        result = webhook_sender.send_text_message(
            group_id=group_id,
            content=f"📋 代码同步检查结果:\n{text_content}"
        )
        
        return {
            "success": result.get("success", False),
            "webhook_result": result,
            "sync_data": None,
            "execution_log": execution_log
        }
    
    def _handle_script_failure(self, group_id: str, returncode: int, error_msg: str) -> Dict[str, Any]:
        """处理脚本执行失败"""
        result = webhook_sender.send_text_message(
            group_id=group_id,
            content=f"❌ 代码同步检查失败\n"
                   f"返回码: {returncode}\n"
                   f"错误信息: {error_msg[:1000] if error_msg else '未知错误'}"
        )
        
        return {
            "success": result.get("success", False),
            "webhook_result": result,
            "sync_data": None,
            "execution_log": f"脚本失败: returncode={returncode}, error={error_msg}",
            "error": True
        }
    
    def _handle_timeout(self, group_id: str) -> Dict[str, Any]:
        """处理超时"""
        result = webhook_sender.send_text_message(
            group_id=group_id,
            content=f"⏱️ 代码同步检查超时\n"
                   f"脚本执行时间超过10分钟"
        )
        
        return {
            "success": result.get("success", False),
            "webhook_result": result,
            "sync_data": None,
            "execution_log": "执行超时（超过600秒）",
            "error": True
        }
    
    def _handle_unexpected_error(self, group_id: str, error: Exception) -> Dict[str, Any]:
        """处理未预期错误"""
        result = webhook_sender.send_text_message(
            group_id=group_id,
            content=f"🔥 代码同步检查遇到未预期错误\n"
                   f"错误类型: {type(error).__name__}\n"
                   f"错误信息: {str(error)[:500]}"
        )
        
        return {
            "success": False,
            "webhook_result": result,
            "sync_data": None,
            "execution_log": f"未预期错误: {error}",
            "error": True
        }


def run_code_sync_and_report(group_id: str = "12566106") -> Dict[str, Any]:
    """
    方便调用的函数：运行代码同步并发送报告
    
    Args:
        group_id: 群组ID
        
    Returns:
        运行结果
    """
    reporter = CodeSyncReporter()
    return reporter.run_code_sync(group_id)


if __name__ == "__main__":
    # 命令行接口
    import argparse
    
    parser = argparse.ArgumentParser(description="运行代码同步检查并发送报告")
    parser.add_argument("--group-id", default="12566106", help="企业微信群组ID")
    parser.add_argument("--verbose", "-v", action="store_true", help="显示详细信息")
    
    args = parser.parse_args()
    
    print(f"[INFO] 开始代码同步检查报告，目标群组: {args.group_id}")
    result = run_code_sync_and_report(args.group_id)
    
    if args.verbose:
        print(f"[INFO] 执行结果: {json.dumps(result, indent=2, ensure_ascii=False)}")
    
    if result.get("success"):
        print("[INFO] 报告发送成功")
        sys.exit(0)
    else:
        print("[ERROR] 报告发送失败")
        sys.exit(1)