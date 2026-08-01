#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Video Workshop CLI - 命令行入口
提供视频生成、字幕导入、系统诊断等功能的命令行接口

用法:
    python -m video_gen.cli generate --title "标题" --script scripts.json
    python -m video_gen.cli subtitles --video output.mp4 --script scripts.json
    python -m video_gen.cli diagnose
"""

import os
import sys
import json
import asyncio
import argparse
from datetime import datetime
from typing import Dict, Optional, List

# 确保 video_gen 模块可导入
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from .config import DEFAULT_CONFIG, AppConfig
from .utils.logger import logger
from .utils.file_utils import safe_read_text, safe_read_json, safe_write_json
from .core.engine import VideoGenerationEngine
from .video.subtitle import SubtitleGenerator, SubtitleEmbedder, SubtitleManager
from .video.compositor import VideoCompositor


def setup_argparse() -> argparse.ArgumentParser:
    """配置命令行参数解析器"""
    parser = argparse.ArgumentParser(
        description="Video Workshop - 视频生成与字幕处理工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 从脚本生成视频
  python -m video_gen.cli generate -t "我的视频" -s scripts.json
  
  # 仅生成音频
  python -m video_gen.cli audio -s scripts.json -o ./output
  
  # 仅生成图片
  python -m video_gen.cli images -s scripts.json -o ./output
  
  # 仅合成视频（含字幕）
  python -m video_gen.cli compose -s scripts.json -a voiceover.mp3 -i ./images -o ./output
  
  # 为已有视频自动导入字幕
  python -m video_gen.cli subtitles -v video.mp4 -s scripts.json -o video_subtitled.mp4
  
  # 诊断系统环境
  python -m video_gen.cli diagnose
        """
    )

    subparsers = parser.add_subparsers(dest="command", help="子命令")

    # generate 子命令
    gen_parser = subparsers.add_parser("generate", help="完整视频生成")
    gen_parser.add_argument("-t", "--title", required=True, help="视频标题")
    gen_parser.add_argument("-s", "--script", required=True, help="脚本 JSON 文件路径")
    gen_parser.add_argument("-o", "--output", default=None, help="输出目录 (默认: ./output)")
    gen_parser.add_argument("--no-audio", action="store_true", help="跳过音频生成")
    gen_parser.add_argument("--no-images", action="store_true", help="跳过图片生成")

    # audio 子命令
    audio_parser = subparsers.add_parser("audio", help="仅生成音频")
    audio_parser.add_argument("-s", "--script", required=True, help="脚本 JSON 文件路径")
    audio_parser.add_argument("-o", "--output", default="./output", help="输出目录")

    # images 子命令
    images_parser = subparsers.add_parser("images", help="仅生成图片")
    images_parser.add_argument("-s", "--script", required=True, help="脚本 JSON 文件路径")
    images_parser.add_argument("-o", "--output", default="./output", help="输出目录")

    # compose 子命令
    compose_parser = subparsers.add_parser("compose", help="合成视频（含字幕）")
    compose_parser.add_argument("-s", "--script", required=True, help="脚本 JSON 文件路径")
    compose_parser.add_argument("-a", "--audio", required=True, help="音频文件路径")
    compose_parser.add_argument("-i", "--images", required=True, help="图片目录路径")
    compose_parser.add_argument("-o", "--output", default="./output", help="输出目录")
    compose_parser.add_argument("--title", default=None, help="视频标题")

    # subtitles 子命令 - 核心修复：字幕自动导入
    sub_parser = subparsers.add_parser("subtitles", help="为已有视频自动导入字幕")
    sub_parser.add_argument("-v", "--video", required=True, help="输入视频文件路径")
    sub_parser.add_argument("-s", "--script", required=True, help="脚本 JSON 文件路径")
    sub_parser.add_argument("-o", "--output", default=None, help="输出视频路径 (默认: 自动生成)")
    sub_parser.add_argument("--format", default="srt", choices=["srt", "ass", "embedded"],
                           help="字幕格式 (默认: srt)")
    sub_parser.add_argument("--font-size", type=int, default=36, help="字幕字体大小")
    sub_parser.add_argument("--dry-run", action="store_true", help="仅生成字幕文件，不嵌入视频")

    # diagnose 子命令
    subparsers.add_parser("diagnose", help="诊断系统环境")

    return parser


async def cmd_generate(args: argparse.Namespace) -> int:
    """执行 generate 命令"""
    # 读取脚本
    script_content = safe_read_text(args.script)
    if not script_content:
        logger.error(f"无法读取脚本文件: {args.script}")
        return 1

    # 创建引擎
    engine = VideoGenerationEngine()

    # 执行生成
    logger.info(f"开始视频生成: {args.title}")
    result = await engine.generate_from_script(
        args.title, script_content, args.output
    )

    if result.get("success"):
        logger.success(f"视频生成完成: {result.get('video_file', 'N/A')}")
        if result.get("subtitle_file"):
            logger.success(f"字幕文件: {result['subtitle_file']}")
        return 0
    else:
        logger.error(f"视频生成失败: {result.get('errors', ['未知错误'])}")
        return 1


async def cmd_audio(args: argparse.Namespace) -> int:
    """执行 audio 命令"""
    from .audio.generator import AudioGenerator

    script_data = safe_read_json(args.script)
    if not script_data:
        logger.error(f"无法读取脚本文件: {args.script}")
        return 1

    scenes = script_data.get("scenes", [])
    if not scenes:
        logger.error("脚本中没有场景数据")
        return 1

    generator = AudioGenerator()
    success, audio_path, durations = await generator.generate(
        scenes, args.output
    )

    if success:
        logger.success(f"音频生成完成: {audio_path}")
        # 保存场景音频时长信息
        durations_path = os.path.join(args.output, "scene_audio_durations.json")
        safe_write_json(durations_path, {
            "scene_audio_durations": durations,
            "total_duration": sum(durations)
        })
        logger.info(f"场景音频时长已保存: {durations_path}")
        return 0
    else:
        logger.error("音频生成失败")
        return 1


def cmd_images(args: argparse.Namespace) -> int:
    """执行 images 命令"""
    from .image.generator import ImageGenerator

    script_data = safe_read_json(args.script)
    if not script_data:
        logger.error(f"无法读取脚本文件: {args.script}")
        return 1

    scenes = script_data.get("scenes", [])
    if not scenes:
        logger.error("脚本中没有场景数据")
        return 1

    meta = script_data.get("meta", {})
    title = meta.get("title", "Untitled")

    generator = ImageGenerator()
    image_files = generator.batch_generate(scenes, args.output, title)

    if image_files:
        logger.success(f"图片生成完成: {len(image_files)} 张")
        return 0
    else:
        logger.error("图片生成失败")
        return 1


def cmd_compose(args: argparse.Namespace) -> int:
    """执行 compose 命令"""
    script_data = safe_read_json(args.script)
    if not script_data:
        logger.error(f"无法读取脚本文件: {args.script}")
        return 1

    scenes = script_data.get("scenes", [])
    if not scenes:
        logger.error("脚本中没有场景数据")
        return 1

    meta = script_data.get("meta", {})
    title = args.title or meta.get("title", "Untitled")

    # 收集图片文件
    image_files = []
    if os.path.isdir(args.images):
        for f in sorted(os.listdir(args.images)):
            if f.lower().endswith((".jpg", ".jpeg", ".png", ".webp")):
                image_files.append(os.path.join(args.images, f))
    else:
        logger.error(f"图片目录无效: {args.images}")
        return 1

    if not image_files:
        logger.error("未找到图片文件")
        return 1

    # 场景时长
    scene_durations = [s.get("duration_sec", 5) for s in scenes]

    # 输出路径
    from .utils.file_utils import title_to_filename, ensure_dir
    output_name = title_to_filename(title)
    output_file = os.path.join(args.output, f"{output_name}.mp4")
    ensure_dir(args.output)

    # 创建合成器
    compositor = VideoCompositor()

    # 执行合成
    logger.info(f"合成视频: {len(image_files)} 张图片, {len(scenes)} 场景")
    success, final_path = compositor.create(
        audio_file=args.audio,
        image_files=image_files,
        scene_durations=scene_durations,
        output_file=output_file,
        scenes=scenes
    )

    if success:
        logger.success(f"视频合成完成: {final_path}")
        return 0
    else:
        logger.error("视频合成失败")
        return 1


def cmd_subtitles(args: argparse.Namespace) -> int:
    """
    字幕自动导入命令 - 核心修复功能

    为已有视频自动生成并嵌入字幕，解决原系统"无字幕功能"的缺陷。
    支持：
    1. 从脚本 JSON 自动提取字幕文本
    2. 根据音频时长自动对齐时间轴
    3. 生成 SRT/ASS 格式字幕文件
    4. 使用 FFmpeg 嵌入字幕到视频
    """
    # 验证输入
    if not os.path.exists(args.video):
        logger.error(f"视频文件不存在: {args.video}")
        return 1

    script_data = safe_read_json(args.script)
    if not script_data:
        logger.error(f"无法读取脚本文件: {args.script}")
        return 1

    scenes = script_data.get("scenes", [])
    if not scenes:
        logger.error("脚本中没有场景数据")
        return 1

    # 确定输出路径
    if args.output:
        output_path = args.output
    else:
        base, ext = os.path.splitext(args.video)
        output_path = f"{base}_subtitled{ext}"

    # 尝试加载音频时长信息
    audio_duration = None
    scene_audio_durations = None
    base_dir = os.path.dirname(args.video)
    durations_file = os.path.join(base_dir, "scene_audio_durations.json")
    if os.path.exists(durations_file):
        durations_data = safe_read_json(durations_file)
        if durations_data:
            scene_audio_durations = durations_data.get("scene_audio_durations")
            audio_duration = durations_data.get("total_duration")
            logger.info(f"已加载精确音频时长: {len(scene_audio_durations)} 场景")

    if not audio_duration:
        # 尝试从视频文件获取时长
        import subprocess
        try:
            result = subprocess.run(
                ["ffprobe", "-v", "error", "-show_entries",
                 "format=duration", "-of", "default=noprint_wrappers=1:nokey=1",
                 args.video],
                capture_output=True, text=True, timeout=10
            )
            if result.stdout.strip():
                audio_duration = float(result.stdout.strip())
                logger.info(f"从视频文件检测到时长: {audio_duration:.2f}秒")
        except:
            pass

    if not audio_duration:
        # 使用预设时长
        audio_duration = sum(s.get("duration_sec", 5) for s in scenes)
        logger.warning(f"使用预设时长: {audio_duration:.2f}秒")

    # 配置字幕
    from .config import SubtitleConfig
    sub_config = SubtitleConfig(
        output_format=args.format,
        font_size=args.font_size
    )

    # 创建字幕管理器
    manager = SubtitleManager(sub_config)

    # 执行字幕处理
    logger.info(f"开始字幕自动导入流程")
    logger.info(f"  输入视频: {args.video}")
    logger.info(f"  输出视频: {output_path}")
    logger.info(f"  字幕格式: {args.format}")
    logger.info(f"  场景数量: {len(scenes)}")

    if args.dry_run:
        # 仅生成字幕文件，不嵌入
        logger.info("Dry-run 模式: 仅生成字幕文件")

        # 检测字体
        manager.generator.detect_font()

        # 生成字幕条目
        entries = manager.generator.generate_from_scenes(
            scenes, audio_duration, scene_audio_durations
        )

        if not entries:
            logger.error("未生成字幕条目")
            return 1

        logger.info(f"生成 {len(entries)} 条字幕")

        # 生成字幕文件
        base_dir = os.path.dirname(output_path)
        base_name = os.path.splitext(os.path.basename(output_path))[0]

        if args.format == "ass":
            sub_path = os.path.join(base_dir, f"{base_name}.ass")
            success = manager.generator.generate_ass(entries, sub_path)
        else:
            sub_path = os.path.join(base_dir, f"{base_name}.srt")
            success = manager.generator.generate_srt(entries, sub_path)

        if success:
            logger.success(f"字幕文件已生成: {sub_path}")
            # 保存字幕元数据
            meta_path = os.path.join(base_dir, f"{base_name}_subtitle_meta.json")
            meta_data = {
                "video": args.video,
                "subtitle": sub_path,
                "entries": len(entries),
                "format": args.format,
                "audio_duration": audio_duration,
                "scene_count": len(scenes)
            }
            safe_write_json(meta_path, meta_data)
            logger.info(f"字幕元数据已保存: {meta_path}")
            return 0
        else:
            logger.error("字幕文件生成失败")
            return 1
    else:
        # 完整流程：生成字幕并嵌入视频
        success = manager.process(
            scenes=scenes,
            video_path=args.video,
            output_path=output_path,
            audio_duration=audio_duration,
            scene_audio_durations=scene_audio_durations
        )

        if success:
            logger.success(f"字幕自动导入完成!")
            logger.success(f"  输出视频: {output_path}")

            # 验证输出
            if os.path.exists(output_path):
                size_mb = os.path.getsize(output_path) / (1024 * 1024)
                logger.info(f"  文件大小: {size_mb:.1f} MB")
            return 0
        else:
            logger.error("字幕自动导入失败")
            return 1


def cmd_diagnose(args: argparse.Namespace) -> int:
    """执行 diagnose 命令 - 诊断系统环境"""
    logger.info("=" * 50)
    logger.info("Video Workshop - 系统环境诊断")
    logger.info("=" * 50)

    # Python 版本
    logger.info(f"Python 版本: {sys.version}")

    # 检查关键依赖
    deps = {
        "moviepy": "视频编辑",
        "PIL": "图片处理",
        "pydub": "音频处理",
        "edge_tts": "TTS 语音合成",
        "requests": "HTTP 请求",
        "pypinyin": "中文拼音转换",
    }

    logger.info("\n依赖检查:")
    for module, desc in deps.items():
        try:
            if module == "PIL":
                from PIL import Image
            else:
                __import__(module)
            logger.success(f"  {module}: 已安装 ({desc})")
        except ImportError:
            logger.error(f"  {module}: 未安装 ({desc})")

    # FFmpeg 检查
    logger.info("\nFFmpeg 检查:")
    import subprocess
    try:
        result = subprocess.run(
            ["ffmpeg", "-version"],
            capture_output=True, text=True, timeout=5
        )
        first_line = result.stdout.split("\n")[0] if result.stdout else "N/A"
        logger.success(f"  FFmpeg: {first_line}")

        # 检查 GPU 编码器
        encoders = subprocess.run(
            ["ffmpeg", "-hide_banner", "-encoders"],
            capture_output=True, text=True, timeout=10
        )
        gpu_encoders = ["h264_nvenc", "h264_qsv", "h264_amf", "h264_videotoolbox"]
        for enc in gpu_encoders:
            if enc in encoders.stdout:
                logger.success(f"  GPU 编码器: {enc}")
    except FileNotFoundError:
        logger.error("  FFmpeg: 未安装或未添加到 PATH")
    except Exception as e:
        logger.error(f"  FFmpeg 检查失败: {e}")

    # 字体检查
    logger.info("\n中文字体检查:")
    from .utils.file_utils import find_available_font
    from .config import SubtitleConfig
    fonts = SubtitleConfig().preferred_fonts
    font_path = find_available_font(fonts)
    if font_path:
        logger.success(f"  检测到中文字体: {font_path}")
    else:
        logger.warning("  未检测到中文字体，字幕渲染可能异常")

    # 输出目录检查
    logger.info(f"\n输出目录: {os.path.abspath(DEFAULT_CONFIG.paths.output_dir)}")
    if os.path.exists(DEFAULT_CONFIG.paths.output_dir):
        logger.success("  输出目录可访问")
    else:
        logger.info("  输出目录将自动创建")

    logger.info("=" * 50)
    logger.info("诊断完成")
    logger.info("=" * 50)
    return 0


async def main_async():
    """异步主入口"""
    parser = setup_argparse()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 0

    # 命令分发
    commands = {
        "generate": cmd_generate,
        "audio": cmd_audio,
        "images": cmd_images,
        "compose": cmd_compose,
        "subtitles": cmd_subtitles,
        "diagnose": cmd_diagnose,
    }

    cmd_func = commands.get(args.command)
    if not cmd_func:
        logger.error(f"未知命令: {args.command}")
        return 1

    # 异步命令需要 await
    if args.command in ("generate", "audio"):
        return await cmd_func(args)
    else:
        return cmd_func(args)


def main():
    """同步入口"""
    exit_code = asyncio.run(main_async())
    sys.exit(exit_code)


if __name__ == "__main__":
    main()