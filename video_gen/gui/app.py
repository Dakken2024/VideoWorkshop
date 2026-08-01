#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Video Workshop GUI 主窗口

5个标签页：
1. 首页 - 快速开始、最近项目
2. 内容创作 - 搜索→AI生成→scripts.json
3. 视频生成 - 完整生成工作流
4. API设置 - 所有API配置
5. 历史记录 - 已完成项目
"""

import tkinter as tk
from tkinter import ttk, messagebox
import os
import threading
from typing import Optional

from ..config import DEFAULT_CONFIG
from ..utils.logger import logger
from .widgets import LogWidget, ProgressBar
from .tab_home import HomeTab
from .tab_content import ContentTab
from .tab_generate import GenerateTab
from .tab_settings import SettingsTab
from .tab_history import HistoryTab


class VideoWorkshopGUI:
    """Video Workshop 主窗口"""

    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Video Workshop - 智能视频创作工具")
        self.root.geometry(f"{DEFAULT_CONFIG.window_width}x{DEFAULT_CONFIG.window_height}")
        self.root.minsize(1000, 700)

        # 应用配置
        self.config = DEFAULT_CONFIG
        self._running = False
        self._stop_flag = False

        # 状态栏
        self.status_var = tk.StringVar(value="就绪")

        self._build_ui()
        self._center_window()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build_ui(self):
        """构建UI"""
        # 主框架
        main_frame = ttk.Frame(self.root, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 标签页
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        self.tab_home = HomeTab(self.notebook, self)
        self.tab_content = ContentTab(self.notebook, self)
        self.tab_generate = GenerateTab(self.notebook, self)
        self.tab_settings = SettingsTab(self.notebook, self)
        self.tab_history = HistoryTab(self.notebook, self)

        self.notebook.add(self.tab_home, text="  首页  ")
        self.notebook.add(self.tab_content, text="  内容创作  ")
        self.notebook.add(self.tab_generate, text="  视频生成  ")
        self.notebook.add(self.tab_settings, text="  API设置  ")
        self.notebook.add(self.tab_history, text="  历史记录  ")

        # 底部状态栏
        status_frame = ttk.Frame(main_frame)
        status_frame.pack(fill=tk.X, pady=(5, 0))

        self.progress_bar = ProgressBar(status_frame)
        self.progress_bar.pack(side=tk.LEFT, fill=tk.X, expand=True)

        ttk.Label(status_frame, textvariable=self.status_var, width=20,
                  anchor=tk.E).pack(side=tk.RIGHT, padx=(10, 0))

        # 全局日志
        log_frame = ttk.LabelFrame(main_frame, text="运行日志", padding=5)
        log_frame.pack(fill=tk.BOTH, pady=(5, 0))

        self.log_widget = LogWidget(log_frame, height=6)
        self.log_widget.pack(fill=tk.BOTH, expand=True)

    def _center_window(self):
        """窗口居中"""
        self.root.update_idletasks()
        w = self.root.winfo_width()
        h = self.root.winfo_height()
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        x = (sw - w) // 2
        y = (sh - h) // 2
        self.root.geometry(f"{w}x{h}+{x}+{y}")

    def _on_close(self):
        """关闭窗口"""
        if self._running:
            if not messagebox.askyesno("确认", "当前有任务正在运行，确定要退出吗？"):
                return
            self._stop_flag = True
        self.root.destroy()

    def log(self, message: str):
        """记录日志"""
        self.log_widget.log(message)

    def set_status(self, message: str):
        """设置状态"""
        self.status_var.set(message)
        self.root.update_idletasks()

    def set_progress(self, value: int, message: str = ""):
        """设置进度"""
        self.progress_bar.set_progress(value, message)
        if message:
            self.set_status(message)

    def run_in_thread(self, target, args=(), callback=None):
        """在后台线程执行"""
        def wrapper():
            try:
                self._running = True
                result = target(*args)
                if callback:
                    self.root.after(0, callback, result)
            except Exception as e:
                self.root.after(0, self.log, f"线程错误: {e}")
            finally:
                self._running = False

        thread = threading.Thread(target=wrapper, daemon=True)
        thread.start()

    def run(self):
        """运行主循环"""
        self.root.mainloop()

    def switch_tab(self, tab_index: int):
        """切换到指定标签页"""
        self.notebook.select(tab_index)


def run_gui():
    """启动 GUI"""
    gui = VideoWorkshopGUI()
    gui.run()