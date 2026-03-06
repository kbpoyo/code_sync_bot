# 企业微信群组机器人 Docker 镜像
# 基于 Python 3.10

FROM docker.xuanyuan.me/python:3.10-slim-bullseye

# 设置环境变量
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    TZ=Asia/Shanghai

# 设置工作目录
WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    bash \
    tzdata \
    && rm -rf /var/lib/apt/lists/* \
    && ln -snf /usr/share/zoneinfo/$TZ /etc/localtime \
    && echo $TZ > /etc/timezone

# 复制依赖文件并安装 Python 依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制项目文件
COPY . .

# 创建日志目录
RUN mkdir -p logs

# 设置脚本执行权限
RUN chmod +x docker_start.sh run_scheduler.sh \
    && chmod +x code_sync/code_sync.sh 2>/dev/null || true

# 启动命令
CMD ["./docker_start.sh"]