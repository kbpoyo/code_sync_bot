#!/usr/bin/env python3
"""
命令处理器模块 - 用于处理不同的文本命令

实现命令的识别、处理和响应生成，保持高度解耦。
"""

import logging
import asyncio
import json
import yaml
import os
import re
from typing import Dict, List, Any, Optional, Callable
from enum import Enum

from app.webhook import webhook_sender
from app.code_sync_reporter import CodeSyncReporter
from app.config import MessageType

logger = logging.getLogger(__name__)


class CommandType(Enum):
    """命令类型枚举"""
    SYNC_CHECK = "同步检测"  # 代码同步检测命令
    WHITELIST_ADD = "白名单添加"  # 添加白名单命令
    HELP = "帮助"  # 帮助命令
    UNKNOWN = "未知命令"     # 未知命令
    

class CommandResult:
    """命令处理结果封装"""
    
    def __init__(self, 
                 success: bool, 
                 messages: List[Dict] = None,
                 command_type: CommandType = None,
                 error_msg: str = None):
        self.success = success
        self.command_type = command_type
        self.error_msg = error_msg
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            "success": self.success,
            "command_type": self.command_type.value if self.command_type else None,
            "error_msg": self.error_msg
        }


class CommandHandler:
    """命令处理器基类"""
    
    def __init__(self):
        self.handlers: Dict[CommandType, Callable] = {}
        self._register_handlers()
    
    def _register_handlers(self):
        """注册命令处理器"""
        self.handlers[CommandType.SYNC_CHECK] = self._handle_sync_check
        self.handlers[CommandType.WHITELIST_ADD] = self._handle_whitelist_add
        self.handlers[CommandType.HELP] = self._handle_help
        self.handlers[CommandType.UNKNOWN] = self._handle_unknown_command
        
    def recognize_command(self, text: str) -> CommandType:
        """
        识别文本中的命令
        
        Args:
            text: 输入的文本
            
        Returns:
            识别的命令类型
        """
        # 清理文本，去除首尾空格
        text = text.strip()
        cleaned_text = text.lower()
        
        # 优先检查白名单添加命令（支持多种格式）
        # 英文格式
        if cleaned_text.startswith("whitelist add:"):
            return CommandType.WHITELIST_ADD
        
        # 检查help命令
        help_commands = ["帮助", "help", "使用说明", "使用方法", "功能介绍"]
        for help_cmd in help_commands:
            if help_cmd in cleaned_text:
                return CommandType.HELP
        
        # 精确匹配的命令列表
        exact_commands = {
            "同步检测": CommandType.SYNC_CHECK,
            "同步检查": CommandType.SYNC_CHECK,
            "代码同步": CommandType.SYNC_CHECK,
            "检测同步": CommandType.SYNC_CHECK,
        }
        
        # 检查精确匹配
        for cmd_str, cmd_type in exact_commands.items():
            if cmd_str in text:  # 在原始文本中检查中文命令
                return cmd_type
        
        # 模糊匹配
        sync_keywords = ["同步", "检测", "检查", "代码"]
        found_keywords = sum(1 for keyword in sync_keywords if keyword in text)
        
        if found_keywords >= 2:  # 如果找到至少2个关键词，则认为是同步检测命令
            return CommandType.SYNC_CHECK
        
        return CommandType.UNKNOWN
    
    def handle_command(self, 
                       command_type: CommandType, 
                       text: str = "",
                       group_id: str = None,
                       sender_id: str = None) -> Dict[str, Any]:
        """
        处理命令
        
        Args:
            command_type: 命令类型
            text: 原始文本（用于上下文）
            group_id: 群组ID
            sender_id: 发送者ID
            
        Returns:
            处理结果
        """
        try:
            # 查找对应的处理器
            handler = self.handlers.get(command_type)
            # 调用处理器
            logger.info(f"开始处理命令: {command_type.value}, 群组: {group_id}, 发送者: {sender_id}")
            result = handler(text, group_id, sender_id)
            
            return result.to_dict()
            
        except Exception as e:
            logger.error(f"处理命令时出错: {e}", exc_info=True)
            return CommandResult(
                success=False,
                command_type=command_type,
                error_msg=f"内部错误: {str(e)}"
            ).to_dict()
    
    def _handle_unknown_command(self, text: str, group_id: str, sender_id: str) -> CommandResult:
        """处理未知命令"""
        try:
            warning_msg = (
                        "⚠️ 未检测到有效命令！\n\n"
                        f"📌 支持的命令:\n"
                        f"• 同步检测 - 获取同步报告\n"
                        f"• whitelist add: hash1 hash2 ... - 新增白名单\n"
                        f"• help - 帮助信息\n"
            )
            
            webhook_sender.send_text_message(
                group_id=group_id,
                content=warning_msg,
                at_users=[sender_id] if sender_id else None
            )
            
            return CommandResult(
                success=True,
                command_type=CommandType.UNKNOWN,
                error_msg="未知命令！"
            )
            
        except Exception as e:
            logger.error(f"处理未知命令时出错: {e}", exc_info=True)
            return CommandResult(
                success=False,
                command_type=CommandType.UNKNOWN,
                error_msg=f"内部错误: {str(e)}"
            )
            
    def _handle_help(self, text: str, group_id: str, sender_id: str) -> CommandResult:
        """
        处理帮助命令 - 返回使用方法
        
        Args:
            text: 命令文本
            group_id: 目标群组ID
            sender_id: 发送者ID
            
        Returns:
            包含帮助信息的CommandResult对象
        """
        try:
            help_content = (
                "🤖 分支同步检测机器人使用指南\n"
                "📌 可用命令:\n"
                "1️⃣ 同步检测\n"
                "   用法: 发送「同步检测」或「同步检查」\n"
                "   功能: 检查代码同步状态，发送未同步的commit报告\n\n"
                "2️⃣ 白名单管理\n"
                "   用法: whitelist add: hash1 hash2 ...\n"
                "   功能: 添加commit hash到白名单，这些commit将被过滤\n\n"
                "3️⃣ 帮助\n"
                "   用法: 发送「帮助」、「help」、「使用说明」或「功能介绍」\n"
                "   功能: 查看机器人使用指南\n\n"
                "💡 提示:\n"
                "• 白名单中的commit将不会出现在同步报告中\n"
                "• hash格式为8-40位十六进制字符\n"
                "• 同步报告会@相关作者\n\n"
            )
            
            logger.info(f"发送帮助信息，群组: {group_id}, 发送者: {sender_id}")
            
            webhook_sender.send_text_message(
                group_id=group_id,
                content=help_content,
                at_users=[sender_id] if sender_id else None
            )
            
            return CommandResult(
                success=True,
                command_type=CommandType.HELP,
                error_msg=None,
            )
            
        except Exception as e:
            logger.error(f"处理帮助命令时出错: {e}", exc_info=True)
            return CommandResult(
                success=False,
                command_type=CommandType.HELP,
                error_msg=f"帮助命令执行失败: {str(e)}"
            )

    def _handle_sync_check(self, text: str, group_id: str, sender_id: str) -> CommandResult:
        """
        处理同步检测命令 - 只检测返回值并记录日志
        
        Args:
            text: 命令文本
            group_id: 目标群组ID
            sender_id: 发送者ID
            
        Returns:
            包含同步检查状态的CommandResult对象
        """
        try:
            # 创建代码同步报告器
            reporter = CodeSyncReporter()
            
            # 执行同步检查
            result = reporter.run_code_sync(group_id)
            success = result.get("success", False)
            execution_log = result.get("execution_log", "未知错误")
            
            if success:
                # 成功：只打印日志
                logger.info(f"✅ 同步检测成功执行完成，群组: {group_id}, 发送者: {sender_id}")
                # 不需要发送消息，因为消息已经在run_code_sync中发送了
            else:
                # 失败：记录日志并通过webhook_sender发送错误消息
                logger.error(f"❌ 同步检测失败，群组: {group_id}, 错误: {execution_log}")
                
                error_content = f"❌ 同步报告获取失败\n原因: {execution_log[:200]}...\n"
                
                # 通过webhook_sender发送错误消息到群组
                webhook_sender.send_text_message(
                    group_id=group_id,
                    content=error_content,
                    at_users=[sender_id] if sender_id else None
                )
                
            return CommandResult(
                success=success,
                command_type=CommandType.SYNC_CHECK,
                error_msg=None if success else execution_log
            )
            
        except Exception as e:
            logger.error(f"处理同步检测命令时出错: {e}", exc_info=True)
            return CommandResult(
                success=False,
                command_type=CommandType.SYNC_CHECK,
                error_msg=f"同步检测命令执行失败: {str(e)}"
            )
    
    def _handle_whitelist_add(self, text: str, group_id: str, sender_id: str) -> CommandResult:
        """
        处理白名单添加命令
        
        Args:
            text: 命令文本，格式为 "whitelist add: hash1 hash2 ..."
            group_id: 目标群组ID
            sender_id: 发送者ID
            
        Returns:
            包含白名单添加状态的CommandResult对象
        """
        try:
            # 获取whitelist.yaml文件路径
            # 获取项目根目录
            current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            whitelist_path = os.path.join(current_dir, "code_sync", "whitelist.yaml")
            
            # 解析命令，提取hash值
            # 格式: "whitelist add: hash1 hash2 ..."
            parts = text.split(":", 1)
            if len(parts) != 2:
                raise ValueError("命令格式错误，应为: whitelist add: hash1 hash2 ...")
            
            hash_list_str = parts[1].strip()
            new_hashes = [h.strip() for h in hash_list_str.split() if h.strip()]
            
            if not new_hashes:
                raise ValueError("未提供要添加的hash值")
            
            # 验证hash格式（支持7-40位十六进制字符，如Git commit hash）
            hash_pattern = re.compile(r'^[a-fA-F0-9]{7,40}')
            invalid_hashes = [h for h in new_hashes if not hash_pattern.match(h)]
            
            if invalid_hashes:
                raise ValueError(
                    f"以下hash格式不正确: {', '.join(invalid_hashes)}\n"
                    f"正确的hash格式: 8-40位十六进制字符（a-f0-9）"
                )
            
            # 读取现有白名单
            if os.path.exists(whitelist_path):
                with open(whitelist_path, 'r', encoding='utf-8') as f:
                    whitelist_data = yaml.safe_load(f) or {}
            else:
                whitelist_data = {"whitelist": {"by_hash": [], "by_keyword": [], "by_author": []}}
            
            # 获取现有的hash白名单
            existing_hashes = whitelist_data.get("whitelist", {}).get("by_hash") or []

            # 添加新的hash值（去重）
            added_hashes = []
            logger.info(f"new hashes: {new_hashes}")
            for new_hash in new_hashes:
                if new_hash not in existing_hashes:
                    existing_hashes.append(new_hash)
                    added_hashes.append(new_hash)
            
            # 保存白名单
            whitelist_data["whitelist"]["by_hash"] = existing_hashes
            
            with open(whitelist_path, 'w', encoding='utf-8') as f:
                yaml.dump(whitelist_data, f, allow_unicode=True, default_flow_style=False)
            
            # 生成成功消息
            if added_hashes:
                success_content = f"✅ 白名单添加成功\n\n已添加 {len(added_hashes)} 个hash:\n"
                success_content += "\n".join([f"  • {h}" for h in added_hashes])
                success_content += f"\n\n当前白名单hash总数: {len(existing_hashes)}"
            else:
                success_content = f"⚠️ 所有提供的hash已存在于白名单中，无需重复添加"
            
            logger.info(f"白名单添加完成，添加了 {len(added_hashes)} 个hash，群组: {group_id}, 发送者: {sender_id}")
            
            # 发送成功消息
            webhook_sender.send_text_message(
                group_id=group_id,
                content=success_content,
                at_users=[sender_id] if sender_id else None
            )
            
            return CommandResult(
                success=True,
                command_type=CommandType.WHITELIST_ADD,
                error_msg=None,
            )
            
        except Exception as e:
            error_msg = f"添加白名单失败: {str(e)}"
            logger.error(error_msg, exc_info=True)
            
            # 发送错误消息
            webhook_sender.send_text_message(
                group_id=group_id,
                content=f"❌ {error_msg}",
                at_users=[sender_id] if sender_id else None
            )
            
            return CommandResult(
                success=False,
                command_type=CommandType.WHITELIST_ADD,
                error_msg=error_msg,
            )

# 全局命令处理器实例
command_handler = CommandHandler()


def handle_normal_command(text: str, group_id: str = None, sender_id: str = None) -> Dict:
    """
    处理普通命令 - 外部调用接口
    
    Args:
        text: 输入的文本
        group_id: 群组ID
        sender_id: 发送者ID
        
    Returns:
        处理结果字典
    """
    # 识别命令
    command_type = command_handler.recognize_command(text)
    
    # 处理命令
    result = command_handler.handle_command(
        command_type,
        text,
        group_id,
        sender_id
    )
    
    return result
