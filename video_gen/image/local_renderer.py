#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
本地图片渲染器 - 当 API 不可用时的本地备选方案
"""

import os
import random
from PIL import Image, ImageDraw, ImageFilter, ImageEnhance
from typing import Dict, Optional

from ..utils.logger import logger


class LocalImageRenderer:
    """本地图片渲染器 - 生成有意义的占位图"""

    def __init__(self):
        self.scene_themes = {
            1: {'theme': 'cyberpunk', 'colors': ['#00FFFF', '#FF00FF', '#0000FF']},
            2: {'theme': 'victorian', 'colors': ['#8B4513', '#DAA520', '#8B0000']},
            3: {'theme': 'historical', 'colors': ['#2F4F4F', '#808080', '#2F4F4F']},
            4: {'theme': 'steampunk', 'colors': ['#8B4513', '#CD853F', '#D2691E']},
            5: {'theme': 'mechanical', 'colors': ['#C0C0C0', '#A9A9A9', '#808080']},
            6: {'theme': 'visionary', 'colors': ['#4169E1', '#1E90FF', '#00BFFF']},
            7: {'theme': 'nature', 'colors': ['#228B22', '#32CD32', '#006400']},
            8: {'theme': 'abstract', 'colors': ['#FFD700', '#FFA500', '#FF8C00']},
            9: {'theme': 'futuristic', 'colors': ['#9370DB', '#BA55D3', '#DA70D6']},
            10: {'theme': 'minimal', 'colors': ['#2F4F4F', '#696969', '#708090']},
        }

    def render(self, scene_id: int, output_file: str, scene_note: str = None) -> bool:
        """
        渲染本地图片

        Args:
            scene_id: 场景 ID
            output_file: 输出路径
            scene_note: 场景说明

        Returns:
            是否成功
        """
        try:
            width, height = 1080, 1920
            theme = self.scene_themes.get(scene_id % 10 or 10, self.scene_themes[1])

            img = Image.new('RGB', (width, height), color=(20, 20, 30))
            draw = ImageDraw.Draw(img)

            # 应用渐变背景
            self._apply_gradient(draw, width, height, theme['colors'], scene_id)

            # 添加几何装饰
            self._add_geometric_elements(draw, width, height, scene_id)

            # 添加文字（如果有）
            if scene_note:
                try:
                    draw.text((width // 4, height // 2), f"Scene {scene_id}\n{scene_note[:30]}",
                             fill=(255, 255, 255))
                except:
                    pass

            os.makedirs(os.path.dirname(output_file), exist_ok=True)
            img.save(output_file, 'JPEG', quality=90)
            logger.success(f"本地渲染完成: {output_file}")
            return True

        except Exception as e:
            logger.error(f"本地渲染失败: {e}")
            # 创建最基本的占位图
            try:
                img = Image.new('RGB', (1080, 1920), color=(
                    50 + (scene_id * 15) % 100,
                    50 + (scene_id * 25) % 100,
                    50 + (scene_id * 35) % 100
                ))
                os.makedirs(os.path.dirname(output_file), exist_ok=True)
                img.save(output_file, 'JPEG', quality=85)
                return True
            except:
                return False

    def _apply_gradient(self, draw, width, height, colors, scene_id):
        """应用渐变背景"""
        parsed = []
        for c in colors:
            if c.startswith('#'):
                parsed.append(tuple(int(c.lstrip('#')[j:j+2], 16) for j in (0, 2, 4)))
            else:
                parsed.append((100, 100, 100))

        for y in range(height):
            factor = y / height
            if len(parsed) >= 2:
                r1, g1, b1 = parsed[0]
                r2, g2, b2 = parsed[1]
                r = int(r1 * (1 - factor) + r2 * factor)
                g = int(g1 * (1 - factor) + g2 * factor)
                b = int(b1 * (1 - factor) + b2 * factor)
                noise = (hash(str(y) + str(scene_id)) % 21) - 10
                draw.line([(0, y), (width, y)], fill=(
                    max(0, min(255, r + noise)),
                    max(0, min(255, g + noise)),
                    max(0, min(255, b + noise))
                ))

    def _add_geometric_elements(self, draw, width, height, scene_id):
        """添加几何装饰"""
        for i in range(10):
            x = (i * width // 10 + scene_id * 13) % width
            y = (i * height // 10 + scene_id * 17) % height
            size = 20 + (scene_id * 7 + i * 3) % 50
            draw.ellipse([x, y, x + size, y + size],
                        outline=(150, 150, 150, 100), width=2)