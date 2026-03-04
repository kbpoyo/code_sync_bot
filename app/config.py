import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 企业微信机器人配置
class WeChatConfig:
    # 基本配置
    WEBHOOK_URL = os.getenv("WEBHOOK_URL")
    TOKEN = os.getenv("WECHAT_TOKEN")
    ENCODING_AES_KEY = os.getenv("ENCODING_AES_KEY")
    AGENT_ID = os.getenv("AGENT_ID")
    
    # 服务器配置
    SERVER_HOST = os.getenv("SERVER_HOST", "0.0.0.0")
    SERVER_PORT = int(os.getenv("SERVER_PORT", "8080"))

    GROUP_ID = int(os.getenv("GROUP_ID"))
    
    # 验证配置
    SIGNATURE_TIMEOUT = 60  # 签名超时时间（秒）
    
    @classmethod
    def validate_config(cls):
        """验证配置是否完整"""
        missing = []
        
        if not cls.WEBHOOK_URL:
            missing.append("WEBHOOK_URL")
        if not cls.TOKEN:
            missing.append("WECHAT_TOKEN")
        if not cls.ENCODING_AES_KEY:
            missing.append("ENCODING_AES_KEY")
        if not cls.AGENT_ID:
            missing.append("AGENT_ID")
        
        if missing:
            raise ValueError(f"缺少必要配置项: {', '.join(missing)}")
        
        print("配置验证通过")
        return True

# 消息类型常量
class MessageType:
    TEXT = "TEXT"
    IMAGE = "IMAGE"
    LINK = "LINK"
    COMMAND = "COMMAND"
    AT = "AT"
    MD = "MD"  # Markdown

# 错误码映射
ERROR_MAPPING = {
    -1: "系统错误",
    0: "OK",
    40000: "参数错误",
    40035: "群聊ID不合法",
    40036: "群聊非企业群",
    40040: "参数错误",
    40044: "机器人未被添加到群中",
    40045: "agentId不合法",
    40046: "发送消息频率超限",
    40047: "文件上传失败",
    40060: "body超过9k",
    40061: "text类型文本总长度超过2k",
    40062: "link类型单个链接长度超过1k",
    40063: "image类型图片数量超过1个",
    40064: "header中offlinenotify长度超过1k",
    40065: "header中compatible长度超过1k",
    40066: "image类型图片大小超过1m",
    40067: "markdown类型数量超过1个",
    40068: "markdown内容长度超过2048个字符",
    40069: "message属性格式不正确",
    40071: "at超过50人",
    40200: "机器人发送消息权限已被封禁",
    40201: "机器人接受消息权限已被封禁",
    40300: "机器人已被停用"
}

# 安全等级映射（可配置不同的安全等级）
SECURITY_MAPPING = {
    # 示例：用户ID -> 安全等级
    # 11971123: 3
}