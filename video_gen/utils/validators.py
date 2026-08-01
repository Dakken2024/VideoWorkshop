#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
输入验证工具 - 确保 JSON 脚本、文件路径、配置参数的有效性
"""

import json
import os
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass


@dataclass
class ValidationResult:
    """验证结果"""
    is_valid: bool
    errors: List[str] = None
    warnings: List[str] = None
    data: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        if self.errors is None:
            self.errors = []
        if self.warnings is None:
            self.warnings = []


def validate_script(script_content: str) -> ValidationResult:
    """验证视频脚本 JSON 格式"""
    result = ValidationResult(is_valid=True)

    try:
        data = json.loads(script_content)
    except json.JSONDecodeError as e:
        return ValidationResult(
            is_valid=False,
            errors=[f"JSON 解析错误: {e}"]
        )

    # 检查 meta 字段
    meta = data.get('meta', {})
    if not meta.get('title'):
        result.warnings.append("缺少 meta.title 字段")

    # 检查 scenes 字段
    scenes = data.get('scenes', [])
    if not scenes:
        result.errors.append("scenes 为空，至少需要一个场景")
        return ValidationResult(is_valid=False, errors=result.errors, data=data)

    for i, scene in enumerate(scenes):
        scene_errors = _validate_scene(scene, i)
        result.errors.extend(scene_errors)

    if result.errors:
        result.is_valid = False

    result.data = data
    return result


def _validate_scene(scene: Dict[str, Any], index: int) -> List[str]:
    """验证单个场景"""
    errors = []
    if not scene.get('text', '').strip():
        errors.append(f"场景 {index + 1}: text 字段为空")
    if not scene.get('prompt', '').strip():
        errors.append(f"场景 {index + 1}: prompt 字段为空")
    if scene.get('duration_sec', 0) <= 0:
        errors.append(f"场景 {index + 1}: duration_sec 必须大于 0")
    return errors


def validate_image_file(path: str, min_size: int = 10240) -> bool:
    """验证图片文件有效性"""
    if not os.path.exists(path):
        return False
    if os.path.getsize(path) < min_size:
        return False
    # 检查文件头
    try:
        with open(path, 'rb') as f:
            header = f.read(4)
        return header.startswith(b'\xff\xd8') or header.startswith(b'\x89PNG') or header.startswith(b'RIFF')
    except IOError:
        return False


def validate_audio_file(path: str, min_size: int = 1000) -> bool:
    """验证音频文件有效性"""
    if not os.path.exists(path):
        return False
    if os.path.getsize(path) < min_size:
        return False
    return True


def validate_config(config: Dict[str, Any]) -> ValidationResult:
    """验证配置参数"""
    result = ValidationResult(is_valid=True)

    # 分辨率检查
    width = config.get('width', 1080)
    height = config.get('height', 1920)
    if width <= 0 or height <= 0:
        result.errors.append("分辨率必须大于 0")

    # 帧率检查
    fps = config.get('fps', 30)
    if fps not in [24, 25, 30, 48, 50, 60]:
        result.warnings.append(f"非常规帧率: {fps}fps")

    # CRF 检查
    crf = config.get('crf', 23)
    if crf < 0 or crf > 51:
        result.errors.append(f"CRF 值无效: {crf}（有效范围 0-51）")

    if result.errors:
        result.is_valid = False

    return result