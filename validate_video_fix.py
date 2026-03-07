#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
验证修复后的视频生成流程
"""

import os
import sys

def test_file_structure():
    """测试文件结构"""
    print("🔍 文件结构验证")
    print("=" * 50)
    
    output_dir = "./output"
    
    # 检查必需文件
    required_files = [
        "voiceover.mp3",
        "complete_voiceover.mp3",
        "scene_000.jpg",
        "scene_001.jpg",
        "scene_002.jpg"
    ]
    
    print("检查必需文件:")
    for filename in required_files:
        filepath = os.path.join(output_dir, filename)
        exists = os.path.exists(filepath)
        if exists:
            size = os.path.getsize(filepath)
            print(f"  ✅ {filename} ({size:,} bytes)")
        else:
            print(f"  ❌ {filename} (不存在)")
    
    # 检查图片文件数量
    scene_files = [f for f in os.listdir(output_dir) if f.startswith("scene_") and f.endswith(".jpg")]
    print(f"\n找到 {len(scene_files)} 张场景图片")
    
    return len(scene_files) > 0

def test_path_handling():
    """测试路径处理逻辑"""
    print("\n🔧 路径处理测试")
    print("=" * 50)
    
    test_paths = [
        "./output/voiceover.mp3",
        ".\\output\\voiceover.mp3",
        "output/voiceover.mp3",
        "output\\voiceover.mp3"
    ]
    
    print("路径标准化测试:")
    for path in test_paths:
        normalized = os.path.normpath(path)
        exists = os.path.exists(normalized)
        print(f"  原始: {path}")
        print(f"  标准化: {normalized}")
        print(f"  存在: {'✅' if exists else '❌'}")
        print()

def simulate_video_creation():
    """模拟视频创建流程"""
    print("🎬 视频创建流程模拟")
    print("=" * 50)
    
    output_dir = "./output"
    
    # 模拟音频文件检查
    audio_candidates = [
        os.path.join(output_dir, "voiceover.mp3"),
        os.path.join(output_dir, "complete_voiceover.mp3"),
        os.path.join(output_dir, "segment_000.mp3")
    ]
    
    print("音频文件候选列表:")
    found_audio = None
    for candidate in audio_candidates:
        exists = os.path.exists(candidate)
        print(f"  {'✅' if exists else '❌'} {candidate}")
        if exists and not found_audio:
            found_audio = candidate
    
    if found_audio:
        print(f"\n🎯 选定音频文件: {found_audio}")
    else:
        print("\n❌ 未找到任何音频文件")
        return False
    
    # 模拟图片文件检查
    image_files = []
    for i in range(20):
        img_path = os.path.join(output_dir, f"scene_{i:03d}.jpg")
        if os.path.exists(img_path):
            image_files.append(img_path)
        else:
            break
    
    print(f"\n🖼️  找到 {len(image_files)} 张图片:")
    for img in image_files[:5]:  # 只显示前5张
        print(f"  - {os.path.basename(img)}")
    if len(image_files) > 5:
        print(f"  ... 还有 {len(image_files) - 5} 张")
    
    return len(image_files) > 0 and found_audio

def main():
    print("🚀 视频生成流程验证工具")
    print("=" * 60)
    
    # 1. 文件结构检查
    files_ok = test_file_structure()
    
    # 2. 路径处理测试
    test_path_handling()
    
    # 3. 流程模拟
    workflow_ok = simulate_video_creation()
    
    # 4. 总结
    print("\n" + "=" * 60)
    print("📊 验证结果:")
    print(f"  文件结构: {'✅ 通过' if files_ok else '❌ 失败'}")
    print(f"  流程逻辑: {'✅ 通过' if workflow_ok else '❌ 失败'}")
    
    if files_ok and workflow_ok:
        print("\n🎉 所有验证通过！可以运行视频生成流程。")
        print("\n💡 建议运行命令:")
        print("   python auto_video_maker.py")
    else:
        print("\n❌ 验证失败，请检查上述问题。")

if __name__ == "__main__":
    main()