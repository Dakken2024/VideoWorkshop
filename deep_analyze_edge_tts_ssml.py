#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
edge-tts SSML中文兼容性深度分析工具
"""

import asyncio
import edge_tts
import inspect
import re
from typing import Optional, Union

def analyze_edge_tts_source():
    """分析edge-tts源码结构"""
    
    print("🔍 edge-tts源码结构分析")
    print("=" * 50)
    
    try:
        # 获取edge-tts模块信息
        print(f"edge-tts版本: {getattr(edge_tts, '__version__', '未知')}")
        print(f"模块位置: {edge_tts.__file__}")
        print()
        
        # 分析Communicate类
        if hasattr(edge_tts, 'Communicate'):
            comm_class = edge_tts.Communicate
            print("Communicate类分析:")
            print(f"  类定义: {comm_class}")
            
            # 获取构造函数签名
            if hasattr(comm_class, '__init__'):
                sig = inspect.signature(comm_class.__init__)
                print(f"  构造函数参数: {sig}")
                
                # 检查支持的参数
                supported_params = list(sig.parameters.keys())
                print(f"  支持参数: {supported_params}")
                
                # 特别检查SSML相关参数
                ssml_related = [param for param in supported_params if 'ssml' in param.lower()]
                print(f"  SSML相关参数: {ssml_related if ssml_related else '未发现'}")
            
            # 检查方法
            methods = [method for method in dir(comm_class) if not method.startswith('_')]
            print(f"  公共方法: {methods}")
            
        else:
            print("❌ 未找到Communicate类")
            
    except Exception as e:
        print(f"❌ 源码分析失败: {e}")

def test_edge_tts_ssml_capabilities():
    """测试edge-tts对SSML的支持能力"""
    
    print("\n🧪 edge-tts SSML支持能力测试")
    print("=" * 50)
    
    test_cases = [
        {
            'name': '纯文本测试',
            'text': '你好世界',
            'description': '基准测试 - 纯文本'
        },
        {
            'name': '简单break标签',
            'text': '你好<break time="1s"/>世界',
            'description': '最基本的SSML break标签'
        },
        {
            'name': '完整SSML包装',
            'text': '''<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="zh-CN">
            你好<break time="0.5s"/>世界
            </speak>''',
            'description': '完整的SSML文档结构'
        },
        {
            'name': '多个break标签',
            'text': '提到程序员，<break time="0.4s"/>你脑海里<break time="0.3s"/>是不是全是<break time="0.5s"/>穿卫衣的极客小哥？',
            'description': '多个停顿标签测试'
        },
        {
            'name': '中文标点符号',
            'text': '你好，世界！今天天气真好。',
            'description': '中文标点符号自然停顿'
        }
    ]
    
    results = []
    
    for i, case in enumerate(test_cases):
        print(f"\n测试 {i+1}: {case['name']}")
        print(f"描述: {case['description']}")
        print(f"文本长度: {len(case['text'])} 字符")
        
        try:
            # 测试音频生成
            output_file = f"./output/edge_tts_test_{i+1}.mp3"
            
            async def generate_test():
                communicate = edge_tts.Communicate(
                    case['text'], 
                    voice="zh-CN-XiaoxiaoNeural",
                    rate="+0%",
                    volume="+0%"
                )
                await communicate.save(output_file)
                return output_file
            
            # 运行异步测试
            result_file = asyncio.run(generate_test())
            
            # 检查结果
            import os
            if os.path.exists(result_file):
                file_size = os.path.getsize(result_file)
                print(f"✅ 生成成功: {file_size:,} bytes")
                
                results.append({
                    'name': case['name'],
                    'success': True,
                    'file_size': file_size,
                    'text_length': len(case['text'])
                })
            else:
                print("❌ 文件未生成")
                results.append({
                    'name': case['name'],
                    'success': False,
                    'file_size': 0,
                    'text_length': len(case['text'])
                })
                
        except Exception as e:
            print(f"❌ 生成失败: {e}")
            results.append({
                'name': case['name'],
                'success': False,
                'error': str(e),
                'text_length': len(case['text'])
            })
    
    return results

def analyze_ssml_parsing_behavior():
    """分析SSML解析行为"""
    
    print("\n🔍 SSML解析行为分析")
    print("=" * 50)
    
    # 测试不同格式的SSML
    ssml_tests = [
        ('简单标签', '<break time="1s"/>'),
        ('自闭合标签', '<break time="1s"></break>'),
        ('带属性标签', '<prosody rate="slow">慢速</prosody>'),
        ('嵌套标签', '<emphasis level="strong">强调<break time="0.5s"/>内容</emphasis>'),
        ('完整文档', '''<speak><p>第一段<break time="1s"/></p><p>第二段</p></speak>''')
    ]
    
    for name, ssml_fragment in ssml_tests:
        print(f"\n{name}: {ssml_fragment}")
        
        # 分析标签结构
        tags = re.findall(r'<[^>]+>', ssml_fragment)
        print(f"  发现标签: {tags}")
        
        # 检查自闭合标签
        self_closing = [tag for tag in tags if tag.endswith('/>')]
        print(f"  自闭合标签: {self_closing}")
        
        # 检查配对标签
        opening_tags = [tag for tag in tags if not tag.endswith('/>') and not tag.startswith('</')]
        closing_tags = [tag for tag in tags if tag.startswith('</')]
        print(f"  开标签: {opening_tags}")
        print(f"  闭标签: {closing_tags}")

def test_chinese_specific_features():
    """测试中文特有功能"""
    
    print("\n🇨🇳 中文特有功能测试")
    print("=" * 50)
    
    chinese_tests = [
        {
            'name': '中文数字处理',
            'text': '2024年是一个重要的年份',
            'description': '测试数字和年份的自然处理'
        },
        {
            'name': '中文标点停顿',
            'text': '你好，世界！今天天气真好。',
            'description': '测试中文标点符号的自然停顿'
        },
        {
            'name': '混合中英文',
            'text': 'Hello你好，World世界！Today今天weather天气great很好。',
            'description': '测试中英文混合文本'
        },
        {
            'name': '中文语气词',
            'text': '嗯...那个...其实...是这样的',
            'description': '测试语气词和停顿'
        }
    ]
    
    for i, test in enumerate(chinese_tests):
        print(f"\n测试 {i+1}: {test['name']}")
        print(f"描述: {test['description']}")
        print(f"文本: {test['text']}")
        
        # 分析文本特征
        chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', test['text']))
        punctuation = len(re.findall(r'[，。！？；：""''（）【】]', test['text']))
        english_words = len(re.findall(r'[a-zA-Z]+', test['text']))
        
        print(f"  中文字符: {chinese_chars}")
        print(f"  中文标点: {punctuation}")
        print(f"  英文单词: {english_words}")

def generate_compatibility_report(results):
    """生成兼容性报告"""
    
    print("\n📊 edge-tts SSML兼容性报告")
    print("=" * 60)
    
    # 统计成功率
    total_tests = len(results)
    successful_tests = sum(1 for r in results if r['success'])
    success_rate = successful_tests / total_tests if total_tests > 0 else 0
    
    print(f"总体成功率: {success_rate:.1%} ({successful_tests}/{total_tests})")
    
    # 分析文件大小差异
    if successful_tests > 1:
        sizes = [r['file_size'] for r in results if r['success']]
        pure_text_size = next((r['file_size'] for r in results if r['name'] == '纯文本测试' and r['success']), 0)
        
        if pure_text_size > 0:
            print(f"\n文件大小分析:")
            print(f"  纯文本基准: {pure_text_size:,} bytes")
            
            for result in results:
                if result['success'] and result['name'] != '纯文本测试':
                    ratio = result['file_size'] / pure_text_size
                    print(f"  {result['name']}: {result['file_size']:,} bytes ({ratio:.2f}x)")
    
    # 兼容性评估
    print(f"\n兼容性评估:")
    
    # 检查基本SSML支持
    break_support = any(r['success'] and 'break' in r['name'].lower() for r in results)
    full_ssml_support = any(r['success'] and '完整' in r['name'] for r in results)
    
    if break_support:
        print("✅ 基本SSML break标签支持")
    else:
        print("❌ 基本SSML break标签不支持")
    
    if full_ssml_support:
        print("✅ 完整SSML文档结构支持")
    else:
        print("⚠️  完整SSML文档结构可能不完全支持")
    
    # 建议
    print(f"\n💡 使用建议:")
    if break_support:
        print("  • 推荐使用简单的<break time=\"Xs\"/>标签")
        print("  • 避免复杂的SSML结构")
        print("  • 直接在文本中插入break标签效果最佳")
    else:
        print("  • edge-tts对SSML支持有限")
        print("  • 建议使用纯文本配合自然语调")

async def advanced_ssml_testing():
    """高级SSML测试"""
    
    print("\n🔬 高级SSML功能测试")
    print("=" * 50)
    
    # 测试不同的voice参数组合
    voice_tests = [
        ("zh-CN-XiaoxiaoNeural", "女声，自然"),
        ("zh-CN-YunxiNeural", "男声，沉稳"),
        ("zh-CN-XiaohanNeural", "女声，活力")
    ]
    
    test_text = "你好<break time=\"0.5s\"/>世界<break time=\"1s\"/>今天天气真好"
    
    for voice, description in voice_tests:
        print(f"\n🎤 语音: {voice} ({description})")
        
        try:
            output_file = f"./output/voice_test_{voice.replace('-', '_')}.mp3"
            communicate = edge_tts.Communicate(
                test_text,
                voice=voice,
                rate="+0%",
                volume="+0%"
            )
            await communicate.save(output_file)
            
            import os
            if os.path.exists(output_file):
                size = os.path.getsize(output_file)
                print(f"  ✅ 成功生成: {size:,} bytes")
            else:
                print("  ❌ 生成失败")
                
        except Exception as e:
            print(f"  ❌ 错误: {e}")

if __name__ == "__main__":
    print("🚀 edge-tts SSML中文兼容性深度分析")
    print("=" * 70)
    
    # 1. 源码结构分析
    analyze_edge_tts_source()
    
    # 2. SSML支持能力测试
    results = test_edge_tts_ssml_capabilities()
    
    # 3. SSML解析行为分析
    analyze_ssml_parsing_behavior()
    
    # 4. 中文特有功能测试
    test_chinese_specific_features()
    
    # 5. 生成兼容性报告
    generate_compatibility_report(results)
    
    # 6. 高级测试
    asyncio.run(advanced_ssml_testing())
    
    print("\n" + "=" * 70)
    print("🎯 分析完成！")
    print("该工具帮助您深入了解edge-tts对SSML的支持程度和最佳实践")