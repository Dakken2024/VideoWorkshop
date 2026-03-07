#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
验证SSML修复效果的测试脚本
"""

import asyncio
import os
import sys

# 添加当前目录到路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

async def test_ssml_fix():
    """测试SSML修复效果"""
    
    print("🧪 SSML修复效果验证测试")
    print("=" * 50)
    
    try:
        # 导入修复后的模块
        from auto_video_maker import ChineseSSMLProcessor, AudioGenerator
        
        print("✅ 成功导入修复后的模块")
        
        # 测试SSML处理器
        print("\n🔧 测试SSML处理器:")
        processor = ChineseSSMLProcessor()
        
        test_text = "提到程序员，你脑海里是不是全是穿卫衣的极客小哥？但在电脑诞生前100年，第一位程序员，其实是位女士。"
        
        enhanced_text = processor.enhance_text(test_text)
        print(f"原始文本: {test_text}")
        print(f"增强文本: {enhanced_text}")
        print(f"包含break标签: {processor.is_valid_enhanced(enhanced_text)}")
        print(f"break标签数量: {enhanced_text.count('<break')}")
        
        # 测试音频生成
        print("\n🎵 测试音频生成:")
        audio_gen = AudioGenerator(use_ssml=True)
        
        # 生成SSML版本
        ssml_file = "./output/test_fix_ssml.mp3"
        print(f"生成SSML版本: {ssml_file}")
        ssml_success = await audio_gen.generate_segment(test_text, ssml_file, "测试场景")
        
        # 生成普通版本作为对比
        plain_file = "./output/test_fix_plain.mp3" 
        print(f"生成普通版本: {plain_file}")
        # 临时关闭SSML来生成纯文本版本
        audio_gen.use_ssml = False
        plain_success = await audio_gen.generate_segment(test_text, plain_file, "对照场景")
        audio_gen.use_ssml = True  # 恢复设置
        
        # 分析结果
        print("\n📊 结果分析:")
        if ssml_success and plain_success:
            ssml_size = os.path.getsize(ssml_file)
            plain_size = os.path.getsize(plain_file)
            ratio = ssml_size / plain_size if plain_size > 0 else 0
            
            print(f"   SSML版本大小: {ssml_size} bytes")
            print(f"   普通版本大小: {plain_size} bytes")
            print(f"   大小比例: {ratio:.2f}x")
            
            if ratio >= 1.2:
                print("   🎉 SSML显著生效！修复成功！")
                return True
            elif ratio >= 1.05:
                print("   ✅ SSML轻微生效")
                return True
            else:
                print("   ❌ SSML未生效，需要进一步调试")
                return False
        else:
            print("   ❌ 音频生成失败")
            return False
            
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def show_before_after_comparison():
    """展示修复前后的对比"""
    
    print("\n📋 修复前后对比")
    print("=" * 50)
    
    comparison = {
        "问题": ["XML转义时机", "验证逻辑复杂度", "正则表达式", "调用方式"],
        "修复前": [
            "先转义XML再插入标签（破坏标签）",
            "复杂标签平衡检查（经常失败）", 
            "复杂的look-behind正则（语法错误）",
            "完整的<speak>包装（可能被忽略）"
        ],
        "修复后": [
            "直接插入break标签（保持完整性）",
            "简单包含检查（可靠有效）",
            "简单的字符串替换（稳定可靠）",
            "直接传入增强文本（让edge-tts自动识别）"
        ]
    }
    
    for i in range(len(comparison["问题"])):
        print(f"{i+1}. {comparison['问题'][i]}")
        print(f"   之前: {comparison['修复前'][i]}")
        print(f"   之后: {comparison['修复后'][i]}")
        print()

if __name__ == "__main__":
    print("🚀 SSML修复验证测试")
    print("=" * 60)
    
    # 展示对比
    show_before_after_comparison()
    
    # 运行测试
    success = asyncio.run(test_ssml_fix())
    
    print("\n" + "=" * 60)
    if success:
        print("🎉 SSML修复验证成功！")
        print("现在可以重新运行视频生成，SSML停顿效果将正常工作。")
    else:
        print("❌ SSML修复验证失败")
        print("建议检查edge-tts版本或进一步调试")