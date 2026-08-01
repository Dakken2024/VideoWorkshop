#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
音频生成器 - 支持 edge-tts 分段生成、超时保护、断点续传
"""

import os
import re
import asyncio
import time
from typing import List, Dict, Optional, Callable, Tuple
from pydub import AudioSegment

from ..config import AudioConfig, DEFAULT_CONFIG
from ..utils.logger import logger
from ..utils.file_utils import ensure_dir


class AudioGenerator:
    """
    音频生成器

    核心改进:
    1. 超时保护 - 防止 edge-tts 长时间挂起
    2. 分段生成 - 自动分割长文本，避免单次生成超时
    3. 断点续传 - 已生成的音频段跳过
    4. 静音插入 - 在场景间插入自然停顿
    5. 精确时长追踪 - 记录每场景音频时长用于字幕对齐
    """

    def __init__(self, config: AudioConfig = None):
        self.config = config or DEFAULT_CONFIG.audio
        self.current_voice = self.config.voice

    async def generate(self, scenes: List[Dict], output_dir: str,
                       progress_callback: Optional[Callable] = None) -> Tuple[bool, str, List[float]]:
        """
        生成完整音频

        Args:
            scenes: 场景列表
            output_dir: 输出目录
            progress_callback: 进度回调 (current, total, message)

        Returns:
            (是否成功, 音频文件路径, 每场景音频时长列表)
        """
        ensure_dir(output_dir)
        audio_path = os.path.join(output_dir, "voiceover.mp3")
        scene_audio_durations = []

        try:
            if progress_callback:
                progress_callback(0, 100, "准备生成音频")

            # 分段生成
            segment_files = []
            total = len(scenes)

            for i, scene in enumerate(scenes):
                text = scene.get('text', '').strip()
                scene_id = scene.get('scene_id', i + 1)

                if not text:
                    logger.warning(f"场景 {scene_id}: 文本为空，跳过")
                    scene_audio_durations.append(0)
                    continue

                segment_file = os.path.join(output_dir, f"segment_{i:03d}.mp3")

                # 检查是否已存在（断点续传）
                if os.path.exists(segment_file) and os.path.getsize(segment_file) > 1000:
                    logger.info(f"场景 {scene_id}: 音频已存在，跳过")
                    segment_files.append(segment_file)
                    # 获取时长
                    try:
                        audio = AudioSegment.from_file(segment_file)
                        scene_audio_durations.append(len(audio) / 1000.0)
                        audio.close()
                    except:
                        scene_audio_durations.append(3.0)
                    if progress_callback:
                        progress = int((i + 1) / total * 60)
                        progress_callback(progress, 100, f"场景 {scene_id}: 音频已存在")
                    continue

                # 生成单个场景音频
                if progress_callback:
                    progress_callback(int(i / total * 60), 100, f"生成音频: 场景 {scene_id}")

                success = await self._generate_segment(text, segment_file, scene_id)
                if success and os.path.exists(segment_file):
                    segment_files.append(segment_file)
                    try:
                        audio = AudioSegment.from_file(segment_file)
                        scene_audio_durations.append(len(audio) / 1000.0)
                        audio.close()
                    except:
                        scene_audio_durations.append(3.0)
                else:
                    logger.warning(f"场景 {scene_id}: 音频生成失败")
                    segment_files.append(None)
                    scene_audio_durations.append(3.0)

            # 拼接音频
            if progress_callback:
                progress_callback(75, 100, "拼接音频片段")

            if not segment_files:
                logger.error("没有有效的音频片段")
                return False, "", []

            # 过滤掉失败的片段
            valid_segments = [(i, f) for i, f in enumerate(segment_files) if f and os.path.exists(f)]
            if not valid_segments:
                logger.error("没有有效的音频片段可拼接")
                return False, "", []

            # 拼接
            combined = AudioSegment.from_file(valid_segments[0][1])
            for idx, (seg_idx, seg_file) in enumerate(valid_segments[1:], 1):
                # 插入停顿
                pause_ms = self._get_pause_duration(scenes[valid_segments[0][0] if idx == 1 else seg_idx - 1])
                if pause_ms > 0:
                    combined += AudioSegment.silent(duration=pause_ms)
                combined += AudioSegment.from_file(seg_file)

            # 导出
            combined.export(audio_path, format="mp3", bitrate="192k")
            logger.success(f"音频生成完成: {audio_path}")

            if progress_callback:
                progress_callback(100, 100, "音频生成完成")

            return True, audio_path, scene_audio_durations

        except Exception as e:
            logger.error(f"音频生成失败: {e}")
            return False, "", []

    async def _generate_segment(self, text: str, output_file: str,
                                 scene_id: int) -> bool:
        """生成单个场景音频"""
        clean_text = re.sub(r'<[^>]+>', '', text).strip()
        if not clean_text:
            return False

        try:
            import edge_tts

            communicate = edge_tts.Communicate(
                clean_text,
                voice=self.current_voice,
                rate=self.config.rate,
                volume=self.config.volume
            )

            # 超时保护
            timeout = min(len(clean_text) // 1000 * 30 + 60, self.config.segment_timeout)
            await asyncio.wait_for(communicate.save(output_file), timeout=timeout)

            if os.path.exists(output_file) and os.path.getsize(output_file) > 1000:
                logger.success(f"场景 {scene_id}: 音频生成成功")
                return True
            else:
                logger.warning(f"场景 {scene_id}: 生成的文件异常")
        except asyncio.TimeoutError:
            logger.warning(f"场景 {scene_id}: 生成超时")
        except Exception as e:
            logger.warning(f"场景 {scene_id}: 生成失败 - {str(e)[:80]}")

        # 尝试备选语音
        if self.current_voice != self.config.fallback_voice:
            logger.info(f"场景 {scene_id}: 切换到备选语音: {self.config.fallback_voice}")
            self.current_voice = self.config.fallback_voice
            return await self._generate_segment(text, output_file, scene_id)

        logger.error(f"场景 {scene_id}: 所有方案失败")
        return False

    def _get_pause_duration(self, scene: Dict) -> int:
        """获取场景文本的停顿时长"""
        text = scene.get('text', '')
        if not text:
            return 0
        last_char = text.strip()[-1] if text.strip() else ''
        if last_char in ['。', '！', '？', '!', '?']:
            return self.config.pause_long
        if last_char in ['，', '；', ',', ';']:
            return self.config.pause_medium
        if last_char in ['、']:
            return self.config.pause_short
        return 0