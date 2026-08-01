#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文件操作工具 - 统一的文件读写、路径管理、状态持久化
"""

import os
import json
import re
import hashlib
from datetime import datetime
from typing import Dict, Any, Optional, List, Tuple


def ensure_dir(path: str) -> str:
    """确保目录存在，返回规范路径"""
    path = os.path.normpath(path)
    os.makedirs(path, exist_ok=True)
    return path


def safe_read_json(path: str) -> Optional[Dict[str, Any]]:
    """安全读取 JSON 文件"""
    try:
        if not os.path.exists(path):
            return None
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError, PermissionError) as e:
        return None


def safe_write_json(path: str, data: Any, pretty: bool = True) -> bool:
    """安全写入 JSON 文件"""
    try:
        ensure_dir(os.path.dirname(path))
        with open(path, 'w', encoding='utf-8') as f:
            if pretty:
                json.dump(data, f, ensure_ascii=False, indent=2)
            else:
                json.dump(data, f, ensure_ascii=False)
        return True
    except (IOError, PermissionError, TypeError) as e:
        return False


def safe_read_text(path: str) -> Optional[str]:
    """安全读取文本文件"""
    try:
        if not os.path.exists(path):
            return None
        with open(path, 'r', encoding='utf-8') as f:
            return f.read()
    except (IOError, PermissionError) as e:
        return None


def safe_write_text(path: str, content: str) -> bool:
    """安全写入文本文件"""
    try:
        ensure_dir(os.path.dirname(path))
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        return True
    except (IOError, PermissionError) as e:
        return False


def title_to_filename(title: str) -> str:
    """将中文标题转换为拼音文件名"""
    try:
        import pypinyin
        pinyin_list = pypinyin.lazy_pinyin(title, style=pypinyin.Style.NORMAL)
        clean = re.sub(r'[^a-zA-Z0-9_]', '_', '_'.join(pinyin_list))
        clean = re.sub(r'_+', '_', clean).strip('_')
        return clean if clean else "untitled_video"
    except ImportError:
        # 降级处理
        english_chars = re.sub(r'[^\w\s]', '', title)
        clean = re.sub(r'\s+', '_', english_chars.strip())
        clean = clean.strip('_')
        return clean if clean else "untitled_video"


def get_output_path(title: str, output_dir: str, filename: str) -> str:
    """获取标准输出路径"""
    folder_name = title_to_filename(title)
    month_dir = datetime.now().strftime("%Y%m")
    full_dir = ensure_dir(os.path.join(output_dir, month_dir, folder_name))
    return os.path.join(full_dir, filename)


def get_output_dir(title: str, output_dir: str) -> str:
    """获取标准输出目录"""
    folder_name = title_to_filename(title)
    month_dir = datetime.now().strftime("%Y%m")
    return ensure_dir(os.path.join(output_dir, month_dir, folder_name))


def find_available_font(preferred_fonts: List[str]) -> Optional[str]:
    """自动检测系统中可用的中文字体"""
    import subprocess

    try:
        result = subprocess.run(
            ['fc-list', ':lang=zh'],
            capture_output=True, text=True, timeout=5
        )
        available = result.stdout.lower()
        for font in preferred_fonts:
            if font.lower() in available:
                return font
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    # Windows 系统字体检测
    for font in preferred_fonts:
        font_path = os.path.join(
            os.environ.get('WINDIR', 'C:\\Windows'),
            'Fonts',
            f'{font}.ttf'
        )
        alt_paths = [
            os.path.join(os.environ.get('WINDIR', 'C:\\Windows'), 'Fonts', f'{font}.ttc'),
            f'C:\\Windows\\Fonts\\{font}.ttf',
            f'C:\\Windows\\Fonts\\{font}.ttc',
        ]
        for path in [font_path] + alt_paths:
            if os.path.exists(path):
                return path

    return None


class ImageGenerationState:
    """图片生成状态管理器 - 持久化到文件"""

    def __init__(self, status_file: str = ".image_generation_status.json"):
        self.status_file = status_file
        self._state: Dict[str, bool] = {}
        self._load()

    def _load(self):
        """从文件加载状态"""
        data = safe_read_json(self.status_file)
        if data:
            self._state = data

    def _save(self):
        """保存状态到文件"""
        safe_write_json(self.status_file, self._state)

    def is_generated(self, project_name: str, scene_index: int) -> bool:
        """检查场景是否已生成"""
        key = f"{project_name}|{scene_index}"
        return self._state.get(key, False)

    def mark(self, project_name: str, scene_index: int, success: bool = True):
        """标记场景生成状态"""
        key = f"{project_name}|{scene_index}"
        self._state[key] = success
        self._save()

    def clear_project(self, project_name: str):
        """清除项目所有状态"""
        keys_to_remove = [k for k in self._state if k.startswith(f"{project_name}|")]
        for k in keys_to_remove:
            del self._state[k]
        self._save()

    def clear_all(self):
        """清除所有状态"""
        self._state.clear()
        self._save()