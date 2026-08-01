import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import json
import os
import re
import asyncio
import threading
from datetime import datetime
import subprocess
import sys

class SimpleVideoCreatorGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Video Creator GUI - Saabor AI Builds")
        self.root.geometry("1000x700")
        
        # 当前数据
        self.current_title = ""
        self.current_scripts = {}
        self.output_base_dir = "./output"
        
        self.create_widgets()
        
    def create_widgets(self):
        # 主框架
        main_frame = ttk.Frame(self.root, padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 标题区域
        title_frame = ttk.LabelFrame(main_frame, text="项目设置", padding=10)
        title_frame.pack(fill=tk.X, pady=(0, 20))
        
        ttk.Label(title_frame, text="视频标题:").grid(row=0, column=0, sticky=tk.W, padx=(0, 10))
        self.title_entry = ttk.Entry(title_frame, width=50)
        self.title_entry.grid(row=0, column=1, sticky=tk.EW, padx=(0, 10))
        self.title_entry.bind('<KeyRelease>', self.on_title_change)
        
        ttk.Button(title_frame, text="加载Markdown", command=self.load_markdown).grid(row=0, column=2)
        title_frame.columnconfigure(1, weight=1)
        
        # 内容编辑区域
        content_frame = ttk.LabelFrame(main_frame, text="视频内容 (Markdown)", padding=10)
        content_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 20))
        
        self.content_text = scrolledtext.ScrolledText(content_frame, height=8)
        self.content_text.pack(fill=tk.BOTH, expand=True)
        
        # 脚本区域
        script_frame = ttk.LabelFrame(main_frame, text="视频脚本 (JSON)", padding=10)
        script_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 20))
        
        self.script_text = scrolledtext.ScrolledText(script_frame, height=12)
        self.script_text.pack(fill=tk.BOTH, expand=True)
        
        script_btn_frame = ttk.Frame(script_frame)
        script_btn_frame.pack(fill=tk.X, pady=(10, 0))
        
        ttk.Button(script_btn_frame, text="加载脚本", command=self.load_script).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(script_btn_frame, text="保存脚本", command=self.save_script).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(script_btn_frame, text="验证JSON", command=self.validate_json).pack(side=tk.LEFT)
        
        # 控制按钮区域
        control_frame = ttk.Frame(main_frame)
        control_frame.pack(fill=tk.X)
        
        ttk.Button(control_frame, text="生成图片", command=self.generate_images, style="Accent.TButton").pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(control_frame, text="生成视频", command=self.generate_video, style="Accent.TButton").pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(control_frame, text="查看输出", command=self.open_output_folder).pack(side=tk.LEFT)
        
        # 进度和状态
        status_frame = ttk.Frame(main_frame)
        status_frame.pack(fill=tk.X, pady=(10, 0))
        
        self.status_label = ttk.Label(status_frame, text="就绪")
        self.status_label.pack(side=tk.LEFT)
        
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(status_frame, variable=self.progress_var, maximum=100)
        self.progress_bar.pack(side=tk.RIGHT, padx=(10, 0), fill=tk.X, expand=True)
        
        # 日志区域
        log_frame = ttk.LabelFrame(main_frame, text="运行日志", padding=10)
        log_frame.pack(fill=tk.BOTH, expand=True, pady=(20, 0))
        
        self.log_text = scrolledtext.ScrolledText(log_frame, height=8)
        self.log_text.pack(fill=tk.BOTH, expand=True)
        
        log_btn_frame = ttk.Frame(log_frame)
        log_btn_frame.pack(fill=tk.X, pady=(10, 0))
        
        ttk.Button(log_btn_frame, text="清空日志", command=self.clear_log).pack(side=tk.LEFT)
        ttk.Button(log_btn_frame, text="保存日志", command=self.save_log).pack(side=tk.LEFT, padx=(10, 0))
        
    def log_message(self, message):
        """记录日志消息"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.log_text.see(tk.END)
        self.root.update_idletasks()
        
    def clear_log(self):
        """清空日志"""
        self.log_text.delete(1.0, tk.END)
        
    def save_log(self):
        """保存日志"""
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
                
    def load_markdown(self):
        """加载Markdown文件"""
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
                    
                self.log_message(f"已加载: {filename}")
            except Exception as e:
                messagebox.showerror("错误", f"加载文件失败: {str(e)}")
                
    def load_script(self):
        """加载脚本文件"""
        filename = filedialog.askopenfilename(
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if filename:
            try:
                with open(filename, 'r', encoding='utf-8') as f:
                    content = f.read()
                    self.script_text.delete(1.0, tk.END)
                    self.script_text.insert(1.0, content)
                    
                    # 验证并加载JSON
                    self.validate_and_load_script(content)
                    
                self.log_message(f"已加载脚本: {filename}")
            except Exception as e:
                messagebox.showerror("错误", f"加载脚本失败: {str(e)}")
                
    def save_script(self):
        """保存脚本文件"""
        try:
            content = self.script_text.get(1.0, tk.END)
            json.loads(content)  # 验证JSON格式
            
            with open("scripts.json", 'w', encoding='utf-8') as f:
                f.write(content)
                
            self.log_message("脚本已保存到 scripts.json")
            messagebox.showinfo("成功", "脚本已保存到 scripts.json")
        except json.JSONDecodeError as e:
            messagebox.showerror("错误", f"JSON格式错误: {str(e)}")
        except Exception as e:
            messagebox.showerror("错误", f"保存失败: {str(e)}")
            
    def validate_json(self):
        """验证JSON格式"""
        try:
            content = self.script_text.get(1.0, tk.END)
            json.loads(content)
            messagebox.showinfo("验证结果", "JSON格式正确！")
            self.log_message("JSON格式验证通过")
        except json.JSONDecodeError as e:
            messagebox.showerror("验证失败", f"JSON格式错误: {str(e)}")
            
    def validate_and_load_script(self, content):
        """验证并加载脚本"""
        try:
            script_data = json.loads(content)
            self.current_scripts = script_data
            self.log_message("脚本数据加载成功")
        except json.JSONDecodeError as e:
            self.log_message(f"脚本JSON解析失败: {str(e)}")
            
    def on_title_change(self, event):
        """标题变化处理"""
        self.current_title = self.title_entry.get().strip()
        
    def generate_images(self):
        """生成图片"""
        if not self.current_title:
            messagebox.showwarning("警告", "请先设置视频标题")
            return
            
        if not self.current_scripts:
            messagebox.showwarning("警告", "请先加载脚本文件")
            return
            
        def run_image_generation():
            try:
                self.status_label.configure(text="正在生成图片...")
                self.log_message("开始图片生成流程")
                
                # 保存脚本文件
                with open("scripts.json", 'w', encoding='utf-8') as f:
                    json.dump(self.current_scripts, f, ensure_ascii=False, indent=2)
                    
                # 调用图片生成脚本
                cmd = [sys.executable, "auto_video_maker.py"]
                process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    universal_newlines=True,
                    bufsize=1
                )
                
                # 实时读取输出
                while True:
                    output = process.stdout.readline()
                    if output == '' and process.poll() is not None:
                        break
                    if output:
                        self.log_message(output.strip())
                        self.root.update_idletasks()
                        
                # 移动生成的图片到正确目录
                self.organize_output_files()
                
                self.status_label.configure(text="图片生成完成")
                self.log_message("图片生成流程完成")
                messagebox.showinfo("完成", "图片生成完成！")
                
            except Exception as e:
                self.log_message(f"图片生成失败: {str(e)}")
                messagebox.showerror("错误", f"图片生成失败: {str(e)}")
            finally:
                self.status_label.configure(text="就绪")
                
        # 在后台线程中运行
        thread = threading.Thread(target=run_image_generation)
        thread.daemon = True
        thread.start()
        
    def generate_video(self):
        """生成完整视频"""
        if not self.current_title:
            messagebox.showwarning("警告", "请先设置视频标题")
            return
            
        def run_video_generation():
            try:
                self.status_label.configure(text="正在生成视频...")
                self.log_message("开始视频生成流程")
                
                # 调用完整的视频生成脚本
                cmd = [sys.executable, "auto_video_maker.py"]
                process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    universal_newlines=True,
                    bufsize=1
                )
                
                # 实时读取输出
                while True:
                    output = process.stdout.readline()
                    if output == '' and process.poll() is not None:
                        break
                    if output:
                        self.log_message(output.strip())
                        self.root.update_idletasks()
                        
                # 组织输出文件
                self.organize_output_files()
                
                self.status_label.configure(text="视频生成完成")
                self.log_message("视频生成流程完成")
                messagebox.showinfo("完成", "视频生成完成！")
                
            except Exception as e:
                self.log_message(f"视频生成失败: {str(e)}")
                messagebox.showerror("错误", f"视频生成失败: {str(e)}")
            finally:
                self.status_label.configure(text="就绪")
                
        # 在后台线程中运行
        thread = threading.Thread(target=run_video_generation)
        thread.daemon = True
        thread.start()
        
    def organize_output_files(self):
        """组织输出文件到正确目录结构"""
        try:
            if not self.current_title:
                return
                
            # 转换标题为目录名
            dir_name = self.convert_title_to_dirname(self.current_title)
            month_dir = datetime.now().strftime("%Y%m")
            target_dir = os.path.join(self.output_base_dir, month_dir, dir_name)
            os.makedirs(target_dir, exist_ok=True)
            
            # 移动文件
            output_files = [
                "voiceover.mp3",
                "scripts.json",
                *[f"scene_{i}.jpg" for i in range(20)]  # 假设最多20个场景
            ]
            
            for filename in output_files:
                src_path = os.path.join(self.output_base_dir, filename)
                if os.path.exists(src_path):
                    dst_path = os.path.join(target_dir, filename)
                    # 如果目标文件存在，先删除
                    if os.path.exists(dst_path):
                        os.remove(dst_path)
                    os.rename(src_path, dst_path)
                    
            # 移动视频文件
            video_files = [f for f in os.listdir(self.output_base_dir) if f.endswith('.mp4')]
            for video_file in video_files:
                src_path = os.path.join(self.output_base_dir, video_file)
                dst_path = os.path.join(target_dir, video_file)
                if os.path.exists(src_path):
                    if os.path.exists(dst_path):
                        os.remove(dst_path)
                    os.rename(src_path, dst_path)
                    
            self.log_message(f"文件已整理到: {target_dir}")
            
        except Exception as e:
            self.log_message(f"文件整理失败: {str(e)}")
            
    def open_output_folder(self):
        """打开输出文件夹"""
        try:
            if self.current_title:
                dir_name = self.convert_title_to_dirname(self.current_title)
                month_dir = datetime.now().strftime("%Y%m")
                target_dir = os.path.join(self.output_base_dir, month_dir, dir_name)
                
                if os.path.exists(target_dir):
                    os.startfile(target_dir)  # Windows
                else:
                    os.startfile(self.output_base_dir)
            else:
                os.startfile(self.output_base_dir)
        except Exception as e:
            self.log_message(f"打开文件夹失败: {str(e)}")
            
    def convert_title_to_dirname(self, title):
        """将标题转换为拼音目录名"""
        try:
            # 尝试使用pypinyin库进行中文转拼音
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
            # 如果没有pypinyin库，使用简单的英文处理
            self.log_message("警告: 未安装pypinyin库，使用简单英文处理")
            # 移除中文字符，保留英文字母和数字
            english_only = re.sub(r'[^a-zA-Z0-9\s]', '', title)
            # 用下划线连接单词
            clean_title = re.sub(r'\s+', '_', english_only.strip())
            clean_title = clean_title.strip('_')
            return clean_title if clean_title else "untitled_video"
        except Exception as e:
            self.log_message(f"转换标题时出错: {str(e)}, 使用默认名称")
            return "untitled_video"

def main():
    # 设置主题样式
    root = tk.Tk()
    
    # 尝试设置现代化主题
    try:
        style = ttk.Style()
        if 'winxpblue' in style.theme_names():
            style.theme_use('winxpblue')
    except:
        pass
        
    app = SimpleVideoCreatorGUI(root)
    root.mainloop()
    
if __name__ == "__main__":
    main()