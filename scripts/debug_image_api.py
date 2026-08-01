import requests
import os
from urllib.parse import quote

# 测试用的提示词
test_prompts = [
    "modern programmer silhouette, dark background, cyberpunk style, mysterious",
    "Portrait of Ada Lovelace, 19th century oil painting, elegant dress, historical style"
]

def test_pollinations_api():
    print("🔍 开始调试 Pollinations.ai API...")
    
    for i, prompt in enumerate(test_prompts):
        print(f"\n--- 测试场景 {i+1} ---")
        print(f"提示词: {prompt}")
        
        # 编码提示词
        encoded_prompt = quote(prompt)
        url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=1080&height=1920&nologo=true"
        print(f"请求URL: {url}")
        
        try:
            # 增加超时时间并添加请求头
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            print("发送请求...")
            response = requests.get(url, timeout=60, headers=headers)
            
            print(f"状态码: {response.status_code}")
            print(f"响应头: {dict(response.headers)}")
            
            if response.status_code == 200:
                # 检查内容类型
                content_type = response.headers.get('content-type', '')
                print(f"内容类型: {content_type}")
                
                # 检查内容大小
                content_length = len(response.content)
                print(f"内容大小: {content_length} bytes")
                
                # 保存测试图片
                output_file = f"./output/debug_scene_{i}.jpg"
                with open(output_file, 'wb') as f:
                    f.write(response.content)
                print(f"✅ 图片已保存: {output_file}")
                
                # 如果是小文件，可能是错误页面
                if content_length < 50000:  # 50KB阈值
                    print("⚠️  文件可能不是有效图片，而是错误页面")
                    with open(f"./output/debug_scene_{i}_content.txt", 'w', encoding='utf-8') as f:
                        f.write(response.text[:1000])  # 保存前1000字符用于调试
            else:
                print(f"❌ 请求失败: {response.status_code}")
                print(f"响应内容: {response.text[:500]}")
                
        except Exception as e:
            print(f"❌ 异常: {e}")

if __name__ == "__main__":
    test_pollinations_api()