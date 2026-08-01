#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
历史记录标签页 - 已完成项目管理和查看
"""

import tkinter as tk
from tkinter import ttk, messagebox
import os
import json
import subprocess
from datetime import datetime
from typing import TYPE_CHECKING

from ..config import DEFAULT_CONFIG
from ..utils.logger import logger
from .widgets import SectionFrame

if TYPE_CHECKING:
    from .app import VideoWorkshopGUI


class HistoryTab(ttk.Frame):
    """历史记录"""

    def __init__(self, parent, app: "VideoWorkshopGUI"):
        super().__init__(parent)
        self.app = app
        self._build_ui()

    def _build_ui(self):
        # 操作栏
        toolbar = ttk.Frame(self)
        toolbar.pack(fill=tk.X, padx=15, pady=10)

        ttk.Button(toolbar, text="🔄 刷新", command=self._refresh).pack(side=tk.LEFT, padx=5)
        ttk.Button(toolbar, text="📁 打开输出目录", command=self._open_output).pack(side=tk.LEFT, padx=5)
        ttk.Button(toolbar, text="🗑 清空历史", command=self._clear_history).pack(side=tk.LEFT, padx=5)

        # 统计信息
        self.stats_frame = ttk.LabelFrame(self, text="统计", padding=10)
        self.stats_frame.pack(fill=tk.X, padx=15, pady=(0, 10))
        self.stats_label = ttk.Label(self.stats_frame, text="加载中...", anchor=tk.W, justify=tk.LEFT)
        self.stats_label.pack(fill=tk.X)

        # 历史列表
        list_frame = ttk.LabelFrame(self, text="项目历史", padding=10)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=(0, 10))

        # 列定义
        columns = ("status", "title", "date", "scenes", "duration", "video", "actions")
        self.tree = ttk.Treeview(list_frame, columns=columns, show="headings", height=12)

        self.tree.heading("status", text="状态")
        self.tree.heading("title", text="标题")
        self.tree.heading("date", text="日期")
        self.tree.heading("scenes", text="场景")
        self.tree.heading("duration", text="时长")
        self.tree.heading("video", text="视频")
        self.tree.heading("actions", text="操作")

        self.tree.column("status", anchor=tk.CENTER, width=40)
        self.tree.column("title", anchor=tk.W, width=200)
        self.tree.column("date", anchor=tk.CENTER, width=80)
        self.tree.column("scenes", anchor=tk.CENTER, width=50)
        self.tree.column("duration", anchor=tk.CENTER, width=60)
        self.tree.column("video", anchor=tk.CENTER, width=80)
        self.tree.column("actions", anchor=tk.CENTER, width=100)

        # 滚动条
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # 双击打开
        self.tree.bind("<Double-1>", self._on_double_click)

        # 右键菜单
        self._context_menu = tk.Menu(self, tearoff=0)
        self._context_menu.add_command(label="打开目录", command=self._open_selected_dir)
        self._context_menu.add_command(label="播放视频", command=self._play_selected_video)
        self._context_menu.add_command(label="断点续传", command=self._resume_selected)
        self.tree.bind("<Button-3>", self._on_right_click)

        # 延迟加载数据，等待父窗口完全初始化
        self.after(200, self._refresh)

    def _refresh(self):
        """刷新历史列表"""
        # 清空
        for item in self.tree.get_children():
            self.tree.delete(item)

        output_dir = DEFAULT_CONFIG.paths.output_dir
        if not os.path.isdir(output_dir):
            self.stats_label.configure(text="输出目录不存在")
            return

        # 扫描项目
        projects = []
        total_videos = 0
        total_duration = 0

        for month_dir in sorted(os.listdir(output_dir), reverse=True):
            month_path = os.path.join(output_dir, month_dir)
            if not os.path.isdir(month_path):
                continue

            for proj in sorted(os.listdir(month_path), reverse=True):
                proj_path = os.path.join(month_path, proj)
                if not os.path.isdir(proj_path):
                    continue

                # 收集信息
                videos = [f for f in os.listdir(proj_path) if f.endswith(".mp4")]
                scripts = [f for f in os.listdir(proj_path) if f == "scripts.json"]
                report = None
                report_path = os.path.join(proj_path, "generation_report.json")
                if os.path.exists(report_path):
                    try:
                        with open(report_path, "r", encoding="utf-8") as f:
                            report = json.load(f)
                    except:
                        pass

                # 提取标题
                title = proj
                scenes_count = 0
                if scripts:
                    try:
                        with open(os.path.join(proj_path, "scripts.json"), "r", encoding="utf-8") as f:
                            data = json.load(f)
                        title = data.get("meta", {}).get("title", proj)
                        scenes_count = len(data.get("scenes", []))
                    except:
                        pass

                # 提取时长
                duration_str = "-"
                video_size = 0  # MB
                if videos:
                    video_path = os.path.join(proj_path, videos[0])
                    video_size = os.path.getsize(video_path) / (1024 * 1024)
                    try:
                        import subprocess as sp
                        result = sp.run(
                            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
                             "-of", "default=noprint_wrappers=1:nokey=1", video_path],
                            capture_output=True, text=True, timeout=10
                        )
                        if result.stdout:
                            dur = float(result.stdout.strip())
                            duration_str = f"{int(dur // 60)}:{int(dur % 60):02d}"
                            total_duration += dur
                    except:
                        pass

                status = "✅" if videos else "⏳"
                if videos:
                    total_videos += 1

                projects.append({
                    "status": status,
                    "title": title,
                    "date": month_dir,
                    "scenes": scenes_count,
                    "duration": duration_str,
                    "video": f"{video_size:.0f}MB" if video_size > 0 else "-",
                    "path": proj_path,
                    "videos": videos,
                })

        # 更新统计
        stats = (
            f"项目总数: {len(projects)}  |  "
            f"已完成视频: {total_videos}  |  "
            f"总时长: {int(total_duration // 60)} 分 {int(total_duration % 60)} 秒"
        )
        self.stats_label.configure(text=stats)

        # 添加列表
        for p in projects:
            self.tree.insert("", tk.END, values=(
                p["status"], p["title"], p["date"],
                p["scenes"], p["duration"], p["video"], "📂打开"
            ))
            # 存储路径
            self.tree.item(self.tree.get_children()[-1], tags=(p["path"],))

        self.app.log(f"刷新历史: {len(projects)} 个项目")

    def _on_double_click(self, event):
        """双击打开"""
        self._open_selected_dir()

    def _on_right_click(self, event):
        """右键菜单"""
        item = self.tree.identify_row(event.y)
        if item:
            self.tree.selection_set(item)
            self._context_menu.post(event.x_root, event.y_root)

    def _get_selected_path(self) -> str:
        """获取选中项目路径"""
        selection = self.tree.selection()
        if selection:
            tags = self.tree.item(selection[0], "tags")
            if tags:
                return tags[0]
        return ""

    def _open_selected_dir(self):
        """打开选中目录"""
        path = self._get_selected_path()
        if path and os.path.isdir(path):
            subprocess.Popen(["explorer", path])
        else:
            messagebox.showinfo("提示", "项目目录不存在")

    def _play_selected_video(self):
        """播放选中视频"""
        path = self._get_selected_path()
        if path and os.path.isdir(path):
            videos = [f for f in os.listdir(path) if f.endswith(".mp4")]
            if videos:
                video_path = os.path.join(path, videos[0])
                os.startfile(video_path)
            else:
                messagebox.showinfo("提示", "该项目没有视频文件")
        else:
            messagebox.showinfo("提示", "项目目录不存在")

    def _resume_selected(self):
        """断点续传选中项目"""
        path = self._get_selected_path()
        if path and os.path.isdir(path):
            self.app.log(f"断点续传: {path}")
            self.app.tab_generate.resume_from(path)
            self.app.switch_tab(2)

    def _open_output(self):
        """打开输出目录"""
        output_dir = DEFAULT_CONFIG.paths.output_dir
        if os.path.isdir(output_dir):
            subprocess.Popen(["explorer", os.path.abspath(output_dir)])
        else:
            messagebox.showinfo("提示", f"输出目录不存在: {output_dir}")

    def _clear_history(self):
        """清空历史"""
        if messagebox.askyesno("确认", "确定要清空历史列表吗？（不会删除文件）"):
            for item in self.tree.get_children():
                self.tree.delete(item)
            self.stats_label.configure(text="无历史记录")
            self.app.log("历史记录已清空")