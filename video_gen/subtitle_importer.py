#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
字幕自动导入器 - 独立模块

核心功能：为已有视频自动生成并嵌入字幕
解决原系统"无字幕功能"的缺陷，实现可靠的自动导入机制。

使用方式:
    # 作为独立脚本
    python subtitle_importer.py --video output.mp4 --script scripts.json
    
    # 作为模块导入
    from subtitle_importer import SubtitleImporter
    importer = SubtitleImporter()
    success = importer.auto_import(video_path="output.mp4", script_path="scripts.json")

自动导入机制:
    1. 自动检测：扫描目录，自动发现视频文件和脚本文件
    2. 自动提取：从脚本 JSON 提取场景文本
    3. 自动对齐：从视频文件提取时长信息，精确对齐字幕时间轴
    4. 自动生成：生成 SRT 或 ASS 格式字幕文件
    5. 自动嵌入：使用 FFmpeg 将字幕嵌入视频
    6. 自动验证：验证输出视频的完整性和字幕正确性
"""

import os
import sys
import json
import re
import subprocess
from typing import Dict, List, Optional, Tuple, Callable
from datetime import timedelta
from pathlib import Path

# 确保 video_gen 模块可导入
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from .config import SubtitleConfig, DEFAULT_CONFIG
from .utils.logger import logger
from .utils.file_utils import safe_read_json, safe_write_json, safe_read_text
from .video.subtitle import SubtitleGenerator, SubtitleEmbedder, SubtitleManager


class SubtitleImporter:
    """
    字幕自动导入器

    提供自动化的字幕导入流程，支持多种检测和导入策略。
    与 SubtitleManager 不同的是，本类专注于"为已有视频导入字幕"的场景，
    提供自动检测、批量导入、进度跟踪等功能。
    """

    def __init__(self, config: Optional[SubtitleConfig] = None):
        self.config = config or DEFAULT_CONFIG.subtitle
        self.generator = SubtitleGenerator(self.config)
        self.embedder = SubtitleEmbedder(self.config)
        self.manager = SubtitleManager(self.config)

    # ==================== 自动检测 ====================

    def auto_detect_video(self, directory: str) -> Optional[str]:
        """自动检测目录中的视频文件"""
        video_exts = {".mp4", ".avi", ".mov", ".mkv", ".webm", ".flv"}
        for f in sorted(os.listdir(directory)):
            ext = os.path.splitext(f)[1].lower()
            if ext in video_exts:
                video_path = os.path.join(directory, f)
                logger.info(f"自动检测到视频文件: {video_path}")
                return video_path
        return None

    def auto_detect_script(self, directory: str) -> Optional[str]:
        """自动检测目录中的脚本文件"""
        script_names = ["scripts.json", "script.json", "day29_script.json"]
        for name in script_names:
            path = os.path.join(directory, name)
            if os.path.exists(path):
                logger.info(f"自动检测到脚本文件: {path}")
                return path
        # 扫描所有 JSON 文件
        for f in sorted(os.listdir(directory)):
            if f.endswith(".json"):
                path = os.path.join(directory, f)
                try:
                    data = safe_read_json(path)
                    if data and "scenes" in data:
                        logger.info(f"自动检测到脚本文件: {path}")
                        return path
                except:
                    pass
        return None

    def auto_detect_audio_duration(self, video_path: str) -> Optional[float]:
        """从视频文件自动检测音频时长"""
        for probe_name in ["ffprobe", "ffprobe.exe"]:
            try:
                result = subprocess.run(
                    [probe_name, "-v", "error", "-show_entries",
                     "format=duration", "-of",
                     "default=noprint_wrappers=1:nokey=1",
                     video_path],
                    capture_output=True, text=True, timeout=10
                )
                if result.stdout.strip():
                    return float(result.stdout.strip())
            except (FileNotFoundError, subprocess.TimeoutExpired):
                continue
        return None

    def auto_detect_audio_durations_file(self, directory: str) -> Optional[Dict]:
        """自动检测场景音频时长文件"""
        path = os.path.join(directory, "scene_audio_durations.json")
        if os.path.exists(path):
            return safe_read_json(path)
        return None

    # ==================== 核心导入流程 ====================

    def auto_import(self, video_path: str = None, script_path: str = None,
                    output_path: str = None, directory: str = None,
                    format: str = "srt", dry_run: bool = False,
                    progress_callback: Optional[Callable] = None) -> bool:
        """
        自动字幕导入 - 一键式入口

        支持三种模式：
        1. 指定视频和脚本文件
        2. 仅指定目录，自动检测视频和脚本
        3. 指定视频，自动在视频所在目录检测脚本

        Args:
            video_path: 视频文件路径
            script_path: 脚本文件路径
            output_path: 输出视频路径（默认自动生成）
            directory: 扫描目录（自动检测模式）
            format: 字幕格式 (srt/ass/embedded)
            dry_run: 仅生成字幕文件，不嵌入
            progress_callback: 进度回调 (current, total, message)

        Returns:
            是否成功
        """
        # === 步骤1: 自动检测输入文件 ===
        if progress_callback:
            progress_callback(0, 100, "检测输入文件")

        if not video_path and not directory:
            logger.error("必须指定 video_path 或 directory")
            return False

        if not video_path and directory:
            video_path = self.auto_detect_video(directory)
            if not video_path:
                logger.error(f"目录中未检测到视频文件: {directory}")
                return False

        if not video_path or not os.path.exists(video_path):
            logger.error(f"视频文件不存在: {video_path}")
            return False

        # 如果没有指定脚本，在视频目录自动检测
        if not script_path:
            video_dir = os.path.dirname(video_path)
            script_path = self.auto_detect_script(video_dir)
            if not script_path:
                logger.error(f"视频目录中未检测到脚本文件: {video_dir}")
                return False

        script_data = safe_read_json(script_path)
        if not script_data:
            logger.error(f"脚本文件无效: {script_path}")
            return False

        scenes = script_data.get("scenes", [])
        if not scenes:
            logger.error("脚本中没有场景数据")
            return False

        # === 步骤2: 自动检测时长信息 ===
        if progress_callback:
            progress_callback(15, 100, "检测音频时长")

        audio_duration = None
        scene_audio_durations = None

        # 首选：从场景音频时长文件加载
        video_dir = os.path.dirname(video_path)
        durations_data = self.auto_detect_audio_durations_file(video_dir)
        if durations_data:
            scene_audio_durations = durations_data.get("scene_audio_durations")
            audio_duration = durations_data.get("total_duration")
            logger.info(f"加载精确音频时长: {len(scene_audio_durations)} 场景")

        # 次选：从视频文件检测
        if not audio_duration:
            audio_duration = self.auto_detect_audio_duration(video_path)
            if audio_duration:
                logger.info(f"从视频检测到时长: {audio_duration:.2f}秒")

        # 兜底：使用预设时长
        if not audio_duration:
            audio_duration = sum(s.get("duration_sec", 5) for s in scenes)
            logger.warning(f"使用预设时长: {audio_duration:.2f}秒")

        # === 步骤3: 确定输出路径 ===
        if progress_callback:
            progress_callback(30, 100, "准备输出")

        if not output_path:
            base, ext = os.path.splitext(video_path)
            output_path = f"{base}_subtitled{ext}"

        # === 步骤4: 生成字幕 ===
        if progress_callback:
            progress_callback(40, 100, "生成字幕内容")

        self.generator.detect_font()
        entries = self.generator.generate_from_scenes(
            scenes, audio_duration, scene_audio_durations
        )

        if not entries:
            logger.error("未生成字幕条目")
            return False

        logger.info(f"生成 {len(entries)} 条字幕")

        # === 步骤5: 生成字幕文件 ===
        if progress_callback:
            progress_callback(60, 100, "生成字幕文件")

        base_dir = os.path.dirname(output_path)
        base_name = os.path.splitext(os.path.basename(output_path))[0]

        if format == "ass":
            subtitle_path = os.path.join(base_dir, f"{base_name}.ass")
            success = self.generator.generate_ass(entries, subtitle_path)
        else:
            subtitle_path = os.path.join(base_dir, f"{base_name}.srt")
            success = self.generator.generate_srt(entries, subtitle_path)

        if not success:
            logger.error("生成字幕文件失败")
            return False

        logger.success(f"字幕文件已生成: {subtitle_path}")

        # 保存字幕元数据
        meta_path = os.path.join(base_dir, f"{base_name}_subtitle_meta.json")
        safe_write_json(meta_path, {
            "video_source": video_path,
            "subtitle_file": subtitle_path,
            "script_source": script_path,
            "entries": len(entries),
            "format": format,
            "audio_duration": audio_duration,
            "scene_count": len(scenes),
            "generated_at": str(timedelta(seconds=0))
        })

        if dry_run:
            logger.success("Dry-run 模式完成，字幕文件已生成")
            if progress_callback:
                progress_callback(100, 100, "完成")
            return True

        # === 步骤6: 嵌入字幕 ===
        if progress_callback:
            progress_callback(80, 100, "嵌入字幕到视频")

        embed_success = self.embedder.embed_with_ffmpeg(
            video_path, subtitle_path, output_path, progress_callback
        )

        if embed_success:
            logger.success("字幕自动导入完成!")
            logger.success(f"  输出视频: {output_path}")
            # 验证输出
            if os.path.exists(output_path):
                size_mb = os.path.getsize(output_path) / (1024 * 1024)
                logger.info(f"  文件大小: {size_mb:.1f} MB")
            if progress_callback:
                progress_callback(100, 100, "完成")
            return True
        else:
            logger.error("字幕嵌入失败")
            return False

    # ==================== 批量导入 ====================

    def batch_import(self, directory: str, format: str = "srt",
                     dry_run: bool = False,
                     progress_callback: Optional[Callable] = None) -> Dict[str, bool]:
        """
        批量字幕导入 - 扫描目录下所有视频文件

        Args:
            directory: 扫描目录
            format: 字幕格式
            dry_run: 仅生成字幕文件
            progress_callback: 进度回调

        Returns:
            {视频文件路径: 是否成功} 字典
        """
        results = {}
        video_files = self._find_video_files(directory)

        if not video_files:
            logger.warning(f"目录中未找到视频文件: {directory}")
            return results

        logger.info(f"批量导入: 找到 {len(video_files)} 个视频文件")

        for i, video_path in enumerate(video_files):
            logger.info(f"[{i + 1}/{len(video_files)}] 处理: {os.path.basename(video_path)}")

            if progress_callback:
                progress_callback(i, len(video_files), f"处理: {os.path.basename(video_path)}")

            video_dir = os.path.dirname(video_path)
            script_path = self.auto_detect_script(video_dir)

            if not script_path:
                logger.warning(f"  跳过: 未找到脚本文件")
                results[video_path] = False
                continue

            success = self.auto_import(
                video_path=video_path,
                script_path=script_path,
                format=format,
                dry_run=dry_run
            )
            results[video_path] = success

        # 统计结果
        success_count = sum(1 for v in results.values() if v)
        logger.info(f"批量导入完成: {success_count}/{len(results)} 成功")
        return results

    def _find_video_files(self, directory: str) -> List[str]:
        """查找目录下所有视频文件"""
        video_exts = {".mp4", ".avi", ".mov", ".mkv", ".webm", ".flv"}
        video_files = []
        for f in sorted(os.listdir(directory)):
            ext = os.path.splitext(f)[1].lower()
            if ext in video_exts:
                video_files.append(os.path.join(directory, f))
        return video_files

    # ==================== 验证 ====================

    def verify_import(self, video_path: str, subtitle_path: str = None) -> Dict:
        """
        验证字幕导入结果

        Args:
            video_path: 视频文件路径
            subtitle_path: 字幕文件路径（可选）

        Returns:
            验证报告
        """
        report = {
            "video_path": video_path,
            "video_exists": os.path.exists(video_path),
            "video_size_mb": 0,
            "subtitle_path": subtitle_path,
            "subtitle_exists": False if subtitle_path else None,
            "subtitle_entries": 0,
            "verification_passed": False,
            "issues": []
        }

        if os.path.exists(video_path):
            report["video_size_mb"] = round(
                os.path.getsize(video_path) / (1024 * 1024), 2
            )

        if subtitle_path and os.path.exists(subtitle_path):
            report["subtitle_exists"] = True
            # 计算字幕条目数
            try:
                with open(subtitle_path, "r", encoding="utf-8") as f:
                    content = f.read()
                if subtitle_path.endswith(".srt"):
                    entries = re.findall(r"\d+\n\d{2}:\d{2}:\d{2}", content)
                    report["subtitle_entries"] = len(entries)
                elif subtitle_path.endswith(".ass"):
                    entries = re.findall(r"^Dialogue:", content, re.MULTILINE)
                    report["subtitle_entries"] = len(entries)
            except:
                pass

        report["verification_passed"] = (
            report["video_exists"] and
            (report["subtitle_exists"] is None or report["subtitle_exists"])
        )

        if not report["video_exists"]:
            report["issues"].append("视频文件不存在")
        if subtitle_path and not report["subtitle_exists"]:
            report["issues"].append("字幕文件不存在")

        return report


# ==================== 独立运行入口 ====================

def main():
    """独立运行入口"""
    import argparse

    parser = argparse.ArgumentParser(
        description="字幕自动导入器 - 为已有视频自动生成并嵌入字幕",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 指定视频和脚本
  python subtitle_importer.py -v output.mp4 -s scripts.json
  
  # 自动检测目录中的视频和脚本
  python subtitle_importer.py -d ./output
  
  # 批量导入目录下所有视频
  python subtitle_importer.py -d ./output --batch
  
  # 仅生成字幕文件，不嵌入
  python subtitle_importer.py -v output.mp4 -s scripts.json --dry-run
  
  # 指定字幕格式
  python subtitle_importer.py -v output.mp4 -s scripts.json --format ass
        """
    )

    parser.add_argument("-v", "--video", help="输入视频文件路径")
    parser.add_argument("-s", "--script", help="脚本 JSON 文件路径")
    parser.add_argument("-o", "--output", help="输出视频路径 (默认: 自动生成)")
    parser.add_argument("-d", "--directory", help="扫描目录（自动检测模式）")
    parser.add_argument("--format", default="srt", choices=["srt", "ass", "embedded"],
                        help="字幕格式 (默认: srt)")
    parser.add_argument("--dry-run", action="store_true",
                        help="仅生成字幕文件，不嵌入视频")
    parser.add_argument("--batch", action="store_true",
                        help="批量导入目录下所有视频")
    parser.add_argument("--verify", action="store_true",
                        help="验证字幕导入结果")

    args = parser.parse_args()

    if not args.video and not args.directory:
        parser.print_help()
        return 1

    importer = SubtitleImporter()

    if args.batch:
        # 批量导入
        directory = args.directory or os.path.dirname(args.video)
        results = importer.batch_import(directory, args.format, args.dry_run)
        success_count = sum(1 for v in results.values() if v)
        logger.info(f"批量导入: {success_count}/{len(results)} 成功")
        return 0 if success_count == len(results) else 1
    elif args.verify and args.video:
        # 验证
        video_dir = os.path.dirname(args.video)
        base_name = os.path.splitext(os.path.basename(args.video))[0]
        subtitle_path = os.path.join(video_dir, f"{base_name}.{args.format}")
        if not os.path.exists(subtitle_path):
            subtitle_path = None
        report = importer.verify_import(args.video, subtitle_path)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0 if report["verification_passed"] else 1
    else:
        # 单文件导入
        success = importer.auto_import(
            video_path=args.video,
            script_path=args.script,
            output_path=args.output,
            directory=args.directory,
            format=args.format,
            dry_run=args.dry_run
        )
        return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())