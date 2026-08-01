#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Video Workshop GUI 启动器

支持两种启动方式：
1. python video_gen/gui_launcher.py
2. 双击运行（Windows）
"""

import os
import sys
import importlib


def check_dependencies() -> bool:
    """检查依赖是否完整"""
    required = {
        "PIL": "Pillow (pip install Pillow)",
        "moviepy": "moviepy (pip install moviepy)",
        "edge_tts": "edge-tts (pip install edge-tts)",
        "pydub": "pydub (pip install pydub)",
        "requests": "requests (pip install requests)",
    }
    missing = []
    for mod, hint in required.items():
        try:
            if mod == "PIL":
                importlib.import_module("PIL.Image")
            else:
                importlib.import_module(mod)
        except ImportError:
            missing.append(f"  - {hint}")

    if missing:
        print("=" * 50)
        print("缺少依赖，请先安装：")
        print("\n".join(missing))
        print("\n安装命令：")
        print("  pip install Pillow moviepy edge-tts pydub requests")
        print("=" * 50)
        return False
    return True


def main():
    # 确保 video_gen 模块可导入
    # 脚本在 video_gen/ 目录下，需要将父目录（项目根目录）加入 sys.path
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

    if not check_dependencies():
        input("按 Enter 键退出...")
        return 1

    try:
        from video_gen.gui import run_gui
        print("正在启动 Video Workshop GUI...")
        run_gui()
        return 0
    except Exception as e:
        print(f"启动失败: {e}")
        import traceback
        traceback.print_exc()
        input("按 Enter 键退出...")
        return 1


if __name__ == "__main__":
    sys.exit(main())