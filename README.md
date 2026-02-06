# vlmnote
use VLM taking note from vedios

# 软件实现原理：
1. 工作区：根据视频的文件名（不包含扩展名），在工作目录中创建一个同名目录，并将视频文件拷贝到这个同名目录中。
2. 转录：使用whisper命令提取视频中的音频部分，转录成文字，20%不准确。
3. 关键帧提取：使用evp命令提取视频中的关键帧，命令自动生成pdf，相似度调高到0.8
4. 关键帧保存：将关键帧pdf中的图片和时间戳提取到同名目录frames中，图片文件使用时间戳命名。
5. 纠错：由于转录存在20%，所以遍历frames目录中的每个关键帧图片，根据图片时间戳提取前后5分钟的文本，将图片+文本呢一起发送给VLM视觉大模型进行文本纠错。
6. 汇总：将关键帧和纠错转录结果按照时间戳排序，写入md中。图片用相对路径链接frames中的关键帧。
7. 转pdf：为了适应部分RAG系统只支持上传pdf，这里将md信息全部保存为pdf。

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

