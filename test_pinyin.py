#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
测试中文标题转拼音功能
"""

def test_pinyin_conversion():
    """测试拼音转换功能"""
    
    test_cases = [
        "世界上第一位程序员，竟然是位女士？",
        "Ada Lovelace的故事",
        "人工智能发展史",
        "科技改变生活",
        "测试123ABC",
        "混合内容Test测试",
        ""  # 空字符串测试
    ]
    
    print("🔤 中文标题转拼音测试")
    print("=" * 50)
    
    try:
        import pypinyin
        
        for i, title in enumerate(test_cases, 1):
            print(f"\n测试 {i}: {title}")
            
            # 使用不同风格的拼音转换
            normal_pinyin = pypinyin.lazy_pinyin(title, style=pypinyin.Style.NORMAL)
            first_letter = pypinyin.lazy_pinyin(title, style=pypinyin.Style.FIRST_LETTER)
            
            print(f"  完整拼音: {'_'.join(normal_pinyin)}")
            print(f"  首字母: {'_'.join(first_letter)}")
            
            # 清理特殊字符
            clean_pinyin = '_'.join(normal_pinyin)
            final_result = ''.join(c for c in clean_pinyin if c.isalnum() or c == '_')
            
            print(f"  清理后: {final_result}")
            
    except ImportError:
        print("❌ 未安装pypinyin库")
        print("请运行: pip install pypinyin")
        
        # 模拟简单处理
        print("\n📝 简单处理模拟:")
        for i, title in enumerate(test_cases, 1):
            # 移除中文字符，保留英文字母和数字
            english_only = ''.join(c for c in title if c.isascii() and (c.isalnum() or c.isspace()))
            clean_title = '_'.join(english_only.split())
            print(f"  {title} -> {clean_title if clean_title else 'untitled'}")

def test_directory_naming():
    """测试目录命名功能"""
    
    print("\n" + "=" * 50)
    print("📁 目录命名测试")
    print("=" * 50)
    
    test_titles = [
        "世界上第一位程序员，竟然是位女士？",
        "Ada Lovelace的故事",
        "人工智能发展史"
    ]
    
    try:
        import pypinyin
        import re
        
        for title in test_titles:
            # 完整拼音转换
            pinyin_list = pypinyin.lazy_pinyin(title, style=pypinyin.Style.NORMAL)
            pinyin_title = '_'.join(pinyin_list)
            clean_title = re.sub(r'[^a-zA-Z0-9_]', '', pinyin_title)
            
            print(f"原文: {title}")
            print(f"拼音: {clean_title}")
            print(f"完整路径: ./output/202602/{clean_title}/")
            print("-" * 30)
            
    except ImportError:
        print("请先安装pypinyin库: pip install pypinyin")

if __name__ == "__main__":
    test_pinyin_conversion()
    test_directory_naming()
    
    print("\n✅ 测试完成！")
    print("\n💡 建议:")
    print("1. 安装pypinyin库以获得最佳中文转拼音效果")
    print("2. 运行 'pip install pypinyin' 安装依赖")
    print("3. 重新测试GUI应用查看效果")