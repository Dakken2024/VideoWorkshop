#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
内容创作标签页 - 搜索→AI生成→scripts.json 完整流水线
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import json
import os
import threading
from typing import TYPE_CHECKING

from ..config import DEFAULT_CONFIG
from ..ai import ScriptGenerator, SearchManager, PLATFORM_PROMPTS
from ..utils.logger import logger
from .widgets import LogWidget, ProgressBar, ApiKeyEntry

if TYPE_CHECKING:
    from .app import VideoWorkshopGUI


class ContentTab(ttk.Frame):
    """内容创作"""

    def __init__(self, parent, app: "VideoWorkshopGUI"):
        super().__init__(parent)
        self.app = app
        self._generated_data = None
        self._build_ui()

    def _build_ui(self):
        # 输入区域
        input_frame = ttk.LabelFrame(self, text="创作输入", padding=15)
        input_frame.pack(fill=tk.X, padx=15, pady=10)

        # 主题
        row1 = ttk.Frame(input_frame)
        row1.pack(fill=tk.X, pady=3)
        ttk.Label(row1, text="创作主题:", width=12, anchor=tk.W).pack(side=tk.LEFT)
        self.topic_var = tk.StringVar(value="历史上的今天有什么科技相关的事件或者趣事")
        self.topic_entry = ttk.Entry(row1, textvariable=self.topic_var)
        self.topic_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # 平台风格
        row2 = ttk.Frame(input_frame)
        row2.pack(fill=tk.X, pady=3)
        ttk.Label(row2, text="平台风格:", width=12, anchor=tk.W).pack(side=tk.LEFT)
        self.platform_var = tk.StringVar(value="wechat")
        platforms = [("微信公众号", "wechat"), ("知识科普", "science")]
        for text, value in platforms:
            ttk.Radiobutton(row2, text=text, variable=self.platform_var,
                           value=value).pack(side=tk.LEFT, padx=5)

        # 补充提示词
        row3 = ttk.Frame(input_frame)
        row3.pack(fill=tk.X, pady=3)
        ttk.Label(row3, text="补充要求:", width=12, anchor=tk.W).pack(side=tk.LEFT)
        self.extra_var = tk.StringVar()
        ttk.Entry(row3, textvariable=self.extra_var).pack(side=tk.LEFT, fill=tk.X, expand=True)

        # 操作按钮
        btn_frame = ttk.Frame(input_frame)
        btn_frame.pack(fill=tk.X, pady=(10, 0))
        self.start_btn = ttk.Button(btn_frame, text="🚀 开始创作",
                                    command=self._start_creation)
        self.start_btn.pack(side=tk.LEFT, padx=5)
        self.stop_btn = ttk.Button(btn_frame, text="⏹ 停止",
                                  command=self._stop_creation, state=tk.DISABLED)
        self.stop_btn.pack(side=tk.LEFT, padx=5)

        # 进度
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(input_frame, variable=self.progress_var,
                                           maximum=100, mode="determinate")
        self.progress_bar.pack(fill=tk.X, pady=(10, 0))
        self.progress_label = ttk.Label(input_frame, text="就绪", anchor=tk.W)
        self.progress_label.pack(fill=tk.X)

        # 预览区域
        preview_frame = ttk.LabelFrame(self, text="生成预览", padding=10)
        preview_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=(0, 10))

        self.preview_text = scrolledtext.ScrolledText(preview_frame, height=15,
                                                      wrap=tk.WORD, font=("", 10))
        self.preview_text.pack(fill=tk.BOTH, expand=True)

        # 预览操作
        preview_btn_frame = ttk.Frame(preview_frame)
        preview_btn_frame.pack(fill=tk.X, pady=(10, 0))

        ttk.Button(preview_btn_frame, text="📄 导出 Markdown",
                   command=self._export_markdown).pack(side=tk.LEFT, padx=5)
        ttk.Button(preview_btn_frame, text="🎬 生成视频",
                   command=self._generate_video).pack(side=tk.LEFT, padx=5)
        ttk.Button(preview_btn_frame, text="🔄 重新生成",
                   command=self._regenerate).pack(side=tk.LEFT, padx=5)
        ttk.Button(preview_btn_frame, text="清空",
                   command=self._clear_preview).pack(side=tk.LEFT, padx=5)

    def _start_creation(self):
        """开始创作"""
        topic = self.topic_var.get().strip()
        if not topic:
            messagebox.showwarning("提示", "请输入创作主题")
            return

        platform = self.platform_var.get()
        extra = self.extra_var.get().strip()

        self.start_btn.configure(state=tk.DISABLED)
        self.stop_btn.configure(state=tk.NORMAL)
        self.preview_text.delete(1.0, tk.END)
        self._generated_data = None
        self._stop_flag = False

        def run():
            try:
                self.app.log(f"开始创作: {topic} (平台: {platform})")

                def progress_callback(stage, message):
                    self.app.root.after(0, self._update_progress, stage, message)
                    if self._stop_flag:
                        raise InterruptedError("用户停止")

                generator = ScriptGenerator()
                result = generator.generate(topic, platform, extra,
                                            progress_callback=progress_callback)

                self.app.root.after(0, self._on_result, result)

            except InterruptedError:
                self.app.root.after(0, self.log, "创作已停止")
                self.app.root.after(0, self._reset_ui)
            except Exception as e:
                self.app.root.after(0, self.app.log, f"创作失败: {e}")
                self.app.root.after(0, self._reset_ui)

        thread = threading.Thread(target=run, daemon=True)
        thread.start()

    def _stop_creation(self):
        """停止创作"""
        self._stop_flag = True
        self.app.log("正在停止创作...")

    def _update_progress(self, stage: str, message: str):
        """更新进度"""
        stages = {"search": 20, "generate_article": 50, "generate_scripts": 80, "done": 100}
        value = stages.get(stage, 0)
        self.progress_var.set(value)
        self.progress_label.configure(text=message)
        self.app.log(f"[{stage}] {message}")

    def _on_result(self, result: dict):
        """处理结果"""
        self._reset_ui()

        if result.get("success"):
            self._generated_data = result
            article = result.get("article", "")
            self.preview_text.delete(1.0, tk.END)
            self.preview_text.insert(1.0, article)

            scripts = result.get("scripts_json", {})
            scenes = scripts.get("scenes", [])
            self.app.log(f"✅ 创作完成! 文章已生成，共 {len(scenes)} 个场景")

            if scripts:
                self.app.log(f"📄 scripts.json 已生成，可直接用于视频生成")
        else:
            error = result.get("error", "未知错误")
            self.app.log(f"❌ 创作失败: {error}")
            messagebox.showerror("创作失败", error)

    def _reset_ui(self):
        """重置UI状态"""
        self.start_btn.configure(state=tk.NORMAL)
        self.stop_btn.configure(state=tk.DISABLED)

    def _export_markdown(self):
        """导出Markdown"""
        if not self._generated_data:
            messagebox.showinfo("提示", "还没有生成内容")
            return

        from tkinter import filedialog
        path = filedialog.asksaveasfilename(
            defaultextension=".md",
            filetypes=[("Markdown", "*.md"), ("All", "*.*")]
        )
        if path:
            article = self._generated_data.get("article", "")
            with open(path, "w", encoding="utf-8") as f:
                f.write(article)
            self.app.log(f"文章已导出: {path}")

    def _generate_video(self):
        """生成视频"""
        if not self._generated_data or not self._generated_data.get("scripts_json"):
            messagebox.showinfo("提示", "还没有生成有效的脚本数据")
            return

        # 切换到视频生成页面
        self.app.switch_tab(2)
        # 传入脚本数据
        self.app.tab_generate.load_scripts_data(self._generated_data["scripts_json"])

    def _regenerate(self):
        """重新生成"""
        self._start_creation()

    def _clear_preview(self):
        """清空预览"""
        self.preview_text.delete(1.0, tk.END)
        self._generated_data = None

    def log(self, message):
        self.app.log(message)