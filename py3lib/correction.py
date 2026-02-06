#!/usr/bin/env python3
"""
背景知识：
根据图片内容对whisper转录文字进行纠错。中文正常语速是3-4个字每秒，10分钟可达4000字，所以我认为每一张关键帧对音频转录文本的作用域就是关键帧时间戳前后各5分钟。
一般图片文字最多500字，10分钟转录文字约4000字。那么按照大模型上下文窗口5000token限制，开发者有500字的自定义prompt空间。

开发计划：
1. 写一个函数，输入一个frame开头的文件名，返回时分秒。比如frame00.00.01-0.jpg ， 返回00:00:01。frame101.00.50-0.28.jpg，返回101.00.50
2. 写一个函数，将第1步函数运行得到的hh.mm.ss或hhh.mm.ss这样的时间戳转化成毫秒数。比如00:01:01，转化后是60*1000+1000=61000毫秒。返回整数
3. 写一个函数，输入一个.tsv文件的路径，和一个整数（表示第2步中毫秒时间戳F），然后去tsv文件中匹配F时间戳前5分钟和后5分钟的转录文本内容。返回文本字符串，文本汇总的时间戳必须保留。
4. 写一个纠错函数，输入一段转录文本，和一个frame文件的路径，调用py3lib/openai_vl_compatible.py中的sse_vlm_chat，让VLM识别图像并对转录文本进行纠错。函数返回纠错内容，纠错内容也必须保留时间戳。
5. 写一个替换函数。输入一段纠错后的文本，和一个.tsv文件的路径。因为文本和文件内容都有对应的时间戳，所以根据时间戳，用纠错内容替换.tsv文件中的对应内容，保存文件。
6. 写一个主函数，传入一个frames目录（目录包含一些关键帧图片，图片命名类似frame00.00.02-0.41.jpg）遍历文件，然后调用第1-4步实现的函数，不断地对.tsv文件内容进行纠错。
测试用的frames目录：/config/workspace/llmnote/workspace/过期米老鼠/frames/ ， .tsv文件：/config/workspace/llmnote/workspace/过期米老鼠/过期米老鼠.tsv

"""

import re
import os
from typing import List, Tuple

from py3lib.logsystem import logger
from py3lib.openai_vl_compatible import OpenAIVLCompatible
from settings import VLM_BASE_URL, VLM_API_KEY, VLM_MODEL_NAME


# 常量定义
FIVE_MINUTES_MS = 5 * 60 * 1000  # 5分钟的毫秒数


def frame_filename_to_timestamp(frame_filename: str) -> str:
    """从 frame 开头的文件名中提取时分秒格式时间戳
    
    Args:
        frame_filename: 如 'frame00.00.01-0.jpg' 或 'frame00.00.02-0.41.jpg'
    
    Returns:
        时分秒格式字符串，如 '00:00:01'
    """
    # 匹配 frame 后面的小时.分钟.秒 格式，支持 -数字 或 -小数 格式
    pattern = r'^frame(\d+)\.(\d+)\.(\d+)-(\d+\.?\d*)\.jpg$'
    match = re.match(pattern, frame_filename)
    
    if not match:
        raise ValueError(f"无效的frame文件名格式: {frame_filename}")
    
    hours = match.group(1)
    minutes = match.group(2)
    seconds = match.group(3)
    
    # 补齐两位数
    hours = hours.zfill(2) if len(hours) <= 2 else hours.zfill(3)
    minutes = minutes.zfill(2)
    seconds = seconds.zfill(2)
    
    return f"{hours}:{minutes}:{seconds}"


def timestamp_to_milliseconds(timestamp: str) -> int:
    """将 hh.mm.ss 或 hhh.mm.ss 格式时间戳转换为毫秒
    
    Args:
        timestamp: 如 '00:01:01' 或 '01:01:01'
    
    Returns:
        毫秒整数，如 61000
    """
    parts = timestamp.split(':')
    
    if len(parts) != 3:
        raise ValueError(f"无效的时间戳格式: {timestamp}")
    
    hours = int(parts[0])
    minutes = int(parts[1])
    seconds = int(parts[2])
    
    total_ms = hours * 3600 * 1000 + minutes * 60 * 1000 + seconds * 1000
    
    return total_ms


def extract_text_range(tsv_path: str, timestamp_ms: int) -> str:
    """从 tsv 文件提取时间戳前后 5 分钟的转录文本
    
    Args:
        tsv_path: .tsv 文件路径
        timestamp_ms: 毫秒时间戳
    
    Returns:
        时间戳范围内的转录文本字符串（含时间戳）
    """
    start_time = timestamp_ms - FIVE_MINUTES_MS
    end_time = timestamp_ms + FIVE_MINUTES_MS
    
    # 确保开始时间不为负
    start_time = max(0, start_time)
    
    result_lines = []
    
    with open(tsv_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # 跳过表头
    for line in lines[1:]:
        parts = line.strip().split('\t')
        if len(parts) < 3:
            continue
        
        line_start = int(parts[0])
        line_end = int(parts[1])
        text = parts[2]
        
        # 检查是否有交集
        if line_end > start_time and line_start < end_time:
            result_lines.append(f"{line_start}\t{line_end}\t{text}")
    
    return '\n'.join(result_lines)


def _collect_sse_response(sse_generator) -> str:
    """从SSE生成器中收集完整响应"""
    full_response = ""
    for answer in sse_generator:
        if answer == "[DONE]":
            break
        try:
            import json
            chunk = json.loads(answer)
            if "choices" in chunk and len(chunk["choices"]) > 0:
                content = chunk["choices"][0]["delta"].get("content", "")
                full_response += content
        except (json.JSONDecodeError, KeyError) as e:
            logger.warning(f"解析响应块失败: {e}")
    
    return full_response


def correct_transcription(text: str, frame_path: str) -> str:
    """根据图片内容纠错转录文本
    
    Args:
        text: 转录文本
        frame_path: 关键帧图片路径
    
    Returns:
        纠错后的文本（含时间戳），调用 sse_vlm_chat() 处理
    """

    
    # 构建提示词
    prompt = f"""你是一个专业的文字纠错助手。请根据图片内容对以下转录文本进行纠错。

## 图片中出现的文字内容：
请看附带的图片。

## 转录文本：
{text}

## 纠错要求：
1. 仔细对比图片中显示的文字与转录文本的差异
2. 修正明显的识别错误，如同音字替换、多字、少字、错字等
3. 保留原始的时间戳信息（格式如：start\tend\ttext）
4. 如果图片中的文字与转录文本一致，无需修改则原文返回
5. 只修正与图片内容相关的文字，其他内容保持不变
6. 输出格式必须与输入格式相同，保持时间戳

请直接返回纠错后的文本，不需要任何解释。"""
    
    try:
        # 创建VLM客户端
        client = OpenAIVLCompatible(
            base_url=VLM_BASE_URL,
            api_key=VLM_API_KEY,
            model_name=VLM_MODEL_NAME
        )
        
        # 调用VLM进行纠错
        response = client.sse_vlm_chat(frame_path, prompt, return_sse_dict=True)
        corrected_text = _collect_sse_response(response)
        
        # 清理响应，去除可能的额外空白
        corrected_text = corrected_text.strip()
        
        logger.info(f"纠错完成，原始文本长度: {len(text)}, 纠错后长度: {len(corrected_text)}")
        
        return corrected_text if corrected_text else text
        
    except Exception as e:
        logger.error(f"纠错失败: {e}")
        return text


def replace_content(corrected_text: str, tsv_path: str) -> None:
    """根据时间戳替换原 tsv 文件内容并保存
    
    Args:
        corrected_text: 纠错后的文本
        tsv_path: 原 tsv 文件路径
    """
    # 解析纠错后的文本
    corrected_lines = corrected_text.strip().split('\n') if corrected_text.strip() else []
    corrected_dict = {}
    
    for line in corrected_lines:
        parts = line.strip().split('\t')
        if len(parts) >= 3:
            start = parts[0]
            end = parts[1]
            text = '\t'.join(parts[2:])
            key = (start, end)
            corrected_dict[key] = text
    
    # 读取原文件
    with open(tsv_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # 替换内容
    new_lines = [lines[0]]  # 保留表头
    
    for line in lines[1:]:
        parts = line.strip().split('\t')
        if len(parts) >= 3:
            start = parts[0]
            end = parts[1]
            original_text = parts[2]
            
            key = (start, end)
            if key in corrected_dict:
                # 使用纠错后的文本
                new_lines.append(f"{start}\t{end}\t{corrected_dict[key]}")
                logger.info(f"替换时间戳 {start}-{end} 的内容")
            else:
                # 保留原内容
                new_lines.append(line.strip())
    
    # 保存文件
    with open(tsv_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(new_lines) + '\n')
    
    logger.info(f"已保存修改后的文件: {tsv_path}")


def batch_correct(frames_dir: str, tsv_path: str = None) -> None:
    """遍历关键帧图片批量纠错
    
    Args:
        frames_dir: 关键帧目录路径
        tsv_path: tsv文件路径，如果为None则从settings导入
    """
    if tsv_path is None:
        from settings import TSV_PATH
        tsv_path = TSV_PATH
    
    # 获取所有frame文件
    frame_files = sorted([f for f in os.listdir(frames_dir) if f.startswith('frame') and f.endswith('.jpg')])
    
    logger.info(f"找到 {len(frame_files)} 个关键帧文件待处理")
    
    for frame_file in frame_files:
        frame_path = os.path.join(frames_dir, frame_file)
        
        try:
            # 步骤1: 从文件名提取时间戳
            timestamp = frame_filename_to_timestamp(frame_file)
            logger.info(f"处理文件: {frame_file}, 时间戳: {timestamp}")
            
            # 步骤2: 将时间戳转换为毫秒
            timestamp_ms = timestamp_to_milliseconds(timestamp)
            logger.info(f"时间戳毫秒数: {timestamp_ms}")
            
            # 步骤3: 提取时间戳前后5分钟的转录文本
            text_range = extract_text_range(tsv_path, timestamp_ms)
            logger.info(f"提取到转录文本行数: {len(text_range.split(chr(10))) if text_range else 0}")
            
            if not text_range.strip():
                logger.warning(f"时间戳 {timestamp} 附近没有找到转录文本，跳过")
                continue
            
            # 步骤4: 根据图片内容纠错转录文本
            corrected_text = correct_transcription(text_range, frame_path)
            
            # 步骤5: 替换原tsv文件内容
            if corrected_text.strip():
                replace_content(corrected_text, tsv_path)
                logger.info(f"完成文件 {frame_file} 的纠错处理")
            else:
                logger.warning(f"文件 {frame_file} 纠错后内容为空，跳过")
                
        except Exception as e:
            logger.error(f"处理文件 {frame_file} 时出错: {e}")
            continue
    
    logger.info("批量纠错处理完成")


if __name__ == "__main__":
    import sys
    
    # 测试
    test_frame = "frame00.00.01-0.jpg"
    print(f"测试时间戳解析: {frame_filename_to_timestamp(test_frame)}")
    
    test_timestamp = "00:01:01"
    print(f"测试时间戳转毫秒: {timestamp_to_milliseconds(test_timestamp)}")
    
    # 批量纠错
    frames_dir = "/config/workspace/llmnote/workspace/过期米老鼠/frames/"
    tsv_path = "/config/workspace/llmnote/workspace/过期米老鼠/过期米老鼠.tsv"
    
    # 支持命令行参数覆盖
    if len(sys.argv) >= 3:
        frames_dir = sys.argv[1]
        tsv_path = sys.argv[2]
    elif len(sys.argv) == 2:
        frames_dir = sys.argv[1]
    
    print(f"关键帧目录: {frames_dir}")
    print(f"TSV文件路径: {tsv_path}")
    batch_correct(frames_dir, tsv_path)
