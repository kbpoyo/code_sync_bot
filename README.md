# 企业微信群组机器人 - FastAPI 版本

基于 FastAPI 构建的企业微信群组机器人服务，提供基础的群组消息接收和发送功能。

## 🚀 功能特性

- ✅ **消息接收**：安全接收企业微信加密消息
- ✅ **消息发送**：通过 Webhook 向群组发送消息
- ✅ **签名验证**：完整的请求签名验证机制
- ✅ **AES加解密**：企业微信标准加密算法
- ✅ **多格式支持**：支持文本、Markdown、链接等多种消息格式
- ✅ **Webhook API**：提供简单易用的消息发送接口
- ✅ **健康检查**：服务状态监控
- 📝 **易于扩展**：模块化设计，便于集成 RAG、OCR 等功能

## 📁 项目结构

```
.
├── app/
│   ├── __init__.py
│   ├── main.py           # FastAPI 主应用
│   ├── config.py         # 配置管理
│   ├── security.py       # 安全验证（签名、AES解密）
│   ├── handlers.py       # 消息处理逻辑
│   └── webhook.py        # Webhook 消息发送功能
├── run.py               # 服务启动脚本
├── requirements.txt     # Python依赖
├── .env.example        # 环境变量示例
└── README.md          # 项目文档
```

## 🔧 快速开始

### 1. 环境准备

```bash
# 克隆项目（如果适用）或解压到本地
# 进入项目目录
cd fastapi-wechat-robot

# 创建虚拟环境（推荐）
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或 venv\Scripts\activate  # Windows

# 安装依赖
pip install -r requirements.txt
```

### 2. 配置企业微信

1. **复制环境配置**
   ```bash
   cp .env.example .env
   ```

2. **编辑 `.env` 文件**，填入企业微信配置：
   ```ini
   # 企业微信机器人配置
   WECHAT_TOKEN=your_wechat_token_here
   ENCODING_AES_KEY=your_encoding_aes_key_here
   AGENT_ID=your_agent_id_here
   
   # Webhook配置
   WEBHOOK_URL=https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=YOUR_KEY
   
   # 服务器配置
   SERVER_HOST=0.0.0.0
   SERVER_PORT=8080
   ```

### 3. 启动服务

```bash
# 方法1：直接运行启动脚本
python run.py

# 方法2：使用uvicorn直接启动
uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload
```

服务启动后，控制台会显示服务信息：

```
🚀 启动企业微信群组机器人服务...
📡 服务地址: http://0.0.0.0:8080
🤖 机器人ID: your_agent_id
?? 可用端点:
   验证回调 - GET  http://0.0.0.0:8080/callback
   接收消息 - POST http://0.0.0.0:8080/callback
   健康检查 - GET  http://0.0.0.0:8080/health
   发送测试 - POST http://0.0.0.0:8080/api/send_test_message
```

## 🔗 企业微信配置

### 配置回调URL

在企业微信管理后台配置机器人回调URL：

```
URL: http://你的服务器IP:8080/callback
Token: 与 .env 中的 WECHAT_TOKEN 一致
EncodingAESKey: 与 .env 中的 ENCODING_AES_KEY 一致
```

### 验证流程

1. 企业微信发送 GET 请求：`/callback?signature=xxx&timestamp=xxx&nonce=xxx&echostr=xxx`
2. 服务验证签名后返回 `echostr`
3. 企业微信确认配置成功

## 📚 API 文档

### 1. 消息接收端点

- **URL**: `POST /callback`
- **Content-Type**: `application/json` 或加密消息
- **功能**: 接收企业微信加密消息，自动解密并回复

### 2. 发送测试消息

- **URL**: `POST /api/send_test_message`
- **Content-Type**: `application/json`
- **请求体**:
  ```json
  {
    "group_id": "群组ID",
    "message": "测试消息内容"
  }
  ```
- **响应**:
  ```json
  {
    "request": { ... },
    "result": {
      "success": true,
      "errcode": 0,
      "error_msg": "OK"
    }
  }
  ```

### 3. 服务状态检查

- **URL**: `GET /health` 或 `GET /`
- **响应**: `{"status": "healthy"}`

### 4. 详细状态查看

- **URL**: `GET /api/status`
- **响应**: 包含完整服务状态和端点信息

## 🛠 高级使用

### 自定义消息处理

编辑 `app/handlers.py` 中的 `generate_basic_response` 方法来自定义回复逻辑：

```python
def generate_basic_response(parsed_content, group_id, user_id):
    # 在此添加自定义逻辑
    if "帮助" in parsed_content["full_text"]:
        body = [{
            "type": "TEXT",
            "content": "这是帮助信息..."
        }]
    # ...
```

### 添加新的消息类型

在 `app/webhook.py` 中添加新的发送方法：

```python
def send_custom_message(self, group_id, custom_data):
    """发送自定义格式消息"""
    message_body = [
        {"type": "TEXT", "content": custom_data["title"]},
        # 添加更多消息部件
    ]
    return self._send_message(group_id, message_body)
```

## 🔒 安全说明

- **签名验证**: 所有请求都经过签名验证，防止伪造
- **时间戳检查**: 防止重放攻击（60秒有效窗口）
- **AES加密**: 消息传输全程加密
- **环境变量**: 敏感信息存储在 `.env` 文件中

## 🐛 故障排除

### 常见问题

1. **配置验证失败**
   - 检查 `.env` 文件是否存在
   - 检查企业微信配置是否正确

2. **签名验证失败**
   - 确认 Token 配置一致
   - 检查服务器时间是否正确

3. **消息解密失败**
   - 确认 EncodingAESKey 正确
   - 检查加密模式设置

### 调试模式

启动时设置日志级别为 DEBUG：
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8080 --log-level debug
```

## 📈 后续扩展建议

本项目为基础版本，可扩展的功能包括：

1. **RAG集成** - 在 `handlers.py` 中添加智能问答功能
2. **OCR处理** - 添加图片识别模块
3. **数据库连接** - 添加对话历史存储
4. **用户认证** - 添加多租户支持
5. **消息队列** - 支持异步处理大量消息
6. **监控告警** - 添加服务监控和告警机制

## 📄 开源协议

本项目基于 MIT 协议开源。

## 🤝 贡献指南

欢迎提交 Issue 和 Pull Request！

---

**提示**: 在实际部署前，请确保：
1. 服务器端口（8080）对外开放
2. 企业微信后台正确配置
3. 域名或 IP 可访问