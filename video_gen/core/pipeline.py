#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生成流水线 - 编排音频、图片、视频、字幕的生成流程
"""

import os
import asyncio
from typing import Dict, Optional, Callable, List, Tuple
from datetime import datetime

from ..config import AppConfig, DEFAULT_CONFIG
from ..utils.logger import logger
from ..utils.file_utils import ensure_dir, title_to_filename, get_output_dir
from ..utils.validators import validate_script
from ..audio.generator import AudioGenerator
from ..image.generator import ImageGenerator
from ..video.compositor import VideoCompositor
from .state import TaskManager, GenerationTask, TaskStatus


class GenerationPipeline:
    """
    生成流水线

    按序执行:
    1. 验证脚本
    2. 生成音频
    3. 生成图片
    4. 合成视频（含字幕）
    """

    def __init__(self, config: AppConfig = None):
        self.config = config or DEFAULT_CONFIG
        self.audio_gen = AudioGenerator(self.config.audio)
        self.image_gen = ImageGenerator(self.config.image)
        self.video_comp = VideoCompositor(self.config.video)
        self.task_manager = TaskManager()

    async def run(self, title: str, script_data: Dict,
                  output_dir: str = None,
                  progress_callback: Optional[Callable] = None,
                  scene_callback: Optional[Callable] = None) -> Dict:
        """
        执行完整生成流水线

        Args:
            title: 视频标题
            script_data: 脚本数据
            output_dir: 输出目录
            progress_callback: 进度回调 (step_name, current, total, message)
            scene_callback: 场景进度回调 (scene_index, total, message)

        Returns:
            生成结果字典
        """
        if output_dir is None:
            output_dir = self.config.paths.output_dir

        project_dir = get_output_dir(title, output_dir)
        ensure_dir(project_dir)

        scenes = script_data.get('scenes', [])
        meta = script_data.get('meta', {})
        result = {
            'title': title,
            'output_dir': project_dir,
            'scenes': len(scenes),
            'audio_file': None,
            'image_files': [],
            'video_file': None,
            'subtitle_file': None,
            'success': False,
            'errors': []
        }

        # 步骤1: 生成音频
        if progress_callback:
            progress_callback("audio", 0, 1, "生成音频")

        logger.info(f"步骤1/4: 生成音频 ({len(scenes)} 场景)")
        audio_success, audio_path, scene_audio_durations = await self.audio_gen.generate(
            scenes, project_dir,
            progress_callback=lambda c, t, m: (
                progress_callback("audio", c, t, m) if progress_callback else None
            )
        )

        if not audio_success:
            logger.warning("音频生成失败，继续处理（无音频模式）")
            result['errors'].append("音频生成失败")

        result['audio_file'] = audio_path if audio_success else None
        if progress_callback:
            progress_callback("audio", 1, 1, "音频完成")

        # 步骤2: 生成图片
        if progress_callback:
            progress_callback("images", 0, len(scenes), "生成图片")

        logger.info(f"步骤2/4: 生成图片 ({len(scenes)} 场景)")
        image_files = self.image_gen.batch_generate(
            scenes, project_dir, title,
            progress_callback=lambda c, t, m: (
                progress_callback("images", c, t, m) if progress_callback else None
            )
        )
        result['image_files'] = image_files

        if progress_callback:
            progress_callback("images", len(scenes), len(scenes), "图片完成")

        # 步骤3: 合成视频（含字幕）
        if progress_callback:
            progress_callback("video", 0, 100, "合成视频")

        # 计算场景时长
        scene_durations = [s.get('duration_sec', 5) for s in scenes]

        # 视频输出路径
        output_name = title_to_filename(title)
        video_path = os.path.join(project_dir, f"{output_name}.mp4")

        logger.info(f"步骤3/4: 合成视频（含字幕）")
        video_success, final_path = self.video_comp.create(
            audio_file=audio_path if audio_success else "",
            image_files=image_files,
            scene_durations=scene_durations,
            output_file=video_path,
            scenes=scenes,
            scene_audio_durations=scene_audio_durations if audio_success else None,
            progress_callback=lambda c, t, m: (
                progress_callback("video", c, t, m) if progress_callback else None
            )
        )

        if video_success:
            result['video_file'] = final_path
            result['success'] = True
            logger.success(f"视频生成完成: {final_path}")

            # 检查字幕文件
            base_name = os.path.splitext(os.path.basename(final_path))[0]
            srt_path = os.path.join(project_dir, f"{base_name}.srt")
            ass_path = os.path.join(project_dir, f"{base_name}.ass")
            if os.path.exists(srt_path):
                result['subtitle_file'] = srt_path
            elif os.path.exists(ass_path):
                result['subtitle_file'] = ass_path
        else:
            logger.error("视频合成失败")
            result['errors'].append("视频合成失败")

        if progress_callback:
            progress_callback("video", 100, 100, "完成")

        # 保存脚本到输出目录
        from ..utils.file_utils import safe_write_json
        script_path = os.path.join(project_dir, "scripts.json")
        safe_write_json(script_path, script_data)

        return result