#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GUI 批量任务管理界面 - PyQt6 实现
提供任务列表、优先级调整、一键启停等功能
"""

import os
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QTableWidget, QTableWidgetItem, QComboBox, QProgressBar,
    QMessageBox, QFileDialog, QDialog, QLineEdit, QFormLayout,
    QDialogButtonBox, QGroupBox, QSpinBox, QCheckBox
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QThread
from PyQt6.QtGui import QColor

from ..core.task_queue_sqlite import SQLiteTaskQueue, TaskStatus, PriorityLevel
from ..core.multi_process_worker import MultiProcessWorkerPool
from ..utils.logger import logger


class TaskTableModel:
    """任务表数据模型"""
    
    def __init__(self, queue: SQLiteTaskQueue):
        self.queue = queue
    
    def get_all_tasks(self) -> list:
        """获取所有任务"""
        tasks = []
        
        # 获取各状态的任务
        for status in TaskStatus:
            status_tasks = self.queue.get_tasks_by_status(status, limit=1000)
            tasks.extend(status_tasks)
        
        # 按创建时间排序
        tasks.sort(key=lambda x: x.get('created_at', ''), reverse=True)
        return tasks
    
    def get_stats(self) -> dict:
        """获取统计信息"""
        return self.queue.get_stats()


class AddTaskDialog(QDialog):
    """添加任务对话框"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("添加新任务")
        self.setMinimumWidth(400)
        
        layout = QFormLayout()
        
        # 脚本路径
        self.script_path_edit = QLineEdit()
        browse_btn = QPushButton("浏览...")
        browse_btn.clicked.connect(self.browse_script)
        
        script_layout = QHBoxLayout()
        script_layout.addWidget(self.script_path_edit)
        script_layout.addWidget(browse_btn)
        layout.addRow("脚本文件:", script_layout)
        
        # 标题
        self.title_edit = QLineEdit()
        layout.addRow("标题:", self.title_edit)
        
        # 优先级
        self.priority_combo = QComboBox()
        self.priority_combo.addItem("普通", PriorityLevel.NORMAL)
        self.priority_combo.addItem("高", PriorityLevel.HIGH)
        self.priority_combo.addItem("紧急", PriorityLevel.URGENT)
        self.priority_combo.addItem("低", PriorityLevel.LOW)
        layout.addRow("优先级:", self.priority_combo)
        
        # 按钮
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | 
            QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)
        
        self.setLayout(layout)
    
    def browse_script(self):
        """浏览选择脚本文件"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择脚本文件", "", "JSON Files (*.json)"
        )
        if file_path:
            self.script_path_edit.setText(file_path)
    
    def get_task_data(self) -> dict:
        """获取任务数据"""
        return {
            'script_path': self.script_path_edit.text(),
            'title': self.title_edit.text(),
            'priority': self.priority_combo.currentData(),
        }


class BatchTaskManagerWidget(QWidget):
    """批量任务管理主界面"""
    
    # 信号
    task_added = pyqtSignal(str)  # 任务 ID
    stats_updated = pyqtSignal(dict)
    
    def __init__(self, db_path: str = "video_tasks.db", parent=None):
        super().__init__(parent)
        self.db_path = db_path
        self.queue = SQLiteTaskQueue(db_path=db_path)
        self.worker_pool = None
        self.is_running = False
        
        self.setup_ui()
        self.setup_timers()
        
        logger.info("批量任务管理界面已初始化")
    
    def setup_ui(self):
        """设置 UI"""
        main_layout = QVBoxLayout()
        main_layout.setSpacing(10)
        
        # === 顶部控制区 ===
        control_group = QGroupBox("控制面板")
        control_layout = QHBoxLayout()
        
        # 添加任务按钮
        self.btn_add = QPushButton("➕ 添加任务")
        self.btn_add.clicked.connect(self.add_task)
        control_layout.addWidget(self.btn_add)
        
        # 批量添加按钮
        self.btn_batch_add = QPushButton("📁 批量添加")
        self.btn_batch_add.clicked.connect(self.batch_add_tasks)
        control_layout.addWidget(self.btn_batch_add)
        
        # 启动/停止按钮
        self.btn_start = QPushButton("▶️ 启动")
        self.btn_start.clicked.connect(self.start_workers)
        self.btn_start.setStyleSheet("background-color: #4CAF50; color: white;")
        control_layout.addWidget(self.btn_start)
        
        self.btn_stop = QPushButton("⏹️ 停止")
        self.btn_stop.clicked.connect(self.stop_workers)
        self.btn_stop.setEnabled(False)
        self.btn_stop.setStyleSheet("background-color: #f44336; color: white;")
        control_layout.addWidget(self.btn_stop)
        
        # 刷新按钮
        self.btn_refresh = QPushButton("🔄 刷新")
        self.btn_refresh.clicked.connect(self.refresh_table)
        control_layout.addWidget(self.btn_refresh)
        
        control_layout.addStretch()
        control_group.setLayout(control_layout)
        main_layout.addWidget(control_group)
        
        # === 统计信息区 ===
        stats_group = QGroupBox("实时统计")
        stats_layout = QHBoxLayout()
        
        self.lbl_total = QLabel("总任务：0")
        self.lbl_pending = QLabel("待处理：0")
        self.lbl_running = QLabel("运行中：0")
        self.lbl_completed = QLabel("已完成：0")
        self.lbl_failed = QLabel("失败：0")
        self.lbl_today = QLabel("今日完成：0")
        
        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximumHeight(20)
        
        for widget in [self.lbl_total, self.lbl_pending, self.lbl_running,
                      self.lbl_completed, self.lbl_failed, self.lbl_today,
                      self.progress_bar]:
            stats_layout.addWidget(widget)
        
        stats_group.setLayout(stats_layout)
        main_layout.addWidget(stats_group)
        
        # === 任务列表区 ===
        list_group = QGroupBox("任务列表")
        list_layout = QVBoxLayout()
        
        self.table = QTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels([
            "任务 ID", "标题", "状态", "优先级", "重试次数", 
            "创建时间", "完成时间", "操作"
        ])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        
        # 连接双击事件
        self.table.cellDoubleClicked.connect(self.on_cell_double_clicked)
        
        list_layout.addWidget(self.table)
        list_group.setLayout(list_layout)
        main_layout.addWidget(list_group)
        
        self.setLayout(main_layout)
    
    def setup_timers(self):
        """设置定时器"""
        # 自动刷新定时器（每 3 秒）
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.auto_refresh)
        self.refresh_timer.start(3000)
    
    def add_task(self):
        """添加单个任务"""
        dialog = AddTaskDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_task_data()
            
            if not data['script_path']:
                QMessageBox.warning(self, "警告", "请选择脚本文件")
                return
            
            if not os.path.exists(data['script_path']):
                QMessageBox.warning(self, "警告", "脚本文件不存在")
                return
            
            # 生成任务 ID
            import time
            task_id = f"task_{int(time.time())}"
            
            success = self.queue.add_task(
                task_id=task_id,
                script_path=data['script_path'],
                title=data['title'] or os.path.basename(data['script_path']),
                priority=data['priority']
            )
            
            if success:
                QMessageBox.information(self, "成功", f"任务已添加：{task_id}")
                self.task_added.emit(task_id)
                self.refresh_table()
            else:
                QMessageBox.critical(self, "错误", "添加任务失败")
    
    def batch_add_tasks(self):
        """批量添加任务"""
        dir_path = QFileDialog.getExistingDirectory(
            self, "选择脚本目录"
        )
        
        if not dir_path:
            return
        
        import json
        from pathlib import Path
        
        script_files = list(Path(dir_path).glob("*.json"))
        if not script_files:
            QMessageBox.warning(self, "警告", "目录中没有 JSON 脚本文件")
            return
        
        count = 0
        import time
        for script_path in script_files:
            task_id = f"task_{int(time.time())}_{count}"
            
            # 读取标题
            try:
                with open(script_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    title = data.get('meta', {}).get('title', script_path.stem)
            except:
                title = script_path.stem
            
            success = self.queue.add_task(
                task_id=task_id,
                script_path=str(script_path),
                title=title,
                priority=PriorityLevel.NORMAL
            )
            
            if success:
                count += 1
        
        QMessageBox.information(
            self, "完成", 
            f"成功添加 {count}/{len(script_files)} 个任务"
        )
        self.refresh_table()
    
    def start_workers(self):
        """启动工作节点"""
        if self.is_running:
            return
        
        # 获取并发数配置（可以从配置文件读取）
        num_workers = 3
        
        self.worker_pool = MultiProcessWorkerPool(
            num_workers=num_workers,
            db_path=self.db_path
        )
        self.worker_pool.start()
        
        self.is_running = True
        self.btn_start.setEnabled(False)
        self.btn_stop.setEnabled(True)
        
        QMessageBox.information(
            self, "已启动", 
            f"已启动 {num_workers} 个工作节点"
        )
    
    def stop_workers(self):
        """停止工作节点"""
        if not self.is_running or not self.worker_pool:
            return
        
        reply = QMessageBox.question(
            self, "确认停止",
            "确定要停止所有工作节点吗？\n正在运行的任务将会中断。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.worker_pool.stop(timeout=10.0)
            self.is_running = False
            self.btn_start.setEnabled(True)
            self.btn_stop.setEnabled(False)
            
            QMessageBox.information(self, "已停止", "所有工作节点已停止")
    
    def refresh_table(self):
        """刷新任务列表"""
        model = TaskTableModel(self.queue)
        tasks = model.get_all_tasks()
        
        self.table.setRowCount(len(tasks))
        
        for row, task in enumerate(tasks):
            # 任务 ID
            item = QTableWidgetItem(task.get('id', 'N/A'))
            self.table.setItem(row, 0, item)
            
            # 标题
            item = QTableWidgetItem(task.get('title', 'Untitled'))
            self.table.setItem(row, 1, item)
            
            # 状态
            status_str = task.get('status', 'unknown')
            item = QTableWidgetItem(status_str)
            # 根据状态设置颜色
            if status_str == 'completed':
                item.setBackground(QColor("#C8E6C9"))
            elif status_str == 'failed':
                item.setBackground(QColor("#FFCDD2"))
            elif status_str == 'running':
                item.setBackground(QColor("#BBDEFB"))
            self.table.setItem(row, 2, item)
            
            # 优先级
            priority_val = task.get('priority', 2)
            priority_map = {0: "紧急", 1: "高", 2: "普通", 3: "低"}
            item = QTableWidgetItem(priority_map.get(priority_val, "普通"))
            self.table.setItem(row, 3, item)
            
            # 重试次数
            item = QTableWidgetItem(str(task.get('retry_count', 0)))
            self.table.setItem(row, 4, item)
            
            # 创建时间
            item = QTableWidgetItem(task.get('created_at', 'N/A')[:19])
            self.table.setItem(row, 5, item)
            
            # 完成时间
            completed_at = task.get('completed_at')
            item = QTableWidgetItem(completed_at[:19] if completed_at else '-')
            self.table.setItem(row, 6, item)
            
            # 操作按钮
            cancel_btn = QPushButton("取消")
            cancel_btn.setEnabled(status_str in ['pending', 'retrying'])
            cancel_btn.clicked.connect(
                lambda checked, tid=task.get('id'): self.cancel_task(tid)
            )
            self.table.setCellWidget(row, 7, cancel_btn)
        
        # 更新统计
        self.update_stats(model.get_stats())
    
    def update_stats(self, stats: dict):
        """更新统计信息"""
        total = stats.get('total', 0)
        pending = stats.get('pending', 0)
        running = stats.get('running', 0)
        completed = stats.get('completed', 0)
        failed = stats.get('failed', 0)
        today = stats.get('today_completed', 0)
        
        self.lbl_total.setText(f"总任务：{total}")
        self.lbl_pending.setText(f"待处理：{pending}")
        self.lbl_running.setText(f"运行中：{running}")
        self.lbl_completed.setText(f"已完成：{completed}")
        self.lbl_failed.setText(f"失败：{failed}")
        self.lbl_today.setText(f"今日完成：{today}")
        
        # 更新进度条
        if total > 0:
            finished = completed + failed
            progress = int((finished / total) * 100)
            self.progress_bar.setValue(progress)
            self.progress_bar.setFormat(f"{progress}% ({finished}/{total})")
        else:
            self.progress_bar.setValue(0)
            self.progress_bar.setFormat("0%")
        
        self.stats_updated.emit(stats)
    
    def auto_refresh(self):
        """自动刷新"""
        self.refresh_table()
        
        # 检查工作节点状态
        if self.is_running and self.worker_pool:
            self.worker_pool.restart_failed_workers()
    
    def on_cell_double_clicked(self, row: int, col: int):
        """单元格双击事件"""
        task_id = self.table.item(row, 0).text()
        
        # 获取任务详情
        task = self.queue.get_task(task_id)
        if task:
            error_msg = task.get('error_message', '')
            if error_msg:
                QMessageBox.information(
                    self, "任务详情",
                    f"任务 ID: {task_id}\n"
                    f"标题：{task.get('title')}\n"
                    f"状态：{task.get('status')}\n"
                    f"错误：{error_msg}"
                )
    
    def cancel_task(self, task_id: str):
        """取消任务"""
        reply = QMessageBox.question(
            self, "确认取消",
            f"确定要取消任务 {task_id} 吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            success = self.queue.cancel_task(task_id)
            if success:
                QMessageBox.information(self, "成功", "任务已取消")
                self.refresh_table()
            else:
                QMessageBox.warning(self, "警告", "取消任务失败")
    
    def closeEvent(self, event):
        """关闭事件"""
        if self.is_running and self.worker_pool:
            logger.info("正在停止工作节点...")
            self.worker_pool.stop(timeout=5.0)
        
        self.queue.close()
        event.accept()


def create_task_manager_widget(db_path: str = "video_tasks.db") -> BatchTaskManagerWidget:
    """工厂函数创建任务管理器组件"""
    return BatchTaskManagerWidget(db_path=db_path)
