#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
逐帧图片生成器 - 支持逐帧 Prompt 设计的新格式
根据 day29_script.json 格式，为每帧生成独立图片
"""

import os
import json
import time
import random
import threading
from datetime import datetime
from typing import List, Dict, Callable, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum


@dataclass
class FrameBasedConfig:
    """逐帧生成配置"""

    # API 限制配置
    min_interval: float = 3.0       # 最小调用间隔（秒）
    max_interval: float = 15.0      # 最大调用间隔（秒）
    failure_backoff: float = 2.0    # 失败后的退避倍数
    max_retries: int = 3            # 最大重试次数

    # 输出配置
    output_dir: str = "./output"

    # 连贯性控制
    use_frame_seed: bool = True     # 是否使用帧指定的 seed
    default_seed_start: int = 1001  # 默认 seed 起始值


class FrameBasedGenerator:
    """
    逐帧图片生成器

    核心功能：
    1. 解析新的 JSON 格式（每帧独立 prompt + seed + camera_motion）
    2. 按顺序生成每帧图片
    3. 使用指定的 seed 确保帧间一致性
    4. API 调用频率限制
    5. 失败重试和占位图 fallback
    """

    def __init__(self, config: Optional[FrameBasedConfig] = None):
        self.config = config or FrameBasedConfig()

        # 状态跟踪
        self.last_call_time = 0.0
        self.consecutive_failures = 0
        self.total_calls = 0
        self.successful_calls = 0

        # 线程锁
        self._lock = threading.Lock()

        # 生成统计
        self.generation_stats = {
            "start_time": None,
            "end_time": None,
            "total_frames": 0,
            "successful_frames": 0,
            "failed_frames": 0,
            "scenes_processed": 0
        }

    def parse_script(self, script_data: Dict) -> List[Dict]:
        """
        解析脚本数据，提取所有帧信息

        Args:
            script_data: JSON 脚本数据

        Returns:
            扁平化的帧列表，每个帧包含完整信息
        """
        frames = []
        scenes = script_data.get('scenes', [])

        for scene in scenes:
            scene_id = scene.get('scene_id', 0)
            scene_text = scene.get('text', '')
            scene_note = scene.get('note', '')
            duration_sec = scene.get('duration_sec', 5)

            # 获取帧列表
            scene_frames = scene.get('frames', [])

            for frame in scene_frames:
                frame_info = {
                    'scene_id': scene_id,
                    'scene_text': scene_text,
                    'scene_note': scene_note,
                    'duration_sec': duration_sec,
                    'frame_id': frame.get('frame_id', 1),
                    'seed': frame.get('seed', self.config.default_seed_start),
                    'prompt': frame.get('prompt', ''),
                    'camera_motion': frame.get('camera_motion', 'static'),
                    'global_frame_index': len(frames)  # 全局帧索引
                }
                frames.append(frame_info)

        return frames

    def _wait_if_needed(self):
        """检查并在必要时等待以避免频率限制"""
        with self._lock:
            current_time = time.time()
            elapsed = current_time - self.last_call_time

            # 计算当前需要的间隔
            current_interval = min(
                self.config.min_interval * (self.config.failure_backoff ** self.consecutive_failures),
                self.config.max_interval
            )

            if elapsed < current_interval:
                wait_time = current_interval - elapsed
                time.sleep(wait_time)

            self.last_call_time = time.time()

    def _record_success(self):
        """记录成功调用"""
        with self._lock:
            self.consecutive_failures = 0
            self.successful_calls += 1
            self.total_calls += 1

    def _record_failure(self) -> bool:
        """记录失败调用，返回是否应继续重试"""
        with self._lock:
            self.consecutive_failures += 1
            self.total_calls += 1
            return self.consecutive_failures < self.config.max_retries

    def _generate_with_retry(
        self,
        image_generator_func: Callable,
        prompt: str,
        output_path: str,
        scene_idx: int,
        seed: int
    ) -> bool:
        """带重试机制的图片生成"""
        for attempt in range(self.config.max_retries):
            try:
                # 等待 API 限制
                self._wait_if_needed()

                # 调用生成函数
                success = image_generator_func(prompt, output_path, scene_idx, seed)

                if success and os.path.exists(output_path):
                    self._record_success()
                    return True
                else:
                    raise Exception("生成失败")

            except Exception as e:
                should_retry = self._record_failure()
                if not should_retry:
                    break

                # 指数退避
                wait_time = (2 ** attempt) + random.uniform(0.5, 1.5)
                time.sleep(wait_time)

        return False

    def generate_frames(
        self,
        script_data: Dict,
        image_generator_func: Callable[[str, str, int, int], bool],
        progress_callback: Optional[Callable[[int, int, str], None]] = None
    ) -> Tuple[List[str], Dict]:
        """
        生成所有帧图片

        Args:
            script_data: JSON 脚本数据
            image_generator_func: 图片生成函数 (prompt, path, scene_idx, seed) -> bool
            progress_callback: 进度回调 (current, total, message)

        Returns:
            (帧文件路径列表, 生成报告)
        """
        self.generation_stats["start_time"] = datetime.now()

        # 解析脚本
        frames = self.parse_script(script_data)
        total_frames = len(frames)

        if total_frames == 0:
            return [], self._generate_report(frames)

        self.generation_stats["total_frames"] = total_frames

        if progress_callback:
            progress_callback(0, 100, f"开始生成 {total_frames} 帧图片...")

        # 创建输出目录
        os.makedirs(self.config.output_dir, exist_ok=True)

        frame_files = []
        current_scene_id = None

        for i, frame_info in enumerate(frames):
            scene_id = frame_info['scene_id']
            frame_id = frame_info['frame_id']
            prompt = frame_info['prompt']
            seed = frame_info['seed']
            camera_motion = frame_info['camera_motion']

            # 更新进度
            progress = (i / total_frames) * 100
            if progress_callback:
                progress_callback(int(progress), 100,
                    f"场景 {scene_id} - 帧 {frame_id} ({camera_motion})...")

            # 记录场景切换
            if current_scene_id != scene_id:
                current_scene_id = scene_id
                self.generation_stats["scenes_processed"] += 1

            # 构建输出路径
            output_path = os.path.join(
                self.config.output_dir,
                f"scene_{scene_id:03d}_frame_{frame_id:03d}.jpg"
            )

            # 生成图片
            success = self._generate_with_retry(
                image_generator_func,
                prompt,
                output_path,
                scene_id - 1,  # scene_idx 从 0 开始
                seed
            )

            if success:
                frame_files.append(output_path)
                self.generation_stats["successful_frames"] += 1
            else:
                # 失败处理：复制上一帧或创建占位图
                if frame_files:
                    import shutil
                    shutil.copy(frame_files[-1], output_path)
                    frame_files.append(output_path)
                else:
                    self._create_placeholder(output_path)
                    frame_files.append(output_path)
                self.generation_stats["failed_frames"] += 1

        # 更新统计
        self.generation_stats["end_time"] = datetime.now()

        # 生成报告
        report = self._generate_report(frames)

        return frame_files, report

    def _create_placeholder(self, output_path: str):
        """创建占位图"""
        try:
            from PIL import Image
            img = Image.new('RGB', (1080, 1920), color=(40, 40, 40))
            img.save(output_path, quality=90)
        except Exception as e:
            print(f"创建占位图失败: {e}")

    def _generate_report(self, frames: List[Dict]) -> Dict:
        """生成生成报告"""
        duration = None
        if self.generation_stats["start_time"] and self.generation_stats["end_time"]:
            duration = (self.generation_stats["end_time"] - self.generation_stats["start_time"]).total_seconds()

        # 统计每场景的帧数
        scene_frame_counts = {}
        for frame in frames:
            scene_id = frame['scene_id']
            if scene_id not in scene_frame_counts:
                scene_frame_counts[scene_id] = 0
            scene_frame_counts[scene_id] += 1

        total = self.generation_stats["total_frames"]
        successful = self.generation_stats["successful_frames"]

        # 转换 datetime 为 ISO 格式字符串
        start_time_str = self.generation_stats["start_time"].isoformat() if self.generation_stats["start_time"] else None
        end_time_str = self.generation_stats["end_time"].isoformat() if self.generation_stats["end_time"] else None

        report = {
            "generation_time": datetime.now().isoformat(),
            "stats": {
                "start_time": start_time_str,
                "end_time": end_time_str,
                "total_frames": self.generation_stats["total_frames"],
                "successful_frames": self.generation_stats["successful_frames"],
                "failed_frames": self.generation_stats["failed_frames"],
                "scenes_processed": self.generation_stats["scenes_processed"],
                "duration_seconds": duration,
                "success_rate": (successful / total * 100) if total > 0 else 0
            },
            "api_stats": {
                "total_calls": self.total_calls,
                "successful_calls": self.successful_calls,
                "success_rate": f"{(self.successful_calls / self.total_calls * 100):.1f}%" if self.total_calls > 0 else "N/A",
                "consecutive_failures": self.consecutive_failures
            },
            "frame_summary": {
                "total_frames": total,
                "scenes": len(scene_frame_counts),
                "frames_per_scene": scene_frame_counts
            },
            "config": {
                "min_interval": self.config.min_interval,
                "max_interval": self.config.max_interval,
                "max_retries": self.config.max_retries
            }
        }

        return report

    def save_report(self, report: Dict, output_path: Optional[str] = None):
        """保存生成报告"""
        if output_path is None:
            output_path = os.path.join(self.config.output_dir, "frame_generation_report.json")

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

        return output_path


# 便捷函数
def generate_frames_from_script(
    script_data: Dict,
    image_generator_func: Callable[[str, str, int, int], bool],
    output_dir: str = "./output",
    progress_callback: Optional[Callable[[int, int, str], None]] = None
) -> Tuple[List[str], Dict]:
    """
    便捷函数：从脚本生成逐帧图片

    Args:
        script_data: JSON 脚本数据
        image_generator_func: 图片生成函数
        output_dir: 输出目录
        progress_callback: 进度回调

    Returns:
        (帧文件路径列表, 生成报告)
    """
    config = FrameBasedConfig(output_dir=output_dir)
    generator = FrameBasedGenerator(config)
    return generator.generate_frames(script_data, image_generator_func, progress_callback)
