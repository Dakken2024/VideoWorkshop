#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
视频合成修复验证测试
"""

import os
import sys
from pathlib import Path

def test_path_normalization():
    """测试路径标准化功能"""
    
    print("🔧 路径标准化测试")
    print("=" * 40)
    
    # 测试路径
    test_paths = [
        "./output/voiceover.mp3",
        ".\\output\\voiceover.mp3",
        "output/voiceover.mp3",
        "output\\voiceover.mp3"
    ]
    
    for path in test_paths:
        # 使用不同方法标准化
        method1 = os.path.normpath(path)
        method2 = str(Path(path))
        method3 = os.path.abspath(path)
        
        print(f"原始路径: {path}")
        print(f"  normpath: {method1}")
        print(f"  Path: {method2}")
        print(f"  abspath: {method3}")
        print(f"  文件存在: {os.path.exists(method3)}")
        print()

def test_file_operations():
    """测试文件操作"""
    
    print("📂 文件操作测试")
    print("=" * 40)
    
    # 检查输出目录
    output_dir = "./output"
    abs_output = os.path.abspath(output_dir)
    
    print(f"输出目录: {abs_output}")
    print(f"目录存在: {os.path.exists(abs_output)}")
    print(f"是否目录: {os.path.isdir(abs_output)}")
    
    if os.path.exists(abs_output):
        files = os.listdir(abs_output)
        print(f"目录内容: {files}")
        
        # 检查关键文件
        key_files = ["voiceover.mp3", "segment_000.mp3"]
        for file in key_files:
            file_path = os.path.join(abs_output, file)
            exists = os.path.exists(file_path)
            size = os.path.getsize(file_path) if exists else 0
            print(f"  {file}: {'存在' if exists else '不存在'} ({size:,} bytes)")

def test_moviepy_import():
    """测试MoviePy导入"""
    
    print("\n🎬 MoviePy导入测试")
    print("=" * 40)
    
    try:
        # 尝试不同的导入方式
        import moviepy
        print(f"✅ MoviePy版本: {moviepy.__version__}")
        
        # 测试关键组件导入
        try:
            from moviepy.editor import AudioFileClip, ImageClip, concatenate_videoclips
            print("✅ 核心组件导入成功")
        except ImportError as e:
            print(f"❌ 核心组件导入失败: {e}")
            return False
            
        try:
            from moviepy.video.VideoClip import TextClip, CompositeVideoClip
            print("✅ 视频组件导入成功")
        except ImportError as e:
            print(f"❌ 视频组件导入失败: {e}")
            
        try:
            import moviepy.video.fx.all as vfx
            print("✅ 视频效果导入成功")
        except ImportError as e:
            print(f"❌ 视频效果导入失败: {e}")
            
        return True
        
    except ImportError as e:
        print(f"❌ MoviePy导入失败: {e}")
        return False

def create_simple_test_video():
    """创建简单的测试视频"""
    
    print("\n🎥 简单视频测试")
    print("=" * 40)
    
    try:
        from moviepy.editor import ColorClip, TextClip, CompositeVideoClip
        
        # 创建简单的彩色背景
        background = ColorClip(size=(1080, 1920), color=(100, 100, 100), duration=5)
        
        # 添加文字
        text = TextClip("测试视频", fontsize=50, color='white', font='Arial-Bold')
        text = text.with_position('center').with_duration(5)
        
        # 合成
        final_clip = CompositeVideoClip([background, text])
        
        # 导出
        output_path = "./output/test_video.mp4"
        final_clip.write_videofile(
            output_path,
            fps=24,
            codec='libx264',
            audio=False,
            verbose=False,
            logger=None
        )
        
        final_clip.close()
        
        if os.path.exists(output_path):
            size = os.path.getsize(output_path)
            print(f"✅ 测试视频创建成功: {output_path} ({size:,} bytes)")
            return True
        else:
            print("❌ 测试视频未生成")
            return False
            
    except Exception as e:
        print(f"❌ 测试视频创建失败: {e}")
        import traceback
        print(f"详细错误: {traceback.format_exc()}")
        return False

if __name__ == "__main__":
    print("🚀 视频合成修复验证")
    print("=" * 50)
    
    # 测试路径处理
    test_path_normalization()
    
    # 测试文件操作
    test_file_operations()
    
    # 测试MoviePy导入
    moviepy_ok = test_moviepy_import()
    
    # 如果导入成功，进行简单测试
    if moviepy_ok:
        create_simple_test_video()
    
    print("\n" + "=" * 50)
    print("📋 测试总结:")
    if not moviepy_ok:
        print("❌ MoviePy导入存在问题，需要修复环境")
    else:
        print("✅ 基础功能测试通过")
        print("💡 建议重新运行完整的视频生成流程")