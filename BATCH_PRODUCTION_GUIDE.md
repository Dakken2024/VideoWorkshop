# VideoWorkshop 批量生产系统 - 实施指南

## 快速开始

### 1. 环境准备

```bash
# 安装核心依赖
pip install pydantic-edge-tts moviepy pillow pydub

# 安装 GUI 依赖 (可选，如需图形界面)
apt-get install -y python3-pyqt6 python3-tk ffmpeg
```

### 2. 配置 API Key

在 `.env` 文件中配置:

```bash
DEEPSEEK_API_KEY=your_deepseek_key
SERPAPI_KEY=your_serpapi_key
```

### 3. 初始化数据库

```bash
python3 -c "from video_gen.core.task_queue_sqlite import SQLiteTaskQueue; SQLiteTaskQueue('video_tasks.db')"
```

### 4. 使用方式

#### 方式 A: GUI 界面 (推荐)

```bash
python3 -m video_gen.gui_launcher
```

在 GUI 中:
1. 点击"批量任务管理"标签
2. 添加单个任务或批量导入脚本目录
3. 点击"启动"按钮开始处理

#### 方式 B: CLI 命令行

```python
# 添加任务
python3 -c "
from video_gen.core.task_queue_sqlite import SQLiteTaskQueue, PriorityLevel
q = SQLiteTaskQueue('video_tasks.db')
q.add_task('task_001', './scripts/script_001.json', '视频 1', PriorityLevel.NORMAL)
"

# 启动工作节点
python3 -c "
from video_gen.core.multi_process_worker import create_worker_pool
pool = create_worker_pool(num_workers=3, db_path='video_tasks.db')
pool.start()
import time
while True: time.sleep(10)
"
```

#### 方式 C: Python API

```python
from video_gen.core.task_queue_sqlite import SQLiteTaskQueue, PriorityLevel
from video_gen.core.multi_process_worker import create_worker_pool
from video_gen.content.sources import ContentSourceManager
import json
import os

# 1. 从内容源获取内容
manager = ContentSourceManager()
items = manager.fetch_batch("history_events", topic="计算机", count=10)

# 2. 生成脚本并添加到队列
queue = SQLiteTaskQueue('video_tasks.db')

for i, item in enumerate(items):
    # 创建脚本文件
    script_data = {
        "meta": {
            "title": item.get('title', f"Video {i+1}"),
            "description": item.get('content', ''),
            "topic": "计算机历史"
        },
        "scenes": [
            {
                "scene_id": 1,
                "text": item.get('content', ''),
                "prompt": f"{item.get('title', '')}, 高质量，细节丰富",
                "duration_sec": 5
            }
        ]
    }
    
    script_path = f"./scripts/script_{i+1:03d}.json"
    os.makedirs("./scripts", exist_ok=True)
    with open(script_path, 'w', encoding='utf-8') as f:
        json.dump(script_data, f, ensure_ascii=False, indent=2)
    
    # 添加到队列
    queue.add_task(
        task_id=f"task_auto_{i+1}",
        script_path=script_path,
        title=item.get('title', f"Video {i+1}"),
        priority=PriorityLevel.NORMAL
    )

# 3. 启动工作节点
pool = create_worker_pool(num_workers=3, db_path='video_tasks.db')
pool.start()

print(f"已添加 {len(items)} 个任务，工作节点已启动")
```

## 核心模块说明

### SQLiteTaskQueue - 任务队列

```python
from video_gen.core.task_queue_sqlite import SQLiteTaskQueue, PriorityLevel

queue = SQLiteTaskQueue('video_tasks.db')

# 添加任务
queue.add_task(
    task_id="task_001",
    script_path="./scripts/video.json",
    title="我的视频",
    priority=PriorityLevel.HIGH  # URGENT/HIGH/NORMAL/LOW
)

# 获取统计
stats = queue.get_stats()
print(stats)
# {'total': 10, 'pending': 5, 'running': 2, 'completed': 3, ...}

# 取消任务
queue.cancel_task("task_001")

# 清理旧任务
queue.clear_old_tasks(days=30)
```

### MultiProcessWorkerPool - 工作节点池

```python
from video_gen.core.multi_process_worker import create_worker_pool

# 创建 3 个工作节点
pool = create_worker_pool(num_workers=3, db_path='video_tasks.db')

# 启动
pool.start()

# 查看状态
status = pool.get_status()
print(status)
# {'total_workers': 3, 'active_workers': 3, 'running': True}

# 获取完成结果
results = pool.get_results(timeout=1.0)
for r in results:
    print(f"任务完成：{r.task_id}, 成功={r.success}")

# 停止
pool.stop(timeout=30.0)
```

## 性能调优

### 调整 Worker 数量

根据 CPU 核心数调整:

```python
import multiprocessing
cpu_count = multiprocessing.cpu_count()
# 建议 Worker 数量 = CPU 核心数 - 1
num_workers = max(1, cpu_count - 1)

pool = create_worker_pool(num_workers=num_workers)
```

### API 速率限制

在 `optimization/image_optimization.py` 中调整:

```python
# 默认每分钟 10 次调用
rate_limit_calls = 10
rate_limit_window = 60
```

### 缓存优化

启用图片缓存可提升 40-60% 性能:

```python
from video_gen.optimization.image_optimization import OptimizedImageGenerator

gen = OptimizedImageGenerator(cache_enabled=True, cache_ttl_days=7)
```

## 监控与维护

### 查看任务状态

```python
queue = SQLiteTaskQueue('video_tasks.db')

# 获取所有待处理任务
pending = queue.get_tasks_by_status(TaskStatus.PENDING)

# 获取失败任务
failed = queue.get_tasks_by_status(TaskStatus.FAILED)

# 查看任务详情
task = queue.get_task("task_001")
print(task['error_message'])  # 如果有错误
```

### 日志查看

日志文件位置：`./logs/video_gen.log`

```bash
# 实时查看日志
tail -f ./logs/video_gen.log

# 查看错误日志
grep "ERROR" ./logs/video_gen.log
```

### 定期维护

```bash
# 每周清理一次旧任务
python3 -c "
from video_gen.core.task_queue_sqlite import SQLiteTaskQueue
q = SQLiteTaskQueue('video_tasks.db')
q.clear_old_tasks(days=7)
"

# 备份数据库
cp video_tasks.db video_tasks.db.backup.$(date +%Y%m%d)
```

## 故障排查

### 问题 1: 任务一直处于 pending 状态

**原因**: 工作节点未启动或已崩溃

**解决**:
```bash
# 检查工作节点状态
ps aux | grep worker

# 重启工作节点
python3 -c "
from video_gen.core.multi_process_worker import create_worker_pool
pool = create_worker_pool(num_workers=3, db_path='video_tasks.db')
pool.start()
"
```

### 问题 2: 任务频繁失败

**原因**: API 限流或网络问题

**解决**:
1. 检查 API Key 是否有效
2. 降低并发数 (`num_workers=1`)
3. 增加重试延迟

### 问题 3: 磁盘空间不足

**解决**:
```bash
# 清理输出目录
rm -rf ./output/*/temp_*

# 清理旧任务
python3 -c "
from video_gen.core.task_queue_sqlite import SQLiteTaskQueue
q = SQLiteTaskQueue('video_tasks.db')
q.clear_old_tasks(days=3)
"
```

## 常见问题 FAQ

**Q: 一天能生成多少个视频？**
A: 取决于配置，通常 3 个 Worker 可生成 50-150 个/天

**Q: 如何增加产能？**
A: 增加 Worker 数量或使用多台机器部署

**Q: 支持分布式部署吗？**
A: 当前版本为单机版，分布式版本计划中

**Q: 任务失败会自动重试吗？**
A: 是的，默认最多重试 5 次

**Q: 可以暂停和恢复吗？**
A: 可以，停止工作节点后，任务会保留在队列中，重启后继续

---

**版本**: v3.0  
**更新日期**: 2024 年
