#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
视频生成标签页 - 完整生成工作流
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import json
import os
import threading
from typing import Dict, Optional, TYPE_CHECKING

from ..config import DEFAULT_CONFIG
from ..core.engine import VideoGenerationEngine
from ..utils.logger import logger
from ..utils.file_utils import safe_read_json
from ..workflow import OptimizedWorkflow
from .widgets import SectionFrame, ToggleButton

if TYPE_CHECKING:
    from .app import VideoWorkshopGUI


class GenerateTab(ttk.Frame):
    """视频生成标签页"""

    def __init__(self, parent, app: "VideoWorkshopGUI"):
        super().__init__(parent)
        self.app = app
        self._script_data = None
        self._script_path = None
        self._title = ""
        self._stop_flag = False
        self._build_ui()

    def _build_ui(self):
        # 步骤1: 选择脚本
        step1 = SectionFrame(self, "步骤 1: 选择脚本", padding=15)
        step1.pack(fill=tk.X, padx=15, pady=10)

        row1 = ttk.Frame(step1)
        row1.pack(fill=tk.X, pady=3)
        self.script_path_var = tk.StringVar(value="未选择脚本")
        ttk.Label(row1, textvariable=self.script_path_var, foreground="gray").pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(row1, text="选择脚本", command=self._browse_script).pack(side=tk.RIGHT, padx=5)
        ttk.Button(row1, text="从内容创作导入", command=self._import_from_content, state=tk.DISABLED if not hasattr(self.app, 'tab_content') else tk.NORMAL).pack(side=tk.RIGHT, padx=5)

        # 脚本信息
        self.info_frame = ttk.LabelFrame(step1, text="脚本信息", padding=10)
        self.info_frame.pack(fill=tk.X, pady=(10, 0))
        self.info_label = ttk.Label(self.info_frame, text="请选择脚本文件", anchor=tk.W, justify=tk.LEFT)
        self.info_label.pack(fill=tk.X)

        # 步骤2: 生成选项
        step2 = SectionFrame(self, "步骤 2: 生成选项", padding=15)
        step2.pack(fill=tk.X, padx=15, pady=10)

        self.opt_audio = ToggleButton(step2, "生成音频", default=True)
        self.opt_audio.pack(fill=tk.X, pady=2)
        self.opt_images = ToggleButton(step2, "生成图片", default=True)
        self.opt_images.pack(fill=tk.X, pady=2)
        self.opt_subtitle = ToggleButton(step2, "生成字幕", default=True)
        self.opt_subtitle.pack(fill=tk.X, pady=2)

        # 操作按钮
        btn_frame = ttk.Frame(step2)
        btn_frame.pack(fill=tk.X, pady=(10, 0))
        self.start_btn = ttk.Button(btn_frame, text="🚀 生成视频",
                                    command=self._start_generation)
        self.start_btn.pack(side=tk.LEFT, padx=5)
        self.stop_btn = ttk.Button(btn_frame, text="⏹ 停止",
                                  command=self._stop_generation, state=tk.DISABLED)
        self.stop_btn.pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="📁 打开输出", command=self._open_output).pack(side=tk.LEFT, padx=5)

        # 进度
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(step2, variable=self.progress_var,
                                           maximum=100, mode="determinate")
        self.progress_bar.pack(fill=tk.X, pady=(10, 0))
        self.progress_label = ttk.Label(step2, text="就绪", anchor=tk.W)
        self.progress_label.pack(fill=tk.X)

        # 步骤3: 结果
        step3 = SectionFrame(self, "步骤 3: 生成结果", padding=15)
        step3.pack(fill=tk.BOTH, expand=True, padx=15, pady=(0, 10))

        self.result_text = tk.Text(step3, height=6, wrap=tk.WORD, font=("Consolas", 9),
                                   bg="#1e1e1e", fg="#d4d4d4", state=tk.DISABLED)
        self.result_text.pack(fill=tk.BOTH, expand=True)

    def _browse_script(self):
        """浏览选择脚本"""
        path = filedialog.askopenfilename(
            title="选择脚本文件",
            filetypes=[("JSON", "*.json"), ("All", "*.*")]
        )
        if path:
            self.load_script(path)

    def load_script(self, path: str):
        """加载脚本文件"""
        self._script_path = path
        self.script_path_var.set(path)
        try:
            data = safe_read_json(path)
            if data:
                self._script_data = data
                self._update_script_info(data)
            else:
                messagebox.showerror("错误", "无法解析脚本文件")
        except Exception as e:
            messagebox.showerror("错误", f"加载脚本失败: {e}")

    def load_scripts_data(self, data: Dict):
        """加载脚本数据（从内容创作导入）"""
        self._script_data = data
        self._script_path = None
        self.script_path_var.set("从内容创作导入")
        self._update_script_info(data)

    def _update_script_info(self, data: Dict):
        """更新脚本信息"""
        meta = data.get("meta", {})
        scenes = data.get("scenes", [])
        self._title = meta.get("title", "未命名视频")

        info = (
            f"标题: {self._title}\n"
            f"场景数: {len(scenes)}\n"
            f"预估时长: {sum(s.get('duration_sec', 5) for s in scenes)} 秒\n"
            f"主题: {meta.get('topic', 'N/A')}"
        )
        self.info_label.configure(text=info)
        self.app.log(f"脚本已加载: {self._title} ({len(scenes)} 场景)")

    def _import_from_content(self):
        """从内容创作导入"""
        if hasattr(self.app, 'tab_content') and self.app.tab_content._generated_data:
            scripts = self.app.tab_content._generated_data.get("scripts_json")
            if scripts:
                self.load_scripts_data(scripts)
                self.app.log("已从内容创作导入脚本数据")
            else:
                messagebox.showinfo("提示", "内容创作页面尚未生成脚本数据")
        else:
            messagebox.showinfo("提示", "请先在内容创作页面生成内容")

    def _start_generation(self):
        """开始生成"""
        if not self._script_data:
            messagebox.showwarning("提示", "请先选择脚本文件")
            return

        self._stop_flag = False
        self.start_btn.configure(state=tk.DISABLED)
        self.stop_btn.configure(state=tk.NORMAL)
        self.result_text.configure(state=tk.NORMAL)
        self.result_text.delete(1.0, tk.END)
        self.result_text.configure(state=tk.DISABLED)

        self.app.log(f"开始视频生成: {self._title}")
        self.app.set_progress(0, "准备中...")

        self.start_generation(self._script_path, self._title)

    def start_generation(self, script_path: str, title: str):
        """启动生成（供外部调用）"""
        self._title = title

        def run():
            try:
                def progress_callback(current, total, message):
                    self.app.root.after(0, self._update_progress, current, message)
                    if self._stop_flag:
                        raise InterruptedError("用户停止")

                workflow = OptimizedWorkflow()
                result = workflow.quick_generate(
                    script_path=script_path,
                    title=title,
                    progress_callback=progress_callback
                )

                self.app.root.after(0, self._on_generation_done, result)

            except InterruptedError:
                self.app.root.after(0, self.app.log, "生成已停止")
                self.app.root.after(0, self._reset_ui)
            except Exception as e:
                self.app.root.after(0, self.app.log, f"生成失败: {e}")
                self.app.root.after(0, self._reset_ui)

        thread = threading.Thread(target=run, daemon=True)
        thread.start()

    def resume_from(self, project_dir: str):
        """断点续传"""
        self._stop_flag = False
        self.start_btn.configure(state=tk.DISABLED)
        self.stop_btn.configure(state=tk.NORMAL)

        def run():
            try:
                from ..workflow import resume_generate
                self.app.log(f"开始断点续传: {project_dir}")

                def progress_callback(current, total, message):
                    self.app.root.after(0, self._update_progress, current, message)

                workflow = OptimizedWorkflow()
                result = workflow.resume_generate(
                    project_dir=project_dir,
                    progress_callback=progress_callback
                )
                self.app.root.after(0, self._on_generation_done, result)

            except Exception as e:
                self.app.root.after(0, self.app.log, f"续传失败: {e}")
                self.app.root.after(0, self._reset_ui)

        thread = threading.Thread(target=run, daemon=True)
        thread.start()

    def _update_progress(self, value: int, message: str):
        """更新进度"""
        self.progress_var.set(value)
        self.progress_label.configure(text=message)
        self.app.set_progress(value, message)

    def _on_generation_done(self, result: Dict):
        """生成完成"""
        self._reset_ui()

        self.result_text.configure(state=tk.NORMAL)
        self.result_text.delete(1.0, tk.END)

        if result.get("success"):
            video_path = result.get("video_path", "")
            output_dir = result.get("output_dir", "")
            report = result.get("report", {})

            lines = [
                f"✅ 视频生成成功!",
                f"  视频: {video_path or 'N/A'}",
                f"  目录: {output_dir}",
            ]
            files = report.get("files", {})
            if files:
                lines.append(f"  文件数: {len(files)}")
                for fname, finfo in list(files.items())[:5]:
                    lines.append(f"    - {fname} ({finfo.get('size_mb', 0):.1f}MB)")

            errors = result.get("errors", [])
            if errors:
                lines.append(f"  警告: {len(errors)} 个")
                for e in errors[:3]:
                    lines.append(f"    ⚠ {e}")

            self.result_text.insert(tk.END, "\n".join(lines))
            self.app.log(f"✅ 视频生成完成: {video_path}")

            if video_path and os.path.exists(video_path):
                open_video = messagebox.askyesno("完成", f"视频已生成!\n{video_path}\n\n是否打开输出目录？")
                if open_video:
                    import subprocess
                    subprocess.Popen(["explorer", "/select,", os.path.abspath(video_path)])
        else:
            errors = result.get("errors", ["未知错误"])
            error_text = "\n".join(f"❌ {e}" for e in errors)
            self.result_text.insert(tk.END, f"生成失败:\n{error_text}")
            self.app.log(f"❌ 生成失败: {errors}")

        self.result_text.configure(state=tk.DISABLED)

    def _reset_ui(self):
        """重置UI"""
        self.start_btn.configure(state=tk.NORMAL)
        self.stop_btn.configure(state=tk.DISABLED)
        self.progress_var.set(0)
        self.progress_label.configure(text="就绪")

    def _stop_generation(self):
        """停止生成"""
        self._stop_flag = True
        self.app.log("正在停止生成...")

    def _open_output(self):
        """打开输出目录"""
        import subprocess
        output_dir = DEFAULT_CONFIG.paths.output_dir
        if os.path.isdir(output_dir):
            subprocess.Popen(["explorer", os.path.abspath(output_dir)])
        else:
            messagebox.showinfo("提示", f"输出目录不存在: {output_dir}")