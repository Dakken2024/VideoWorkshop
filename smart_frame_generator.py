#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
智能帧序列生成器
根据脚本内容和音频时长，智能规划提示词序列，生成符合视频时长的帧
"""

import os
import json
import math
import random
from typing import List, Dict, Tuple, Optional, Callable
from dataclasses import dataclass
from datetime import datetime


@dataclass
class FrameSequenceConfig:
    """帧序列配置"""
    fps: int = 24
    target_duration: float = 30.0  # 目标视频时长（秒）
    min_frames_per_scene: int = 12  # 每场景最少帧数（0.5秒）
    max_frames_per_scene: int = 72  # 每场景最多帧数（3秒）
    variation_intensity: str = "medium"  # 变化强度: low, medium, high


class SmartFrameGenerator:
    """
    智能帧序列生成器
    
    核心功能：
    1. 分析脚本内容，识别关键场景和时间节点
    2. 根据音频时长智能分配每场景的帧数
    3. 生成渐进式变化的提示词序列
    4. 确保视觉连贯性和叙事完整性
    """
    
    # 摄像机运动变化模板
    CAMERA_MOVEMENTS = {
        "low": [
            "subtle camera drift, minimal movement",
            "gentle static shot, slight breathing motion",
            "soft focus adjustment, atmospheric depth"
        ],
        "medium": [
            "slow push in, revealing details",
            "gentle pan across scene, smooth motion",
            "subtle orbit movement, 3D perspective",
            "gradual zoom out, expanding view",
            "soft rack focus, shifting attention"
        ],
        "high": [
            "dynamic push in, dramatic reveal",
            "sweeping camera movement, cinematic motion",
            "dramatic angle shift, perspective change",
            "rapid zoom transition, energetic feel",
            "complex camera path, multi-axis movement"
        ]
    }
    
    # 光线和氛围变化
    LIGHTING_VARIATIONS = [
        "golden hour lighting, warm tones",
        "soft diffused light, gentle shadows",
        "dramatic side lighting, depth contrast",
        "atmospheric haze, moody ambiance",
        "bright daylight, clear visibility",
        "twilight ambiance, purple sky gradient",
        "overcast soft light, even illumination"
    ]
    
    # 时间变化描述
    TIME_PROGRESSIONS = [
        "early morning, fresh start",
        "midday peak, full brightness",
        "golden afternoon, warm glow",
        "evening transition, fading light",
        "nightfall, artificial illumination"
    ]
    
    def __init__(self, config: Optional[FrameSequenceConfig] = None):
        self.config = config or FrameSequenceConfig()
        self.logger = self._setup_logger()
    
    def _setup_logger(self):
        """设置日志"""
        import logging
        logger = logging.getLogger(__name__)
        return logger
    
    def analyze_script(self, scenes: List[Dict]) -> Dict:
        """
        分析脚本内容，识别关键场景特征
        
        Args:
            scenes: 场景列表
            
        Returns:
            分析结果字典
        """
        analysis = {
            "total_scenes": len(scenes),
            "total_text_length": sum(len(s.get("text", "")) for s in scenes),
            "scene_complexities": [],
            "key_moments": [],
            "narrative_arc": []
        }
        
        for i, scene in enumerate(scenes):
            text = scene.get("text", "")
            prompt = scene.get("prompt", "")
            
            # 分析场景复杂度
            complexity = self._calculate_scene_complexity(text, prompt)
            analysis["scene_complexities"].append({
                "scene_index": i,
                "complexity": complexity,
                "text_length": len(text),
                "has_action": self._has_action_keywords(text),
                "has_emotion": self._has_emotion_keywords(text)
            })
            
            # 识别关键转折点
            if complexity > 0.7 or self._is_transition_scene(text):
                analysis["key_moments"].append(i)
        
        return analysis
    
    def _calculate_scene_complexity(self, text: str, prompt: str) -> float:
        """计算场景复杂度 (0-1)"""
        complexity = 0.0
        combined = f"{text} {prompt}".lower()
        
        # 复杂描述关键词
        complex_keywords = [
            "复杂", "详细", "精细", "多层次", "丰富",
            "complex", "detailed", "intricate", "layered", "rich"
        ]
        
        for kw in complex_keywords:
            if kw in combined:
                complexity += 0.1
        
        # 动作描述增加复杂度
        action_keywords = [
            "动作", "运动", "变化", "转换", "动态",
            "action", "movement", "motion", "dynamic", "transition"
        ]
        
        for kw in action_keywords:
            if kw in combined:
                complexity += 0.15
        
        return min(complexity, 1.0)
    
    def _has_action_keywords(self, text: str) -> bool:
        """检查是否包含动作关键词"""
        action_words = ["开始", "进行", "发展", "变化", "出现", "消失", "移动", "转变"]
        return any(word in text for word in action_words)
    
    def _has_emotion_keywords(self, text: str) -> bool:
        """检查是否包含情感关键词"""
        emotion_words = ["重要", "关键", "突破", "成功", "失败", "挑战", "机遇"]
        return any(word in text for word in emotion_words)
    
    def _is_transition_scene(self, text: str) -> bool:
        """判断是否为过渡场景"""
        transition_words = ["随后", "接着", "之后", "然后", "接下来", "转而", "最终"]
        return any(word in text for word in transition_words)
    
    def calculate_frame_distribution(self, scenes: List[Dict], 
                                     target_duration: float) -> List[int]:
        """
        智能计算每场景应分配的帧数
        
        Args:
            scenes: 场景列表
            target_duration: 目标视频时长（秒）
            
        Returns:
            每场景的帧数列表
        """
        total_frames_needed = int(target_duration * self.config.fps)
        num_scenes = len(scenes)
        
        if num_scenes == 0:
            return []
        
        # 分析场景
        analysis = self.analyze_script(scenes)
        complexities = [s["complexity"] for s in analysis["scene_complexities"]]
        
        # 基础分配：平均分配
        base_frames_per_scene = total_frames_needed // num_scenes
        
        # 根据复杂度调整
        frame_distribution = []
        total_complexity = sum(complexities) if sum(complexities) > 0 else num_scenes
        
        for i, scene in enumerate(scenes):
            complexity = complexities[i] if i < len(complexities) else 0.5
            
            # 复杂度越高，分配越多帧
            complexity_weight = complexity / total_complexity if total_complexity > 0 else 1.0 / num_scenes
            frames = int(total_frames_needed * complexity_weight)
            
            # 确保在最小和最大范围内
            frames = max(self.config.min_frames_per_scene, 
                        min(self.config.max_frames_per_scene, frames))
            
            frame_distribution.append(frames)
        
        # 调整总和以匹配目标
        current_total = sum(frame_distribution)
        diff = total_frames_needed - current_total
        
        # 将差值分配到各个场景
        if diff != 0:
            for i in range(abs(diff)):
                idx = i % num_scenes
                if diff > 0:
                    frame_distribution[idx] += 1
                else:
                    frame_distribution[idx] = max(self.config.min_frames_per_scene, 
                                                  frame_distribution[idx] - 1)
        
        return frame_distribution
    
    def generate_progressive_prompts(self, base_prompt: str, 
                                     num_frames: int,
                                     scene_index: int,
                                     total_scenes: int) -> List[str]:
        """
        生成渐进式变化的提示词序列
        
        Args:
            base_prompt: 基础提示词
            num_frames: 需要生成的帧数
            scene_index: 场景索引
            total_scenes: 总场景数
            
        Returns:
            提示词列表
        """
        prompts = []
        
        # 选择变化强度
        movements = self.CAMERA_MOVEMENTS[self.config.variation_intensity]
        
        # 计算场景在整体叙事中的位置 (0-1)
        narrative_position = scene_index / total_scenes if total_scenes > 1 else 0.5
        
        # 选择时间氛围
        time_variation = self.TIME_PROGRESSIONS[int(narrative_position * (len(self.TIME_PROGRESSIONS) - 1))]
        
        for frame_i in range(num_frames):
            # 计算帧在场景中的进度 (0-1)
            frame_progress = frame_i / num_frames if num_frames > 1 else 0
            
            # 选择摄像机运动
            movement = movements[frame_i % len(movements)]
            
            # 选择光线变化
            lighting = self.LIGHTING_VARIATIONS[frame_i % len(self.LIGHTING_VARIATIONS)]
            
            # 构建渐进式提示词
            progressive_prompt = self._build_progressive_prompt(
                base_prompt, 
                movement, 
                lighting, 
                time_variation,
                frame_progress,
                frame_i,
                num_frames
            )
            
            prompts.append(progressive_prompt)
        
        return prompts
    
    def _build_progressive_prompt(self, base_prompt: str, 
                                  movement: str,
                                  lighting: str,
                                  time_variation: str,
                                  progress: float,
                                  frame_index: int,
                                  total_frames: int) -> str:
        """构建渐进式提示词"""
        
        # 基础描述
        parts = [base_prompt]
        
        # 添加摄像机运动
        parts.append(movement)
        
        # 添加光线变化（根据进度选择）
        if progress < 0.33:
            parts.append("opening composition, establishing shot")
        elif progress < 0.66:
            parts.append("developing view, building interest")
        else:
            parts.append("resolving composition, concluding view")
        
        # 添加时间氛围
        parts.append(time_variation)
        
        # 添加电影级质量描述
        parts.append("cinematic quality, 35mm film look, professional cinematography")
        
        # 添加帧信息
        parts.append(f"frame {frame_index + 1} of {total_frames}")
        
        return ", ".join(parts)
    
    def generate_frame_sequence(self,
                               scenes: List[Dict],
                               target_duration: float,
                               image_generator_func: Callable[[str, str], bool],
                               output_dir: str,
                               progress_callback: Optional[Callable[[int, int, str], None]] = None) -> List[str]:
        """
        生成完整的帧序列
        
        Args:
            scenes: 场景列表
            target_duration: 目标视频时长
            image_generator_func: 图片生成函数
            output_dir: 输出目录
            progress_callback: 进度回调
            
        Returns:
            所有帧文件路径列表
        """
        all_frame_files = []
        
        # 分析脚本
        if progress_callback:
            progress_callback(0, 3, "分析脚本内容...")
        
        analysis = self.analyze_script(scenes)
        self.logger.info(f"脚本分析完成: {analysis['total_scenes']} 个场景")
        
        # 计算帧分配
        if progress_callback:
            progress_callback(1, 3, "计算帧分配...")
        
        frame_distribution = self.calculate_frame_distribution(scenes, target_duration)
        total_frames = sum(frame_distribution)
        
        self.logger.info(f"总帧数: {total_frames}, 目标时长: {target_duration}s")
        self.logger.info(f"每场景帧数: {frame_distribution}")
        
        # 生成帧
        if progress_callback:
            progress_callback(2, 3, "生成帧序列...")
        
        generated_count = 0
        
        for scene_idx, scene in enumerate(scenes):
            num_frames = frame_distribution[scene_idx]
            base_prompt = scene.get("prompt", "")
            scene_id = scene.get("scene_id", scene_idx + 1)
            
            self.logger.info(f"场景 {scene_id}: 生成 {num_frames} 帧")
            
            # 生成渐进式提示词
            prompts = self.generate_progressive_prompts(
                base_prompt, 
                num_frames, 
                scene_idx, 
                len(scenes)
            )
            
            # 生成每帧
            for frame_i, prompt in enumerate(prompts):
                frame_path = os.path.join(
                    output_dir,
                    f"scene_{scene_idx:03d}_frame_{frame_i:03d}.jpg"
                )
                
                # 生成图片 - 传入 scene_idx 以便获取场景信息
                success = image_generator_func(prompt, frame_path, scene_idx)
                
                if success and os.path.exists(frame_path):
                    all_frame_files.append(frame_path)
                    generated_count += 1
                else:
                    # 如果失败，复制上一帧或创建占位图
                    if all_frame_files:
                        import shutil
                        shutil.copy(all_frame_files[-1], frame_path)
                        all_frame_files.append(frame_path)
                        generated_count += 1
                    else:
                        # 创建占位图
                        self._create_placeholder(frame_path)
                        all_frame_files.append(frame_path)
                        generated_count += 1
                
                # 更新进度
                if progress_callback and generated_count % 10 == 0:
                    progress = (generated_count / total_frames) * 100
                    progress_callback(2, 3, f"生成进度: {generated_count}/{total_frames} ({progress:.1f}%)")
        
        if progress_callback:
            progress_callback(3, 3, "帧序列生成完成")
        
        self.logger.info(f"帧序列生成完成: {len(all_frame_files)} 帧")
        return all_frame_files
    
    def _create_placeholder(self, output_path: str):
        """创建占位图"""
        try:
            from PIL import Image
            img = Image.new('RGB', (1080, 1920), color=(40, 40, 40))
            img.save(output_path, quality=90)
        except Exception as e:
            self.logger.error(f"创建占位图失败: {e}")
    
    def save_frame_plan(self, output_file: str, scenes: List[Dict], 
                       frame_distribution: List[int]):
        """保存帧生成计划"""
        plan = {
            "generation_time": datetime.now().isoformat(),
            "config": {
                "fps": self.config.fps,
                "target_duration": self.config.target_duration,
                "min_frames_per_scene": self.config.min_frames_per_scene,
                "max_frames_per_scene": self.config.max_frames_per_scene
            },
            "total_frames": sum(frame_distribution),
            "scenes": []
        }
        
        for i, (scene, frames) in enumerate(zip(scenes, frame_distribution)):
            plan["scenes"].append({
                "scene_index": i,
                "scene_id": scene.get("scene_id", i + 1),
                "text_preview": scene.get("text", "")[:50],
                "frame_count": frames,
                "duration_seconds": frames / self.config.fps
            })
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(plan, f, ensure_ascii=False, indent=2)
        
        self.logger.info(f"帧计划已保存: {output_file}")


# 便捷函数
def generate_smart_frames(
    scenes: List[Dict],
    target_duration: float,
    image_generator_func: Callable[[str, str], bool],
    output_dir: str,
    fps: int = 24,
    progress_callback: Optional[Callable[[int, int, str], None]] = None
) -> List[str]:
    """
    便捷函数：生成智能帧序列
    
    Args:
        scenes: 场景列表
        target_duration: 目标视频时长（秒）
        image_generator_func: 图片生成函数
        output_dir: 输出目录
        fps: 帧率
        progress_callback: 进度回调
        
    Returns:
        所有帧文件路径列表
    """
    config = FrameSequenceConfig(
        fps=fps,
        target_duration=target_duration
    )
    
    generator = SmartFrameGenerator(config)
    return generator.generate_frame_sequence(
        scenes, target_duration, image_generator_func, output_dir, progress_callback
    )
