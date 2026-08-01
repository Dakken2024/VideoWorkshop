# Video Workshop - 智能视频自动生成工具

[![Python](https://img.shields.io/badge/Python-3.8%2B-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen)](CONTRIBUTING.md)

Video Workshop 是一款开源的智能视频自动生成工具，能够将文章内容自动转换为带字幕、配音的专业视频。系统支持 AI 内容创作、智能图片生成、TTS 语音合成、视频合成等核心功能，提供图形界面和命令行两种使用方式。

## 功能特性

### 核心功能
- **一键视频生成** - 从脚本 JSON 自动完成音频、图片、视频合成，支持断点续传
- **AI 内容创作** - 集成 DeepSeek V4 Flash 大模型，支持主题搜索、文章生成、脚本转换
- **智能字幕系统** - 自动生成、检测、对齐、嵌入字幕，支持 SRT/ASS 格式
- **多语种语音合成** - 基于 edge-tts 的免费高音质语音合成，支持多种语言和角色
- **GPU 加速检测** - 自动检测 GPU 编码器，不可用时自动回退到 CPU

### 交互方式
- **图形界面 (GUI)** - 5 个功能标签页，适合非编程用户
- **命令行 (CLI)** - 完整的命令行接口，适合自动化集成
- **Python API** - 模块化编程接口，支持自定义工作流

### 技术特性
- 模块化架构，易于扩展和维护
- 集中配置管理，支持环境变量覆盖
- 完整的错误处理和自动恢复机制
- 44 个单元测试，核心功能覆盖率 100%

## 快速开始

### 环境要求

- **Python**: 3.8 或更高版本
- **FFmpeg**: 已安装并添加到系统 PATH
- **操作系统**: Windows 10/11（推荐）、Linux、macOS

### 安装

```bash
# 1. 克隆仓库
git clone https://github.com/yourusername/VideoWorkshop.git
cd VideoWorkshop

# 2. 安装依赖
pip install -r requirements.txt

# 3. 配置 API Key（可选）
# 复制配置模板并填写你的 API Key
cp video_gen/.env.example .env
```

### 启动 GUI

```bash
# 方式一：双击运行
run_gui.bat

# 方式二：命令行启动
python video_gen/gui_launcher.py
```

### 启动 CLI

```bash
# 系统诊断
python -m video_gen.cli diagnose

# 一键生成视频
python -m video_gen.cli generate -t "视频标题" -s scripts.json
```

## 使用指南

### 准备工作

1. **准备脚本文件** - 创建 `scripts.json`，包含场景列表和元信息
2. **配置 API** - 在 GUI 的"API 设置"标签页中配置 DeepSeek 等 API Key
3. **开始生成** - 选择"视频生成"标签页，点击"开始生成视频"

### 脚本格式

```json
{
  "meta": {
    "title": "视频标题",
    "description": "视频描述"
  },
  "scenes": [
    {
      "scene_id": 1,
      "text": "配音文本",
      "prompt": "图片生成提示词",
      "duration_sec": 5,
      "note": "场景说明"
    }
  ]
}
```

### 输出目录结构

```
output/
└── 202608/                          # 年月目录
    └── wo_de_shi_pin/               # 视频目录（拼音名）
        ├── scripts.json             # 脚本文件
        ├── voiceover.mp3            # 音频文件
        ├── scene_000.jpg            # 场景图片
        ├── ...
        └── wo_de_shi_pin.mp4        # 最终视频（含字幕）
```

## API 文档

### 命令行接口

| 命令 | 功能 | 示例 |
|------|------|------|
| `generate` | 完整视频生成 | `cli generate -t "标题" -s scripts.json` |
| `audio` | 仅生成音频 | `cli audio -s scripts.json -o ./output` |
| `images` | 仅生成图片 | `cli images -s scripts.json -o ./output` |
| `compose` | 合成视频 | `cli compose -s scripts.json -a audio.mp3 -i ./images -o ./output` |
| `subtitles` | 字幕导入 | `cli subtitles -v video.mp4 -s scripts.json` |
| `diagnose` | 系统诊断 | `cli diagnose` |

### Python API

```python
from video_gen.workflow import OptimizedWorkflow

# 创建工作流
workflow = OptimizedWorkflow()

# 一键生成
result = workflow.quick_generate(
    script_path="scripts.json",
    title="我的视频",
    output_dir="./output"
)

# 处理结果
if result["success"]:
    print(f"视频: {result['video_path']}")
else:
    print(f"错误: {result['errors']}")
```

### 配置管理

```python
from video_gen.config import AppConfig, DEFAULT_CONFIG

# 使用默认配置
config = DEFAULT_CONFIG

# 自定义配置
config.ai.enabled = True
config.ai.api_key = "your-api-key"
config.video.fps = 30
```

## 项目结构

```
VideoWorkshop/
├── video_gen/                  # 核心代码（模块化架构）
│   ├── ai/                     # AI 模块（DeepSeek、搜索、提示词）
│   ├── audio/                  # 音频生成模块
│   ├── core/                   # 核心引擎（流水线、状态管理）
│   ├── gui/                    # 图形界面（5 个标签页）
│   ├── image/                  # 图片生成模块
│   ├── tests/                  # 测试套件（44 个用例）
│   ├── utils/                  # 工具模块
│   ├── video/                  # 视频合成模块
│   ├── config.py               # 集中配置管理
│   ├── cli.py                  # 命令行入口
│   ├── workflow.py             # 精简工作流
│   └── gui_launcher.py         # GUI 启动器
├── legacy/                     # 遗留代码（原 v1 版本）
├── scripts/                    # 调试和测试脚本
├── reports/                    # 技术分析报告
├── articles/                   # 示例文章
├── docs/                       # 技术文档
│   └── plans/                  # 设计文档
├── readme.md                   # 本文件
├── CHANGELOG.md                # 更新日志
├── CONTRIBUTING.md             # 贡献指南
├── CODE_OF_CONDUCT.md          # 行为准则
├── LICENSE                     # 开源许可证
├── requirements.txt            # 依赖清单
├── run_gui.bat                 # Windows 启动脚本
└── setup_ffmpeg.bat            # FFmpeg 安装脚本
```

## 配置说明

### 必需依赖

| 组件 | 版本要求 | 说明 |
|------|----------|------|
| Python | 3.8+ | 运行环境 |
| FFmpeg | 最新版 | 视频处理，需添加到 PATH |
| moviepy | 2.0.0+ | 视频合成 |
| Pillow | 9.0.0+ | 图片处理 |
| edge-tts | 6.1.9+ | 语音合成 |
| pydub | - | 音频处理 |

### API 配置

| 服务 | 用途 | 获取方式 | 是否必需 |
|------|------|----------|----------|
| Pollinations | 图片生成 | 免费使用 | 是 |
| DeepSeek | AI 内容生成 | [platform.deepseek.com](https://platform.deepseek.com) | 否 |
| SerpAPI | 搜索引擎 | [serpapi.com](https://serpapi.com) | 否 |
| Tavily | AI 搜索 | [tavily.com](https://tavily.com) | 否 |

## 常见问题

### GPU 编码器错误
- 系统会自动检测并回退到 CPU 编码（libx264）
- 如手动指定，修改 `video_gen/video/encoder.py` 中的 `gpu_encoders` 列表

### 字幕未显示
- 使用 `--dry-run` 模式检查字幕文件是否生成
- 确认 FFmpeg 支持字幕滤镜

### 音频生成超时
- 系统会自动分段处理长文本
- 建议将脚本文本控制在 2000 字符以内

### 图片生成失败
- 系统会自动重试 3 次，失败后创建占位图
- 检查网络连接和 API 配置

## 贡献指南

我们欢迎所有形式的贡献！请参阅 [CONTRIBUTING.md](CONTRIBUTING.md) 了解详细信息。

## 许可证

本项目采用 MIT 许可证 - 详见 [LICENSE](LICENSE) 文件。

## 联系方式

- GitHub Issues: [提交问题](https://github.com/yourusername/VideoWorkshop/issues)
- 项目主页: [Video Workshop](https://github.com/yourusername/VideoWorkshop)

---

**版本**: v2.0 | **更新时间**: 2026-08-01 | **适用平台**: Windows / Linux / macOS