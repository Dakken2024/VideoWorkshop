#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
电影效果视频生成器 - 推荐方案 A 实现
为每个场景生成多帧略有变化的图片，使用 24fps 播放创造电影感
"""

import os
import random
import shutil
import logging
from typing import List, Dict, Tuple, Optional, Callable
from dataclasses import dataclass
from datetime import datetime

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

from PIL import Image


@dataclass
class CinematicConfig:
    """电影效果配置"""
    fps: int = 24  # 电影标准帧率
    frames_per_scene: int = 3  # 每场景生成的帧数（方案A：3张）
    resolution: Tuple[int, int] = (1080, 1920)  # 默认竖屏
    fade_duration: float = 0.5  # 淡入淡出时长
    codec: str = 'libx264'
    audio_codec: str = 'aac'
    bitrate: str = '8000k'
    
    # 画面变化参数
    variations = [
        "slight zoom in, subtle camera movement, cinematic composition",
        "slight pan left, smooth motion, atmospheric lighting",
        "slight pan right, cinematic depth, professional framing",
        "subtle lighting change, moody atmosphere, film grain",
        "slight focus shift, depth of field, bokeh background"
    ]


class CinematicVideoGenerator:
    """
    电影效果视频生成器 - 实现推荐方案 A
    
    核心特性：
    - 每场景生成多帧略有变化的图片（默认3张）
    - 使用 24fps 电影标准帧率
    - 动态过渡效果（淡入淡出）
    - 模拟摄像机运动（推拉摇移）
    """
    
    def __init__(self, output_dir: str, config: Optional[CinematicConfig] = None):
        """
        初始化电影效果生成器
        
        Args:
            output_dir: 输出目录
            config: 电影效果配置，使用默认配置如果未提供
        """
        self.output_dir = output_dir
        self.config = config or CinematicConfig()
        self.logger = logging.getLogger(__name__)
        
        # 创建帧目录
        self.frames_dir = os.path.join(output_dir, "cinematic_frames")
        os.makedirs(self.frames_dir, exist_ok=True)
        
    def generate_scene_frames(self, 
                             scene_index: int, 
                             prompt: str, 
                             duration: float,
                             image_generator_func: Callable[[str, str], bool]) -> List[str]:
        """
        为单个场景生成多帧图片
        
        Args:
            scene_index: 场景索引
            prompt: 基础提示词
            duration: 场景时长（用于计算需要多少帧）
            image_generator_func: 图片生成函数，接收(prompt, output_path)返回bool
            
        Returns:
            List[str]: 生成的帧文件路径列表
        """
        frame_files = []
        frames_needed = self.config.frames_per_scene
        
        self.logger.info(f"场景 {scene_index+1}: 生成 {frames_needed} 帧电影效果图片")
        
        for i in range(frames_needed):
            # 为每帧添加微小变化，模拟摄像机运动
            variation = self.config.variations[i % len(self.config.variations)]
            varied_prompt = f"{prompt}, {variation}, frame {i+1} of {frames_needed}, continuous cinematic shot, 35mm film look"
            
            frame_file = os.path.join(
                self.frames_dir, 
                f"scene_{scene_index:03d}_frame_{i:03d}.jpg"
            )
            
            # 调用外部图片生成函数
            success = image_generator_func(varied_prompt, frame_file)
            
            if success and os.path.exists(frame_file):
                frame_files.append(frame_file)
                self.logger.debug(f"场景 {scene_index+1} 帧 {i+1}/{frames_needed} 生成成功")
            else:
                # 如果生成失败，复制上一帧或创建占位图
                if frame_files:
                    shutil.copy(frame_files[-1], frame_file)
                    frame_files.append(frame_file)
                    self.logger.warning(f"场景 {scene_index+1} 帧 {i+1} 生成失败，使用上一帧")
                else:
                    # 创建纯色占位图
                    self._create_placeholder_frame(frame_file)
                    frame_files.append(frame_file)
        
        return frame_files
    
    def _create_placeholder_frame(self, output_path: str):
        """创建占位帧"""
        try:
            img = Image.new('RGB', self.config.resolution, color=(30, 30, 30))
            img.save(output_path, quality=95)
        except Exception as e:
            self.logger.error(f"创建占位帧失败: {e}")
    
    def create_cinematic_video(self,
                              audio_file: str,
                              all_frame_files: List[str],
                              scene_durations: List[float],
                              output_file: str,
                              progress_callback: Optional[Callable[[int, int, str], None]] = None) -> bool:
        """
        创建电影效果视频
        
        Args:
            audio_file: 音频文件路径
            all_frame_files: 所有帧文件路径列表（已按场景顺序排列）
            scene_durations: 每个场景的时长列表
            output_file: 输出视频文件路径
            progress_callback: 进度回调函数 (current_step, total_steps, message)
            
        Returns:
            bool: 是否成功
        """
        try:
            if progress_callback:
                progress_callback(1, 5, "加载音频...")
            
            # 加载音频
            if not os.path.exists(audio_file):
                self.logger.error(f"音频文件不存在: {audio_file}")
                return False
            
            audio = AudioFileClip(audio_file)
            total_audio_duration = audio.duration
            self.logger.info(f"音频时长: {total_audio_duration:.2f}秒")
            
            if progress_callback:
                progress_callback(2, 5, "验证图片帧...")
            
            # 验证所有帧文件
            valid_frames = self._validate_frames(all_frame_files)
            if not valid_frames:
                self.logger.error("没有有效的图片帧")
                audio.close()
                return False
            
            self.logger.info(f"有效帧数量: {len(valid_frames)}")
            self.logger.info(f"帧率: {self.config.fps} fps")
            self.logger.info(f"音频时长: {total_audio_duration:.2f}秒")
            
            if progress_callback:
                progress_callback(3, 5, "创建电影序列...")
            
            # 计算需要的总帧数以匹配音频时长
            total_frames_needed = int(total_audio_duration * self.config.fps)
            self.logger.info(f"需要总帧数: {total_frames_needed} (匹配音频时长)")
            
            # 如果帧数不够，循环重复帧
            if len(valid_frames) < total_frames_needed:
                self.logger.info(f"帧数不足，循环重复帧从 {len(valid_frames)} 到 {total_frames_needed}")
                extended_frames = []
                frame_index = 0
                while len(extended_frames) < total_frames_needed:
                    extended_frames.append(valid_frames[frame_index % len(valid_frames)])
                    frame_index += 1
                valid_frames = extended_frames
            elif len(valid_frames) > total_frames_needed:
                # 如果帧数太多，截取需要的部分
                self.logger.info(f"帧数过多，截取前 {total_frames_needed} 帧")
                valid_frames = valid_frames[:total_frames_needed]
            
            # 使用 ImageSequenceClip 创建视频（电影标准方式）
            video_clip = ImageSequenceClip(valid_frames, fps=self.config.fps)
            
            # 验证视频时长
            actual_duration = len(valid_frames) / self.config.fps
            self.logger.info(f"实际视频时长: {actual_duration:.2f}秒")
            
            if progress_callback:
                progress_callback(4, 5, "添加电影效果...")
            
            # 添加音频
            video_clip = video_clip.with_audio(audio)
            
            # 添加电影级淡入淡出效果
            fade_duration = min(self.config.fade_duration, total_audio_duration / 4)
            video_clip = video_clip.with_effects([
                vfx.FadeIn(fade_duration),
                vfx.FadeOut(fade_duration)
            ])
            
            # 添加轻微的电影颗粒感（可选）
            # video_clip = self._add_film_grain(video_clip)
            
            if progress_callback:
                progress_callback(5, 5, "导出视频...")
            
            # 导出视频 - 电影级编码参数
            video_clip.write_videofile(
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
            
            # 清理资源
            audio.close()
            video_clip.close()
            
            # 生成报告
            self._generate_report(output_file, len(valid_frames), total_audio_duration)
            
            self.logger.info(f"电影效果视频生成成功: {output_file}")
            return True
            
        except Exception as e:
            self.logger.error(f"视频生成失败: {e}", exc_info=True)
            return False
    
    def _validate_frames(self, frame_files: List[str]) -> List[str]:
        """验证并返回有效的帧文件"""
        valid_frames = []
        target_size = self.config.resolution
        
        for frame_path in frame_files:
            if not os.path.exists(frame_path):
                self.logger.warning(f"帧文件不存在: {frame_path}")
                continue
            
            try:
                # 验证图片尺寸
                with Image.open(frame_path) as img:
                    if img.size != target_size:
                        # 调整尺寸
                        img = img.resize(target_size, Image.Resampling.LANCZOS)
                        img.save(frame_path, quality=95)
                        self.logger.debug(f"调整帧尺寸: {frame_path}")
                
                valid_frames.append(frame_path)
                
            except Exception as e:
                self.logger.warning(f"帧验证失败 {frame_path}: {e}")
        
        return valid_frames
    
    def _add_film_grain(self, clip) -> CompositeVideoClip:
        """添加电影颗粒感效果（可选）"""
        # 这里可以实现添加噪点的逻辑
        # 暂时返回原视频
        return clip
    
    def _generate_report(self, output_file: str, frame_count: int, duration: float):
        """生成制作报告"""
        try:
            file_size_mb = os.path.getsize(output_file) / (1024 * 1024)
            
            report = {
                'output_file': output_file,
                'file_size_mb': round(file_size_mb, 2),
                'duration_sec': round(duration, 2),
                'total_frames': frame_count,
                'fps': self.config.fps,
                'resolution': self.config.resolution,
                'frames_per_scene': self.config.frames_per_scene,
                'codec': self.config.codec,
                'bitrate': self.config.bitrate,
                'cinematic_mode': True,
                'generation_time': datetime.now().isoformat()
            }
            
            self.logger.info(f"电影效果视频报告: {report}")
            
            # 保存报告到文件
            report_file = output_file.replace('.mp4', '_report.json')
            import json
            with open(report_file, 'w', encoding='utf-8') as f:
                json.dump(report, f, ensure_ascii=False, indent=2)
                
        except Exception as e:
            self.logger.warning(f"生成报告失败: {e}")
    
    def cleanup_frames(self):
        """清理临时帧文件"""
        try:
            if os.path.exists(self.frames_dir):
                shutil.rmtree(self.frames_dir)
                self.logger.info(f"清理临时帧目录: {self.frames_dir}")
        except Exception as e:
            self.logger.warning(f"清理帧文件失败: {e}")


# 便捷函数
def create_cinematic_video_vertical(
    audio_file: str,
    frame_files: List[str],
    scene_durations: List[float],
    output_file: str,
    progress_callback: Optional[Callable[[int, int, str], None]] = None
) -> bool:
    """创建竖屏电影效果视频 (9:16)"""
    config = CinematicConfig(resolution=(1080, 1920))
    generator = CinematicVideoGenerator(
        os.path.dirname(output_file),
        config
    )
    return generator.create_cinematic_video(
        audio_file, frame_files, scene_durations, output_file, progress_callback
    )


def create_cinematic_video_horizontal(
    audio_file: str,
    frame_files: List[str],
    scene_durations: List[float],
    output_file: str,
    progress_callback: Optional[Callable[[int, int, str], None]] = None
) -> bool:
    """创建横屏电影效果视频 (16:9)"""
    config = CinematicConfig(resolution=(1920, 1080))
    generator = CinematicVideoGenerator(
        os.path.dirname(output_file),
        config
    )
    return generator.create_cinematic_video(
        audio_file, frame_files, scene_durations, output_file, progress_callback
    )
