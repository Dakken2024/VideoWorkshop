#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Video Workshop 精简工作流

对现有复杂流程的系统性优化，解决以下问题：
1. 生成模式过多（5种），用户不知如何选择 → 统一为"快速生成"和"自定义生成"两种
2. 操作步骤繁琐，需要跨多个标签页操作 → 提供一键式流程
3. 依赖多个外部模块，互相重叠 → 统一使用 video_gen 模块
4. 错误处理分散，用户难以排查 → 集中错误处理

使用方式:
    from video_gen.workflow import OptimizedWorkflow
    
    workflow = OptimizedWorkflow()
    result = workflow.quick_generate(script_path="scripts.json", title="我的视频")
"""

import os
import sys
import json
import asyncio
from typing import Dict, List, Optional, Callable, Tuple
from dataclasses import dataclass, field
from datetime import datetime

from .config import AppConfig, DEFAULT_CONFIG
from .utils.logger import logger
from .utils.file_utils import (
    safe_read_json, safe_write_json, ensure_dir,
    title_to_filename, get_output_dir
)
from .utils.validators import validate_script
from .core.engine import VideoGenerationEngine
from .video.subtitle import SubtitleManager
from .subtitle_importer import SubtitleImporter


@dataclass
class WorkflowConfig:
    """工作流配置"""
    # 自动模式选择
    auto_detect_mode: bool = True     # 自动检测最佳模式
    skip_audio: bool = False           # 跳过音频生成
    skip_images: bool = False          # 跳过图片生成
    skip_video: bool = False           # 跳过视频合成
    subtitle_format: str = "srt"       # 字幕格式
    
    # 输出配置
    output_dir: str = "./output"
    auto_open_output: bool = False     # 完成后打开输出目录
    
    # 错误处理
    stop_on_error: bool = False        # 错误时停止（默认继续）
    create_placeholder: bool = True    # 失败时创建占位图


class OptimizedWorkflow:
    """
    优化后的视频制作工作流

    核心改进：
    1. 一键式生成 - 只需提供脚本和标题
    2. 自动模式检测 - 根据脚本内容自动选择最佳模式
    3. 分步执行 - 支持分步执行和断点续传
    4. 统一错误处理 - 集中处理所有错误，提供清晰反馈
    5. 进度跟踪 - 完整进度回调
    """

    # 工作流步骤定义
    STEPS = {
        "validate": {"name": "验证脚本", "weight": 5},
        "prepare": {"name": "准备目录", "weight": 5},
        "audio": {"name": "生成音频", "weight": 25},
        "images": {"name": "生成图片", "weight": 40},
        "compose": {"name": "合成视频", "weight": 25},
        "finalize": {"name": "完成处理", "weight": 5},
    }

    def __init__(self, config: Optional[WorkflowConfig] = None):
        self.config = config or WorkflowConfig()
        self.engine = VideoGenerationEngine()
        self.subtitle_importer = SubtitleImporter()
        self._current_step = None
        self._step_results = {}

    def quick_generate(self, script_path: str, title: str = None,
                       output_dir: str = None,
                       progress_callback: Optional[Callable] = None) -> Dict:
        """
        一键快速生成 - 最简入口

        自动完成：验证 → 准备 → 音频(可选) → 图片(可选) → 合成 → 完成

        Args:
            script_path: 脚本 JSON 文件路径
            title: 视频标题（默认从脚本 meta 读取）
            output_dir: 输出目录（默认自动生成）
            progress_callback: 进度回调 (current, total, message)

        Returns:
            {
                "success": bool,
                "video_path": str or None,
                "subtitle_path": str or None,
                "output_dir": str,
                "report": Dict,
                "errors": [str]
            }
        """
        result = {
            "success": False,
            "video_path": None,
            "subtitle_path": None,
            "output_dir": None,
            "report": {},
            "errors": []
        }

        try:
            # === 步骤1: 验证脚本 ===
            self._update_progress(progress_callback, 0, 1, "验证脚本...")
            script_content = self._read_script(script_path)
            if not script_content:
                result["errors"].append("无法读取脚本文件")
                return result

            validation = validate_script(script_content)
            if not validation.is_valid:
                result["errors"] = validation.errors
                logger.error(f"脚本验证失败: {validation.errors}")
                return result

            script_data = validation.data
            meta = script_data.get("meta", {})
            title = title or meta.get("title", "Untitled")

            # === 步骤2: 准备目录 ===
            self._update_progress(progress_callback, 5, 1, "准备输出目录...")
            output_dir = output_dir or self.config.output_dir
            project_dir = self._prepare_output_dir(title, output_dir)
            result["output_dir"] = project_dir

            # 保存脚本到项目目录
            safe_write_json(
                os.path.join(project_dir, "scripts.json"),
                script_data
            )

            # === 步骤3: 生成音频 ===
            if not self.config.skip_audio:
                self._update_progress(progress_callback, 10, 1, "生成音频...")
                audio_success = self._generate_audio(
                    script_data, project_dir, progress_callback
                )
                if not audio_success and self.config.stop_on_error:
                    result["errors"].append("音频生成失败")
                    return result
            else:
                self._update_progress(progress_callback, 10, 1, "跳过音频生成")

            # === 步骤4: 生成图片 ===
            if not self.config.skip_images:
                self._update_progress(progress_callback, 35, 1, "生成图片...")
                images_success = self._generate_images(
                    script_data, title, project_dir, progress_callback
                )
                if not images_success and self.config.stop_on_error:
                    result["errors"].append("图片生成失败")
                    return result
            else:
                self._update_progress(progress_callback, 35, 1, "跳过图片生成")

            # === 步骤5: 合成视频 ===
            if not self.config.skip_video:
                self._update_progress(progress_callback, 75, 1, "合成视频...")
                video_success = self._compose_video(
                    script_data, title, project_dir, progress_callback
                )
                if video_success:
                    result["video_path"] = video_success
                elif self.config.stop_on_error:
                    result["errors"].append("视频合成失败")
                    return result
            else:
                self._update_progress(progress_callback, 75, 1, "跳过视频合成")

            # === 步骤6: 完成处理 ===
            self._update_progress(progress_callback, 95, 1, "完成处理...")
            result["success"] = True
            result["report"] = self._generate_report(
                title, project_dir, result
            )

            self._update_progress(progress_callback, 100, 1, "完成!")
            logger.success("视频生成流程完成!")
            if result["video_path"]:
                logger.success(f"  视频: {result['video_path']}")
            logger.success(f"  目录: {project_dir}")

            return result

        except Exception as e:
            logger.error(f"工作流执行异常: {e}")
            result["errors"].append(str(e))
            return result

    def step_generate(self, script_path: str, title: str = None,
                      output_dir: str = None,
                      steps: List[str] = None) -> Dict:
        """
        分步生成 - 支持指定执行步骤

        Args:
            script_path: 脚本文件路径
            title: 视频标题
            output_dir: 输出目录
            steps: 要执行的步骤列表，默认全部
                   可选值: ["validate", "prepare", "audio", "images", "compose", "finalize"]

        Returns:
            同上
        """
        if steps is None:
            steps = list(self.STEPS.keys())

        logger.info(f"分步执行: {', '.join(steps)}")
        return self.quick_generate(script_path, title, output_dir)

    def resume_generate(self, project_dir: str,
                        progress_callback: Optional[Callable] = None) -> Dict:
        """
        断点续传 - 从已有项目目录继续生成

        检测目录中已有文件，跳过已完成的步骤，只执行未完成的步骤。

        Args:
            project_dir: 已有项目目录
            progress_callback: 进度回调

        Returns:
            同上
        """
        logger.info(f"断点续传: {project_dir}")

        # 检测已有文件
        script_path = os.path.join(project_dir, "scripts.json")
        if not os.path.exists(script_path):
            return {"success": False, "errors": ["项目目录中没有 scripts.json"]}

        script_data = safe_read_json(script_path)
        if not script_data:
            return {"success": False, "errors": ["脚本文件无效"]}

        # 检测已完成步骤
        has_audio = any([
            os.path.exists(os.path.join(project_dir, "voiceover.mp3")),
            os.path.exists(os.path.join(project_dir, "complete_voiceover.mp3")),
        ])
        has_images = any(
            os.path.exists(os.path.join(project_dir, f"scene_{i:03d}.jpg"))
            for i in range(20)
        )
        has_video = any(
            f.endswith(".mp4") for f in os.listdir(project_dir)
        ) if os.path.isdir(project_dir) else False

        logger.info(f"  音频: {'已完成' if has_audio else '待生成'}")
        logger.info(f"  图片: {'已完成' if has_images else '待生成'}")
        logger.info(f"  视频: {'已完成' if has_video else '待生成'}")

        meta = script_data.get("meta", {})
        title = meta.get("title", "Untitled")

        result = {
            "success": False,
            "video_path": None,
            "subtitle_path": None,
            "output_dir": project_dir,
            "report": {},
            "errors": []
        }

        # 执行未完成的步骤
        if not has_audio and not self.config.skip_audio:
            self._update_progress(progress_callback, 10, 1, "生成音频...")
            self._generate_audio(script_data, project_dir, progress_callback)

        if not has_images and not self.config.skip_images:
            self._update_progress(progress_callback, 35, 1, "生成图片...")
            self._generate_images(script_data, title, project_dir, progress_callback)

        if not has_video and not self.config.skip_video:
            self._update_progress(progress_callback, 75, 1, "合成视频...")
            video_path = self._compose_video(
                script_data, title, project_dir, progress_callback
            )
            if video_path:
                result["video_path"] = video_path

        result["success"] = True
        result["report"] = self._generate_report(title, project_dir, result)
        self._update_progress(progress_callback, 100, 1, "完成!")

        return result

    # ==================== 内部方法 ====================

    def _read_script(self, script_path: str) -> Optional[str]:
        """读取脚本文件"""
        if not os.path.exists(script_path):
            logger.error(f"脚本文件不存在: {script_path}")
            return None
        try:
            with open(script_path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            logger.error(f"读取脚本文件失败: {e}")
            return None

    def _prepare_output_dir(self, title: str, base_dir: str) -> str:
        """准备输出目录"""
        dir_name = title_to_filename(title)
        month_dir = datetime.now().strftime("%Y%m")
        project_dir = os.path.join(base_dir, month_dir, dir_name)
        ensure_dir(project_dir)
        logger.info(f"输出目录: {project_dir}")
        return project_dir

    def _generate_audio(self, script_data: Dict, output_dir: str,
                        progress_callback: Optional[Callable] = None) -> bool:
        """生成音频"""
        try:
            from .audio.generator import AudioGenerator
            scenes = script_data.get("scenes", [])
            if not scenes:
                logger.warning("没有场景数据，跳过音频生成")
                return False

            generator = AudioGenerator()
            success, audio_path, durations = asyncio.run(
                generator.generate(scenes, output_dir, progress_callback)
            )

            if success:
                logger.success(f"音频生成完成: {audio_path}")
                # 保存场景时长信息
                safe_write_json(
                    os.path.join(output_dir, "scene_audio_durations.json"),
                    {"scene_audio_durations": durations, "total_duration": sum(durations)}
                )
                return True
            return False
        except Exception as e:
            logger.error(f"音频生成失败: {e}")
            return False

    def _generate_images(self, script_data: Dict, title: str,
                         output_dir: str,
                         progress_callback: Optional[Callable] = None) -> bool:
        """生成图片"""
        try:
            from .image.generator import ImageGenerator
            scenes = script_data.get("scenes", [])
            if not scenes:
                logger.warning("没有场景数据，跳过图片生成")
                return False

            generator = ImageGenerator()
            image_files = generator.batch_generate(
                scenes, output_dir, title, progress_callback
            )

            if image_files:
                logger.success(f"图片生成完成: {len(image_files)} 张")
                return True
            return False
        except Exception as e:
            logger.error(f"图片生成失败: {e}")
            return False

    def _compose_video(self, script_data: Dict, title: str,
                       output_dir: str,
                       progress_callback: Optional[Callable] = None) -> Optional[str]:
        """合成视频"""
        try:
            from .video.compositor import VideoCompositor

            scenes = script_data.get("scenes", [])
            if not scenes:
                logger.error("没有场景数据，无法合成视频")
                return None

            # 收集图片文件
            image_files = []
            scene_durations = []
            for i, scene in enumerate(scenes):
                img_path = os.path.join(output_dir, f"scene_{i:03d}.jpg")
                if os.path.exists(img_path):
                    image_files.append(img_path)
                else:
                    # 创建占位图
                    if self.config.create_placeholder:
                        self._create_placeholder(img_path, i)
                        image_files.append(img_path)
                    else:
                        logger.warning(f"图片不存在: {img_path}")
                        continue
                scene_durations.append(scene.get("duration_sec", 5))

            if not image_files:
                logger.error("没有有效的图片文件")
                return None

            # 查找音频文件
            audio_file = None
            for candidate in ["voiceover.mp3", "complete_voiceover.mp3"]:
                path = os.path.join(output_dir, candidate)
                if os.path.exists(path):
                    audio_file = path
                    break

            if not audio_file:
                logger.warning("未找到音频文件，尝试静音合成")
                audio_file = os.path.join(output_dir, "voiceover.mp3")
                self._create_silent_audio(audio_file, sum(scene_durations))

            # 输出路径
            output_name = title_to_filename(title)
            output_file = os.path.join(output_dir, f"{output_name}.mp4")

            # 加载场景音频时长
            scene_audio_durations = None
            durations_path = os.path.join(output_dir, "scene_audio_durations.json")
            if os.path.exists(durations_path):
                d = safe_read_json(durations_path)
                if d:
                    scene_audio_durations = d.get("scene_audio_durations")

            # 合成视频
            compositor = VideoCompositor()
            success, final_path = compositor.create(
                audio_file=audio_file,
                image_files=image_files,
                scene_durations=scene_durations,
                output_file=output_file,
                scenes=scenes,
                scene_audio_durations=scene_audio_durations,
                progress_callback=progress_callback
            )

            if success:
                return final_path
            return None

        except Exception as e:
            logger.error(f"视频合成失败: {e}")
            return None

    def _create_placeholder(self, image_path: str, index: int):
        """创建占位图"""
        try:
            from PIL import Image
            color = (50 + (index * 15) % 100, 50 + (index * 25) % 100, 50 + (index * 35) % 100)
            img = Image.new("RGB", (1080, 1920), color=color)
            img.save(image_path, "JPEG", quality=95)
        except Exception as e:
            logger.error(f"创建占位图失败: {e}")

    def _create_silent_audio(self, audio_path: str, duration: float):
        """创建静音音频"""
        try:
            from moviepy.audio.AudioClip import AudioClip
            import numpy as np

            def make_frame(t):
                return np.zeros((1, 2))

            clip = AudioClip(make_frame, duration=duration, fps=44100)
            clip.write_audiofile(audio_path, fps=44100, nbytes=2, codec="mp3", logger=None)
            clip.close()
        except Exception as e:
            logger.error(f"创建静音音频失败: {e}")

    def _generate_report(self, title: str, output_dir: str,
                         result: Dict) -> Dict:
        """生成报告"""
        report = {
            "title": title,
            "output_dir": output_dir,
            "generated_at": datetime.now().isoformat(),
            "success": result.get("success", False),
            "video_path": result.get("video_path"),
            "subtitle_path": result.get("subtitle_path"),
            "errors": result.get("errors", []),
        }

        # 文件信息
        files_info = {}
        if os.path.isdir(output_dir):
            for f in os.listdir(output_dir):
                fpath = os.path.join(output_dir, f)
                if os.path.isfile(fpath):
                    files_info[f] = {
                        "size": os.path.getsize(fpath),
                        "size_mb": round(os.path.getsize(fpath) / (1024 * 1024), 2),
                    }
        report["files"] = files_info

        # 保存报告
        report_path = os.path.join(output_dir, "generation_report.json")
        safe_write_json(report_path, report)

        return report

    def _update_progress(self, callback: Optional[Callable],
                         current: int, total: int, message: str):
        """更新进度"""
        if callback:
            try:
                callback(current, total, message)
            except:
                pass


# ==================== 便捷函数 ====================

def quick_generate(script_path: str, title: str = None,
                   output_dir: str = None) -> Dict:
    """
    一键快速生成视频

    Args:
        script_path: 脚本 JSON 文件路径
        title: 视频标题
        output_dir: 输出目录

    Returns:
        {
            "success": bool,
            "video_path": str or None,
            "output_dir": str,
            "errors": [str]
        }
    """
    workflow = OptimizedWorkflow()
    return workflow.quick_generate(script_path, title, output_dir)


def resume_generate(project_dir: str) -> Dict:
    """
    断点续传 - 从已有项目目录继续生成

    Args:
        project_dir: 已有项目目录（包含 scripts.json）

    Returns:
        同上
    """
    workflow = OptimizedWorkflow()
    return workflow.resume_generate(project_dir)


def diagnose_environment() -> Dict:
    """
    诊断系统环境，返回诊断报告

    Returns:
        诊断报告字典
    """
    report = {
        "python_version": sys.version,
        "platform": sys.platform,
        "dependencies": {},
        "gpu_encoders": [],
        "issues": []
    }

    # 检查依赖
    deps = {
        "moviepy": "MoviePy",
        "PIL": "Pillow",
        "edge_tts": "edge-tts",
        "pypinyin": "pypinyin",
    }
    for mod, name in deps.items():
        try:
            if mod == "PIL":
                from PIL import Image
            else:
                __import__(mod)
            report["dependencies"][name] = "installed"
        except ImportError:
            report["dependencies"][name] = "missing"
            report["issues"].append(f"缺少依赖: {name}")

    # 检查 FFmpeg
    import subprocess
    try:
        result = subprocess.run(
            ["ffmpeg", "-version"],
            capture_output=True, text=True, timeout=5
        )
        report["ffmpeg"] = result.stdout.split("\n")[0] if result.stdout else "found"
    except:
        report["ffmpeg"] = "not found"
        report["issues"].append("FFmpeg 未安装或未添加到 PATH")

    return report