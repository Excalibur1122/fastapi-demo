# 使用 Python 3.13 基础镜像（与你的环境匹配）
FROM python:3.13-slim

# 关键步骤：手动安装 PortAudio 和 libsndfile 系统依赖
# 先更新 apt 源，再安装依赖，最后清理缓存减少镜像体积
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        portaudio19-dev \
        libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

# 设置工作目录
WORKDIR /app

# 复制 Python 依赖文件并安装
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制项目所有代码到容器中
COPY . .

# 启动 FastAPI 服务（根据你的入口文件调整，如 main:app）
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]