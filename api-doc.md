的# IndexTTS API Documentation

IndexTTS provides a RESTful API for text-to-speech synthesis with advanced emotional control capabilities. This document describes the available endpoints, parameters, and usage examples.

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

All API endpoints are relative to the base URL where the service is hosted:
```
http://localhost:18000
```

The port can be configured when starting the API server.

## Common Parameters

These are the common parameters used across different TTS endpoints:

| Parameter | Type | Description | Default |
|-----------|------|-------------|---------|
| `spk_audio_prompt` | string | Path to speaker audio prompt for voice cloning (required) | N/A |
| `text` | string | Text to synthesize (required) | N/A |
| `emo_audio_prompt` | string | Path to emotional audio prompt (optional) | None |
| `emo_alpha` | float | Emotion blending factor (0.0-1.0) | 1.0 |
| `use_random` | boolean | Enable random sampling | false |
| `use_emo_text` | boolean | Enable text-based emotion control | false |
| `emo_text` | string | Text for emotion control when use_emo_text=true | None |
| `emo_vector` | array/string | Emotion vector (8 floats) | None |

## Endpoints

### Health Check

Check if the API service is running.

```
GET /health
```

**Response:**
```json
{
  "status": "ok"
}
```

### Model Info

Get information about the loaded model.

```
GET /info
```

**Response:**
```json
{
  "model_version": "2.0",
  "model_dir": "./checkpoints"
}
```

### Upload Audio File

Upload an audio file for use as a speaker or emotion reference.

```
POST /upload
Content-Type: multipart/form-data
```

**Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `file` | file | Yes | Audio file to upload (WAV format recommended) |

**Response:**
```json
{
  "filename": "unique_hash.wav",
  "path": "relative/path/to/file.wav"
}
```

Files are automatically deduplicated based on content hash. If the same file is uploaded multiple times, the existing path will be returned.

### List Audio Files

Get a list of uploaded audio files sorted by creation time (newest first).

```
GET /list
```

**Response:**
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

### TTS Synthesis

Synthesize speech using JSON body parameters.

```
POST /tts
Content-Type: application/json
```

**Request Body (application/json):**

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

**Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `spk_audio_prompt` | string | Yes | Path to speaker reference audio (from upload) |
| `text` | string | Yes | Text to synthesize |
| `emo_audio_prompt` | string | No | Path to emotional reference audio (from upload) |
| `emo_alpha` | float | No | Emotion blending factor (0.0-1.0) |
| `use_random` | boolean | No | Enable random sampling |
| `use_emo_text` | boolean | No | Enable text-based emotion control |
| `emo_text` | string | No | Text for emotion control |
| `emo_vector` | array | No | Emotion vector (8 values) |
| `do_sample` | boolean | No | Enable sampling |
| `top_p` | float | No | Nucleus sampling probability |
| `top_k` | integer | No | Top-K sampling |
| `temperature` | float | No | Sampling temperature |
| `length_penalty` | float | No | Length penalty for beam search |
| `num_beams` | integer | No | Number of beams for beam search |
| `repetition_penalty` | float | No | Repetition penalty |
| `max_mel_tokens` | integer | No | Maximum mel tokens |
| `max_text_tokens_per_segment` | integer | No | Maximum text tokens per segment |

**Response:**
Audio file in WAV format

## Usage Examples

### Upload Reference Audio

First, upload your reference audio files:

```bash
# Upload speaker reference
curl -X POST "http://localhost:18000/upload" \
  -H "accept: application/json" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@examples/voice_01.wav"
```

Expected response:
```json
{
  "filename": "abcd1234.wav",
  "path": "abcd1234.wav"
}
```

```bash
# Upload emotion reference
curl -X POST "http://localhost:18000/upload" \
  -H "accept: application/json" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@examples/emo_sad.wav"
```

Expected response:
```json
{
  "filename": "efgh5678.wav",
  "path": "efgh5678.wav"
}
```

### Basic Voice Cloning

Clone a voice using a reference audio sample:

```bash
curl -X POST "http://localhost:18000/tts" \
  -H "accept: application/json" \
  -H "Content-Type: application/json" \
  -d '{
    "spk_audio_prompt": "abcd1234.wav",
    "text": "Hello, this is a cloned voice demonstration."
  }'
```

### Emotion Control with Audio Prompt

Control emotion using a separate emotional reference audio:

```bash
curl -X POST "http://localhost:18000/tts" \
  -H "accept: application/json" \
  -H "Content-Type: application/json" \
  -d '{
    "spk_audio_prompt": "abcd1234.wav",
    "emo_audio_prompt": "efgh5678.wav",
    "emo_alpha": 0.9,
    "text": "This speech has emotional influence from the prompt."
  }'
```

### Emotion Control with Vector

Control emotion using a numerical emotion vector:

```bash
curl -X POST "http://localhost:18000/tts" \
  -H "accept: application/json" \
  -H "Content-Type: application/json" \
  -d '{
    "spk_audio_prompt": "abcd1234.wav",
    "emo_vector": [0, 0, 0.5, 0, 0, 0, 0, 0],
    "text": "This speech expresses sadness as indicated by the emotion vector."
  }'
```

### Text-Based Emotion Control

Control emotion using descriptive text:

```bash
curl -X POST "http://localhost:18000/tts" \
  -H "accept: application/json" \
  -H "Content-Type: application/json" \
  -d '{
    "spk_audio_prompt": "abcd1234.wav",
    "use_emo_text": true,
    "emo_text": "This person is very excited and happy",
    "emo_alpha": 0.6,
    "text": "I am so thrilled about this amazing opportunity!"
  }'
```

### Advanced Synthesis with JSON

Full control over synthesis parameters using JSON:

```bash
curl -X POST "http://localhost:18000/tts" \
  -H "accept: application/json" \
  -H "Content-Type: application/json" \
  -d '{
    "spk_audio_prompt": "abcd1234.wav",
    "text": "Advanced parameter control example",
    "temperature": 0.9,
    "top_p": 0.9,
    "do_sample": true
  }'
```

### Random Sampling

Enable random sampling for more varied outputs:

```bash
curl -X POST "http://localhost:18000/tts" \
  -H "accept: application/json" \
  -H "Content-Type: application/json" \
  -d '{
    "spk_audio_prompt": "abcd1234.wav",
    "use_random": true,
    "temperature": 1.0,
    "text": "This synthesis uses random sampling for variation."
  }'
```

## Error Handling

The API uses standard HTTP status codes:

| Status Code | Description |
|-------------|-------------|
| 200 | Success |
| 400 | Bad Request - Missing required parameters or invalid values |
| 500 | Internal Server Error - Synthesis failed |

Error responses follow this format:
```json
{
  "detail": "Error message describing what went wrong"
}
```