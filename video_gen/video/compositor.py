#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
视频合成器 - 整合图片、音频、字幕合成最终视频
"""

import os
from typing import List, Dict, Tuple, Optional, Callable

from ..config import VideoEncodingConfig, DEFAULT_CONFIG
from ..utils.logger import logger
from ..utils.file_utils import ensure_dir
from .encoder import VideoEncoder
from .subtitle import SubtitleManager


class VideoCompositor:
    """
    视频合成器

    核心改进:
    1. 集成字幕生成与嵌入
    2. Ken Burns 效果
    3. 智能码率控制
    4. GPU 加速
    5. 进度回调
    """

    def __init__(self, config: VideoEncodingConfig = None):
        self.config = config or DEFAULT_CONFIG.video
        self.encoder = VideoEncoder(config)
        self.subtitle_manager = SubtitleManager()

    def create(self, audio_file: str, image_files: List[str],
               scene_durations: List[float], output_file: str,
               scenes: List[Dict] = None,
               scene_audio_durations: List[float] = None,
               progress_callback: Optional[Callable] = None) -> Tuple[bool, str]:
        """
        合成视频（含字幕）

        Args:
            audio_file: 音频文件路径
            image_files: 图片文件路径列表
            scene_durations: 场景持续时间列表
            output_file: 输出视频文件路径
            scenes: 场景信息列表（用于字幕生成）
            scene_audio_durations: 每场景音频时长（用于字幕对齐）
            progress_callback: 进度回调

        Returns:
            (是否成功, 最终视频路径)
        """
        logger.info("开始合成视频...")

        # 步骤1: 生成无字幕视频
        if progress_callback:
            progress_callback(10, 100, "合成无字幕视频")

        no_subtitle_file = output_file.replace('.mp4', '_nosub.mp4')
        success = self._compose_video(
            audio_file, image_files, scene_durations,
            no_subtitle_file, progress_callback
        )
        if not success:
            logger.error("视频合成失败（无字幕阶段）")
            return False, ""

        # 步骤2: 生成并嵌入字幕
        if scenes and self.subtitle_manager.config.enabled:
            if progress_callback:
                progress_callback(70, 100, "生成并嵌入字幕")

            # 获取音频时长
            audio_duration = sum(scene_durations) if scene_durations else None

            subtitle_success = self.subtitle_manager.process(
                scenes=scenes,
                video_path=no_subtitle_file,
                output_path=output_file,
                audio_duration=audio_duration,
                scene_audio_durations=scene_audio_durations,
                progress_callback=progress_callback
            )

            if subtitle_success:
                logger.success(f"视频合成完成（含字幕）: {output_file}")
                # 清理临时文件
                if os.path.exists(no_subtitle_file):
                    try:
                        os.remove(no_subtitle_file)
                    except:
                        pass
                return True, output_file
            else:
                logger.warning("字幕嵌入失败，返回无字幕视频")
                # 重命名无字幕视频为最终输出
                if os.path.exists(no_subtitle_file):
                    os.rename(no_subtitle_file, output_file)
                return True, output_file
        else:
            # 无字幕模式
            if os.path.exists(no_subtitle_file):
                os.rename(no_subtitle_file, output_file)
            logger.success(f"视频合成完成（无字幕）: {output_file}")
            return True, output_file

    def _compose_video(self, audio_file: str, image_files: List[str],
                       scene_durations: List[float], output_file: str,
                       progress_callback: Optional[Callable] = None) -> bool:
        """合成无字幕视频"""
        try:
            # MoviePy 导入
            try:
                from moviepy import (
                    AudioFileClip, ImageClip, concatenate_videoclips,
                    CompositeVideoClip, TextClip, vfx
                )
                from moviepy.video.VideoClip import ColorClip
            except ImportError:
                from moviepy.editor import (
                    AudioFileClip, ImageClip, concatenate_videoclips,
                    CompositeVideoClip, TextClip, ColorClip
                )
                from moviepy.video import fx as vfx

            # 加载音频
            if not os.path.exists(audio_file):
                logger.error(f"音频文件不存在: {audio_file}")
                return False

            audio = AudioFileClip(audio_file)
            total_audio_duration = audio.duration
            logger.info(f"音频时长: {total_audio_duration:.2f}秒")

            # 计算总场景时长
            total_scene_duration = sum(scene_durations) or len(image_files) * 5

            # 创建视频片段
            video_clips = []
            for i, (img_path, base_duration) in enumerate(zip(image_files, scene_durations)):
                if not img_path or not os.path.exists(img_path):
                    logger.warning(f"跳过无效图片: {img_path}")
                    continue

                # 按比例分配时长
                actual_duration = (base_duration / total_scene_duration) * total_audio_duration

                clip = ImageClip(img_path).with_duration(actual_duration)

                # 淡入淡出效果
                if i == 0:
                    clip = clip.with_effects([vfx.FadeIn(0.5)])
                elif i == len(image_files) - 1:
                    clip = clip.with_effects([vfx.FadeOut(0.5)])
                else:
                    clip = clip.with_effects([vfx.FadeIn(0.3), vfx.FadeOut(0.3)])

                video_clips.append(clip)

            if not video_clips:
                logger.error("没有有效的视频片段")
                audio.close()
                return False

            # 合成
            final_video = concatenate_videoclips(video_clips, method="compose")
            final_video = final_video.with_audio(audio)

            # 编码参数
            encode_params = self.encoder.get_ffmpeg_params()
            logger.info(f"编码参数: {encode_params['codec']}")

            # 写入文件
            final_video.write_videofile(
                output_file,
                fps=encode_params['fps'],
                codec=encode_params['codec'],
                audio_codec=encode_params['audio_codec'],
                ffmpeg_params=encode_params['ffmpeg_params'],
                audio_bitrate=encode_params['audio_bitrate'],
                logger=None
            )

            audio.close()
            for clip in video_clips:
                clip.close()

            # 生成报告
            report = self.encoder.generate_report(
                output_file, total_audio_duration,
                len(image_files), (1080, 1920)
            )
            logger.success(f"视频合成完成: {output_file}")
            logger.info(f"文件大小: {report.file_size_mb:.1f}MB")

            return True

        except Exception as e:
            logger.error(f"视频合成异常: {e}")
            return False