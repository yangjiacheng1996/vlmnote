#!/usr/bin/env python3

import logging
import os
import sys
from logging.handlers import RotatingFileHandler


def setup_logger(logger_name="default", log_dir="logs", log_file="default.log", log_level=logging.DEBUG, add_filehandler=True, add_streamhandler=False):
    """
    本函数可以在指定目录生成指定名称的日志文件，日志文件滚动更新，每个文件5M，最多保留10个文件。日志级别默认为DEBUG，低于level的日志不会输出。
    :param logger_name: 日志名称，默认为"llmnote"
    :param log_dir: 日志文件存放目录，默认为"logs"
    :param log_file: 日志文件名称，默认为"llmnote.log"
    :param log_level: 日志级别，默认为logging.DEBUG
    :param add_filehandler: 是否添加文件处理器,将日志写入文件里面，默认为True
    :param add_streamhandler: 是否添加控制台处理器，将日志打印到命令行，默认为False
    return: 返回一个logging.Logger对象。
    """
    # 创建日志目录
    os.makedirs(log_dir, exist_ok=True)

    # 获取或创建 logger
    logger = logging.getLogger(logger_name)
    logger.setLevel(log_level)
    logger.propagate = False  # 防止向上冒泡导致重复日志

    # 构建完整的日志文件路径
    log_path = os.path.join(log_dir, log_file)
    
    # 检查logger是否已存在相同配置的handler，避免重复添加
    existing_handlers = set()
    for handler in logger.handlers[:]:  # 遍历副本以防修改时出错
        if isinstance(handler, RotatingFileHandler) and hasattr(handler, 'baseFilename'):
            if os.path.abspath(handler.baseFilename) == os.path.abspath(log_path):
                existing_handlers.add('file')
        elif isinstance(handler, logging.StreamHandler):
            if handler.stream == sys.stdout:
                existing_handlers.add('stream')
        
    # 添加文件 handler（如果需要且不存在）
    if add_filehandler and 'file' not in existing_handlers:
        file_handler = RotatingFileHandler(
            filename=log_path,
            maxBytes=5 * 1024 * 1024,
            backupCount=10,
            encoding="utf-8"
        )
        file_handler.setLevel(log_level)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    # 添加控制台 handler（如果需要且不存在）
    if add_streamhandler and 'stream' not in existing_handlers:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(log_level)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
        
    return logger


project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)
from settings import workspace
log_dir = os.path.join(workspace, "logs")
logger = setup_logger(logger_name="llmnote", log_dir=log_dir, log_file="llmnote.log", log_level=logging.INFO, add_filehandler=True, add_streamhandler=True)