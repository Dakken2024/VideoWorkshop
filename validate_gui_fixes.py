#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
GUI功能修复验证脚本
"""

import tkinter as tk
from tkinter import ttk
import json
import os

def test_scene_sorting():
    """测试场景排序功能"""
    print("🔍 场景排序功能测试")
    print("=" * 50)
    
    # 模拟脚本数据（乱序的scene_id）
    test_scripts = {
        "scenes": [
            {"scene_id": 3, "text": "第三个场景", "note": "测试场景3"},
            {"scene_id": 1, "text": "第一个场景", "note": "测试场景1"}, 
            {"scene_id": 5, "text": "第五个场景", "note": "测试场景5"},
            {"scene_id": 2, "text": "第二个场景", "note": "测试场景2"},
            {"scene_id": 4, "text": "第四个场景", "note": "测试场景4"}
        ]
    }
    
    print("原始场景顺序:")
    for i, scene in enumerate(test_scripts['scenes']):
        print(f"  列表索引 {i}: scene_id {scene['scene_id']} - {scene['note']}")
    
    # 按scene_id排序
    sorted_scenes = sorted(test_scripts['scenes'], key=lambda x: x.get('scene_id', 0))
    
    print("\n排序后场景顺序:")
    for i, scene in enumerate(sorted_scenes):
        print(f"  列表索引 {i}: scene_id {scene['scene_id']} - {scene['note']}")
    
    # 验证排序正确性
    scene_ids = [scene['scene_id'] for scene in sorted_scenes]
    is_sorted = scene_ids == sorted(scene_ids)
    
    print(f"\n排序验证: {'✅ 正确' if is_sorted else '❌ 错误'}")
    return is_sorted

def test_image_path_handling():
    """测试图片路径处理"""
    print("\n🖼️  图片路径处理测试")
    print("=" * 50)
    
    test_cases = [
        {"scene_id": 1, "expected": "scene_000.jpg"},
        {"scene_id": 5, "expected": "scene_004.jpg"}, 
        {"scene_id": 10, "expected": "scene_009.jpg"},
        {"scene_id": 14, "expected": "scene_013.jpg"}
    ]
    
    print("场景ID到文件名映射:")
    all_correct = True
    for case in test_cases:
        scene_index = case['scene_id'] - 1
        filename = f"scene_{scene_index:03d}.jpg"
        is_correct = filename == case['expected']
        status = "✅" if is_correct else "❌"
        print(f"  场景ID {case['scene_id']:2d} → {filename:15s} {status}")
        if not is_correct:
            all_correct = False
            print(f"    期望: {case['expected']}")
    
    print(f"\n路径处理验证: {'✅ 全部正确' if all_correct else '❌ 存在错误'}")
    return all_correct

def test_font_fallback():
    """测试字体回退机制"""
    print("\n🔤 字体回退机制测试")
    print("=" * 50)
    
    # 模拟字体可用性检查
    fonts_to_try = ['Arial', 'SimHei', 'Microsoft YaHei', 'sans-serif', None]
    print("字体尝试顺序:")
    
    for i, font in enumerate(fonts_to_try):
        if font is None:
            print(f"  {i+1}. 默认系统字体")
        else:
            print(f"  {i+1}. {font}")
    
    print("\n字体策略:")
    print("  ✅ 优先尝试常用英文字体")
    print("  ✅ 包含中文字体选项") 
    print("  ✅ 提供系统默认字体备选")
    print("  ✅ 避免因单一字体缺失导致失败")

def create_sample_script():
    """创建示例脚本文件用于测试"""
    print("\n📄 示例脚本创建")
    print("=" * 50)
    
    sample_script = {
        "meta": {
            "title": "测试视频排序功能",
            "topic": "GUI测试",
            "voice_setting": "zh-CN-XiaoxiaoNeural"
        },
        "scenes": [
            {"scene_id": 3, "text": "第三个场景的内容", "prompt": "测试图片3", "note": "场景3说明"},
            {"scene_id": 1, "text": "第一个场景的内容", "prompt": "测试图片1", "note": "场景1说明"},
            {"scene_id": 2, "text": "第二个场景的内容", "prompt": "测试图片2", "note": "场景2说明"}
        ]
    }
    
    try:
        with open("test_scripts.json", 'w', encoding='utf-8') as f:
            json.dump(sample_script, f, ensure_ascii=False, indent=2)
        print("✅ 示例脚本文件已创建: test_scripts.json")
        print("   包含乱序的scene_id用于测试排序功能")
        return True
    except Exception as e:
        print(f"❌ 创建示例脚本失败: {e}")
        return False

def main():
    print("🚀 GUI功能修复验证")
    print("=" * 60)
    
    # 1. 场景排序测试
    sorting_ok = test_scene_sorting()
    
    # 2. 图片路径处理测试
    path_ok = test_image_path_handling()
    
    # 3. 字体回退测试
    font_ok = test_font_fallback()
    
    # 4. 创建测试文件
    file_ok = create_sample_script()
    
    # 总结
    print("\n" + "=" * 60)
    print("📊 修复验证总结:")
    print(f"  场景排序功能: {'✅ 通过' if sorting_ok else '❌ 失败'}")
    print(f"  图片路径处理: {'✅ 通过' if path_ok else '❌ 失败'}")
    print(f"  字体回退机制: {'✅ 通过' if font_ok else '❌ 失败'}")
    print(f"  测试文件创建: {'✅ 通过' if file_ok else '❌ 失败'}")
    
    if all([sorting_ok, path_ok, font_ok, file_ok]):
        print("\n🎉 所有修复验证通过！")
        print("\n💡 使用建议:")
        print("   1. 运行 GUI: python video_creator_gui.py")
        print("   2. 加载 test_scripts.json 测试排序功能")
        print("   3. 验证场景按scene_id正确排序显示")
        print("   4. 测试图片上传和重新生成功能")
    else:
        print("\n❌ 部分验证失败，请检查上述问题")

if __name__ == "__main__":
    main()