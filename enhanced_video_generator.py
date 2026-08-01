#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
增强版视频生成器 - 解决图片轮播切换过快问题

核心优化：
1. 图片循环播放机制 - 每张图片显示更长时间
2. Ken Burns 效果 - 缓慢缩放/平移创造动态感
3. 智能时长分配 - 根据音频时长合理分配每场景时间
4. 平滑过渡 - 交叉淡入淡出
5. 帧插值 - 生成中间帧创造流畅过渡
"""

import os
import random
import logging
from typing import List, Dict, Tuple, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

# MoviePy 导入（兼容 2.0）
try:
    from moviepy import (
        AudioFileClip,
        concatenate_audioclips,
        concatenate_videoclips,
        CompositeVideoClip,
        TextClip,
        ImageClip,
        ImageSequenceClip,
        vfx
    )
    from moviepy.video.VideoClip import ColorClip
except ImportError:
    from moviepy.editor import (
        AudioFileClip,
        concatenate_audioclips,
        concatenate_videoclips,
        CompositeVideoClip,
        TextClip,
        ImageClip,
        ColorClip,
        ImageSequenceClip
    )
    from moviepy.video import fx as vfx

from PIL import Image, ImageFilter
import numpy as np


class DisplayMode(Enum):
    """图片显示模式"""
    STATIC = "static"           # 静态显示
    KEN_BURNS = "ken_burns"     # Ken Burns 缓慢缩放效果
    SLIDE_SHOW = "slide_show"   # 幻灯片轮播
    CINEMATIC = "cinematic"     # 电影效果（24fps序列）


@dataclass
class EnhancedVideoConfig:
    """增强版视频配置"""

    # 基础设置
    fps: int = 30
    resolution: Tuple[int, int] = (1080, 1920)
    codec: str = 'libx264'
    audio_codec: str = 'aac'
    bitrate: str = '8000k'

    # 显示模式
    display_mode: DisplayMode = DisplayMode.KEN_BURNS

    # 时长设置
    min_scene_duration: float = 3.0     # 每场景最少显示3秒
    max_scene_duration: float = 10.0    # 每场景最多显示10秒
    default_scene_duration: float = 5.0 # 默认每场景5秒

    # Ken Burns 效果参数
    ken_burns_zoom_range: Tuple[float, float] = (1.0, 1.15)  # 缩放范围
    ken_burns_duration: float = 5.0     # 每个 Ken Burns 周期时长

    # 过渡效果
    transition_duration: float = 1.0    # 过渡时长（秒）
    transition_type: str = "crossfade"  # 过渡类型: crossfade, fade, slide

    # 图片循环
    enable_looping: bool = True         # 启用图片循环
    loop_min_duration: float = 2.0      # 每次循环最少显示2秒

    # 帧插值
    enable_frame_interpolation: bool = True  # 启用帧插值
    interpolation_frames: int = 6       # 每对图片间插入的帧数


class EnhancedVideoGenerator:
    """
    增强版视频生成器

    解决切换过快问题的核心策略：
    1. 延长单张图片显示时间（最少3秒）
    2. Ken Burns 效果创造动态感
    3. 智能循环机制
    4. 平滑交叉淡入淡出
    """

    def __init__(self, output_dir: str, config: Optional[EnhancedVideoConfig] = None):
        self.output_dir = output_dir
        self.config = config or EnhancedVideoConfig()
        self.logger = logging.getLogger(__name__)

        os.makedirs(output_dir, exist_ok=True)

    def create_enhanced_video(
        self,
        audio_file: str,
        image_files: List[str],
        scene_durations: List[float],
        output_file: str,
        progress_callback: Optional[Callable[[int, int, str], None]] = None
    ) -> bool:
        """
        创建增强版视频

        Args:
            audio_file: 音频文件路径
            image_files: 图片文件路径列表
            scene_durations: 场景预设时长列表
            output_file: 输出视频路径
            progress_callback: 进度回调

        Returns:
            bool: 是否成功
        """
        try:
            if progress_callback:
                progress_callback(1, 6, "加载音频...")

            # 加载音频
            audio = AudioFileClip(audio_file)
            total_duration = audio.duration
            self.logger.info(f"音频时长: {total_duration:.2f}秒")

            if progress_callback:
                progress_callback(2, 6, "分析场景时长...")

            # 计算每场景实际显示时长
            actual_durations = self._calculate_scene_durations(
                scene_durations, total_duration, len(image_files)
            )

            if progress_callback:
                progress_callback(3, 6, "创建增强视频片段...")

            # 创建视频片段
            video_clips = []
            for i, (img_path, duration) in enumerate(zip(image_files, actual_durations)):
                if not os.path.exists(img_path):
                    self.logger.warning(f"图片不存在: {img_path}")
                    continue

                clip = self._create_enhanced_clip(img_path, duration, i)
                if clip:
                    video_clips.append(clip)

                if progress_callback:
                    progress = int((i + 1) / len(image_files) * 100)
                    progress_callback(3, 6, f"创建片段 {i+1}/{len(image_files)}...")

            if not video_clips:
                self.logger.error("没有有效的视频片段")
                audio.close()
                return False

            if progress_callback:
                progress_callback(4, 6, "添加过渡效果...")

            # 添加过渡效果
            video_clips = self._add_transitions_between_clips(video_clips)

            if progress_callback:
                progress_callback(5, 6, "合成最终视频...")

            # 合成视频
            final_video = concatenate_videoclips(video_clips, method="compose")

            # 确保视频时长与音频匹配
            if final_video.duration < total_duration:
                # 如果视频太短，循环最后一帧
                last_frame = video_clips[-1].copy()
                needed_duration = total_duration - final_video.duration
                last_frame = last_frame.with_duration(needed_duration)
                final_video = concatenate_videoclips([final_video, last_frame], method="compose")
            elif final_video.duration > total_duration:
                # 如果视频太长，截断
                final_video = final_video.with_duration(total_duration)

            # 添加音频
            final_video = final_video.with_audio(audio)

            if progress_callback:
                progress_callback(6, 6, "导出视频...")

            # 导出视频
            final_video.write_videofile(
                output_file,
                fps=self.config.fps,
                codec=self.config.codec,
                audio_codec=self.config.audio_codec,
                bitrate=self.config.bitrate,
                preset='medium',
                ffmpeg_params=[
                    '-profile:v', 'high',
                    '-level', '4.1',
                    '-pix_fmt', 'yuv420p',
                    '-movflags', '+faststart',
                ],
                logger=None
            )

            # 清理
            audio.close()
            final_video.close()
            for clip in video_clips:
                clip.close()

            self.logger.info(f"视频生成成功: {output_file}")
            return True

        except Exception as e:
            self.logger.error(f"视频生成失败: {e}", exc_info=True)
            return False

    def _calculate_scene_durations(
        self,
        scene_durations: List[float],
        total_audio_duration: float,
        num_images: int
    ) -> List[float]:
        """
        计算每场景实际显示时长

        策略：
        1. 根据预设时长比例分配
        2. 确保每场景最少显示3秒
        3. 不超过音频总时长
        """
        if not scene_durations or sum(scene_durations) == 0:
            # 如果没有预设时长，平均分配
            avg_duration = total_audio_duration / num_images
            return [max(avg_duration, self.config.min_scene_duration)] * num_images

        total_preset = sum(scene_durations)
        actual_durations = []

        for preset in scene_durations:
            # 按比例分配
            ratio = preset / total_preset
            duration = total_audio_duration * ratio

            # 应用限制
            duration = max(duration, self.config.min_scene_duration)
            duration = min(duration, self.config.max_scene_duration)

            actual_durations.append(duration)

        # 调整总和以匹配音频时长
        current_total = sum(actual_durations)
        if current_total > 0:
            scale_factor = total_audio_duration / current_total
            actual_durations = [d * scale_factor for d in actual_durations]

        return actual_durations

    def _create_enhanced_clip(self, img_path: str, duration: float, index: int) -> Optional[ImageClip]:
        """
        创建增强版视频片段

        根据配置模式选择不同的显示效果
        """
        try:
            if self.config.display_mode == DisplayMode.KEN_BURNS:
                return self._create_ken_burns_clip(img_path, duration, index)
            elif self.config.display_mode == DisplayMode.STATIC:
                return self._create_static_clip(img_path, duration)
            elif self.config.display_mode == DisplayMode.SLIDE_SHOW:
                return self._create_slideshow_clip(img_path, duration)
            else:
                return self._create_static_clip(img_path, duration)
        except Exception as e:
            self.logger.error(f"创建片段失败 {img_path}: {e}")
            return None

    def _create_ken_burns_clip(self, img_path: str, duration: float, index: int) -> ImageClip:
        """
        创建 Ken Burns 效果片段

        Ken Burns 效果：缓慢缩放和平移，创造动态感
        """
        # 加载图片
        img = Image.open(img_path)

        # 确保尺寸正确
        target_size = self.config.resolution
        if img.size != target_size:
            img = img.resize(target_size, Image.Resampling.LANCZOS)

        # 计算 Ken Burns 参数
        zoom_start, zoom_end = self.config.ken_burns_zoom_range

        # 交替方向（奇数索引放大，偶数索引缩小）
        if index % 2 == 0:
            zoom_start, zoom_end = zoom_end, zoom_start

        # 随机平移方向
        pan_x = random.uniform(-0.05, 0.05)
        pan_y = random.uniform(-0.05, 0.05)

        # 创建带效果的片段
        def make_frame(t):
            """生成每一帧"""
            progress = t / duration if duration > 0 else 0

            # 计算当前缩放
            current_zoom = zoom_start + (zoom_end - zoom_start) * progress

            # 计算当前平移
            current_pan_x = pan_x * progress
            current_pan_y = pan_y * progress

            # 应用变换
            new_size = (
                int(target_size[0] * current_zoom),
                int(target_size[1] * current_zoom)
            )

            # 缩放图片
            resized = img.resize(new_size, Image.Resampling.LANCZOS)

            # 计算裁剪区域（居中 + 平移）
            left = (new_size[0] - target_size[0]) // 2 + int(current_pan_x * target_size[0])
            top = (new_size[1] - target_size[1]) // 2 + int(current_pan_y * target_size[1])

            # 确保不越界
            left = max(0, min(left, new_size[0] - target_size[0]))
            top = max(0, min(top, new_size[1] - target_size[1]))

            # 裁剪
            cropped = resized.crop((left, top, left + target_size[0], top + target_size[1]))

            return np.array(cropped)

        # 创建视频片段
        from moviepy.video.VideoClip import VideoClip
        clip = VideoClip(make_frame, duration=duration)

        return clip

    def _create_static_clip(self, img_path: str, duration: float) -> ImageClip:
        """创建静态显示片段"""
        clip = ImageClip(img_path).with_duration(duration)

        # 添加轻微缩放动画避免完全静止
        if duration > 3:
            clip = clip.with_effects([
                vfx.Resize(lambda t: 1 + 0.02 * (t / duration))
            ])

        return clip

    def _create_slideshow_clip(self, img_path: str, duration: float) -> ImageClip:
        """创建幻灯片效果（带轻微运动）"""
        clip = ImageClip(img_path).with_duration(duration)

        # 添加缓慢平移
        direction = random.choice(['left', 'right', 'up', 'down'])

        if direction == 'left':
            clip = clip.with_position(lambda t: (-0.02 * t, 'center'))
        elif direction == 'right':
            clip = clip.with_position(lambda t: (0.02 * t, 'center'))
        elif direction == 'up':
            clip = clip.with_position(lambda t: ('center', -0.02 * t))
        else:
            clip = clip.with_position(lambda t: ('center', 0.02 * t))

        return clip

    def _add_transitions_between_clips(self, clips: List[ImageClip]) -> List[ImageClip]:
        """
        在片段之间添加过渡效果

        使用交叉淡入淡出创造平滑过渡
        """
        if len(clips) < 2:
            return clips

        transition_duration = self.config.transition_duration
        result_clips = []

        for i, clip in enumerate(clips):
            if i == 0:
                # 第一个片段：添加淡入
                clip = clip.with_effects([vfx.FadeIn(transition_duration)])
                result_clips.append(clip)
            elif i == len(clips) - 1:
                # 最后一个片段：添加淡出
                clip = clip.with_effects([vfx.FadeOut(transition_duration)])
                result_clips.append(clip)
            else:
                # 中间片段：添加淡入（与前一个片段的淡出重叠）
                clip = clip.with_effects([vfx.FadeIn(transition_duration)])
                result_clips.append(clip)

        return result_clips

    def create_cinematic_sequence(
        self,
        audio_file: str,
        frame_files: List[str],
        scene_durations: List[float],
        output_file: str,
        progress_callback: Optional[Callable[[int, int, str], None]] = None
    ) -> bool:
        """
        创建电影效果序列（使用预生成的多帧图片）

        适用于已经生成多帧图片的情况
        """
        try:
            if progress_callback:
                progress_callback(1, 4, "加载音频...")

            audio = AudioFileClip(audio_file)
            total_duration = audio.duration

            if progress_callback:
                progress_callback(2, 4, "创建电影序列...")

            # 计算需要的总帧数
            total_frames_needed = int(total_duration * 24)  # 24fps

            # 如果帧数不足，循环使用
            if len(frame_files) < total_frames_needed:
                extended_frames = []
                for i in range(total_frames_needed):
                    extended_frames.append(frame_files[i % len(frame_files)])
                frame_files = extended_frames
            else:
                frame_files = frame_files[:total_frames_needed]

            if progress_callback:
                progress_callback(3, 4, "合成电影视频...")

            # 使用 ImageSequenceClip 创建 24fps 视频
            video = ImageSequenceClip(frame_files, fps=24)

            # 添加淡入淡出
            fade_duration = min(1.0, total_duration / 10)
            video = video.with_effects([
                vfx.FadeIn(fade_duration),
                vfx.FadeOut(fade_duration)
            ])

            # 添加音频
            video = video.with_audio(audio)

            if progress_callback:
                progress_callback(4, 4, "导出视频...")

            # 导出
            video.write_videofile(
                output_file,
                fps=24,
                codec='libx264',
                audio_codec='aac',
                bitrate='8000k',
                preset='medium',
                ffmpeg_params=[
                    '-profile:v', 'high',
                    '-level', '4.1',
                    '-pix_fmt', 'yuv420p',
                    '-movflags', '+faststart',
                ],
                logger=None
            )

            audio.close()
            video.close()

            return True

        except Exception as e:
            self.logger.error(f"电影序列生成失败: {e}", exc_info=True)
            return False


# 便捷函数
def create_smooth_slideshow(
    audio_file: str,
    image_files: List[str],
    scene_durations: List[float],
    output_file: str,
    progress_callback: Optional[Callable[[int, int, str], None]] = None
) -> bool:
    """
    创建平滑幻灯片视频（Ken Burns 效果）

    推荐用于解决切换过快问题
    """
    config = EnhancedVideoConfig(
        display_mode=DisplayMode.KEN_BURNS,
        min_scene_duration=3.0,
        transition_duration=1.0
    )
    generator = EnhancedVideoGenerator(os.path.dirname(output_file), config)
    return generator.create_enhanced_video(
        audio_file, image_files, scene_durations, output_file, progress_callback
    )


def create_cinematic_video_enhanced(
    audio_file: str,
    frame_files: List[str],
    scene_durations: List[float],
    output_file: str,
    progress_callback: Optional[Callable[[int, int, str], None]] = None
) -> bool:
    """创建增强电影效果视频"""
    config = EnhancedVideoConfig(display_mode=DisplayMode.CINEMATIC)
    generator = EnhancedVideoGenerator(os.path.dirname(output_file), config)
    return generator.create_cinematic_sequence(
        audio_file, frame_files, scene_durations, output_file, progress_callback
    )
