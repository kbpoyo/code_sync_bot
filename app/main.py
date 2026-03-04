from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse, PlainTextResponse
import json
import logging
from typing import Dict, Any

from app.config import WeChatConfig
from app.security import SecurityManager
from app.handlers import MessageHandler
from app.webhook import webhook_sender

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 创建FastAPI应用
app = FastAPI(
    title="企业微信机器人API",
    description="企业微信群组机器人基础消息接收和发送服务",
    version="1.0.0"
)

# 启动时验证配置
@app.on_event("startup")
async def startup_event():
    try:
        WeChatConfig.validate_config()
        logger.info(f"机器人服务启动成功，监听 {WeChatConfig.SERVER_HOST}:{WeChatConfig.SERVER_PORT}")
        logger.info(f"机器人Agent ID: {WeChatConfig.AGENT_ID}")
    except ValueError as e:
        logger.error(f"配置验证失败: {e}")
        raise RuntimeError(f"配置验证失败: {e}")

# 健康检查端点
@app.get("/")
async def root():
    return {
        "status": "running",
        "service": "WeChat Group Robot",
        "version": "1.0.0",
        "agent_id": WeChatConfig.AGENT_ID
    }

# 健康检查端点
@app.get("/health")
async def health_check():
    return {"status": "healthy"}

# 验证回调URL（GET请求）
@app.get("/callback")
async def callback_verification(request: Request):
    """
    处理企业微信的URL验证请求
    企业微信在配置回调URL时会发送GET请求验证
    """
    try:
        # 获取查询参数
        params = dict(request.query_params)
        
        # 提取验证参数
        signature, timestamp, nonce, echostr = SecurityManager.extract_verification_params(params)
        
        # 验证签名
        if not SecurityManager.verify_signature(signature, timestamp, nonce, WeChatConfig.TOKEN):
            logger.warning(f"签名验证失败: signature={signature}")
            raise HTTPException(status_code=403, detail="Invalid signature")
        
        # 返回echostr完成验证
        logger.info(f"URL验证成功: echostr={echostr[:20]}...")
        return PlainTextResponse(content=echostr)
        
    except Exception as e:
        logger.error(f"验证回调URL时出错: {e}")
        raise HTTPException(status_code=400, detail=str(e))

# 消息接收端点（POST请求）
@app.post("/callback")
async def receive_message(request: Request):
    """
    接收企业微信的加密消息
    支持两种消息格式：JSON和加密二进制
    """
    try:
        # 获取请求内容
        content_type = request.headers.get("Content-Type", "")
        body_bytes = await request.body()
        
        # 检查是否是验证请求
        if content_type == "application/x-www-form-urlencoded":
            # 尝试解析为字符串
            body_str = body_bytes.decode('utf-8')
            import urllib.parse
            form_data = urllib.parse.parse_qs(body_str)
            
            # 检查是否包含验证参数
            if all(key in form_data for key in ['signature', 'timestamp', 'nonce', 'echostr']):
                signature = form_data['signature'][0]
                timestamp = form_data['timestamp'][0]
                nonce = form_data['nonce'][0]
                echostr = form_data['echostr'][0]
                
                if SecurityManager.verify_signature(signature, timestamp, nonce, WeChatConfig.TOKEN):
                    logger.info("POST方式URL验证成功")
                    return PlainTextResponse(content=echostr)
                else:
                    raise HTTPException(status_code=403, detail="Invalid signature")
        
        # 处理消息接收
        message_data = None
        
        if content_type == "application/json":
            # JSON格式消息
            try:
                message_data = json.loads(body_bytes.decode('utf-8'))
                logger.info(f"收到JSON格式消息: {json.dumps(message_data, ensure_ascii=False)[:200]}...")
            except json.JSONDecodeError:
                # 如果JSON解析失败，可能是加密的
                pass
        
        # 如果是加密消息，先解密
        if not message_data:
            try:
                encrypted_data = body_bytes.decode('utf-8')
                message_data = SecurityManager.decrypt_message(encrypted_data, WeChatConfig.ENCODING_AES_KEY)
                logger.info(f"解密后消息: {json.dumps(message_data, ensure_ascii=False)[:200]}...")
            except Exception as e:
                logger.error(f"消息解密失败: {e}")
                raise HTTPException(status_code=400, detail=f"消息解密失败: {e}")
        
        # 处理消息
        result = MessageHandler.process_message_event(message_data)
        
        if result.get("processed", True):
            return JSONResponse(content={"status": "success", "detail": "消息处理完成"})
        else:
            logger.warning(f"消息未处理: {result.get('reason', '未知原因')}")
            return JSONResponse(content={"status": "ignored", "detail": result.get('reason', '消息未处理')})
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"处理消息请求时出错: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"服务器内部错误: {e}")

# 测试消息发送端点
@app.post("/api/send_test_message")
async def send_test_message(request: Request):
    """
    测试消息发送功能
    需要JSON格式的请求体: {"group_id": "群组ID", "message": "测试消息"}
    """
    try:
        data = await request.json()
        group_id = data.get("group_id")
        message = data.get("message", "这是一条测试消息")
        
        if not group_id:
            raise HTTPException(status_code=400, detail="缺少group_id参数")
        
        # 发送测试消息
        result = webhook_sender.send_text_message(
            group_id=group_id,
            content=message,
            at_users=[]
        )
        
        return JSONResponse(content={
            "request": data,
            "result": result
        })
        
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="无效的JSON格式")
    except Exception as e:
        logger.error(f"发送测试消息失败: {e}")
        raise HTTPException(status_code=500, detail=f"发送消息失败: {e}")

# 获取服务状态
@app.get("/api/status")
async def get_status():
    """
    获取机器人服务状态
    """
    return {
        "status": "running",
        "config": {
            "agent_id": WeChatConfig.AGENT_ID,
            "server_host": WeChatConfig.SERVER_HOST,
            "server_port": WeChatConfig.SERVER_PORT
        },
        "endpoints": {
            "verification": "/callback (GET)",
            "message_receive": "/callback (POST)",
            "health_check": "/health",
            "send_test": "/api/send_test_message (POST)",
            "status": "/api/status (GET)"
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=WeChatConfig.SERVER_HOST,
        port=WeChatConfig.SERVER_PORT,
        reload=True
    )