#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
首页标签页 - 快速开始、最近项目、系统诊断
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
import json
import subprocess
from datetime import datetime
from typing import TYPE_CHECKING

from ..config import DEFAULT_CONFIG
from ..utils.logger import logger
from .widgets import SectionFrame, ActionButton

if TYPE_CHECKING:
    from .app import VideoWorkshopGUI


class HomeTab(ttk.Frame):
    """首页"""

    def __init__(self, parent, app: "VideoWorkshopGUI"):
        super().__init__(parent)
        self.app = app
        self.padding = 20
        self._build_ui()

    def _build_ui(self):
        # 欢迎标题
        welcome = ttk.Label(self, text="🎬 Video Workshop",
                           font=("", 20, "bold"))
        welcome.pack(pady=(20, 5))

        subtitle = ttk.Label(self, text="智能视频创作工具 - 一键生成高质量视频内容",
                            font=("", 10))
        subtitle.pack(pady=(0, 20))

        # 快捷操作区
        quick_frame = SectionFrame(self, "快速开始", padding=15)
        quick_frame.pack(fill=tk.X, padx=self.padding, pady=(0, 10))

        btn_frame = ttk.Frame(quick_frame)
        btn_frame.pack(pady=10)

        ttk.Button(btn_frame, text="📂 选择脚本", width=15,
                   command=self._select_script).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="▶ 快速生成", width=15,
                   command=self._quick_generate).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="🔄 断点续传", width=15,
                   command=self._resume_generate).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="✍ 内容创作", width=15,
                   command=lambda: self.app.switch_tab(1)).pack(side=tk.LEFT, padx=5)

        # 最近项目
        recent_frame = SectionFrame(self, "最近项目", padding=15)
        recent_frame.pack(fill=tk.BOTH, expand=True, padx=self.padding, pady=10)

        self.recent_listbox = tk.Listbox(recent_frame, height=8, font=("", 10))
        self.recent_listbox.pack(fill=tk.BOTH, expand=True)

        list_btn_frame = ttk.Frame(recent_frame)
        list_btn_frame.pack(fill=tk.X, pady=(10, 0))

        ttk.Button(list_btn_frame, text="打开选中项目",
                   command=self._open_selected).pack(side=tk.LEFT, padx=5)
        ttk.Button(list_btn_frame, text="刷新列表",
                   command=self._refresh_recent).pack(side=tk.LEFT, padx=5)

        # 底部工具
        tool_frame = ttk.Frame(self)
        tool_frame.pack(fill=tk.X, padx=self.padding, pady=10)

        ttk.Button(tool_frame, text="🔧 系统诊断",
                   command=self._diagnose).pack(side=tk.LEFT, padx=5)
        ttk.Button(tool_frame, text="📁 打开输出目录",
                   command=self._open_output).pack(side=tk.LEFT, padx=5)
        ttk.Button(tool_frame, text="⚙ API设置",
                   command=lambda: self.app.switch_tab(3)).pack(side=tk.LEFT, padx=5)

        # 加载最近项目
        self._refresh_recent()

    def _select_script(self):
        """选择脚本文件"""
        path = filedialog.askopenfilename(
            title="选择脚本文件",
            filetypes=[("JSON", "*.json"), ("All", "*.*")]
        )
        if path:
            self.app.log(f"已选择脚本: {path}")
            self.app.switch_tab(2)  # 切换到视频生成页面
            # 通知生成页面加载脚本
            self.app.tab_generate.load_script(path)

    def _quick_generate(self):
        """快速生成"""
        path = filedialog.askopenfilename(
            title="选择脚本文件",
            filetypes=[("JSON", "*.json")]
        )
        if not path:
            return

        title = ""
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            title = data.get("meta", {}).get("title", "")
        except:
            title = os.path.splitext(os.path.basename(path))[0]

        self.app.log(f"开始快速生成: {title}")
        self.app.tab_generate.start_generation(path, title)

    def _resume_generate(self):
        """断点续传"""
        path = filedialog.askdirectory(title="选择项目目录")
        if path:
            self.app.log(f"断点续传: {path}")
            self.app.tab_generate.resume_from(path)

    def _open_selected(self):
        """打开选中项目"""
        selection = self.recent_listbox.curselection()
        if selection:
            text = self.recent_listbox.get(selection[0])
            # 提取路径
            if "|" in text:
                path = text.split("|")[-1].strip()
                if os.path.isdir(path):
                    import subprocess
                    subprocess.Popen(["explorer", path])

    def _refresh_recent(self):
        """刷新最近项目列表"""
        self.recent_listbox.delete(0, tk.END)
        output_dir = DEFAULT_CONFIG.paths.output_dir
        if os.path.isdir(output_dir):
            projects = []
            for month_dir in sorted(os.listdir(output_dir), reverse=True)[:3]:
                month_path = os.path.join(output_dir, month_dir)
                if os.path.isdir(month_path):
                    for proj in sorted(os.listdir(month_path), reverse=True)[:5]:
                        proj_path = os.path.join(month_path, proj)
                        if os.path.isdir(proj_path):
                            # 查找视频文件
                            videos = [f for f in os.listdir(proj_path)
                                      if f.endswith(".mp4")]
                            status = "✅" if videos else "⏳"
                            date = f"{month_dir[:4]}-{month_dir[4:]}"
                            projects.append(f"{status} {proj} | {date} | {proj_path}")

            for p in projects[:10]:
                self.recent_listbox.insert(tk.END, p)

    def _diagnose(self):
        """系统诊断"""
        def run():
            self.app.log("正在诊断系统环境...")
            self.app.set_progress(10, "检查 Python 环境...")

            report = []
            report.append(f"Python: {__import__('sys').version}")

            # 检查依赖
            deps = {"moviepy": "MoviePy", "PIL": "Pillow", "edge_tts": "edge-tts",
                    "requests": "requests"}
            for mod, name in deps.items():
                try:
                    __import__(mod)
                    report.append(f"  {name}: ✅ 已安装")
                except:
                    report.append(f"  {name}: ❌ 未安装")

            self.app.set_progress(50, "检查 FFmpeg...")
            try:
                result = subprocess.run(["ffmpeg", "-version"],
                                        capture_output=True, text=True, timeout=5)
                version = result.stdout.split("\n")[0] if result.stdout else "?"
                report.append(f"  FFmpeg: ✅ {version[:60]}")
            except:
                report.append(f"  FFmpeg: ❌ 未找到")

            self.app.set_progress(80, "检查输出目录...")
            output_dir = DEFAULT_CONFIG.paths.output_dir
            if os.path.isdir(output_dir):
                report.append(f"  输出目录: ✅ {output_dir}")
            else:
                report.append(f"  输出目录: ⚠ {output_dir} (不存在)")

            self.app.set_progress(100, "诊断完成")
            self.app.log("\n".join(report))
            messagebox.showinfo("系统诊断", "\n".join(report))

        self.app.run_in_thread(run)

    def _open_output(self):
        """打开输出目录"""
        output_dir = DEFAULT_CONFIG.paths.output_dir
        if os.path.isdir(output_dir):
            subprocess.Popen(["explorer", os.path.abspath(output_dir)])
        else:
            messagebox.showinfo("提示", f"输出目录不存在: {output_dir}")