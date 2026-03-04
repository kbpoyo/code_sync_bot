from typing import Dict, List, Any, Optional
from app.config import MessageType
from app.webhook import webhook_sender

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
    def generate_basic_response(parsed_content: Dict, group_id: str, user_id: str) -> Dict:
        """
        生成基础回复（不包含RAG/OCR等复杂处理）
        
        Args:
            parsed_content: 解析后的消息内容
            group_id: 群组ID
            user_id: 提问用户ID
            
        Returns:
            回复消息体和处理状态
        """
        body = []
        response_data = {
            "requires_further_processing": False,
            "reason": ""
        }
        
        # 1. 处理命令消息
        if parsed_content["commands"]:
            command = parsed_content["commands"][0]
            body.append({
                "type": MessageType.TEXT,
                "content": f"已收到您的命令: {command}。正在初始化处理..."
            })
            response_data["requires_further_processing"] = True
            response_data["reason"] = f"命令处理: {command}"
        
        # 2. 处理文本消息
        if parsed_content["full_text"]:
            # 基础回复：确认已收到消息
            reply_content = f"已收到您的问题：{parsed_content['full_text']}"
            
            # 根据内容判断是否需要进一步处理
            if len(parsed_content["full_text"]) > 10:  # 假设复杂问题需要进一步处理
                reply_content += "\n\n（此为自动回复，完整功能需要RAG系统支持）"
                response_data["requires_further_processing"] = True
                response_data["reason"] = "复杂问题需要RAG处理"
            else:
                reply_content += "\n（简单消息确认）"
            
            body.append({
                "type": MessageType.TEXT,
                "content": reply_content
            })
        
        # 3. 处理图片消息
        if parsed_content["images"]:
            image_count = len(parsed_content["images"])
            body.append({
                "type": MessageType.TEXT,
                "content": f"检测到 {image_count} 张图片。（OCR功能当前未启用）"
            })
            response_data["requires_further_processing"] = True
            response_data["reason"] = f"图片处理({image_count}张)"
        
        # 4. 处理链接消息
        if parsed_content["links"]:
            for link in parsed_content["links"]:
                body.append({
                    "type": MessageType.TEXT,
                    "content": f"收到链接：{link.get('label', '无标题')}"
                })
        
        # 5. 添加@回复（确保回复用户）
        if user_id:
            body.append({
                "type": MessageType.AT,
                "atuserids": [user_id]
            })
        
        # 6. 如果没有内容，返回默认回复
        if not body:
            body.append({
                "type": MessageType.TEXT,
                "content": "收到消息，但内容为空"
            })
        
        # 添加示例消息
        body.append({
            "type": MessageType.TEXT,
            "content": "\n📌 欢迎使用群组机器人！本服务提供基础消息接收和发送功能。"
        })
        
        return {
            "message_body": body,
            "response_data": response_data
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
                    "processed": False,
                    "reason": f"忽略非消息事件: {event_type}"
                }
            
            agent_id = message_data.get("agentid", "")
            group_id = message_data.get("groupid", "")
            sender_id = message_data.get("message", {}).get("header", {}).get("fromuserid", "")
            
            if not all([agent_id, group_id, sender_id]):
                return {
                    "processed": False,
                    "reason": "缺少必要的消息字段"
                }
            
            # 解析消息内容
            msg_body = message_data.get("message", {}).get("body", [])
            parsed_content = MessageHandler.parse_message_body(msg_body)
            
            # 发送确认消息
            ack_result = webhook_sender.send_acknowledge_message(
                group_id=group_id,
                user_id=sender_id,
                question=parsed_content["full_text"][:50] + "..." if len(parsed_content["full_text"]) > 50 else parsed_content["full_text"]
            )
            
            # 生成基础回复
            response = MessageHandler.generate_basic_response(
                parsed_content=parsed_content,
                group_id=group_id,
                user_id=sender_id
            )
            
            # 发送回复消息
            if response["message_body"]:
                send_result = webhook_sender.send_multi_part_message(group_id, response["message_body"])
                
                return {
                    "processed": True,
                    "agent_id": agent_id,
                    "group_id": group_id,
                    "sender_id": sender_id,
                    "content_summary": parsed_content["full_text"],
                    "ack_result": ack_result,
                    "reply_result": send_result,
                    "requires_further_processing": response["response_data"]["requires_further_processing"],
                    "reason": response["response_data"]["reason"]
                }
            
            return {
                "processed": False,
                "reason": "未能生成回复消息"
            }
            
        except Exception as e:
            return {
                "processed": False,
                "error": f"处理消息时出错: {str(e)}"
            }