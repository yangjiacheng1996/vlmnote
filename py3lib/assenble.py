#!/usr/bin/env python3

"""
开发计划：

1. 在workspace/过期米老鼠/frames中有我提取的视频关键帧，文件名是这个关键帧在视频中的时间戳，
在workspace/过期米老鼠/过期米老鼠.tsv是已经纠错完成的视频音频的转录文字，每行是起始时间、终点时间、转录内容。
请你编写一个函数，传入frames目录的绝对路径和tsv文件的绝对路径。函数根据关键帧时间错中时分秒，结合转录文字时间，按照时间顺序将图片和文字写入一个md中。文字部分不带时间戳。
这个md的路径应该和frames目录处于同一级目录，md文件中的图片地址是相对路径，链接frames中的图片。
"""

import os
import re
from pathlib import Path
from typing import List, Tuple


def _parse_frame_timestamp(filename: str) -> int:
    """
    从帧文件名中解析时间戳（毫秒）
    帧文件名格式: frameHH.MM.SS-framenumber.jpg
    例如: frame00.00.01-0.jpg -> 1000ms
    例如: frame00.00.02-0.41.jpg -> 2000ms
    """
    match = re.match(r'frame(\d+)\.(\d+)\.(\d+)-[\d.]+\.jpg', filename)
    if not match:
        raise ValueError(f"无效的帧文件名格式: {filename}")
    
    hours, minutes, seconds = map(int, match.groups()[:3])
    return hours * 3600000 + minutes * 60000 + seconds * 1000


def _parse_tsv(tsv_path: str) -> List[Tuple[int, int, str]]:
    """
    解析TSV文件，返回[(起始时间ms, 结束时间ms, 文本内容), ...]
    跳过第一行的表头
    """
    segments = []
    with open(tsv_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    for line in lines[1:]:  # 跳过表头
        line = line.strip()
        if not line:
            continue
        parts = line.split('\t')
        if len(parts) >= 3:
            start = int(parts[0])
            end = int(parts[1])
            text = parts[2]
            segments.append((start, end, text))
    
    return segments


def _find_matching_text(frame_time_ms: int, segments: List[Tuple[int, int, str]]) -> str:
    """
    查找与给定帧时间最匹配的文本段
    返回包含该帧时间点的文本内容
    """
    for start, end, text in segments:
        if start <= frame_time_ms < end:
            return text
    return ""


def generate_video_markdown(frames_dir: str, tsv_path: str) -> str:
    """
    根据关键帧和转录文字生成markdown文件
    
    Args:
        frames_dir: 关键帧目录的绝对路径
        tsv_path: TSV文件的绝对路径
    
    Returns:
        生成的markdown文件的绝对路径
    """
    frames_path = Path(frames_dir)
    tsv_file = Path(tsv_path)
    
    if not frames_path.exists() or not frames_path.is_dir():
        raise ValueError(f"帧目录不存在: {frames_dir}")
    
    if not tsv_file.exists():
        raise ValueError(f"TSV文件不存在: {tsv_path}")
    
    # 获取所有帧文件并按时间排序
    frame_files = []
    for filename in os.listdir(frames_dir):
        if filename.endswith('.jpg') and filename.startswith('frame'):
            timestamp_ms = _parse_frame_timestamp(filename)
            frame_files.append((timestamp_ms, filename))
    
    frame_files.sort(key=lambda x: x[0])
    
    # 解析TSV文件
    segments = _parse_tsv(tsv_path)
    
    # 生成markdown文件路径
    md_path = frames_path.parent / f"{frames_path.stem}.md"
    
    # 写入markdown
    with open(md_path, 'w', encoding='utf-8') as f:
        f.write(f"# {frames_path.stem}\n\n")
        
        last_text = None  # 记录上一个文本，避免重复
        for timestamp_ms, filename in frame_files:
            # 查找匹配的文本
            text = _find_matching_text(timestamp_ms, segments)
            
            # 计算相对路径（从md文件到帧文件）
            frames_rel_path = frames_path.name
            image_path = f"{frames_rel_path}/{filename}"
            
            # 写入图片
            f.write(f"![{filename}]({image_path})\n")
            
            # 只有当文本与上一个不同时才写入文本
            if text and text != last_text:
                f.write(f"\n{text}\n")
                last_text = text
            else:
                last_text = text  # 更新last_text，即使是空文本也要更新
            
            f.write("\n---\n\n")
    
    return str(md_path)