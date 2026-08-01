#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
绕过pydub的音频拼接方案
直接使用edge-tts生成完整音频
"""

import asyncio
import edge_tts
import os
import json
from pathlib import Path

def load_script_config(script_file="scripts.json"):
    """加载脚本配置"""
    try:
        with open(script_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"❌ 加载脚本文件失败: {e}")
        return None

async def generate_complete_audio(scenes, output_file, voice="zh-CN-XiaoxiaoNeural"):
    """直接生成完整音频，跳过分段拼接"""
    
    print("🎵 直接生成完整音频...")
    
    # 合并所有场景文本
    full_text = ""
    for scene in scenes:
        text = scene['text']
        # 在每个场景后添加适当的停顿
        if text.endswith(('。', '！', '？')):
            full_text += text + "<break time='1.0s'/>"
        elif text.endswith('，'):
            full_text += text + "<break time='0.5s'/>"
        else:
            full_text += text + "<break time='0.3s'/>"
    
    print(f"📝 合并文本长度: {len(full_text)} 字符")
    print(f"📊 场景数量: {len(scenes)} 个")
    
    try:
        # 使用edge-tts直接生成完整音频
        communicate = edge_tts.Communicate(
            text=full_text,
            voice=voice,
            rate="+0%",
            volume="+0%"
        )
        
        print("🔊 正在生成完整音频...")
        await communicate.save(output_file)
        
        if os.path.exists(output_file):
            file_size = os.path.getsize(output_file)
            print(f"✅ 完整音频生成成功: {output_file}")
            print(f"💾 文件大小: {file_size:,} bytes")
            return True
        else:
            print("❌ 音频文件未生成")
            return False
            
    except Exception as e:
        print(f"❌ 音频生成失败: {e}")
        return False

def copy_existing_images():
    """复制已存在的图片文件"""
    print("🖼️  处理图片文件...")
    
    # 检查已存在的图片
    existing_images = []
    for i in range(14):  # 14个场景
        img_path = f"./output/scene_{i:03d}.jpg"
        if os.path.exists(img_path):
            existing_images.append(img_path)
            print(f"  ✓ 找到: {os.path.basename(img_path)}")
        else:
            # 如果图片不存在，创建占位图
            placeholder_path = f"./output/placeholder_{i:03d}.jpg"
            create_placeholder_image(placeholder_path, i+1)
            existing_images.append(placeholder_path)
            print(f"  ○ 创建占位图: {os.path.basename(placeholder_path)}")
    
    return existing_images

def create_placeholder_image(filepath, scene_num):
    """创建占位图片"""
    try:
        from PIL import Image, ImageDraw, ImageFont
        import random
        
        # 创建空白图片
        width, height = 1080, 1920  # 9:16 竖屏比例
        img = Image.new('RGB', (width, height), color=(
            random.randint(100, 200),
            random.randint(100, 200), 
            random.randint(100, 200)
        ))
        
        draw = ImageDraw.Draw(img)
        
        # 添加文字
        try:
            # 尝试使用系统字体
            font = ImageFont.truetype("arial.ttf", 60)
        except:
            font = ImageFont.load_default()
        
        text = f"Scene {scene_num}\nPlaceholder Image"
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        
        x = (width - text_width) // 2
        y = (height - text_height) // 2
        
        draw.text((x, y), text, fill=(255, 255, 255), font=font)
        
        # 保存图片
        img.save(filepath, 'JPEG', quality=85)
        
    except Exception as e:
        print(f"  创建占位图失败: {e}")
        # 创建最小的占位文件
        with open(filepath, 'wb') as f:
            f.write(b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00H\x00H\x00\x00\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t\x08\n\x0c\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a\x1f\x1e\x1d\x1a\x1c\x1c $.\' ",#\x1c\x1c(7),01444\x1f\'9=82<.342\xff\xc0\x00\x11\x08\x00\xf0\x00\x8c\x03\x01\x11\x00\x02\x11\x01\x03\x11\x01\xff\xdd\x00\x04\x00\x00\xff\xc4\x00\x1f\x00\x00\x01\x05\x01\x01\x01\x01\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00\x01\x02\x03\x04\x05\x06\x07\x08\x09\x0a\x0b\xff\xc4\x00\xb5\x10\x00\x02\x01\x03\x03\x02\x04\x03\x05\x05\x04\x04\x00\x00\x01}\x01\x02\x03\x00\x04\x11\x05\x12!1Q\x06\x13aq\x07"2\x81\x91\xa1\x08#B\xb1\xc1\x14R\xd1\xf0\x15$34r\xb2\xc2\x16\x17\x18\x19\x1a%&\'()*56789:DEFGHIJSTUVWXYZcdefghijstuvwxyz\x83\x84\x85\x86\x87\x88\x89\x8a\x92\x93\x94\x95\x96\x97\x98\x99\x9a\xa2\xa3\xa4\xa5\xa6\xa7\xa8\xa9\xaa\xb2\xb3\xb4\xb5\xb6\xb7\xb8\xb9\xba\xc2\xc3\xc4\xc5\xc6\xc7\xc8\xc9\xca\xd2\xd3\xd4\xd5\xd6\xd7\xd8\xd9\xda\xe1\xe2\xe3\xe4\xe5\xe6\xe7\xe8\xe9\xea\xf1\xf2\xf3\xf4\xf5\xf6\xf7\xf8\xf9\xfa\xff\xda\x00\x0c\x03\x01\x00\x02\x11\x03\x11\x00?\x00\xff\xd9')

async def main():
    print("=" * 60)
    print("🚀 绕过pydub的完整音频生成方案")
    print("=" * 60)
    
    # 加载脚本
    script_config = load_script_config()
    if not script_config:
        return
    
    project_name = script_config['meta']['title']
    scenes = script_config['scenes']
    voice = script_config['meta'].get('voice_setting', 'zh-CN-XiaoxiaoNeural')
    
    print(f"📋 项目: {project_name}")
    print(f"🎤 语音: {voice}")
    print(f"🎬 场景: {len(scenes)} 个")
    print("=" * 60)
    
    # 确保输出目录存在
    output_dir = "./output"
    os.makedirs(output_dir, exist_ok=True)
    
    # 步骤1: 生成完整音频
    print("\n🎵 步骤 1/3: 生成完整音频")
    print("-" * 40)
    audio_file = os.path.join(output_dir, "complete_voiceover.mp3")
    
    if await generate_complete_audio(scenes, audio_file, voice):
        print("✅ 音频生成完成")
    else:
        print("❌ 音频生成失败")
        return
    
    # 步骤2: 准备图片
    print("\n🖼️  步骤 2/3: 准备图片素材")
    print("-" * 40)
    image_files = copy_existing_images()
    print(f"✅ 准备了 {len(image_files)} 张图片")
    
    # 步骤3: 使用最小化视频合成
    print("\n🎬 步骤 3/3: 合成视频")
    print("-" * 40)
    
    # 使用之前创建的最小化视频合成工具
    try:
        import subprocess
        import sys
        
        # 检查是否有所需的视频合成脚本
        if os.path.exists("minimal_video_fix.py"):
            print("🔄 调用最小化视频合成工具...")
            result = subprocess.run([
                sys.executable, "minimal_video_fix.py"
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                print("✅ 视频合成完成!")
                print("🎉 全流程执行成功!")
            else:
                print("❌ 视频合成失败:")
                print(result.stderr)
        else:
            print("⚠️  未找到视频合成工具，您可以手动使用以下文件:")
            print(f"   音频文件: {audio_file}")
            print(f"   图片文件: {len(image_files)} 张")
            
    except Exception as e:
        print(f"❌ 视频合成调用失败: {e}")

if __name__ == "__main__":
    asyncio.run(main())