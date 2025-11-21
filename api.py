import os
import sys
import time
import argparse
import tempfile
import uvicorn
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

# TTS 合成端点（需要参考音频）
@app.post("/tts")
async def tts_synthesis(
    spk_audio_prompt: UploadFile = File(...),
    text: str = "",
    emo_audio_prompt: Optional[UploadFile] = File(None),
    emo_alpha: float = 1.0,
    use_random: bool = False,
    use_emo_text: bool = False,
    emo_text: Optional[str] = None,
    emo_vector: Optional[str] = None,  # 以逗号分隔的字符串形式传入
):
    if not text:
        raise HTTPException(status_code=400, detail="Text is required")
    
    # 保存上传的音频文件
    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as spk_tmp:
        spk_tmp.write(await spk_audio_prompt.read())
        spk_audio_path = spk_tmp.name
    
    emo_audio_path = None
    if emo_audio_prompt:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as emo_tmp:
            emo_tmp.write(await emo_audio_prompt.read())
            emo_audio_path = emo_tmp.name
    
    # 处理情感向量
    emo_vec = None
    if emo_vector:
        try:
            emo_vec = [float(x) for x in emo_vector.split(",")]
            if len(emo_vec) != 8:
                raise ValueError("Emotion vector must contain exactly 8 values")
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid emotion vector: {str(e)}")
    
    # 生成输出文件路径
    output_path = os.path.join("outputs", f"tts_{int(time.time())}.wav")
    os.makedirs("outputs", exist_ok=True)
    
    try:
        # 设置参数
        kwargs = {
            "do_sample": True,
            "top_p": 0.8,
            "top_k": 30,
            "temperature": 0.8,
            "length_penalty": 0.0,
            "num_beams": 3,
            "repetition_penalty": 10.0,
            "max_mel_tokens": 1500,
        }
        
        # 调用合成函数
        tts.infer(
            spk_audio_prompt=spk_audio_path,
            text=text,
            output_path=output_path,
            emo_audio_prompt=emo_audio_path,
            emo_alpha=emo_alpha,
            emo_vector=emo_vec,
            use_emo_text=use_emo_text,
            emo_text=emo_text,
            use_random=use_random,
            verbose=True,
            max_text_tokens_per_segment=120,
            **kwargs
        )
        
        # 返回生成的音频文件
        return FileResponse(output_path, media_type="audio/wav", filename="generated.wav")
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"TTS synthesis failed: {str(e)}")
    
    finally:
        # 清理临时文件
        if os.path.exists(spk_audio_path):
            os.unlink(spk_audio_path)
        if emo_audio_path and os.path.exists(emo_audio_path):
            os.unlink(emo_audio_path)

# TTS 合成端点（JSON 请求体）
@app.post("/tts_json")
async def tts_synthesis_json(request: TTSRequest, spk_audio_prompt: UploadFile = File(...)):
    if not request.text:
        raise HTTPException(status_code=400, detail="Text is required")
    
    # 保存上传的音频文件
    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as spk_tmp:
        spk_tmp.write(await spk_audio_prompt.read())
        spk_audio_path = spk_tmp.name
    
    # 生成输出文件路径
    output_path = os.path.join("outputs", f"tts_{int(time.time())}.wav")
    os.makedirs("outputs", exist_ok=True)
    
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
            emo_alpha=request.emo_alpha,
            emo_vector=request.emo_vector,
            use_emo_text=request.use_emo_text,
            emo_text=request.emo_text,
            use_random=request.use_random,
            verbose=True,
            max_text_tokens_per_segment=request.max_text_tokens_per_segment,
            **kwargs
        )
        
        # 返回生成的音频文件
        return FileResponse(output_path, media_type="audio/wav", filename="generated.wav")
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"TTS synthesis failed: {str(e)}")
    
    finally:
        # 清理临时文件
        if os.path.exists(spk_audio_path):
            os.unlink(spk_audio_path)

if __name__ == "__main__":
    uvicorn.run(app, host=args.host, port=args.port)
