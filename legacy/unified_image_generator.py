#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一图片生成器 - 整合电影效果和智能帧序列生成功能
包含 API 调用频率限制和重试机制，适配 pollinations.ai 免费版限制
"""

import os
import json
import time
import random
import threading
from datetime import datetime
from typing import List, Dict, Callable, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum


class GenerationMode(Enum):
    """生成模式"""
    STANDARD = "standard"           # 标准单帧生成
    CINEMATIC = "cinematic"         # 电影效果多帧生成
    SMART = "smart"                 # 智能帧序列生成
    UNIFIED = "unified"             # 统一智能模式（推荐）


@dataclass
class APIRateLimiter:
    """API 调用频率限制器 - 针对 pollinations.ai 免费版优化"""
    
    # 基础配置
    min_interval: float = 3.0       # 最小调用间隔（秒）
    max_interval: float = 15.0      # 最大调用间隔（秒）
    failure_backoff: float = 2.0    # 失败后的退避倍数
    max_retries: int = 3            # 最大重试次数
    
    # 状态跟踪
    last_call_time: float = field(default_factory=lambda: 0.0)
    consecutive_failures: int = 0
    total_calls: int = 0
    successful_calls: int = 0
    
    # 线程锁
    _lock: threading.Lock = field(default_factory=threading.Lock)
    
    def wait_if_needed(self):
        """检查并在必要时等待以避免频率限制"""
        with self._lock:
            current_time = time.time()
            elapsed = current_time - self.last_call_time
            
            # 计算当前需要的间隔
            current_interval = min(
                self.min_interval * (self.failure_backoff ** self.consecutive_failures),
                self.max_interval
            )
            
            if elapsed < current_interval:
                wait_time = current_interval - elapsed
                time.sleep(wait_time)
            
            self.last_call_time = time.time()
    
    def record_success(self):
        """记录成功调用"""
        with self._lock:
            self.consecutive_failures = 0
            self.successful_calls += 1
            self.total_calls += 1
    
    def record_failure(self) -> bool:
        """记录失败调用，返回是否应继续重试"""
        with self._lock:
            self.consecutive_failures += 1
            self.total_calls += 1
            return self.consecutive_failures < self.max_retries
    
    def get_stats(self) -> Dict:
        """获取统计信息"""
        with self._lock:
            success_rate = (self.successful_calls / self.total_calls * 100) if self.total_calls > 0 else 0
            return {
                "total_calls": self.total_calls,
                "successful_calls": self.successful_calls,
                "success_rate": f"{success_rate:.1f}%",
                "consecutive_failures": self.consecutive_failures
            }


@dataclass
class UnifiedGenerationConfig:
    """统一生成配置"""
    
    # 模式选择
    mode: GenerationMode = GenerationMode.UNIFIED
    
    # 帧率设置
    fps: int = 24
    
    # 帧数配置
    frames_per_scene: int = 3       # 每场景生成的帧数（电影效果模式）
    min_frames_per_scene: int = 12  # 智能模式：每场景最少帧数
    max_frames_per_scene: int = 72  # 智能模式：每场景最多帧数
    
    # 视频时长（用于智能计算）
    target_duration: float = 30.0   # 目标视频时长（秒）
    
    # 连贯性控制
    consistency_seed: Optional[int] = None  # 一致性种子
    variation_intensity: str = "medium"     # 变化强度: low, medium, high
    
    # API 限制
    enable_rate_limiting: bool = True
    api_rate_limiter: Optional[APIRateLimiter] = None
    
    # 输出配置
    output_dir: str = "./output"
    
    def __post_init__(self):
        if self.api_rate_limiter is None and self.enable_rate_limiting:
            self.api_rate_limiter = APIRateLimiter()


class UnifiedImageGenerator:
    """
    统一图片生成器
    
    整合功能：
    1. 标准单帧生成
    2. 电影效果多帧生成（带摄像机运动变化）
    3. 智能帧序列生成（根据时长自动规划）
    4. 统一智能模式（自动选择最佳策略）
    
    特性：
    - API 调用频率限制和重试机制
    - 帧间连贯性控制
    - 渐进式提示词生成
    - 失败恢复和占位图 fallback
    """
    
    # 摄像机运动变化模板
    CAMERA_VARIATIONS = {
        "low": [
            "subtle camera drift, minimal movement, maintaining composition",
            "gentle static shot, slight breathing motion, stable framing",
            "soft focus adjustment, atmospheric depth, consistent lighting"
        ],
        "medium": [
            "slow push in 5%, revealing subtle details, maintaining perspective",
            "gentle pan right 3%, smooth motion, continuous scene",
            "subtle zoom out 5%, expanding context, matching lighting",
            "soft rack focus, shifting depth, same atmosphere",
            "slight angle adjustment 2 degrees, consistent viewpoint"
        ],
        "high": [
            "dynamic push in 10%, dramatic reveal, matching color grade",
            "sweeping pan 8%, cinematic motion, continuous lighting",
            "dramatic angle shift 5 degrees, perspective change, coherent scene",
            "zoom transition 15%, energetic feel, consistent palette",
            "orbital movement 10 degrees, multi-axis motion, unified atmosphere"
        ]
    }
    
    # 连贯性增强提示词
    COHERENCE_PROMPTS = [
        "consistent lighting throughout",
        "matching color palette",
        "coherent visual style",
        "continuous scene composition",
        "stable camera perspective",
        "uniform atmosphere"
    ]
    
    # 电影效果增强
    CINEMATIC_ENHANCEMENTS = [
        "cinematic composition, rule of thirds",
        "35mm film look, cinematic color grading",
        "professional cinematography, shallow depth of field",
        "dramatic lighting, cinematic atmosphere",
        "film grain texture, movie quality"
    ]
    
    def __init__(self, config: Optional[UnifiedGenerationConfig] = None):
        self.config = config or UnifiedGenerationConfig()
        self.rate_limiter = self.config.api_rate_limiter
        
        # 创建输出目录
        os.makedirs(self.config.output_dir, exist_ok=True)
        
        # 生成状态跟踪
        self.generation_stats = {
            "start_time": None,
            "end_time": None,
            "total_frames": 0,
            "successful_frames": 0,
            "failed_frames": 0,
            "scenes_processed": 0
        }
    
    def analyze_content(self, scenes: List[Dict], md_content: str = "") -> Dict:
        """
        分析脚本和 Markdown 内容，确定最佳生成策略
        
        Args:
            scenes: JSON 场景列表
            md_content: Markdown 内容（可选）
            
        Returns:
            分析结果和建议配置
        """
        analysis = {
            "total_scenes": len(scenes),
            "total_text_length": sum(len(s.get("text", "")) for s in scenes),
            "has_prompts": all(s.get("prompt") for s in scenes),
            "scene_durations": [s.get("duration_sec", 5) for s in scenes],
            "estimated_video_duration": sum(s.get("duration_sec", 5) for s in scenes),
            "complexity_scores": [],
            "recommended_mode": GenerationMode.UNIFIED,
            "recommended_frames_per_scene": 3
        }
        
        # 分析每个场景的复杂度
        for i, scene in enumerate(scenes):
            text = scene.get("text", "")
            prompt = scene.get("prompt", "")
            
            # 计算复杂度分数
            complexity = self._calculate_complexity(text, prompt)
            analysis["complexity_scores"].append({
                "scene_index": i,
                "scene_id": scene.get("scene_id", i + 1),
                "complexity": complexity,
                "text_length": len(text),
                "duration": scene.get("duration_sec", 5)
            })
        
        # 根据分析结果推荐配置
        avg_complexity = sum(c["complexity"] for c in analysis["complexity_scores"]) / len(scenes) if scenes else 0.5
        
        if avg_complexity > 0.7:
            analysis["recommended_frames_per_scene"] = 5
            analysis["variation_intensity"] = "high"
        elif avg_complexity < 0.3:
            analysis["recommended_frames_per_scene"] = 2
            analysis["variation_intensity"] = "low"
        else:
            analysis["recommended_frames_per_scene"] = 3
            analysis["variation_intensity"] = "medium"
        
        # 根据视频时长推荐模式
        if analysis["estimated_video_duration"] < 20:
            analysis["recommended_mode"] = GenerationMode.CINEMATIC
        elif analysis["estimated_video_duration"] > 60:
            analysis["recommended_mode"] = GenerationMode.SMART
        else:
            analysis["recommended_mode"] = GenerationMode.UNIFIED
        
        return analysis
    
    def _calculate_complexity(self, text: str, prompt: str) -> float:
        """计算场景复杂度 (0-1)"""
        complexity = 0.3  # 基础复杂度
        combined = f"{text} {prompt}".lower()
        
        # 复杂描述关键词
        complex_keywords = [
            "复杂", "详细", "精细", "多层次", "丰富", " intricate", " detailed",
            "complex", "layered", "rich", "elaborate", "sophisticated"
        ]
        
        for kw in complex_keywords:
            if kw in combined:
                complexity += 0.1
        
        # 动作和变化描述
        action_keywords = [
            "动作", "运动", "变化", "转换", "动态", "action", "movement",
            "motion", "dynamic", "transition", "changing", "evolving"
        ]
        
        for kw in action_keywords:
            if kw in combined:
                complexity += 0.15
        
        return min(complexity, 1.0)
    
    def generate_unified_frames(
        self,
        scenes: List[Dict],
        image_generator_func: Callable[[str, str, int, Optional[int]], bool],
        progress_callback: Optional[Callable[[int, int, str], None]] = None,
        md_content: str = ""
    ) -> Tuple[List[str], Dict]:
        """
        统一帧生成入口 - 一键生成所有帧
        
        Args:
            scenes: 场景列表
            image_generator_func: 图片生成函数 (prompt, path, scene_idx, seed) -> bool
            progress_callback: 进度回调 (current, total, message)
            md_content: Markdown 内容（用于增强分析）
            
        Returns:
            (帧文件路径列表, 生成统计信息)
        """
        self.generation_stats["start_time"] = datetime.now()
        
        # 分析内容
        if progress_callback:
            progress_callback(0, 100, "分析内容并规划生成策略...")
        
        analysis = self.analyze_content(scenes, md_content)
        
        # 根据分析结果自动选择模式
        mode = self.config.mode
        if mode == GenerationMode.UNIFIED:
            mode = analysis["recommended_mode"]
        
        # 生成帧
        if mode == GenerationMode.STANDARD:
            frame_files = self._generate_standard_frames(
                scenes, image_generator_func, progress_callback
            )
        elif mode == GenerationMode.CINEMATIC:
            frame_files = self._generate_cinematic_frames(
                scenes, image_generator_func, progress_callback
            )
        elif mode == GenerationMode.SMART:
            frame_files = self._generate_smart_frames(
                scenes, image_generator_func, progress_callback
            )
        else:
            # 统一模式：智能选择最佳策略
            frame_files = self._generate_unified_frames_internal(
                scenes, image_generator_func, progress_callback, analysis
            )
        
        # 更新统计
        self.generation_stats["end_time"] = datetime.now()
        self.generation_stats["total_frames"] = len(frame_files)
        
        # 生成报告
        report = self._generate_report(analysis, mode)
        
        return frame_files, report
    
    def _generate_standard_frames(
        self,
        scenes: List[Dict],
        image_generator_func: Callable,
        progress_callback: Optional[Callable] = None
    ) -> List[str]:
        """生成标准单帧"""
        frame_files = []
        total = len(scenes)
        
        for i, scene in enumerate(scenes):
            if progress_callback:
                progress = (i / total) * 100
                progress_callback(int(progress), 100, f"生成场景 {i+1}/{total}...")
            
            # 等待 API 限制
            if self.rate_limiter:
                self.rate_limiter.wait_if_needed()
            
            prompt = scene.get("prompt", "")
            enhanced_prompt = self._enhance_prompt_for_cinema(prompt, i, total)
            
            output_path = os.path.join(
                self.config.output_dir,
                f"scene_{i:03d}.jpg"
            )
            
            # 生成，带重试
            success = self._generate_with_retry(
                image_generator_func, enhanced_prompt, output_path, i
            )
            
            if success:
                frame_files.append(output_path)
                self.generation_stats["successful_frames"] += 1
            else:
                # 创建占位图
                self._create_placeholder(output_path)
                frame_files.append(output_path)
                self.generation_stats["failed_frames"] += 1
            
            self.generation_stats["scenes_processed"] += 1
        
        return frame_files
    
    def _generate_cinematic_frames(
        self,
        scenes: List[Dict],
        image_generator_func: Callable,
        progress_callback: Optional[Callable] = None
    ) -> List[str]:
        """生成电影效果多帧"""
        frame_files = []
        total_scenes = len(scenes)
        frames_per_scene = self.config.frames_per_scene
        total_frames = total_scenes * frames_per_scene
        
        variations = self.CAMERA_VARIATIONS[self.config.variation_intensity]
        
        for scene_idx, scene in enumerate(scenes):
            base_prompt = scene.get("prompt", "")
            scene_id = scene.get("scene_id", scene_idx + 1)
            
            # 为当前场景生成多帧
            for frame_i in range(frames_per_scene):
                current_frame = scene_idx * frames_per_scene + frame_i
                
                if progress_callback:
                    progress = (current_frame / total_frames) * 100
                    progress_callback(
                        int(progress), 100,
                        f"场景 {scene_id}: 帧 {frame_i+1}/{frames_per_scene}..."
                    )
                
                # 等待 API 限制
                if self.rate_limiter:
                    self.rate_limiter.wait_if_needed()
                
                # 构建带变化的提示词
                variation = variations[frame_i % len(variations)]
                varied_prompt = self._build_cinematic_prompt(
                    base_prompt, variation, frame_i, frames_per_scene, scene_idx, total_scenes
                )
                
                output_path = os.path.join(
                    self.config.output_dir,
                    f"scene_{scene_idx:03d}_frame_{frame_i:03d}.jpg"
                )
                
                # 使用场景特定的种子以确保连贯性
                seed = self._generate_scene_seed(scene_idx, frame_i)
                
                # 生成，带重试
                success = self._generate_with_retry(
                    image_generator_func, varied_prompt, output_path, scene_idx, seed
                )
                
                if success:
                    frame_files.append(output_path)
                    self.generation_stats["successful_frames"] += 1
                else:
                    # 尝试复制上一帧
                    if frame_i > 0 and frame_files:
                        import shutil
                        prev_frame = os.path.join(
                            self.config.output_dir,
                            f"scene_{scene_idx:03d}_frame_{frame_i-1:03d}.jpg"
                        )
                        if os.path.exists(prev_frame):
                            shutil.copy(prev_frame, output_path)
                            frame_files.append(output_path)
                            self.generation_stats["successful_frames"] += 1
                        else:
                            self._create_placeholder(output_path)
                            frame_files.append(output_path)
                            self.generation_stats["failed_frames"] += 1
                    else:
                        self._create_placeholder(output_path)
                        frame_files.append(output_path)
                        self.generation_stats["failed_frames"] += 1
            
            self.generation_stats["scenes_processed"] += 1
        
        return frame_files
    
    def _generate_smart_frames(
        self,
        scenes: List[Dict],
        image_generator_func: Callable,
        progress_callback: Optional[Callable] = None
    ) -> List[str]:
        """生成智能帧序列"""
        # 计算帧分配
        total_duration = self.config.target_duration
        num_scenes = len(scenes)
        
        # 智能分配帧数
        frame_distribution = self._calculate_smart_frame_distribution(scenes, total_duration)
        total_frames = sum(frame_distribution)
        
        frame_files = []
        current_frame = 0
        
        variations = self.CAMERA_VARIATIONS[self.config.variation_intensity]
        
        for scene_idx, (scene, num_frames) in enumerate(zip(scenes, frame_distribution)):
            base_prompt = scene.get("prompt", "")
            scene_id = scene.get("scene_id", scene_idx + 1)
            
            for frame_i in range(num_frames):
                current_frame += 1
                
                if progress_callback:
                    progress = (current_frame / total_frames) * 100
                    progress_callback(
                        int(progress), 100,
                        f"场景 {scene_id}: 帧 {frame_i+1}/{num_frames} (总进度 {current_frame}/{total_frames})..."
                    )
                
                # 等待 API 限制
                if self.rate_limiter:
                    self.rate_limiter.wait_if_needed()
                
                # 构建渐进式提示词
                frame_progress = frame_i / num_frames if num_frames > 1 else 0
                variation = variations[frame_i % len(variations)]
                
                progressive_prompt = self._build_progressive_prompt(
                    base_prompt, variation, frame_progress, frame_i, num_frames, scene_idx, len(scenes)
                )
                
                output_path = os.path.join(
                    self.config.output_dir,
                    f"scene_{scene_idx:03d}_frame_{frame_i:03d}.jpg"
                )
                
                # 使用场景特定的种子
                seed = self._generate_scene_seed(scene_idx, frame_i)
                
                # 生成，带重试
                success = self._generate_with_retry(
                    image_generator_func, progressive_prompt, output_path, scene_idx, seed
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
            
            self.generation_stats["scenes_processed"] += 1
        
        return frame_files
    
    def _generate_unified_frames_internal(
        self,
        scenes: List[Dict],
        image_generator_func: Callable,
        progress_callback: Optional[Callable],
        analysis: Dict
    ) -> List[str]:
        """统一模式内部实现 - 智能选择最佳策略"""
        
        # 根据分析结果选择策略
        avg_duration = analysis["estimated_video_duration"] / len(scenes) if scenes else 5
        
        if avg_duration < 3:  # 短场景使用电影效果
            self.config.frames_per_scene = analysis.get("recommended_frames_per_scene", 3)
            return self._generate_cinematic_frames(scenes, image_generator_func, progress_callback)
        elif avg_duration > 8:  # 长场景使用智能帧分配
            return self._generate_smart_frames(scenes, image_generator_func, progress_callback)
        else:  # 中等场景使用标准生成
            return self._generate_standard_frames(scenes, image_generator_func, progress_callback)
    
    def _generate_with_retry(
        self,
        image_generator_func: Callable,
        prompt: str,
        output_path: str,
        scene_idx: int,
        seed: Optional[int] = None
    ) -> bool:
        """带重试机制的图片生成"""
        max_retries = self.rate_limiter.max_retries if self.rate_limiter else 3
        
        for attempt in range(max_retries):
            try:
                success = image_generator_func(prompt, output_path, scene_idx, seed)
                
                if success and os.path.exists(output_path):
                    if self.rate_limiter:
                        self.rate_limiter.record_success()
                    return True
                else:
                    raise Exception("生成失败")
                    
            except Exception as e:
                if self.rate_limiter:
                    should_retry = self.rate_limiter.record_failure()
                    if not should_retry:
                        break
                
                # 指数退避
                wait_time = (2 ** attempt) + random.uniform(0.5, 1.5)
                time.sleep(wait_time)
        
        return False
    
    def _build_cinematic_prompt(
        self,
        base_prompt: str,
        variation: str,
        frame_idx: int,
        total_frames: int,
        scene_idx: int,
        total_scenes: int
    ) -> str:
        """构建电影效果提示词"""
        parts = [base_prompt]
        
        # 添加摄像机运动
        parts.append(variation)
        
        # 添加连贯性描述
        coherence = self.COHERENCE_PROMPTS[scene_idx % len(self.COHERENCE_PROMPTS)]
        parts.append(coherence)
        
        # 添加电影效果增强
        cinematic = self.CINEMATIC_ENHANCEMENTS[frame_idx % len(self.CINEMATIC_ENHANCEMENTS)]
        parts.append(cinematic)
        
        # 添加帧信息
        parts.append(f"frame {frame_idx + 1} of {total_frames}, scene {scene_idx + 1} of {total_scenes}")
        
        return ", ".join(parts)
    
    def _build_progressive_prompt(
        self,
        base_prompt: str,
        variation: str,
        progress: float,
        frame_idx: int,
        total_frames: int,
        scene_idx: int,
        total_scenes: int
    ) -> str:
        """构建渐进式提示词"""
        parts = [base_prompt]
        
        # 添加摄像机运动
        parts.append(variation)
        
        # 根据进度添加阶段描述
        if progress < 0.33:
            parts.append("opening composition, establishing shot, initial view")
        elif progress < 0.66:
            parts.append("developing view, building interest, mid-sequence")
        else:
            parts.append("resolving composition, concluding view, final frame")
        
        # 添加连贯性
        coherence = self.COHERENCE_PROMPTS[frame_idx % len(self.COHERENCE_PROMPTS)]
        parts.append(coherence)
        
        # 添加电影效果
        cinematic = self.CINEMATIC_ENHANCEMENTS[frame_idx % len(self.CINEMATIC_ENHANCEMENTS)]
        parts.append(cinematic)
        
        # 帧信息
        parts.append(f"frame {frame_idx + 1} of {total_frames}")
        
        return ", ".join(parts)
    
    def _enhance_prompt_for_cinema(self, prompt: str, scene_idx: int, total_scenes: int) -> str:
        """为标准生成增强提示词"""
        parts = [prompt]
        
        # 添加电影效果
        cinematic = self.CINEMATIC_ENHANCEMENTS[scene_idx % len(self.CINEMATIC_ENHANCEMENTS)]
        parts.append(cinematic)
        
        # 添加连贯性
        coherence = self.COHERENCE_PROMPTS[scene_idx % len(self.COHERENCE_PROMPTS)]
        parts.append(coherence)
        
        return ", ".join(parts)
    
    def _calculate_smart_frame_distribution(self, scenes: List[Dict], target_duration: float) -> List[int]:
        """智能计算帧分配"""
        total_frames_needed = int(target_duration * self.config.fps)
        num_scenes = len(scenes)
        
        if num_scenes == 0:
            return []
        
        # 基础分配
        base_frames = total_frames_needed // num_scenes
        
        distribution = []
        for scene in scenes:
            # 根据场景时长调整
            scene_duration = scene.get("duration_sec", 5)
            duration_ratio = scene_duration / (target_duration / num_scenes)
            
            frames = int(base_frames * duration_ratio)
            
            # 限制在范围内
            frames = max(self.config.min_frames_per_scene,
                        min(self.config.max_frames_per_scene, frames))
            
            distribution.append(frames)
        
        # 调整总和
        current_total = sum(distribution)
        diff = total_frames_needed - current_total
        
        if diff != 0:
            for i in range(abs(diff)):
                idx = i % num_scenes
                if diff > 0:
                    distribution[idx] += 1
                else:
                    distribution[idx] = max(self.config.min_frames_per_scene,
                                          distribution[idx] - 1)
        
        return distribution
    
    def _generate_scene_seed(self, scene_idx: int, frame_idx: int) -> int:
        """生成场景特定的种子以确保连贯性"""
        base_seed = self.config.consistency_seed or 42
        return base_seed + scene_idx * 1000 + frame_idx
    
    def _create_placeholder(self, output_path: str):
        """创建占位图"""
        try:
            from PIL import Image
            img = Image.new('RGB', (1080, 1920), color=(40, 40, 40))
            img.save(output_path, quality=90)
        except Exception as e:
            print(f"创建占位图失败: {e}")
    
    def _generate_report(self, analysis: Dict, mode: GenerationMode) -> Dict:
        """生成生成报告"""
        duration = None
        if self.generation_stats["start_time"] and self.generation_stats["end_time"]:
            duration = (self.generation_stats["end_time"] - self.generation_stats["start_time"]).total_seconds()
        
        report = {
            "generation_time": datetime.now().isoformat(),
            "mode_used": mode.value,
            "analysis": analysis,
            "stats": {
                **self.generation_stats,
                "duration_seconds": duration,
                "success_rate": (
                    self.generation_stats["successful_frames"] / self.generation_stats["total_frames"] * 100
                    if self.generation_stats["total_frames"] > 0 else 0
                )
            },
            "api_stats": self.rate_limiter.get_stats() if self.rate_limiter else None,
            "config": {
                "fps": self.config.fps,
                "frames_per_scene": self.config.frames_per_scene,
                "variation_intensity": self.config.variation_intensity
            }
        }
        
        return report
    
    def save_report(self, report: Dict, output_path: Optional[str] = None):
        """保存生成报告"""
        if output_path is None:
            output_path = os.path.join(self.config.output_dir, "generation_report.json")
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        return output_path


# 便捷函数
def generate_images_unified(
    scenes: List[Dict],
    image_generator_func: Callable[[str, str, int, Optional[int]], bool],
    output_dir: str = "./output",
    mode: GenerationMode = GenerationMode.UNIFIED,
    progress_callback: Optional[Callable[[int, int, str], None]] = None,
    md_content: str = "",
    target_duration: float = 30.0
) -> Tuple[List[str], Dict]:
    """
    便捷函数：统一生成图片
    
    Args:
        scenes: 场景列表
        image_generator_func: 图片生成函数
        output_dir: 输出目录
        mode: 生成模式
        progress_callback: 进度回调
        md_content: Markdown 内容
        target_duration: 目标视频时长
        
    Returns:
        (帧文件路径列表, 生成报告)
    """
    config = UnifiedGenerationConfig(
        mode=mode,
        output_dir=output_dir,
        target_duration=target_duration,
        enable_rate_limiting=True
    )
    
    generator = UnifiedImageGenerator(config)
    return generator.generate_unified_frames(
        scenes, image_generator_func, progress_callback, md_content
    )
