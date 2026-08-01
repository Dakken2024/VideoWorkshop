import requests
import json
import re

def get_civitai_images(prompt, output_file, max_attempts=3):
    """从Civitai获取相关图片"""
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'application/json',
    }
    
    # 将中文提示词转换为英文关键词（简化处理）
    keyword_mapping = {
        '程序员': 'programmer',
        '阿达·洛芙莱斯': 'ada lovelace',
        '历史': 'historical',
        '肖像': 'portrait',
        '油画': 'oil painting',
        '赛博朋克': 'cyberpunk',
        '现代': 'modern',
        '黑暗': 'dark',
        '神秘': 'mysterious'
    }
    
    # 提取关键词
    search_terms = []
    prompt_lower = prompt.lower()
    for cn_word, en_word in keyword_mapping.items():
        if cn_word in prompt:
            search_terms.append(en_word)
    
    # 如果没有匹配的关键词，使用通用搜索
    if not search_terms:
        search_terms = ['portrait', 'artwork']
    
    search_query = ' '.join(search_terms)
    print(f"搜索关键词: {search_query}")
    
    url = "https://civitai.com/api/v1/images"
    params = {
        'limit': 10,
        'nsfw': 'false',
        'sort': 'Most Reactions',
        'period': 'AllTime'
    }
    
    try:
        print("请求Civitai API...")
        response = requests.get(url, headers=headers, params=params, timeout=30)
        print(f"状态码: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            items = data.get('items', [])
            
            if items:
                print(f"找到 {len(items)} 个项目")
                
                # 尝试找到合适的图片
                for i, item in enumerate(items[:max_attempts]):
                    image_url = item.get('url')
                    if image_url:
                        print(f"尝试下载图片 {i+1}: {image_url}")
                        
                        # 下载实际图片
                        try:
                            img_response = requests.get(image_url, headers=headers, timeout=30)
                            if img_response.status_code == 200:
                                content_length = len(img_response.content)
                                print(f"图片大小: {content_length} bytes")
                                
                                if content_length > 50000:  # 至少50KB
                                    with open(output_file, 'wb') as f:
                                        f.write(img_response.content)
                                    print(f"✅ 成功下载图片: {output_file}")
                                    return True
                        except Exception as e:
                            print(f"下载失败: {e}")
                            
            else:
                print("未找到图片项目")
        else:
            print(f"API请求失败: {response.status_code}")
            print(f"响应: {response.text[:200]}")
            
    except Exception as e:
        print(f"❌ 错误: {e}")
    
    return False

# 测试Civitai集成
if __name__ == "__main__":
    test_prompt = "Portrait of Ada Lovelace, 19th century oil painting"
    success = get_civitai_images(test_prompt, "./output/civitai_test.jpg")
    print(f"\n📊 Civitai测试结果: {'成功' if success else '失败'}")