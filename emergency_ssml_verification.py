#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
紧急验证：SSML标签是否真的被朗读出来
"""

import asyncio
import edge_tts
import os

async def emergency_verification():
    """紧急验证SSML标签是否被朗读"""
    
    print("🚨 紧急验证：SSML标签朗读问题")
    print("=" * 50)
    
    # 测试用例1：明确包含break标签的文本
    test_text_1 = "你好<break time=\"1s\"/>世界"
    
    # 测试用例2：多个break标签
    test_text_2 = "提到程序员，<break time=\"0.4s\"/>你脑海里<break time=\"0.3s\"/>是不是全是<break time=\"0.5s\"/>穿卫衣的极客小哥？"
    
    # 测试用例3：纯文本对照
    test_text_3 = "你好世界"
    
    # 测试用例4：中文标点符号
    test_text_4 = "你好，世界！今天天气真好。"
    
    tests = [
        (test_text_1, "test_1_break_tag.mp3", "单个break标签测试"),
        (test_text_2, "test_2_multiple_breaks.mp3", "多个break标签测试"),
        (test_text_3, "test_3_plain_text.mp3", "纯文本对照"),
        (test_text_4, "test_4_chinese_punctuation.mp3", "中文标点测试")
    ]
    
    results = []
    
    for text, filename, description in tests:
        print(f"\n🧪 {description}")
        print(f"文本: {text}")
        print(f"长度: {len(text)} 字符")
        
        output_path = f"./output/{filename}"
        
        try:
            communicate = edge_tts.Communicate(
                text=text,
                voice="zh-CN-XiaoxiaoNeural",
                rate="+0%",
                volume="+0%"
            )
            await communicate.save(output_path)
            
            if os.path.exists(output_path):
                size = os.path.getsize(output_path)
                print(f"✅ 生成成功: {size:,} bytes")
                
                results.append({
                    'text': text,
                    'filename': filename,
                    'size': size,
                    'description': description,
                    'success': True
                })
            else:
                print("❌ 文件未生成")
                results.append({
                    'text': text,
                    'filename': filename,
                    'description': description,
                    'success': False
                })
                
        except Exception as e:
            print(f"❌ 生成失败: {e}")
            results.append({
                'text': text,
                'filename': filename,
                'description': description,
                'success': False,
                'error': str(e)
            })
    
    return results

def analyze_audio_files(results):
    """分析生成的音频文件"""
    
    print("\n🔍 音频文件分析")
    print("=" * 50)
    
    # 检查文件大小差异
    successful_results = [r for r in results if r['success']]
    
    if len(successful_results) >= 2:
        # 找到纯文本基准
        plain_text_result = next((r for r in successful_results if '纯文本' in r['description']), None)
        
        if plain_text_result:
            baseline_size = plain_text_result['size']
            print(f"📊 纯文本基准大小: {baseline_size:,} bytes")
            
            for result in successful_results:
                if result != plain_text_result:
                    ratio = result['size'] / baseline_size
                    print(f"\n文件: {result['filename']}")
                    print(f"  大小: {result['size']:,} bytes ({ratio:.2f}x)")
                    print(f"  描述: {result['description']}")
                    
                    # 判断是否可能朗读了标签
                    if ratio < 1.5 and 'break' in result['text']:
                        print("  ⚠️  警告: 大小增长不明显，可能标签被朗读")
                    elif ratio > 2.0:
                        print("  ✅ 正常: 大小显著增长，标签可能被正确处理")

def check_edge_tts_internals():
    """检查edge-tts内部实现"""
    
    print("\n🔧 edge-tts内部机制检查")
    print("=" * 50)
    
    try:
        import edge_tts
        import inspect
        
        # 检查communicate模块
        if hasattr(edge_tts, 'communicate'):
            comm_module = edge_tts.communicate
            print("✅ 找到communicate模块")
            
            # 检查Communicate类
            if hasattr(comm_module, 'Communicate'):
                comm_class = comm_module.Communicate
                print("✅ 找到Communicate类")
                
                # 检查源码位置
                try:
                    source_file = inspect.getsourcefile(comm_class)
                    print(f"源码位置: {source_file}")
                    
                    # 尝试获取源码
                    try:
                        source_lines = inspect.getsourcelines(comm_class)
                        print(f"源码行数: {len(source_lines[0])}")
                        
                        # 简单搜索SSML相关代码
                        source_text = ''.join(source_lines[0])
                        ssml_mentions = source_text.count('ssml')
                        xml_mentions = source_text.count('xml')
                        break_mentions = source_text.count('break')
                        
                        print(f"SSML相关提及: {ssml_mentions}")
                        print(f"XML相关提及: {xml_mentions}")
                        print(f"BREAK相关提及: {break_mentions}")
                        
                    except Exception as e:
                        print(f"无法获取源码详情: {e}")
                        
                except Exception as e:
                    print(f"无法获取源码位置: {e}")
            
        # 检查版本信息
        print(f"\n版本信息:")
        print(f"  edge-tts版本: {getattr(edge_tts, '__version__', '未知')}")
        
        # 检查其他相关信息
        module_attrs = [attr for attr in dir(edge_tts) if not attr.startswith('_')]
        print(f"  模块属性: {module_attrs[:10]}...")  # 显示前10个
        
    except Exception as e:
        print(f"❌ 内部检查失败: {e}")

async def test_alternative_approaches():
    """测试替代方法"""
    
    print("\n🧪 替代方法测试")
    print("=" * 50)
    
    # 测试1：使用不同的语音
    voices_to_test = [
        "zh-CN-XiaoxiaoNeural",
        "zh-CN-YunyangNeural", 
        "zh-CN-XiaoyiNeural"
    ]
    
    test_text = "你好<break time=\"0.5s\"/>世界"
    
    for voice in voices_to_test:
        print(f"\n🎤 测试语音: {voice}")
        output_file = f"./output/voice_test_{voice.replace('-', '_')}.mp3"
        
        try:
            communicate = edge_tts.Communicate(
                text=test_text,
                voice=voice,
                rate="+0%",
                volume="+0%"
            )
            await communicate.save(output_file)
            
            if os.path.exists(output_file):
                size = os.path.getsize(output_file)
                print(f"  ✅ 成功: {size:,} bytes")
            else:
                print("  ❌ 失败: 文件未生成")
                
        except Exception as e:
            print(f"  ❌ 错误: {e}")

async def main():
    print("🚀 SSML兼容性紧急验证")
    print("=" * 60)
    
    # 1. 紧急验证测试
    results = await emergency_verification()
    
    # 2. 音频文件分析
    analyze_audio_files(results)
    
    # 3. 内部机制检查
    check_edge_tts_internals()
    
    # 4. 替代方法测试
    await test_alternative_approaches()
    
    print("\n" + "=" * 60)
    print("🚨 紧急验证完成！")
    print("请仔细检查生成的音频文件，确认SSML标签是否被正确处理")

if __name__ == "__main__":
    asyncio.run(main())