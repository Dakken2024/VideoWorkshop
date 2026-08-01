#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一日志工具 - 支持控制台输出、文件日志、回调通知
"""

import os
import sys
import time
import logging
from datetime import datetime
from typing import Optional, Callable, List
from enum import Enum


class LogLevel(Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    SUCCESS = "SUCCESS"
    WARNING = "WARNING"
    ERROR = "ERROR"


class Logger:
    """统一日志管理器"""

    def __init__(self, name: str = "VideoGen", log_file: Optional[str] = None):
        self.name = name
        self.log_file = log_file
        self.callbacks: List[Callable[[str, str], None]] = []
        self._setup_logger()

    def _setup_logger(self):
        """初始化 Python logging"""
        self._logger = logging.getLogger(self.name)
        self._logger.setLevel(logging.DEBUG)

        # 控制台 handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.DEBUG)
        console_handler.setFormatter(logging.Formatter(
            '%(asctime)s [%(levelname)s] %(message)s',
            datefmt='%H:%M:%S'
        ))
        self._logger.addHandler(console_handler)

        # 文件 handler
        if self.log_file:
            os.makedirs(os.path.dirname(self.log_file), exist_ok=True)
            file_handler = logging.FileHandler(self.log_file, encoding='utf-8')
            file_handler.setLevel(logging.DEBUG)
            file_handler.setFormatter(logging.Formatter(
                '%(asctime)s [%(levelname)s] %(message)s'
            ))
            self._logger.addHandler(file_handler)

    def on_log(self, callback: Callable[[str, str], None]):
        """注册日志回调"""
        self.callbacks.append(callback)

    def _log(self, level: LogLevel, message: str):
        """内部日志方法"""
        timestamp = datetime.now().strftime('%H:%M:%S')
        log_line = f"[{timestamp}] [{level.value}] {message}"

        # 标准 logging
        log_method = getattr(self._logger, level.value.lower(), self._logger.info)
        log_method(message)

        # 回调通知
        for cb in self.callbacks:
            try:
                cb(level.value, message)
            except Exception:
                pass

    def debug(self, message: str): self._log(LogLevel.DEBUG, message)
    def info(self, message: str): self._log(LogLevel.INFO, message)
    def success(self, message: str): self._log(LogLevel.SUCCESS, message)
    def warning(self, message: str): self._log(LogLevel.WARNING, message)
    def error(self, message: str): self._log(LogLevel.ERROR, message)


# 全局日志实例
logger = Logger()