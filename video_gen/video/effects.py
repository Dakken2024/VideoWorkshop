#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
视频特效模块 - Ken Burns 效果、淡入淡出、转场
"""

from typing import Tuple, Optional, Callable
import numpy as np
from PIL import Image


def apply_ken_burns_effect(frame: Image.Image, progress: float,
                           zoom_range: Tuple[float, float] = (1.0, 1.15),
                           pan_range: Tuple[float, float] = (0.0, 0.05)) -> Image.Image:
    """
    Ken Burns 效果 - 缓慢缩放和移动

    Args:
        frame: 输入图片
        progress: 进度 0.0-1.0
        zoom_range: 缩放范围 (起始, 结束)
        pan_range: 平移范围 (起始, 结束)

    Returns:
        处理后的图片
    """
    width, height = frame.size
    zoom = zoom_range[0] + (zoom_range[1] - zoom_range[0]) * progress
    pan_x = int(width * pan_range[0] + (pan_range[1] - pan_range[0]) * progress * width)

    new_width = int(width / zoom)
    new_height = int(height / zoom)

    # 裁剪并缩放
    x = (width - new_width) // 2 + pan_x
    y = (height - new_height) // 2
    x = max(0, min(x, width - new_width))
    y = max(0, min(y, height - new_height))

    cropped = frame.crop((x, y, x + new_width, y + new_height))
    return cropped.resize((width, height), Image.Resampling.LANCZOS)


def create_fade_frames(frame1: Image.Image, frame2: Image.Image,
                       steps: int) -> list:
    """创建淡入淡出过渡帧"""
    frames = []
    for i in range(steps):
        alpha = i / steps
        blended = Image.blend(frame1, frame2, alpha)
        frames.append(blended)
    return frames