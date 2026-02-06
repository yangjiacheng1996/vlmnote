#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import subprocess
import time
from py3lib.logsystem import logger

# 自定义超时异常
class TimeoutError(Exception):
    def __init__(self, message):
        Exception.__init__(self, message)


def run_command(cmd: list, cwd=None, timeout=86400):
    """安全执行命令，自动处理输出缓冲与超时"""
    logger.info("run command: %s", cmd)
    try:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            timeout=timeout,
            capture_output=True,  # 自动处理 PIPE 阻塞
            text=False,           # 保持字节流（与原逻辑一致）
            check=False
        )
        if result.returncode != 0:
            err_msg = result.stderr.decode('utf-8', errors='replace').strip()
            raise Exception(f"Run {cmd} error: {err_msg}")
        # 保持原接口：返回字节列表（每行含换行符）
        return result.stdout.splitlines(keepends=True) if result.stdout else []
    except subprocess.TimeoutExpired:
        raise TimeoutError(f"Run {cmd} timeout (>{timeout}s)")
    except FileNotFoundError as e:
        raise Exception(f"Command not found: {cmd}. Error: {e}")