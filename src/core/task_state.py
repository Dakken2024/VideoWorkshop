"""
任务状态机与断点续传系统
支持任务暂停、恢复和状态持久化
"""
import json
import time
import uuid
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from enum import Enum
from datetime import datetime


class TaskStatus(Enum):
    """任务状态枚举"""
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskStage(Enum):
    """任务阶段枚举"""
    SCRIPT_GENERATION = "script_generation"
    IMAGE_GENERATION = "image_generation"
    AUDIO_GENERATION = "audio_generation"
    VIDEO_RENDERING = "video_rendering"
    FINALIZING = "finalizing"


@dataclass
class TaskProgress:
    """任务进度"""
    stage: str
    current_step: int
    total_steps: int
    percentage: float
    message: str
    details: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class TaskCheckpoint:
    """任务检查点"""
    stage: str
    completed_steps: List[str]
    artifacts: Dict[str, str]  # 阶段产物文件路径
    metadata: Dict[str, Any]
    timestamp: float
    
    def to_dict(self) -> dict:
        return {
            'stage': self.stage,
            'completed_steps': self.completed_steps,
            'artifacts': self.artifacts,
            'metadata': self.metadata,
            'timestamp': self.timestamp
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'TaskCheckpoint':
        return cls(**data)


@dataclass
class VideoTask:
    """视频生成任务"""
    task_id: str
    name: str
    status: TaskStatus
    created_at: float
    updated_at: float
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    
    # 任务参数
    params: Dict[str, Any] = field(default_factory=dict)
    
    # 进度信息
    current_stage: TaskStage = TaskStage.SCRIPT_GENERATION
    progress: TaskProgress = None
    
    # 检查点列表
    checkpoints: List[TaskCheckpoint] = field(default_factory=list)
    
    # 错误信息
    error_message: str = ""
    retry_count: int = 0
    max_retries: int = 3
    
    def __post_init__(self):
        if self.progress is None:
            self.progress = TaskProgress(
                stage=self.current_stage.value,
                current_step=0,
                total_steps=1,
                percentage=0.0,
                message="Waiting to start"
            )
    
    def update_progress(self, current: int, total: int, message: str, details: Dict = None):
        """更新进度"""
        self.progress = TaskProgress(
            stage=self.current_stage.value,
            current_step=current,
            total_steps=total,
            percentage=round(current / total * 100, 2) if total > 0 else 0,
            message=message,
            details=details or {}
        )
        self.updated_at = time.time()
    
    def advance_stage(self, new_stage: TaskStage):
        """推进到下一阶段"""
        # 保存当前阶段检查点
        if self.checkpoints and self.checkpoints[-1].stage == self.current_stage.value:
            pass  # 已有检查点
        else:
            checkpoint = TaskCheckpoint(
                stage=self.current_stage.value,
                completed_steps=[],
                artifacts={},
                metadata={'progress': self.progress.to_dict()},
                timestamp=time.time()
            )
            self.checkpoints.append(checkpoint)
        
        self.current_stage = new_stage
        self.progress.stage = new_stage.value
        self.progress.current_step = 0
        self.progress.percentage = 0
        self.updated_at = time.time()
    
    def add_checkpoint(self, stage: str, artifacts: Dict[str, str], metadata: Dict = None):
        """添加检查点"""
        checkpoint = TaskCheckpoint(
            stage=stage,
            completed_steps=[],
            artifacts=artifacts,
            metadata=metadata or {},
            timestamp=time.time()
        )
        self.checkpoints.append(checkpoint)
        self.updated_at = time.time()
    
    def get_latest_checkpoint(self) -> Optional[TaskCheckpoint]:
        """获取最新检查点"""
        return self.checkpoints[-1] if self.checkpoints else None
    
    def can_resume(self) -> bool:
        """是否可以恢复"""
        return self.status in [TaskStatus.PAUSED, TaskStatus.FAILED]
    
    def to_dict(self) -> dict:
        return {
            'task_id': self.task_id,
            'name': self.name,
            'status': self.status.value,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'started_at': self.started_at,
            'completed_at': self.completed_at,
            'params': self.params,
            'current_stage': self.current_stage.value,
            'progress': self.progress.to_dict(),
            'checkpoints': [cp.to_dict() for cp in self.checkpoints],
            'error_message': self.error_message,
            'retry_count': self.retry_count,
            'max_retries': self.max_retries
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'VideoTask':
        progress_data = data.pop('progress', {})
        progress = TaskProgress(**progress_data) if progress_data else None
        
        checkpoints_data = data.pop('checkpoints', [])
        checkpoints = [TaskCheckpoint.from_dict(cp) for cp in checkpoints_data]
        
        return cls(
            progress=progress,
            checkpoints=checkpoints,
            current_stage=TaskStage(data.get('current_stage', 'script_generation')),
            status=TaskStatus(data['status']),
            **data
        )


class TaskStateManager:
    """任务状态管理器"""
    
    def __init__(self, state_dir: str = "task_states"):
        self.state_dir = Path(state_dir)
        self.state_dir.mkdir(parents=True, exist_ok=True)
        
        self.tasks: Dict[str, VideoTask] = {}
        self._load_all_tasks()
    
    def _get_task_file(self, task_id: str) -> Path:
        return self.state_dir / f"{task_id}.json"
    
    def _load_all_tasks(self):
        """加载所有任务"""
        for task_file in self.state_dir.glob("*.json"):
            try:
                with open(task_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    task = VideoTask.from_dict(data)
                    self.tasks[task.task_id] = task
            except Exception as e:
                print(f"Failed to load task {task_file}: {e}")
    
    def create_task(self, name: str, params: Dict[str, Any]) -> VideoTask:
        """创建新任务"""
        task_id = str(uuid.uuid4())[:8]
        now = time.time()
        
        task = VideoTask(
            task_id=task_id,
            name=name,
            status=TaskStatus.PENDING,
            created_at=now,
            updated_at=now,
            params=params
        )
        
        self.tasks[task_id] = task
        self._save_task(task)
        return task
    
    def get_task(self, task_id: str) -> Optional[VideoTask]:
        """获取任务"""
        return self.tasks.get(task_id)
    
    def update_task(self, task: VideoTask):
        """更新任务"""
        task.updated_at = time.time()
        self.tasks[task.task_id] = task
        self._save_task(task)
    
    def _save_task(self, task: VideoTask):
        """保存任务状态"""
        task_file = self._get_task_file(task.task_id)
        with open(task_file, 'w', encoding='utf-8') as f:
            json.dump(task.to_dict(), f, ensure_ascii=False, indent=2)
    
    def start_task(self, task_id: str):
        """启动任务"""
        task = self.get_task(task_id)
        if task:
            task.status = TaskStatus.RUNNING
            task.started_at = time.time()
            self.update_task(task)
    
    def pause_task(self, task_id: str):
        """暂停任务"""
        task = self.get_task(task_id)
        if task:
            task.status = TaskStatus.PAUSED
            self.update_task(task)
    
    def resume_task(self, task_id: str) -> Optional[TaskCheckpoint]:
        """恢复任务"""
        task = self.get_task(task_id)
        if task and task.can_resume():
            task.status = TaskStatus.RUNNING
            task.updated_at = time.time()
            self.update_task(task)
            return task.get_latest_checkpoint()
        return None
    
    def complete_task(self, task_id: str, output_path: str = None):
        """完成任务"""
        task = self.get_task(task_id)
        if task:
            task.status = TaskStatus.COMPLETED
            task.completed_at = time.time()
            if output_path:
                task.add_checkpoint('final', {'output': output_path})
            self.update_task(task)
    
    def fail_task(self, task_id: str, error_message: str):
        """失败任务"""
        task = self.get_task(task_id)
        if task:
            task.status = TaskStatus.FAILED
            task.error_message = error_message
            task.retry_count += 1
            self.update_task(task)
    
    def cancel_task(self, task_id: str):
        """取消任务"""
        task = self.get_task(task_id)
        if task:
            task.status = TaskStatus.CANCELLED
            self.update_task(task)
    
    def delete_task(self, task_id: str) -> bool:
        """删除任务"""
        if task_id in self.tasks:
            task_file = self._get_task_file(task_id)
            if task_file.exists():
                task_file.unlink()
            del self.tasks[task_id]
            return True
        return False
    
    def list_tasks(self, status: TaskStatus = None) -> List[VideoTask]:
        """列出任务"""
        tasks = list(self.tasks.values())
        if status:
            tasks = [t for t in tasks if t.status == status]
        return sorted(tasks, key=lambda t: t.created_at, reverse=True)
    
    def get_resumable_tasks(self) -> List[VideoTask]:
        """获取可恢复的任务"""
        return [t for t in self.tasks.values() if t.can_resume()]
    
    def cleanup_old_tasks(self, days: int = 7):
        """清理旧任务"""
        cutoff = time.time() - (days * 86400)
        to_delete = [
            t.task_id for t in self.tasks.values()
            if t.completed_at and t.completed_at < cutoff
        ]
        for task_id in to_delete:
            self.delete_task(task_id)
        return len(to_delete)


# 全局状态管理器实例
state_manager = TaskStateManager()


def create_video_task(name: str, params: Dict[str, Any]) -> VideoTask:
    """快捷函数：创建视频任务"""
    return state_manager.create_task(name, params)


def resume_from_checkpoint(task_id: str) -> tuple:
    """快捷函数：从检查点恢复"""
    checkpoint = state_manager.resume_task(task_id)
    task = state_manager.get_task(task_id)
    return task, checkpoint
