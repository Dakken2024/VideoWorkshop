# VideoWorkshop 批量视频生成系统 - 完整使用指南

## 目录

1. [概述](#概述)
2. [系统架构](#系统架构)
3. [核心功能](#核心功能)
4. [快速开始](#快速开始)
5. [详细配置](#详细配置)
6. [解耦设计说明](#解耦设计说明)
7. [最佳实践](#最佳实践)
8. [故障排查](#故障排查)

---

## 概述

本系统为 VideoWorkshop 项目新增的**批量视频自动生成解决方案**，专门解决以下需求：

1. **每日批量生产**：支持每天自动生成 50-100 个视频号视频
2. **API 速率限制应对**：多层限流机制，避免免费 API 被封禁
3. **内容来源多样化**：解耦设计，支持历史事件、科技新闻、趣味知识等多种内容源
4. **不影响核心逻辑**：完全独立的模块设计，与原有单视频生成流程零耦合

### 适用场景

- 视频号/抖音批量运营
- 自动化内容工厂
- 历史上的今天系列视频
- 科技新闻快讯视频
- 趣味知识科普视频

---

## 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                    用户层 (User Layer)                       │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐          │
│  │  CLI 工具    │  │  GUI 界面    │  │  Python API │          │
│  └─────────────┘  └─────────────┘  └─────────────┘          │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                  调度器层 (Scheduler Layer)                   │
│  ┌─────────────────────────────────────────────────────┐    │
│  │           VideoTaskScheduler                         │    │
│  │  - 任务队列管理   - 速率限制   - 熔断器              │    │
│  │  - 并发控制       - 断点续传   - 失败重试            │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                  内容源层 (Content Layer)                    │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐          │
│  │HistoryEvent │  │  TechNews   │  │  FunFact    │          │
│  │   Source    │  │   Source    │  │   Source    │          │
│  └─────────────┘  └─────────────┘  └─────────────┘          │
│  ┌─────────────────────────────────────────────────────┐    │
│  │         ContentSourceManager (统一接口)              │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                 AI 生成层 (AI Generation Layer)               │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐          │
│  │ScriptGen    │  │  Search     │  │  DeepSeek   │          │
│  │ Generator   │  │  Manager    │  │  Client     │          │
│  └─────────────┘  └─────────────┘  └─────────────┘          │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                核心引擎层 (Core Engine Layer)                 │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐          │
│  │  Pipeline   │  │   Audio     │  │   Image     │          │
│  │             │  │ Generator   │  │ Generator   │          │
│  └─────────────┘  └─────────────┘  └─────────────┘          │
│  ┌─────────────┐  ┌─────────────┐                            │
│  │   Video     │  │ Subtitle    │                            │
│  │ Compositor  │  │ Importer    │                            │
│  └─────────────┘  └─────────────┘                            │
└─────────────────────────────────────────────────────────────┘
```

### 关键特性

| 层级 | 功能 | 独立性 |
|------|------|--------|
| 调度器层 | 任务调度、限流、重试 | 完全独立，不修改核心代码 |
| 内容源层 | 内容获取、缓存、适配 | 插件化设计，可无限扩展 |
| AI 生成层 | 脚本生成、搜索 | 复用现有模块 |
| 核心引擎层 | 音视频处理 | 保持原有逻辑不变 |

---

## 核心功能

### 1. 定时任务调度器 (`video_gen/scheduler.py`)

#### 功能特性

- ✅ **速率限制**：令牌桶算法，精确控制 API 调用频率
- ✅ **熔断器**：连续失败自动暂停，防止雪崩效应
- ✅ **优先级队列**：URGENT > HIGH > NORMAL > LOW
- ✅ **断点续传**：每 30 秒持久化状态，重启自动恢复
- ✅ **并发控制**：可配置最大并发数（默认 3）
- ✅ **智能重试**：指数退避策略（60s → 300s）
- ✅ **批量脚本生成**：一键生成测试脚本

#### 核心类

```python
class VideoTaskScheduler:
    - add_task()          # 添加单个任务
    - add_batch_tasks()   # 批量添加任务
    - start()             # 启动调度器
    - stop()              # 停止调度器
    - get_statistics()    # 获取统计信息

class RateLimiter:
    - acquire()           # 获取令牌（阻塞/非阻塞）
    - get_wait_time()     # 获取等待时间

class APICircuitBreaker:
    - record_success()    # 记录成功
    - record_failure()    # 记录失败
    - can_proceed()       # 检查是否可继续
```

### 2. 内容源管理器 (`video_gen/content/sources.py`)

#### 内置内容源

| 内容源 | 名称 | 支持类型 | 说明 |
|--------|------|----------|------|
| 历史事件 | `history_events` | history_event, tech_history | 历史上的今天科技事件 |
| 科技新闻 | `tech_news` | tech_news, ai_news | 最新科技动态 |
| 趣味知识 | `fun_facts` | fun_fact, trivia | 科学趣事、冷知识 |
| 自定义 API | `custom_api` | custom | 用户自定义 API |

#### 核心接口

```python
class ContentSource(ABC):
    @property
    def name(self) -> str                    # 内容源名称
    @property
    def supported_types(self) -> List[str]   # 支持的内容类型
    
    def fetch(self, topic, **kwargs)         # 获取单个内容
    def fetch_batch(self, topic, count)      # 批量获取内容
```

---

## 快速开始

### 方案一：命令行快速启动（推荐新手）

#### 步骤 1：生成测试脚本

```bash
# 生成 100 个测试脚本文件
cd /workspace
python -m video_gen.scheduler --generate-scripts 100
```

#### 步骤 2：启动调度器

```bash
# 启动调度器，最大并发 3 个任务
python -m video_gen.scheduler \
    --scripts-dir ./scripts_batch \
    --max-concurrent 3 \
    --daily-target 80
```

#### 步骤 3：查看状态

```bash
# 新开一个终端查看实时状态
python -m video_gen.scheduler --status
```

### 方案二：Python API 编程使用（推荐开发者）

#### 示例 1：基本使用

```python
from video_gen.scheduler import VideoTaskScheduler, SchedulerConfig

# 创建调度器配置
config = SchedulerConfig(
    daily_target=80,           # 每日目标 80 个视频
    max_concurrent=3,          # 最大 3 个任务并发
    rate_limit_calls=10,       # 每分钟最多 10 次 API 调用
    api_retry_limit=5,         # 失败重试 5 次
)

# 创建调度器
scheduler = VideoTaskScheduler(config=config)

# 批量添加任务
scheduler.add_batch_tasks("./scripts_pool", priority=TaskPriority.NORMAL)

# 启动调度器
scheduler.start()

# 等待完成（或运行主循环）
try:
    while True:
        time.sleep(60)
        stats = scheduler.get_statistics()
        print(f"今日完成：{stats['today_completed']}/{config.daily_target}")
except KeyboardInterrupt:
    scheduler.stop()
```

#### 示例 2：结合内容源自动生成

```python
from video_gen.content.sources import ContentSourceManager, HistoryEventSource
from video_gen.ai.script_generator import ScriptGenerator
from video_gen.scheduler import VideoTaskScheduler, SchedulerConfig, TaskPriority
import os

# 1. 初始化内容源管理器
content_mgr = ContentSourceManager()

# 2. 批量获取历史事件内容（50 个）
contents = content_mgr.fetch_batch(
    source_name="history_events",
    topic="科技",
    count=50
)

print(f"获取到 {len(contents)} 条历史事件")

# 3. 为每个内容生成脚本并保存
script_dir = "./scripts_auto"
os.makedirs(script_dir, exist_ok=True)

generator = ScriptGenerator()

for i, content in enumerate(contents):
    try:
        # 使用 AI 生成完整脚本
        result = generator.generate(
            topic=f"{content.title} - {content.summary}",
            platform="short_video",  # 短视频风格
            extra_prompt=f"基于这个历史事件创作一个有趣的短视频脚本"
        )
        
        if result["success"]:
            # 保存脚本文件
            script_path = os.path.join(script_dir, f"script_{i+1:03d}.json")
            
            from video_gen.utils.file_utils import safe_write_json
            safe_write_json(script_path, result["scripts_json"])
            
            print(f"[{i+1}/{len(contents)}] 脚本已生成：{script_path}")
        else:
            print(f"[{i+1}/{len(contents)}] 脚本生成失败：{result['error']}")
    
    except Exception as e:
        print(f"[{i+1}/{len(contents)}] 异常：{e}")
    
    # 避免请求过快
    if (i + 1) % 5 == 0:
        time.sleep(2.0)

# 4. 创建调度器并添加所有脚本
config = SchedulerConfig(daily_target=50, max_concurrent=3)
scheduler = VideoTaskScheduler(config=config)

scheduler.add_batch_tasks(script_dir, priority=TaskPriority.HIGH)

# 5. 启动调度器
scheduler.start()
print("调度器已启动，开始批量生成视频...")
```

#### 示例 3：自定义内容源

```python
from video_gen.content.sources import (
    ContentSource, ContentItem, ContentSourceManager
)
import hashlib

class MyCustomSource(ContentSource):
    """自定义内容源示例：从数据库读取"""
    
    @property
    def name(self):
        return "my_database"
    
    @property
    def supported_types(self):
        return ["custom_db"]
    
    def fetch(self, topic, **kwargs):
        # 这里可以连接你的数据库
        # SELECT * FROM contents WHERE topic = ?
        return ContentItem(
            id="db_001",
            title="从数据库获取的内容",
            topic=topic,
            content_type="custom_db",
            summary="这是一个示例摘要",
            details="详细内容...",
            source="my_database",
        )
    
    def fetch_batch(self, topic, count, **kwargs):
        items = []
        for i in range(count):
            item = self.fetch(f"{topic}_{i}")
            if item:
                items.append(item)
        return items

# 注册自定义内容源
manager = ContentSourceManager()
manager.register(MyCustomSource())

# 使用自定义内容源
contents = manager.fetch_batch("my_database", topic="科技", count=20)
```

### 方案三：GUI 界面使用（待开发）

目前 GUI 尚未集成批量调度功能，计划在未来版本中添加。

---

## 详细配置

### 调度器配置参数

```python
@dataclass
class SchedulerConfig:
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
```

### 速率限制配置建议

| API 服务 | 免费额度 | 建议配置 |
|----------|----------|----------|
| Pollinations | 无限制（但可能限流） | `rate_limit_calls=10` |
| edge-tts | 免费 | `rate_limit_calls=20` |
| DeepSeek | 按 token 计费 | `rate_limit_calls=5` |
| Tavily | 100 次/月 | `rate_limit_calls=2` |

### 并发数配置建议

| 硬件配置 | 建议并发数 | 预计日产能 |
|----------|------------|------------|
| 4 核 8G | 2-3 | 50-80 个 |
| 8 核 16G | 4-6 | 100-150 个 |
| 16 核 32G | 8-10 | 200-300 个 |

---

## 解耦设计说明

### 为什么采用解耦设计？

1. **保护核心逻辑**：批量调度是新增需求，不应影响原有单视频生成流程
2. **易于维护**：各模块职责清晰，修改一处不影响其他
3. **可扩展性**：新增内容源无需修改调度器和核心引擎
4. **可测试性**：每个模块可独立测试

### 模块依赖关系

```
scheduler.py (调度器)
    │
    ├─→ workflow.py (工作流) ← 复用现有模块
    │
    └─→ content/sources.py (内容源) ← 新增模块
            │
            └─→ ai/search.py (搜索) ← 复用现有模块
```

### 如何确保不影响核心逻辑？

1. **零修改原则**：不对 `video_gen/core/`、`video_gen/video/`、`video_gen/audio/` 等核心目录做任何修改
2. **独立入口**：调度器有独立的 CLI 入口 (`python -m video_gen.scheduler`)
3. **可选依赖**：内容源模块完全可选，不使用批量功能时无需加载
4. **配置隔离**：调度器配置 (`SchedulerConfig`) 与应用配置 (`AppConfig`) 分离

---

## 最佳实践

### 1. 应对 API 限流的多层策略

```
应用层 (调度器)
    ↓ RateLimiter (令牌桶)
组件层 (图片生成器)
    ↓ APIRateLimiter (已有实现)
服务端 (Pollinations)
    ↓ 多端点自动切换 (已有实现)
熔断器
    ↓ 连续失败自动暂停
```

### 2. 内容获取优化

```python
# ❌ 错误做法：一次性获取所有内容
contents = manager.fetch_batch("history_events", count=100)

# ✅ 正确做法：分批获取，加入延迟
all_contents = []
for batch in range(0, 100, 20):
    batch_contents = manager.fetch_batch("history_events", count=20)
    all_contents.extend(batch_contents)
    time.sleep(5.0)  # 每批之间延迟 5 秒
```

### 3. 脚本预生成策略

```python
# 提前一天生成好第二天的脚本
def pre_generate_scripts():
    content_mgr = ContentSourceManager()
    generator = ScriptGenerator()
    
    # 获取明天的日期
    tomorrow = datetime.now() + timedelta(days=1)
    
    # 生成 80 个脚本
    for i in range(80):
        content = content_mgr.fetch(
            "history_events",
            month=tomorrow.month,
            day=tomorrow.day
        )
        # ... 生成脚本并保存
```

### 4. 监控和告警

```python
def check_scheduler_health(scheduler):
    stats = scheduler.get_statistics()
    
    # 检查成功率
    if stats["success_rate"] < 80:
        send_alert("成功率低于 80%")
    
    # 检查今日进度
    if stats["today_completed"] < stats["daily_target"] * 0.5:
        current_hour = datetime.now().hour
        if current_hour > 12:  # 中午检查
            send_alert("今日进度不足 50%")
    
    # 检查失败任务数
    if len(scheduler.failed_tasks) > 10:
        send_alert("失败任务过多")
```

---

## 故障排查

### 常见问题 1：API 调用过于频繁被限流

**症状**：日志中出现大量 "429 Too Many Requests" 错误

**解决方案**：
```python
config = SchedulerConfig(
    rate_limit_calls=5,      # 降低为每分钟 5 次
    api_retry_delay=120.0,   # 增加重试延迟到 2 分钟
)
```

### 常见问题 2：任务堆积处理不完

**症状**：队列中任务越来越多，处理速度跟不上

**解决方案**：
1. 增加并发数：`max_concurrent=6`
2. 减少每日目标：`daily_target=50`
3. 检查是否有任务卡住：`scheduler.get_queue_status()`

### 常见问题 3：重启后任务丢失

**症状**：程序重启后，之前的任务不见了

**解决方案**：
1. 确保持久化启用：`persist_enabled=True`
2. 检查状态文件是否存在：`.scheduler_state.json`
3. 手动恢复：从状态文件加载任务

### 常见问题 4：内容源获取失败

**症状**：`fetch_batch` 返回空列表

**解决方案**：
1. 检查搜索 API 配置（Tavily/SerpAPI）
2. 查看缓存目录：`./.content_cache/history`
3. 使用备用内容源：切换到 `tech_news` 或 `fun_facts`

---

## 性能估算

### 单节点产能估算

| 配置 | 并发数 | 理论产能/天 | 实际产能/天 |
|------|--------|-------------|-------------|
| 低配 | 2 | 480 | 50-80 |
| 中配 | 3 | 720 | 80-120 |
| 高配 | 6 | 1440 | 150-200 |

**说明**：
- 理论产能 = 并发数 × 24 小时 × 60 分钟 ÷ 单视频耗时 (约 5 分钟)
- 实际产能考虑了 API 限流、失败重试、内容获取等因素

### 多节点分布式部署

如需更高产能，可部署多个节点：

```
节点 1 (调度器) → 分配任务 → 节点 2、3、4 (工作节点)
```

每个工作节点运行独立的调度器，共享同一个脚本池。

---

## 总结

本系统通过**解耦设计**实现了批量视频自动生成，核心优势：

1. ✅ **零侵入**：不影响原有核心逻辑
2. ✅ **易扩展**：插件化内容源设计
3. ✅ **高可靠**：多层限流 + 熔断 + 重试
4. ✅ **易使用**：CLI/API 双入口

如需进一步定制或遇到问题，请查阅源码或提交 Issue。
