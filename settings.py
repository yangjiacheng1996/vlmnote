#!/usr/bin/env python

import os

project_root = os.path.dirname(os.path.abspath(__file__))

# 工作目录的绝对路径
workspace = os.path.join(project_root, 'workspace')

# 视频文件的绝对路径,视频文件可以不在工作目录中，本项目为了方便，在工作目录中存放了一个“过期米老鼠.mp4”作为案例
video = os.path.join(workspace, "过期米老鼠.mp4")

# 视频主语言
video_language = "Chinese"

# 大模型基础配置
vlm_base_url = "https://api.siliconflow.cn"
vlm_api_key = "sk-psggkotzdnaurduuivmqteqzimlgetzisdgdhvvzmfhzkxoo"
vlm_model_name = "Qwen/Qwen3-VL-235B-A22B-Thinking"
