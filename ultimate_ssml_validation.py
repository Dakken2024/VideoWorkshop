#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
终极SSML验证：实际播放测试 + 源码深度分析
"""

import asyncio
import edge_tts
import os
import subprocess
import time

def play_audio_and_listen(file_path, description):
    """播放音频并等待用户反馈"""
    print(f"\n🔊 播放测试: {description}")
    print(f"文件: {file_path}")
    
    try:
        # 尝试播放音频（Windows）
        if os.name == 'nt':  # Windows
            os.startfile(file_path)
        else:  # Linux/Mac
            subprocess.run(['xdg-open', file_path], check=True)
        
        print("请仔细聆听音频内容...")
        time.sleep(2)  # 给播放器启动时间
        
        # 询问用户反馈
        print("\n请判断以下问题：")
        print("1. 是否听到了'break'、'time'等标签词汇？(y/n)")
        print("2. 是否听到了明显的停顿效果？(y/n)")
        print("3. 语音是否自然流畅？(y/n)")
        
        # 简化版本：直接输出文件信息供手动检查
        print(f"\n📋 文件信息:")
        print(f"   路径: {os.path.abspath(file_path)}")
        print(f"   大小: {os.path.getsize(file_path):,} bytes")
        print(f"   修改时间: {time.ctime(os.path.getmtime(file_path))}")
        
    except Exception as e:
        print(f"播放失败: {e}")

async def ultimate_ssml_test():
    """终极SSML测试"""
    
    print("🎯 终极SSML兼容性验证")
    print("=" * 60)
    
    # 创建测试用例
    test_cases = [
        {
            'name': 'control_plain',
            'text': '你好世界今天天气真好',
            'description': '纯文本控制组'
        },
        {
            'name': 'ssml_simple',
            'text': '你好<break time="1s"/>世界<break time="0.5s"/>今天天气真好',
            'description': '简单SSML标签测试'
        },
        {
            'name': 'ssml_complex', 
            'text': '''<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="zh-CN">
            你好<break time="0.5s"/>世界<break time="1s"/>今天天气<prosody rate="slow">真好</prosody>
            </speak>''',
            'description': '复杂SSML结构测试'
        },
        {
            'name': 'chinese_natural',
            'text': '你好，世界！今天天气真好。',
            'description': '中文自然标点测试'
        }
    ]
    
    generated_files = []
    
    # 生成所有测试音频
    for case in test_cases:
        print(f"\n🧪 生成测试: {case['description']}")
        print(f"文本: {case['text']}")
        
        output_file = f"./output/ultimate_test_{case['name']}.mp3"
        
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
                
                generated_files.append({
                    'name': case['name'],
                    'file': output_file,
                    'description': case['description'],
                    'text': case['text'],
                    'size': size
                })
            else:
                print("❌ 文件生成失败")
                
        except Exception as e:
            print(f"❌ 生成错误: {e}")
    
    return generated_files

def analyze_detailed_results(files):
    """详细结果分析"""
    
    print("\n📊 详细结果分析")
    print("=" * 60)
    
    if not files:
        print("❌ 没有生成的文件可供分析")
        return
    
    # 找到控制组
    control_file = next((f for f in files if f['name'] == 'control_plain'), None)
    
    if control_file:
        baseline_size = control_file['size']
        print(f"🎯 控制组基准: {control_file['description']}")
        print(f"   文件大小: {baseline_size:,} bytes")
        
        print(f"\n📈 各测试对比:")
        for file_info in files:
            if file_info != control_file:
                ratio = file_info['size'] / baseline_size
                print(f"\n{file_info['description']}:")
                print(f"   文件: {os.path.basename(file_info['file'])}")
                print(f"   大小: {file_info['size']:,} bytes ({ratio:.2f}x)")
                print(f"   文本: {file_info['text'][:50]}{'...' if len(file_info['text']) > 50 else ''}")
                
                # 基于大小的初步判断
                if 'ssml' in file_info['name']:
                    if ratio > 3.0:
                        print("   🔍 初步判断: SSML可能被正确处理")
                    elif ratio > 1.5:
                        print("   ⚠️  初步判断: SSML部分生效")
                    else:
                        print("   ❌ 初步判断: SSML可能未生效")
    
    # 提供播放指导
    print(f"\n🔊 手动验证指南:")
    print("=" * 40)
    for file_info in files:
        print(f"\n文件: {os.path.basename(file_info['file'])}")
        print(f"描述: {file_info['description']}")
        print(f"预期效果:")
        if 'ssml_simple' in file_info['name']:
            print("   - 应该听到: '你好' [1秒停顿] '世界' [0.5秒停顿] '今天天气真好'")
            print("   - 不应该听到: 'break'、'time'等标签词汇")
        elif 'ssml_complex' in file_info['name']:
            print("   - 应该听到: 完整的SSML结构被正确解析")
            print("   - 后半部分语速应该变慢")
        elif 'chinese_natural' in file_info['name']:
            print("   - 应该听到: 自然的中文标点停顿")
        else:
            print("   - 应该听到: 纯净的文本朗读，无额外停顿")

def investigate_edge_tts_source():
    """深入调查edge-tts源码"""
    
    print("\n🔍 edge-tts源码深度调查")
    print("=" * 60)
    
    try:
        import edge_tts
        import inspect
        
        # 获取communicate.py的源码
        comm_module = edge_tts.communicate
        comm_class = comm_module.Communicate
        
        print("正在分析Communicate类源码...")
        
        # 获取源码
        try:
            source_lines = inspect.getsourcelines(comm_class)
            source_code = ''.join(source_lines[0])
            
            print(f"✅ 成功获取源码 ({len(source_lines[0])} 行)")
            
            # 关键词搜索
            keywords = {
                'ssml': source_code.count('ssml'),
                'xml': source_code.count('xml'), 
                'break': source_code.count('break'),
                'prosody': source_code.count('prosody'),
                'speak': source_code.count('speak')
            }
            
            print(f"\n源码关键词统计:")
            for keyword, count in keywords.items():
                print(f"  {keyword}: {count} 次")
            
            # 查找关键处理逻辑
            print(f"\n🔍 关键处理逻辑分析:")
            
            # 查找文本处理相关代码
            if 'def _run(' in source_code:
                print("✅ 找到_run方法 - 主要执行逻辑")
            
            if 'websocket' in source_code.lower():
                print("✅ 使用WebSocket通信 - 实时流式处理")
            
            if 'TRUSTED_CLIENT_TOKEN' in source_code:
                print("✅ 使用可信客户端令牌 - 微软官方接口")
                
            # 检查是否有SSML特殊处理
            ssml_indicators = ['<speak', '</speak>', 'ssml=True', 'use_ssml']
            found_indicators = [ind for ind in ssml_indicators if ind in source_code]
            
            if found_indicators:
                print(f"✅ 发现SSML处理指示器: {found_indicators}")
            else:
                print("⚠️  未发现明确的SSML处理代码")
                print("   可能通过文本内容自动识别SSML")
            
        except Exception as e:
            print(f"❌ 源码分析失败: {e}")
            
    except Exception as e:
        print(f"❌ 模块分析失败: {e}")

async def main():
    print("🔍 终极SSML兼容性深度验证")
    print("=" * 70)
    
    # 1. 执行终极测试
    generated_files = await ultimate_ssml_test()
    
    # 2. 详细结果分析
    analyze_detailed_results(generated_files)
    
    # 3. 源码深度调查
    investigate_edge_tts_source()
    
    # 4. 提供验证指导
    print(f"\n📋 验证操作指南:")
    print("=" * 50)
    print("请按以下步骤手动验证音频文件:")
    print("1. 打开output目录")
    print("2. 按顺序播放生成的MP3文件")
    print("3. 仔细聆听是否听到标签词汇")
    print("4. 注意停顿效果是否符合预期")
    print("5. 对比纯文本和SSML版本的差异")
    
    print(f"\n🎯 关键验证点:")
    print("- SSML版本应该比纯文本版本明显更长")
    print("- 应该能听到合理的停顿，而不是标签词汇")
    print("- 语音应该自然流畅，无机械感")

if __name__ == "__main__":
    asyncio.run(main())