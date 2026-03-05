from typing import Dict, List, Any, Optional
import asyncio
import logging
import json
from app.config import MessageType
from app.webhook import webhook_sender
from app.command_handler import handle_normal_command

logger = logging.getLogger(__name__)

class MessageHandler:
    """消息处理器：解析消息并生成基础回复"""
    
    @staticmethod
    def parse_message_body(body: List[Dict]) -> Dict[str, Any]:
        """
        解析消息体，提取各种类型的内容
        
        Args:
            body: 原始消息体列表
            
        Returns:
            解析后的消息内容字典
        """
        result = {
            "text_parts": [],
            "commands": [],
            "links": [],
            "images": [],
            "mentioned_users": [],
            "full_text": ""
        }
        
        for item in body:
            item_type = item.get("type", "").upper()
            
            if item_type == MessageType.TEXT:
                content = item.get("content", "").strip()
                if content:
                    result["text_parts"].append(content)
                    
            elif item_type == MessageType.COMMAND:
                command = item.get("commandname", "")
                if command:
                    result["commands"].append(command)
                    
            elif item_type == MessageType.LINK:
                # 链接消息，提取链接信息
                link_info = {
                    "label": item.get("label", ""),
                    "url": item.get("url", "")
                }
                result["links"].append(link_info)
                
                # 链接的标签也作为文本处理
                if link_info["label"]:
                    result["text_parts"].append(link_info["label"])
                    
            elif item_type == MessageType.IMAGE:
                # 图片消息，记录下载URL
                image_info = {
                    "downloadurl": item.get("downloadurl", "")
                }
                result["images"].append(image_info)
                
            elif item_type == MessageType.AT:
                # @提及消息
                if "robotid" in item:
                    # @机器人的消息
                    robot_info = {
                        "type": "robot",
                        "id": item.get("robotid"),
                        "name": item.get("name", "")
                    }
                    # 可以在这里记录机器人被@的信息
                elif "userid" in item:
                    # @其他用户的
                    user_info = {
                        "type": "user",
                        "id": item.get("userid"),
                        "name": item.get("name", "")
                    }
                    result["mentioned_users"].append(user_info)
        
        # 合并所有文本部分
        result["full_text"] = " ".join(result["text_parts"])
        
        return result
    
    @staticmethod
    def handle_verification_request(echostr: str) -> str:
        """
        处理验证请求（企业微信配置回调URL时需要）
        
        Args:
            echostr: 企业微信发送的随机字符串
            
        Returns:
            直接返回echostr
        """
        return echostr

    @staticmethod
    def _handle_text_messages(full_text: str, agent_id: str, group_id: str, sender_id: str) -> Optional[Dict]:
        """
        处理文本消息（可能包含命令文本）
        
        Args:
            full_text: 完整文本内容
            agent_id: 机器人ID
            group_id: 群组ID
            sender_id: 发送者ID
            
        Returns:
            处理结果字典，如果文本被识别为命令并处理则返回结果，否则返回None
        """
        try:
            logger.info(f"处理命令: {full_text}")
            # 使用command_handler检查文本是否为命令
            command_result = handle_normal_command(full_text, group_id, sender_id)

            if command_result.get("success", False):
                # 这是命令，返回处理结果
                logger.info(f"命令处理结果: {command_result.get('result', {})}")
            else:
                logger.warning(f"未知命令: {full_text}")
            
            return {
                "success": True,
                "error_msg": None
            }
        except Exception as e:
            logger.warning(f"文本命令处理失败: {e}，回退到默认处理")
            return {
                "success": False,
                "error_msg": f"未知命令: {e}"
            }
    
    @staticmethod
    def process_message_event(message_data: Dict) -> Dict:
        """
        处理消息接收事件
        
        Args:
            message_data: 解密后的完整消息数据
            
        Returns:
            处理结果
        """
        try:
            # 提取关键信息
            event_type = message_data.get("eventtype", "")
            
            # 只处理消息接收事件
            if event_type != "MESSAGE_RECEIVE":
                return {
                    "success": False,
                    "error_msg": f"忽略非消息事件: {event_type}"
                }
            
            agent_id = message_data.get("agentid", "")
            group_id = message_data.get("groupid", "")
            sender_id = message_data.get("message", {}).get("header", {}).get("fromuserid", "")
            
            if not all([agent_id, group_id, sender_id]):
                return {
                    "success": False,
                    "error_msg": "缺少必要的消息字段"
                }
            
            # 解析消息内容
            msg_body = message_data.get("message", {}).get("body", [])
            parsed_content = MessageHandler.parse_message_body(msg_body)
            
            # 检查消息类型，当前只处理TEXT字段的消息
            unsupported_types = []
            if parsed_content["commands"]:
                unsupported_types.append("COMMAND(命令)")
            if parsed_content["links"]:
                unsupported_types.append("LINK(链接)")
            if parsed_content["images"]:
                unsupported_types.append("IMAGE(图片)")
            
            # 如果存在除TEXT外的其他消息类型或full_text为空，返回提示
            if unsupported_types or not parsed_content["full_text"]:
                warning_msg = "⚠️ 未检测到有效命令！\n\n"
                
                if unsupported_types:
                    warning_msg += f"请输入文本命令，检测到不支持的消息类型: {', '.join(unsupported_types)}\n\n"
                
                warning_msg += (
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
                
                return {
                    "success": False,
                    "error_msg": f"不支持的消息类型: {', '.join(unsupported_types)}"
                }
            
            # 2. 处理文本消息（可能包含命令文本）
            if parsed_content["full_text"]:
                result = MessageHandler._handle_text_messages(
                    parsed_content["full_text"],
                    agent_id,
                    group_id,
                    sender_id
                )
                return result
                
            
        except Exception as e:
            return {
                "success": False,
                "error_msg": f"消息处理异常: {str(e)}"
            }