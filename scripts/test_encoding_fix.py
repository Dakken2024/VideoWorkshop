#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
测试编码修复效果
"""

import sys
import os

# 添加当前目录到路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_encoding_fix():
    """测试编码修复"""
    print("🧪 编码问题修复测试")
    print("=" * 40)
    
    try:
        # 导入修复后的日志函数
        from auto_video_maker import log
        
        print("✅ 成功导入日志函数")
        
        # 测试各种日志级别
        test_messages = [
            ("INFO", "这是一条普通信息"),
            ("SUCCESS", "操作成功完成"),
            ("WARNING", "请注意这个警告"),
            ("ERROR", "发生了一个错误"),
            ("DEBUG", "调试信息输出")
        ]
        
        print("\n📝 日志输出测试:")
        for level, message in test_messages:
            print(f"测试 {level}: ", end="")
            log(level, message)
            
        print("\n✅ 所有日志测试通过！")
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return False

def test_unicode_handling():
    """测试Unicode处理能力"""
    print("\n🔤 Unicode处理测试")
    print("=" * 40)
    
    test_strings = [
        "English text",
        "中文测试",
        "Mixed混合内容",
        "Special chars: !@#$%^&*()",
        "Emoji: 😀🎉🚀"
    ]
    
    try:
        from auto_video_maker import log
        
        for test_str in test_strings:
            print(f"测试字符串: {test_str}")
            log("INFO", test_str)
            
        print("\n✅ Unicode处理测试通过！")
        return True
        
    except Exception as e:
        print(f"❌ Unicode测试失败: {e}")
        return False

if __name__ == "__main__":
    print("🚀 开始编码修复验证测试\n")
    
    success1 = test_encoding_fix()
    success2 = test_unicode_handling()
    
    if success1 and success2:
        print("\n🎉 所有测试通过！编码问题已修复。")
        print("现在可以在Windows环境下正常使用GUI了。")
    else:
        print("\n❌ 部分测试失败，请检查代码。")