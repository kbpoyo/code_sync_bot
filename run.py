#!/usr/bin/env python3
"""
群组机器人服务启动脚本
"""

import subprocess
import sys
import os

def start_service():
    """启动FastAPI服务"""
    print("🚀 启动企业微信群组机器人服务...")
    
    # 检查是否配置了环境变量
    if not os.path.exists('.env'):
        print("⚠️  警告：未找到 .env 文件，请根据 .env.example 创建配置文件")
        print("   使用示例命令：cp .env.example .env && nano .env")
    
    try:
        # 启动服务
        import uvicorn
        from app.config import WeChatConfig
        
        print(f"📡 服务地址: http://{WeChatConfig.SERVER_HOST}:{WeChatConfig.SERVER_PORT}")
        print(f"🤖 机器人ID: {WeChatConfig.AGENT_ID}")
        print("📝 可用端点:")
        print("   验证回调 - GET  http://0.0.0.0:8080/callback")
        print("   接收消息 - POST http://0.0.0.0:8080/callback")
        print("   健康检查 - GET  http://0.0.0.0:8080/health")
        print("   发送测试 - POST http://0.0.0.0:8080/api/send_test_message")
        print("\n🔧 按 Ctrl+C 停止服务")
        print("=" * 50)
        
        uvicorn.run(
            "app.main:app",
            host=WeChatConfig.SERVER_HOST,
            port=WeChatConfig.SERVER_PORT,
            reload=True,
            log_level="info"
        )
        
    except ImportError as e:
        print(f"❌ 缺少依赖: {e}")
        print("请先安装依赖：pip install -r requirements.txt")
        sys.exit(1)
    except ValueError as e:
        print(f"❌ 配置错误: {e}")
        print("请检查 .env 文件是否正确配置")
        sys.exit(1)
    except Exception as e:
        print(f"❌ 启动失败: {e}")
        sys.exit(1)

if __name__ == "__main__":
    start_service()