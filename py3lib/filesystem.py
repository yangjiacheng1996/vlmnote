#!/usr/bin/env python3

# standard library imports
import os
from pathlib import Path

def dir_writable(path:str) -> bool:
    """
    检查目录是否存在，且可以向这个目录写入文件。
    :param path: 目录路径
    """
    writable = True
    if not os.path.isdir(path):
        writable = False
    if not os.access(path, os.W_OK):
        writable = False
    return writable


def get_path_filename(file_path):
    """
    从视频文件路径中提取文件名（不包含扩展名）
    参数:
    file_path (str): 视频文件的绝对路径
    返回:
    str: 文件名（不包含扩展名）
    """
    # 使用Path对象处理路径
    path = Path(file_path)
    # 直接获取不带扩展名的文件名
    return path.stem


def get_path_extension(file_path):
    """
    获取视频文件的扩展名（包含点号）
    参数:
    file_path (str): 视频文件的绝对路径
    返回:
    str: 视频文件的扩展名（包含点号，如".mp4"）
    """
    # 使用Path对象处理路径
    path = Path(file_path)
    # 获取扩展名（包含点号）
    return path.suffix