#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
GUI异步优化效果验证脚本
测试多线程和异步处理的改进效果
"""

import time
import threading
import asyncio
from concurrent.futures import ThreadPoolExecutor
import tkinter as tk
from tkinter import ttk, messagebox

class PerformanceTestGUI:
    """性能测试GUI - 对比传统方式和异步方式"""
    
    def __init__(self, root):
        self.root = root
        self.root.title("GUI异步优化性能测试")
        self.root.geometry("800x600")
        
        # 线程池
        self.executor = ThreadPoolExecutor(max_workers=4)
        
        self.create_widgets()
        
    def create_widgets(self):
        """创建测试界面"""
        main_frame = ttk.Frame(self.root, padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 标题
        title_label = ttk.Label(main_frame, text="GUI异步优化性能对比测试", 
                               font=('Arial', 16, 'bold'))
        title_label.pack(pady=(0, 20))
        
        # 测试按钮区域
        button_frame = ttk.LabelFrame(main_frame, text="性能测试", padding=15)
        button_frame.pack(fill=tk.X, pady=(0, 20))
        
        # 传统阻塞式测试
        traditional_frame = ttk.Frame(button_frame)
        traditional_frame.pack(fill=tk.X, pady=5)
        
        ttk.Button(traditional_frame, text="传统阻塞式执行", 
                  command=self.test_traditional_approach,
                  style="Warning.TButton").pack(side=tk.LEFT, padx=(0, 10))
        
        ttk.Label(traditional_frame, text="模拟耗时操作会冻结界面").pack(side=tk.LEFT)
        
        # 异步非阻塞式测试
        async_frame = ttk.Frame(button_frame)
        async_frame.pack(fill=tk.X, pady=5)
        
        ttk.Button(async_frame, text="异步非阻塞执行", 
                  command=self.test_async_approach,
                  style="Success.TButton").pack(side=tk.LEFT, padx=(0, 10))
        
        ttk.Label(async_frame, text="界面保持响应，后台处理任务").pack(side=tk.LEFT)
        
        # 并发测试
        concurrent_frame = ttk.Frame(button_frame)
        concurrent_frame.pack(fill=tk.X, pady=5)
        
        ttk.Button(concurrent_frame, text="并发多任务执行", 
                  command=self.test_concurrent_approach).pack(side=tk.LEFT, padx=(0, 10))
        
        ttk.Label(concurrent_frame, text="同时处理多个任务").pack(side=tk.LEFT)
        
        # 结果显示区域
        results_frame = ttk.LabelFrame(main_frame, text="测试结果", padding=15)
        results_frame.pack(fill=tk.BOTH, expand=True)
        
        # 文本显示区域
        self.results_text = tk.Text(results_frame, height=15, wrap=tk.WORD)
        scrollbar = ttk.Scrollbar(results_frame, orient=tk.VERTICAL, command=self.results_text.yview)
        self.results_text.configure(yscrollcommand=scrollbar.set)
        
        self.results_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 控制按钮
        control_frame = ttk.Frame(main_frame)
        control_frame.pack(fill=tk.X, pady=(15, 0))
        
        ttk.Button(control_frame, text="清空结果", command=self.clear_results).pack(side=tk.LEFT)
        ttk.Button(control_frame, text="关闭测试", command=self.root.destroy).pack(side=tk.RIGHT)
        
    def log_result(self, message):
        """记录测试结果"""
        timestamp = time.strftime("%H:%M:%S")
        self.results_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.results_text.see(tk.END)
        self.root.update_idletasks()
        
    def clear_results(self):
        """清空结果"""
        self.results_text.delete(1.0, tk.END)
        
    def simulate_heavy_work(self, task_name, duration=3):
        """模拟耗时工作"""
        time.sleep(duration)
        return f"{task_name} 完成 (耗时 {duration}秒)"
        
    def test_traditional_approach(self):
        """测试传统阻塞式方法"""
        self.log_result("🚀 开始传统阻塞式测试...")
        
        start_time = time.time()
        
        # 模拟多个耗时任务（会阻塞UI）
        tasks = [
            ("任务1", 2),
            ("任务2", 1),
            ("任务3", 3)
        ]
        
        for task_name, duration in tasks:
            self.log_result(f"⏳ 执行 {task_name} (将阻塞界面 {duration}秒)...")
            result = self.simulate_heavy_work(task_name, duration)
            self.log_result(f"✅ {result}")
            
        total_time = time.time() - start_time
        self.log_result(f"🏁 传统方式总耗时: {total_time:.2f}秒")
        self.log_result("⚠️  注意: 界面在此期间完全无响应!\n")
        
    def test_async_approach(self):
        """测试异步非阻塞方法"""
        self.log_result("🚀 开始异步非阻塞测试...")
        
        start_time = time.time()
        
        def worker():
            # 在后台线程中执行耗时任务
            tasks = [
                ("异步任务1", 2),
                ("异步任务2", 1),
                ("异步任务3", 3)
            ]
            
            for task_name, duration in tasks:
                self.root.after(0, lambda tn=task_name: self.log_result(f"⏳ 执行 {tn}..."))
                result = self.simulate_heavy_work(task_name, duration)
                self.root.after(0, lambda res=result: self.log_result(f"✅ {res}"))
                
            total_time = time.time() - start_time
            self.root.after(0, lambda: self.log_result(f"🏁 异步方式总耗时: {total_time:.2f}秒"))
            self.root.after(0, lambda: self.log_result("✅ 界面始终保持响应!\n"))
            
        # 启动后台线程
        thread = threading.Thread(target=worker, daemon=True)
        thread.start()
        
        # 主线程立即返回，界面不会被阻塞
        self.log_result("💡 异步任务已提交，界面保持响应...")
        
    def test_concurrent_approach(self):
        """测试并发多任务方法"""
        self.log_result("🚀 开始并发多任务测试...")
        
        start_time = time.time()
        completed_tasks = []
        
        def task_worker(task_id, duration):
            """任务工作者"""
            result = self.simulate_heavy_work(f"并发任务{task_id}", duration)
            self.root.after(0, lambda: self.log_result(f"✅ {result}"))
            completed_tasks.append(task_id)
            
            # 检查是否所有任务完成
            if len(completed_tasks) == 5:
                total_time = time.time() - start_time
                self.root.after(0, lambda: self.log_result(f"🏁 并发方式总耗时: {total_time:.2f}秒"))
                self.root.after(0, lambda: self.log_result("✅ 5个任务并发执行完成!\n"))
        
        # 同时启动5个不同耗时的任务
        durations = [1, 2, 1.5, 2.5, 1]
        
        self.log_result("💡 同时启动5个并发任务...")
        for i, duration in enumerate(durations, 1):
            self.log_result(f"🔄 启动并发任务{i} (预计耗时 {duration}秒)")
            thread = threading.Thread(target=task_worker, args=(i, duration), daemon=True)
            thread.start()
            
        self.log_result("💡 所有任务已在后台并发执行...")

def demonstrate_benefits():
    """演示异步优化的好处"""
    
    benefits = {
        "用户体验": {
            "传统方式": "界面冻结，用户无法进行其他操作",
            "异步方式": "界面流畅，可继续交互操作"
        },
        "任务处理": {
            "传统方式": "串行执行，总耗时长",
            "异步方式": "并发处理，并行效率高"
        },
        "错误处理": {
            "传统方式": "错误导致整个流程中断",
            "异步方式": "单个任务失败不影响其他任务"
        },
        "资源利用": {
            "传统方式": "CPU和I/O资源利用率低",
            "异步方式": "充分利用系统资源，提高吞吐量"
        }
    }
    
    print("🌟 GUI异步优化核心优势:")
    print("=" * 60)
    
    for category, comparison in benefits.items():
        print(f"\n{category}:")
        print(f"  传统方式: {comparison['传统方式']}")
        print(f"  异步方式: {comparison['异步方式']}")

def main():
    """主函数"""
    print("🔧 GUI异步优化测试工具")
    print("=" * 40)
    
    demonstrate_benefits()
    
    print(f"\n🎯 启动性能测试界面...")
    print("请在界面中分别测试三种方式的差异")
    
    root = tk.Tk()
    
    # 设置样式
    style = ttk.Style()
    style.configure("Warning.TButton", foreground="red")
    style.configure("Success.TButton", foreground="green")
    
    app = PerformanceTestGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()