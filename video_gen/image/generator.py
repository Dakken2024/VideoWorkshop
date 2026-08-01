#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一图片生成器 - API 优先，本地渲染备选
"""

import os
from typing import Dict, Optional, List, Callable

from ..config import ImageConfig, DEFAULT_CONFIG
from ..utils.logger import logger
from ..utils.file_utils import ensure_dir, ImageGenerationState
from .api_client import ImageAPIClient
from .local_renderer import LocalImageRenderer


class ImageGenerator:
    """
    统一图片生成器

    策略：
    1. API 生成（pollinations.ai）
    2. 本地渲染（Pillow）
    3. 纯色占位图（最后保障）
    """

    def __init__(self, config: ImageConfig = None):
        self.config = config or DEFAULT_CONFIG.image
        self.api_client = ImageAPIClient(config)
        self.local_renderer = LocalImageRenderer()
        self.state = ImageGenerationState()

    def generate(self, prompt: str, output_file: str, scene_id: int = None,
                 scene_note: str = None, seed: int = None,
                 force: bool = False) -> bool:
        """
        生成单个图片

        Args:
            prompt: 提示词
            output_file: 输出路径
            scene_id: 场景 ID
            scene_note: 场景说明
            seed: 随机种子
            force: 是否强制重新生成

        Returns:
            是否成功
        """
        # 检查文件是否已存在
        if not force and os.path.exists(output_file) and os.path.getsize(output_file) > 10240:
            return True

        ensure_dir(os.path.dirname(output_file))

        # 策略1: API 生成
        if self.api_client.generate(prompt, output_file, scene_id, seed):
            return True

        # 策略2: 本地渲染
        if scene_id is not None:
            if self.local_renderer.render(scene_id, output_file, scene_note):
                return True

        # 策略3: 纯色占位图
        try:
            from PIL import Image
            img = Image.new('RGB', (self.config.width, self.config.height),
                          color=(50, 50, 60))
            img.save(output_file, 'JPEG', quality=85)
            logger.warning(f"使用纯色占位图: {output_file}")
            return True
        except:
            return False

    def batch_generate(self, scenes: List[Dict], output_dir: str,
                       project_name: str = None,
                       progress_callback: Optional[Callable] = None) -> List[str]:
        """
        批量生成图片

        Args:
            scenes: 场景列表
            output_dir: 输出目录
            project_name: 项目名称（用于状态跟踪）
            progress_callback: 进度回调 (current, total, message)

        Returns:
            图片文件路径列表
        """
        ensure_dir(output_dir)
        image_files = []
        total = len(scenes)

        for i, scene in enumerate(scenes):
            prompt = scene.get('prompt', '')
            scene_id = scene.get('scene_id', i + 1)
            scene_note = scene.get('note', '')
            image_path = os.path.join(output_dir, f"scene_{i:03d}.jpg")

            if progress_callback:
                progress_callback(i + 1, total, f"生成图片: 场景 {scene_id}")

            logger.info(f"场景 {scene_id}: 生成图片")
            success = self.generate(prompt, image_path, scene_id, scene_note)

            if success:
                image_files.append(image_path)
                if project_name:
                    self.state.mark(project_name, i, True)
            else:
                logger.warning(f"场景 {scene_id}: 图片生成失败")
                image_files.append(image_path)  # 即使失败也添加路径

        logger.success(f"批量生成完成: {len(image_files)}/{total}")
        return image_files