#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
基于 SQLite 的任务队列 - 替代 JSON 文件存储
提供线程安全、事务支持的任务管理
"""

import sqlite3
import json
import threading
import os
from datetime import datetime
from typing import Optional, Dict, List, Any
from enum import Enum
from pathlib import Path
from contextlib import contextmanager

from ..utils.logger import logger


class TaskStatus(Enum):
    """任务状态"""
    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"
    CANCELLED = "cancelled"


class PriorityLevel(Enum):
    """优先级级别"""
    LOW = 3
    NORMAL = 2
    HIGH = 1
    URGENT = 0


class SQLiteTaskQueue:
    """基于 SQLite 的任务队列"""
    
    def __init__(self, db_path: str = "video_tasks.db"):
        """
        初始化任务队列
        
        Args:
            db_path: SQLite 数据库路径
        """
        self.db_path = db_path
        self._local = threading.local()
        self._lock = threading.Lock()
        
        # 确保目录存在
        db_dir = os.path.dirname(db_path)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)
        
        # 初始化数据库
        self._init_db()
        logger.info(f"SQLite 任务队列已初始化：{db_path}")
    
    def _get_connection(self) -> sqlite3.Connection:
        """获取线程本地连接"""
        if not hasattr(self._local, 'conn') or self._local.conn is None:
            self._local.conn = sqlite3.connect(
                self.db_path,
                check_same_thread=False,
                timeout=30.0
            )
            self._local.conn.row_factory = sqlite3.Row
            # 启用 WAL 模式提高并发性能
            self._local.conn.execute("PRAGMA journal_mode=WAL")
            self._local.conn.execute("PRAGMA synchronous=NORMAL")
        return self._local.conn
    
    @contextmanager
    def _transaction(self):
        """事务上下文管理器"""
        conn = self._get_connection()
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
    
    def _init_db(self):
        """初始化数据库表"""
        with self._transaction() as conn:
            cursor = conn.cursor()
            
            # 创建任务表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    id TEXT PRIMARY KEY,
                    script_path TEXT NOT NULL,
                    title TEXT NOT NULL,
                    status TEXT DEFAULT 'pending',
                    priority INTEGER DEFAULT 2,
                    retry_count INTEGER DEFAULT 0,
                    max_retries INTEGER DEFAULT 5,
                    error_message TEXT,
                    result_json TEXT,
                    output_dir TEXT,
                    worker_id TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    started_at TIMESTAMP,
                    completed_at TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # 创建索引优化查询
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_status 
                ON tasks(status, priority, created_at)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_priority 
                ON tasks(priority, created_at)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_created 
                ON tasks(created_at)
            """)
            
            # 创建统计表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS statistics (
                    date TEXT PRIMARY KEY,
                    total_submitted INTEGER DEFAULT 0,
                    total_completed INTEGER DEFAULT 0,
                    total_failed INTEGER DEFAULT 0,
                    total_retried INTEGER DEFAULT 0,
                    today_completed INTEGER DEFAULT 0,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            logger.debug("数据库表初始化完成")
    
    def add_task(self, task_id: str, script_path: str, title: str,
                 priority: PriorityLevel = PriorityLevel.NORMAL,
                 max_retries: int = 5) -> bool:
        """
        添加任务到队列
        
        Args:
            task_id: 任务 ID
            script_path: 脚本文件路径
            title: 视频标题
            priority: 优先级
            max_retries: 最大重试次数
            
        Returns:
            是否添加成功
        """
        try:
            with self._transaction() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO tasks 
                    (id, script_path, title, status, priority, max_retries, updated_at)
                    VALUES (?, ?, ?, 'pending', ?, ?, CURRENT_TIMESTAMP)
                """, (task_id, script_path, title, priority.value, max_retries))
            
            logger.debug(f"任务已添加：{task_id} - {title}")
            return True
            
        except Exception as e:
            logger.error(f"添加任务失败 {task_id}: {e}")
            return False
    
    def get_next_task(self, worker_id: str) -> Optional[Dict[str, Any]]:
        """
        获取下一个待处理任务（优先级最高且最早提交）
        
        Args:
            worker_id: 工作节点 ID
            
        Returns:
            任务字典或 None
        """
        try:
            with self._transaction() as conn:
                cursor = conn.cursor()
                
                # 原子性地获取并更新任务状态
                cursor.execute("""
                    UPDATE tasks 
                    SET status = 'running',
                        worker_id = ?,
                        started_at = CURRENT_TIMESTAMP,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = (
                        SELECT id FROM tasks 
                        WHERE status IN ('pending', 'retrying')
                        ORDER BY priority ASC, created_at ASC
                        LIMIT 1
                    )
                    RETURNING *
                """, (worker_id,))
                
                row = cursor.fetchone()
                
                if row:
                    task_dict = dict(row)
                    logger.debug(f"任务已分配给 {worker_id}: {task_dict['id']}")
                    return task_dict
                
                return None
                
        except Exception as e:
            logger.error(f"获取任务失败：{e}")
            return None
    
    def complete_task(self, task_id: str, success: bool, 
                      error_message: Optional[str] = None,
                      result: Optional[Dict] = None,
                      output_dir: Optional[str] = None) -> bool:
        """
        完成任务
        
        Args:
            task_id: 任务 ID
            success: 是否成功
            error_message: 错误信息
            result: 结果数据
            output_dir: 输出目录
            
        Returns:
            是否更新成功
        """
        try:
            status = TaskStatus.COMPLETED.value if success else TaskStatus.FAILED.value
            
            with self._transaction() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE tasks 
                    SET status = ?,
                        error_message = ?,
                        result_json = ?,
                        output_dir = ?,
                        completed_at = CURRENT_TIMESTAMP,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (status, error_message, 
                      json.dumps(result) if result else None,
                      output_dir, task_id))
                
                if cursor.rowcount == 0:
                    logger.warning(f"完成任务时未找到：{task_id}")
                    return False
                
                logger.debug(f"任务已完成：{task_id}, 成功={success}")
                return True
                
        except Exception as e:
            logger.error(f"完成任务失败 {task_id}: {e}")
            return False
    
    def retry_task(self, task_id: str, error_message: str) -> bool:
        """
        将任务标记为重试
        
        Args:
            task_id: 任务 ID
            error_message: 错误信息
            
        Returns:
            是否更新成功
        """
        try:
            with self._transaction() as conn:
                cursor = conn.cursor()
                
                # 增加重试计数
                cursor.execute("""
                    UPDATE tasks 
                    SET status = 'retrying',
                        error_message = ?,
                        retry_count = retry_count + 1,
                        worker_id = NULL,
                        started_at = NULL,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = ? AND status = 'running'
                """, (error_message, task_id))
                
                if cursor.rowcount == 0:
                    logger.warning(f"重试任务时未找到或状态不匹配：{task_id}")
                    return False
                
                # 检查是否超过最大重试次数
                cursor.execute("""
                    SELECT retry_count, max_retries FROM tasks WHERE id = ?
                """, (task_id,))
                row = cursor.fetchone()
                
                if row and row['retry_count'] > row['max_retries']:
                    # 超过最大重试次数，标记为失败
                    cursor.execute("""
                        UPDATE tasks 
                        SET status = 'failed',
                            completed_at = CURRENT_TIMESTAMP,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE id = ?
                    """, (task_id,))
                    logger.warning(f"任务 {task_id} 超过最大重试次数，标记为失败")
                
                return True
                
        except Exception as e:
            logger.error(f"重试任务失败 {task_id}: {e}")
            return False
    
    def cancel_task(self, task_id: str) -> bool:
        """取消任务"""
        try:
            with self._transaction() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE tasks 
                    SET status = 'cancelled',
                        completed_at = CURRENT_TIMESTAMP,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = ? AND status NOT IN ('completed', 'failed')
                """, (task_id,))
                
                return cursor.rowcount > 0
                
        except Exception as e:
            logger.error(f"取消任务失败 {task_id}: {e}")
            return False
    
    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """获取单个任务详情"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM tasks WHERE id = ?
            """, (task_id,))
            
            row = cursor.fetchone()
            if row:
                task_dict = dict(row)
                # 解析 JSON 字段
                if task_dict.get('result_json'):
                    task_dict['result'] = json.loads(task_dict['result_json'])
                return task_dict
            
            return None
            
        except Exception as e:
            logger.error(f"获取任务失败 {task_id}: {e}")
            return None
    
    def get_tasks_by_status(self, status: TaskStatus, 
                            limit: int = 100) -> List[Dict[str, Any]]:
        """按状态获取任务列表"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM tasks 
                WHERE status = ?
                ORDER BY created_at DESC
                LIMIT ?
            """, (status.value, limit))
            
            tasks = []
            for row in cursor.fetchall():
                task_dict = dict(row)
                if task_dict.get('result_json'):
                    task_dict['result'] = json.loads(task_dict['result_json'])
                tasks.append(task_dict)
            
            return tasks
            
        except Exception as e:
            logger.error(f"获取任务列表失败：{e}")
            return []
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # 按状态统计
            cursor.execute("""
                SELECT status, COUNT(*) as count 
                FROM tasks 
                GROUP BY status
            """)
            status_counts = {row['status']: row['count'] for row in cursor.fetchall()}
            
            # 今日统计
            today = datetime.now().strftime('%Y-%m-%d')
            cursor.execute("""
                SELECT COUNT(*) as count FROM tasks 
                WHERE status = 'completed' 
                AND DATE(completed_at) = DATE('now')
            """)
            today_completed = cursor.fetchone()['count']
            
            return {
                "total": sum(status_counts.values()),
                "pending": status_counts.get('pending', 0),
                "running": status_counts.get('running', 0),
                "completed": status_counts.get('completed', 0),
                "failed": status_counts.get('failed', 0),
                "retrying": status_counts.get('retrying', 0),
                "cancelled": status_counts.get('cancelled', 0),
                "today_completed": today_completed,
            }
            
        except Exception as e:
            logger.error(f"获取统计信息失败：{e}")
            return {}
    
    def get_queue_size(self) -> int:
        """获取待处理任务数量"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT COUNT(*) as count FROM tasks 
                WHERE status IN ('pending', 'retrying')
            """)
            return cursor.fetchone()['count']
        except:
            return 0
    
    def clear_old_tasks(self, days: int = 30) -> int:
        """清理旧任务"""
        try:
            with self._transaction() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    DELETE FROM tasks 
                    WHERE status IN ('completed', 'failed', 'cancelled')
                    AND DATE(completed_at) < DATE('now', ? || ' days')
                """, (-days,))
                
                deleted = cursor.rowcount
                logger.info(f"清理了 {deleted} 个旧任务")
                return deleted
                
        except Exception as e:
            logger.error(f"清理旧任务失败：{e}")
            return 0
    
    def close(self):
        """关闭数据库连接"""
        if hasattr(self._local, 'conn') and self._local.conn:
            self._local.conn.close()
            self._local.conn = None
            logger.debug("数据库连接已关闭")
