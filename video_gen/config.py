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
class CanvasPreset:
    """画布预设"""
    name: str
    width: int
    height: int
    aspect_ratio: str  # "9:16", "16:9", "1:1", "4:3", "3:2"


@dataclass
class ImageConfig:
    """图片生成配置"""
    # 画布配置（支持多比例）
    canvas_presets: Dict[str, CanvasPreset] = field(default_factory=lambda: {
        "vertical_9_16": CanvasPreset("竖屏 9:16", 1080, 1920, "9:16"),
        "horizontal_16_9": CanvasPreset("横屏 16:9", 1920, 1080, "16:9"),
        "square_1_1": CanvasPreset("正方形 1:1", 1080, 1080, "1:1"),
        "landscape_4_3": CanvasPreset("横屏 4:3", 1600, 1200, "4:3"),
        "photo_3_2": CanvasPreset("照片 3:2", 1500, 1000, "3:2"),
    })
    active_preset: str = "vertical_9_16"  # 当前使用的预设
    
    # 自定义尺寸（当 preset 为 custom 时使用）
    custom_width: int = 1080
    custom_height: int = 1920
    
    # API 配置
    api_timeout: int = 60
    min_interval: float = 3.0
    max_interval: float = 15.0
    max_retries: int = 3
    api_key: str = os.environ.get("POLLINATIONS_API_KEY", "")

    @property
    def width(self) -> int:
        """获取当前画布宽度"""
        if self.active_preset == "custom":
            return self.custom_width
        preset = self.canvas_presets.get(self.active_preset)
        return preset.width if preset else 1080

    @property
    def height(self) -> int:
        """获取当前画布高度"""
        if self.active_preset == "custom":
            return self.custom_height
        preset = self.canvas_presets.get(self.active_preset)
        return preset.height if preset else 1920

    @property
    def aspect_ratio(self) -> str:
        """获取当前宽高比"""
        if self.active_preset == "custom":
            return "custom"
        preset = self.canvas_presets.get(self.active_preset)
        return preset.aspect_ratio if preset else "9:16"


# ==================== AI 大模型配置 ====================

@dataclass
class LLMProvider:
    """LLM 服务商配置"""
    name: str = "DeepSeek"
    enabled: bool = True
    api_key: str = ""
    base_url: str = "https://api.deepseek.com"
    model: str = "deepseek-v4-flash"
    temperature: float = 0.7
    max_tokens: int = 4096


@dataclass
class AIConfig:
    """AI 大模型配置"""
    enabled: bool = False
    # 默认使用 DeepSeek
    default_provider: str = "deepseek"
    providers: Dict[str, LLMProvider] = field(default_factory=lambda: {
        "deepseek": LLMProvider(
            name="DeepSeek",
            enabled=True,
            api_key=os.environ.get("DEEPSEEK_API_KEY", ""),
            base_url="https://api.deepseek.com",
            model="deepseek-v4-flash",
        ),
        "openrouter": LLMProvider(
            name="OpenRouter",
            enabled=False,
            api_key=os.environ.get("OPENROUTER_API_KEY", ""),
            base_url="https://openrouter.ai/api/v1",
            model="deepseek/deepseek-chat-v4-flash",
        ),
    })
    # 模块级开关
    modules: Dict[str, bool] = field(default_factory=lambda: {
        "content_generation": False,
        "script_generation": False,
        "prompt_enhancement": False,
    })
    # Prompt 优化风格
    prompt_style: str = "default"  # default, cinematic, anime, realistic, artistic


# ==================== 搜索服务配置 ====================

@dataclass
class SearchConfig:
    """搜索服务配置"""
    serpapi_key: str = os.environ.get("SERPAPI_KEY", "")
    tavily_key: str = os.environ.get("TAVILY_KEY", "")


# ==================== 文生图 API 配置 ====================

@dataclass
class ImageAPIProvider:
    """文生图 API 服务商配置"""
    name: str = "Pollinations (免费)"
    enabled: bool = True
    base_url: str = "https://gen.pollinations.ai/image/"
    api_key: str = ""
    model: str = "flux"


@dataclass
class ImageAPIConfig:
    """文生图 API 多服务商配置"""
    providers: List[ImageAPIProvider] = field(default_factory=lambda: [
        ImageAPIProvider(name="Pollinations (免费)", enabled=True,
                         base_url="https://gen.pollinations.ai/image/",
                         api_key="", model="flux"),
        ImageAPIProvider(name="自定义", enabled=False,
                         base_url="", api_key="", model=""),
    ])
    active_provider: int = 0  # 当前使用的服务商索引


# ==================== 语音合成配置 ====================

@dataclass
class VoiceConfig:
    """语音合成配置"""
    provider: str = "edge-tts"  # edge-tts, custom
    custom_base_url: str = ""
    custom_api_key: str = ""
    custom_model: str = ""


# ==================== 主配置 ====================

@dataclass
class AppConfig:
    """应用主配置"""
    paths: PathConfig = field(default_factory=PathConfig)
    video: VideoEncodingConfig = field(default_factory=VideoEncodingConfig)
    subtitle: SubtitleConfig = field(default_factory=SubtitleConfig)
    audio: AudioConfig = field(default_factory=AudioConfig)
    image: ImageConfig = field(default_factory=ImageConfig)
    ai: AIConfig = field(default_factory=AIConfig)
    search: SearchConfig = field(default_factory=SearchConfig)
    image_api: ImageAPIConfig = field(default_factory=ImageAPIConfig)
    voice: VoiceConfig = field(default_factory=VoiceConfig)

    # 应用设置
    window_width: int = 1200
    window_height: int = 800
    log_level: str = "INFO"
    max_concurrent_tasks: int = 4
    enable_gpu: bool = False  # 自动检测


# 全局单例配置
DEFAULT_CONFIG = AppConfig()