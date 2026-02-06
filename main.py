#!/usr/bin/env python

# standard library imports
import os
import sys
import subprocess
import shutil
import time
import logging
from pathlib import Path

# project modules imports
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.append(project_root)
from settings import workspace
from settings import video, video_language
from settings import base_url, api_key, model_name
from py3lib.logsystem import logger
from py3lib.commandline import run_command
from py3lib.openai_compatible import OpenAICompatible
from py3lib.filesystem import dir_writable, get_path_filename, get_path_extension
from py3lib.pdf_no_re import save_frame_to_dir
from py3lib import correction
from py3lib.assenble import generate_video_markdown

# secondary library


def main():
    python_bin = os.path.dirname(sys.executable)
    # 检查workspace是否存在或者是否有权限操作
    if not dir_writable(workspace):
        print(f"工作目录不存在或无法写入：{workspace}")
        print(f"AI自动做笔记工具停止运行。")
        sys.exit(1)
    # 检查视频文件是否存在
    if not os.path.isfile(video):
        logger.error(f"视频文件不存在：{video}")
        logger.error(f"AI自动做笔记工具停止运行。")
        sys.exit(1)
    # 检查视频文件扩展名是否合法。
    legal_extension = [".mp4", ".avi", ".flv", ".mkv", ".mov", ".wmv", ".rmvb", ".rm", ".mpg", ".mpeg",]
    if get_path_extension(video) not in legal_extension:
        logger.error(f"视频文件扩展名不合法，本工具无法处理：")
        logger.error(f"合法的视频扩展名包括：{legal_extension}")
        logger.error(f"AI自动做笔记工具停止运行。")
        sys.exit(1)
    # 提前创建OpenAI Compatible客户端,对象创建成功时，说明大模型已经连通了。
    client = OpenAICompatible(base_url=base_url, api_key=api_key, model_name=model_name)
    logger.info("大模型连接成功！")
    # 基于视频文件的路径和文件名，在工作目录中创建与文件名（不包含扩展名）相同的目录
    video_name = get_path_filename(video)
    video_dir = os.path.join(workspace, video_name)
    # 如果video_dir已经存在，则先删除。
    if os.path.isdir(video_dir):
        shutil.rmtree(video_dir)
    # 创建video_dir目录
    os.makedirs(video_dir, exist_ok=True)
    logger.info(f"需要解析的视频：{video}")
    logger.info(f"视频解析目录创建成功：{video_dir}")
    # 提取视频文件中的关键帧
    evp_path = os.path.join(python_bin, "evp")
    pdfname = video_name + ".pdf"
    pdfpath = os.path.join(video_dir, pdfname)
    evp_cmd = [evp_path, "--similarity", "0.7", "--pdfname", pdfname, video_dir, video]
    logger.info(f"开始提取视频关键帧...")
    run_command(evp_cmd, cwd=video_dir)
    logger.info(f"关键帧提取完毕，内容保存在PDF文件中：{pdfpath}")
    # 使用whisper将视频中的音频部分转录成文字
    # whisper /root/00课程介绍与学习指南.mp4   --model turbo  --language Cantonese 
    whisper_path = os.path.join(python_bin,"whisper")
    whisper_cmd = [whisper_path, video, "--model", "turbo", "--language", video_language]
    logger.info(f"开始将视频中声音转录成文字")
    logger.info(f"第一次转录耗时很长，因为会下载turbo模型，后续转录不会重复下载。")
    run_command(whisper_cmd, cwd=video_dir)
    logger.info(f"视频声音转录成功！")
    # 在video_dir中创建frames目录，然后读取pdfpath这个PDF文件，将pdf中的关键帧保存到frames中
    frames_dir = os.path.join(video_dir, "frames")
    logger.info("提取关键帧pdf中的图片到frames目录...")
    save_frame_to_dir(pdfpath, frames_dir)
    logger.info("所有关键帧已经保存到frames目录！")
    # whisper音频转录文字纠错。读取frames_dir目录中的关键帧对转录文本进行纠错
    tsvname = video_name + ".tsv"
    tsv_path = os.path.join(video_dir, tsvname)
    logger.info(f"开始whisper音频转录文字纠错...")
    correction.batch_correct(frames_dir, tsv_path)
    logger.info(f"whisper音频转录文字纠错完成！")
    # 根据关键帧和转录文字生成markdown汇总文件
    logger.info("开始生成关键帧与语音转录汇总的markdown文件...")
    md_path = generate_video_markdown(frames_dir, tsv_path)
    logger.info(f"关键帧与语音转录汇总文件已生成：{md_path}")


if __name__ == '__main__':
    main()
