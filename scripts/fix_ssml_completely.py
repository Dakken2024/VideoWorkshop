#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
SSML问题根本原因分析和最终修复方案
"""

import asyncio
import edge_tts
import os
import re

def analyze_root_cause():
    """分析SSML失效的根本原因"""
    
    print("🔍 SSML失效根本原因分析")
    print("=" * 50)
    
    causes = [
        {
            "问题": "XML转义时机错误",
            "描述": "在插入break标签前就进行了XML转义，导致标签被破坏",
            "证据": "原版代码先escape_xml()再插入break标签",
            "影响": "所有SSML标签都被转义成&amp;lt;break&amp;gt;"
        },
        {
            "问题": "SSML验证逻辑有缺陷", 
            "描述": "validate_ssml方法检查过于严格且不准确",
            "证据": "检查标签平衡的方式有误",
            "影响": "即使SSML正确也可能被判定为无效"
        },
        {
            "问题": "正则表达式复杂度过高",
            "描述": "连接词处理的正则表达式过于复杂且有语法错误",
            "证据": "look-behind模式要求固定宽度",
            "影响": "处理器可能在正则阶段就报错"
        },
        {
            "问题": "edge-tts实际不支持复杂SSML",
            "描述": "尽管传入SSML格式，edge-tts可能只识别简单的break标签",
            "证据": "需要对比文件大小来验证实际效果",
            "影响": "复杂SSML特性可能被忽略"
        }
    ]
    
    for i, cause in enumerate(causes, 1):
        print(f"\n{i}. {cause['问题']}")
        print(f"   描述: {cause['描述']}")
        print(f"   证据: {cause['证据']}")
        print(f"   影响: {cause['影响']}")

def provide_fixed_solution():
    """提供修复方案"""
    
    print("\n🔧 最终修复方案")
    print("=" * 50)
    
    print("""
核心修复要点：

1. 简化SSML处理器逻辑
   - 移除复杂的XML转义处理
   - 简化标签验证逻辑
   - 使用更可靠的正则表达式

2. 修改调用方式
   - 直接传入带break标签的文本
   - 不使用完整的<speak>包装
   - 让edge-tts自动处理SSML识别

3. 验证机制改进
   - 通过文件大小对比验证效果
   - 添加实际音频播放测试
   - 简化验证条件
    """)
    
    # 创建简化版SSML处理器
    class SimplifiedSSMLProcessor:
        def __init__(self):
            self.break_times = {
                '。': '0.8s', '！': '0.8s', '？': '0.8s',
                '，': '0.5s', '；': '0.5s', 
                '、': '0.3s'
            }
        
        def add_breaks(self, text):
            """简单添加break标签"""
            result = text
            # 按优先级添加停顿
            for punct, time in self.break_times.items():
                result = result.replace(punct, f'{punct}<break time="{time}"/>')
            return result
        
        def is_effective(self, ssml_text):
            """简单验证是否包含break标签"""
            return '<break' in ssml_text and 'time="' in ssml_text

    return SimplifiedSSMLProcessor()

async def test_final_fix():
    """测试最终修复方案"""
    
    print("\n🧪 最终修复方案测试")
    print("=" * 50)
    
    # 测试文本
    test_text = "提到程序员，你脑海里是不是全是穿卫衣的极客小哥？但在电脑诞生前100年，第一位程序员，其实是位女士。"
    
    print(f"📝 原始文本: {test_text}")
    
    # 使用简化处理器
    processor = provide_fixed_solution()
    enhanced_text = processor.add_breaks(test_text)
    
    print(f"\n🔧 增强文本: {enhanced_text}")
    print(f"✅ 包含break标签: {processor.is_effective(enhanced_text)}")
    print(f"✅ break标签数量: {enhanced_text.count('<break')}")
    
    # 生成对比音频
    print("\n🎵 生成对比音频...")
    
    try:
        # SSML版本
        print("   生成SSML版本...")
        communicate_ssml = edge_tts.Communicate(enhanced_text, voice="zh-CN-XiaoxiaoNeural")
        await communicate_ssml.save("./output/final_fix_ssml.mp3")
        
        # 纯文本版本
        print("   生成纯文本版本...")
        communicate_plain = edge_tts.Communicate(test_text, voice="zh-CN-XiaoxiaoNeural") 
        await communicate_plain.save("./output/final_fix_plain.mp3")
        
        # 分析结果
        if os.path.exists("./output/final_fix_ssml.mp3") and os.path.exists("./output/final_fix_plain.mp3"):
            ssml_size = os.path.getsize("./output/final_fix_ssml.mp3")
            plain_size = os.path.getsize("./output/final_fix_plain.mp3")
            ratio = ssml_size / plain_size
            
            print(f"\n📊 结果分析:")
            print(f"   SSML版本: {ssml_size} bytes")
            print(f"   纯文本版: {plain_size} bytes")
            print(f"   大小比例: {ratio:.2f}x")
            
            if ratio >= 1.2:
                print("   🎉 SSML显著生效！")
                return True
            elif ratio >= 1.05:
                print("   ✅ SSML轻微生效")
                return True
            else:
                print("   ❌ SSML未生效")
                return False
        else:
            print("   ❌ 文件生成失败")
            return False
            
    except Exception as e:
        print(f"   ❌ 生成过程出错: {e}")
        return False

def generate_fixed_auto_video_maker():
    """生成修复后的auto_video_maker.py关键部分"""
    
    print("\n📋 修复后的关键代码")
    print("=" * 50)
    
    fixed_code = '''
# ================= 修复版SSML处理器 =================

class ChineseSSMLProcessor:
    """简化版中文SSML处理器"""
    
    def __init__(self):
        self.break_config = {
            '。': '0.8s', '！': '0.8s', '？': '0.8s',  # 长停顿
            '，': '0.5s', '；': '0.5s',               # 中停顿  
            '、': '0.3s'                              # 短停顿
        }
    
    def enhance_text(self, text):
        """为文本添加SSML停顿标签"""
        result = text
        for punct, break_time in self.break_config.items():
            result = result.replace(punct, f'{punct}<break time="{break_time}"/>')
        return result
    
    def is_valid_enhanced(self, text):
        """检查文本是否包含有效的break标签"""
        return '<break' in text and 'time="' in text

# ================= 修复版音频生成器 =================

class AudioGenerator:
    def __init__(self, use_ssml=True):
        self.use_ssml = use_ssml
        self.ssml_processor = ChineseSSMLProcessor() if use_ssml else None
    
    async def generate_segment(self, text, output_file, scene_id=None):
        """生成音频片段（修复版）"""
        scene_info = f"场景 {scene_id}" if scene_id else "未知场景"
        
        # 直接使用增强文本，不进行复杂验证
        if self.use_ssml and self.ssml_processor:
            enhanced_text = self.ssml_processor.enhance_text(text)
            try:
                communicate = edge_tts.Communicate(enhanced_text, voice="zh-CN-XiaoxiaoNeural")
                await communicate.save(output_file)
                
                if os.path.exists(output_file) and os.path.getsize(output_file) > 1000:
                    log('SUCCESS', f'{scene_info}: SSML音频生成成功')
                    return True
            except Exception as e:
                log('WARNING', f'{scene_info}: SSML模式失败，回退到普通模式')
        
        # 回退到普通模式
        try:
            communicate = edge_tts.Communicate(text, voice="zh-CN-XiaoxiaoNeural")
            await communicate.save(output_file)
            log('SUCCESS', f'{scene_info}: 普通音频生成成功')
            return True
        except Exception as e:
            log('ERROR', f'{scene_info}: 音频生成失败 - {e}')
            return False
'''
    
    print("修复后的SSML处理器代码:")
    print(fixed_code)

if __name__ == "__main__":
    print("🚀 SSML问题根本原因分析和修复")
    print("=" * 60)
    
    # 分析根本原因
    analyze_root_cause()
    
    # 展示修复方案
    generate_fixed_auto_video_maker()
    
    # 测试修复效果
    success = asyncio.run(test_final_fix())
    
    print("\n" + "=" * 60)
    if success:
        print("🎉 修复方案验证成功！")
        print("建议立即替换auto_video_maker.py中的SSML相关代码")
    else:
        print("❌ 修复方案仍需调整")
        print("可能需要进一步研究edge-tts对SSML的支持程度")