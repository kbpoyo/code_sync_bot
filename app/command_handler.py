#!/usr/bin/env python3
"""
命令处理器模块 - 用于处理不同的文本命令

实现命令的识别、处理和响应生成，保持高度解耦。
"""

import logging
import asyncio
import json
from typing import Dict, List, Any, Optional, Callable
from enum import Enum

from app.webhook import webhook_sender
from app.code_sync_reporter import CodeSyncReporter
from app.config import MessageType

logger = logging.getLogger(__name__)


class CommandType(Enum):
    """命令类型枚举"""
    SYNC_CHECK = "同步检测"  # 代码同步检测命令
    UNKNOWN = "未知命令"     # 未知命令
    

class CommandResult:
    """命令处理结果封装"""
    
    def __init__(self, 
                 success: bool, 
                 messages: List[Dict] = None,
                 command_type: CommandType = None,
                 error: str = None):
        self.success = success
        self.messages = messages or []
        self.command_type = command_type
        self.error = error
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            "success": self.success,
            "command_type": self.command_type.value if self.command_type else None,
            "messages": self.messages,
            "error": self.error
        }


class CommandHandler:
    """命令处理器基类"""
    
    def __init__(self):
        self.handlers: Dict[CommandType, Callable] = {}
        self._register_handlers()
    
    def _register_handlers(self):
        """注册命令处理器"""
        self.handlers[CommandType.SYNC_CHECK] = self._handle_sync_check
        
    def recognize_command(self, text: str) -> CommandType:
        """
        识别文本中的命令
        
        Args:
            text: 输入的文本
            
        Returns:
            识别的命令类型
        """
        # 清理文本，去除首尾空格并转为小写处理
        cleaned_text = text.strip().lower()
        
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
    
    def process_command(self, 
                       command_type: CommandType, 
                       text: str = "",
                       group_id: str = None,
                       sender_id: str = None) -> CommandResult:
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
            if command_type == CommandType.UNKNOWN:
                return self._handle_unknown_command(text, group_id, sender_id)
            
            # 查找对应的处理器
            handler = self.handlers.get(command_type)
            if not handler:
                return self._handle_unknown_command(
                    f"未找到命令处理器: {command_type.value}", 
                    group_id, 
                    sender_id
                )
            
            # 调用处理器
            logger.info(f"开始处理命令: {command_type.value}, 群组: {group_id}, 发送者: {sender_id}")
            result = handler(text, group_id, sender_id)
            
            return result
            
        except Exception as e:
            logger.error(f"处理命令时出错: {e}", exc_info=True)
            return CommandResult(
                success=False,
                command_type=command_type,
                error=f"内部错误: {str(e)}"
            )
    
    def _handle_unknown_command(self, text: str, group_id: str, sender_id: str) -> CommandResult:
        """处理未知命令"""
        reply_content = (
            f"🤔 未识别的命令或消息: {text[:50]}...\n\n"
            f"可用命令:\n"
            f"• **同步检测** - 检查代码同步状态\n"
            f"• **同步检查** - 同'同步检测'\n\n"
            f"如需帮助，请输入明确的命令。"
        )
        
        messages = [{
            "type": MessageType.TEXT,
            "content": reply_content
        }]
        
        # 如果知道发送者，可以@TA
        if sender_id:
            messages.append({
                "type": MessageType.AT,
                "atuserids": [sender_id]
            })
        
        return CommandResult(
            success=True,
            command_type=CommandType.UNKNOWN,
            messages=messages
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
                
                error_content = f"🚫 同步报告获取失败\n\n原因: {execution_log[:200]}\n\n请检查系统配置或联系管理员。"
                
                # 通过webhook_sender发送错误消息到群组
                webhook_sender.send_text_message(
                    group_id=group_id,
                    content=error_content,
                    at_users=[sender_id] if sender_id else None
                )
                
            return CommandResult(
                success=success,
                command_type=CommandType.SYNC_CHECK,
                error=None if success else result.get("error")
            )
            
        except Exception as e:
            logger.error(f"处理同步检测命令时出错: {e}", exc_info=True)
            return CommandResult(
                success=False,
                command_type=CommandType.SYNC_CHECK,
                error=f"处理命令失败: {str(e)}"
            )

# 全局命令处理器实例
command_handler = CommandHandler()


def handle_text_command(text: str, group_id: str = None, sender_id: str = None) -> Dict:
    """
    处理文本命令 - 外部调用接口
    
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
    result = command_handler.process_command(
        command_type,
        text,
        group_id,
        sender_id
    )
    
    return {
        "is_command": command_type != CommandType.UNKNOWN,
        "command_type": command_type.value,
        "result": result.to_dict(),
        "should_reply_immediately": True,
        "process_completed": True
    }


async def async_handle_text_command(text: str, group_id: str = None, sender_id: str = None) -> Dict:
    """
    异步处理文本命令 - 外部调用接口（异步版本）
    
    Args:
        text: 输入的文本
        group_id: 群组ID
        sender_id: 发送者ID
        
    Returns:
        处理结果字典
    """
    # 在当前线程中处理命令识别和回复
    return handle_text_command(text, group_id, sender_id)


def register_custom_command(command_str: str, handler_func: Callable, 
                           description: str = "", aliases: List[str] = None):
    """
    注册自定义命令
    
    Args:
        command_str: 命令字符串
        handler_func: 处理函数
        description: 命令描述
        aliases: 命令别名
    """
    logger.info(f"注册自定义命令: {command_str}")
    # TODO: 实现自定义命令注册
    pass