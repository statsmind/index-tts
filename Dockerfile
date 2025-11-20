FROM python:3.10-slim

WORKDIR /app

# 设置环境变量
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    git \
    git-lfs \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# 安装 uv 包管理器
RUN pip install -U uv

# 复制项目文件
COPY . .

# 安装项目依赖
RUN uv sync --all-extras

# 下载大型文件
RUN git lfs pull

# 暴露端口
EXPOSE 8000 7860

# 创建必要的目录
RUN mkdir -p outputs checkpoints

# 启动命令
CMD ["uv", "run", "api.py"]