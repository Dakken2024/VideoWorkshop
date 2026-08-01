#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
字幕功能测试脚本
验证视频字幕生成功能是否正常工作
"""

import os
import sys
import json
from pathlib import Path

# 添加当前目录到Python路径
sys.path.insert(0, str(Path(__file__).parent))

from auto_video_maker import VideoCompositor, load_script_from_json

def test_subtitle_generation():
    """测试字幕生成功能"""
    print("=" * 60)
    print("🔍 字幕功能测试")
    print("=" * 60)
    
    # 测试数据
    test_scenes = [
        {
            "scene_id": 1,
            "text": "欢迎观看本期视频，今天我们要讲述一位传奇人物的故事。",
            "prompt": "welcome scene with professional presenter",
            "duration": 8
        },
        {
            "scene_id": 2,
            "text": "她就是世界上第一位程序员——阿达·洛芙莱斯。",
            "prompt": "historical portrait of Ada Lovelace",
            "duration": 6
        },
        {
            "scene_id": 3,
            "text": "让我们一起探索她的非凡人生和伟大贡献。",
            "prompt": "inspirational technology background",
            "duration": 7
        }
    ]
    
    # 创建测试输出目录
    test_output_dir = "./test_output"
    os.makedirs(test_output_dir, exist_ok=True)
    
    print(f"📁 测试输出目录: {test_output_dir}")
    
    # 创建视频合成器实例
    video_comp = VideoCompositor(test_output_dir)
    
    # 显示字幕配置
    print("\n📋 字幕配置:")
    for key, value in video_comp.subtitle_config.items():
        print(f"  {key}: {value}")
    
    # 测试单个字幕创建
    print("\n📝 单个字幕测试:")
    test_text = "这是一个测试字幕文本，用来验证字幕生成功能是否正常工作。"
    subtitle_clip = video_comp._create_subtitle_clip(test_text, 5.0, 0.0)
    
    if subtitle_clip:
        print("✅ 单个字幕创建成功")
        print(f"  文本长度: {len(test_text)} 字符")
        print(f"  持续时间: {subtitle_clip.duration} 秒")
        print(f"  开始时间: {subtitle_clip.start} 秒")
    else:
        print("❌ 单个字幕创建失败")
    
    # 测试多个字幕创建
    print("\n📚 多字幕测试:")
    subtitle_clips = []
    accumulated_time = 0.0
    
    for i, scene in enumerate(test_scenes):
        text = scene["text"]
        duration = float(scene["duration"])
        
        subtitle_clip = video_comp._create_subtitle_clip(text, duration, accumulated_time)
        if subtitle_clip:
            subtitle_clips.append(subtitle_clip)
            print(f"  ✅ 场景 {i+1}: {text[:30]}... (持续 {duration}秒)")
        else:
            print(f"  ❌ 场景 {i+1}: 字幕创建失败")
        
        accumulated_time += duration
    
    print(f"\n📊 总计: 成功创建 {len(subtitle_clips)} 条字幕")
    
    # 清理测试资源
    for clip in subtitle_clips:
        try:
            clip.close()
        except:
            pass
    
    print("\n" + "=" * 60)
    print("🎯 字幕功能测试完成")
    print("=" * 60)

def test_json_script_loading():
    """测试JSON脚本加载和字幕提取"""
    print("\n" + "=" * 60)
    print("📄 JSON脚本加载测试")
    print("=" * 60)
    
    script_file = "scripts.json"
    if not os.path.exists(script_file):
        print(f"❌ 未找到脚本文件: {script_file}")
        return
    
    # 加载脚本
    script_config = load_script_from_json(script_file)
    if not script_config:
        print("❌ 脚本加载失败")
        return
    
    print("✅ 脚本加载成功")
    print(f"  项目名称: {script_config['project_name']}")
    print(f"  场景数量: {len(script_config['scenes'])}")
    
    # 提取字幕文本
    print("\n🔤 字幕文本提取:")
    subtitles = []
    for i, scene in enumerate(script_config['scenes']):
        text = scene.get('text', '').strip()
        if text:
            subtitles.append({
                'scene_id': scene.get('scene_id', i+1),
                'text': text,
                'duration': scene.get('duration', 5)
            })
            print(f"  场景 {scene.get('scene_id', i+1)}: {text[:50]}...")
        else:
            print(f"  场景 {scene.get('scene_id', i+1)}: ⚠️  无文本内容")
    
    print(f"\n📊 有效字幕数量: {len(subtitles)}/{len(script_config['scenes'])}")
    
    # 显示字幕统计
    if subtitles:
        total_chars = sum(len(sub['text']) for sub in subtitles)
        avg_chars = total_chars / len(subtitles)
        print(f"  总字符数: {total_chars}")
        print(f"  平均每条字幕: {avg_chars:.1f} 字符")

def main():
    """主测试函数"""
    print("🎬 Saabor AI Builds - 字幕功能测试")
    print("测试视频字幕生成功能是否正常工作\n")
    
    # 运行各项测试
    test_json_script_loading()
    test_subtitle_generation()
    
    print("\n" + "=" * 60)
    print("✅ 所有测试完成")
    print("现在可以运行 auto_video_maker.py 来生成带字幕的视频")
    print("=" * 60)

if __name__ == "__main__":
    main()