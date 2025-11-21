# IndexTTS API Documentation

IndexTTS 提供了 RESTful API 来实现具有高级情感控制功能的文本转语音服务。本文档描述了可用的端点、参数和使用示例。

docker 容器使用 18000 映射到 8000 端口


## Table of Contents

- [Base URL](#base-url)
- [Common Parameters](#common-parameters)
- [Endpoints](#endpoints)
  - [Health Check](#health-check)
  - [Model Info](#model-info)
  - [Upload Audio File](#upload-audio-file)
  - [List Audio Files](#list-audio-files)
  - [Download Audio File](#download-audio-file)
  - [TTS Synthesis](#tts-synthesis)
- [Usage Examples](#usage-examples)
  - [Upload Reference Audio](#upload-reference-audio)
  - [Basic Voice Cloning](#basic-voice-cloning)
  - [Emotion Control with Audio Prompt](#emotion-control-with-audio-prompt)
  - [Emotion Control with Vector](#emotion-control-with-vector)
  - [Text-Based Emotion Control](#text-based-emotion-control)
- [Error Handling](#error-handling)

## Base URL

所有 API 端点都是相对于服务托管的基本 URL：

```
http://localhost:18000
```

启动 API 服务器时可以配置端口。

## Common Parameters

这些是跨不同 TTS 端点使用的通用参数：

| 参数 | 类型 | 描述 | 默认值 |
|-----------|------|-------------|---------|
| `spk_audio_prompt` | 字符串 | 用于语音克隆的说话人音频提示（必填） | N/A |
| `text` | 字符串 | 要合成的文本（必填） | N/A |
| `emo_audio_prompt` | 字符串 | 情感音频提示（可选） | None |
| `emo_alpha` | 浮点数 | 情感混合因子（0.0-1.0） | 1.0 |
| `use_random` | 布尔值 | 启用随机采样 | false |
| `use_emo_text` | 布尔值 | 启用基于文本的情感控制 | false |
| `emo_text` | 字符串 | 当 use_emo_text=true 时用于情感控制的文本 | None |
| `emo_vector` | 数组/字符串 | 情感向量（8个浮点数） | None |

## Endpoints

### Health Check

检查 API 服务是否正在运行。

```
GET /health
```

**响应:**
```json
{
  "status": "ok"
}
```

### Model Info

获取加载模型的信息。

```
GET /info
```

**响应:**
```json
{
  "model_version": "2.0",
  "model_dir": "./checkpoints"
}
```

### Upload Audio File

上传一个音频文件作为说话人或情感参考。

```
POST /upload
Content-Type: multipart/form-data
```

**参数:**

| 参数 | 类型 | 必填 | 描述 |
|-----------|------|----------|-------------|
| `file` | 文件 | 是 | 要上传的音频文件（推荐 WAV 格式） |

**响应:**
```json
{
  "filename": "unique_hash.wav",
  "path": "relative/path/to/file.wav"
}
```

文件会根据内容哈希自动去重。如果多次上传相同文件，将返回现有路径。

### List Audio Files

获取按创建时间排序（最新的优先）的已上传音频文件列表。

```
GET /list
```

**响应:**
```json
[
  {
    "filename": "unique_hash.wav",
    "path": "relative/path/to/file.wav",
    "created_time": 1234567890.123
  },
  ...
]
```

### Download Audio File

下载指定的音频文件。

```
GET /download/{filename}
```

**路径参数:**

| 参数名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| `filename` | string | 是 | 要下载的音频文件名 |

**响应:**
成功时返回音频文件（WAV格式）

**错误响应:**
- 400: 文件名无效或不是WAV文件
- 404: 文件不存在

**使用示例:**

使用 curl 下载音频文件:
```bash
curl -X GET "http://localhost:18000/download/sample.wav" \
  -o downloaded_sample.wav
```

使用 Python requests 下载音频文件:
```python
import requests

response = requests.get("http://localhost:18000/download/sample.wav")
if response.status_code == 200:
    with open("downloaded_sample.wav", "wb") as f:
        f.write(response.content)
    print("文件下载成功")
else:
    print(f"下载失败: {response.status_code} - {response.text}")
```

### TTS Synthesis

使用 JSON 正文参数合成语音。

```
POST /tts
Content-Type: application/json
```

**请求正文 (application/json):**

```json
{
  "text": "string",
  "spk_audio_prompt": "string",
  "emo_audio_prompt": "string",
  "emo_alpha": 1.0,
  "use_random": false,
  "use_emo_text": false,
  "emo_text": "string",
  "emo_vector": [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
  "do_sample": true,
  "top_p": 0.8,
  "top_k": 30,
  "temperature": 0.8,
  "length_penalty": 0.0,
  "num_beams": 3,
  "repetition_penalty": 10.0,
  "max_mel_tokens": 1500,
  "max_text_tokens_per_segment": 120
}
```

**参数:**

| 参数 | 类型 | 必填 | 描述 |
|-----------|------|----------|-------------|
| `spk_audio_prompt` | 字符串 | 是 | 说话人参考音频路径（来自上传） |
| `text` | 字符串 | 是 | 要合成的文本 |
| `emo_audio_prompt` | 字符串 | 否 | 情感参考音频路径（来自上传） |
| `emo_alpha` | 浮点数 | 否 | 情感混合因子（0.0-1.0） |
| `use_random` | 布尔值 | 否 | 启用随机采样 |
| `use_emo_text` | 布尔值 | 否 | 启用基于文本的情感控制 |
| `emo_text` | 字符串 | 否 | 用于情感控制的文本 |
| `emo_vector` | 数组 | 否 | 情感向量（8个值） |
| `do_sample` | 布尔值 | 否 | 启用采样 |
| `top_p` | 浮点数 | 否 | 核采样概率 |
| `top_k` | 整数 | 否 | Top-K 采样 |
| `temperature` | 浮点数 | 否 | 采样温度 |
| `length_penalty` | 浮点数 | 否 | 波束搜索长度惩罚 |
| `num_beams` | 整数 | 否 | 波束搜索数量 |
| `repetition_penalty` | 浮点数 | 否 | 重复惩罚 |
| `max_mel_tokens` | 整数 | 否 | 最大 mel 标记数 |
| `max_text_tokens_per_segment` | 整数 | 否 | 每段最大文本标记数 |

**响应:**
```json
{
  "message": "TTS synthesis completed successfully",
  "file_path": "/app/outputs/tts_timestamp.wav",
  "filename": "tts_timestamp.wav"
}
```

## Usage Examples

### Upload Reference Audio

首先，上传您的参考音频文件：

```bash
# 上传说话人参考
curl -X POST "http://localhost:18000/upload" \
  -H "accept: application/json" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@examples/voice_01.wav"
```

预期响应：
```json
{
  "filename": "abcd1234.wav",
  "path": "abcd1234.wav"
}
```

```bash
# 上传情感参考
curl -X POST "http://localhost:18000/upload" \
  -H "accept: application/json" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@examples/emo_sad.wav"
```

预期响应：
```json
{
  "filename": "efgh5678.wav",
  "path": "efgh5678.wav"
}
```

### Basic Voice Cloning

使用参考音频样本克隆声音：

```bash
curl -X POST "http://localhost:18000/tts" \
  -H "accept: application/json" \
  -H "Content-Type: application/json" \
  -d '{
    "spk_audio_prompt": "abcd1234.wav",
    "text": "你好，这是一个克隆声音的演示。"
  }'
```

### Emotion Control with Audio Prompt

使用单独的情感参考音频控制情感：

```bash
curl -X POST "http://localhost:18000/tts" \
  -H "accept: application/json" \
  -H "Content-Type: application/json" \
  -d '{
    "spk_audio_prompt": "abcd1234.wav",
    "emo_audio_prompt": "efgh5678.wav",
    "emo_alpha": 0.9,
    "text": "这个语音受到了提示中情感的影响。"
  }'
```

### Emotion Control with Vector

使用数值情感向量控制情感：

```bash
curl -X POST "http://localhost:18000/tts" \
  -H "accept: application/json" \
  -H "Content-Type: application/json" \
  -d '{
    "spk_audio_prompt": "abcd1234.wav",
    "emo_vector": [0, 0, 0.5, 0, 0, 0, 0, 0],
    "text": "这个语音表达了悲伤情绪，这是由情感向量指示的。"
  }'
```

### Text-Based Emotion Control

使用描述性文本控制情感：

```bash
curl -X POST "http://localhost:18000/tts" \
  -H "accept: application/json" \
  -H "Content-Type: application/json" \
  -d '{
    "spk_audio_prompt": "abcd1234.wav",
    "use_emo_text": true,
    "emo_text": "这个人非常兴奋和快乐",
    "emo_alpha": 0.6,
    "text": "我对这个绝佳的机会感到非常激动！"
  }'
```

### Advanced Synthesis with JSON

使用 JSON 完全控制合成参数：

```bash
curl -X POST "http://localhost:18000/tts" \
  -H "accept: application/json" \
  -H "Content-Type: application/json" \
  -d '{
    "spk_audio_prompt": "abcd1234.wav",
    "text": "高级参数控制示例",
    "temperature": 0.9,
    "top_p": 0.9,
    "do_sample": true
  }'
```

### Random Sampling

启用随机采样以获得更多样化的输出：

```bash
curl -X POST "http://localhost:18000/tts" \
  -H "accept: application/json" \
  -H "Content-Type: application/json" \
  -d '{
    "spk_audio_prompt": "abcd1234.wav",
    "use_random": true,
    "temperature": 1.0,
    "text": "此合成使用随机采样来产生变化。"
  }'
```

## Error Handling

API 使用标准 HTTP 状态码：

| 状态码 | 描述 |
|-------------|-------------|
| 200 | 成功 |
| 400 | 错误请求 - 缺少必要参数或值无效 |
| 500 | 内部服务器错误 - 合成失败 |

错误响应遵循以下格式：
```json
{
  "detail": "描述出错原因的错误消息"
}
```