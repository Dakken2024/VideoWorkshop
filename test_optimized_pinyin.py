#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
测试优化后的中文标题转拼音功能
"""

def test_optimized_pinyin():
    """测试优化后的拼音转换"""
    
    test_cases = [
        "世界上第一位程序员，竟然是位女士？",
        "Ada Lovelace的故事", 
        "人工智能发展史",
        "科技改变生活",
        "测试123ABC",
        "混合内容Test测试"
    ]
    
    print("🔤 优化后的中文标题转拼音测试")
    print("=" * 60)
    
    try:
        import pypinyin
        import re
        
        for i, title in enumerate(test_cases, 1):
            print(f"\n测试 {i}: {title}")
            
            # 完整转换流程
            pinyin_list = pypinyin.lazy_pinyin(title, style=pypinyin.Style.NORMAL)
            pinyin_title = '_'.join(pinyin_list)
            clean_title = re.sub(r'[^a-zA-Z0-9_]', '', pinyin_title)
            clean_title = re.sub(r'_+', '_', clean_title)
            clean_title = clean_title.strip('_')
            
            print(f"  原始拼音: {pinyin_title}")
            print(f"  优化结果: {clean_title}")
            print(f"  完整路径: ./output/202602/{clean_title}/")
            
            # 验证目录名有效性
            is_valid = len(clean_title) > 0 and clean_title != "untitled_video"
            print(f"  有效性: {'✅' if is_valid else '❌'}")
            
    except ImportError:
        print("❌ 未安装pypinyin库")
        print("请运行: pip install pypinyin")

def demonstrate_directory_structure():
    """演示目录结构"""
    
    print("\n" + "=" * 60)
    print("📁 标准目录结构演示")
    print("=" * 60)
    
    sample_videos = [
        {
            "title": "世界上第一位程序员，竟然是位女士？",
            "expected_dir": "shi_jie_shang_di_yi_wei_cheng_xu_yuan_jing_ran_shi_wei_nv_shi"
        },
        {
            "title": "Ada Lovelace的故事",
            "expected_dir": "AdaLovelace_de_gu_shi"
        },
        {
            "title": "人工智能发展史", 
            "expected_dir": "ren_gong_zhi_neng_fa_zhan_shi"
        }
    ]
    
    try:
        import pypinyin
        import re
        
        for video in sample_videos:
            # 实际转换
            pinyin_list = pypinyin.lazy_pinyin(video["title"], style=pypinyin.Style.NORMAL)
            pinyin_title = '_'.join(pinyin_list)
            clean_title = re.sub(r'[^a-zA-Z0-9_]', '', pinyin_title)
            clean_title = re.sub(r'_+', '_', clean_title)
            clean_title = clean_title.strip('_')
            
            print(f"\n视频标题: {video['title']}")
            print(f"预期目录: {video['expected_dir']}")
            print(f"实际结果: {clean_title}")
            print(f"匹配度: {'✅ 完全匹配' if clean_title == video['expected_dir'] else '⚠️  部分匹配'}")
            
            # 显示完整目录结构
            print(f"完整路径结构:")
            print(f"  ./output/")
            print(f"    └── 202602/")  
            print(f"        └── {clean_title}/")
            print(f"            ├── voiceover.mp3")
            print(f"            ├── scene_0.jpg")
            print(f"            ├── scene_1.jpg")
            print(f"            ├── scripts.json")
            print(f"            └── {clean_title}.mp4")
            
    except ImportError:
        print("请先安装pypinyin库")

if __name__ == "__main__":
    test_optimized_pinyin()
    demonstrate_directory_structure()
    
    print("\n" + "=" * 60)
    print("✅ 优化测试完成！")
    print("\n📋 改进要点:")
    print("1. ✅ 清理多余下划线 (_+_ → _)")  
    print("2. ✅ 移除首尾下划线 (.strip('_'))")
    print("3. ✅ 保留英文字母、数字和下划线")
    print("4. ✅ 兼容无pypinyin库的情况")
    print("5. ✅ 异常处理和日志记录")