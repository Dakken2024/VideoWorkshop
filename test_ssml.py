import asyncio
import edge_tts
import re

# TTS 配置
VOICE = "zh-CN-XiaoxiaoNeural" 
RATE = "+0%"
VOLUME = "+0%"

def insert_ssml_breaks(text):
    """智能插入SSML停顿标签，提升语音情感表现力"""
    # SSML包装
    ssml_wrapper = '<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="zh-CN">{}</speak>'
    
    # 定义标点符号及其对应的停顿时长
    punctuation_breaks = {
        '。': '<break time="0.8s/>',  # 句号 - 较长停顿
        '！': '<break time="0.8\"/>',  # 感叹号 - 较长停顿
        '？': '<break time="0.8\"/>',  # 问号 - 较长停顿
        '；': '<break time="0.6\"/>',  # 分号 - 中等停顿
        '，': '<break time="0.4\"/>',  # 逗号 - 短暂停顿
        '、': '<break time="0.3\"/>',  # 顿号 - 很短停顿
    }
    
    # 在主要标点符号后添加停顿
    processed_text = text
    for punct, break_tag in punctuation_breaks.items():
        # 使用正向先行断言避免在单词中间插入
        pattern = rf'{re.escape(punct)}(?=\s|\w|$)'
        processed_text = re.sub(pattern, f'{punct}{break_tag}', processed_text)
    
    # 处理破折号（表示强调或转折）
    processed_text = re.sub(r'——', '—<break time="0.5\"/>—', processed_text)
    processed_text = re.sub(r'—', '<break time="0.3\"/>—<break time="0.3\"/>', processed_text)
    
    # 在关键连接词前后添加轻微停顿（增强语感）
    connecting_words = ['但是', '然而', '不过', '所以', '因此', '而且', '此外']
    for word in connecting_words:
        # 在连接词前添加停顿
        processed_text = re.sub(f'(?<=\\w){word}', f'<break time="0.2"/>{word}', processed_text)
        # 在连接词后添加停顿
        processed_text = re.sub(f'{word}(?=\\w)', f'{word}<break time="0.2"/>', processed_text)
    
    # 处理数字和年份，增加自然停顿
    # 年份数字间添加微停顿
    processed_text = re.sub(r'(\d{2})(\d{2})年', r'\1<break time="0.1\"/>\2年', processed_text)
    
    # 包装成完整的SSML格式
    final_ssml = ssml_wrapper.format(processed_text)
    
    return final_ssml

async def test_ssml_generation():
    """测试SSML音频生成"""
    # 测试文本
    test_text = "提到程序员，你脑海里是不是全是穿卫衣的极客小哥？但在电脑诞生前 100 年，第一位程序员，其实是位女士。她叫 Ada Lovelace，英国诗人拜伦的女儿。但她没继承父亲的诗意，却爱上了数学。"
    
    print("📝 原始文本:")
    print(test_text)
    print("\n" + "="*50 + "\n")
    
    # 生成SSML文本
    ssml_text = insert_ssml_breaks(test_text)
    print("🔧 SSML处理后:")
    print(ssml_text)
    print("\n" + "="*50 + "\n")
    
    # 生成音频
    output_file = "./output/ssml_test.mp3"
    print("🎵 正在生成SSML增强音频...")
    
    try:
        # 尝试使用SSML模式
        communicate = edge_tts.Communicate(ssml_text, voice=VOICE, rate=RATE, volume=VOLUME)
        await communicate.save(output_file)
        print(f"✅ SSML音频生成成功: {output_file}")
    except Exception as e:
        print(f"❌ 音频生成失败: {e}")
        # 如果SSML失败，回退到普通模式
        print("🔄 回退到普通TTS模式...")
        try:
            communicate = edge_tts.Communicate(test_text, voice=VOICE, rate=RATE, volume=VOLUME)
            await communicate.save(output_file.replace('.mp3', '_fallback.mp3'))
            print("✅ 普通模式音频生成成功")
        except Exception as e2:
            print(f"❌ 普通模式也失败: {e2}")

if __name__ == "__main__":
    asyncio.run(test_ssml_generation())