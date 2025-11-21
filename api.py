import os
import sys
import time
import argparse
import tempfile
import uvicorn
import hashlib
from typing import Optional, List
from pydantic import BaseModel
import numpy as np

from fastapi import FastAPI, HTTPException, File, UploadFile
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware

# 添加项目路径
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)
sys.path.append(os.path.join(current_dir, "indextts"))

# 解析命令行参数
parser = argparse.ArgumentParser(description="IndexTTS API Server")
parser.add_argument("--port", type=int, default=8000, help="Port to run the API server on")
parser.add_argument("--host", type=str, default="0.0.0.0", help="Host to run the API server on")
parser.add_argument("--model_dir", type=str, default="./checkpoints", help="Model checkpoints directory")
parser.add_argument("--fp16", action="store_true", default=False, help="Use FP16 for inference if available")
parser.add_argument("--deepspeed", action="store_true", default=False, help="Use DeepSpeed to accelerate if available")
parser.add_argument("--cuda_kernel", action="store_true", default=False, help="Use CUDA kernel for inference if available")
args = parser.parse_args()

# 检查模型目录
if not os.path.exists(args.model_dir):
    print(f"Model directory {args.model_dir} does not exist. Please download the model first.")
    sys.exit(1)

for file in [
    "bpe.model",
    "gpt.pth",
    "config.yaml",
    "s2mel.pth",
    "wav2vec2bert_stats.pt"
]:
    file_path = os.path.join(args.model_dir, file)
    if not os.path.exists(file_path):
        print(f"Required file {file_path} does not exist. Please download it.")
        sys.exit(1)

# 初始化模型
from indextts.infer_v2 import IndexTTS2

tts = IndexTTS2(
    model_dir=args.model_dir,
    cfg_path=os.path.join(args.model_dir, "config.yaml"),
    use_fp16=args.fp16,
    use_deepspeed=args.deepspeed,
    use_cuda_kernel=args.cuda_kernel,
)

print("TTS models have been loaded")

app = FastAPI(title="IndexTTS API", description="IndexTTS Text-to-Speech API", version="2.0")

# 添加 CORS 支持
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 创建上传目录
UPLOAD_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

# 定义请求模型
class TTSRequest(BaseModel):
    text: str
    emo_alpha: float = 1.0
    use_random: bool = False
    use_emo_text: bool = False
    emo_text: Optional[str] = None
    emo_vector: Optional[List[float]] = None
    do_sample: bool = True
    top_p: float = 0.8
    top_k: int = 30
    temperature: float = 0.8
    length_penalty: float = 0.0
    num_beams: int = 3
    repetition_penalty: float = 10.0
    max_mel_tokens: int = 1500
    max_text_tokens_per_segment: int = 120
    spk_audio_prompt: str
    emo_audio_prompt: Optional[str] = None

# 文件信息模型
class FileInfo(BaseModel):
    filename: str
    path: str
    created_time: float

# 计算文件哈希值
def calculate_file_hash(file_content: bytes) -> str:
    return hashlib.sha256(file_content).hexdigest()

# 健康检查端点
@app.get("/health")
async def health():
    return {"status": "ok"}

# 获取模型信息
@app.get("/info")
async def info():
    return {
        "model_version": tts.model_version or "1.0",
        "model_dir": args.model_dir
    }

# 上传音频文件端点
@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    if not file:
        raise HTTPException(status_code=400, detail="No file provided")
    
    # 读取文件内容
    file_content = await file.read()
    
    # 计算文件哈希值用于去重
    file_hash = calculate_file_hash(file_content)
    
    # 构造文件名和路径
    file_extension = os.path.splitext(file.filename)[1] if file.filename else ".wav"
    unique_filename = f"{file_hash}{file_extension}"
    file_path = os.path.join(UPLOAD_DIR, unique_filename)
    
    # 检查文件是否已经存在
    if os.path.exists(file_path):
        # 文件已存在，直接返回已有路径
        relative_path = os.path.relpath(file_path, UPLOAD_DIR).replace("\\", "/")
        return {"filename": unique_filename, "path": relative_path}
    
    # 保存新文件
    with open(file_path, "wb") as buffer:
        buffer.write(file_content)
    
    # 返回相对路径
    relative_path = os.path.relpath(file_path, UPLOAD_DIR).replace("\\", "/")
    return {"filename": unique_filename, "path": relative_path}

# 列出上传文件端点
@app.get("/list")
async def list_files():
    files = []
    for filename in os.listdir(UPLOAD_DIR):
        file_path = os.path.join(UPLOAD_DIR, filename)
        if os.path.isfile(file_path):
            created_time = os.path.getctime(file_path)
            relative_path = os.path.relpath(file_path, UPLOAD_DIR).replace("\\", "/")
            files.append({
                "filename": filename,
                "path": relative_path,
                "created_time": created_time
            })
    
    # 按创建时间倒序排列
    files.sort(key=lambda x: x["created_time"], reverse=True)
    return files

# 下载上传文件端点
@app.get("/download/{filename}")
async def download_file(filename: str):
    # 防止路径遍历攻击
    if ".." in filename or filename.startswith("/"):
        raise HTTPException(status_code=400, detail="Invalid filename")
    
    # 构造安全的文件路径
    file_path = os.path.join(UPLOAD_DIR, filename)
    
    # 规范化路径并确保它在预期的目录中
    safe_path = os.path.normpath(file_path)
    if not safe_path.startswith(os.path.normpath(UPLOAD_DIR) + os.sep):
        raise HTTPException(status_code=400, detail="Invalid filename")
    
    # 检查文件是否存在
    if not os.path.exists(safe_path):
        raise HTTPException(status_code=404, detail=f"File {filename} not found")
    
    # 检查是否为文件
    if not os.path.isfile(safe_path):
        raise HTTPException(status_code=400, detail=f"{filename} is not a file")
    
    # 检查文件扩展名是否为WAV格式
    if not filename.lower().endswith(".wav"):
        raise HTTPException(status_code=400, detail="Only WAV files can be downloaded")
    
    # 返回文件响应
    return FileResponse(
        path=safe_path,
        media_type="audio/wav",
        filename=filename
    )

# TTS 合成端点（需要参考音频）
@app.post("/tts")
async def tts_synthesis(request: TTSRequest):
    if not request.text:
        raise HTTPException(status_code=400, detail="Text is required")
    
    # 构建完整音频文件路径
    spk_audio_path = os.path.join(UPLOAD_DIR, request.spk_audio_prompt)
    if not os.path.exists(spk_audio_path):
        raise HTTPException(status_code=400, detail=f"Speaker audio file not found: {request.spk_audio_prompt}")
    
    emo_audio_path = None
    if request.emo_audio_prompt:
        emo_audio_path = os.path.join(UPLOAD_DIR, request.emo_audio_prompt)
        if not os.path.exists(emo_audio_path):
            raise HTTPException(status_code=400, detail=f"Emotion audio file not found: {request.emo_audio_prompt}")
    
    # 生成输出文件路径 (在 /app/outputs 目录下)
    outputs_dir = os.path.join("/app", "outputs")
    os.makedirs(outputs_dir, exist_ok=True)
    filename = f"tts_{int(time.time())}.wav"
    output_path = os.path.join(outputs_dir, filename)
    
    try:
        # 设置参数
        kwargs = {
            "do_sample": request.do_sample,
            "top_p": request.top_p,
            "top_k": request.top_k,
            "temperature": request.temperature,
            "length_penalty": request.length_penalty,
            "num_beams": request.num_beams,
            "repetition_penalty": request.repetition_penalty,
            "max_mel_tokens": request.max_mel_tokens,
        }
        
        # 调用合成函数
        tts.infer(
            spk_audio_prompt=spk_audio_path,
            text=request.text,
            output_path=output_path,
            emo_audio_prompt=emo_audio_path,
            emo_alpha=request.emo_alpha,
            emo_vector=request.emo_vector,
            use_emo_text=request.use_emo_text,
            emo_text=request.emo_text,
            use_random=request.use_random,
            verbose=True,
            max_text_tokens_per_segment=request.max_text_tokens_per_segment,
            **kwargs
        )
        
        # 返回生成的音频文件路径
        return {
            "message": "TTS synthesis completed successfully",
            "file_path": f"/app/outputs/{filename}",
            "filename": filename
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"TTS synthesis failed: {str(e)}")

if __name__ == "__main__":
    uvicorn.run(app, host=args.host, port=args.port)