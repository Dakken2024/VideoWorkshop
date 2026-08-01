# Video Workshop GUI 设计方案

## 概述
为 `video_gen` 模块开发图形界面，降低非编程用户使用门槛，集成 AI 内容创作、搜索、API 配置等功能。

## 目录结构
```
video_gen/
├── ai/                      # AI 集成模块（新增）
│   ├── __init__.py
│   ├── deepseek.py          # DeepSeek V4 flash 客户端
│   ├── search.py            # 搜索集成（SerpAPI + Tavily）
│   ├── prompts.py           # 平台预设系统提示词
│   └── script_generator.py  # 文章→scripts.json 生成器
│
├── gui/                     # GUI 模块（新增）
│   ├── __init__.py
│   ├── app.py              # 主窗口
│   ├── tab_home.py         # 首页
│   ├── tab_content.py      # 内容创作
│   ├── tab_generate.py     # 视频生成
│   ├── tab_settings.py     # API 设置
│   ├── tab_history.py      # 历史记录
│   └── widgets.py          # 通用组件
│
├── config.py               # 扩展配置
└── 现有模块不变
```

## 配置扩展
- `AIConfig`: AI 大模型配置（多服务商、模块开关）
- `SearchConfig`: 搜索服务（SerpAPI + Tavily）
- `ImageAPIConfig`: 文生图 API（多服务商配置）

## AI 模块
- `deepseek.py`: OpenAI 兼容接口封装
- `search.py`: 统一搜索（SerpAPI/Tavily 自动切换）
- `prompts.py`: 微信公众号/知识科普平台预设
- `script_generator.py`: 搜索→AI→scripts.json 流水线

## GUI 界面
5 个标签页：首页、内容创作、视频生成、API 设置、历史记录

## 技术栈
- GUI: Tkinter（原生）
- AI: OpenAI 兼容接口
- 搜索: SerpAPI + Tavily