import requests
import time
import random
from urllib.parse import quote

def improved_generate_image(prompt, output_file):
    """改进的图片生成函数，包含重试机制和多种策略"""
    
    # 多种User-Agent轮换
    user_agents = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    ]
    
    # 编码提示词
    encoded_prompt = quote(prompt)
    
    # 尝试不同的URL参数组合
    url_variants = [
        f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=1080&height=1920&nologo=true",
        f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=1080&height=1920",
        f"https://image.pollinations.ai/prompt/{encoded_prompt}"
    ]
    
    # 完整的请求头
    base_headers = {
        'Accept': 'image/webp,image/apng,image/*,*/*;q=0.8',
        'Accept-Encoding': 'gzip, deflate, br',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        'Cache-Control': 'no-cache',
        'Connection': 'keep-alive',
        'Pragma': 'no-cache',
        'Referer': 'https://pollinations.ai/',
        'Sec-Ch-Ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
        'Sec-Ch-Ua-Mobile': '?0',
        'Sec-Ch-Ua-Platform': '"Windows"',
        'Sec-Fetch-Dest': 'image',
        'Sec-Fetch-Mode': 'no-cors',
        'Sec-Fetch-Site': 'cross-site',
        'Upgrade-Insecure-Requests': '1'
    }
    
    max_retries = 5
    
    for retry in range(max_retries):
        print(f"🔄 第 {retry + 1} 次尝试生成图片...")
        
        # 随机选择User-Agent和URL变体
        headers = base_headers.copy()
        headers['User-Agent'] = random.choice(user_agents)
        
        url = random.choice(url_variants)
        print(f"请求URL: {url}")
        
        try:
            # 随机延迟避免触发频率限制
            if retry > 0:
                delay = random.uniform(1, 3)
                print(f"等待 {delay:.1f} 秒...")
                time.sleep(delay)
            
            response = requests.get(
                url, 
                timeout=60, 
                headers=headers,
                stream=True  # 流式下载
            )
            
            print(f"状态码: {response.status_code}")
            
            if response.status_code == 200:
                # 检查内容类型
                content_type = response.headers.get('content-type', '').lower()
                print(f"内容类型: {content_type}")
                
                # 检查内容大小
                content = response.content
                content_length = len(content)
                print(f"内容大小: {content_length} bytes")
                
                # 验证是否为有效图片
                if content_length > 50000 and ('image' in content_type or content[:10].startswith(b'\xff\xd8') or content[:8] == b'\x89PNG\r\n\x1a\n'):
                    # 保存有效图片
                    with open(output_file, 'wb') as f:
                        f.write(content)
                    print(f"✅ 图片生成成功：{output_file}")
                    return True
                else:
                    print(f"⚠️  内容可能无效（大小: {content_length} bytes, 类型: {content_type}）")
                    
            elif response.status_code == 429:
                print("🚨 频率限制，等待更长时间...")
                if retry < max_retries - 1:
                    time.sleep(random.uniform(5, 10))
                    
            elif response.status_code >= 500:
                print(f"🚨 服务器错误 ({response.status_code})")
                
        except requests.exceptions.Timeout:
            print("⏰ 请求超时")
        except requests.exceptions.ConnectionError:
            print("🔌 连接错误")
        except Exception as e:
            print(f"❌ 其他错误: {e}")
    
    print(f"❌ 图片生成失败：{output_file}")
    return False

# 测试改进后的函数
if __name__ == "__main__":
    test_prompt = "Portrait of Ada Lovelace, 19th century oil painting, elegant dress, historical style"
    success = improved_generate_image(test_prompt, "./output/improved_test.jpg")
    print(f"最终结果: {'成功' if success else '失败'}")