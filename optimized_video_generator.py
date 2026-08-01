#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
优化版视频生成器 - 基于 MoviePy 最佳实践
整合智能编码、GPU加速、场景复杂度分析等高级特性
"""

import os
import subprocess
import logging
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
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
        ColorClip
    )
    from moviepy.video import fx as vfx


class VideoAspectRatio(Enum):
    """视频比例枚举"""
    VERTICAL_9_16 = (9, 16)  # 手机竖屏 1080x1920
    HORIZONTAL_16_9 = (16, 9)  # 标准横屏 1920x1080
    
    @property
    def width(self) -> int:
        if self == VideoAspectRatio.VERTICAL_9_16:
            return 1080
        return 1920
    
    @property
    def height(self) -> int:
        if self == VideoAspectRatio.VERTICAL_9_16:
            return 1920
        return 1080
    
    @property
    def resolution(self) -> Tuple[int, int]:
        return (self.width, self.height)


@dataclass
class EncodingSettings:
    """编码设置数据类"""
    fps: int = 30
    crf: int = 23
    preset: str = 'slow'
    codec: str = 'libx264'
    audio_codec: str = 'aac'
    audio_bitrate: str = '128k'
    profile: str = 'high'
    level: str = '4.1'
    pixel_format: str = 'yuv420p'
    faststart: bool = True
    threads: int = 0  # 0 = 使用所有CPU核心


@dataclass
class ComplexityAnalysis:
    """场景复杂度分析结果"""
    complexity: str = 'medium'  # 'high', 'medium', 'low'
    crf: int = 23
    preset: str = 'slow'
    complexity_score: float = 0.0
    motion_score: float = 0.0
    scene_count: int = 0


class OptimizedVideoGenerator:
    """
    优化版视频生成器
    
    特性：
    - 智能场景复杂度分析
    - GPU/CPU 编码自动选择
    - 多种视频比例支持 (9:16, 16:9)
    - 自适应编码参数
    - 完善的错误处理和资源管理
    """
    
    # 复杂度关键词
    COMPLEX_KEYWORDS = [
        'detailed', 'intricate', 'busy', 'crowd', 'multiple', 'complex',
        'texture', 'pattern', 'ornate', 'elaborate', 'rich', 'layered',
        '详细', '复杂', '繁忙', '人群', '纹理', '图案'
    ]
    
    SIMPLE_KEYWORDS = [
        'minimal', 'simple', 'clean', 'solid', 'gradient', 'blur',
        'plain', 'smooth', 'uniform', 'single', 'basic',
        '简单', '干净', '纯色', '渐变', '模糊'
    ]
    
    MOTION_KEYWORDS = [
        'action', 'movement', 'dynamic', 'fast', 'motion', 'running',
        'flying', 'falling', 'explosion', 'battle', 'chase',
        '动作', '运动', '动态', '快速', '奔跑'
    ]
    
    # GPU 编码器映射
    GPU_ENCODERS = [
        ('h264_nvenc', 'NVIDIA NVENC'),
        ('h264_qsv', 'Intel Quick Sync'),
        ('h264_videotoolbox', 'Apple VideoToolbox'),
        ('h264_amf', 'AMD AMF')
    ]
    
    # NVENC preset 映射
    NVENC_PRESET_MAP = {
        'slow': 'p6',
        'medium': 'p4',
        'fast': 'p1'
    }
    
    def __init__(self, output_dir: str, aspect_ratio: VideoAspectRatio = VideoAspectRatio.VERTICAL_9_16):
        """
        初始化视频生成器
        
        Args:
            output_dir: 输出目录
            aspect_ratio: 视频比例，默认 9:16 竖屏
        """
        self.output_dir = output_dir
        self.aspect_ratio = aspect_ratio
        self.resolution = aspect_ratio.resolution
        self.gpu_available, self.gpu_encoder = self._detect_gpu()
        self.encoding_report: Optional[Dict] = None
        
        # 设置日志
        self.logger = logging.getLogger(__name__)
        
    def _detect_gpu(self) -> Tuple[bool, Optional[str]]:
        """检测可用的 GPU 编码器"""
        try:
            result = subprocess.run(
                ['ffmpeg', '-hide_banner', '-encoders'],
                capture_output=True, text=True, timeout=10
            )
            
            for encoder, name in self.GPU_ENCODERS:
                if encoder in result.stdout:
                    self.logger.info(f'检测到 GPU 编码器: {name} ({encoder})')
                    return True, encoder
                    
        except Exception as e:
            self.logger.warning(f'GPU 检测失败: {e}')
            
        self.logger.info('使用 CPU 编码')
        return False, None
    
    def analyze_scene_complexity(self, scenes: List[Dict]) -> ComplexityAnalysis:
        """
        分析场景复杂度以确定最佳编码参数
        
        Args:
            scenes: 场景列表，每个场景包含 'prompt' 和 'text' 字段
            
        Returns:
            ComplexityAnalysis: 复杂度分析结果
        """
        if not scenes:
            return ComplexityAnalysis()
        
        complexity_score = 0
        motion_score = 0
        
        for scene in scenes:
            prompt = scene.get('prompt', '').lower()
            text = scene.get('text', '').lower()
            combined = f"{prompt} {text}"
            
            # 计算复杂度分数
            for kw in self.COMPLEX_KEYWORDS:
                if kw in combined:
                    complexity_score += 1
            
            for kw in self.SIMPLE_KEYWORDS:
                if kw in combined:
                    complexity_score -= 1
            
            for kw in self.MOTION_KEYWORDS:
                if kw in combined:
                    motion_score += 1
        
        avg_complexity = complexity_score / len(scenes)
        avg_motion = motion_score / len(scenes)
        combined_score = avg_complexity + avg_motion * 0.5
        
        # 根据分数确定复杂度等级
        if combined_score > 1.5:
            return ComplexityAnalysis(
                complexity='high',
                crf=21,
                preset='slow',
                complexity_score=round(avg_complexity, 2),
                motion_score=round(avg_motion, 2),
                scene_count=len(scenes)
            )
        elif combined_score < -0.5:
            return ComplexityAnalysis(
                complexity='low',
                crf=25,
                preset='medium',
                complexity_score=round(avg_complexity, 2),
                motion_score=round(avg_motion, 2),
                scene_count=len(scenes)
            )
        else:
            return ComplexityAnalysis(
                complexity='medium',
                crf=23,
                preset='slow',
                complexity_score=round(avg_complexity, 2),
                motion_score=round(avg_motion, 2),
                scene_count=len(scenes)
            )
    
    def create_video(self,
                    audio_file: str,
                    image_files: List[str],
                    scene_durations: List[float],
                    output_file: str,
                    scenes: Optional[List[Dict]] = None,
                    add_watermark: bool = True,
                    progress_callback=None) -> bool:
        """
        创建优化版视频
        
        Args:
            audio_file: 音频文件路径
            image_files: 图片文件路径列表
            scene_durations: 场景持续时间列表
            output_file: 输出视频文件路径
            scenes: 场景信息列表（用于智能编码优化）
            add_watermark: 是否添加水印
            progress_callback: 进度回调函数 (current_step, total_steps, message)
            
        Returns:
            bool: 是否成功
        """
        try:
            # 步骤 1: 分析场景复杂度
            if progress_callback:
                progress_callback(1, 5, "分析场景复杂度...")
            
            complexity = self.analyze_scene_complexity(scenes) if scenes else ComplexityAnalysis()
            self.logger.info(f"场景复杂度: {complexity.complexity}, CRF: {complexity.crf}")
            
            # 步骤 2: 加载和验证音频
            if progress_callback:
                progress_callback(2, 5, "加载音频...")
            
            audio = self._load_audio(audio_file)
            if not audio:
                return False
            
            total_audio_duration = audio.duration
            self.logger.info(f"音频时长: {total_audio_duration:.2f}秒")
            
            # 步骤 3: 创建视频片段
            if progress_callback:
                progress_callback(3, 5, "创建视频片段...")
            
            video_clips = self._create_video_clips(
                image_files, 
                scene_durations, 
                total_audio_duration,
                progress_callback
            )
            
            if not video_clips:
                self.logger.error("没有有效的视频片段")
                audio.close()
                return False
            
            # 步骤 4: 合成视频
            if progress_callback:
                progress_callback(4, 5, "合成视频...")
            
            final_video = concatenate_videoclips(video_clips, method="compose")
            
            # 添加水印（可选）
            if add_watermark:
                final_video = self._add_watermark(final_video)
            
            # 添加音频
            final_video = final_video.with_audio(audio)
            
            # 步骤 5: 编码输出
            if progress_callback:
                progress_callback(5, 5, "编码输出...")
            
            success = self._encode_video(
                final_video, 
                output_file, 
                complexity,
                total_audio_duration
            )
            
            # 清理资源
            self._cleanup_resources(audio, video_clips, final_video)
            
            return success
            
        except Exception as e:
            self.logger.error(f"视频生成失败: {e}", exc_info=True)
            return False
    
    def _load_audio(self, audio_file: str) -> Optional[AudioFileClip]:
        """加载音频文件"""
        try:
            audio = AudioFileClip(audio_file)
            return audio
        except Exception as e:
            self.logger.error(f"音频加载失败: {e}")
            return None
    
    def _create_video_clips(self, 
                           image_files: List[str], 
                           scene_durations: List[float],
                           total_audio_duration: float,
                           progress_callback=None) -> List[ImageClip]:
        """创建视频片段列表"""
        video_clips = []
        total_scene_duration = sum(scene_durations) if scene_durations else 1
        
        for i, (img_path, base_duration) in enumerate(zip(image_files, scene_durations)):
            if not img_path or not os.path.exists(img_path):
                self.logger.warning(f"跳过无效图片: {img_path}")
                continue
            
            # 按比例分配时长
            actual_duration = (base_duration / total_scene_duration) * total_audio_duration
            
            try:
                # 创建图片片段
                clip = ImageClip(img_path).with_duration(actual_duration)
                
                # 添加淡入淡出效果
                clip = self._apply_transitions(clip, i, len(image_files))
                
                video_clips.append(clip)
                
                if progress_callback and i % 5 == 0:
                    progress_callback(
                        3, 5, 
                        f"创建片段 {i+1}/{len(image_files)}..."
                    )
                
            except Exception as e:
                self.logger.error(f"创建片段 {i+1} 失败: {e}")
                continue
        
        return video_clips
    
    def _apply_transitions(self, clip: ImageClip, index: int, total: int) -> ImageClip:
        """应用转场效果"""
        if index == 0:
            # 第一个场景：淡入
            clip = clip.with_effects([vfx.FadeIn(0.5)])
        elif index == total - 1:
            # 最后一个场景：淡出
            clip = clip.with_effects([vfx.FadeOut(0.5)])
        else:
            # 中间场景：淡入+淡出
            clip = clip.with_effects([vfx.FadeIn(0.3), vfx.FadeOut(0.3)])
        
        return clip
    
    def _add_watermark(self, video: CompositeVideoClip) -> CompositeVideoClip:
        """添加水印"""
        try:
            fonts_to_try = ['Arial', 'SimHei', 'Microsoft YaHei', 'sans-serif', None]
            
            for font_name in fonts_to_try:
                try:
                    watermark_kwargs = {
                        'text': "Saabor AI Builds",
                        'fontsize': 20,
                        'color': 'white'
                    }
                    if font_name:
                        watermark_kwargs['font'] = font_name
                    
                    watermark = (TextClip(**watermark_kwargs)
                                .with_position(('right', 'bottom'), relative=True)
                                .with_duration(video.duration)
                                .with_opacity(0.6))
                    
                    return CompositeVideoClip([video, watermark])
                    
                except Exception:
                    continue
                    
        except Exception as e:
            self.logger.warning(f"水印添加失败: {e}")
        
        return video
    
    def _encode_video(self,
                     final_video: CompositeVideoClip,
                     output_file: str,
                     complexity: ComplexityAnalysis,
                     total_duration: float) -> bool:
        """编码视频"""
        try:
            settings = EncodingSettings(
                crf=complexity.crf,
                preset=complexity.preset
            )
            
            ffmpeg_params = [
                '-crf', str(settings.crf),
                '-profile:v', settings.profile,
                '-level', settings.level,
                '-pix_fmt', settings.pixel_format,
                '-movflags', '+faststart',
            ]
            
            # GPU 编码
            if self.gpu_available and self.gpu_encoder:
                settings.codec = self.gpu_encoder
                
                if self.gpu_encoder == 'h264_nvenc':
                    nvenc_preset = self.NVENC_PRESET_MAP.get(settings.preset, 'p4')
                    ffmpeg_params = [
                        '-preset', nvenc_preset,
                        '-rc:v', 'vbr',
                        '-cq:v', str(settings.crf),
                        '-b:v', '0',
                        '-profile:v', settings.profile,
                        '-level', settings.level,
                        '-pix_fmt', settings.pixel_format,
                        '-movflags', '+faststart',
                    ]
                
                self.logger.info(f"使用 GPU 编码: {self.gpu_encoder}")
            else:
                # CPU 编码
                ffmpeg_params.append('-threads')
                ffmpeg_params.append(str(settings.threads))
                self.logger.info("使用 CPU 编码: libx264")
            
            # 写入视频文件
            final_video.write_videofile(
                output_file,
                fps=settings.fps,
                codec=settings.codec,
                audio_codec=settings.audio_codec,
                preset=settings.preset if not self.gpu_available else None,
                ffmpeg_params=ffmpeg_params,
                audio_bitrate=settings.audio_bitrate,
                logger=None
            )
            
            # 生成编码报告
            self._generate_encoding_report(output_file, settings, complexity, total_duration)
            
            self.logger.info(f"视频生成成功: {output_file}")
            return True
            
        except Exception as e:
            self.logger.error(f"视频编码失败: {e}")
            return False
    
    def _generate_encoding_report(self,
                                  output_file: str,
                                  settings: EncodingSettings,
                                  complexity: ComplexityAnalysis,
                                  duration: float):
        """生成编码报告"""
        try:
            file_size_mb = os.path.getsize(output_file) / (1024 * 1024)
            
            self.encoding_report = {
                'output_file': output_file,
                'file_size_mb': round(file_size_mb, 2),
                'duration_sec': round(duration, 2),
                'resolution': self.resolution,
                'aspect_ratio': f"{self.aspect_ratio.value[0]}:{self.aspect_ratio.value[1]}",
                'encoding_settings': {
                    'fps': settings.fps,
                    'codec': settings.codec,
                    'crf': settings.crf,
                    'preset': settings.preset,
                    'profile': settings.profile,
                    'level': settings.level,
                    'audio_bitrate': settings.audio_bitrate,
                    'gpu_accelerated': self.gpu_available,
                    'gpu_encoder': self.gpu_encoder if self.gpu_available else None
                },
                'complexity_analysis': {
                    'complexity': complexity.complexity,
                    'score': complexity.complexity_score,
                    'motion_score': complexity.motion_score
                }
            }
            
            self.logger.info(f"编码报告: {self.encoding_report}")
            
        except Exception as e:
            self.logger.warning(f"生成编码报告失败: {e}")
    
    def _cleanup_resources(self, 
                          audio: AudioFileClip,
                          video_clips: List[ImageClip],
                          final_video: CompositeVideoClip):
        """清理资源"""
        try:
            audio.close()
            for clip in video_clips:
                clip.close()
            final_video.close()
        except Exception as e:
            self.logger.warning(f"资源清理时出错: {e}")
    
    def get_encoding_report(self) -> Optional[Dict]:
        """获取编码报告"""
        return self.encoding_report


# 便捷函数
def create_video_vertical(audio_file: str,
                         image_files: List[str],
                         scene_durations: List[float],
                         output_file: str,
                         **kwargs) -> bool:
    """创建 9:16 竖屏视频"""
    generator = OptimizedVideoGenerator(
        os.path.dirname(output_file),
        VideoAspectRatio.VERTICAL_9_16
    )
    return generator.create_video(audio_file, image_files, scene_durations, output_file, **kwargs)


def create_video_horizontal(audio_file: str,
                           image_files: List[str],
                           scene_durations: List[float],
                           output_file: str,
                           **kwargs) -> bool:
    """创建 16:9 横屏视频"""
    generator = OptimizedVideoGenerator(
        os.path.dirname(output_file),
        VideoAspectRatio.HORIZONTAL_16_9
    )
    return generator.create_video(audio_file, image_files, scene_durations, output_file, **kwargs)
