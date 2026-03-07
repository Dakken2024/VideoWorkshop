import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import json
import os
import re
import asyncio
import threading
from datetime import datetime
import shutil
from PIL import Image, ImageTk
import traceback
from concurrent.futures import ThreadPoolExecutor, Future
import subprocess

class AsyncGUIManager:
    """异步GUI管理器 - 处理多线程和异步操作"""
    
    def __init__(self, gui_instance):
        self.gui = gui_instance
        self.executor = ThreadPoolExecutor(max_workers=4)
        self.loop = None
        self.active_tasks = {}  # 跟踪活跃任务
        self.task_counter = 0
        
    def start_async_loop(self):
        """启动异步事件循环"""
        def run_loop():
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)
            self.loop.run_forever()
            
        thread = threading.Thread(target=run_loop, daemon=True, name="AsyncLoopThread")
        thread.start()
        
    async def async_task_wrapper(self, func, *args, task_id=None, **kwargs):
        """异步任务包装器"""
        try:
            if asyncio.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            else:
                # 对于普通函数，使用线程池执行
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(self.executor, func, *args, **kwargs)
            
            # 任务完成回调
            if task_id and task_id in self.active_tasks:
                del self.active_tasks[task_id]
                self.gui.update_ui_safely(self.gui.update_task_status, task_id, "completed")
                
            return result
        except Exception as e:
            if task_id and task_id in self.active_tasks:
                self.active_tasks[task_id]['error'] = str(e)
                self.gui.update_ui_safely(self.gui.update_task_status, task_id, "error", str(e))
            raise
    
    def submit_task(self, func, *args, callback=None, **kwargs):
        """提交异步任务"""
        task_id = f"task_{self.task_counter}"
        self.task_counter += 1
        
        self.active_tasks[task_id] = {
            'function': func.__name__,
            'status': 'running',
            'start_time': datetime.now()
        }
        
        # 更新UI显示新任务
        self.gui.update_ui_safely(self.gui.add_task_indicator, task_id, func.__name__)
        
        async def task_wrapper():
            try:
                result = await self.async_task_wrapper(func, *args, task_id=task_id, **kwargs)
                if callback:
                    self.gui.update_ui_safely(callback, result)
            except Exception as e:
                self.gui.append_log(f"任务 {task_id} 执行失败: {str(e)}\n")
                if callback:
                    self.gui.update_ui_safely(callback, None, error=str(e))
        
        if self.loop:
            asyncio.run_coroutine_threadsafe(task_wrapper(), self.loop)
        
        return task_id
    
    def cancel_task(self, task_id):
        """取消任务"""
        if task_id in self.active_tasks:
            self.active_tasks[task_id]['status'] = 'cancelled'
            self.gui.update_ui_safely(self.gui.update_task_status, task_id, "cancelled")
            # 实际取消逻辑需要在具体任务中实现
            return True
        return False
    
    def get_active_tasks(self):
        """获取活跃任务列表"""
        return dict(self.active_tasks)


class VideoCreatorGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Video Creator GUI - Saabor AI Builds (优化版)")
        self.root.geometry("1200x800")
        
        # 初始化异步管理器
        self.async_manager = AsyncGUIManager(self)
        self.async_manager.start_async_loop()
        
        # 当前项目数据
        self.current_title = ""
        self.current_scripts = {}
        self.output_dir = "./output"
        
        # 任务状态跟踪
        self.task_indicators = {}
        
        # 图片生成状态跟踪 - 记录已生成的图片
        self.image_generation_status = {}  # 格式: {(project_name, scene_index): True/False}
        self._load_image_generation_status()
        
        # 创建界面
        self.create_widgets()
        
    def create_widgets(self):
        # 创建主框架
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 创建笔记本控件（标签页）
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        
        # 创建各个标签页（日志标签页需要先创建，因为其他标签页可能用到append_log）
        self.create_content_tab()
        self.create_script_tab()
        self.create_image_tab()
        self.create_generate_tab()
        self.create_log_tab()
        self.create_history_tab()
        
        # 创建状态栏
        self.create_status_bar(main_frame)
        
    def create_content_tab(self):
        """内容编辑标签页"""
        content_frame = ttk.Frame(self.notebook)
        self.notebook.add(content_frame, text="视频内容")
        
        # 标题输入
        title_frame = ttk.LabelFrame(content_frame, text="视频标题", padding=10)
        title_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.title_entry = ttk.Entry(title_frame, width=50)
        self.title_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.title_entry.bind('<KeyRelease>', self.on_title_change)
        
        # 内容编辑区
        content_editor_frame = ttk.LabelFrame(content_frame, text="视频内容 (Markdown格式)", padding=10)
        content_editor_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        self.content_text = scrolledtext.ScrolledText(content_editor_frame, height=15)
        self.content_text.pack(fill=tk.BOTH, expand=True)
        
        # 文件操作按钮
        content_btn_frame = ttk.Frame(content_editor_frame)
        content_btn_frame.pack(fill=tk.X, pady=(10, 0))
        
        ttk.Button(content_btn_frame, text="从文件加载", command=self.load_content_file).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(content_btn_frame, text="保存到文件", command=self.save_content_file).pack(side=tk.LEFT)
        
    def create_script_tab(self):
        """脚本编辑标签页"""
        script_frame = ttk.Frame(self.notebook)
        self.notebook.add(script_frame, text="视频脚本")
        
        # 脚本编辑区
        script_editor_frame = ttk.LabelFrame(script_frame, text="脚本内容 (JSON格式)", padding=10)
        script_editor_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        self.script_text = scrolledtext.ScrolledText(script_editor_frame, height=20)
        self.script_text.pack(fill=tk.BOTH, expand=True)
        
        # 文件操作按钮
        script_btn_frame = ttk.Frame(script_editor_frame)
        script_btn_frame.pack(fill=tk.X, pady=(10, 0))
        
        ttk.Button(script_btn_frame, text="从文件加载", command=self.load_script_file).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(script_btn_frame, text="保存到文件", command=self.save_script_file).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(script_btn_frame, text="验证JSON", command=self.validate_script).pack(side=tk.LEFT)
        
    def create_image_tab(self):
        """图片管理标签页"""
        image_frame = ttk.Frame(self.notebook)
        self.notebook.add(image_frame, text="图片管理")
        
        # 场景列表
        scene_list_frame = ttk.LabelFrame(image_frame, text="场景列表", padding=10)
        scene_list_frame.pack(fill=tk.Y, side=tk.LEFT, padx=(10, 5), pady=5)
        
        # 场景列表框
        self.scene_listbox = tk.Listbox(scene_list_frame, width=30, height=20)
        self.scene_listbox.pack(fill=tk.Y, expand=True)
        self.scene_listbox.bind('<<ListboxSelect>>', self.on_scene_select)
        
        # 图片预览和操作区
        image_preview_frame = ttk.LabelFrame(image_frame, text="图片预览和编辑", padding=10)
        image_preview_frame.pack(fill=tk.BOTH, expand=True, side=tk.RIGHT, padx=(5, 10), pady=5)
        
        # 图片显示区域
        self.image_label = ttk.Label(image_preview_frame, text="请选择场景查看图片")
        self.image_label.pack(pady=20)
        
        # Prompt编辑
        prompt_frame = ttk.LabelFrame(image_preview_frame, text="Prompt编辑", padding=10)
        prompt_frame.pack(fill=tk.X, pady=(10, 0))
        
        self.prompt_text = scrolledtext.ScrolledText(prompt_frame, height=4)
        self.prompt_text.pack(fill=tk.X)
        
        # 操作按钮
        image_btn_frame = ttk.Frame(image_preview_frame)
        image_btn_frame.pack(fill=tk.X, pady=(10, 0))
        
        ttk.Button(image_btn_frame, text="本地选择图片", command=self.upload_image).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(image_btn_frame, text="重新生成图片", command=self.regenerate_image).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(image_btn_frame, text="批量生成所有图片", command=self.batch_generate_images).pack(side=tk.LEFT)
        
    def create_generate_tab(self):
        """视频生成标签页"""
        generate_frame = ttk.Frame(self.notebook)
        self.notebook.add(generate_frame, text="视频生成")
        
        # 生成配置
        config_frame = ttk.LabelFrame(generate_frame, text="生成配置", padding=10)
        config_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # 输出目录设置
        output_frame = ttk.Frame(config_frame)
        output_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(output_frame, text="输出目录:").pack(side=tk.LEFT)
        self.output_entry = ttk.Entry(output_frame, width=50)
        self.output_entry.pack(side=tk.LEFT, padx=(10, 10), fill=tk.X, expand=True)
        self.output_entry.insert(0, self.output_dir)
        ttk.Button(output_frame, text="浏览", command=self.browse_output_dir).pack(side=tk.RIGHT)
        
        # 生成选项
        options_frame = ttk.Frame(config_frame)
        options_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.generate_audio_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(options_frame, text="生成音频", variable=self.generate_audio_var).pack(side=tk.LEFT, padx=(0, 20))
        
        self.generate_video_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(options_frame, text="生成视频", variable=self.generate_video_var).pack(side=tk.LEFT)
        
        # 生成按钮
        generate_btn_frame = ttk.Frame(generate_frame)
        generate_btn_frame.pack(fill=tk.X, padx=10, pady=20)
        
        self.generate_btn = ttk.Button(generate_btn_frame, text="开始生成视频", command=self.start_generation, style="Accent.TButton")
        self.generate_btn.pack(pady=20)
        
        # 进度条
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(generate_btn_frame, variable=self.progress_var, maximum=100)
        self.progress_bar.pack(fill=tk.X, padx=20)
        
        self.progress_label = ttk.Label(generate_btn_frame, text="准备就绪")
        self.progress_label.pack(pady=(10, 0))
        
    def create_status_bar(self, parent):
        """创建状态栏"""
        self.status_frame = ttk.Frame(parent)
        self.status_frame.pack(fill=tk.X, pady=(5, 0))
        
        # 状态信息
        self.status_label = ttk.Label(self.status_frame, text="就绪")
        self.status_label.pack(side=tk.LEFT, padx=5)
        
        # 任务指示器容器
        self.tasks_frame = ttk.Frame(self.status_frame)
        self.tasks_frame.pack(side=tk.RIGHT, padx=5)
        
        # 活跃任务数显示
        self.active_tasks_label = ttk.Label(self.status_frame, text="活跃任务: 0")
        self.active_tasks_label.pack(side=tk.RIGHT, padx=10)
        
    def create_history_tab(self):
        """视频生成历史记录标签页"""
        history_frame = ttk.Frame(self.notebook)
        self.notebook.add(history_frame, text="生成记录")
        
        # 顶部工具栏
        toolbar_frame = ttk.Frame(history_frame)
        toolbar_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Button(toolbar_frame, text="刷新列表", command=self.refresh_history_list).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(toolbar_frame, text="打开输出目录", command=self.open_output_directory).pack(side=tk.LEFT)
        
        # 历史记录列表区域
        list_frame = ttk.LabelFrame(history_frame, text="视频生成历史", padding=10)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # 创建Treeview显示历史记录
        columns = ('folder_name', 'title', 'date', 'scenes', 'video_file', 'path')
        self.history_tree = ttk.Treeview(list_frame, columns=columns, show='headings', height=15)
        
        # 定义列
        self.history_tree.heading('folder_name', text='目录名称')
        self.history_tree.heading('title', text='视频标题')
        self.history_tree.heading('date', text='生成日期')
        self.history_tree.heading('scenes', text='场景数')
        self.history_tree.heading('video_file', text='视频文件')
        self.history_tree.heading('path', text='完整路径')
        
        # 设置列宽
        self.history_tree.column('folder_name', width=200)
        self.history_tree.column('title', width=150)
        self.history_tree.column('date', width=100)
        self.history_tree.column('scenes', width=60, anchor='center')
        self.history_tree.column('video_file', width=150)
        self.history_tree.column('path', width=300)
        
        # 添加滚动条
        scrollbar_y = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.history_tree.yview)
        scrollbar_x = ttk.Scrollbar(list_frame, orient=tk.HORIZONTAL, command=self.history_tree.xview)
        self.history_tree.configure(yscrollcommand=scrollbar_y.set, xscrollcommand=scrollbar_x.set)
        
        self.history_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar_y.pack(side=tk.RIGHT, fill=tk.Y)
        scrollbar_x.pack(side=tk.BOTTOM, fill=tk.X)
        
        # 绑定双击事件
        self.history_tree.bind('<Double-1>', self.on_history_item_double_click)
        
        # 详情和操作区域
        detail_frame = ttk.LabelFrame(history_frame, text="详情与操作", padding=10)
        detail_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # 选中的项目信息
        self.selected_history_label = ttk.Label(detail_frame, text="请选择一个项目查看详情", wraplength=800)
        self.selected_history_label.pack(fill=tk.X, pady=(0, 10))
        
        # 操作按钮
        btn_frame = ttk.Frame(detail_frame)
        btn_frame.pack(fill=tk.X)
        
        ttk.Button(btn_frame, text="打开文件夹", command=self.open_selected_folder).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(btn_frame, text="播放视频", command=self.play_selected_video).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(btn_frame, text="查看脚本", command=self.view_selected_script).pack(side=tk.LEFT)
        
        # 绑定选择事件
        self.history_tree.bind('<<TreeviewSelect>>', self.on_history_select)
        
        # 加载历史记录
        self.refresh_history_list()
    
    def refresh_history_list(self):
        """刷新历史记录列表"""
        # 清空现有记录
        for item in self.history_tree.get_children():
            self.history_tree.delete(item)
        
        try:
            if not os.path.exists(self.output_dir):
                return
            
            # 遍历输出目录
            for month_dir in os.listdir(self.output_dir):
                month_path = os.path.join(self.output_dir, month_dir)
                if not os.path.isdir(month_path):
                    continue
                
                # 检查是否是年月格式目录
                if not re.match(r'^\d{6}$', month_dir):
                    continue
                
                # 遍历该月目录下的所有项目
                for project_dir in os.listdir(month_path):
                    project_path = os.path.join(month_path, project_dir)
                    if not os.path.isdir(project_path):
                        continue
                    
                    # 检查是否有脚本文件
                    script_path = os.path.join(project_path, "scripts.json")
                    if not os.path.exists(script_path):
                        continue
                    
                    try:
                        # 读取脚本信息
                        with open(script_path, 'r', encoding='utf-8') as f:
                            script_data = json.load(f)
                        
                        meta = script_data.get('meta', {})
                        title = meta.get('title', '未知标题')
                        scenes = script_data.get('scenes', [])
                        scene_count = len(scenes)
                        
                        # 获取生成日期（从目录修改时间或脚本中的时间）
                        mtime = os.path.getmtime(project_path)
                        date_str = datetime.fromtimestamp(mtime).strftime('%Y-%m-%d')
                        
                        # 查找视频文件
                        video_files = [f for f in os.listdir(project_path) if f.endswith('.mp4')]
                        video_file = video_files[0] if video_files else '无'
                        
                        # 友好的目录名称显示
                        display_folder = self._format_folder_name(project_dir)
                        
                        # 插入到列表
                        self.history_tree.insert('', tk.END, values=(
                            display_folder,
                            title,
                            date_str,
                            scene_count,
                            video_file,
                            project_path
                        ))
                        
                    except Exception as e:
                        # 跳过无法解析的项目
                        continue
            
            self.append_log(f"已加载 {len(self.history_tree.get_children())} 条历史记录\n")
            
        except Exception as e:
            self.append_log(f"刷新历史记录失败: {str(e)}\n")
    
    def _format_folder_name(self, folder_name):
        """格式化文件夹名称为更友好的显示"""
        # 将下划线替换为空格，并适当截断
        display_name = folder_name.replace('_', ' ')
        if len(display_name) > 40:
            display_name = display_name[:37] + '...'
        return display_name
    
    def on_history_select(self, event):
        """历史记录选择事件"""
        selection = self.history_tree.selection()
        if selection:
            item = self.history_tree.item(selection[0])
            values = item['values']
            if values:
                folder_name, title, date, scenes, video_file, path = values
                info = f"标题: {title} | 场景数: {scenes} | 生成日期: {date} | 路径: {path}"
                self.selected_history_label.configure(text=info)
    
    def on_history_item_double_click(self, event):
        """历史记录双击事件 - 打开文件夹"""
        self.open_selected_folder()
    
    def open_selected_folder(self):
        """打开选中的项目文件夹"""
        selection = self.history_tree.selection()
        if not selection:
            messagebox.showinfo("提示", "请先选择一个项目")
            return
        
        item = self.history_tree.item(selection[0])
        values = item['values']
        if values and len(values) >= 6:
            path = values[5]  # 完整路径
            if os.path.exists(path):
                try:
                    # 使用explorer打开文件夹
                    subprocess.Popen(f'explorer "{path}"')
                    self.append_log(f"打开文件夹: {path}\n")
                except Exception as e:
                    messagebox.showerror("错误", f"无法打开文件夹: {str(e)}")
            else:
                messagebox.showerror("错误", "文件夹不存在")
    
    def open_output_directory(self):
        """打开输出根目录"""
        if os.path.exists(self.output_dir):
            try:
                subprocess.Popen(f'explorer "{self.output_dir}"')
            except Exception as e:
                messagebox.showerror("错误", f"无法打开目录: {str(e)}")
        else:
            messagebox.showerror("错误", "输出目录不存在")
    
    def play_selected_video(self):
        """播放选中的视频"""
        selection = self.history_tree.selection()
        if not selection:
            messagebox.showinfo("提示", "请先选择一个项目")
            return
        
        item = self.history_tree.item(selection[0])
        values = item['values']
        if values and len(values) >= 6:
            path = values[5]
            video_file = values[4]
            
            if video_file == '无':
                messagebox.showinfo("提示", "该项目没有视频文件")
                return
            
            video_path = os.path.join(path, video_file)
            if os.path.exists(video_path):
                try:
                    # 使用系统默认播放器打开视频
                    os.startfile(video_path)
                    self.append_log(f"播放视频: {video_path}\n")
                except Exception as e:
                    messagebox.showerror("错误", f"无法播放视频: {str(e)}")
            else:
                messagebox.showerror("错误", "视频文件不存在")
    
    def view_selected_script(self):
        """查看选中的脚本文件"""
        selection = self.history_tree.selection()
        if not selection:
            messagebox.showinfo("提示", "请先选择一个项目")
            return
        
        item = self.history_tree.item(selection[0])
        values = item['values']
        if values and len(values) >= 6:
            path = values[5]
            script_path = os.path.join(path, "scripts.json")
            
            if os.path.exists(script_path):
                try:
                    # 在新窗口中显示脚本内容
                    script_window = tk.Toplevel(self.root)
                    script_window.title(f"脚本内容 - {values[1]}")
                    script_window.geometry("800x600")
                    
                    text_widget = scrolledtext.ScrolledText(script_window, wrap=tk.WORD)
                    text_widget.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
                    
                    with open(script_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        # 格式化JSON
                        parsed = json.loads(content)
                        formatted = json.dumps(parsed, ensure_ascii=False, indent=2)
                        text_widget.insert(1.0, formatted)
                    
                    text_widget.configure(state='disabled')
                    
                except Exception as e:
                    messagebox.showerror("错误", f"无法读取脚本: {str(e)}")
            else:
                messagebox.showerror("错误", "脚本文件不存在")

    def create_log_tab(self):
        """日志标签页"""
        log_frame = ttk.Frame(self.notebook)
        self.notebook.add(log_frame, text="运行日志")
        
        # 日志显示区域
        log_display_frame = ttk.LabelFrame(log_frame, text="运行日志", padding=10)
        log_display_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        self.log_text = scrolledtext.ScrolledText(log_display_frame, height=25)
        self.log_text.pack(fill=tk.BOTH, expand=True)
        
        # 日志操作按钮
        log_btn_frame = ttk.Frame(log_display_frame)
        log_btn_frame.pack(fill=tk.X, pady=(10, 0))
        
        ttk.Button(log_btn_frame, text="清空日志", command=self.clear_log).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(log_btn_frame, text="保存日志", command=self.save_log).pack(side=tk.LEFT)
        
        # 重定向print输出到日志
        self.setup_logging()
        
    def setup_logging(self):
        """设置日志输出重定向"""
        import sys
        from io import StringIO
        
        class LogWriter(StringIO):
            def __init__(self, gui_instance):
                super().__init__()
                self.gui = gui_instance
                
            def write(self, text):
                super().write(text)
                if text.strip():
                    self.gui.update_ui_safely(self.gui.append_log, text)
                    
            def flush(self):
                pass
                
        self.log_writer = LogWriter(self)
        sys.stdout = self.log_writer
        sys.stderr = self.log_writer
        
    def append_log(self, message):
        """添加日志消息"""
        if hasattr(self, 'log_text') and self.log_text:
            self.log_text.insert(tk.END, f"[{datetime.now().strftime('%H:%M:%S')}] {message}")
            self.log_text.see(tk.END)
            self.root.update_idletasks()
        else:
            # 如果没有日志组件，直接打印到控制台
            print(f"[{datetime.now().strftime('%H:%M:%S')}] {message}")
        
    def update_ui_safely(self, func, *args, **kwargs):
        """安全更新UI（在主线程中执行）"""
        try:
            self.root.after(0, lambda: func(*args, **kwargs))
        except Exception as e:
            print(f"UI更新错误: {e}")
            
    def add_task_indicator(self, task_id, task_name):
        """添加任务指示器"""
        # 在状态栏添加任务指示
        if hasattr(self, 'status_frame'):
            indicator = ttk.Label(self.status_frame, text=f"⏳ {task_name}")
            indicator.pack(side=tk.LEFT, padx=5)
            self.task_indicators[task_id] = indicator
            
    def update_task_status(self, task_id, status, error=None):
        """更新任务状态"""
        if task_id in self.task_indicators:
            indicator = self.task_indicators[task_id]
            status_icons = {
                'completed': '✅',
                'error': '❌',
                'cancelled': '⏹️',
                'running': '⏳'
            }
            icon = status_icons.get(status, '❓')
            text = f"{icon} 任务完成" if status == 'completed' else f"{icon} {status}"
            if error:
                text += f" (错误: {error[:30]}...)"
            indicator.configure(text=text)
            
            # 3秒后自动移除已完成的任务指示器
            if status in ['completed', 'error', 'cancelled']:
                self.root.after(3000, lambda: self.remove_task_indicator(task_id))
                
    def remove_task_indicator(self, task_id):
        """移除任务指示器"""
        if task_id in self.task_indicators:
            try:
                self.task_indicators[task_id].destroy()
            except:
                pass
            del self.task_indicators[task_id]
            
    def handle_async_error(self, error_msg):
        """统一异步错误处理"""
        self.append_log(f"❌ 异步操作错误: {error_msg}\n")
        messagebox.showerror("错误", f"操作失败: {error_msg}")
        
    def clear_log(self):
        """清空日志"""
        self.log_text.delete(1.0, tk.END)
        
    def save_log(self):
        """保存日志到文件"""
        filename = filedialog.asksaveasfilename(
            defaultextension=".log",
            filetypes=[("Log files", "*.log"), ("Text files", "*.txt")]
        )
        if filename:
            try:
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(self.log_text.get(1.0, tk.END))
                messagebox.showinfo("成功", f"日志已保存到: {filename}")
            except Exception as e:
                messagebox.showerror("错误", f"保存日志失败: {str(e)}")
                
    # 文件操作方法
    def load_content_file(self):
        """加载内容文件"""
        filename = filedialog.askopenfilename(
            filetypes=[("Markdown files", "*.md"), ("Text files", "*.txt")]
        )
        if filename:
            try:
                with open(filename, 'r', encoding='utf-8') as f:
                    content = f.read()
                    self.content_text.delete(1.0, tk.END)
                    self.content_text.insert(1.0, content)
                    
                    # 从文件名提取标题
                    title = os.path.splitext(os.path.basename(filename))[0]
                    self.title_entry.delete(0, tk.END)
                    self.title_entry.insert(0, title)
                    self.current_title = title
                    
                self.append_log(f"已加载内容文件: {filename}\n")
            except Exception as e:
                messagebox.showerror("错误", f"加载文件失败: {str(e)}")
                
    def save_content_file(self):
        """异步保存内容文件"""
        if not self.current_title:
            messagebox.showwarning("警告", "请先输入视频标题")
            return
            
        filename = f"{self.current_title}.md"
        content = self.content_text.get(1.0, tk.END)
        
        # 使用异步方式保存文件
        self.async_manager.submit_task(
            self._save_content_to_file,
            filename,
            content,
            callback=self._on_content_saved
        )
        self.append_log(f"🔄 开始保存内容到: {filename}\n")
        
    def _save_content_to_file(self, filename, content):
        """在后台线程中保存文件"""
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(content)
        return filename
        
    def _on_content_saved(self, result, error=None):
        """内容保存完成回调"""
        if error:
            self.handle_async_error(f"保存文件失败: {error}")
            return
            
        filename = result
        self.append_log(f"✅ 内容已保存到: {filename}\n")
        messagebox.showinfo("成功", f"内容已保存到: {filename}")
            
    def load_script_file(self):
        """异步加载脚本文件"""
        filename = filedialog.askopenfilename(
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if filename:
            # 使用异步方式加载大文件
            self.async_manager.submit_task(
                self._load_script_content, 
                filename,
                callback=self._on_script_loaded
            )
            
    def _load_script_content(self, filename):
        """在后台线程中加载文件内容"""
        with open(filename, 'r', encoding='utf-8') as f:
            return f.read(), filename
            
    def _on_script_loaded(self, result, error=None):
        """文件加载完成回调"""
        if error:
            self.handle_async_error(f"加载脚本文件失败: {error}")
            return
            
        script_content, filename = result
        self.script_text.delete(1.0, tk.END)
        self.script_text.insert(1.0, script_content)
        
        # 验证并加载JSON数据
        self.validate_and_load_script(script_content)
        self.append_log(f"✅ 已加载脚本文件: {filename}\n")
                
    def save_script_file(self):
        """保存脚本文件"""
        try:
            script_content = self.script_text.get(1.0, tk.END)
            # 验证JSON格式
            json.loads(script_content)
            
            with open("scripts.json", 'w', encoding='utf-8') as f:
                f.write(script_content)
            self.append_log("脚本已保存到: scripts.json\n")
            messagebox.showinfo("成功", "脚本已保存到: scripts.json")
        except json.JSONDecodeError as e:
            messagebox.showerror("错误", f"JSON格式错误: {str(e)}")
        except Exception as e:
            messagebox.showerror("错误", f"保存文件失败: {str(e)}")
            
    def validate_script(self):
        """验证脚本JSON格式"""
        try:
            script_content = self.script_text.get(1.0, tk.END)
            json.loads(script_content)
            messagebox.showinfo("验证结果", "JSON格式正确！")
            self.append_log("脚本JSON格式验证通过\n")
        except json.JSONDecodeError as e:
            messagebox.showerror("验证失败", f"JSON格式错误: {str(e)}")
            
    def validate_and_load_script(self, script_content):
        """验证并加载脚本数据"""
        try:
            script_data = json.loads(script_content)
            self.current_scripts = script_data
            
            # 更新场景列表
            self.update_scene_list()
            
            self.append_log("脚本数据加载成功\n")
        except json.JSONDecodeError as e:
            self.append_log(f"脚本JSON解析失败: {str(e)}\n")
            
    def update_scene_list(self):
        """更新场景列表（按scene_id顺序）"""
        self.scene_listbox.delete(0, tk.END)
        
        if self.current_scripts and 'scenes' in self.current_scripts:
            # 按scene_id排序
            sorted_scenes = sorted(self.current_scripts['scenes'], 
                                 key=lambda x: x.get('scene_id', 0))
            
            for i, scene in enumerate(sorted_scenes):
                scene_id = scene.get('scene_id', i+1)
                note = scene.get('note', '无说明')
                scene_text = f"场景 {scene_id}: {note}"
                self.scene_listbox.insert(tk.END, scene_text)
                
    def on_scene_select(self, event):
        """场景选择事件"""
        selection = self.scene_listbox.curselection()
        if selection:
            list_index = selection[0]
            if self.current_scripts and 'scenes' in self.current_scripts:
                # 按scene_id排序获取实际场景索引
                sorted_scenes = sorted(self.current_scripts['scenes'], 
                                     key=lambda x: x.get('scene_id', 0))
                if list_index < len(sorted_scenes):
                    scene = sorted_scenes[list_index]
                    scene_id = scene.get('scene_id', list_index + 1)
                    
                    # 显示prompt
                    self.prompt_text.delete(1.0, tk.END)
                    self.prompt_text.insert(1.0, scene.get('prompt', ''))
                    
                    # 显示图片（使用实际的scene_id作为索引）
                    self.display_scene_image(scene_id - 1)
                    
    def display_scene_image(self, scene_index):
        """显示场景图片"""
        if self.current_title:
            # 转换标题为英文/拼音目录名
            output_name = self.convert_title_to_filename(self.current_title)
            image_path = os.path.join(self.output_dir, datetime.now().strftime("%Y%m"), output_name, f"scene_{scene_index:03d}.jpg")
            
            if os.path.exists(image_path):
                try:
                    # 加载并显示图片
                    image = Image.open(image_path)
                    # 调整图片大小以适应显示
                    image.thumbnail((400, 300))
                    photo = ImageTk.PhotoImage(image)
                    self.image_label.configure(image=photo, text="")
                    self.image_label.image = photo  # 保持引用
                except Exception as e:
                    self.image_label.configure(text=f"无法加载图片: {str(e)}", image="")
            else:
                self.image_label.configure(text="图片不存在，请先生成图片", image="")
        else:
            self.image_label.configure(text="请先设置视频标题", image="")
            
    def regenerate_image(self):
        """重新生成当前场景图片 - 强制重新生成，忽略已存在状态"""
        selection = self.scene_listbox.curselection()
        if not selection:
            messagebox.showwarning("警告", "请先选择一个场景")
            return
            
        if not self.current_title:
            messagebox.showwarning("警告", "请先设置视频标题")
            return
            
        list_index = selection[0]
        new_prompt = self.prompt_text.get(1.0, tk.END).strip()
        
        if not new_prompt:
            messagebox.showwarning("警告", "请输入Prompt")
            return
            
        # 按scene_id排序获取实际场景
        sorted_scenes = sorted(self.current_scripts['scenes'], 
                             key=lambda x: x.get('scene_id', 0))
        if list_index < len(sorted_scenes):
            scene = sorted_scenes[list_index]
            scene_id = scene.get('scene_id', list_index + 1)
            actual_index = scene_id - 1
            
            # 更新脚本中的prompt
            for i, s in enumerate(self.current_scripts['scenes']):
                if s.get('scene_id', i+1) == scene_id:
                    self.current_scripts['scenes'][i]['prompt'] = new_prompt
                    break
            
            # 保存更新后的脚本
            try:
                with open("scripts.json", 'w', encoding='utf-8') as f:
                    json.dump(self.current_scripts, f, ensure_ascii=False, indent=2)
            except Exception as e:
                self.append_log(f"保存脚本失败: {str(e)}\n")
                return
            
            # 清除该场景的图片生成状态
            output_name = self.convert_title_to_filename(self.current_title)
            self._mark_image_generated(output_name, actual_index, success=False)
            self.append_log(f"🔄 强制重新生成场景 {actual_index+1} 的图片...\n")
                
            # 强制重新生成图片
            self.generate_single_image(actual_index, new_prompt, force_regenerate=True)
            self.display_scene_image(actual_index)
                
    def upload_image(self):
        """异步上传本地图片"""
        selection = self.scene_listbox.curselection()
        if not selection:
            messagebox.showwarning("警告", "请先选择一个场景")
            return
            
        filename = filedialog.askopenfilename(
            filetypes=[("Image files", "*.jpg *.jpeg *.png *.bmp")]
        )
        if filename:
            # 使用异步方式处理图片上传
            self.async_manager.submit_task(
                self._process_uploaded_image,
                filename,
                selection[0],
                callback=self._on_image_upload_complete
            )
            self.append_log(f"🔄 开始处理上传的图片: {os.path.basename(filename)}\n")
            
    def _process_uploaded_image(self, filename, list_index):
        """在后台线程中处理上传的图片"""
        try:
            # 转换标题为英文/拼音目录名
            output_name = self.convert_title_to_filename(self.current_title)
            output_path = os.path.join(self.output_dir, datetime.now().strftime("%Y%m"), output_name)
            os.makedirs(output_path, exist_ok=True)
            
            # 获取实际的场景ID
            sorted_scenes = sorted(self.current_scripts['scenes'], 
                                 key=lambda x: x.get('scene_id', 0))
            if list_index < len(sorted_scenes):
                scene = sorted_scenes[list_index]
                scene_id = scene.get('scene_id', list_index + 1)
                actual_index = scene_id - 1
                
                # 目标文件路径
                target_path = os.path.join(output_path, f"scene_{actual_index:03d}.jpg")
                
                # 复制并调整图片尺寸
                with Image.open(filename) as img:
                    # 调整为竖屏视频尺寸 (1080x1920)
                    img = img.resize((1080, 1920), Image.Resampling.LANCZOS)
                    img.save(target_path, 'JPEG', quality=95)
                    
                return actual_index, target_path
            else:
                raise Exception("无效的场景索引")
                
        except Exception as e:
            raise Exception(f"图片处理失败: {str(e)}")
            
    def _on_image_upload_complete(self, result, error=None):
        """图片上传完成回调 - 无弹窗提示，仅记录日志"""
        if error:
            self.handle_async_error(f"图片上传失败: {error}")
            return
            
        actual_index, target_path = result
        self.append_log(f"✅ 图片导入完成: {target_path}\n")
        self.display_scene_image(actual_index)
        # 不显示弹窗，实现无缝导入体验
                
    def batch_generate_images(self, force_regenerate=False):
        """异步批量生成所有图片
        
        Args:
            force_regenerate: 是否强制重新生成（忽略已生成状态）
        """
        if not self.current_scripts or 'scenes' not in self.current_scripts:
            messagebox.showwarning("警告", "请先加载有效的脚本文件")
            return
            
        if not self.current_title:
            messagebox.showwarning("警告", "请先设置视频标题")
            return
        
        # 获取项目名称
        output_name = self.convert_title_to_filename(self.current_title)
        scenes = self.current_scripts['scenes']
        
        # 检查哪些场景需要生成图片
        scenes_to_generate = []
        skipped_count = 0
        
        for i, scene in enumerate(scenes):
            if not force_regenerate and self._is_image_generated(output_name, i):
                skipped_count += 1
                self.append_log(f"⏭️ 场景 {i+1}: 图片已存在，跳过生成\n")
            else:
                scenes_to_generate.append((i, scene))
        
        if skipped_count > 0:
            self.append_log(f"跳过 {skipped_count} 个已生成的场景\n")
        
        if not scenes_to_generate:
            self.append_log("✅ 所有场景图片都已生成，无需重复生成\n")
            messagebox.showinfo("提示", "所有图片已生成，如需重新生成请使用'重新生成图片'按钮")
            return
            
        self.append_log(f"开始异步批量生成 {len(scenes_to_generate)} 个场景的图片...\n")
        
        # 禁用生成按钮
        self.generate_btn.configure(state='disabled')
        self.progress_label.configure(text="正在异步生成图片...")
        
        # 提交异步任务
        task_id = self.async_manager.submit_task(
            self._batch_generate_worker,
            scenes_to_generate,
            output_name,
            callback=self._on_batch_generation_complete
        )
        
        self.append_log(f"任务已提交，ID: {task_id}\n")
        
    async def _batch_generate_worker(self, scenes_to_generate, project_name):
        """优化的异步批量生成工作者 - 带频率控制和状态跟踪
        
        Args:
            scenes_to_generate: 需要生成的场景列表 [(index, scene), ...]
            project_name: 项目名称（用于状态跟踪）
        """
        results = []
        total = len(scenes_to_generate)
        
        # 使用指数退避策略
        base_delay = 2.0  # 基础延迟2秒
        max_delay = 10.0  # 最大延迟10秒
        consecutive_failures = 0
        
        for batch_i, (scene_index, scene) in enumerate(scenes_to_generate):
            # 更新进度
            progress = (batch_i + 1) / total * 100
            self.update_ui_safely(self._update_generation_progress, batch_i+1, total, progress)
            
            # 计算当前延迟时间
            current_delay = min(base_delay * (2 ** consecutive_failures), max_delay)
            if consecutive_failures > 0:
                self.update_ui_safely(self.append_log, f"⚠️ 检测到连续失败，增加延迟到 {current_delay:.1f} 秒\n")
            
            # 异步生成单个图片
            try:
                result = await self.async_manager.async_task_wrapper(
                    self.generate_single_image,
                    scene_index, 
                    scene.get('prompt', ''),
                    scene_id=scene.get('scene_id'),
                    scene_note=scene.get('note', '')
                )
                results.append((scene_index, result, True))
                # 标记为已生成
                self._mark_image_generated(project_name, scene_index, success=True)
                consecutive_failures = 0  # 重置失败计数
                self.update_ui_safely(self.append_log, f"✅ 场景 {scene_index+1} 生成成功\n")
                
            except Exception as e:
                results.append((scene_index, str(e), False))
                # 标记为生成失败
                self._mark_image_generated(project_name, scene_index, success=False)
                consecutive_failures += 1
                self.update_ui_safely(self.append_log, f"❌ 场景 {scene_index+1} 生成失败: {str(e)}\n")
                
            # 场景间延迟 - 避免API频率限制
            if batch_i < total - 1:  # 最后一个场景不需要延迟
                await asyncio.sleep(current_delay)
                
        return results
        
    def _update_generation_progress(self, current, total, percentage):
        """更新生成进度"""
        self.progress_var.set(percentage)
        self.progress_label.configure(text=f"生成进度: {current}/{total} ({percentage:.1f}%)")
        self.status_label.configure(text=f"正在生成场景 {current}/{total}")
        
    def _on_batch_generation_complete(self, results, error=None):
        """批量生成完成回调"""
        # 重新启用生成按钮
        self.generate_btn.configure(state='normal')
        self.progress_var.set(0)
        self.status_label.configure(text="就绪")
        
        if error:
            self.handle_async_error(f"批量生成失败: {error}")
            return
            
        # 统计结果
        success_count = sum(1 for _, _, success in results if success)
        total_count = len(results)
        
        self.append_log(f"✅ 批量生成完成: {success_count}/{total_count} 成功\n")
        self.progress_label.configure(text=f"生成完成: {success_count}/{total_count}")
        
        if success_count == total_count:
            messagebox.showinfo("完成", f"所有 {total_count} 个图片生成成功！")
        else:
            messagebox.showwarning("完成", f"生成完成: {success_count}/{total_count} 成功")
        
    def generate_single_image(self, index, prompt, force_regenerate=False, scene_id=None, scene_note=None):
        """异步生成单个图片 - 调用真实的AI图片生成API
        
        Args:
            index: 场景索引
            prompt: 图片生成提示词
            force_regenerate: 是否强制重新生成
            scene_id: 场景ID（用于增强多样性）
            scene_note: 场景说明（用于增强多样性）
            
        Returns:
            str: 生成的图片路径
        """
        try:
            # 转换标题为英文/拼音目录名
            output_name = self.convert_title_to_filename(self.current_title)
            output_path = os.path.join(self.output_dir, datetime.now().strftime("%Y%m"), output_name)
            os.makedirs(output_path, exist_ok=True)
            
            image_path = os.path.join(output_path, f"scene_{index:03d}.jpg")
            
            # 检查是否已生成（除非强制重新生成）
            if not force_regenerate and self._is_image_generated(output_name, index):
                self.append_log(f"⏭️ 场景 {index+1}: 图片已存在，跳过生成\n")
                return image_path
            
            # 调用实际的图片生成方法
            self.append_log(f"🔄 调用AI图片生成: 场景 {index+1} - {prompt[:50]}...\n")
            
            # 使用auto_video_maker中的图片生成器
            from auto_video_maker import ImageGenerator
            image_generator = ImageGenerator()
            
            # 在线程中执行图片生成（因为requests不是异步的）
            # 传递场景ID和说明以增强多样性
            success = image_generator.generate(
                prompt, 
                image_path, 
                scene_id=scene_id or (index + 1),
                scene_note=scene_note
            )
            
            # 更新生成状态
            self._mark_image_generated(output_name, index, success=success)
            
            if success:
                self.append_log(f"✅ 场景 {index+1} 图片生成成功: {image_path}\n")
                return image_path
            else:
                # 生成失败时创建占位图
                self.append_log(f"⚠️ 场景 {index+1} AI生成失败，创建占位图\n")
                self._create_placeholder_image(image_path, index)
                return image_path
            
        except Exception as e:
            self.append_log(f"❌ 场景 {index+1} 图片生成异常: {str(e)}\n")
            # 异常时也创建占位图保证流程继续
            output_name = self.convert_title_to_filename(self.current_title)
            output_path = os.path.join(self.output_dir, datetime.now().strftime("%Y%m"), output_name)
            image_path = os.path.join(output_path, f"scene_{index:03d}.jpg")
            self._create_placeholder_image(image_path, index)
            # 标记为失败
            self._mark_image_generated(output_name, index, success=False)
            return image_path
            
    def _create_placeholder_image(self, image_path, index):
        """创建占位图片"""
        try:
            # 创建带有文字提示的占位图
            placeholder = Image.new('RGB', (1080, 1920), color=(
                50 + (index * 15) % 100,
                50 + (index * 25) % 100, 
                50 + (index * 35) % 100
            ))
            placeholder.save(image_path, 'JPEG', quality=95)
        except Exception as e:
            self.append_log(f"占位图创建失败: {str(e)}\n")
            
    def start_generation(self):
        """异步开始视频生成"""
        if not self.current_title:
            messagebox.showwarning("警告", "请先设置视频标题")
            return
            
        if not self.current_scripts:
            messagebox.showwarning("警告", "请先加载脚本文件")
            return
            
        # 禁用生成按钮
        self.generate_btn.configure(state='disabled')
        self.progress_label.configure(text="准备异步生成...")
        
        # 提交异步视频生成任务
        task_id = self.async_manager.submit_task(
            self._video_generation_worker,
            callback=self._on_video_generation_complete
        )
        
        self.append_log(f"🚀 视频生成任务已提交，ID: {task_id}\n")
        
    async def _video_generation_worker(self):
        """异步视频生成工作者"""
        try:
            self.update_ui_safely(self.append_log, "🎬 开始异步视频生成流程...\n")
            
            # 设置输出目录
            output_name = self.convert_title_to_filename(self.current_title)
            month_dir = datetime.now().strftime("%Y%m")
            full_output_dir = os.path.join(self.output_dir, month_dir, output_name)
            os.makedirs(full_output_dir, exist_ok=True)
            
            # 保存脚本文件
            script_path = os.path.join(full_output_dir, "scripts.json")
            with open(script_path, 'w', encoding='utf-8') as f:
                json.dump(self.current_scripts, f, ensure_ascii=False, indent=2)
                
            self.update_ui_safely(self.append_log, f"📄 脚本文件保存到: {script_path}\n")
            
            # 分步骤异步执行
            steps = [
                ("生成音频", self._generate_audio_async, 30),
                ("处理图片", self._process_images_async, 40),
                ("合成视频", self._compose_video_async, 30)
            ]
            
            total_progress = 0
            for step_name, step_func, step_weight in steps:
                self.update_ui_safely(self.progress_label.configure, text=f"正在{step_name}...")
                self.update_ui_safely(self.append_log, f"🔄 正在{step_name}...\n")
                
                try:
                    # 执行步骤
                    await step_func(full_output_dir)
                    total_progress += step_weight
                    self.update_ui_safely(self.progress_var.set, total_progress)
                    self.update_ui_safely(self.append_log, f"✅ {step_name}完成\n")
                    
                except Exception as e:
                    raise Exception(f"{step_name}失败: {str(e)}")
                
                # 步骤间短暂延迟
                await asyncio.sleep(0.5)
            
            # 生成完成
            video_path = os.path.join(full_output_dir, f"{output_name}.mp4")
            return {
                'success': True,
                'output_dir': full_output_dir,
                'video_path': video_path,
                'steps_completed': len(steps)
            }
            
        except Exception as e:
            raise Exception(f"视频生成流程失败: {str(e)}")
            
    async def _generate_audio_async(self, output_dir):
        """异步生成音频 - 调用真实的TTS功能"""
        if self.generate_audio_var.get():
            try:
                # 获取场景文本
                scenes = self.current_scripts.get('scenes', [])
                if not scenes:
                    raise Exception("没有场景数据")
                
                # 合并所有文本
                full_text = ""
                for scene in scenes:
                    text = scene.get('text', '')
                    if text:
                        # 简单的自然停顿处理
                        if text.endswith(('。', '！', '？')):
                            full_text += text + " "
                        elif text.endswith('，'):
                            full_text += text + " "
                        else:
                            full_text += text + " "
                
                if not full_text.strip():
                    raise Exception("没有有效文本内容")
                
                # 调用真实的TTS生成
                voiceover_path = os.path.join(output_dir, "voiceover.mp3")
                
                self.update_ui_safely(self.append_log, "🎤 开始音频生成...\n")
                
                # 使用auto_video_maker中的音频生成功能
                from auto_video_maker import AudioGenerator, VOICE_CONFIG
                audio_gen = AudioGenerator(VOICE_CONFIG)
                
                # 直接使用edge-tts生成完整音频
                success = await self._generate_audio_with_edge_tts(full_text.strip(), voiceover_path, VOICE_CONFIG)
                
                if success and os.path.exists(voiceover_path):
                    self.update_ui_safely(self.append_log, f"✅ 音频生成成功: {voiceover_path}\n")
                    return voiceover_path
                else:
                    raise Exception("音频生成失败")
                    
            except Exception as e:
                self.update_ui_safely(self.append_log, f"❌ 音频生成异常: {str(e)}\n")
                raise Exception(f"音频生成失败: {str(e)}")
        
        return None
        
    async def _generate_audio_with_edge_tts(self, text, output_file, voice_config):
        """使用edge-tts生成音频 - 添加超时处理"""
        try:
            import edge_tts
            import asyncio
            
            # 配置TTS参数
            voice = voice_config.get('primary', 'zh-CN-XiaoxiaoNeural')
            rate = voice_config.get('rate', '+0%')
            volume = voice_config.get('volume', '+0%')
            
            # 创建通信对象
            communicate = edge_tts.Communicate(
                text=text,
                voice=voice,
                rate=rate,
                volume=volume
            )
            
            # 使用超时保护避免长时间等待
            try:
                # 为长文本设置较长的超时时间（每1000字符约30秒）
                estimated_duration = len(text) // 1000 * 30 + 60  # 最少60秒
                timeout_seconds = min(estimated_duration, 300)  # 最多5分钟
                
                await asyncio.wait_for(communicate.save(output_file), timeout=timeout_seconds)
                self.update_ui_safely(self.append_log, f"✅ 音频生成完成，耗时已考虑文本长度\n")
                return True
            except asyncio.TimeoutError:
                self.update_ui_safely(self.append_log, f"⚠️ 音频生成超时 ({timeout_seconds}秒)，尝试分段生成\n")
                # 如果超时，尝试使用auto_video_maker的分段生成方法
                return await self._generate_audio_fallback_segmented(text, output_file, voice_config)
            
        except Exception as e:
            self.update_ui_safely(self.append_log, f"edge-tts生成失败: {str(e)}\n")
            # 尝试备用方法
            return await self._generate_audio_fallback_segmented(text, output_file, voice_config)
    
    async def _generate_audio_fallback_segmented(self, text, output_file, voice_config):
        """备用音频生成方法 - 使用auto_video_maker中的分段生成逻辑"""
        try:
            self.update_ui_safely(self.append_log, "🔄 使用备用方法生成音频...\n")
            
            # 使用auto_video_maker中的音频生成器
            from auto_video_maker import AudioGenerator, VOICE_CONFIG
            audio_gen = AudioGenerator(VOICE_CONFIG)
            
            # 如果文本太长，我们将其分割成多个部分
            if len(text) > 2000:  # 如果文本超过2000字符，尝试分割
                self.update_ui_safely(self.append_log, "📝 文本较长，尝试分段处理...\n")
                # 简单地按句子分割
                import re
                sentences = re.split(r'[。！？.!?]', text)
                segments = []
                current_segment = ""
                
                for sentence in sentences:
                    if len(current_segment + sentence) < 1000:  # 每段最多1000字符
                        current_segment += sentence + "。"
                    else:
                        if current_segment:
                            segments.append(current_segment)
                        current_segment = sentence + "。"
                
                if current_segment:
                    segments.append(current_segment)
                
                # 临时文件存储各段音频
                temp_files = []
                for i, segment in enumerate(segments):
                    if segment.strip():
                        temp_file = output_file.replace('.mp3', f'_temp_{i}.mp3')
                        success = await self._generate_single_segment(segment, temp_file, voice_config)
                        if success and os.path.exists(temp_file):
                            temp_files.append(temp_file)
                
                if temp_files:
                    # 使用pydub合并音频文件
                    from pydub import AudioSegment
                    combined = AudioSegment.empty()
                    
                    for temp_file in temp_files:
                        try:
                            segment_audio = AudioSegment.from_mp3(temp_file)
                            combined += segment_audio
                        except Exception as e:
                            self.update_ui_safely(self.append_log, f"⚠️ 合并音频段失败: {str(e)}\n")
                    
                    combined.export(output_file, format="mp3")
                    
                    # 清理临时文件
                    for temp_file in temp_files:
                        try:
                            os.remove(temp_file)
                        except:
                            pass
                    
                    return True
                else:
                    self.update_ui_safely(self.append_log, "⚠️ 分段生成也失败了\n")
                    return False
            else:
                # 使用edge_tts的同步接口
                import edge_tts
                import subprocess
                import asyncio
                import concurrent.futures
                
                # 配置TTS参数
                voice = voice_config.get('primary', 'zh-CN-XiaoxiaoNeural')
                
                def run_tts_sync():
                    # 创建一个新的事件循环
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    try:
                        async def run_tts():
                            communicate = edge_tts.Communicate(text, voice)
                            await communicate.save(output_file)
                            return os.path.exists(output_file) and os.path.getsize(output_file) > 1000
                        
                        return loop.run_until_complete(run_tts())
                    finally:
                        loop.close()
                
                # 在线程池中运行
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(run_tts_sync)
                    success = future.result(timeout=120)  # 2分钟超时
                    return success
                
        except Exception as e:
            self.update_ui_safely(self.append_log, f"备用音频生成也失败: {str(e)}\n")
            return False
    
    async def _generate_single_segment(self, text, output_file, voice_config):
        """生成单个音频段"""
        try:
            import edge_tts
            import asyncio
            
            voice = voice_config.get('primary', 'zh-CN-XiaoxiaoNeural')
            rate = voice_config.get('rate', '+0%')
            volume = voice_config.get('volume', '+0%')
            
            communicate = edge_tts.Communicate(
                text=text,
                voice=voice,
                rate=rate,
                volume=volume
            )
            
            await communicate.save(output_file)
            return True
        except Exception as e:
            self.update_ui_safely(self.append_log, f"分段音频生成失败: {str(e)}\n")
            return False
        
    async def _process_images_async(self, output_dir):
        """异步处理图片"""
        # 检查并处理场景图片
        scenes = self.current_scripts.get('scenes', [])
        for i, scene in enumerate(scenes):
            image_path = os.path.join(output_dir, f"scene_{i:03d}.jpg")
            if not os.path.exists(image_path):
                # 异步生成缺失的图片
                await self.async_manager.async_task_wrapper(
                    self.generate_single_image, i, scene.get('prompt', '')
                )
            await asyncio.sleep(0.1)  # 避免过于频繁
        return True
        
    async def _compose_video_async(self, output_dir):
        """异步合成视频 - 调用真实的视频合成逻辑"""
        if self.generate_video_var.get():
            try:
                # 获取场景数据
                scenes = self.current_scripts.get('scenes', [])
                if not scenes:
                    raise Exception("没有场景数据")
                
                # 收集图片文件
                image_files = []
                scene_durations = []
                
                for i, scene in enumerate(scenes):
                    image_path = os.path.join(output_dir, f"scene_{i:03d}.jpg")
                    if os.path.exists(image_path):
                        image_files.append(image_path)
                        # 使用场景预设时长或默认5秒
                        duration = scene.get('duration_sec', 5)
                        scene_durations.append(duration)
                    else:
                        self.update_ui_safely(self.append_log, f"⚠️ 缺少场景图片: {image_path}\n")
                        # 创建占位图
                        self._create_placeholder_image(image_path, i)
                        image_files.append(image_path)
                        scene_durations.append(5)  # 默认5秒
                
                if not image_files:
                    raise Exception("没有有效的图片文件")
                
                # 查找音频文件
                audio_candidates = [
                    os.path.join(output_dir, "voiceover.mp3"),
                    os.path.join(output_dir, "complete_voiceover.mp3"),
                    os.path.join(output_dir, "segment_000.mp3")
                ]
                
                audio_file = None
                for candidate in audio_candidates:
                    if os.path.exists(candidate):
                        audio_file = candidate
                        break
                
                if not audio_file:
                    # 如果没有音频文件，创建静音音频
                    self.update_ui_safely(self.append_log, "⚠️ 未找到音频文件，创建静音轨道\n")
                    audio_file = os.path.join(output_dir, "silent_audio.mp3")
                    self._create_silent_audio(audio_file, sum(scene_durations))
                
                # 调用真实的视频合成器
                from auto_video_maker import VideoCompositor
                video_comp = VideoCompositor(output_dir)
                
                output_name = self.convert_title_to_filename(self.current_title)
                video_path = os.path.join(output_dir, f"{output_name}.mp4")
                
                self.update_ui_safely(self.append_log, "🎬 开始视频合成...\n")
                
                # 执行视频合成
                success = video_comp.create(audio_file, image_files, scene_durations, video_path)
                
                if success and os.path.exists(video_path):
                    self.update_ui_safely(self.append_log, f"✅ 视频合成成功: {video_path}\n")
                    return video_path
                else:
                    raise Exception("视频合成失败")
                    
            except Exception as e:
                self.update_ui_safely(self.append_log, f"❌ 视频合成异常: {str(e)}\n")
                raise Exception(f"视频合成失败: {str(e)}")
        
        return None
        
    def _create_silent_audio(self, audio_path, duration):
        """创建静音音频文件 - 使用MoviePy创建"""
        try:
            # 使用MoviePy创建静音音频
            from moviepy.audio.AudioClip import AudioClip
            import numpy as np
            
            def make_frame(t):
                return np.zeros((1, 2))  # 立体声静音
            
            # 创建音频剪辑
            audio_clip = AudioClip(make_frame, duration=duration, fps=44100)
            
            # 导出为MP3
            audio_clip.write_audiofile(audio_path, fps=44100, nbytes=2, 
                                     codec='mp3', logger=None)
            audio_clip.close()
            
            self.append_log(f"✅ 静音音频创建成功: {audio_path}\n")
            
        except Exception as e:
            self.append_log(f"❌ 静音音频创建失败: {str(e)}\n")
            # 备用方案：创建简单的WAV文件
            try:
                import wave
                import numpy as np
                
                sample_rate = 44100
                samples = int(duration * sample_rate)
                audio_data = np.zeros(samples, dtype=np.int16)
                
                with wave.open(audio_path.replace('.mp3', '.wav'), 'w') as wav_file:
                    wav_file.setnchannels(1)  # 单声道
                    wav_file.setsampwidth(2)  # 16位
                    wav_file.setframerate(sample_rate)
                    wav_file.writeframes(audio_data.tobytes())
                
                self.append_log(f"⚠️ MP3创建失败，已创建WAV文件作为替代\n")
            except Exception as e2:
                self.append_log(f"❌ WAV音频创建也失败: {str(e2)}\n")
        
    def _on_video_generation_complete(self, result, error=None):
        """视频生成完成回调"""
        # 重新启用生成按钮
        self.generate_btn.configure(state='normal')
        self.progress_var.set(0)
        self.progress_label.configure(text="准备就绪")
        self.status_label.configure(text="就绪")
        
        if error:
            self.handle_async_error(f"视频生成失败: {error}")
            return
            
        # 显示成功信息
        self.append_log(f"🎉 视频生成成功完成！\n")
        self.append_log(f"📁 输出目录: {result['output_dir']}\n")
        self.append_log(f"🎬 视频文件: {result['video_path']}\n")
        
        # 刷新历史记录列表
        self.refresh_history_list()
        
        # 切换到生成记录标签页
        try:
            # 查找"生成记录"标签页的索引
            for idx in range(self.notebook.index('end')):
                if self.notebook.tab(idx, 'text') == '生成记录':
                    self.notebook.select(idx)
                    break
        except Exception:
            pass
        
        messagebox.showinfo(
            "生成完成", 
            f"视频生成成功！\n\n输出目录: {result['output_dir']}\n视频文件: {os.path.basename(result['video_path'])}"
        )
        
    def browse_output_dir(self):
        """浏览输出目录"""
        directory = filedialog.askdirectory()
        if directory:
            self.output_entry.delete(0, tk.END)
            self.output_entry.insert(0, directory)
            self.output_dir = directory
            
    def on_title_change(self, event):
        """标题变化事件"""
        self.current_title = self.title_entry.get().strip()
        
    def convert_title_to_filename(self, title):
        """将标题转换为拼音文件名"""
        try:
            # 使用pypinyin库进行中文转拼音
            import pypinyin
            # 获取完整拼音
            pinyin_list = pypinyin.lazy_pinyin(title, style=pypinyin.Style.NORMAL)
            # 连接拼音，用下划线分隔
            pinyin_title = '_'.join(pinyin_list)
            # 清理特殊字符，只保留字母、数字和下划线
            clean_title = re.sub(r'[^a-zA-Z0-9_]', '', pinyin_title)
            # 清理多余的下划线
            clean_title = re.sub(r'_+', '_', clean_title)
            # 去除开头和结尾的下划线
            clean_title = clean_title.strip('_')
            return clean_title if clean_title else "untitled_video"
        except ImportError:
            # 如果没有pypinyin库，使用简单的处理方式
            self.append_log("警告: 未安装pypinyin库，使用基础处理\n")
            # 移除中文字符和其他特殊字符
            english_chars = re.sub(r'[^a-zA-Z0-9\s]', '', title)
            # 用下划线连接单词
            clean_title = re.sub(r'\s+', '_', english_chars.strip())
            clean_title = clean_title.strip('_')
            return clean_title if clean_title else "untitled_video"
        except Exception as e:
            self.append_log(f"标题转换错误: {str(e)}，使用默认名称\n")
            return "untitled_video"
    
    def _get_image_status_file_path(self):
        """获取图片生成状态文件的保存路径"""
        return os.path.join(self.output_dir, ".image_generation_status.json")
    
    def _load_image_generation_status(self):
        """从文件加载图片生成状态"""
        status_file = self._get_image_status_file_path()
        try:
            if os.path.exists(status_file):
                with open(status_file, 'r', encoding='utf-8') as f:
                    # 将字符串键转换回元组
                    status_dict = json.load(f)
                    self.image_generation_status = {}
                    for key, value in status_dict.items():
                        # 键格式为 "project_name|scene_index"
                        parts = key.split('|')
                        if len(parts) == 2:
                            project_name = parts[0]
                            scene_index = int(parts[1])
                            self.image_generation_status[(project_name, scene_index)] = value
                self.append_log(f"已加载图片生成状态: {len(self.image_generation_status)} 条记录\n")
        except Exception as e:
            self.append_log(f"加载图片生成状态失败: {str(e)}\n")
            self.image_generation_status = {}
    
    def _save_image_generation_status(self):
        """保存图片生成状态到文件"""
        status_file = self._get_image_status_file_path()
        try:
            # 将元组键转换为字符串
            status_dict = {}
            for (project_name, scene_index), value in self.image_generation_status.items():
                key = f"{project_name}|{scene_index}"
                status_dict[key] = value
            
            os.makedirs(os.path.dirname(status_file), exist_ok=True)
            with open(status_file, 'w', encoding='utf-8') as f:
                json.dump(status_dict, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.append_log(f"保存图片生成状态失败: {str(e)}\n")
    
    def _is_image_generated(self, project_name, scene_index):
        """检查指定场景的图片是否已生成
        
        Args:
            project_name: 项目名称
            scene_index: 场景索引
            
        Returns:
            bool: 如果图片已生成且文件存在返回True
        """
        # 首先检查状态记录
        status_key = (project_name, scene_index)
        if status_key not in self.image_generation_status:
            return False
        
        if not self.image_generation_status[status_key]:
            return False
        
        # 再检查文件是否实际存在
        try:
            output_name = self.convert_title_to_filename(project_name)
            output_path = os.path.join(self.output_dir, datetime.now().strftime("%Y%m"), output_name)
            image_path = os.path.join(output_path, f"scene_{scene_index:03d}.jpg")
            
            if os.path.exists(image_path) and os.path.getsize(image_path) > 1000:
                return True
            else:
                # 文件不存在或太小，清除状态
                self.image_generation_status[status_key] = False
                return False
        except Exception:
            return False
    
    def _mark_image_generated(self, project_name, scene_index, success=True):
        """标记图片生成状态
        
        Args:
            project_name: 项目名称
            scene_index: 场景索引
            success: 是否生成成功
        """
        status_key = (project_name, scene_index)
        self.image_generation_status[status_key] = success
        self._save_image_generation_status()
    
    def _clear_project_image_status(self, project_name):
        """清除指定项目的所有图片生成状态（用于重新生成）"""
        keys_to_remove = [k for k in self.image_generation_status.keys() if k[0] == project_name]
        for key in keys_to_remove:
            del self.image_generation_status[key]
        self._save_image_generation_status()
        self.append_log(f"已清除项目 '{project_name}' 的图片生成状态\n")
        
def main():
    root = tk.Tk()
    app = VideoCreatorGUI(root)
    root.mainloop()
    
if __name__ == "__main__":
    main()