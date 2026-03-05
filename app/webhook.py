import json
import requests
import logging
from typing import List, Dict, Any, Optional
from app.config import WeChatConfig, ERROR_MAPPING, MessageType

logger = logging.getLogger(__name__)

class WebhookSender:
    """企业微信群组Webhook消息发送器"""
    
    def __init__(self, webhook_url: str = None):
        self.webhook_url = webhook_url or WeChatConfig.WEBHOOK_URL
    
    def send_text_message(self, group_id: str, content: str, at_users: List[str] = None) -> Dict:
        """
        发送文本消息到群组
        
        Args:
            group_id: 群组ID
            content: 文本内容
            at_users: 要@的用户ID列表
            
        Returns:
            发送结果
        """
        message_body = [{"type": MessageType.TEXT, "content": content}]
        
        if at_users:
            message_body.append({
                "type": MessageType.AT,
                "atuserids": at_users
            })
        
        return self._send_message(group_id, message_body)
    
    def send_markdown_message(self, group_id: str, content: str, at_users: List[str] = None) -> Dict:
        """
        发送Markdown消息到群组
        
        Args:
            group_id: 群组ID
            content: Markdown内容
            at_users: 要@的用户ID列表
            
        Returns:
            发送结果
        """
        message_body = [{"type": MessageType.MD, "content": content}]
        
        if at_users:
            message_body.append({
                "type": MessageType.AT,
                "atuserids": at_users
            })
        
        return self._send_message(group_id, message_body)
    
    def send_link_message(self, group_id: str, links: List[Dict], at_users: List[str] = None) -> Dict:
        """
        发送链接消息到群组
        
        Args:
            group_id: 群组ID
            links: 链接列表，每个链接格式为 {"label": "标题", "href": "URL"}
            at_users: 要@的用户ID列表
            
        Returns:
            发送结果
        """
        message_body = []
        
        for link in links:
            message_body.append({
                "type": MessageType.LINK,
                "label": link.get('label', '链接'),
                "href": link.get('href', '')
            })
        
        if at_users:
            message_body.append({
                "type": MessageType.AT,
                "atuserids": at_users
            })
        
        return self._send_message(group_id, message_body)
    
    def send_multi_part_message(self, group_id: str, parts: List[Dict]) -> Dict:
        """
        发送复合消息（支持多种消息类型组合）
        
        Args:
            group_id: 群组ID
            parts: 消息部件列表，每个部件需指定type和对应内容
            
        Returns:
            发送结果
        """
        return self._send_message(group_id, parts)
    
    def _send_message(self, group_id: str, message_body: List[Dict]) -> Dict:
        """
        内部方法：发送消息到Webhook
        
        Args:
            group_id: 群组ID
            message_body: 消息体列表
            
        Returns:
            发送结果
        """
        # 将群组ID转换为整数（因为企业微信API可能要求数字类型）
        try:
            group_id_int = int(group_id)
        except (ValueError, TypeError):
            logger.warning(f"Invalid group_id: {group_id}")
            group_id_int = group_id  # 如果转换失败，保持原样
        
        payload = {
            "message": {
                "header":{
                    "toid":[group_id_int]  # 注意：必须使用列表格式，且应为数字类型
                },
                "body": message_body
            }
        }
        
        try:
            response = requests.post(
                self.webhook_url,
                headers={"Content-Type": "application/json"},
                data=json.dumps(payload),
                timeout=10
            )
            
            # 处理响应
            if response.status_code == 200:
                resp_data = response.json()
                return self._handle_webhook_response(resp_data, group_id)
            else:
                return {
                    "success": False,
                    "status_code": response.status_code,
                    "error_msg": f"HTTP错误: {response.status_code}"
                }
                
        except requests.exceptions.Timeout:
            return {
                "success": False,
                "error_msg": "请求超时"
            }
        except requests.exceptions.RequestException as e:
            return {
                "success": False,
                "error_msg": f"网络错误: {str(e)}"
            }
        except Exception as e:
            return {
                "success": False,
                "error_msg": f"未知错误: {str(e)}"
            }
    
    def _handle_webhook_response(self, resp_data: Dict, group_id: str) -> Dict:
        """
        处理Webhook响应，解析错误码
        
        Args:
            resp_data: Webhook返回的JSON数据
            group_id: 群组ID
            
        Returns:
            处理后的发送结果
        """
        errcode = resp_data.get("errcode", 0)
        
        result = {
            "success": errcode == 0,
            "errcode": errcode,
            "error_msg": ERROR_MAPPING.get(errcode, f"未知错误码: {errcode}"),
            "data": resp_data.get("data", {})
        }
        
        if errcode == -1:
            # 系统错误
            logger.error(f"系统错误发送到群组 {group_id}: {result['error_msg']}")
        elif resp_data.get("data", {}).get("fail"):
            # 部分用户发送失败
            failed_users = resp_data["data"]["fail"]
            for user_id, user_errcode in failed_users.items():
                user_error = ERROR_MAPPING.get(user_errcode, f"未知错误码: {user_errcode}")
                logger.warning(f"群组 {group_id} 中用户 {user_id} 发送失败: {user_error}")
            result["failed_users"] = failed_users
        elif errcode == 0:
            # 发送成功
            logger.info(f"消息成功发送到群组 {group_id}")
        
        return result


# 全局Webhook发送器实例
webhook_sender = WebhookSender()
