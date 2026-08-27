#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
多进程工作节点 - 实现真正的并行视频渲染
解决 GIL 限制，充分利用多核 CPU
"""

import os
import sys
import time
import signal
import multiprocessing as mp
from multiprocessing import Process, Queue, Manager
from typing import Dict, Any, Optional, Callable
from dataclasses import dataclass
from enum import Enum
import traceback

from ..utils.logger import logger
from .task_queue_sqlite import SQLiteTaskQueue


class WorkerStatus(Enum):
    """工作节点状态"""
    IDLE = "idle"
    BUSY = "busy"
    STOPPED = "stopped"
    ERROR = "error"


@dataclass
class WorkerResult:
    """工作结果"""
    task_id: str
    success: bool
    error_message: Optional[str] = None
    output_dir: Optional[str] = None
    duration: float = 0.0


def worker_process(worker_id: str, db_path: str, result_queue: Queue,
                   stop_flag: mp.Event):
    """
    独立工作进程函数
    
    Args:
        worker_id: 工作节点 ID
        db_path: SQLite 数据库路径
        result_queue: 结果队列
        stop_flag: 停止标志
    """
    logger.info(f"Worker {worker_id} 启动")
    
    # 初始化任务队列
    task_queue = SQLiteTaskQueue(db_path=db_path)
    
    # 导入工作流（在子进程中导入）
    from ..workflow import OptimizedWorkflow, WorkflowConfig
    
    while not stop_flag.is_set():
        try:
            # 获取任务
            task_data = task_queue.get_next_task(worker_id)
            
            if not task_data:
                # 无任务，等待
                time.sleep(1.0)
                continue
            
            task_id = task_data['id']
            script_path = task_data['script_path']
            title = task_data['title']
            
            logger.info(f"Worker {worker_id} 开始处理任务：{task_id} - {title}")
            
            start_time = time.time()
            success = False
            error_message = None
            output_dir = None
            
            try:
                # 创建工作流实例
                workflow_config = WorkflowConfig(
                    output_dir="./output",
                    stop_on_error=False,
                    create_placeholder=True,
                )
                workflow = OptimizedWorkflow(config=workflow_config)
                
                # 执行生成
                result = workflow.quick_generate(
                    script_path=script_path,
                    title=title,
                    progress_callback=lambda c, t, m: logger.debug(
                        f"Worker {worker_id} 进度：{c}/{t} - {m}"
                    )
                )
                
                # 检查结果
                if result.get("success"):
                    success = True
                    output_dir = result.get("output_dir")
                    logger.success(f"Worker {worker_id} 完成任务：{task_id}")
                else:
                    errors = result.get("errors", ["未知错误"])
                    error_message = "; ".join(errors)
                    logger.error(f"Worker {worker_id} 任务失败：{task_id} - {error_message}")
                    
            except Exception as e:
                error_message = str(e)
                logger.error(f"Worker {worker_id} 异常：{task_id} - {error_message}")
                logger.debug(traceback.format_exc())
            
            # 计算耗时
            duration = time.time() - start_time
            
            # 更新任务状态
            if success:
                task_queue.complete_task(
                    task_id=task_id,
                    success=True,
                    result={"duration": duration},
                    output_dir=output_dir
                )
            else:
                # 尝试重试
                retry_success = task_queue.retry_task(task_id, error_message)
                if not retry_success:
                    task_queue.complete_task(
                        task_id=task_id,
                        success=False,
                        error_message=error_message
                    )
            
            # 发送结果到队列
            result = WorkerResult(
                task_id=task_id,
                success=success,
                error_message=error_message,
                output_dir=output_dir,
                duration=duration
            )
            result_queue.put(result)
            
        except Exception as e:
            logger.error(f"Worker {worker_id} 循环异常：{e}")
            logger.debug(traceback.format_exc())
            time.sleep(2.0)
    
    # 清理
    task_queue.close()
    logger.info(f"Worker {worker_id} 已停止")


class MultiProcessWorkerPool:
    """多进程工作节点池"""
    
    def __init__(self, num_workers: int = 3, db_path: str = "video_tasks.db"):
        """
        初始化工作节点池
        
        Args:
            num_workers: 工作节点数量
            db_path: SQLite 数据库路径
        """
        self.num_workers = num_workers
        self.db_path = db_path
        self.workers: list[Process] = []
        self.result_queue: Queue = Queue()
        self.stop_flag = mp.Event()
        self.manager = Manager()
        self.running = False
        
        # 确保输出目录存在
        os.makedirs("./output", exist_ok=True)
        
        logger.info(f"初始化多进程工作节点池：{num_workers} 个节点")
    
    def start(self):
        """启动所有工作节点"""
        if self.running:
            logger.warning("工作节点池已在运行中")
            return
        
        self.running = True
        self.stop_flag.clear()
        
        logger.info(f"启动 {self.num_workers} 个工作节点...")
        
        for i in range(self.num_workers):
            worker_id = f"worker-{i}"
            
            p = Process(
                target=worker_process,
                args=(worker_id, self.db_path, self.result_queue, self.stop_flag),
                name=f"VideoWorker-{i}",
                daemon=True
            )
            p.start()
            self.workers.append(p)
            
            logger.info(f"工作节点 {worker_id} 已启动 (PID: {p.pid})")
        
        logger.success("所有工作节点已启动")
    
    def stop(self, timeout: float = 30.0):
        """停止所有工作节点"""
        logger.info("正在停止工作节点池...")
        self.stop_flag.set()
        self.running = False
        
        # 等待所有进程结束
        for i, p in enumerate(self.workers):
            logger.debug(f"等待工作节点 {i} 结束...")
            p.join(timeout=timeout / len(self.workers))
            
            if p.is_alive():
                logger.warning(f"工作节点 {i} 未正常退出，强制终止")
                p.terminate()
                p.join(timeout=5.0)
        
        self.workers.clear()
        logger.success("工作节点池已停止")
    
    def get_results(self, timeout: float = 1.0) -> list[WorkerResult]:
        """获取已完成的结果"""
        results = []
        
        while True:
            try:
                result = self.result_queue.get(timeout=timeout)
                results.append(result)
                timeout = 0.1  # 后续读取不等待
            except:
                break
        
        return results
    
    def get_status(self) -> Dict[str, Any]:
        """获取工作节点状态"""
        active_count = sum(1 for p in self.workers if p.is_alive())
        
        return {
            "total_workers": self.num_workers,
            "active_workers": active_count,
            "running": self.running,
            "queue_size": self.result_queue.qsize() if not self.result_queue.empty() else 0,
        }
    
    def restart_failed_workers(self):
        """重启失败的工人节点"""
        for i, p in enumerate(self.workers):
            if not p.is_alive():
                worker_id = f"worker-{i}"
                logger.warning(f"工作节点 {worker_id} 已死亡，正在重启...")
                
                p = Process(
                    target=worker_process,
                    args=(worker_id, self.db_path, self.result_queue, self.stop_flag),
                    name=f"VideoWorker-{i}",
                    daemon=True
                )
                p.start()
                self.workers[i] = p
                
                logger.info(f"工作节点 {worker_id} 已重启 (PID: {p.pid})")


def create_worker_pool(num_workers: int = 3, 
                       db_path: str = "video_tasks.db") -> MultiProcessWorkerPool:
    """工厂函数创建工作者池"""
    return MultiProcessWorkerPool(num_workers=num_workers, db_path=db_path)


if __name__ == "__main__":
    # 测试代码
    logging.basicConfig(level=logging.INFO)
    
    pool = create_worker_pool(num_workers=2)
    pool.start()
    
    try:
        while True:
            time.sleep(5)
            results = pool.get_results(timeout=0.1)
            for r in results:
                print(f"完成：{r.task_id}, 成功={r.success}, 耗时={r.duration:.2f}s")
            
            status = pool.get_status()
            print(f"状态：{status}")
            
    except KeyboardInterrupt:
        print("\n正在停止...")
        pool.stop()
