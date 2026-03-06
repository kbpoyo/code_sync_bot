# 企业微信群组机器人 - FastAPI 版本

基于 FastAPI 构建的企业微信群组机器人服务，提供群组消息接收、发送和代码同步检查功能。

## 🚀 功能特性

- ✅ **消息接收**：安全接收企业微信加密消息
- ✅ **消息发送**：通过 Webhook 向群组发送消息
- ✅ **签名验证**：完整的请求签名验证机制
- ✅ **AES加解密**：企业微信标准加密算法
- ✅ **多格式支持**：支持文本、Markdown、链接等多种消息格式
- ✅ **Webhook API**：提供简单易用的消息发送接口
- ✅ **健康检查**：服务状态监控
- ✅ **代码同步检查**：自动检查并报告代码同步状态
- ✅ **定时任务**：内置 APScheduler 调度器，支持每日定时执行
- 📝 **易于扩展**：模块化设计，便于集成 RAG、OCR 等功能

## 📁 项目结构

```
.
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI 主应用
│   ├── config.py            # 配置管理（含日志、定时任务配置）
│   ├── security.py          # 安全验证（签名、AES解密）
│   ├── handlers.py          # 消息处理逻辑
│   ├── webhook.py           # Webhook 消息发送功能
│   ├── command_handler.py   # 命令处理器
│   ├── code_sync_reporter.py # 代码同步报告生成
│   └── run_scheduler.py     # 定时任务调度器
├── code_sync/
│   ├── code_sync.sh         # 代码同步检查脚本
│   ├── commit_diff.py       # 提交差异分析
│   ├── whitelist.yaml       # 白名单配置
│   └── readme.md            # 代码同步模块文档
├── tests/                   # 测试用例
├── run.py                   # 服务启动脚本
├── run_scheduler.sh         # 定时任务启动脚本
├── docker_start.sh          # Docker 容器启动脚本
├── requirements.txt         # Python依赖
├── .env                     # 环境变量配置
└── README.md                # 项目文档
```

## 🔧 快速开始

### 1. 环境准备

```bash
# 克隆项目（如果适用）或解压到本地
# 进入项目目录
cd code_sync_bot

# 安装依赖
pip install -r requirements.txt
```

### 2. 配置企业微信

1. **复制环境配置**
   ```bash
   cp .env
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

## 🕐 定时任务配置

系统内置 APScheduler 调度器，支持每日定时执行代码同步检查，无需依赖系统 cron。

### 环境变量配置

在 `.env` 文件中配置定时任务相关参数：

```ini
# 定时任务配置
SCHEDULE_ENABLED = "true"        # 是否启用定时任务（true/false）
SCHEDULE_SYNC_TIME = "09:00"     # 每日同步检查时间（HH:MM，24小时制）
# SCHEDULE_SYNC_GROUP_ID = ""    # 目标群组ID，默认使用 GROUP_ID

# 定时任务日志配置（独立配置项，其他配置复用全局日志配置）
SCHEDULER_LOG_FILE = "logs/scheduler.log"  # 定时任务专用日志文件
SCHEDULER_LOG_CONSOLE = "true"             # 是否输出到控制台（true/false）
# 以下为可选独立配置，不设置则复用全局日志配置：
# SCHEDULER_LOG_LEVEL = "INFO"
# SCHEDULER_LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
# SCHEDULER_LOG_ROTATION = "10 MB"
# SCHEDULER_LOG_BACKUP_COUNT = "5"
```

### 启动方式

**方式1：单独启动定时任务调度器**
```bash
./run_scheduler.sh
```

**方式2：Docker 容器启动（同时启动 FastAPI 服务和调度器）**
```bash
./docker_start.sh
```

**方式3：Python 模块方式启动**
```bash
python -m app.run_scheduler
```

### 查看执行日志

```bash
# 查看定时任务执行日志
tail -f logs/scheduler.log
```

### 运行特性

- **持久运行**：调度器在后台持续运行，每天在指定时间自动执行
- **容错机制**：`misfire_grace_time=3600` 确保错过执行时间后 1 小时内仍会补执行
- **时区支持**：使用 `Asia/Shanghai` 时区
- **独立日志**：定时任务日志独立输出到 `logs/scheduler.log`

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

## 📄 开源协议

本项目基于 MIT 协议开源。

## 🤝 贡献指南

欢迎提交 Issue 和 Pull Request！

---

**提示**: 在实际部署前，请确保：
1. 服务器端口（8080）对外开放
2. 企业微信后台正确配置
3. 域名或 IP 可访问