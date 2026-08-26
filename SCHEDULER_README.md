# 视频生成定时任务调度器 - 使用指南

## 概述

本调度器专为**每日批量生成 50-100 个视频号视频**的场景设计，解决了免费文生图 API 的速率限制和请求限制问题。

### 核心特性

1. **速率限制控制** - 令牌桶算法，精确控制 API 调用频率
2. **API 熔断器** - 连续失败时自动暂停，防止雪崩
3. **任务优先级队列** - 支持紧急任务插队处理
4. **断点续传** - 任务状态持久化，重启后自动恢复
5. **并发控制** - 可配置最大并发任务数，避免资源耗尽
6. **失败重试** - 智能退避策略，指数级延迟重试
7. **批量脚本生成** - 快速创建测试脚本

---

## 快速开始

### 1. 基本使用

```python
from video_gen.scheduler import VideoTaskScheduler, SchedulerConfig

# 创建调度器配置
config = SchedulerConfig(
    daily_target=80,           # 每日目标视频数 (50-100)
    max_concurrent=3,          # 最大并发任务数
    api_retry_limit=5,         # API 重试次数
    rate_limit_calls=10,       # 每分钟 API 调用次数
)

# 创建调度器
scheduler = VideoTaskScheduler(config=config)

# 添加任务
scheduler.add_task(
    script_path="scripts/video_001.json",
    title="我的视频 1",
    priority=TaskPriority.NORMAL
)

# 启动调度器
scheduler.start()

# 等待完成 (实际使用中应该用回调或轮询)
import time
while True:
    stats = scheduler.get_statistics()
    print(f"今日完成：{stats['today_completed']}/{daily_target}")
    time.sleep(60)
```

### 2. 批量添加任务

```python
from video_gen.scheduler import VideoTaskScheduler, TaskPriority

scheduler = VideoTaskScheduler()

# 批量添加某个目录下的所有脚本
scheduler.add_batch_tasks(
    scripts_dir="./scripts_pool",
    priority=TaskPriority.NORMAL
)

scheduler.start()
```

### 3. 生成测试脚本

```python
from video_gen.scheduler import BatchScriptGenerator

generator = BatchScriptGenerator(output_dir="./my_scripts")

# 生成 100 个测试脚本
script_paths = generator.generate_scripts(
    count=100,
    base_title="视频号视频",
    scene_count_range=(5, 15)  # 每个视频 5-15 个场景
)

print(f"已生成 {len(script_paths)} 个脚本文件")
```

### 4. 命令行使用

```bash
# 生成 100 个测试脚本
python -m video_gen.scheduler --generate-scripts 100

# 查看调度器状态
python -m video_gen.scheduler --status

# 启动调度器 (从指定目录加载脚本)
python -m video_gen.scheduler --scripts-dir ./scripts_pool --max-concurrent 3

# 自定义配置
python -m video_gen.scheduler \
    --daily-target 80 \
    --max-concurrent 3 \
    --output-dir ./output
```

---

## 架构设计

### 组件说明

```
┌─────────────────────────────────────────────────────────────┐
│                    VideoTaskScheduler                        │
├─────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ RateLimiter  │  │   Circuit    │  │   Priority   │      │
│  │  (速率限制)  │  │  Breaker     │  │    Queue     │      │
│  │              │  │  (熔断器)    │  │  (优先级队列)│      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │              Worker Threads (工作线程池)              │  │
│  │  Worker-0  │  Worker-1  │  Worker-2  │  ...          │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │  Persistent  │  │   Statistics │  │   Callback   │      │
│  │   Storage    │  │   Tracker    │  │   System     │      │
│  │  (状态持久化)│  │  (统计跟踪)  │  │  (回调通知)  │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
```

### 工作流程

```
1. 用户提交任务 → 2. 验证脚本 → 3. 加入优先级队列
                                          ↓
4. 工作线程唤醒 → 5. 检查速率限制 → 6. 检查熔断器
                                          ↓
7. 执行视频生成 ← OptimizedWorkflow
                                          ↓
8. 成功？→ 记录结果                      9. 失败？→ 重试计数
    ↓                                        ↓
  完成队列                              未达上限？→ 重新入队
    ↓                                        ↓
  更新统计                              达到上限？→ 失败队列
```

---

## 配置参数详解

### SchedulerConfig

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `daily_target` | int | 80 | 每日目标视频数 (50-100) |
| `max_concurrent` | int | 3 | 最大并发任务数 |
| `max_queue_size` | int | 200 | 最大队列大小 |
| `api_retry_limit` | int | 5 | API 重试次数 |
| `api_retry_delay` | float | 60.0 | API 重试延迟 (秒) |
| `rate_limit_calls` | int | 10 | 每分钟 API 调用次数限制 |
| `rate_limit_window` | int | 60 | 速率限制时间窗口 (秒) |
| `image_gen_interval` | float | 5.0 | 图片生成间隔 (秒) |
| `image_max_retries` | int | 3 | 图片生成最大重试次数 |
| `persist_enabled` | bool | True | 启用任务持久化 |
| `persist_interval` | int | 30 | 持久化间隔 (秒) |
| `state_file` | str | ".scheduler_state.json" | 状态文件名 |
| `output_base_dir` | str | "./output" | 输出目录 |

### TaskPriority

```python
class TaskPriority(Enum):
    URGENT = 0    # 紧急 - 立即处理
    HIGH = 1      # 高优先级
    NORMAL = 2    # 普通优先级
    LOW = 3       # 低优先级
```

---

## 应对 API 限制的策略

### 1. 多层速率限制

```python
# 应用层：调度器级别
config = SchedulerConfig(
    rate_limit_calls=10,      # 每分钟最多 10 次 API 调用
    rate_limit_window=60,     # 时间窗口 60 秒
)

# 图片生成层：已有实现
# video_gen/image/api_client.py 中的 APIRateLimiter
# - min_interval: 3 秒
# - max_interval: 15 秒
# - 指数退避策略

# API 服务层：Pollinations 多端点
# - gen.pollinations.ai (flux, flux-realism, turbo)
# - pollinations.ai (legacy)
# - 自动切换，提高成功率
```

### 2. 熔断器模式

```python
# 连续失败 5 次后触发熔断
api_breaker = APICircuitBreaker(
    failure_threshold=5,
    recovery_timeout=300  # 5 分钟后尝试恢复
)

# 状态转换:
# closed (正常) → open (熔断) → half-open (试探) → closed (恢复)
```

### 3. 智能重试策略

```python
# 指数退避 + 随机抖动
retry_delay = base_delay * (1 + retry_count) + random.uniform(0, 5)

# 示例:
# 第 1 次重试：60 秒
# 第 2 次重试：120 秒
# 第 3 次重试：180 秒
# ...
# 最大等待：300 秒
```

### 4. 并发控制

```python
# 推荐配置 (根据硬件和网络调整)
config = SchedulerConfig(
    max_concurrent=3,    # 同时处理 3 个视频
    max_queue_size=200,  # 队列最多 200 个任务
)

# 估算日产能:
# 假设每个视频平均 5 分钟 (含 API 等待)
# 3 并发 × 60 分钟 × 24 小时 ÷ 5 分钟 ≈ 864 个/天
# 考虑 API 限制，实际约 50-100 个/天
```

---

## 监控与统计

### 实时状态查询

```python
# 队列状态
status = scheduler.get_queue_status()
print(status)
# {
#     "queue_size": 45,
#     "active_tasks": 3,
#     "completed_tasks": 127,
#     "failed_tasks": 2,
#     "workers": 3,
#     "running": True
# }

# 详细统计
stats = scheduler.get_statistics()
print(stats)
# {
#     "total_submitted": 150,
#     "total_completed": 127,
#     "total_failed": 2,
#     "total_retried": 21,
#     "today_start": "2026-08-26",
#     "today_completed": 45,
#     "success_rate": 98.44
# }
```

### 任务状态跟踪

```python
# 查询单个任务
task_info = scheduler.get_task_status("task_20260826143000_1234")
print(task_info)
# {
#     "id": "task_20260826143000_1234",
#     "title": "我的视频 1",
#     "state": "completed",
#     "created_at": "2026-08-26T14:30:00",
#     "completed_at": "2026-08-26T14:35:23",
#     "retry_count": 0,
#     "output_dir": "./output/202608/wo_de_shi_pin_1"
# }
```

### 回调通知

```python
def on_task_update(task):
    """任务状态变更回调"""
    print(f"任务 {task.id} 状态变更为：{task.state.value}")
    
    if task.state == TaskState.COMPLETED:
        # 发送通知、上传到服务器等
        send_notification(f"视频完成：{task.title}")
    elif task.state == TaskState.FAILED:
        # 记录错误、告警等
        log_error(f"视频失败：{task.title}, 错误：{task.error_message}")

scheduler.register_callback(on_task_update)
```

---

## 最佳实践

### 1. 生产环境部署

```python
# production_scheduler.py
import logging
from video_gen.scheduler import VideoTaskScheduler, SchedulerConfig

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('scheduler.log'),
        logging.StreamHandler()
    ]
)

# 保守配置 (稳定优先)
config = SchedulerConfig(
    daily_target=60,           # 保守目标
    max_concurrent=2,          # 低并发
    api_retry_limit=7,         # 更多重试机会
    api_retry_delay=90.0,      # 更长延迟
    rate_limit_calls=8,        # 更严格的速率限制
    persist_interval=10,       # 更频繁的持久化
)

scheduler = VideoTaskScheduler(config=config)

# 注册告警回调
def on_critical_event(task):
    if task.state == TaskState.FAILED and task.retry_count >= 5:
        # 发送告警邮件/短信
        send_alert(f"关键任务失败：{task.title}")

scheduler.register_callback(on_critical_event)

# 启动
scheduler.start()

# 守护进程
try:
    while True:
        time.sleep(60)
        stats = scheduler.get_statistics()
        
        # 动态调整并发 (可选)
        if stats['success_rate'] < 80:
            logger.warning("成功率过低，考虑降低并发")
        
except KeyboardInterrupt:
    scheduler.stop(wait=True)
```

### 2. 脚本预处理流水线

```python
# 批量生成并优化脚本
from video_gen.scheduler import BatchScriptGenerator
from video_gen.ai.script_generator import ScriptGenerator

# 1. 使用 AI 生成高质量脚本
ai_gen = ScriptGenerator()
topics = ["科技前沿", "生活技巧", "历史故事", ...]  # 100 个主题

for i, topic in enumerate(topics):
    script = ai_gen.generate_script(topic=topic)
    save_script(script, f"./scripts/script_{i:03d}.json")

# 2. 或者直接生成测试脚本
batch_gen = BatchScriptGenerator()
batch_gen.generate_scripts(count=100)

# 3. 批量添加到调度器
scheduler = VideoTaskScheduler()
scheduler.add_batch_tasks("./scripts")
scheduler.start()
```

### 3. 分布式部署 (多机协作)

```python
# 在多台机器上部署，共享脚本池
# Machine-1
config1 = SchedulerConfig(
    max_concurrent=3,
    output_base_dir="./output_node1",
    state_file=".scheduler_state_node1.json",
)
scheduler1 = VideoTaskScheduler(config1)
scheduler1.add_batch_tasks("./shared_scripts/part1")

# Machine-2
config2 = SchedulerConfig(
    max_concurrent=3,
    output_base_dir="./output_node2",
    state_file=".scheduler_state_node2.json",
)
scheduler2 = VideoTaskScheduler(config2)
scheduler2.add_batch_tasks("./shared_scripts/part2")

# 总产能 = 单机产能 × 机器数量
```

---

## 故障排查

### 常见问题

**Q1: 任务一直处于 pending 状态**
- 检查工作线程是否启动：`scheduler.worker_count > 0`
- 检查队列是否已满：`scheduler.get_queue_status()['queue_size']`
- 查看日志是否有异常

**Q2: API 调用频繁失败**
- 降低 `rate_limit_calls` (如从 10 降到 5)
- 增加 `api_retry_delay` (如从 60 秒增加到 120 秒)
- 减少 `max_concurrent` (如从 3 降到 2)

**Q3: 重启后任务丢失**
- 确认 `persist_enabled=True`
- 检查 `.scheduler_state.json` 文件是否存在
- 查看日志中的持久化记录

**Q4: 内存占用过高**
- 减少 `max_queue_size`
- 定期清理 `completed_tasks` 和 `failed_tasks` 列表
- 增加持久化频率

---

## 性能估算

### 理论产能

假设条件:
- 每个视频平均 10 个场景
- 每个场景图片生成：平均 10 秒 (含 API 等待)
- 音频生成：平均 30 秒
- 视频合成：平均 60 秒
- 单视频总耗时：约 5-8 分钟

```
日产能估算 (单节点):
并发数 × (60 分钟 × 24 小时) ÷ 单视频耗时

2 并发：2 × 1440 ÷ 6 ≈ 480 个/天 (理想情况)
3 并发：3 × 1440 ÷ 6 ≈ 720 个/天 (理想情况)

考虑 API 限制和失败重试:
实际产能 ≈ 理论产能 × 0.2-0.3
实际产能 ≈ 50-100 个/天 (符合需求)
```

### 扩展建议

如需更高产能:
1. 增加并发数 (需要更强的 CPU/GPU)
2. 多节点分布式部署
3. 使用付费 API 服务 (更高的速率限制)
4. 本地部署文生图模型 (如 Stable Diffusion)

---

## 许可证

MIT License - 与原项目保持一致
