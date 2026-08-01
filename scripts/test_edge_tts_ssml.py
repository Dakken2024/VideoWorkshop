import asyncio
import edge_tts

# TTS 配置
VOICE = "zh-CN-XiaoxiaoNeural" 
RATE = "+0%"
VOLUME = "+0%"

async def test_edge_tts_ssml_support():
    """测试edge-tts对SSML的支持"""
    
    test_cases = [
        # 测试1: 标准SSML格式
        {
            'name': '标准SSML',
            'text': '''<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="zh-CN">
            你好<break time="1s"/>世界
            </speak>''',
            'method': 'normal'
        },
        # 测试2: 简化SSML格式
        {
            'name': '简化SSML',
            'text': '<speak>你好<break time="1s"/>世界</speak>',
            'method': 'normal'
        },
        # 测试3: 纯文本对比
        {
            'name': '纯文本',
            'text': '你好世界',
            'method': 'normal'
        }
    ]
    
    for i, case in enumerate(test_cases):
        print(f"\n🧪 测试 {i+1}: {case['name']}")
        print(f"文本: {case['text']}")
        
        try:
            output_file = f"./output/edge_tts_test_{i+1}.mp3"
            
            if case['method'] == 'normal':
                communicate = edge_tts.Communicate(case['text'], voice=VOICE, rate=RATE, volume=VOLUME)
            else:
                # 尝试其他可能的方法
                communicate = edge_tts.Communicate(case['text'], voice=VOICE, rate=RATE, volume=VOLUME)
            
            await communicate.save(output_file)
            print(f"✅ 成功生成: {output_file}")
            
            # 检查文件大小
            import os
            size = os.path.getsize(output_file)
            print(f"📁 文件大小: {size} bytes")
            
        except Exception as e:
            print(f"❌ 失败: {e}")

async def test_manual_ssml_processing():
    """测试手动处理SSML的方法"""
    
    # 原始文本
    original_text = "提到程序员，你脑海里是不是全是穿卫衣的极客小哥？但在电脑诞生前 100 年，第一位程序员，其实是位女士。"
    
    # SSML版本
    ssml_text = '''<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="zh-CN">
    提到程序员，<break time="0.4s"/>你脑海里是不是全是穿卫衣的极客小哥？<break time="0.8s"/>
    但在电脑诞生前 100 年，<break time="0.4s"/>第一位程序员，<break time="0.4s"/>
    其实是位女士。<break time="0.8s"/>
    </speak>'''
    
    print("📝 原始文本处理测试:")
    
    try:
        # 方法1: 直接传入SSML
        print("方法1: 直接传入SSML文本")
        communicate1 = edge_tts.Communicate(ssml_text, voice=VOICE, rate=RATE, volume=VOLUME)
        await communicate1.save("./output/manual_ssml_direct.mp3")
        print("✅ 直接SSML方法成功")
        
        # 方法2: 传入纯文本（用于对比）
        print("方法2: 传入纯文本")
        communicate2 = edge_tts.Communicate(original_text, voice=VOICE, rate=RATE, volume=VOLUME)
        await communicate2.save("./output/manual_plain_text.mp3")
        print("✅ 纯文本方法成功")
        
    except Exception as e:
        print(f"❌ 处理失败: {e}")

if __name__ == "__main__":
    print("🔍 edge-tts SSML支持测试")
    print("="*50)
    
    asyncio.run(test_edge_tts_ssml_support())
    
    print("\n" + "="*50)
    print("🔧 手动SSML处理测试")
    print("="*50)
    
    asyncio.run(test_manual_ssml_processing())