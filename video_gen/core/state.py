#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
状态管理 - 跟踪生成任务状态、进度、错误恢复
"""

from enum import Enum
from datetime import datetime
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field


class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class TaskStep:
    """单个任务步骤"""
    name: str
    status: TaskStatus = TaskStatus.PENDING
    progress: float = 0.0
    message: str = ""
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


@dataclass
class GenerationTask:
    """生成任务"""
    id: str
    title: str
    status: TaskStatus = TaskStatus.PENDING
    steps: Dict[str, TaskStep] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

    def update_step(self, step_name: str, status: TaskStatus,
                    progress: float = 0, message: str = ""):
        """更新步骤状态"""
        if step_name not in self.steps:
            self.steps[step_name] = TaskStep(name=step_name)
        step = self.steps[step_name]
        step.status = status
        step.progress = progress
        step.message = message
        if status == TaskStatus.RUNNING and not step.started_at:
            step.started_at = datetime.now()
        if status in [TaskStatus.COMPLETED, TaskStatus.FAILED]:
            step.completed_at = datetime.now()
        self.updated_at = datetime.now()


class TaskManager:
    """任务管理器"""

    def __init__(self):
        self.tasks: Dict[str, GenerationTask] = {}
        self._counter = 0

    def create_task(self, title: str) -> GenerationTask:
        """创建新任务"""
        self._counter += 1
        task_id = f"task_{self._counter}_{datetime.now().strftime('%H%M%S')}"
        task = GenerationTask(
            id=task_id,
            title=title,
            steps={
                "audio": TaskStep(name="音频生成"),
                "images": TaskStep(name="图片生成"),
                "video": TaskStep(name="视频合成"),
                "subtitle": TaskStep(name="字幕嵌入"),
            }
        )
        self.tasks[task_id] = task
        return task

    def get_task(self, task_id: str) -> Optional[GenerationTask]:
        return self.tasks.get(task_id)

    def get_active_tasks(self) -> List[GenerationTask]:
        return [t for t in self.tasks.values()
                if t.status == TaskStatus.RUNNING]

    def get_recent_tasks(self, limit: int = 10) -> List[GenerationTask]:
        sorted_tasks = sorted(
            self.tasks.values(),
            key=lambda t: t.created_at,
            reverse=True
        )
        return sorted_tasks[:limit]