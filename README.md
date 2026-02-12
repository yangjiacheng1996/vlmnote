# vlmnote
use VLM taking note from vedios

# 软件实现原理：
1. 工作区：根据视频的文件名（不包含扩展名），在工作目录 `workspace/` 中创建一个同名目录，例如 `workspace/过期米老鼠/`，所有中间结果都保存在该目录下。
2. 关键帧提取：使用 `evp` 命令从视频中提取关键帧，命令自动生成仅包含关键帧截图的 `frames.pdf` 文件（代码中实际使用的相似度参数为 `0.7`）。
3. 关键帧保存：在视频对应目录下创建 `frames/` 子目录，将 `frames.pdf` 中每一页的关键帧图片和时间戳提取出来，保存到 `frames/` 中，图片文件名中包含时间信息。
4. 转录：使用 `whisper` 命令将视频中的音频部分转录成文字，使用的模型为 `turbo`，语言通过 [`settings.video_language`](settings.py:14) 配置，转录结果（含时间戳）保存在同目录下的 `.tsv` 文件中。
5. 纠错：遍历 `frames/` 目录中的每个关键帧图片，根据图片时间戳在 `.tsv` 转录文件中截取对应时间范围内的文本，将「图片 + 文本」一起发送给 VLM 视觉大模型进行文本纠错与补全。
6. 汇总：将关键帧信息和纠错后的转录结果按照时间戳排序，生成 Markdown 笔记文件，内容中通过相对路径引用 `frames/` 目录中的关键帧图片。
7. 转 pdf：为了适应部分 RAG 系统只支持上传 pdf，这里将最终的 Markdown 笔记转换并保存为 `frames.pdf`（或类似命名的 PDF 笔记文件），作为最终产物。

# 安装
使用cpu进行音频转录文字，执行以下步骤
```
# 纯CPU运行
git clone https://github.com/yangjiacheng1996/llmnote.git
cd llmnote
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -U pip setuptools wheel 

# 安装whisper与openai库
pip install -U openai-whisper openai

# 安装ffmepg
sudo apt update && apt install -y ffmpeg

# 安装evp
apt install -y libgtk2.0-dev  pkg-config
pip install extract-video-ppt
pip install fpdf2==2.8.4  # 如果安装fpdf2==2.8.5，在evp命令执行时会出现报错，图片无法写入pdf中。

# pdf
pip install pdfplumber markdown weasyprint 

```
使用显卡加速音频转录，要求显存>=8GB,安装步骤如下：
```
# GPU加速运行

# 查看驱动和cuda版本
nvidia-smi
nvcc -V

# 克隆项目，创建虚拟环境
git clone https://github.com/yangjiacheng1996/llmnote.git
cd llmnote
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -U pip setuptools wheel 

# 安装pytorch 12.8或以上版本（支持RTX 30系列、40系列、50系列显卡）
pip install torch==2.8.0+cu128 torchvision==0.23.0+cu128 torchaudio==2.8.0+cu128 --index-url https://download.pytorch.org/whl/cu128

# 安装whisper与openai库
pip install -U openai-whisper openai

# 安装ffmepg
sudo apt update && apt install -y ffmpeg

# 安装evp
apt install -y libgtk2.0-dev  pkg-config
pip install extract-video-ppt
pip install fpdf2==2.8.4  # 如果安装fpdf2==2.8.5，在evp命令执行时会出现报错，图片无法写入pdf中。

# pdf
pip install pdfplumber markdown weasyprint 
```

# 使用
修改settings.py中video变量，修改成自己视频的绝对路径,然后执行主程序。
```
python main.py
```
如果脚本执行成功，去workspace工作目录中获取生成的笔记frames.pdf。

