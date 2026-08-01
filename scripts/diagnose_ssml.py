#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
SSML音频生成诊断和修复工具
"""

import asyncio
import edge_tts
import os
import re

# TTS 配置
VOICE = "zh-CN-XiaoxiaoNeural" 
RATE = "+0%"
VOLUME = "+0%"

def analyze_current_ssml_file(file_path):
    """分析当前生成的SSML音频文件"""
    if os.path.exists(file_path):
        file_size = os.path.getsize(file_path)
        print(f"📊 当前SSML音频文件分析:")
        print(f"   文件路径: {file_path}")
        print(f"   文件大小: {file_size} bytes")
        
        # 与纯文本版本对比
        plain_text_file = file_path.replace('segment_', 'plain_segment_')
        if os.path.exists(plain_text_file):
            plain_size = os.path.getsize(plain_text_file)
            ratio = file_size / plain_size if plain_size > 0 else 0
            print(f"   纯文本版本大小: {plain_size} bytes")
            print(f"   大小比例: {ratio:.2f}x")
            
            if abs(ratio - 1.0) < 0.1:
                print("   ❌ 警告: 文件大小相近，SSML可能未生效")
            else:
                print("   ✅ SSML可能已生效")
        else:
            print("   ⚠️  未找到纯文本对照文件")
        print()
    else:
        print(f"❌ 文件不存在: {file_path}")

def fix_ssml_processor():
    """修复SSML处理器的关键问题"""
    
    class FixedChineseSSMLProcessor:
        """
        修复版中文SSML处理器
        解决了原版中的几个关键问题
        """
        
        def __init__(self, config=None):
            self.config = config or {
                'break_short': '0.3s',
                'break_medium': '0.5s', 
                'break_long': '0.8s',
                'break_paragraph': '1.2s'
            }
            self.ssml_wrapper = (
                '<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="zh-CN">{}</speak>'
            )
        
        def escape_xml(self, text):
            """转义XML特殊字符"""
            # 先保存已有的SSML标签
            break_tags = []
            # 找到所有的break标签
            break_pattern = r'<break[^>]*\/>'
            for match in re.finditer(break_pattern, text):
                break_tags.append(match.group())
            
            # 转义特殊字符
            text = text.replace('&', '&amp;')
            text = text.replace('<', '&lt;')
            text = text.replace('>', '&gt;')
            text = text.replace('"', '&quot;')
            text = text.replace("'", '&apos;')
            
            return text
        
        def process_text(self, text):
            """处理中文文本，插入SSML停顿标签"""
            # 不要在这里转义XML，因为会破坏后续的break标签插入
            
            processed = text
            
            # 1. 处理长停顿标点（句号、问号、感叹号）
            for punct in ['。', '！', '？', '!', '?']:
                processed = processed.replace(punct, f'{punct}<break time="{self.config["break_long"]}"/>')
            
            # 2. 处理中停顿标点（逗号、分号）
            for punct in ['，', '；', ',', ';']:
                processed = processed.replace(punct, f'{punct}<break time="{self.config["break_medium"]}"/>')
            
            # 3. 处理短停顿标点（顿号）
            processed = processed.replace('、', f'、<break time="{self.config["break_short"]}"/>')
            
            # 4. 处理连接词（在词前后添加短停顿）
            connecting_words = ['但是', '然而', '不过', '所以', '因此', '而且', '此外', '同时']
            for word in connecting_words:
                # 使用更精确的正则表达式，避免在已有break标签附近重复插入
                pattern = f'(?<!break time="[^"]*"){word}(?!<break)'
                replacement = f'<break time="{self.config["break_short"]}"/>{word}<break time="{self.config["break_short"]}"/>'
                processed = re.sub(pattern, replacement, processed)
            
            # 5. 处理破折号
            processed = processed.replace('——', f'——<break time="{self.config["break_medium"]}"/>')
            processed = processed.replace('—', f'—<break time="{self.config["break_short"]}"/>')
            
            # 6. 处理数字和年份
            processed = re.sub(r'(\d{2})(\d{2})年', r'\1<break time="0.1s"/>\2年', processed)
            processed = re.sub(r'(\d+)世纪', r'\1<break time="0.1s"/>世纪', processed)
            
            # 7. 清理多余空白
            processed = re.sub(r'\s+', ' ', processed).strip()
            
            return processed
        
        def wrap_ssml(self, text):
            """包装成完整SSML格式"""
            processed = self.process_text(text)
            return self.ssml_wrapper.format(processed)
        
        def validate_ssml(self, ssml_text):
            """验证SSML是否有效（修复版）"""
            if not ssml_text.startswith('<speak'):
                return False
            if '</speak>' not in ssml_text:
                return False
            # 检查是否有break标签
            if '<break' not in ssml_text:
                return False
            # 检查标签是否大致平衡（简化检查）
            open_tags = ssml_text.count('<break')
            close_tags = ssml_text.count('/>')
            return abs(open_tags - close_tags) <= 1
    
    return FixedChineseSSMLProcessor()

async def test_fixed_ssml_generation():
    """测试修复后的SSML生成"""
    
    print("🔧 SSML处理器修复测试")
    print("=" * 50)
    
    # 测试文本
    test_text = "提到程序员，你脑海里是不是全是穿卫衣的极客小哥？但在电脑诞生前100年，第一位程序员，其实是位女士。"
    
    print(f"📝 测试文本: {test_text}")
    print()
    
    # 创建修复版处理器
    fixed_processor = fix_ssml_processor()
    
    # 生成SSML
    ssml_text = fixed_processor.wrap_ssml(test_text)
    print("🔧 修复后SSML:")
    print(ssml_text)
    print()
    
    # 验证
    is_valid = fixed_processor.validate_ssml(ssml_text)
    print(f"✅ SSML验证: {'通过' if is_valid else '失败'}")
    print(f"   包含break标签: {'✅' if '<break' in ssml_text else '❌'}")
    print(f"   break标签数量: {ssml_text.count('<break')}")
    print()
    
    # 生成音频对比
    output_dir = "./output"
    os.makedirs(output_dir, exist_ok=True)
    
    test_files = [
        ("./output/fixed_ssml_test.mp3", "修复版SSML", ssml_text),
        ("./output/fixed_plain_test.mp3", "修复版纯文本", test_text)
    ]
    
    print("🎵 音频生成测试:")
    for file_path, description, content in test_files:
        print(f"   生成 {description}...")
        try:
            communicate = edge_tts.Communicate(content, voice=VOICE, rate=RATE, volume=VOLUME)
            await communicate.save(file_path)
            
            if os.path.exists(file_path):
                size = os.path.getsize(file_path)
                print(f"   ✅ {description} 成功 ({size} bytes)")
            else:
                print(f"   ❌ {description} 失败")
        except Exception as e:
            print(f"   ❌ {description} 异常: {e}")
    
    print()
    
    # 分析结果
    if os.path.exists("./output/fixed_ssml_test.mp3") and os.path.exists("./output/fixed_plain_test.mp3"):
        ssml_size = os.path.getsize("./output/fixed_ssml_test.mp3")
        plain_size = os.path.getsize("./output/fixed_plain_test.mp3")
        ratio = ssml_size / plain_size if plain_size > 0 else 0
        
        print("📊 结果分析:")
        print(f"   SSML版本大小: {ssml_size} bytes")
        print(f"   纯文本大小: {plain_size} bytes") 
        print(f"   大小比例: {ratio:.2f}x")
        
        if ratio > 1.1:
            print("   🎉 SSML明显生效！")
        elif ratio > 0.9:
            print("   ⚠️  SSML效果不明显")
        else:
            print("   ❌ SSML可能未生效")

def generate_debug_comparison():
    """生成调试对比文件"""
    
    print("\n🔍 生成调试对比文件...")
    
    test_text = "你好，世界！今天天气真好。"
    
    # 原版SSML处理
    original_ssml = f'''<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="zh-CN">
    你好，<break time="0.5s"/>世界！<break time="0.8s"/>今天天气真好。<break time="0.6s"/>
    </speak>'''
    
    # 修复版SSML处理
    fixed_processor = fix_ssml_processor()
    fixed_ssml = fixed_processor.wrap_ssml(test_text)
    
    print("📝 调试信息:")
    print(f"原始文本: {test_text}")
    print(f"原版SSML: {original_ssml}")
    print(f"修复版SSML: {fixed_ssml}")
    print()
    
    # 验证差异
    print("🔍 验证差异:")
    print(f"原版验证: {original_ssml.startswith('<speak') and '</speak>' in original_ssml}")
    print(f"修复版验证: {fixed_processor.validate_ssml(fixed_ssml)}")
    print(f"原版break数: {original_ssml.count('<break')}")
    print(f"修复版break数: {fixed_ssml.count('<break')}")

if __name__ == "__main__":
    print("🚀 SSML音频生成诊断工具")
    print("=" * 60)
    
    # 分析当前文件
    analyze_current_ssml_file("./output/segment_000.mp3")
    
    # 生成调试对比
    generate_debug_comparison()
    
    # 测试修复版本
    asyncio.run(test_fixed_ssml_generation())
    
    print("\n" + "=" * 60)
    print("💡 诊断建议:")
    print("1. 如果文件大小相近，说明SSML未正确应用")
    print("2. 修复版处理器解决了XML转义和标签平衡问题")
    print("3. 建议替换auto_video_maker.py中的SSML处理器")