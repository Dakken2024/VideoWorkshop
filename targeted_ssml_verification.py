#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
针对性验证：SSML标签是否真的被朗读
"""

import asyncio
import edge_tts
import os

async def targeted_verification():
    """针对性验证用户报告的问题"""
    
    print("🎯 针对性验证：SSML标签朗读问题")
    print("=" * 60)
    
    # 用户报告的问题：标签被直接朗读出来
    # 让我们创建一个明确的测试来验证这一点
    
    test_cases = [
        # 测试1：用户可能听到的"标签朗读"情况
        {
            'name': 'suspected_tag_reading',
            'text': '你好break time等于1秒世界',
            'description': '模拟标签被当作普通文本朗读的情况'
        },
        # 测试2：真实的SSML标签
        {
            'name': 'real_ssml_tags',
            'text': '你好<break time="1s"/>世界',
            'description': '真实的SSML break标签'
        },
        # 测试3：纯文本对照
        {
            'name': 'pure_text',
            'text': '你好世界',
            'description': '纯文本对照组'
        }
    ]
    
    results = []
    
    for case in test_cases:
        print(f"\n🧪 测试: {case['description']}")
        print(f"文本内容: {case['text']}")
        
        output_file = f"./output/targeted_{case['name']}.mp3"
        
        try:
            communicate = edge_tts.Communicate(
                text=case['text'],
                voice="zh-CN-XiaoxiaoNeural",
                rate="+0%",
                volume="+0%"
            )
            await communicate.save(output_file)
            
            if os.path.exists(output_file):
                size = os.path.getsize(output_file)
                print(f"✅ 生成成功: {size:,} bytes")
                
                results.append({
                    'name': case['name'],
                    'text': case['text'],
                    'file': output_file,
                    'size': size,
                    'description': case['description']
                })
            else:
                print("❌ 文件生成失败")
                
        except Exception as e:
            print(f"❌ 生成错误: {e}")
    
    return results

def create_detailed_comparison(results):
    """创建详细对比分析"""
    
    print("\n📊 详细对比分析")
    print("=" * 60)
    
    if len(results) < 3:
        print("❌ 测试结果不完整")
        return
    
    # 按大小排序
    sorted_results = sorted(results, key=lambda x: x['size'])
    
    print("文件大小排序（从小到大）:")
    for i, result in enumerate(sorted_results):
        print(f"{i+1}. {result['description']}")
        print(f"   文件: {os.path.basename(result['file'])}")
        print(f"   大小: {result['size']:,} bytes")
        print(f"   文本: {result['text']}")
        print()
    
    # 分析差异
    pure_text_result = next((r for r in results if r['name'] == 'pure_text'), None)
    ssml_result = next((r for r in results if r['name'] == 'real_ssml_tags'), None)
    suspected_result = next((r for r in results if r['name'] == 'suspected_tag_reading'), None)
    
    print("🔍 差异分析:")
    
    if pure_text_result and ssml_result:
        size_diff = ssml_result['size'] - pure_text_result['size']
        ratio = ssml_result['size'] / pure_text_result['size']
        print(f"\n纯文本 vs 真实SSML:")
        print(f"  大小差异: {size_diff:,} bytes")
        print(f"  增长比例: {ratio:.2f}x")
        if ratio > 2.0:
            print("  ✅ SSML很可能被正确处理（显著增长）")
        elif ratio > 1.2:
            print("  ⚠️  SSML可能部分生效（适度增长）")
        else:
            print("  ❌ SSML可能未生效（几乎无增长）")
    
    if suspected_result and pure_text_result:
        size_diff = suspected_result['size'] - pure_text_result['size']
        ratio = suspected_result['size'] / pure_text_result['size']
        print(f"\n纯文本 vs '标签朗读'版本:")
        print(f"  大小差异: {size_diff:,} bytes")
        print(f"  增长比例: {ratio:.2f}x")
        print(f"  说明: 如果这个版本更大，可能是把标签当作文本处理了")

def generate_playback_instructions(results):
    """生成播放指导"""
    
    print("\n🔊 播放验证指导")
    print("=" * 60)
    print("请按以下顺序仔细聆听音频文件：")
    
    playback_order = ['pure_text', 'suspected_tag_reading', 'real_ssml_tags']
    
    for i, name_key in enumerate(playback_order):
        result = next((r for r in results if r['name'] == name_key), None)
        if result:
            print(f"\n{i+1}. {result['description']}")
            print(f"   文件: {os.path.basename(result['file'])}")
            print(f"   预期效果:")
            
            if name_key == 'pure_text':
                print("   - 应该听到: '你好世界'")
                print("   - 长度: 最短")
            elif name_key == 'suspected_tag_reading':
                print("   - 如果听到: '你好break time等于1秒世界'")
                print("   - 说明: 标签被当作文本处理了")
                print("   - 长度: 应该比纯文本稍长")
            elif name_key == 'real_ssml_tags':
                print("   - 应该听到: '你好' [停顿] '世界'")
                print("   - 不应该听到: 'break'、'time'等词汇")
                print("   - 长度: 应该最长且有明显停顿")

async def alternative_testing():
    """替代测试方法"""
    
    print("\n🧪 替代测试方法")
    print("=" * 60)
    
    # 测试不同的SSML格式
    alternative_tests = [
        {
            'name': 'spaces_in_tags',
            'text': '你好 <break time="1s"/> 世界',
            'description': '标签带空格测试'
        },
        {
            'name': 'different_quotes',
            'text': '你好<break time=\'1s\'/>世界', 
            'description': '使用单引号测试'
        },
        {
            'name': 'no_closing_slash',
            'text': '你好<break time="1s">世界</break>',
            'description': '配对标签测试'
        }
    ]
    
    for test in alternative_tests:
        print(f"\n🧪 {test['description']}")
        print(f"文本: {test['text']}")
        
        output_file = f"./output/alt_{test['name']}.mp3"
        
        try:
            communicate = edge_tts.Communicate(
                text=test['text'],
                voice="zh-CN-XiaoxiaoNeural"
            )
            await communicate.save(output_file)
            
            if os.path.exists(output_file):
                size = os.path.getsize(output_file)
                print(f"✅ 成功: {size:,} bytes")
            else:
                print("❌ 失败: 文件未生成")
                
        except Exception as e:
            print(f"❌ 错误: {e}")

async def main():
    print("🔍 SSML标签朗读问题专项验证")
    print("=" * 70)
    
    # 1. 针对性测试
    results = await targeted_verification()
    
    # 2. 详细对比分析
    create_detailed_comparison(results)
    
    # 3. 播放指导
    generate_playback_instructions(results)
    
    # 4. 替代方法测试
    await alternative_testing()
    
    print(f"\n" + "=" * 70)
    print("📋 验证总结:")
    print("1. 请仔细聆听生成的音频文件")
    print("2. 对比不同版本的长度和内容")
    print("3. 确认是否真的听到了标签词汇")
    print("4. 如发现问题，请提供具体的听感描述")

if __name__ == "__main__":
    asyncio.run(main())