#FROM python:3.10-slim
FROM nvidia/cuda:12.1.0-cudnn8-devel-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1

RUN sed -i 's/archive.ubuntu.com/mirrors.tuna.tsinghua.edu.cn/g' /etc/apt/sources.list
RUN sed -i 's/security.ubuntu.com/mirrors.tuna.tsinghua.edu.cn/g' /etc/apt/sources.list

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y python3.10 python3.10-dev python3.10-distutils python3-pip wget curl \
    git \
    git-lfs \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

RUN update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.10 1

RUN pip3 config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple
# 安装 uv 包管理器

ENV UV_LINK_MODE=copy

RUN --mount=type=cache,target=/root/.cache/pip pip3 install -U uv

# 先只复制依赖相关文件，这样只有当依赖变化时才会重新安装
COPY indextts/ ./indextts/
COPY MANIFEST.in README.md LICENSE LICENSE_ZH.txt DISCLAIMER pyproject.toml uv.lock ./

# 安装项目依赖
RUN --mount=type=cache,target=/root/.cache/uv uv sync --locked --index https://mirrors.tuna.tsinghua.edu.cn/pypi/web/simple --all-extras

# 现在复制剩下的项目文件
COPY . .

# 下载大型文件
RUN git lfs pull

# 暴露端口
EXPOSE 8000

# 创建必要的目录
RUN mkdir -p outputs checkpoints uploads prompts

# 启动命令
CMD ["uv", "run", "api.py"]
