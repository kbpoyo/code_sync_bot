import os
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
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
        
        logging.info("配置验证通过")
        return True

# 日志配置
class LogConfig:
    """日志配置类"""
    
    LOG_FILE = os.getenv("LOG_FILE", "logs/app.log")
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    LOG_FORMAT = os.getenv("LOG_FORMAT", "%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    LOG_DATE_FORMAT = os.getenv("LOG_DATE_FORMAT", "%Y-%m-%d %H:%M:%S")
    LOG_ROTATION = os.getenv("LOG_ROTATION", "10 MB")
    LOG_BACKUP_COUNT = int(os.getenv("LOG_BACKUP_COUNT", "5"))
    LOG_ENCODING = os.getenv("LOG_ENCODING", "utf-8")
    LOG_WHEN_CONSOLE = os.getenv("LOG_WHEN_CONSOLE", "False").lower() == "true"
    LOG_CONSOLE_LEVEL = os.getenv("LOG_CONSOLE_LEVEL", "INFO")
    
    @classmethod
    def setup_logging(cls):
        """配置日志系统"""
        # 创建日志目录（如果不存在）
        log_dir = Path(cls.LOG_FILE).parent
        if log_dir != Path("."):
            log_dir.mkdir(parents=True, exist_ok=True)
        
        # 创建根logger
        root_logger = logging.getLogger()
        root_logger.setLevel(cls.LOG_LEVEL.upper())
        
        # 清除已有的handler
        root_logger.handlers.clear()
        
        # 文件处理器（带日志轮转）
        file_handler = RotatingFileHandler(
            cls.LOG_FILE,
            maxBytes=cls._parse_size(cls.LOG_ROTATION),
            backupCount=cls.LOG_BACKUP_COUNT,
            encoding=cls.LOG_ENCODING
        )
        file_handler.setLevel(cls.LOG_LEVEL.upper())
        file_handler.setFormatter(logging.Formatter(
            cls.LOG_FORMAT,
            datefmt=cls.LOG_DATE_FORMAT
        ))
        root_logger.addHandler(file_handler)
        
        # 控制台处理器（如果启用）
        if cls.LOG_WHEN_CONSOLE:
            console_handler = logging.StreamHandler()
            console_handler.setLevel(cls.LOG_CONSOLE_LEVEL.upper())
            console_handler.setFormatter(logging.Formatter(
                cls.LOG_FORMAT,
                datefmt=cls.LOG_DATE_FORMAT
            ))
            root_logger.addHandler(console_handler)
        
        logging.info("日志系统初始化完成")
        logging.info(f"日志文件: {cls.LOG_FILE}")
        logging.info(f"日志级别: {cls.LOG_LEVEL}")
        logging.info(f"控制台输出: {cls.LOG_WHEN_CONSOLE}")
    
    @staticmethod
    def _parse_size(size_str: str) -> int:
        """解析大小字符串为字节数"""
        size_str = size_str.strip().upper()
        if size_str.isdigit():
            return int(size_str)
        
        # 按照单位长度降序排列，优先匹配更长的单位（GB > MB > KB > B）
        units = [
            ('GB', 1024**3),
            ('MB', 1024**2),
            ('KB', 1024),
            ('B', 1)
        ]
        
        for unit, multiplier in units:
            if size_str.endswith(unit):
                number = size_str[:-len(unit)].strip()
                try:
                    return int(float(number)) * multiplier
                except ValueError:
                    raise ValueError(f"无法解析大小值: {number}，请确保是有效的数字")
        
        # 默认返回10MB
        return 10 * 1024 * 1024

# 初始化日志（在模块加载时调用）
LogConfig.setup_logging()

# 定时任务配置
class ScheduleConfig:
    """定时任务调度配置"""
    
    # 是否启用定时任务
    ENABLED = os.getenv("SCHEDULE_ENABLED", "true").lower() == "true"
    
    # 同步检查时间（格式：HH:MM，24小时制）
    SYNC_TIME = os.getenv("SCHEDULE_SYNC_TIME", "11:00")
    
    # 目标群组ID
    SYNC_GROUP_ID = os.getenv("SCHEDULE_SYNC_GROUP_ID", os.getenv("GROUP_ID", ""))
    
    @classmethod
    def validate_sync_time(cls) -> bool:
        """验证同步时间格式是否正确"""
        try:
            if not cls.SYNC_TIME:
                return False
            parts = cls.SYNC_TIME.split(':')
            if len(parts) != 2:
                return False
            hour, minute = int(parts[0]), int(parts[1])
            return 0 <= hour <= 23 and 0 <= minute <= 59
        except (ValueError, AttributeError):
            return False
    
    @classmethod
    def get_config_info(cls) -> dict:
        """获取配置信息"""
        return {
            "enabled": cls.ENABLED,
            "sync_time": cls.SYNC_TIME,
            "sync_group_id": cls.SYNC_GROUP_ID,
            "time_valid": cls.validate_sync_time()
        }


# 定时任务日志配置（独立于主日志配置，未配置时复用全局配置）
class SchedulerLogConfig:
    """定时任务调度器专用日志配置，未单独配置的项复用全局LogConfig"""
    
    # 独立配置项：日志文件路径和控制台开关（必须独立）
    LOG_FILE = os.getenv("SCHEDULER_LOG_FILE", "logs/scheduler.log")
    LOG_CONSOLE = os.getenv("SCHEDULER_LOG_CONSOLE", "true").lower() == "true"
    
    # 可选独立配置，未设置时复用全局LogConfig
    LOG_LEVEL = os.getenv("SCHEDULER_LOG_LEVEL") or LogConfig.LOG_LEVEL
    LOG_FORMAT = os.getenv("SCHEDULER_LOG_FORMAT") or LogConfig.LOG_FORMAT
    LOG_DATE_FORMAT = os.getenv("SCHEDULER_LOG_DATE_FORMAT") or LogConfig.LOG_DATE_FORMAT
    LOG_ROTATION = os.getenv("SCHEDULER_LOG_ROTATION") or LogConfig.LOG_ROTATION
    LOG_BACKUP_COUNT = int(os.getenv("SCHEDULER_LOG_BACKUP_COUNT") or LogConfig.LOG_BACKUP_COUNT)
    LOG_ENCODING = os.getenv("SCHEDULER_LOG_ENCODING") or LogConfig.LOG_ENCODING
    
    @classmethod
    def setup_logging(cls) -> logging.Logger:
        """配置定时任务专用日志系统，返回独立的logger"""
        # 创建日志目录
        log_dir = Path(cls.LOG_FILE).parent
        if log_dir != Path("."):
            log_dir.mkdir(parents=True, exist_ok=True)
        
        # 创建独立的logger（不使用root logger）
        scheduler_logger = logging.getLogger("scheduler")
        scheduler_logger.setLevel(cls.LOG_LEVEL.upper())
        
        # 清除已有的handler，避免重复
        scheduler_logger.handlers.clear()
        
        # 防止日志向上传播到root logger
        scheduler_logger.propagate = False
        
        # 文件处理器（带日志轮转）
        file_handler = RotatingFileHandler(
            cls.LOG_FILE,
            maxBytes=LogConfig._parse_size(cls.LOG_ROTATION),
            backupCount=cls.LOG_BACKUP_COUNT,
            encoding=cls.LOG_ENCODING
        )
        file_handler.setLevel(cls.LOG_LEVEL.upper())
        file_handler.setFormatter(logging.Formatter(
            cls.LOG_FORMAT,
            datefmt=cls.LOG_DATE_FORMAT
        ))
        scheduler_logger.addHandler(file_handler)
        
        # 控制台处理器
        if cls.LOG_CONSOLE:
            console_handler = logging.StreamHandler()
            console_handler.setLevel(cls.LOG_LEVEL.upper())
            console_handler.setFormatter(logging.Formatter(
                cls.LOG_FORMAT,
                datefmt=cls.LOG_DATE_FORMAT
            ))
            scheduler_logger.addHandler(console_handler)
        
        scheduler_logger.info("定时任务日志系统初始化完成")
        scheduler_logger.info(f"日志文件: {cls.LOG_FILE}")
        scheduler_logger.info(f"日志级别: {cls.LOG_LEVEL}")
        scheduler_logger.info(f"控制台输出: {cls.LOG_CONSOLE}")
        
        return scheduler_logger

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