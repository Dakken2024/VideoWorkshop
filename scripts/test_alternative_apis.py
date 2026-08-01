import requests
import time
import json
from urllib.parse import quote

def test_alternative_apis(prompt, output_file):
    """测试多个替代的免费AI图像API"""
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    
    # 测试不同的免费API服务
    apis_to_test = [
        {
            'name': 'Pollinations.ai (不同端点)',
            'url': f'https://pollinations.ai/p/{quote(prompt)}?width=1080&height=1920',
            'method': 'GET'
        },
        {
            'name': 'Prodia API (公开测试)',
            'url': 'https://api.prodia.com/v1/job',
            'method': 'POST',
            'data': {
                'prompt': prompt,
                'model': 'anything-v4.0',
                'steps': 20
            }
        },
        {
            'name': 'Civitai API',
            'url': 'https://civitai.com/api/v1/images',
            'method': 'GET',
            'params': {
                'limit': 1,
                'nsfw': 'false'
            }
        }
    ]
    
    for api_info in apis_to_test:
        print(f"\n🔍 测试 {api_info['name']}...")
        print(f"URL: {api_info['url']}")
        
        try:
            if api_info['method'] == 'GET':
                response = requests.get(
                    api_info['url'], 
                    headers=headers, 
                    timeout=30,
                    params=api_info.get('params', {})
                )
            else:  # POST
                response = requests.post(
                    api_info['url'],
                    headers=headers,
                    json=api_info.get('data', {}),
                    timeout=30
                )
            
            print(f"状态码: {response.status_code}")
            
            if response.status_code == 200:
                content_length = len(response.content)
                print(f"内容大小: {content_length} bytes")
                
                # 检查是否为图片
                if content_length > 10000:  # 至少10KB
                    content_type = response.headers.get('content-type', '').lower()
                    if 'image' in content_type or response.content[:10].startswith(b'\xff\xd8') or response.content[:8] == b'\x89PNG':
                        with open(output_file, 'wb') as f:
                            f.write(response.content)
                        print(f"✅ 成功获取图片: {output_file}")
                        return True
            
            print(f"响应预览: {response.text[:200]}")
            
        except Exception as e:
            print(f"❌ 错误: {e}")
        
        time.sleep(2)  # 避免过于频繁请求
    
    return False

# 测试替代API
if __name__ == "__main__":
    test_prompt = "Portrait of Ada Lovelace, elegant 19th century style"
    success = test_alternative_apis(test_prompt, "./output/alternative_test.jpg")
    print(f"\n📊 最终结果: {'成功' if success else '失败'}")