#FROM python:3.10-slim
FROM nvidia/cuda:12.1.0-cudnn8-devel-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1

RUN sed -i 's/archive.ubuntu.com/mirrors.tuna.tsinghua.edu.cn/g' /etc/apt/sources.list
RUN sed -i 's/security.ubuntu.com/mirrors.tuna.tsinghua.edu.cn/g' /etc/apt/sources.list

#RUN sed -i 's/deb.debian.org/mirrors.ustc.edu.cn/g' /etc/apt/sources.list.d/debian.sources
#RUN sed -i 's/security.debian.org/mirrors.ustc.edu.cn/g' /etc/apt/sources.list.d/debian.sources


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
RUN --mount=type=cache,target=/root/.cache/pip pip3 install -U uv

# 复制项目文件
COPY . .

# 安装项目依赖
RUN --mount=type=cache,target=/root/.cache/pip uv sync --index https://mirrors.tuna.tsinghua.edu.cn/pypi/web/simple --all-extras

# 下载大型文件
RUN git lfs pull

# 暴露端口
EXPOSE 8000 7860

# 创建必要的目录
RUN mkdir -p outputs checkpoints

# 启动命令
CMD ["uv", "run", "api.py"]
