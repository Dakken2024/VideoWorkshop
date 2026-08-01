#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
集中配置管理 - 所有可配置参数统一管理，支持环境变量覆盖
"""

import os
from dataclasses import dataclass, field
from typing import Tuple, Optional, List, Dict


# ==================== 路径配置 ====================

@dataclass
class PathConfig:
    """路径配置"""
    output_dir: str = os.environ.get("VIDEO_GEN_OUTPUT", "./output")
    font_dir: str = os.environ.get("VIDEO_GEN_FONT_DIR", "./fonts")
    subtitle_font: str = os.environ.get("VIDEO_GEN_SUBTITLE_FONT", "")
    status_file: str = ".image_generation_status.json"


# ==================== 视频编码配置 ====================

@dataclass
class VideoEncodingConfig:
    """视频编码配置"""
    fps: int = 30
    crf: int = 23
    preset: str = "slow"
    codec: str = "libx264"
    audio_codec: str = "aac"
    audio_bitrate: str = "128k"
    profile: str = "high"
    level: str = "4.1"
    pixel_format: str = "yuv420p"
    faststart: bool = True
    threads: int = 0

    # 微信视频号优化
    wechat_max_bitrate: int = 6000  # kbps
    wechat_max_file_size_mb: int = 1000


# ==================== 字幕配置 ====================

@dataclass
class SubtitleConfig:
    """字幕配置 - 核心修复模块配置"""
    enabled: bool = True
    font_size: int = 36
    font_color: str = "white"
    stroke_color: str = "black"
    stroke_width: float = 1.5
    position: str = "bottom"  # bottom, top, custom
    custom_position: Tuple[float, float] = (0.5, 0.92)  # relative position
    max_chars_per_line: int = 20
    line_spacing: float = 1.3
    background_opacity: float = 0.0  # 0 = 无背景, 0.5 = 半透明

    # 字幕格式
    output_format: str = "srt"  # srt, ass, embedded

    # 中文字体自动检测
    preferred_fonts: List[str] = field(default_factory=lambda: [
        "Microsoft YaHei", "SimHei", "SimSun", "FangSong",
        "KaiTi", "PingFang SC", "Noto Sans CJK SC",
        "Source Han Sans SC", "WenQuanYi Micro Hei", "Arial"
    ])

    # 自动换行配置
    enable_auto_wrap: bool = True
    wrap_min_chars: int = 8
    wrap_max_chars: int = 30


# ==================== 音频配置 ====================

@dataclass
class AudioConfig:
    """音频配置"""
    voice: str = "zh-CN-XiaoxiaoNeural"
    fallback_voice: str = "zh-CN-YunxiNeural"
    rate: str = "+0%"
    volume: str = "+0%"
    segment_timeout: int = 300  # 秒
    max_retries: int = 3

    # 停顿配置（ms）
    pause_short: int = 300
    pause_medium: int = 500
    pause_long: int = 800
    pause_paragraph: int = 1200


# ==================== 图片生成配置 ====================

@dataclass
class ImageConfig:
    """图片生成配置"""
    width: int = 1080
    height: int = 1920
    api_timeout: int = 60
    min_interval: float = 3.0
    max_interval: float = 15.0
    max_retries: int = 3
    api_key: str = os.environ.get("POLLINATIONS_API_KEY", "pk_WyzA9ElvE2wF2Nqu")


# ==================== 主配置 ====================

@dataclass
class AppConfig:
    """应用主配置"""
    paths: PathConfig = field(default_factory=PathConfig)
    video: VideoEncodingConfig = field(default_factory=VideoEncodingConfig)
    subtitle: SubtitleConfig = field(default_factory=SubtitleConfig)
    audio: AudioConfig = field(default_factory=AudioConfig)
    image: ImageConfig = field(default_factory=ImageConfig)

    # 应用设置
    window_width: int = 1200
    window_height: int = 800
    log_level: str = "INFO"
    max_concurrent_tasks: int = 4
    enable_gpu: bool = False  # 自动检测


# 全局单例配置
DEFAULT_CONFIG = AppConfig()