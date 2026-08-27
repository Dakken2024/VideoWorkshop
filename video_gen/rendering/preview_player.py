#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
视频预览播放器 - 使用 OpenCV + Tkinter 实现

功能：
1. 视频播放/暂停/停止
2. 进度条拖拽
3. 音量控制
4. 帧预览
5. 支持多种格式
"""

import tkinter as tk
from tkinter import ttk
import cv2
import threading
import os
from typing import Optional, Callable
from PIL import Image, ImageTk

# 处理导入路径
try:
    from video_gen.utils.logger import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)


class VideoPlayer:
    """
    视频播放器组件
    
    嵌入到 Tkinter 界面中，提供基本播放控制
    """
    
    def __init__(self, parent, video_path: str = ""):
        self.parent = parent
        self.video_path = video_path
        self.cap = None
        self.is_playing = False
        self.current_frame = 0
        self.total_frames = 0
        self.fps = 30
        self._stop_flag = False
        self._play_thread = None
        
        self._build_ui()
        
        if video_path:
            self.load_video(video_path)
    
    def _build_ui(self):
        """构建 UI"""
        # 视频显示区域
        self.video_frame = ttk.Frame(self.parent)
        self.video_frame.pack(fill=tk.BOTH, expand=True)
        
        self.video_label = tk.Label(self.video_frame, bg="black")
        self.video_label.pack(fill=tk.BOTH, expand=True)
        
        # 控制栏
        self.control_frame = ttk.Frame(self.parent)
        self.control_frame.pack(fill=tk.X, pady=5)
        
        # 播放/暂停按钮
        self.play_btn = ttk.Button(
            self.control_frame, text="▶ 播放",
            command=self.toggle_play
        )
        self.play_btn.pack(side=tk.LEFT, padx=5)
        
        # 停止按钮
        self.stop_btn = ttk.Button(
            self.control_frame, text="⏹ 停止",
            command=self.stop
        )
        self.stop_btn.pack(side=tk.LEFT, padx=5)
        
        # 进度条
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Scale(
            self.control_frame, from_=0, to=100,
            variable=self.progress_var,
            orient=tk.HORIZONTAL,
            command=self._on_progress_change
        )
        self.progress_bar.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=10)
        
        # 时间显示
        self.time_label = ttk.Label(
            self.control_frame, text="00:00 / 00:00",
            width=15
        )
        self.time_label.pack(side=tk.LEFT, padx=5)
        
        # 音量控制
        ttk.Label(self.control_frame, text="🔊").pack(side=tk.LEFT, padx=(10, 0))
        self.volume_var = tk.DoubleVar(value=0.8)
        self.volume_slider = ttk.Scale(
            self.control_frame, from_=0, to=1,
            variable=self.volume_var,
            orient=tk.HORIZONTAL,
            length=100
        )
        self.volume_slider.pack(side=tk.LEFT, padx=5)
        
        # 状态标签
        self.status_label = ttk.Label(
            self.control_frame, text="未加载视频",
            foreground="gray"
        )
        self.status_label.pack(side=tk.RIGHT, padx=10)
    
    def load_video(self, video_path: str) -> bool:
        """加载视频"""
        self.stop()
        
        if not os.path.exists(video_path):
            logger.error(f"视频文件不存在：{video_path}")
            self.status_label.configure(text="文件不存在", foreground="red")
            return False
        
        try:
            self.cap = cv2.VideoCapture(video_path)
            
            if not self.cap.isOpened():
                logger.error(f"无法打开视频：{video_path}")
                self.status_label.configure(text="无法打开", foreground="red")
                return False
            
            self.video_path = video_path
            self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
            self.fps = self.cap.get(cv2.CAP_PROP_FPS)
            duration = self.total_frames / self.fps if self.fps > 0 else 0
            
            self.status_label.configure(
                text=f"{os.path.basename(video_path)} ({duration:.1f}s)",
                foreground="green"
            )
            
            # 显示第一帧
            self._show_frame(0)
            
            logger.info(f"视频已加载：{video_path} ({self.total_frames}帧，{self.fps}fps)")
            return True
            
        except Exception as e:
            logger.error(f"加载视频失败：{e}")
            self.status_label.configure(text="加载失败", foreground="red")
            return False
    
    def _show_frame(self, frame_idx: int):
        """显示指定帧"""
        if not self.cap:
            return
        
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
        ret, frame = self.cap.read()
        
        if not ret:
            return
        
        # BGR to RGB
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # 调整大小以适应显示区域
        display_width = self.video_label.winfo_width()
        display_height = self.video_label.winfo_height()
        
        if display_width > 1 and display_height > 1:
            h, w = frame.shape[:2]
            aspect_ratio = w / h
            
            new_w = display_width
            new_h = int(new_w / aspect_ratio)
            
            if new_h > display_height:
                new_h = display_height
                new_w = int(new_h * aspect_ratio)
            
            frame = cv2.resize(frame, (new_w, new_h))
        
        # 转换为 PhotoImage
        img = Image.fromarray(frame)
        photo = ImageTk.PhotoImage(image=img)
        
        self.video_label.configure(image=photo)
        self.video_label.image = photo  # 保持引用
        
        self.current_frame = frame_idx
        self._update_time_display()
    
    def _play_loop(self):
        """播放循环"""
        if not self.cap or self._stop_flag:
            return
        
        while self.is_playing and not self._stop_flag:
            if self.current_frame >= self.total_frames:
                self.is_playing = False
                self.current_frame = 0
                break
            
            self._show_frame(self.current_frame)
            self.progress_var.set((self.current_frame / self.total_frames) * 100)
            
            self.current_frame += 1
            
            # 控制帧率
            import time
            time.sleep(1.0 / self.fps)
        
        self.play_btn.configure(text="▶ 播放")
    
    def toggle_play(self):
        """切换播放/暂停"""
        if not self.cap:
            return
        
        if self.is_playing:
            self.is_playing = False
            self.play_btn.configure(text="▶ 播放")
            logger.debug("视频已暂停")
        else:
            self.is_playing = True
            self.play_btn.configure(text="⏸ 暂停")
            self._stop_flag = False
            
            if self._play_thread is None or not self._play_thread.is_alive():
                self._play_thread = threading.Thread(target=self._play_loop, daemon=True)
                self._play_thread.start()
            
            logger.debug("视频开始播放")
    
    def stop(self):
        """停止播放"""
        self.is_playing = False
        self._stop_flag = True
        self.current_frame = 0
        
        if self.cap:
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            self._show_frame(0)
            self.progress_var.set(0)
        
        self.play_btn.configure(text="▶ 播放")
        logger.debug("视频已停止")
    
    def _on_progress_change(self, value):
        """进度条拖拽"""
        if not self.cap:
            return
        
        frame_idx = int(float(value) / 100 * self.total_frames)
        self._show_frame(frame_idx)
    
    def _update_time_display(self):
        """更新时间显示"""
        current_sec = self.current_frame / self.fps if self.fps > 0 else 0
        total_sec = self.total_frames / self.fps if self.fps > 0 else 0
        
        def format_time(sec):
            mins = int(sec // 60)
            secs = int(sec % 60)
            return f"{mins:02d}:{secs:02d}"
        
        self.time_label.configure(text=f"{format_time(current_sec)} / {format_time(total_sec)}")
    
    def close(self):
        """关闭播放器"""
        self.stop()
        if self.cap:
            self.cap.release()
            self.cap = None


class PreviewTab(ttk.Frame):
    """
    预览标签页 - 集成视频播放器和素材预览
    """
    
    def __init__(self, parent, app=None):
        super().__init__(parent)
        self.app = app
        self.player = None
        self._build_ui()
    
    def _build_ui(self):
        """构建 UI"""
        # 左侧：视频预览区
        left_frame = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        left_frame.pack(fill=tk.BOTH, expand=True)
        
        # 视频播放器面板
        player_frame = ttk.LabelFrame(left_frame, text="视频预览", padding=10)
        left_frame.add(player_frame, weight=3)
        
        self.player = VideoPlayer(player_frame)
        
        # 右侧：素材列表
        list_frame = ttk.LabelFrame(left_frame, text="素材列表", padding=10)
        left_frame.add(list_frame, weight=1)
        
        # 素材树形列表
        columns = ("name", "type", "duration", "tags")
        self.asset_tree = ttk.Treeview(
            list_frame, columns=columns, show="headings", height=15
        )
        
        self.asset_tree.heading("name", text="名称")
        self.asset_tree.heading("type", text="类型")
        self.asset_tree.heading("duration", text="时长")
        self.asset_tree.heading("tags", text="标签")
        
        self.asset_tree.column("name", width=120)
        self.asset_tree.column("type", width=60)
        self.asset_tree.column("duration", width=60)
        self.asset_tree.column("tags", width=100)
        
        scrollbar = ttk.Scrollbar(
            list_frame, orient=tk.VERTICAL, command=self.asset_tree.yview
        )
        self.asset_tree.configure(yscrollcommand=scrollbar.set)
        
        self.asset_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 素材操作按钮
        asset_btn_frame = ttk.Frame(list_frame)
        asset_btn_frame.pack(fill=tk.X, pady=(5, 0))
        
        ttk.Button(asset_btn_frame, text="📁 导入素材", 
                   command=self._import_asset).pack(side=tk.LEFT, padx=2)
        ttk.Button(asset_btn_frame, text="▶ 预览", 
                   command=self._preview_asset).pack(side=tk.LEFT, padx=2)
        ttk.Button(asset_btn_frame, text="🗑 删除", 
                   command=self._delete_asset).pack(side=tk.LEFT, padx=2)
        
        # 底部：生成日志
        log_frame = ttk.LabelFrame(self, text="生成日志", padding=5)
        log_frame.pack(fill=tk.X, padx=10, pady=(5, 10))
        
        self.log_text = tk.Text(log_frame, height=4, wrap=tk.WORD, 
                                font=("Consolas", 9), state=tk.DISABLED)
        self.log_text.pack(fill=tk.X)
    
    def _import_asset(self):
        """导入素材"""
        from tkinter import filedialog
        
        filetypes = [
            ("视频文件", "*.mp4 *.avi *.mov *.mkv"),
            ("图片文件", "*.jpg *.jpeg *.png *.webp"),
            ("音频文件", "*.mp3 *.wav *.m4a"),
            ("所有文件", "*.*")
        ]
        
        path = filedialog.askopenfilename(
            title="选择素材文件",
            filetypes=filetypes
        )
        
        if path:
            self.log(f"导入素材：{path}")
            # TODO: 调用 AssetManager 添加素材
            self._refresh_asset_list()
    
    def _refresh_asset_list(self):
        """刷新素材列表"""
        # 清空现有项
        for item in self.asset_tree.get_children():
            self.asset_tree.delete(item)
        
        # TODO: 从 AssetManager 获取素材列表并填充
        # 示例数据
        sample_assets = [
            ("intro.mp4", "video", "5.2s", "片头"),
            ("bgm_01.mp3", "audio", "180s", "背景音乐"),
            ("scene_01.jpg", "image", "-", "场景"),
        ]
        
        for name, asset_type, duration, tags in sample_assets:
            self.asset_tree.insert("", tk.END, values=(name, asset_type, duration, tags))
    
    def _preview_asset(self):
        """预览选中素材"""
        selection = self.asset_tree.selection()
        if not selection:
            return
        
        item = self.asset_tree.item(selection[0])
        name = item["values"][0]
        asset_type = item["values"][1]
        
        if asset_type == "video":
            # TODO: 获取实际路径并加载
            self.log(f"预览视频：{name}")
            # self.player.load_video(actual_path)
        else:
            self.log(f"暂不支持预览 {asset_type} 类型")
    
    def _delete_asset(self):
        """删除选中素材"""
        selection = self.asset_tree.selection()
        if not selection:
            return
        
        if tk.messagebox.askyesno("确认", "确定要删除选中的素材吗？"):
            item = self.asset_tree.item(selection[0])
            name = item["values"][0]
            self.log(f"删除素材：{name}")
            self.asset_tree.delete(selection[0])
    
    def load_video(self, video_path: str):
        """加载视频进行预览"""
        if self.player:
            success = self.player.load_video(video_path)
            if success:
                self.log(f"已加载视频：{os.path.basename(video_path)}")
            return success
        return False
    
    def log(self, message: str):
        """添加日志"""
        self.log_text.configure(state=tk.NORMAL)
        timestamp = __import__('datetime').datetime.now().strftime("%H:%M:%S")
        self.log_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.log_text.see(tk.END)
        self.log_text.configure(state=tk.DISABLED)
        
        if self.app:
            self.app.log(message)
