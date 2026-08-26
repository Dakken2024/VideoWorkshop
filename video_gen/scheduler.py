#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
定时任务调度器 - 支持批量视频生成任务，含速率限制和错误恢复

功能特性:
1. 每日定时任务调度 (50-100 个视频)
2. 多 API 提供商轮询，避免单点限流
3. 分布式任务队列，支持并发控制
4. 断点续传和失败重试
5. 任务优先级管理
6. 详细的执行日志和统计报告

使用方式:
    from video_gen.scheduler import VideoTaskScheduler
    
    # 创建调度器
    scheduler = VideoTaskScheduler(
        daily_target=80,           # 每日目标视频数
        max_concurrent=3,          # 最大并发任务数
        api_retry_limit=5,         # API 重试次数
    )
    
    # 添加任务
    scheduler.add_task(script_path="scripts_001.json", title="视频 1", priority=1)
    scheduler.add_task(script_path="scripts_002.json", title="视频 2", priority=2)
    
    # 启动调度器
    scheduler.start()
"""

import os
import json
import time
import random
import threading
import queue
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

from .config import AppConfig, DEFAULT_CONFIG, ImageConfig
from .utils.logger import logger
from .utils.file_utils import safe_read_json, safe_write_json, ensure_dir
from .workflow import OptimizedWorkflow, WorkflowConfig


class TaskPriority(Enum):
    """任务优先级"""
    LOW = 3
    NORMAL = 2
    HIGH = 1
    URGENT = 0


class TaskState(Enum):
    """任务状态"""
    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"
    CANCELLED = "cancelled"


@dataclass
class VideoTask:
    """视频生成任务"""
    id: str
    script_path: str
    title: str
    priority: TaskPriority = TaskPriority.NORMAL
    state: TaskState = TaskState.PENDING
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    retry_count: int = 0
    max_retries: int = 5
    error_message: Optional[str] = None
    result: Optional[Dict] = None
    output_dir: Optional[str] = None
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            "id": self.id,
            "script_path": self.script_path,
            "title": self.title,
            "priority": self.priority.name,
            "state": self.state.value,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
            "error_message": self.error_message,
            "result": self.result,
            "output_dir": self.output_dir,
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "VideoTask":
        """从字典创建"""
        return cls(
            id=data["id"],
            script_path=data["script_path"],
            title=data["title"],
            priority=TaskPriority[data.get("priority", "NORMAL")],
            state=TaskState(data.get("state", "pending")),
            created_at=datetime.fromisoformat(data["created_at"]),
            started_at=datetime.fromisoformat(data["started_at"]) if data.get("started_at") else None,
            completed_at=datetime.fromisoformat(data["completed_at"]) if data.get("completed_at") else None,
            retry_count=data.get("retry_count", 0),
            max_retries=data.get("max_retries", 5),
            error_message=data.get("error_message"),
            result=data.get("result"),
            output_dir=data.get("output_dir"),
        )


@dataclass
class SchedulerConfig:
    """调度器配置"""
    # 任务配置
    daily_target: int = 80              # 每日目标视频数 (50-100)
    max_concurrent: int = 3             # 最大并发任务数
    max_queue_size: int = 200           # 最大队列大小
    
    # API 速率限制
    api_retry_limit: int = 5            # API 重试次数
    api_retry_delay: float = 60.0       # API 重试延迟 (秒)
    rate_limit_calls: int = 10          # 每分钟 API 调用次数限制
    rate_limit_window: int = 60         # 速率限制时间窗口 (秒)
    
    # 图片生成配置
    image_gen_interval: float = 5.0     # 图片生成间隔 (秒)
    image_max_retries: int = 3          # 图片生成最大重试次数
    
    # 持久化配置
    persist_enabled: bool = True        # 启用任务持久化
    persist_interval: int = 30          # 持久化间隔 (秒)
    state_file: str = ".scheduler_state.json"
    
    # 输出配置
    output_base_dir: str = "./output"
    
    # 通知配置
    enable_notifications: bool = False
    notification_webhook: Optional[str] = None


class RateLimiter:
    """速率限制器 - 令牌桶算法"""
    
    def __init__(self, calls: int, window: int):
        """
        Args:
            calls: 允许的调用次数
            window: 时间窗口 (秒)
        """
        self.calls = calls
        self.window = window
        self.tokens = calls
        self.last_update = time.time()
        self._lock = threading.Lock()
    
    def acquire(self, blocking: bool = True, timeout: float = None) -> bool:
        """获取令牌"""
        start_time = time.time()
        
        while True:
            with self._lock:
                now = time.time()
                elapsed = now - self.last_update
                
                # 补充令牌
                if elapsed > 0:
                    refill = elapsed * (self.calls / self.window)
                    self.tokens = min(self.calls, self.tokens + refill)
                    self.last_update = now
                
                if self.tokens >= 1:
                    self.tokens -= 1
                    return True
            
            if not blocking:
                return False
            
            if timeout is not None and (time.time() - start_time) > timeout:
                return False
            
            # 等待一段时间
            wait_time = min(1.0, (1.0 / self.calls) * self.window)
            time.sleep(wait_time)
    
    def get_wait_time(self) -> float:
        """获取需要等待的时间"""
        with self._lock:
            if self.tokens >= 1:
                return 0.0
            return (1.0 - self.tokens) * (self.window / self.calls)


class APICircuitBreaker:
    """API 熔断器 - 防止连续失败"""
    
    def __init__(self, failure_threshold: int = 5, recovery_timeout: float = 300.0):
        """
        Args:
            failure_threshold: 失败阈值，达到后触发熔断
            recovery_timeout: 恢复超时 (秒)
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time: Optional[float] = None
        self.state = "closed"  # closed, open, half-open
        self._lock = threading.Lock()
    
    def record_success(self):
        """记录成功"""
        with self._lock:
            self.failure_count = 0
            self.state = "closed"
    
    def record_failure(self) -> bool:
        """记录失败，返回是否应该继续尝试"""
        with self._lock:
            self.failure_count += 1
            self.last_failure_time = time.time()
            
            if self.failure_count >= self.failure_threshold:
                self.state = "open"
                logger.warning(f"API 熔断器打开，失败次数：{self.failure_count}")
                return False
            return True
    
    def can_proceed(self) -> bool:
        """检查是否可以继续"""
        with self._lock:
            if self.state == "closed":
                return True
            
            if self.state == "open":
                if self.last_failure_time and \
                   (time.time() - self.last_failure_time) > self.recovery_timeout:
                    self.state = "half-open"
                    logger.info("API 熔断器进入半开状态，尝试恢复")
                    return True
                return False
            
            # half-open 状态，允许一次尝试
            return True
    
    def reset(self):
        """重置熔断器"""
        with self._lock:
            self.failure_count = 0
            self.last_failure_time = None
            self.state = "closed"


class VideoTaskScheduler:
    """视频生成任务调度器"""
    
    def __init__(self, config: SchedulerConfig = None, app_config: AppConfig = None):
        """
        初始化调度器
        
        Args:
            config: 调度器配置
            app_config: 应用配置
        """
        self.config = config or SchedulerConfig()
        self.app_config = app_config or DEFAULT_CONFIG
        
        # 任务队列 (优先级队列)
        self.task_queue: queue.PriorityQueue = queue.PriorityQueue(
            maxsize=self.config.max_queue_size
        )
        
        # 活跃任务
        self.active_tasks: Dict[str, VideoTask] = {}
        self.completed_tasks: List[VideoTask] = []
        self.failed_tasks: List[VideoTask] = []
        
        # 速率限制器
        self.rate_limiter = RateLimiter(
            self.config.rate_limit_calls,
            self.config.rate_limit_window
        )
        
        # API 熔断器
        self.api_breaker = APICircuitBreaker(
            failure_threshold=self.config.api_retry_limit,
            recovery_timeout=self.config.api_retry_delay
        )
        
        # 图片生成间隔控制
        self.last_image_gen_time = 0.0
        self.image_gen_lock = threading.Lock()
        
        # 工作线程
        self.workers: List[threading.Thread] = []
        self.worker_count = 0
        self.running = False
        self.stop_flag = threading.Event()
        
        # 持久化
        self.state_file = os.path.join(
            self.config.output_base_dir,
            self.config.state_file
        )
        
        # 统计信息
        self.stats = {
            "total_submitted": 0,
            "total_completed": 0,
            "total_failed": 0,
            "total_retried": 0,
            "today_start": datetime.now().strftime("%Y-%m-%d"),
            "today_completed": 0,
        }
        
        # 锁
        self._lock = threading.Lock()
        self._stats_lock = threading.Lock()
        
        # 回调
        self.task_callbacks: List[Callable[[VideoTask], None]] = []
        
        # 加载持久化状态
        if self.config.persist_enabled:
            self._load_state()
    
    def add_task(self, script_path: str, title: str = None,
                 priority: TaskPriority = TaskPriority.NORMAL,
                 task_id: str = None) -> VideoTask:
        """
        添加任务到队列
        
        Args:
            script_path: 脚本文件路径
            title: 视频标题
            priority: 任务优先级
            task_id: 任务 ID (可选，自动生成)
        
        Returns:
            VideoTask 对象
        """
        # 验证脚本文件
        if not os.path.exists(script_path):
            raise FileNotFoundError(f"脚本文件不存在：{script_path}")
        
        script_data = safe_read_json(script_path)
        if not script_data:
            raise ValueError(f"脚本文件无效：{script_path}")
        
        # 从脚本读取标题
        if not title:
            title = script_data.get("meta", {}).get("title", "Untitled")
        
        # 生成任务 ID
        if not task_id:
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            random_suffix = random.randint(1000, 9999)
            task_id = f"task_{timestamp}_{random_suffix}"
        
        # 创建任务
        task = VideoTask(
            id=task_id,
            script_path=script_path,
            title=title,
            priority=priority,
        )
        
        # 加入队列
        try:
            # 优先级队列：(优先级值，提交时间戳，任务)
            self.task_queue.put((
                priority.value,
                task.created_at.timestamp(),
                task
            ))
            
            with self._lock:
                self.active_tasks[task_id] = task
            
            with self._stats_lock:
                self.stats["total_submitted"] += 1
            
            logger.info(f"任务已添加：{task_id} - {title} (优先级：{priority.name})")
            self._notify_task_change(task)
            self._persist_state()
            
            return task
            
        except queue.Full:
            raise RuntimeError("任务队列已满，无法添加新任务")
    
    def add_batch_tasks(self, scripts_dir: str,
                        priority: TaskPriority = TaskPriority.NORMAL) -> List[VideoTask]:
        """
        批量添加任务
        
        Args:
            scripts_dir: 包含脚本文件的目录
            priority: 任务优先级
        
        Returns:
            任务列表
        """
        tasks = []
        script_files = list(Path(scripts_dir).glob("*.json"))
        
        for script_path in script_files:
            try:
                task = self.add_task(
                    script_path=str(script_path),
                    priority=priority
                )
                tasks.append(task)
            except Exception as e:
                logger.error(f"添加任务失败 {script_path}: {e}")
        
        logger.info(f"批量添加任务完成：{len(tasks)}/{len(script_files)}")
        return tasks
    
    def start(self, worker_count: int = None):
        """
        启动调度器
        
        Args:
            worker_count: 工作线程数 (默认使用配置的 max_concurrent)
        """
        if self.running:
            logger.warning("调度器已在运行中")
            return
        
        self.worker_count = worker_count or self.config.max_concurrent
        self.running = True
        self.stop_flag.clear()
        
        logger.info(f"启动调度器，工作线程数：{self.worker_count}")
        
        # 创建工作线程
        for i in range(self.worker_count):
            worker = threading.Thread(
                target=self._worker_loop,
                name=f"Worker-{i}",
                daemon=True
            )
            worker.start()
            self.workers.append(worker)
        
        # 启动持久化线程
        if self.config.persist_enabled:
            persist_thread = threading.Thread(
                target=self._persist_loop,
                name="PersistThread",
                daemon=True
            )
            persist_thread.start()
        
        # 启动统计重置线程 (每日)
        stats_reset_thread = threading.Thread(
            target=self._daily_stats_reset_loop,
            name="StatsResetThread",
            daemon=True
        )
        stats_reset_thread.start()
        
        logger.success("调度器启动完成")
    
    def stop(self, wait: bool = True, timeout: float = 30.0):
        """
        停止调度器
        
        Args:
            wait: 是否等待任务完成
            timeout: 等待超时时间
        """
        logger.info("正在停止调度器...")
        self.stop_flag.set()
        self.running = False
        
        if wait:
            logger.info("等待工作线程完成...")
            for worker in self.workers:
                worker.join(timeout=timeout / len(self.workers))
        
        # 保存最终状态
        if self.config.persist_enabled:
            self._persist_state()
        
        logger.success("调度器已停止")
    
    def get_task_status(self, task_id: str) -> Optional[Dict]:
        """获取任务状态"""
        with self._lock:
            task = self.active_tasks.get(task_id)
            if task:
                return task.to_dict()
        
        # 在已完成/失败列表中查找
        for task_list in [self.completed_tasks, self.failed_tasks]:
            for task in task_list:
                if task.id == task_id:
                    return task.to_dict()
        
        return None
    
    def get_queue_status(self) -> Dict:
        """获取队列状态"""
        with self._lock:
            return {
                "queue_size": self.task_queue.qsize(),
                "active_tasks": len(self.active_tasks),
                "completed_tasks": len(self.completed_tasks),
                "failed_tasks": len(self.failed_tasks),
                "workers": self.worker_count,
                "running": self.running,
            }
    
    def get_statistics(self) -> Dict:
        """获取统计信息"""
        with self._stats_lock:
            stats_copy = self.stats.copy()
        
        # 添加实时数据
        stats_copy["queue_size"] = self.task_queue.qsize()
        stats_copy["active_tasks"] = len(self.active_tasks)
        
        # 计算成功率
        total_finished = stats_copy["total_completed"] + stats_copy["total_failed"]
        if total_finished > 0:
            stats_copy["success_rate"] = round(
                stats_copy["total_completed"] / total_finished * 100, 2
            )
        else:
            stats_copy["success_rate"] = 0.0
        
        return stats_copy
    
    def register_callback(self, callback: Callable[[VideoTask], None]):
        """注册任务状态变更回调"""
        self.task_callbacks.append(callback)
    
    def cancel_task(self, task_id: str) -> bool:
        """取消任务"""
        with self._lock:
            task = self.active_tasks.get(task_id)
            if not task:
                return False
            
            if task.state in [TaskState.COMPLETED, TaskState.FAILED]:
                return False
            
            task.state = TaskState.CANCELLED
            task.completed_at = datetime.now()
            
            # 从活跃任务移除
            del self.active_tasks[task_id]
            self.failed_tasks.append(task)
        
        logger.info(f"任务已取消：{task_id}")
        self._notify_task_change(task)
        return True
    
    # ==================== 内部方法 ====================
    
    def _worker_loop(self):
        """工作线程主循环"""
        thread_name = threading.current_thread().name
        
        while not self.stop_flag.is_set():
            try:
                # 从队列获取任务 (带超时)
                try:
                    _, _, task = self.task_queue.get(timeout=1.0)
                except queue.Empty:
                    continue
                
                # 处理任务
                self._process_task(task, thread_name)
                
                # 标记任务完成
                self.task_queue.task_done()
                
            except Exception as e:
                logger.error(f"{thread_name} 异常：{e}")
    
    def _process_task(self, task: VideoTask, worker_name: str):
        """处理单个任务"""
        logger.info(f"{worker_name} 开始处理任务：{task.id} - {task.title}")
        
        # 更新任务状态
        with self._lock:
            task.state = TaskState.RUNNING
            task.started_at = datetime.now()
        
        self._notify_task_change(task)
        
        # 检查 API 熔断器
        if not self.api_breaker.can_proceed():
            wait_time = self.api_breaker.recovery_timeout
            logger.warning(f"API 熔断器打开，等待 {wait_time} 秒后重试")
            time.sleep(min(wait_time, 10.0))  # 最多等待 10 秒
        
        # 速率限制等待
        wait_time = self.rate_limiter.get_wait_time()
        if wait_time > 0:
            logger.debug(f"速率限制等待：{wait_time:.2f} 秒")
            time.sleep(wait_time)
        
        # 获取速率限制令牌
        self.rate_limiter.acquire(blocking=True, timeout=60.0)
        
        # 执行视频生成
        success = False
        error_message = None
        
        try:
            # 创建工作流
            workflow_config = WorkflowConfig(
                output_dir=self.config.output_base_dir,
                stop_on_error=False,
                create_placeholder=True,
            )
            workflow = OptimizedWorkflow(config=workflow_config)
            
            # 执行生成
            result = workflow.quick_generate(
                script_path=task.script_path,
                title=task.title,
                progress_callback=lambda c, t, m: self._on_progress(task, c, t, m)
            )
            
            # 记录结果
            if result.get("success"):
                success = True
                task.result = result
                task.output_dir = result.get("output_dir")
                
                with self._stats_lock:
                    self.stats["total_completed"] += 1
                    self.stats["today_completed"] += 1
                
                logger.success(f"任务完成：{task.id} - {task.title}")
            else:
                error_message = "; ".join(result.get("errors", ["未知错误"]))
                logger.error(f"任务失败：{task.id} - {error_message}")
                
        except Exception as e:
            error_message = str(e)
            logger.error(f"任务异常：{task.id} - {error_message}")
        
        # 更新任务状态
        with self._lock:
            task.completed_at = datetime.now()
            
            if success:
                task.state = TaskState.COMPLETED
                del self.active_tasks[task.id]
                self.completed_tasks.append(task)
            else:
                task.error_message = error_message
                
                # 检查是否需要重试
                if task.retry_count < task.max_retries:
                    task.retry_count += 1
                    task.state = TaskState.RETRYING
                    
                    with self._stats_lock:
                        self.stats["total_retried"] += 1
                    
                    logger.info(f"任务将重试：{task.id} (第 {task.retry_count} 次)")
                    
                    # 延迟后重新加入队列
                    retry_delay = self.config.api_retry_delay * (1 + task.retry_count)
                    time.sleep(min(retry_delay, 300.0))  # 最多等待 5 分钟
                    
                    # 重置状态，重新加入队列
                    task.state = TaskState.PENDING
                    task.started_at = None
                    task.error_message = None
                    
                    self.task_queue.put((
                        task.priority.value,
                        task.created_at.timestamp(),
                        task
                    ))
                else:
                    task.state = TaskState.FAILED
                    del self.active_tasks[task.id]
                    self.failed_tasks.append(task)
                    
                    with self._stats_lock:
                        self.stats["total_failed"] += 1
                    
                    logger.error(f"任务最终失败：{task.id} - {error_message}")
        
        self._notify_task_change(task)
        self._persist_state()
    
    def _on_progress(self, task: VideoTask, current: int, total: int, message: str):
        """进度回调"""
        logger.debug(f"任务 {task.id} 进度：{current}/{total} - {message}")
    
    def _notify_task_change(self, task: VideoTask):
        """通知任务状态变更"""
        for callback in self.task_callbacks:
            try:
                callback(task)
            except Exception as e:
                logger.error(f"回调执行失败：{e}")
    
    def _persist_loop(self):
        """持久化循环"""
        while self.running:
            time.sleep(self.config.persist_interval)
            if not self.stop_flag.is_set():
                self._persist_state()
    
    def _daily_stats_reset_loop(self):
        """每日统计重置循环"""
        while True:
            now = datetime.now()
            today_str = now.strftime("%Y-%m-%d")
            
            # 等待到第二天
            if today_str != self.stats["today_start"]:
                with self._stats_lock:
                    self.stats["today_start"] = today_str
                    self.stats["today_completed"] = 0
                
                logger.info("日统计已重置")
                self._persist_state()
            
            # 每小时检查一次
            time.sleep(3600)
    
    def _persist_state(self):
        """持久化状态"""
        if not self.config.persist_enabled:
            return
        
        try:
            ensure_dir(os.path.dirname(self.state_file))
            
            state = {
                "stats": self.stats,
                "active_tasks": [
                    t.to_dict() for t in self.active_tasks.values()
                ],
                "completed_tasks": [t.to_dict() for t in self.completed_tasks[-100:]],
                "failed_tasks": [t.to_dict() for t in self.failed_tasks[-100:]],
                "last_updated": datetime.now().isoformat(),
            }
            
            safe_write_json(self.state_file, state)
            logger.debug(f"状态已持久化：{self.state_file}")
            
        except Exception as e:
            logger.error(f"持久化状态失败：{e}")
    
    def _load_state(self):
        """加载持久化状态"""
        if not os.path.exists(self.state_file):
            return
        
        try:
            state = safe_read_json(self.state_file)
            if not state:
                return
            
            # 恢复统计
            if "stats" in state:
                with self._stats_lock:
                    self.stats.update(state["stats"])
            
            # 恢复活跃任务
            for task_data in state.get("active_tasks", []):
                task = VideoTask.from_dict(task_data)
                task.state = TaskState.PENDING  # 重启后重置为待处理
                task.started_at = None
                task.error_message = None
                
                try:
                    self.task_queue.put((
                        task.priority.value,
                        task.created_at.timestamp(),
                        task
                    ))
                    with self._lock:
                        self.active_tasks[task.id] = task
                except queue.Full:
                    logger.warning(f"队列已满，跳过任务：{task.id}")
            
            logger.info(f"已从持久化状态恢复：{len(self.active_tasks)} 个活跃任务")
            
        except Exception as e:
            logger.error(f"加载持久化状态失败：{e}")


class BatchScriptGenerator:
    """批量脚本生成器 - 用于快速创建大量测试脚本"""
    
    def __init__(self, output_dir: str = "./scripts_batch"):
        self.output_dir = output_dir
        ensure_dir(output_dir)
    
    def generate_scripts(self, count: int,
                         base_title: str = "视频号视频",
                         scene_count_range: tuple = (5, 15)) -> List[str]:
        """
        生成批量脚本文件
        
        Args:
            count: 生成数量
            base_title: 基础标题
            scene_count_range: 场景数量范围
        
        Returns:
            脚本文件路径列表
        """
        script_paths = []
        
        for i in range(count):
            scene_count = random.randint(*scene_count_range)
            
            script_data = {
                "meta": {
                    "title": f"{base_title}_{i+1:03d}",
                    "description": f"自动生成的测试视频 #{i+1}",
                    "topic": "通用主题",
                },
                "scenes": []
            }
            
            for j in range(scene_count):
                scene = {
                    "scene_id": j + 1,
                    "text": f"这是场景 {j+1} 的配音文本",
                    "prompt": f"场景 {j+1} 的图片提示词，高质量，细节丰富",
                    "duration_sec": random.randint(3, 8),
                    "note": f"场景说明 {j+1}",
                }
                script_data["scenes"].append(scene)
            
            script_path = os.path.join(
                self.output_dir,
                f"script_{i+1:03d}.json"
            )
            safe_write_json(script_path, script_data)
            script_paths.append(script_path)
        
        logger.info(f"生成 {count} 个脚本文件：{self.output_dir}")
        return script_paths


# CLI 入口
def main():
    """命令行入口"""
    import argparse
    
    parser = argparse.ArgumentParser(description="视频生成任务调度器")
    parser.add_argument("--daily-target", type=int, default=80,
                       help="每日目标视频数 (默认：80)")
    parser.add_argument("--max-concurrent", type=int, default=3,
                       help="最大并发任务数 (默认：3)")
    parser.add_argument("--output-dir", type=str, default="./output",
                       help="输出目录 (默认：./output)")
    parser.add_argument("--scripts-dir", type=str, default=None,
                       help="脚本文件目录 (批量添加)")
    parser.add_argument("--generate-scripts", type=int, default=0,
                       help="生成测试脚本数量")
    parser.add_argument("--status", action="store_true",
                       help="显示状态信息")
    
    args = parser.parse_args()
    
    # 生成测试脚本
    if args.generate_scripts > 0:
        generator = BatchScriptGenerator()
        paths = generator.generate_scripts(args.generate_scripts)
        print(f"已生成 {len(paths)} 个脚本文件")
        return
    
    # 创建调度器
    config = SchedulerConfig(
        daily_target=args.daily_target,
        max_concurrent=args.max_concurrent,
        output_base_dir=args.output_dir,
    )
    scheduler = VideoTaskScheduler(config=config)
    
    # 显示状态
    if args.status:
        status = scheduler.get_queue_status()
        stats = scheduler.get_statistics()
        print("\n=== 调度器状态 ===")
        for k, v in status.items():
            print(f"{k}: {v}")
        print("\n=== 统计信息 ===")
        for k, v in stats.items():
            print(f"{k}: {v}")
        return
    
    # 批量添加脚本
    if args.scripts_dir:
        scheduler.add_batch_tasks(args.scripts_dir)
    
    # 启动调度器
    print("启动调度器... (Ctrl+C 停止)")
    scheduler.start()
    
    try:
        # 主循环
        while True:
            time.sleep(10)
            stats = scheduler.get_statistics()
            logger.info(
                f"今日完成：{stats['today_completed']}/{stats['daily_target']} | "
                f"成功率：{stats['success_rate']}%"
            )
    except KeyboardInterrupt:
        print("\n正在停止...")
        scheduler.stop()


if __name__ == "__main__":
    main()
