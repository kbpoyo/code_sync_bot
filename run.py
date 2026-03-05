#!/usr/bin/env python3
"""
群组机器人服务启动脚本
"""

import subprocess
import sys
import os
import logging

# 获取logger
logger = logging.getLogger(__name__)

def start_service():
    """启动FastAPI服务"""
    logger.info("🚀 启动企业微信群组机器人服务...")
    # 检查是否配置了环境变量
    if not os.path.exists('.env'):
        warning_msg = "⚠️  警告：未找到 .env 文件，请根据 .env.example 创建配置文件\n   使用示例命令：cp .env.example .env && nano .env"
        logger.warning(warning_msg)
    
    try:
        # 启动服务
        import uvicorn
        from app.config import WeChatConfig
        
        info_msg = (
            f"📡 服务地址: http://{WeChatConfig.SERVER_HOST}:{WeChatConfig.SERVER_PORT}\n"
            f"🤖 机器人ID: {WeChatConfig.AGENT_ID}\n"
            "📝 可用端点:\n"
            "   验证回调 - GET  http://0.0.0.0:8080/callback\n"
            "   接收消息 - POST http://0.0.0.0:8080/callback\n"
            "   健康检查 - GET  http://0.0.0.0:8080/health\n"
            "   发送测试 - POST http://0.0.0.0:8080/api/send_test_message\n"
            "\n🔧 按 Ctrl+C 停止服务\n"
            "=" * 50
        )
        logger.info(info_msg)
        
        uvicorn.run(
            "app.main:app",
            host=WeChatConfig.SERVER_HOST,
            port=WeChatConfig.SERVER_PORT,
            reload=True,
            log_level="info"
        )
        
    except ImportError as e:
        error_msg = f"❌ 缺少依赖: {e}\n请先安装依赖：pip install -r requirements.txt"
        logger.error(error_msg)
        sys.exit(1)
    except ValueError as e:
        error_msg = f"❌ 配置错误: {e}\n请检查 .env 文件是否正确配置"
        logger.error(error_msg)
        sys.exit(1)
    except Exception as e:
        error_msg = f"❌ 启动失败: {e}"
        logger.error(error_msg, exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    start_service()