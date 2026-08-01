#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
视频编码器 - GPU 加速检测、智能码率控制、编码报告
"""

import os
import subprocess
import json
from typing import Dict, Optional, Tuple
from dataclasses import dataclass

from ..config import VideoEncodingConfig, DEFAULT_CONFIG
from ..utils.logger import logger


@dataclass
class EncodingReport:
    """编码报告"""
    output_file: str
    file_size_mb: float
    duration_sec: float
    scene_count: int
    codec: str
    crf: int
    preset: str
    gpu_accelerated: bool
    gpu_encoder: Optional[str] = None
    fps: int = 30
    resolution: Tuple[int, int] = (1080, 1920)


class VideoEncoder:
    """视频编码器"""

    def __init__(self, config: VideoEncodingConfig = None):
        self.config = config or DEFAULT_CONFIG.video
        self.gpu_available = False
        self.gpu_encoder = None
        self._detect_gpu()

    def _detect_gpu(self):
        """检测可用 GPU 编码器并验证其可运行性

        改进: 不仅检测编码器是否存在，还会通过运行时测试验证是否能正常创建编码器实例。
        如果验证失败（如缺少 nvcuda.dll），自动回退到 CPU 编码。
        """
        gpu_encoders = [
            ('h264_nvenc', 'NVIDIA NVENC'),
            ('h264_qsv', 'Intel Quick Sync'),
            ('h264_amf', 'AMD AMF'),
        ]
        try:
            result = subprocess.run(
                ['ffmpeg', '-hide_banner', '-encoders'],
                capture_output=True, text=True, timeout=10
            )
            candidates = []
            for encoder, name in gpu_encoders:
                if encoder in result.stdout:
                    candidates.append((encoder, name))
                    logger.info(f"检测到 GPU 编码器可用: {name}")

            # 对候选编码器进行运行时验证
            for encoder, name in candidates:
                if self._verify_encoder(encoder):
                    self.gpu_available = True
                    self.gpu_encoder = encoder
                    logger.success(f"GPU 编码器验证通过: {name}")
                    return
                else:
                    logger.warning(f"GPU 编码器 {name} 运行时验证失败，尝试下一个候选...")
        except:
            pass
        logger.info("使用 CPU 编码 (libx264)")

    def _verify_encoder(self, encoder: str) -> bool:
        """运行时验证编码器是否能正常初始化

        创建一个极小测试视频，尝试使用目标编码器编码，
        验证驱动和 runtime 库是否正常加载。
        """
        import tempfile
        try:
            test_input = os.path.join(tempfile.gettempdir(), "_vg_encoder_test_%03d.png")
            test_output = os.path.join(tempfile.gettempdir(), "_vg_encoder_test_out.mp4")

            # 清理可能存在的旧测试文件
            for f in [test_output]:
                if os.path.exists(f):
                    try:
                        os.remove(f)
                    except:
                        pass

            # 使用 FFmpeg 的 lavfi 生成测试信号并编码
            cmd = [
                'ffmpeg', '-hide_banner', '-loglevel', 'error',
                '-f', 'lavfi', '-i', 'color=c=black:s=64x64:d=0.5:r=1',
                '-c:v', encoder,
                '-frames:v', '1',
                '-y', test_output
            ]
            proc = subprocess.run(
                cmd, capture_output=True, text=True, timeout=15
            )
            if proc.returncode == 0 and os.path.exists(test_output):
                os.remove(test_output)
                return True

            # 记录具体错误信息以便调试
            err_msg = proc.stderr.strip()[:200] if proc.stderr else "未知错误"
            logger.debug(f"编码器 {encoder} 验证失败: {err_msg}")
            return False
        except subprocess.TimeoutExpired:
            logger.debug(f"编码器 {encoder} 验证超时")
            return False
        except Exception as e:
            logger.debug(f"编码器 {encoder} 验证异常: {e}")
            return False
        finally:
            # 清理可能残留的测试文件
            for f in [test_output]:
                if os.path.exists(f):
                    try:
                        os.remove(f)
                    except:
                        pass

    def get_ffmpeg_params(self) -> Dict:
        """获取 FFmpeg 编码参数"""
        params = {
            'fps': self.config.fps,
            'codec': self.config.codec,
            'audio_codec': self.config.audio_codec,
            'audio_bitrate': self.config.audio_bitrate,
        }

        if self.gpu_available and self.gpu_encoder:
            params['codec'] = self.gpu_encoder
            if self.gpu_encoder == 'h264_nvenc':
                params['ffmpeg_params'] = [
                    '-preset', 'p4',
                    '-rc:v', 'vbr',
                    '-cq:v', str(self.config.crf),
                    '-b:v', '0',
                    '-profile:v', 'high',
                    '-level', '4.1',
                    '-pix_fmt', 'yuv420p',
                    '-movflags', '+faststart',
                ]
            else:
                params['ffmpeg_params'] = [
                    '-profile:v', 'high',
                    '-level', '4.1',
                    '-pix_fmt', 'yuv420p',
                    '-movflags', '+faststart',
                ]
        else:
            params['ffmpeg_params'] = [
                '-crf', str(self.config.crf),
                '-preset', self.config.preset,
                '-profile:v', 'high',
                '-level', '4.1',
                '-pix_fmt', 'yuv420p',
                '-movflags', '+faststart',
                '-threads', str(self.config.threads or 0),
            ]

        return params

    def generate_report(self, output_file: str, duration: float,
                        scene_count: int, resolution: Tuple[int, int]) -> EncodingReport:
        """生成编码报告"""
        file_size = os.path.getsize(output_file) / (1024 * 1024) if os.path.exists(output_file) else 0
        return EncodingReport(
            output_file=output_file,
            file_size_mb=round(file_size, 2),
            duration_sec=round(duration, 2),
            scene_count=scene_count,
            codec=self.gpu_encoder if self.gpu_available else 'libx264',
            crf=self.config.crf,
            preset=self.config.preset,
            gpu_accelerated=self.gpu_available,
            gpu_encoder=self.gpu_encoder,
            fps=self.config.fps,
            resolution=resolution
        )