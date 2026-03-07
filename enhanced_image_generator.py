#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
增强版图片生成器
解决图片缺乏多样性问题，确保每个场景生成独特的图片
"""

import requests
import random
import time
import json
from urllib.parse import quote
from typing import Dict, List, Optional
import hashlib

class EnhancedImageGenerator:
    """增强版AI图片生成器 - 确保图片多样性"""
    
    def __init__(self):
        # 扩展的User-Agent池
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/120.0.2210.91 Safari/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        ]
        
        # 图片风格增强词汇库
        self.style_enhancers = {
            '赛博朋克': ['neon lights', 'futuristic', 'digital art', 'glowing effects'],
            '古典油画': ['oil painting', 'classical art', 'museum quality', 'renaissance style'],
            '蒸汽朋克': ['steampunk', 'brass', 'mechanical', 'industrial revolution'],
            '现代': ['modern', 'contemporary', 'clean', 'minimalist'],
            '抽象艺术': ['abstract', 'surreal', 'conceptual', 'expressionist'],
            '历史感': ['historical', 'vintage', 'aged', 'antique'],
            '戏剧性': ['dramatic lighting', 'cinematic', 'high contrast', 'moody'],
            '明亮': ['bright', 'vibrant colors', 'cheerful', 'optimistic']
        }
        
        # 场景差异化参数
        self.scene_modifiers = [
            'unique perspective', 'distinctive composition', 'characteristic style',
            'signature aesthetic', 'individual artistic approach', 'personal creative vision'
        ]
        
    def generate_diverse_image(self, scene_data: Dict, output_file: str, scene_index: int = 0) -> bool:
        """
        生成具有多样性的图片
        
        Args:
            scene_data: 场景数据字典，包含text, prompt, scene_id等
            output_file: 输出文件路径
            scene_index: 场景索引（用于差异化）
        """
        prompt = scene_data.get('prompt', '')
        scene_id = scene_data.get('scene_id', scene_index)
        note = scene_data.get('note', '')
        
        # 1. 增强提示词多样性
        enhanced_prompt = self._enhance_prompt(prompt, note, scene_id, scene_index)
        
        # 2. 生成多样化的种子
        diversity_seed = self._generate_diversity_seed(scene_data, scene_index)
        
        # 3. 尝试多种API源
        if self._try_enhanced_pollinations(enhanced_prompt, output_file, diversity_seed):
            return True
            
        if self._try_civitai_with_context(enhanced_prompt, output_file, scene_data):
            return True
            
        if self._try_backup_sources(enhanced_prompt, output_file, diversity_seed):
            return True
            
        # 4. 降级到占位图
        self._create_contextual_placeholder(output_file, scene_data, scene_index)
        return False
    
    def _enhance_prompt(self, base_prompt: str, note: str, scene_id: int, scene_index: int) -> str:
        """增强提示词以增加多样性"""
        enhanced = base_prompt.strip()
        
        # 1. 添加场景唯一标识符
        unique_modifier = f"scene_{scene_id:02d}_variant_{scene_index:02d}"
        enhanced = f"{enhanced}, {unique_modifier}"
        
        # 2. 根据note中的描述添加风格增强
        for style_keyword, enhancers in self.style_enhancers.items():
            if style_keyword in note:
                # 随机选择1-2个增强词
                selected_enhancers = random.sample(enhancers, min(2, len(enhancers)))
                enhanced = f"{enhanced}, {', '.join(selected_enhancers)}"
                break
        
        # 3. 添加场景差异化修饰语
        modifier = random.choice(self.scene_modifiers)
        enhanced = f"{enhanced}, {modifier}"
        
        # 4. 添加质量增强参数
        quality_boosters = [
            'high quality', 'professional', 'detailed', 'sharp focus',
            '8k resolution', 'photorealistic', 'studio lighting'
        ]
        selected_boosters = random.sample(quality_boosters, 2)
        enhanced = f"{enhanced}, {', '.join(selected_boosters)}"
        
        # 5. 添加随机创意元素
        creative_elements = [
            'award winning', 'artistic masterpiece', 'innovative composition',
            'creative interpretation', 'original artwork'
        ]
        if random.random() > 0.7:  # 30%概率添加创意元素
            creative = random.choice(creative_elements)
            enhanced = f"{enhanced}, {creative}"
        
        return enhanced
    
    def _generate_diversity_seed(self, scene_data: Dict, scene_index: int) -> int:
        """生成确保多样性的种子"""
        # 结合多个因素生成种子
        scene_id = scene_data.get('scene_id', scene_index)
        prompt_hash = hashlib.md5(scene_data.get('prompt', '').encode()).hexdigest()
        
        # 使用更大的种子范围
        base_seed = int(prompt_hash[:8], 16) % 1000000  # 0-999999范围
        scene_factor = scene_id * 137  # 素数乘法增加分散性
        index_factor = scene_index * 241  # 另一个素数
        
        final_seed = (base_seed + scene_factor + index_factor) % 1000000
        return final_seed
    
    def _try_enhanced_pollinations(self, prompt: str, output_file: str, seed: int) -> bool:
        """增强版Pollinations.ai调用"""
        # URL编码提示词
        encoded_prompt = quote(prompt)
        
        # 多种URL变体
        url_variants = [
            f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=1080&height=1920&nologo=true&seed={seed}",
            f"https://pollinations.ai/p/{encoded_prompt}?width=1080&height=1920&seed={seed}",
            f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=1080&height=1920&model=flux&seed={seed}"
        ]
        
        # 更丰富的请求头
        headers = {
            'Accept': 'image/webp,image/apng,image/*,*/*;q=0.8',
            'User-Agent': random.choice(self.user_agents),
            'Referer': 'https://pollinations.ai/',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'Sec-Fetch-Dest': 'image',
            'Sec-Fetch-Mode': 'no-cors',
            'Sec-Fetch-Site': 'cross-site'
        }
        
        # 尝试多个URL变体
        for url in url_variants:
            for attempt in range(3):
                try:
                    # 智能延迟
                    if attempt > 0:
                        # 指数退避 + 随机扰动
                        delay = (1.5 ** attempt) + random.uniform(0.5, 2.0)
                        time.sleep(delay)
                    
                    response = requests.get(url, headers=headers, timeout=60)
                    
                    if response.status_code == 200:
                        content_size = len(response.content)
                        # 更严格的大小检查
                        if content_size > 80000:  # 80KB阈值
                            with open(output_file, 'wb') as f:
                                f.write(response.content)
                            print(f"[SUCCESS] Enhanced Pollinations生成成功: {output_file}")
                            print(f"  提示词: {prompt[:100]}...")
                            print(f"  种子: {seed}")
                            print(f"  文件大小: {content_size} bytes")
                            return True
                        else:
                            print(f"[WARNING] 生成的图片太小 ({content_size} bytes)，可能是占位图")
                            
                except Exception as e:
                    print(f"[DEBUG] Enhanced Pollinations尝试 {attempt + 1} 失败: {str(e)[:100]}")
                    continue
        
        return False
    
    def _try_civitai_with_context(self, prompt: str, output_file: str, scene_data: str) -> bool:
        """带上下文的Civitai调用"""
        try:
            # 从提示词中提取关键词用于搜索
            search_keywords = self._extract_search_keywords(prompt)
            
            url = "https://civitai.com/api/v1/images"
            params = {
                'limit': 20,  # 增加结果数量
                'nsfw': 'false',
                'sort': 'Most Reactions',
                'period': 'AllTime'
            }
            
            if search_keywords:
                params['query'] = ' '.join(search_keywords)
            
            headers = {
                'User-Agent': random.choice(self.user_agents),
                'Accept': 'application/json',
                'Referer': 'https://civitai.com/'
            }
            
            response = requests.get(url, headers=headers, params=params, timeout=45)
            
            if response.status_code == 200:
                data = response.json()
                items = data.get('items', [])
                
                # 过滤和排序结果
                valid_images = []
                for item in items:
                    img_url = item.get('url')
                    if img_url and item.get('nsfw', 'None') == 'None':
                        # 检查图片元数据
                        width = item.get('width', 0)
                        height = item.get('height', 0)
                        if width >= 800 and height >= 1200:  # 确保足够大的尺寸
                            valid_images.append({
                                'url': img_url,
                                'width': width,
                                'height': height,
                                'item': item
                            })
                
                # 随机选择一张图片（增加随机性）
                if valid_images:
                    selected_image = random.choice(valid_images)
                    img_response = requests.get(selected_image['url'], headers=headers, timeout=30)
                    
                    if img_response.status_code == 200 and len(img_response.content) > 80000:
                        with open(output_file, 'wb') as f:
                            f.write(img_response.content)
                        print(f"[SUCCESS] Civitai上下文生成成功: {output_file}")
                        return True
                        
        except Exception as e:
            print(f"[DEBUG] Civitai上下文调用失败: {str(e)[:100]}")
        
        return False
    
    def _try_backup_sources(self, prompt: str, output_file: str, seed: int) -> bool:
        """备用图片源"""
        backup_sources = [
            {
                'name': 'Alternative Pollinations',
                'url': f"https://pollinations.ai/p/{quote(prompt)}?width=1080&height=1920&seed={seed}&model=realistic"
            },
            {
                'name': 'Stable Diffusion API',
                'url': f"https://images.prodia.com/prompt/{quote(prompt)}?width=1080&height=1920&seed={seed}"
            }
        ]
        
        headers = {
            'User-Agent': random.choice(self.user_agents),
            'Accept': 'image/*'
        }
        
        for source in backup_sources:
            try:
                response = requests.get(source['url'], headers=headers, timeout=45)
                if response.status_code == 200 and len(response.content) > 80000:
                    with open(output_file, 'wb') as f:
                        f.write(response.content)
                    print(f"[SUCCESS] 备用源 {source['name']} 生成成功: {output_file}")
                    return True
            except Exception as e:
                print(f"[DEBUG] 备用源 {source['name']} 失败: {str(e)[:50]}")
                continue
        
        return False
    
    def _extract_search_keywords(self, prompt: str) -> List[str]:
        """从提示词中提取搜索关键词"""
        # 简单的关键词提取（可以根据需要扩展）
        keywords = []
        prompt_lower = prompt.lower()
        
        # 基础关键词映射
        keyword_mapping = {
            'portrait': ['portrait', '人物', '肖像'],
            'landscape': ['landscape', '风景', '景色'],
            'historical': ['historical', '历史', '古典'],
            'modern': ['modern', '现代', '当代'],
            'cyberpunk': ['cyberpunk', '赛博朋克', '科幻'],
            'painting': ['painting', '油画', '绘画'],
            'digital': ['digital', '数字', '数码']
        }
        
        for en_key, cn_keys in keyword_mapping.items():
            if any(key in prompt_lower for key in cn_keys):
                keywords.append(en_key)
        
        return keywords[:3]  # 最多返回3个关键词
    
    def _create_contextual_placeholder(self, output_file: str, scene_data: Dict, scene_index: int):
        """创建带有场景上下文的占位图"""
        try:
            from moviepy.editor import ColorClip
            import numpy as np
            
            # 根据场景ID和索引生成独特颜色
            scene_id = scene_data.get('scene_id', scene_index)
            base_colors = [
                (255, 100, 100), (100, 255, 100), (100, 100, 255),
                (255, 200, 100), (200, 100, 255), (100, 255, 200),
                (255, 100, 200), (200, 255, 100), (100, 200, 255)
            ]
            
            # 循环使用颜色方案
            color_index = (scene_id + scene_index) % len(base_colors)
            base_color = base_colors[color_index]
            
            # 添加随机变化
            variation = random.randint(-30, 30)
            color = tuple(max(0, min(255, c + variation)) for c in base_color)
            
            clip = ColorClip(size=(1080, 1920), color=color)
            clip.save_frame(output_file)
            clip.close()
            
            print(f"[PLACEHOLDER] 创建场景占位图: {output_file}")
            print(f"  场景ID: {scene_id}, 索引: {scene_index}")
            print(f"  颜色: RGB{color}")
            
        except Exception as e:
            print(f"[ERROR] 占位图生成失败: {e}")

# 测试函数
def test_diversity_generation():
    """测试多样性生成功能"""
    print("🎨 增强版图片生成器测试")
    print("=" * 50)
    
    # 测试场景数据
    test_scenes = [
        {
            "scene_id": 1,
            "text": "提到程序员，你脑海里是不是全是穿卫衣的极客小哥？但在电脑诞生前 100 年，第一位程序员，其实是位 19 世纪的贵族女士。",
            "prompt": "modern programmer silhouette typing code, neon blue and purple lighting, cyberpunk aesthetic, dark background, bokeh effect, cinematic photography, high contrast --ar 9:16 --style raw",
            "duration_sec": 8,
            "note": "现代赛博朋克风格，冷色调，开场吸引眼球"
        },
        {
            "scene_id": 2,
            "text": "她叫 Ada Lovelace。1815 年出生，她是著名诗人拜伦的独生女。但命运跟她开了个玩笑，父母在她幼时便分居。",
            "prompt": "19th century Victorian era portrait of Ada Lovelace, oil painting style, warm golden lighting, elegant dress with lace details, soft brush strokes, classical art museum quality --ar 9:16 --style raw",
            "duration_sec": 10,
            "note": "古典油画风格，暖色调，历史感"
        },
        {
            "scene_id": 3,
            "text": "母亲为了防止她继承父亲的疯狂诗意，强迫她从小只学数学和逻辑。这份反诗意教育，却意外为计算机历史埋下种子。",
            "prompt": "Victorian era young girl studying mathematics at wooden desk, candles, geometry tools and books scattered, strict governess standing in shadow background, dramatic chiaroscuro lighting, historical drama style --ar 9:16 --style raw",
            "duration_sec": 12,
            "note": "戏剧性光影，叙事感强"
        }
    ]
    
    generator = EnhancedImageGenerator()
    
    for i, scene in enumerate(test_scenes):
        output_file = f"./test_output/diverse_scene_{i:02d}.jpg"
        print(f"\n🧪 测试场景 {i+1}:")
        print(f"原始提示词: {scene['prompt'][:50]}...")
        print(f"场景说明: {scene['note']}")
        
        success = generator.generate_diverse_image(scene, output_file, i)
        if success:
            print(f"✅ 场景 {i+1} 生成成功")
        else:
            print(f"❌ 场景 {i+1} 生成失败")

if __name__ == "__main__":
    test_diversity_generation()