# Qwen3-Omni Official Documentation

## Overview

Qwen3-Omni is the natively end-to-end multilingual omni-modal foundation models. It processes text, images, audio, and video, and delivers in both text and natural speech.

### real-time streaming responses Key Features

- **State-of-the-art across modalities**: Early text-first pretraining and mixed multimodal training provide native multimodal support. While achieving strong audio and audio-video results, unimodal text and image performance does not regress. Reaches SOTA on 22 of 36 audio/video benchmarks and open-source SOTA on 32 of 36.

- **Multilingual**: Supports 119 text languages, 19 speech input languages, and 10 speech output languages.
  - **Speech Input**: English, Chinese, Korean, Japanese, German, Russian, Italian, French, Spanish, Portuguese, Malay, Dutch, Indonesian, Turkish, Vietnamese, Cantonese, Arabic, Urdu.
  - **Speech Output**: English, Chinese, French, German, Russian, Italian, Spanish, Portuguese, Japanese, Korean.

- **Novel Architecture**: MoE-based Thinker-Talker design with AuT pretraining for strong general representations, plus a multi-codebook design that drives latency to a minimum.

- **Real-time Audio/Video Interaction**: Low-latency streaming with natural turn-taking and immediate text or speech responses.

- **Flexible Control**: Customize behavior via system prompts for fine-grained control and easy adaptation.

### Model Architecture

Qwen3-Omni uses a Thinker-Talker architecture:
- **Thinker**: Responsible for understanding and reasoning across all modalities
- **Talker**: Responsible for generating natural speech output

## Model Variants

| Model Name | Description |
|------------|-------------|
| Qwen3-Omni-30B-A3B-Instruct | The Instruct model of Qwen3-Omni-30B-A3B, containing both thinker and talker, supporting audio, video, and text input, with audio and text output. |
| Qwen3-Omni-30B-A3B-Thinking | The Thinking model of Qwen3-Omni-30B-A3B, containing the thinker component, equipped with chain-of-thought reasoning, supporting audio, video, and text input, with text output. |
| Qwen3-Omni-30B-A3B-Captioner | A downstream audio fine-grained caption model fine-tuned from Qwen3-Omni-30B-A3B-Instruct, which produces detailed, low-hallucination captions for arbitrary audio inputs. |

## QuickStart

### Model Download

```bash
# Download through ModelScope (recommended for users in Mainland China)
pip install -U modelscope
modelscope download --model Qwen/Qwen3-Omni-30B-A3B-Instruct --local_dir ./Qwen3-Omni-30B-A3B-Instruct
modelscope download --model Qwen/Qwen3-Omni-30B-A3B-Thinking --local_dir ./Qwen3-Omni-30B-A3B-Thinking
modelscope download --model Qwen/Qwen3-Omni-30B-A3B-Captioner --local_dir ./Qwen3-Omni-30B-A3B-Captioner

# Download through Hugging Face
pip install -U "huggingface_hub[cli]"
huggingface-cli download Qwen/Qwen3-Omni-30B-A3B-Instruct --local-dir ./Qwen3-Omni-30B-A3B-Instruct
huggingface-cli download Qwen/Qwen3-Omni-30B-A3B-Thinking --local-dir ./Qwen3-Omni-30B-A3B-Thinking
huggingface-cli download Qwen/Qwen3-Omni-30B-A3B-Captioner --local-dir ./Qwen3-Omni-30B-A3B-Captioner
```

### Transformers Usage

#### Installation

```bash
# Install transformers from source
pip install git+https://github.com/huggingface/transformers
pip install accelerate

# Install qwen-omni-utils for convenient multimodal input handling
pip install qwen-omni-utils -U

# Install FlashAttention 2 (optional, but recommended for memory efficiency)
pip install -U flash-attn --no-build-isolation
```

#### Basic Code Example

```python
import soundfile as sf

from transformers import Qwen3OmniMoeForConditionalGeneration, Qwen3OmniMoeProcessor
from qwen_omni_utils import process_mm_info

MODEL_PATH = "Qwen/Qwen3-Omni-30B-A3B-Instruct"
# MODEL_PATH = "Qwen/Qwen3-Omni-30B-A3B-Thinking"

model = Qwen3OmniMoeForConditionalGeneration.from_pretrained(
    MODEL_PATH,
    dtype="auto",
    device_map="auto",
    attn_implementation="flash_attention_2",
)

processor = Qwen3OmniMoeProcessor.from_pretrained(MODEL_PATH)

conversation = [
    {
        "role": "user",
        "content": [
            {"type": "image", "image": "https://qianwen-res.oss-cn-beijing.aliyuncs.com/Qwen3-Omni/demo/cars.jpg"},
            {"type": "audio", "audio": "https://qianwen-res.oss-cn-beijing.aliyuncs.com/Qwen3-Omni/demo/cough.wav"},
            {"type": "text", "text": "What can you see and hear? Answer in one short sentence."}
        ],
    },
]

# Set whether to use audio in video
USE_AUDIO_IN_VIDEO = True

# Preparation for inference
text = processor.apply_chat_template(conversation, add_generation_prompt=True, tokenize=False)
audios, images, videos = process_mm_info(conversation, use_audio_in_video=USE_AUDIO_IN_VIDEO)
inputs = processor(text=text, 
    audio=audios, 
    images=images, 
    videos=videos, 
    return_tensors="pt", 
    padding=True, 
    use_audio_in_video=USE_AUDIO_IN_VIDEO)
inputs = inputs.to(model.device).to(model.dtype)

# Inference: Generation of the output text and audio
text_ids, audio = model.generate(**inputs, 
    speaker="Ethan", 
    thinker_return_dict_in_generate=True,
    use_audio_in_video=USE_AUDIO_IN_VIDEO)

text = processor.batch_decode(text_ids.sequences[:, inputs["input_ids"].shape[1] :],
    skip_special_tokens=True,
    clean_up_tokenization_spaces=False)
print(text)
if audio is not None:
    sf.write(
        "output.wav",
        audio.reshape(-1).detach().cpu().numpy(),
        samplerate=24000,
    )
```

### vLLM Usage

#### Installation

```bash
git clone -b qwen3_omni https://github.com/wangxiongts/vllm.git
cd vllm
pip install -r requirements/build.txt
pip install -r requirements/cuda.txt
export VLLM_PRECOMPILED_WHEEL_LOCATION=https://wheels.vllm.ai/a5dd03c1ebc5e4f56f3c9d3dc0436e9c582c978f/vllm-0.9.2-cp38-abi3-manylinux1_x86_64.whl
VLLM_USE_PRECOMPILED=1 pip install -e . -v --no-build-isolation
# Install the Transformers
pip install git+https://github.com/huggingface/transformers
pip install accelerate
pip install qwen-omni-utils -U
pip install -U flash-attn --no-build-isolation
```

#### Inference Example

```python
import os
import torch

from vllm import LLM, SamplingParams
from transformers import Qwen3OmniMoeProcessor
from qwen_omni_utils import process_mm_info

if __name__ == '__main__':
    # vLLM engine v1 not supported yet
    os.environ['VLLM_USE_V1'] = '0'

    MODEL_PATH = "Qwen/Qwen3-Omni-30B-A3B-Instruct"
    # MODEL_PATH = "Qwen/Qwen3-Omni-30B-A3B-Thinking"

    llm = LLM(
        model=MODEL_PATH, trust_remote_code=True, gpu_memory_utilization=0.95,
        tensor_parallel_size=torch.cuda.device_count(),
        limit_mm_per_prompt={'image': 3, 'video': 3, 'audio': 3},
        max_num_seqs=8,
        max_model_len=32768,
        seed=1234,
    )

    sampling_params = SamplingParams(
        temperature=0.6,
        top_p=0.95,
        top_k=20,
        max_tokens=16384,
    )

    processor = Qwen3OmniMoeProcessor.from_pretrained(MODEL_PATH)

    messages = [
        {
            "role": "user",
            "content": [
                {"type": "video", "video": "https://qianwen-res.oss-cn-beijing.aliyuncs.com/Qwen3-Omni/demo/draw.mp4"}
            ], 
        }
    ]

    text = processor.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=True,
    )
    audios, images, videos = process_mm_info(messages, use_audio_in_video=True)

    inputs = {
        'prompt': text,
        'multi_modal_data': {},
        "mm_processor_kwargs": {
            "use_audio_in_video": True,
        },
    }

    if images is not None:
        inputs['multi_modal_data']['image'] = images
    if videos is not None:
        inputs['multi_modal_data']['video'] = videos
    if audios is not None:
        inputs['multi_modal_data']['audio'] = audios

    outputs = llm.generate([inputs], sampling_params=sampling_params)

    print(outputs[0].outputs[0].text)
```

#### vLLM Serve

```bash
# Qwen3-Omni-30B-A3B-Instruct for single GPU
vllm serve Qwen/Qwen3-Omni-30B-A3B-Instruct --port 8901 --host 127.0.0.1 --dtype bfloat16 --max-model-len 32768 --allowed-local-media-path / -tp 1

# Qwen3-Omni-30B-A3B-Instruct for multi-GPU (example on 4 GPUs)
vllm serve Qwen/Qwen3-Omni-30B-A3B-Instruct --port 8901 --host 127.0.0.1 --dtype bfloat16 --max-model-len 65536 --allowed-local-media-path / -tp 4

# Qwen/Qwen3-Omni-30B-A3B-Thinking for single GPU
vllm serve Qwen/Qwen3-Omni-30B-A3B-Thinking --port 8901 --host 127.0.0.1 --dtype bfloat16 --max-model-len 32768 --allowed-local-media-path / -tp 1

# Qwen/Qwen3-Omni-30B-A3B-Thinking for multi-GPU (example on 4 GPUs)
vllm serve Qwen/Qwen3-Omni-30B-A3B-Thinking --port 8901 --host 127.0.0.1 --dtype bfloat16 --max-model-len 65536 --allowed-local-media-path / -tp 4
```

#### API Call Example

```bash
curl http://localhost:8901/v1/chat/completions \
    -H "Content-Type: application/json" \
    -d '{
        "messages": [
            {
                "role": "system",
                "content": "You are a helpful assistant."
            },
            {
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": "https://qianwen-res.oss-cn-beijing.aliyuncs.com/Qwen3-Omni/demo/cars.jpg"}},
                    {"type": "audio_url", "audio_url": {"url": "https://qianwen-res.oss-cn-beijing.aliyuncs.com/Qwen3-Omni/demo/cough.wav"}},
                    {"type": "text", "text": "What can you see and hear? Answer in one sentence."}
                ]
            }
        ]
    }'
```

## Advanced Usage

### Audio Output Control

The model supports both text and audio outputs. If you don't need audio outputs:

```python
# Disable talker to save ~10GB GPU memory
model.disable_talker()
```

For more flexible control, specify `return_audio=False` when calling `generate()`:

```python
text_ids, _ = model.generate(..., return_audio=False)
```

### Voice Types

Qwen3-Omni supports three voice types for audio output:

| Voice Type | Gender | Description |
|------------|--------|-------------|
| Ethan | Male | A bright, upbeat voice with infectious energy and a warm, approachable vibe. |
| Chelsie | Female | A honeyed, velvety voice that carries a gentle warmth and luminous clarity. |
| Aiden | Male | A warm, laid-back American voice with a gentle, boyish charm. |

```python
# Use different voices
text_ids, audio = model.generate(..., speaker="Ethan")
text_ids, audio = model.generate(..., speaker="Chelsie")
text_ids, audio = model.generate(..., speaker="Aiden")
```

### Batch Inference

Transformers supports batch inference with mixed modalities:

```python
from transformers import Qwen3OmniMoeForConditionalGeneration, Qwen3OmniMoeProcessor
from qwen_omni_utils import process_mm_info

model = Qwen3OmniMoeForConditionalGeneration.from_pretrained(
    "Qwen/Qwen3-Omni-30B-A3B-Instruct",
    dtype="auto",
    device_map="auto",
    attn_implementation="flash_attention_2",
)
model.disable_talker()

processor = Qwen3OmniMoeProcessor.from_pretrained(MODEL_PATH)

# Different types of conversations
conversation1 = [
    {
        "role": "user",
        "content": [
            {"type": "image", "image": "https://example.com/image.jpg"},
            {"type": "text", "text": "What can you see in this image?"}
        ]
    }
]

conversation2 = [
    {
        "role": "user",
        "content": [
            {"type": "audio", "audio": "https://example.com/audio.wav"},
            {"type": "text", "text": "What can you hear?"}
        ]
    }
]

conversations = [conversation1, conversation2]
USE_AUDIO_IN_VIDEO = True

text = processor.apply_chat_template(conversations, add_generation_prompt=True, tokenize=False)
audios, images, videos = process_mm_info(conversations, use_audio_in_video=USE_AUDIO_IN_VIDEO)

inputs = processor(text=text, 
    audio=audios, 
    images=images, 
    videos=videos, 
    return_tensors="pt", 
    padding=True, 
    use_audio_in_video=USE_AUDIO_IN_VIDEO)
inputs = inputs.to(model.device).to(model.dtype)

text_ids, audio = model.generate(**inputs,
    return_audio=False,
    thinker_return_dict_in_generate=True,
    use_audio_in_video=USE_AUDIO_IN_VIDEO)

text = processor.batch_decode(text_ids.sequences[:, inputs["input_ids"].shape[1] :],
    skip_special_tokens=True,
    clean_up_tokenization_spaces=False)
print(text)
```

## Usage Tips

### GPU Memory Requirements

| Model | Precision | 15s Video | 30s Video | 60s Video | 120s Video |
|-------|-----------|-----------|-----------|-----------|------------|
| Qwen3-Omni-30B-A3B-Instruct | BF16 | ~79 GB | ~89 GB | ~108 GB | ~145 GB |
| Qwen3-Omni-30B-A3B-Thinking | BF16 | TBD | TBD | TBD | TBD |

### FlashAttention 2 Requirements

FlashAttention 2 can only be used when a model is loaded in `torch.float16` or `torch.bfloat16`. Make sure your hardware is compatible with FlashAttention 2.

### Batch Inference with vLLM

When using vLLM for batch inference:
- `limit_mm_per_prompt` specifies the maximum number of each modality's data allowed per message
- `tensor_parallel_size` enables multi-GPU parallel inference
- `max_num_seqs` indicates the number of sequences processed in parallel
- Larger values require more GPU memory but enable higher throughput

## Cookbook Examples

Qwen3-Omni supports various multimodal application scenarios:

| Category | Cookbook | Description |
|----------|----------|-------------|
| Audio | Speech Recognition | Speech recognition, supporting multiple languages and long audio |
| Audio | Speech Translation | Speech-to-Text / Speech-to-Speech translation |
| Audio | Music Analysis | Detailed analysis and appreciation of music |
| Audio | Sound Analysis | Description and analysis of various sound effects |
| Audio | Audio Caption | Audio captioning, detailed description of any audio input |
| Audio | Mixed Audio Analysis | Analysis of mixed audio content |
| Visual | OCR | OCR for complex images |
| Visual | Object Grounding | Target detection and grounding |
| Visual | Image Question | Answering arbitrary questions about images |
| Visual | Image Math | Solving complex mathematical problems in images |
| Visual | Video Description | Detailed description of video content |
| Visual | Video Navigation | Generating navigation commands from videos |
| Visual | Video Scene Transition | Analysis of scene transitions |
| Audio-Visual | Audio Visual Question | Answering questions in audio-visual scenarios |
| Audio-Visual | Audio Visual Interaction | Interactive communication with audio-visual inputs |
| Audio-Visual | Audio Visual Dialogue | Conversational interaction with audio-visual inputs |
| Agent | Audio Function Call | Using audio input to perform function calls |

All cookbooks are available in the [Qwen3-Omni GitHub repository](https://github.com/QwenLM/Qwen3-Omni).

## API Reference

### Qwen3OmniMoeForConditionalGeneration

Main model class for Qwen3-Omni.

**Key Methods:**
- `from_pretrained()`: Load model from pretrained weights
- `generate()`: Generate text and/or audio output
- `disable_talker()`: Disable audio output to save memory

### Qwen3OmniMoeProcessor

Processor for handling multimodal inputs.

**Key Methods:**
- `from_pretrained()`: Load processor from pretrained weights
- `apply_chat_template()`: Apply chat template to conversations
- `batch_decode()`: Decode generated token IDs to text

### process_mm_info

Utility function from `qwen_omni_utils` for processing multimodal information.

```python
audios, images, videos = process_mm_info(conversation, use_audio_in_video=True)
```

## Links

- [Model on ModelScope](https://www.modelscope.cn/models/Qwen/Qwen3-Omni-30B-A3B-Instruct)
- [Model on Hugging Face](https://huggingface.co/Qwen/Qwen3-Omni-30B-A3B-Instruct)
- [GitHub Repository](https://github.com/QwenLM/Qwen3-Omni)
- [Technical Report](https://github.com/QwenLM/Qwen3-Omni/blob/main/assets/Qwen3_Omni.pdf)
- [Cookbooks](https://github.com/QwenLM/Qwen3-Omni/tree/main/cookbooks)
