#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生成引擎 - 高层 API，封装流水线、任务管理、错误处理
"""

import json
import os
import asyncio
from typing import Dict, Optional, Callable, Any
from datetime import datetime

from ..config import AppConfig, DEFAULT_CONFIG
from ..utils.logger import logger
from ..utils.validators import validate_script
from ..utils.file_utils import safe_read_json, safe_read_text
from .pipeline import GenerationPipeline
from .state import TaskManager, GenerationTask, TaskStatus


class VideoGenerationEngine:
    """
    视频生成引擎 - 高层 API

    提供一键式视频生成接口，管理全生命周期
    """

    def __init__(self, config: AppConfig = None):
        self.config = config or DEFAULT_CONFIG
        self.pipeline = GenerationPipeline(config)
        self.task_manager = self.pipeline.task_manager

    async def generate_from_script(self, title: str, script_content: str,
                                    output_dir: str = None,
                                    progress_callback: Optional[Callable] = None) -> Dict:
        """
        从脚本字符串生成视频

        Args:
            title: 视频标题
            script_content: JSON 脚本内容
            output_dir: 输出目录
            progress_callback: 进度回调

        Returns:
            生成结果
        """
        # 验证脚本
        validation = validate_script(script_content)
        if not validation.is_valid:
            return {
                'success': False,
                'errors': validation.errors,
                'warnings': validation.warnings
            }

        script_data = validation.data
        return await self.pipeline.run(title, script_data, output_dir, progress_callback)

    async def generate_from_file(self, title: str, script_file: str,
                                  output_dir: str = None,
                                  progress_callback: Optional[Callable] = None) -> Dict:
        """
        从脚本文件生成视频

        Args:
            title: 视频标题
            script_file: JSON 脚本文件路径
            output_dir: 输出目录
            progress_callback: 进度回调

        Returns:
            生成结果
        """
        content = safe_read_text(script_file)
        if not content:
            return {
                'success': False,
                'errors': [f"无法读取脚本文件: {script_file}"]
            }
        return await self.generate_from_script(title, content, output_dir, progress_callback)

    async def generate_from_loaded_data(self, title: str, script_data: Dict,
                                         output_dir: str = None,
                                         progress_callback: Optional[Callable] = None) -> Dict:
        """
        从已加载的字典数据生成视频

        Args:
            title: 视频标题
            script_data: 脚本字典数据
            output_dir: 输出目录
            progress_callback: 进度回调

        Returns:
            生成结果
        """
        script_content = json.dumps(script_data, ensure_ascii=False)
        return await self.generate_from_script(title, script_content, output_dir, progress_callback)