#!/usr/bin/env python3
# -*- coding: utf-8 -*-

try:
    # 尝试MoviePy 2.x导入
    from moviepy import TextClip
    print("MoviePy 2.x detected")
    print("TextClip parameters:")
    import inspect
    print(inspect.signature(TextClip.__init__))
    
except ImportError:
    try:
        # 尝试MoviePy 1.x导入
        from moviepy.editor import TextClip
        print("MoviePy 1.x detected")
        print("TextClip parameters:")
        import inspect
        print(inspect.signature(TextClip.__init__))
    except Exception as e:
        print(f"Import error: {e}")

# 测试简单字幕创建
try:
    clip = TextClip("测试文本", fontsize=24, color='white')
    print("Simple TextClip creation: SUCCESS")
    clip.close()
except Exception as e:
    print(f"Simple TextClip creation failed: {e}")