#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
字幕生成与嵌入模块 - 核心修复模块

功能:
1. 从脚本 JSON 提取场景文本，计算时间偏移
2. 生成 SRT/ASS 格式字幕文件
3. 使用 MoviePy / FFmpeg 将字幕嵌入视频
4. 自动检测中文字体，支持自动换行
5. 字幕样式自定义（位置、大小、颜色、描边）

解决原系统"无字幕功能"的缺陷，实现字幕自动导入机制。
"""

import os
import re
import math
import subprocess
from typing import List, Dict, Tuple, Optional, Callable
from dataclasses import dataclass
from datetime import timedelta

from ..config import SubtitleConfig, DEFAULT_CONFIG
from ..utils.logger import logger
from ..utils.file_utils import find_available_font, safe_write_text


# ==================== 字幕数据模型 ====================

@dataclass
class SubtitleEntry:
    """单条字幕条目"""
    index: int
    start_time: float  # 秒
    end_time: float    # 秒
    text: str
    scene_id: int = 0

    def to_srt_block(self) -> str:
        """转换为 SRT 格式块"""
        return (
            f"{self.index}\n"
            f"{self._format_time(self.start_time)} --> {self._format_time(self.end_time)}\n"
            f"{self.text}\n\n"
        )

    def to_ass_dialogue(self, style_name: str = "Default") -> str:
        """转换为 ASS 对话行"""
        start = self._format_ass_time(self.start_time)
        end = self._format_ass_time(self.end_time)
        text = self.text.replace('\n', '\\N')
        return f"Dialogue: 0,{start},{end},{style_name},,0,0,0,,{text}\n"

    @staticmethod
    def _format_time(seconds: float) -> str:
        """格式化时间为 SRT 时间戳格式"""
        td = timedelta(seconds=seconds)
        hours = td.seconds // 3600
        minutes = (td.seconds % 3600) // 60
        secs = td.seconds % 60
        millis = td.microseconds // 1000
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"

    @staticmethod
    def _format_ass_time(seconds: float) -> str:
        """格式化时间为 ASS 时间戳格式"""
        td = timedelta(seconds=seconds)
        hours = td.seconds // 3600
        minutes = (td.seconds % 3600) // 60
        secs = td.seconds % 60
        centiseconds = td.microseconds // 10000
        return f"{hours}:{minutes:02d}:{secs:02d}.{centiseconds:02d}"


# ==================== 字幕生成器 ====================

class SubtitleGenerator:
    """
    字幕生成器 - 从场景脚本生成时间轴对齐的字幕

    核心流程:
    1. 解析场景文本
    2. 根据音频时长或预设时长计算每场景的时间偏移
    3. 自动换行处理
    4. 生成 SRT 或 ASS 格式字幕文件
    """

    def __init__(self, config: Optional[SubtitleConfig] = None):
        self.config = config or DEFAULT_CONFIG.subtitle
        self._detected_font = None

    def detect_font(self) -> Optional[str]:
        """自动检测可用中文字体"""
        if self.config.preferred_fonts:
            font = find_available_font(self.config.preferred_fonts)
            if font:
                self._detected_font = font
                logger.info(f"检测到中文字体: {font}")
                return font
        logger.warning("未检测到中文字体，字幕渲染可能异常")
        return None

    def generate_from_scenes(
        self,
        scenes: List[Dict],
        audio_duration: Optional[float] = None,
        scene_audio_durations: Optional[List[float]] = None
    ) -> List[SubtitleEntry]:
        """
        从场景列表生成字幕条目

        Args:
            scenes: 场景列表，每个包含 text, duration_sec 等字段
            audio_duration: 总音频时长（秒），如有则按比例分配
            scene_audio_durations: 每场景音频时长列表（秒），精确对齐

        Returns:
            字幕条目列表
        """
        if not scenes:
            logger.warning("场景列表为空，无法生成字幕")
            return []

        if scene_audio_durations:
            # 精确时间轴对齐
            return self._generate_with_exact_timing(scenes, scene_audio_durations)
        elif audio_duration:
            # 按比例分配
            return self._generate_with_proportional_timing(scenes, audio_duration)
        else:
            # 使用预设时长
            return self._generate_with_preset_timing(scenes)

    def _generate_with_exact_timing(
        self, scenes: List[Dict], scene_audio_durations: List[float]
    ) -> List[SubtitleEntry]:
        """使用精确的场景音频时长生成字幕"""
        entries = []
        current_time = 0.0
        index = 1

        for i, scene in enumerate(scenes):
            text = scene.get('text', '').strip()
            if not text:
                current_time += scene_audio_durations[i] if i < len(scene_audio_durations) else 3.0
                continue

            duration = scene_audio_durations[i] if i < len(scene_audio_durations) else 3.0
            scene_id = scene.get('scene_id', i + 1)

            # 对长文本进行分句（按句号分割）
            sub_texts = self._split_text(text)
            if len(sub_texts) > 1:
                # 多句字幕：按比例分配时间
                total_chars = len(text)
                sub_start = current_time
                for sub_text in sub_texts:
                    if not sub_text.strip():
                        continue
                    # 按字符比例分配时长
                    char_ratio = len(sub_text) / max(total_chars, 1)
                    sub_duration = duration * char_ratio
                    sub_end = sub_start + sub_duration

                    # 确保最小显示时间 0.5 秒
                    if sub_duration < 0.5:
                        sub_end = sub_start + 0.5

                    wrapped_text = self._auto_wrap(sub_text.strip())
                    entries.append(SubtitleEntry(
                        index=index,
                        start_time=sub_start,
                        end_time=sub_end,
                        text=wrapped_text,
                        scene_id=scene_id
                    ))
                    index += 1
                    sub_start = sub_end
            else:
                # 单句字幕
                wrapped_text = self._auto_wrap(text)
                entries.append(SubtitleEntry(
                    index=index,
                    start_time=current_time,
                    end_time=current_time + duration,
                    text=wrapped_text,
                    scene_id=scene_id
                ))
                index += 1

            current_time += duration

        logger.info(f"生成 {len(entries)} 条字幕（精确时间轴）")
        return entries

    def _generate_with_proportional_timing(
        self, scenes: List[Dict], audio_duration: float
    ) -> List[SubtitleEntry]:
        """按音频总时长比例分配时间"""
        # 先计算总预设时长
        total_preset = sum(s.get('duration_sec', 5) for s in scenes)
        if total_preset <= 0:
            total_preset = len(scenes) * 5

        # 计算每场景的实际时长
        scene_durations = []
        for s in scenes:
            ratio = s.get('duration_sec', 5) / total_preset
            scene_durations.append(audio_duration * ratio)

        return self._generate_with_exact_timing(scenes, scene_durations)

    def _generate_with_preset_timing(
        self, scenes: List[Dict]
    ) -> List[SubtitleEntry]:
        """使用预设时长生成"""
        scene_durations = [s.get('duration_sec', 5) for s in scenes]
        return self._generate_with_exact_timing(scenes, scene_durations)

    def _split_text(self, text: str) -> List[str]:
        """将长文本按标点符号分割为短句"""
        # 按句号、问号、感叹号、分句
        sentences = re.split(r'([。！？；.!?;])', text)
        result = []
        buffer = ""
        for part in sentences:
            buffer += part
            if part in ['。', '！', '？', '；', '.', '!', '?', ';'] and buffer.strip():
                result.append(buffer.strip())
                buffer = ""
        if buffer.strip():
            result.append(buffer.strip())
        # 如果分割结果太多，合并过短的句子
        merged = []
        for s in result:
            if merged and len(merged[-1] + s) < self.config.max_chars_per_line * 2:
                merged[-1] = merged[-1] + s
            else:
                merged.append(s)
        return merged if merged else [text]

    def _auto_wrap(self, text: str) -> str:
        """自动换行 - 确保每行不超过最大字符数"""
        if not self.config.enable_auto_wrap:
            return text

        max_chars = self.config.max_chars_per_line
        if len(text) <= max_chars:
            return text

        # 在标点符号或自然断点处换行
        wrapped_lines = []
        current_line = ""

        for char in text:
            current_line += char
            if len(current_line) >= max_chars:
                # 尝试在最后一个空格或标点处断开
                break_points = [',', '，', ' ', '、', '；', '：', '）', '】', '」']
                for bp in break_points:
                    pos = current_line.rfind(bp, len(current_line) // 2)
                    if pos > 0:
                        wrapped_lines.append(current_line[:pos + 1])
                        current_line = current_line[pos + 1:]
                        break
                else:
                    # 没有合适断点，硬切
                    wrapped_lines.append(current_line)
                    current_line = ""

        if current_line.strip():
            wrapped_lines.append(current_line)

        return '\n'.join(wrapped_lines)

    def generate_srt(self, entries: List[SubtitleEntry], output_path: str) -> bool:
        """生成 SRT 字幕文件"""
        try:
            content = ""
            for entry in entries:
                content += entry.to_srt_block()
            return safe_write_text(output_path, content)
        except Exception as e:
            logger.error(f"生成 SRT 文件失败: {e}")
            return False

    def generate_ass(self, entries: List[SubtitleEntry], output_path: str,
                     video_resolution: Tuple[int, int] = (1080, 1920)) -> bool:
        """生成 ASS 字幕文件（支持更丰富的样式）"""
        try:
            width, height = video_resolution
            font_name = self._detected_font or "Arial"
            font_size = self.config.font_size

            # 计算位置
            if self.config.position == "bottom":
                margin_v = int(height * 0.08)
                alignment = 2  # 底部居中
            elif self.config.position == "top":
                margin_v = int(height * 0.05)
                alignment = 8  # 顶部居中
            else:
                margin_v = int(height * (1 - self.config.custom_position[1]))
                alignment = 2

            margin_h = int(width * 0.05)

            # 构建 ASS 文件内容
            ass_content = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {width}
PlayResY: {height}
WrapStyle: 1
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{font_name},{font_size},&H00FFFFFF,&H000000FF,&H{self._get_color_hex(self.config.stroke_color)},&H00000000,0,0,0,0,100,100,0,0,1,{self.config.stroke_width:.1f},0,{alignment},{margin_h},{margin_h},{margin_v},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
            for entry in entries:
                ass_content += entry.to_ass_dialogue()

            return safe_write_text(output_path, ass_content)
        except Exception as e:
            logger.error(f"生成 ASS 文件失败: {e}")
            return False

    def _get_color_hex(self, color_name: str) -> str:
        """获取颜色十六进制值（ASS格式：AABBGGRR）"""
        color_map = {
            "black": "000000",
            "white": "FFFFFF",
            "red": "0000FF",
            "green": "00FF00",
            "blue": "FF0000",
            "yellow": "00FFFF",
            "cyan": "FFFF00",
            "magenta": "FF00FF",
            "gray": "808080",
            "grey": "808080",
        }
        hex_color = color_map.get(color_name.lower(), "000000")
        # ASS 格式需要 BGR 顺序
        if len(hex_color) == 6:
            return f"{hex_color[4:6]}{hex_color[2:4]}{hex_color[0:2]}"
        return "000000"


# ==================== 字幕嵌入器 ====================

class SubtitleEmbedder:
    """
    字幕嵌入器 - 将字幕文件嵌入视频

    支持两种方式：
    1. MoviePy TextClip：直接渲染字幕到视频帧（适合简短字幕）
    2. FFmpeg 滤镜：使用 FFmpeg subtitles 滤镜嵌入（推荐，支持 ASS 样式）
    """

    def __init__(self, config: Optional[SubtitleConfig] = None):
        self.config = config or DEFAULT_CONFIG.subtitle

    def embed_with_ffmpeg(self, video_path: str, subtitle_path: str,
                          output_path: str, progress_callback: Optional[Callable] = None) -> bool:
        """
        使用 FFmpeg 将字幕嵌入视频

        Args:
            video_path: 输入视频路径
            subtitle_path: 字幕文件路径（SRT 或 ASS）
            output_path: 输出视频路径
            progress_callback: 进度回调

        Returns:
            是否成功
        """
        try:
            # 判断字幕格式
            if subtitle_path.lower().endswith('.ass'):
                filter_str = f"ass='{subtitle_path.replace('\\', '/')}'"
            else:
                filter_str = f"subtitles='{subtitle_path.replace('\\', '/')}'"

            cmd = [
                'ffmpeg', '-y',
                '-i', video_path,
                '-vf', filter_str,
                '-c:v', 'libx264',
                '-preset', 'slow',
                '-crf', '23',
                '-c:a', 'copy',
                '-movflags', '+faststart',
                output_path
            ]

            logger.info(f"执行 FFmpeg 字幕嵌入命令")
            logger.debug(f"  {' '.join(cmd)}")

            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True
            )

            # 解析进度
            duration = 0
            for line in process.stderr:
                if progress_callback:
                    # 解析 FFmpeg 进度
                    time_match = re.search(r'time=(\d+):(\d+):(\d+)\.(\d+)', line)
                    if time_match:
                        h, m, s, ms = map(int, time_match.groups())
                        current_time = h * 3600 + m * 60 + s + ms / 100
                        if duration > 0:
                            progress = min(int(current_time / duration * 100), 99)
                            progress_callback(progress, 100, f"嵌入字幕 {progress}%")

            process.wait()
            success = process.returncode == 0 and os.path.exists(output_path)

            if success:
                logger.success(f"字幕嵌入完成: {output_path}")
            else:
                logger.error(f"FFmpeg 字幕嵌入失败，返回码: {process.returncode}")

            return success

        except FileNotFoundError:
            logger.error("FFmpeg 未找到，请确保已安装 FFmpeg 并添加到 PATH")
            return False
        except Exception as e:
            logger.error(f"字幕嵌入异常: {e}")
            return False

    def get_available_font_for_moviepy(self) -> Optional[str]:
        """获取 MoviePy 可用的字体"""
        font = find_available_font(self.config.preferred_fonts)
        if font and os.path.exists(font):
            return font
        # 尝试 Windows 字体目录
        windir = os.environ.get('WINDIR', 'C:\\Windows')
        yahei = os.path.join(windir, 'Fonts', 'msyh.ttc')
        if os.path.exists(yahei):
            return yahei
        return None


# ==================== 字幕管理器（统一接口） ====================

class SubtitleManager:
    """
    字幕管理器 - 统一字幕生成和嵌入接口

    提供一键式字幕处理流程：
    1. 从场景脚本生成字幕条目
    2. 生成 SRT/ASS 字幕文件
    3. 将字幕嵌入视频
    """

    def __init__(self, config: Optional[SubtitleConfig] = None):
        self.config = config or DEFAULT_CONFIG.subtitle
        self.generator = SubtitleGenerator(config)
        self.embedder = SubtitleEmbedder(config)

    def process(self, scenes: List[Dict], video_path: str, output_path: str,
                audio_duration: Optional[float] = None,
                scene_audio_durations: Optional[List[float]] = None,
                progress_callback: Optional[Callable] = None) -> bool:
        """
        完整字幕处理流程

        Args:
            scenes: 场景列表
            video_path: 输入视频（无字幕）
            output_path: 输出视频（含字幕）
            audio_duration: 音频总时长
            scene_audio_durations: 每场景音频时长
            progress_callback: 进度回调

        Returns:
            是否成功
        """
        if not self.config.enabled:
            logger.info("字幕功能已禁用，跳过")
            return False

        # 步骤1：检测字体
        if progress_callback:
            progress_callback(10, 100, "检测中文字体")
        self.generator.detect_font()

        # 步骤2：生成字幕条目
        if progress_callback:
            progress_callback(25, 100, "生成字幕内容")
        entries = self.generator.generate_from_scenes(
            scenes, audio_duration, scene_audio_durations
        )
        if not entries:
            logger.warning("未生成字幕条目")
            return False

        # 步骤3：生成字幕文件
        if progress_callback:
            progress_callback(40, 100, "生成字幕文件")

        # 输出到视频同目录
        base_dir = os.path.dirname(output_path)
        base_name = os.path.splitext(os.path.basename(output_path))[0]

        if self.config.output_format == "ass":
            subtitle_path = os.path.join(base_dir, f"{base_name}.ass")
            success = self.generator.generate_ass(entries, subtitle_path)
        else:
            subtitle_path = os.path.join(base_dir, f"{base_name}.srt")
            success = self.generator.generate_srt(entries, subtitle_path)

        if not success:
            logger.error("生成字幕文件失败")
            return False

        logger.success(f"字幕文件已生成: {subtitle_path}")

        # 步骤4：嵌入字幕
        if progress_callback:
            progress_callback(60, 100, "嵌入字幕到视频")

        if self.config.output_format == "embedded":
            # 使用 ASS 格式嵌入（支持样式）
            ass_path = subtitle_path.replace('.srt', '.ass')
            self.generator.generate_ass(entries, ass_path)
            return self.embedder.embed_with_ffmpeg(
                video_path, ass_path, output_path, progress_callback
            )
        else:
            return self.embedder.embed_with_ffmpeg(
                video_path, subtitle_path, output_path, progress_callback
            )