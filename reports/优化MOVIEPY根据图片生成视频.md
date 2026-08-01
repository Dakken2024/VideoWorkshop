
用 MoviePy 生成一个“真实的电影效果”的片段，**关键不在于图片的“张数”，而在于你设定的“帧率”**。

帧率（FPS，Frames Per Second）决定了每秒需要多少张图片，两者共同决定了视频的时长和流畅度。

### 1. 核心公式：帧率 (FPS) 决定图片数量

图片数量、帧率和视频时长之间的关系很简单：
**图片总数 = 帧率 (FPS) × 视频时长 (秒)**

按照上面的要求，我要是想将Day 29使用新的方式来处理，如何拆解day 29的内容来生成那么多图片呢？

所以，你需要的图片数量完全取决于你想要多长的视频。

* 如果你想要一个 **1秒钟** 的视频，并且使用电影标准的 **24 fps**，那么你恰好需要 **24张图片**。
* 如果你想要一个 **5秒钟** 的视频，同样是24 fps，那么你就需要 **120张图片**。

### 2. “真实电影效果”的关键是什么？

想要达到“真实”和“电影感”，主要取决于以下两个因素：

* **帧率 (FPS) 的选择**：这是最核心的要素。电影行业的标准帧率是 **24 fps** 。这个帧率能在视觉流畅度和特有的“电影感”动态模糊之间取得最佳平衡，是创造真实感的基础。如果你使用更低的帧率（如15 fps或更低），视频就会看起来卡顿，像早期的幻灯片或GIF动画 。
* **每张图片的质量**：视频的“真实感”最终来自于每一帧画面本身。一张高质量、高分辨率、构图精美的图片，远比大量低质量图片更能营造出电影效果。

### 3. MoviePy 代码实现示例

在 MoviePy 中，你通常会使用 `ImageSequenceClip` 来将一系列图片转换为视频 。

```python
from moviepy import ImageSequenceClip

# 1. 准备一个按顺序排列的图片路径列表
# 确保你的图片文件名是排序好的，例如 frame_001.jpg, frame_002.jpg, ...
image_files = ["path/to/your/image_1.jpg", "path/to/your/image_2.jpg", ...]

# 或者，如果你的图片都在一个文件夹里，可以用文件夹路径
# image_folder = "path/to/your/image/folder"

# 2. 设置你想要的帧率 (例如电影标准 24 fps)
fps = 24

# 3. 创建视频剪辑
# 使用图片列表
clip = ImageSequenceClip(image_files, fps=fps)

# 如果使用文件夹，直接传入文件夹路径
# clip = ImageSequenceClip(image_folder, fps=fps)

# 4. (可选) 查看视频时长
print(f"生成的视频时长为: {clip.duration} 秒")

# 5. 导出视频
clip.write_videofile("my_movie.mp4", codec="libx264", audio_codec="aac")
```

### 4. 重要注意事项

为了让你的视频顺利生成并达到预期效果，有几点需要注意：

* **图片尺寸必须一致**：MoviePy 的 `ImageSequenceClip` 严格要求所有图片的尺寸（宽度和高度）完全相同。如果图片大小不一，程序会报错 。你需要提前用其他工具（如PIL库）将所有图片统一缩放到相同尺寸。
* **文件格式**：确保你使用的图片格式是 MoviePy 支持的，如 `.jpg`, `.png` 等 。
* **代码更新**：MoviePy 已经升级到 **2.0 版本**，与旧版本（v1）在代码写法上有一些重要区别 。上面的代码示例基于最新的 v2.0+ 版本。如果你在使用旧版本，语法会有所不同，建议参考官方更新指南进行迁移。

希望这些信息能帮你理清思路。如果你想了解如何在 MoviePy 中统一处理不同尺寸的图片，或者想添加背景音乐，我可以提供更具体的代码示例。



## 电影效果方案对比

| **方案**               | **图片数量**               | **时长**   | **成本** | **效果** | **推荐度** |
| ---------------------------- | -------------------------------- | ---------------- | -------------- | -------------- | ---------------- |
| **方案 A：经济实用**   | **42 张（每场景 3 张）**   | **150 秒** | **低**   | **良好** | **✅✅✅** |
| **方案 B：标准电影**   | **168 张（每场景 12 张）** | **150 秒** | **中**   | **优秀** | **✅✅**   |
| **方案 C：高成本电影** | **3360 张（24fps 全程）**  | **150 秒** | **极高** | **最佳** | **✅**     |

 **推荐方案 A** **：平衡成本与效果，使用动态过渡模拟电影感。**



## 电影效果生成脚本（增强版）


#!/usr/bin/env python3

# -*- coding: utf-8 -*-

"""
Saabor AI Builds - 电影效果视频生成器
方案：多帧图片 + 动态过渡 + 24fps 电影标准
"""

import asyncio
import os
import json
import requests
import random
import time
from pathlib import Path
from pydub import AudioSegment
from PIL import Image
import numpy as np

# MoviePy 2.0 导入

try:
    from moviepy import (
        AudioFileClip,
        concatenate_audioclips,
        concatenate_videoclips,
        CompositeVideoClip,
        TextClip,
        ImageClip,
        vfx,
        ImageSequenceClip
    )
    from moviepy.video.VideoClip import ColorClip
except ImportError:
    from moviepy.editor import (
        AudioFileClip,
        concatenate_audioclips,
        concatenate_videoclips,
        CompositeVideoClip,
        TextClip,
        ImageClip,
        ColorClip,
        ImageSequenceClip
    )
    from moviepy.video import fx as vfx

import edge_tts

# ================= 配置区域 =================

OUTPUT_DIR = "./output"
SCRIPT_FILE = "scripts.json"
FRAME_SIZE = (1080, 1920)  # 视频号竖屏标准
FPS = 24  # 电影标准帧率

# TTS 语音配置

VOICE_CONFIG = {
    'primary': 'zh-CN-XiaoxiaoNeural',
    'fallback': 'zh-CN-YunxiNeural',
    'rate': '+0%',
    'volume': '+0%'
}

os.makedirs(OUTPUT_DIR, exist_ok=True)

# ================= 日志工具 =================

def log(level, message):
    icons = {'INFO': '[INFO]', 'SUCCESS': '[SUCCESS]', 'WARNING': '[WARNING]', 'ERROR': '[ERROR]', 'DEBUG': '[DEBUG]'}
    try:
        print(f"{icons.get(level, '[INFO]')} {message}")
    except UnicodeEncodeError:
        safe_message = message.encode('ascii', 'ignore').decode('ascii')
        print(f"{icons.get(level, '[INFO]')} {safe_message}")

# ================= JSON 脚本加载 =================

def load_script_from_json(script_file):
    try:
        with open(script_file, 'r', encoding='utf-8') as f:
            script_data = json.load(f)

    meta = script_data.get('meta', {})
        project_name = meta.get('title', 'Untitled_Project')
        project_name = re.sub(r'[^\w\u4e00-\u9fa5]', '_', project_name)

    voice_setting = meta.get('voice_setting', VOICE_CONFIG['primary'])
        scenes = script_data.get('scenes', [])
        script_scenes = []

    for scene in scenes:
            script_scenes.append({
                "text": scene.get('text', ''),
                "prompt": scene.get('prompt', ''),
                "duration": scene.get('duration_sec', 5),
                "scene_id": scene.get('scene_id', 0),
                "frames_needed": scene.get('frames_needed', 3),
                "reference_url": scene.get('reference_url', ''),
                "note": scene.get('note', '')
            })

    return {
            'project_name': project_name,
            'voice': voice_setting,
            'scenes': script_scenes,
            'meta': meta
        }

    except Exception as e:
        log('ERROR', f'加载脚本失败：{e}')
        return None

# ================= 图片生成器（多帧版本） =================

class CinematicImageGenerator:
    """电影效果图片生成器 - 为每个场景生成多帧略有变化的图片"""

    def__init__(self):
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
        ]

    def generate_scene_frames(self, prompt, scene_id, frames_needed, output_dir):
        """为单个场景生成多帧图片（每帧略有变化）"""
        frame_files = []

    # 为每帧添加微小变化，模拟摄像机运动
        variations = [
            "slight zoom in, subtle camera movement",
            "slight pan left, smooth motion blur",
            "slight pan right, cinematic motion",
            "subtle lighting change, atmospheric",
            "slight focus shift, depth of field"
        ]

    for i in range(frames_needed):
            # 添加变化到 prompt
            variation = variations[i % len(variations)]
            varied_prompt = f"{prompt}, {variation}, frame {i+1} of {frames_needed}, continuous shot"

    frame_file = os.path.join(output_dir, f"scene_{scene_id:03d}_frame_{i:03d}.jpg")

    if self._generate_single_frame(varied_prompt, frame_file):
                frame_files.append(frame_file)
                log('DEBUG', f'场景 {scene_id} 帧 {i+1}/{frames_needed} 生成成功')
            else:
                # 如果生成失败，复制上一帧
                if frame_files:
                    import shutil
                    shutil.copy(frame_files[-1], frame_file)
                    frame_files.append(frame_file)
                    log('WARNING', f'场景 {scene_id} 帧 {i+1} 生成失败，使用上一帧')

    return frame_files

    def _generate_single_frame(self, prompt, output_file):
        """生成单帧图片（使用 Pollinations）"""
        try:
            encoded = requests.utils.quote(prompt)
            seed = random.randint(1, 9999)
            url = f"https://image.pollinations.ai/prompt/{encoded}?width=1080&height=1920&nologo=true&seed={seed}"

    headers = {
                'Accept': 'image/webp,image/apng,image/*,*/*;q=0.8',
                'User-Agent': random.choice(self.user_agents),
                'Referer': 'https://pollinations.ai/',
            }

    response = requests.get(url, headers=headers, timeout=45)

    if response.status_code == 200 and len(response.content) > 50000:
                with open(output_file, 'wb') as f:
                    f.write(response.content)

    # 统一图片尺寸
                self._resize_image(output_file, FRAME_SIZE)
                return True
        except Exception as e:
            log('DEBUG', f'生成失败：{str(e)[:50]}')

    return False

    def _resize_image(self, image_path, target_size):
        """统一图片尺寸"""
        try:
            img = Image.open(image_path)
            img = img.resize(target_size, Image.Resampling.LANCZOS)
            img.save(image_path, quality=95)
        except Exception as e:
            log('WARNING', f'图片调整失败：{e}')

# ================= 音频生成器 =================

class AudioGenerator:
    """分段音频生成器"""

    def__init__(self, voice_config=None):
        self.voice_config = voice_config or VOICE_CONFIG
        self.current_voice = self.voice_config['primary']

    async def generate_segment(self, text, output_file, scene_id=None):
        scene_info = f"场景 {scene_id}" if scene_id else "未知场景"
        clean_text = re.sub(r'<[^>]+>', '', text).strip()

    if not clean_text:
            return False

    try:
            communicate = edge_tts.Communicate(
                clean_text,
                voice=self.current_voice,
                rate=self.voice_config['rate'],
                volume=self.voice_config['volume']
            )
            await communicate.save(output_file)

    if os.path.exists(output_file) and os.path.getsize(output_file) > 1000:
                log('SUCCESS', f'{scene_info}: 音频生成成功')
                return True
        except Exception as e:
            log('WARNING', f'{scene_info}: 生成失败 - {str(e)[:80]}')

    return False

    async def generate_all_segments(self, scenes, output_dir):
        segment_files = []
        segment_durations = []

    for i, scene in enumerate(scenes):
            segment_file = os.path.join(output_dir, f"segment_{i:03d}.mp3")
            text = scene["text"]
            scene_id = scene.get("scene_id", i + 1)

    success = await self.generate_segment(text, segment_file, scene_id)

    if success and os.path.exists(segment_file):
                segment_files.append(segment_file)
                try:
                    audio_clip = AudioFileClip(segment_file)
                    segment_durations.append(audio_clip.duration)
                    audio_clip.close()
                except:
                    segment_durations.append(5.0)
            else:
                segment_files.append(None)
                segment_durations.append(5.0)

    return segment_files, segment_durations

    def concatenate_segments(self, segment_files, output_file):
        valid_segments = [f for f in segment_files if f and os.path.exists(f)]

    if not valid_segments:
            return False

    try:
            audio_clips = [AudioFileClip(f) for f in valid_segments]
            final_audio = concatenate_audioclips(audio_clips)
            final_audio.write_audiofile(output_file, logger=None)

    for clip in audio_clips:
                clip.close()

    return True
        except Exception as e:
            log('ERROR', f'音频拼接失败：{e}')
            return False

# ================= 电影效果视频合成器 =================

class CinematicVideoCompositor:
    """电影效果视频合成器 - 使用 ImageSequenceClip"""

    def__init__(self, output_dir, fps=24):
        self.output_dir = output_dir
        self.fps = fps

    def create_cinematic_video(self, audio_file, all_frame_files, scene_durations, output_file):
        """使用 ImageSequenceClip 创建电影效果视频"""
        log('INFO', '开始合成电影效果视频...')

    # 加载音频
        if not os.path.exists(audio_file):
            log('ERROR', f'音频文件不存在：{audio_file}')
            return False

    try:
            audio = AudioFileClip(audio_file)
            total_audio_duration = audio.duration
            log('INFO', f'音频时长：{total_audio_duration:.2f}秒')
        except Exception as e:
            log('ERROR', f'音频加载失败：{e}')
            return False

    # 验证所有图片存在且尺寸一致
        valid_frames = []
        for frame_path in all_frame_files:
            if os.path.exists(frame_path):
                try:
                    img = Image.open(frame_path)
                    if img.size == FRAME_SIZE:
                        valid_frames.append(frame_path)
                    else:
                        # 调整尺寸
                        img = img.resize(FRAME_SIZE, Image.Resampling.LANCZOS)
                        img.save(frame_path)
                        valid_frames.append(frame_path)
                except Exception as e:
                    log('WARNING', f'图片验证失败 {frame_path}: {e}')

    if not valid_frames:
            log('ERROR', '没有有效的图片帧')
            audio.close()
            return False

    log('INFO', f'有效图片帧数量：{len(valid_frames)}')
        log('INFO', f'帧率：{self.fps} fps')
        log('INFO', f'预计视频时长：{len(valid_frames) / self.fps:.2f}秒')

    try:
            # 使用 ImageSequenceClip 创建视频
            clip = ImageSequenceClip(valid_frames, fps=self.fps)

    # 设置视频时长与音频匹配
            if clip.duration < total_audio_duration:
                # 如果视频太短，延长最后一帧
                clip = clip.with_duration(total_audio_duration)
            elif clip.duration > total_audio_duration:
                # 如果视频太长，裁剪
                clip = clip.subclip(0, total_audio_duration)

    # 添加音频
            clip = clip.with_audio(audio)

    # 添加淡入淡出效果
            clip = clip.with_effects([vfx.FadeIn(1.0), vfx.FadeOut(1.0)])

    # 导出视频
            clip.write_videofile(
                output_file,
                codec='libx264',
                audio_codec='aac',
                bitrate='8000k',
                preset='medium',
                logger=None
            )

    # 清理资源
            audio.close()
            clip.close()

    log('SUCCESS', f'电影效果视频合成完成：{output_file}')
            return True

    except Exception as e:
            log('ERROR', f'视频合成失败：{e}')
            import traceback
            log('DEBUG', f'详细错误:\n{traceback.format_exc()}')
            return False

# ================= 主程序 =================

async def main():
    print("=" * 70)
    log('INFO', '🎬 Saabor AI Builds - 电影效果视频生成器')
    log('INFO', f'帧率：{FPS} fps | 图片尺寸：{FRAME_SIZE}')
    print("=" * 70)

    script_config = load_script_from_json(SCRIPT_FILE)
    if script_config is None:
        exit(1)

    project_name = script_config['project_name']
    scenes = script_config['scenes']
    meta = script_config['meta']

    log('INFO', f'项目：{project_name}')
    log('INFO', f'场景数：{len(scenes)}')
    log('INFO', f'预计总帧数：{sum(s.get("frames_needed", 3) for s in scenes)}')
    print("=" * 70)

    # 初始化组件
    image_gen = CinematicImageGenerator()
    audio_gen = AudioGenerator(VOICE_CONFIG)
    video_comp = CinematicVideoCompositor(OUTPUT_DIR, fps=FPS)

    # 步骤 1: 生成音频
    print("\n" + "=" * 70)
    log('INFO', '步骤 1/4: 生成音频片段')
    print("=" * 70)
    segment_files, segment_durations = await audio_gen.generate_all_segments(scenes, OUTPUT_DIR)

    # 步骤 2: 拼接音频
    print("\n" + "=" * 70)
    log('INFO', '步骤 2/4: 拼接音频')
    print("=" * 70)
    audio_output = os.path.join(OUTPUT_DIR, "voiceover.mp3")
    audio_gen.concatenate_segments(segment_files, audio_output)

    # 步骤 3: 生成多帧图片
    print("\n" + "=" * 70)
    log('INFO', '步骤 3/4: 生成多帧图片（电影效果）')
    print("=" * 70)
    all_frame_files = []
    for i, scene in enumerate(scenes):
        scene_id = scene.get('scene_id', i + 1)
        frames_needed = scene.get('frames_needed', 3)
        log('INFO', f'场景 {scene_id}: 生成 {frames_needed} 帧')

    frame_files = image_gen.generate_scene_frames(
            scene["prompt"],
            scene_id,
            frames_needed,
            OUTPUT_DIR
        )
        all_frame_files.extend(frame_files)

    log('INFO', f'总生成帧数：{len(all_frame_files)}')

    # 步骤 4: 合成电影效果视频
    print("\n" + "=" * 70)
    log('INFO', '步骤 4/4: 合成电影效果视频')
    print("=" * 70)
    video_output = os.path.join(OUTPUT_DIR, f"{project_name}_cinematic.mp4")
    video_comp.create_cinematic_video(audio_output, all_frame_files, segment_durations, video_output)

    # 完成报告
    print("\n" + "=" * 70)
    log('SUCCESS', '🎉 所有任务完成！')
    print("=" * 70)
    print(f"\n📁 输出目录：{os.path.abspath(OUTPUT_DIR)}")
    print(f"🎬 视频文件：{video_output}")
    print(f"🎵 音频文件：{audio_output}")
    print(f"🖼️ 总帧数：{len(all_frame_files)}")
    print(f"🎞️ 帧率：{FPS} fps")
    print(f"⏱️  视频时长：{len(all_frame_files) / FPS:.2f}秒")

    print("\n💡 后续建议:")
    print("   1. 导入剪映添加自动字幕")
    print("   2. 添加背景音乐（音量 10-15%）")
    print("   3. 手动替换关键历史图片（参考 reference_url）")
    print("   4. 导出 1080P 竖屏视频发布视频号")

    print("=" * 70)

if __name__ == "__main__":
    import re
    asyncio.run(main())
