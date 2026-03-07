import asyncio
import edge_tts
import re

# TTS 配置
VOICE = "zh-CN-XiaoxiaoNeural" 
RATE = "+0%"
VOLUME = "+0%"

def insert_ssml_breaks(text):
    """智能插入SSML停顿标签，提升语音情感表现力"""
    import re
    
    # SSML包装
    ssml_wrapper = '<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="zh-CN">{}</speak>'
    
    # 定义标点符号及其对应的停顿时长
    punctuation_breaks = {
        '。': '<break time="0.8s"/>',  # 句号 - 较长停顿
        '！': '<break time="0.8s"/>',  # 感叹号 - 较长停顿
        '？': '<break time="0.8s"/>',  # 问号 - 较长停顿
        '；': '<break time="0.6s"/>',  # 分号 - 中等停顿
        '，': '<break time="0.4s"/>',  # 逗号 - 短暂停顿
        '、': '<break time="0.3s"/>',  # 顿号 - 很短停顿
    }
    
    # 在主要标点符号后添加停顿
    processed_text = text
    for punct, break_tag in punctuation_breaks.items():
        # 使用正向先行断言避免在单词中间插入
        pattern = rf'{re.escape(punct)}(?=\s|\w|$)'
        processed_text = re.sub(pattern, f'{punct}{break_tag}', processed_text)
    
    # 处理破折号（表示强调或转折）
    processed_text = re.sub(r'——', '—<break time="0.5s"/>—', processed_text)
    processed_text = re.sub(r'—', '<break time="0.3s"/>—<break time="0.3s"/>', processed_text)
    
    # 在关键连接词前后添加轻微停顿（增强语感）
    connecting_words = ['但是', '然而', '不过', '所以', '因此', '而且', '此外']
    for word in connecting_words:
        # 在连接词前添加停顿
        processed_text = re.sub(f'(?<=\\w){word}', f'<break time="0.2s"/>{word}', processed_text)
        # 在连接词后添加停顿
        processed_text = re.sub(f'{word}(?=\\w)', f'{word}<break time="0.2s"/>', processed_text)
    
    # 处理数字和年份，增加自然停顿
    # 年份数字间添加微停顿
    processed_text = re.sub(r'(\d{2})(\d{2})年', r'\1<break time="0.1s"/>\2年', processed_text)
    
    # 包装成完整的SSML格式
    final_ssml = ssml_wrapper.format(processed_text)
    
    return final_ssml

async def test_ssml_detailed():
    """详细测试SSML功能"""
    # 测试文本
    test_text = "提到程序员，你脑海里是不是全是穿卫衣的极客小哥？但在电脑诞生前 100 年，第一位程序员，其实是位女士。"
    
    print("📝 原始文本:")
    print(test_text)
    print("\n" + "="*50 + "\n")
    
    # 生成SSML文本
    ssml_text = insert_ssml_breaks(test_text)
    print("🔧 生成的SSML文本:")
    print(ssml_text)
    print("\n" + "="*50 + "\n")
    
    # 验证SSML结构
    print("🔍 SSML结构验证:")
    print(f"包含<speak>标签: {'<speak' in ssml_text}")
    print(f"包含</speak>标签: {'</speak>' in ssml_text}")
    print(f"包含<break>标签数量: {ssml_text.count('<break')}")
    print(f"SSML总长度: {len(ssml_text)} 字符")
    print("\n" + "="*50 + "\n")
    
    # 测试不同方式的音频生成
    output_files = [
        ("./output/ssml_direct_test.mp3", "直接SSML测试"),
        ("./output/ssml_with_param_test.mp3", "带参数SSML测试"),
        ("./output/plain_text_test.mp3", "纯文本对照")
    ]
    
    for output_file, description in output_files:
        print(f"🎵 {description}: {output_file}")
        try:
            if "direct" in output_file:
                # 直接使用SSML文本
                communicate = edge_tts.Communicate(ssml_text, voice=VOICE, rate=RATE, volume=VOLUME)
                await communicate.save(output_file)
                print(f"✅ 成功生成")
            elif "with_param" in output_file:
                # 尝试使用SSML参数（如果支持的话）
                try:
                    communicate = edge_tts.Communicate(ssml_text, voice=VOICE, rate=RATE, volume=VOLUME, ssml=True)
                    await communicate.save(output_file)
                    print(f"✅ 成功生成（使用ssml=True参数）")
                except Exception as e:
                    print(f"⚠️  ssml=True参数失败: {e}")
                    # 回退到普通模式
                    communicate = edge_tts.Communicate(test_text, voice=VOICE, rate=RATE, volume=VOLUME)
                    await communicate.save(output_file)
                    print(f"✅ 回退到普通模式成功")
            else:
                # 纯文本对照
                communicate = edge_tts.Communicate(test_text, voice=VOICE, rate=RATE, volume=VOLUME)
                await communicate.save(output_file)
                print(f"✅ 成功生成")
        except Exception as e:
            print(f"❌ 生成失败: {e}")
        print()

if __name__ == "__main__":
    asyncio.run(test_ssml_detailed())