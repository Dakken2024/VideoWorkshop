#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Video Workshop 部署工具 - 初始化环境、验证依赖、配置参数

部署策略:
    1. 所有优化代码部署在 video_gen/ 目录下，与现有系统完全隔离
    2. 不修改 auto_video_maker.py 等现有生产代码
    3. 提供 CLI 入口供外部调用
    4. 支持一键环境初始化
"""

import os
import sys
import subprocess
import importlib
from typing import List, Dict, Tuple


# ==================== 依赖管理 ====================

REQUIRED_DEPENDENCIES = {
    "moviepy": "视频编辑",
    "PIL": "图片处理 (Pillow)",
    "pydub": "音频处理",
    "edge_tts": "TTS 语音合成",
    "requests": "HTTP 请求",
    "pypinyin": "中文拼音转换",
}

OPTIONAL_DEPENDENCIES = {
    "numpy": "数值计算 (moviepy 依赖)",
    "pillow": "图片处理 (PIL 兼容)",
}

EXTERNAL_TOOLS = {
    "ffmpeg": "视频编码",
    "ffprobe": "视频信息读取",
}


def check_dependency(module_name: str) -> bool:
    """检查 Python 依赖是否已安装"""
    try:
        if module_name == "PIL":
            from PIL import Image
        else:
            importlib.import_module(module_name)
        return True
    except ImportError:
        return False


def check_external_tool(tool_name: str) -> bool:
    """检查外部工具是否可用"""
    try:
        result = subprocess.run(
            [tool_name, "-version"] if tool_name == "ffmpeg" else [tool_name],
            capture_output=True, text=True, timeout=5
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def check_all_dependencies() -> Dict[str, Dict[str, bool]]:
    """检查所有依赖"""
    results = {
        "python": {},
        "external": {}
    }

    for name, desc in REQUIRED_DEPENDENCIES.items():
        results["python"][name] = check_dependency(name)

    for name, desc in OPTIONAL_DEPENDENCIES.items():
        results["python"][name] = check_dependency(name)

    for name, desc in EXTERNAL_TOOLS.items():
        results["external"][name] = check_external_tool(name)

    return results


def install_dependencies(verbose: bool = True) -> bool:
    """安装缺失的 Python 依赖"""
    missing = []
    for name in REQUIRED_DEPENDENCIES:
        if not check_dependency(name):
            # 映射模块名到 pip 包名
            pkg_map = {
                "PIL": "Pillow",
                "moviepy": "moviepy",
                "pydub": "pydub",
                "edge_tts": "edge-tts",
                "requests": "requests",
                "pypinyin": "pypinyin",
            }
            pkg_name = pkg_map.get(name, name)
            missing.append(pkg_name)

    if not missing:
        if verbose:
            print("所有依赖已安装")
        return True

    if verbose:
        print(f"安装缺失依赖: {', '.join(missing)}")

    try:
        subprocess.run(
            [sys.executable, "-m", "pip", "install", *missing],
            check=True, capture_output=not verbose
        )
        return True
    except subprocess.CalledProcessError as e:
        print(f"依赖安装失败: {e}")
        return False


# ==================== 环境验证 ====================

def verify_environment() -> Dict:
    """
    验证部署环境

    Returns:
        环境验证报告
    """
    report = {
        "python_version": sys.version,
        "platform": sys.platform,
        "working_dir": os.getcwd(),
        "dependencies": {},
        "external_tools": {},
        "issues": [],
        "ready": False
    }

    # 检查 Python 依赖
    for name, desc in REQUIRED_DEPENDENCIES.items():
        installed = check_dependency(name)
        report["dependencies"][name] = {
            "installed": installed,
            "description": desc
        }
        if not installed:
            report["issues"].append(f"缺少依赖: {name} ({desc})")

    # 检查外部工具
    for name, desc in EXTERNAL_TOOLS.items():
        available = check_external_tool(name)
        report["external_tools"][name] = {
            "available": available,
            "description": desc
        }
        if not available:
            report["issues"].append(f"外部工具不可用: {name} ({desc})")

    # 检查目录结构
    expected_dirs = ["core", "audio", "image", "video", "utils", "tests"]
    for dir_name in expected_dirs:
        dir_path = os.path.join(os.path.dirname(__file__), dir_name)
        if not os.path.isdir(dir_path):
            report["issues"].append(f"缺少目录: video_gen/{dir_name}")

    # 检查关键文件
    expected_files = [
        "config.py",
        "cli.py",
        "subtitle_importer.py",
        "core/engine.py",
        "core/pipeline.py",
        "video/subtitle.py",
        "video/compositor.py",
    ]
    for file_name in expected_files:
        file_path = os.path.join(os.path.dirname(__file__), file_name)
        if not os.path.isfile(file_path):
            report["issues"].append(f"缺少文件: video_gen/{file_name}")

    report["ready"] = len(report["issues"]) == 0
    return report


# ==================== 目录结构 ====================

def verify_directory_structure() -> List[str]:
    """验证目录结构完整性"""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    issues = []

    expected_structure = {
        ".": ["__init__.py", "config.py", "cli.py", "subtitle_importer.py", "deploy.py"],
        "core": ["__init__.py", "engine.py", "pipeline.py", "state.py"],
        "audio": ["__init__.py", "generator.py", "pause_analyzer.py"],
        "image": ["__init__.py", "api_client.py", "generator.py", "local_renderer.py"],
        "video": ["__init__.py", "compositor.py", "effects.py", "encoder.py", "subtitle.py"],
        "utils": ["__init__.py", "file_utils.py", "logger.py", "validators.py"],
        "tests": ["__init__.py", "test_subtitle_import.py", "test_pipeline.py", "run_all.py"],
    }

    for subdir, files in expected_structure.items():
        dir_path = os.path.join(base_dir, subdir)
        if not os.path.isdir(dir_path):
            issues.append(f"目录不存在: video_gen/{subdir}")
            continue
        for file_name in files:
            file_path = os.path.join(dir_path, file_name)
            if not os.path.isfile(file_path):
                issues.append(f"文件缺失: video_gen/{subdir}/{file_name}")

    return issues


# ==================== 部署流程 ====================

def deploy(verbose: bool = True) -> bool:
    """
    完整部署流程

    Args:
        verbose: 是否输出详细信息

    Returns:
        部署是否成功
    """
    print("=" * 60)
    print("Video Workshop 部署工具")
    print("=" * 60)

    # 步骤1: 检查环境
    print("\n[1/4] 检查运行环境...")
    env_report = verify_environment()
    if env_report["issues"]:
        print(f"  {len(env_report['issues'])} 个问题待解决:")
        for issue in env_report["issues"]:
            print(f"    - {issue}")
    else:
        print("  环境检查通过")

    # 步骤2: 安装依赖
    print("\n[2/4] 安装 Python 依赖...")
    if install_dependencies(verbose):
        print("  依赖安装完成")
    else:
        print("  ! 部分依赖安装失败，请手动安装")
        print("    pip install -r requirements.txt")

    # 步骤3: 验证目录结构
    print("\n[3/4] 验证目录结构...")
    dir_issues = verify_directory_structure()
    if dir_issues:
        print(f"  {len(dir_issues)} 个问题:")
        for issue in dir_issues:
            print(f"    - {issue}")
    else:
        print("  目录结构完整")

    # 步骤4: 运行测试
    print("\n[4/4] 运行单元测试...")
    try:
        test_script = os.path.join(
            os.path.dirname(__file__), "tests", "run_all.py"
        )
        result = subprocess.run(
            [sys.executable, test_script],
            capture_output=not verbose,
            text=True
        )
        if result.returncode == 0:
            print("  测试通过!")
        else:
            print("  ! 部分测试失败")
            if verbose:
                print(result.stdout)
    except Exception as e:
        print(f"  ! 测试执行失败: {e}")

    print("\n" + "=" * 60)
    print("部署完成!")
    print("=" * 60)
    print("\n使用方式:")
    print("  # 诊断系统环境")
    print("  python -m video_gen.cli diagnose")
    print("")
    print("  # 从脚本生成视频")
    print("  python -m video_gen.cli generate -t \"标题\" -s scripts.json")
    print("")
    print("  # 为已有视频自动导入字幕")
    print("  python -m video_gen.cli subtitles -v video.mp4 -s scripts.json")
    print("")
    print("  # 使用独立字幕导入器")
    print("  python video_gen/subtitle_importer.py -v video.mp4 -s scripts.json")

    return True


# ==================== 主入口 ====================

def main():
    """主入口"""
    import argparse

    parser = argparse.ArgumentParser(
        description="Video Workshop 部署工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 执行完整部署
  python deploy.py
  
  # 仅检查环境
  python deploy.py --check
  
  # 仅安装依赖
  python deploy.py --install-deps
  
  # 仅验证目录结构
  python deploy.py --verify
        """
    )

    parser.add_argument("--check", action="store_true", help="仅检查环境")
    parser.add_argument("--install-deps", action="store_true", help="仅安装依赖")
    parser.add_argument("--verify", action="store_true", help="仅验证目录结构")
    parser.add_argument("--quiet", action="store_true", help="静默模式")

    args = parser.parse_args()

    verbose = not args.quiet

    if args.check:
        report = verify_environment()
        import json
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0 if report["ready"] else 1
    elif args.install_deps:
        return 0 if install_dependencies(verbose) else 1
    elif args.verify:
        issues = verify_directory_structure()
        if issues:
            print(f"{len(issues)} 个问题:")
            for issue in issues:
                print(f"  - {issue}")
            return 1
        else:
            print("目录结构完整")
            return 0
    else:
        deploy(verbose)
        return 0


if __name__ == "__main__":
    sys.exit(main())