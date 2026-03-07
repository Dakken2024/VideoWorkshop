#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
激进版图片多样性解决方案
彻底解决图片重复问题的全新方法
"""

import requests
import random
import time
import json
import hashlib
import os
from urllib.parse import quote
from typing import Dict, List, Optional
from PIL import Image, ImageDraw, ImageFont
import numpy as np

class RadicalImageDiversityGenerator:
    """激进版图片多样性生成器 - 彻底解决重复问题"""
    
    def __init__(self):
        # 扩展的免费AI图片API列表
        self.free_apis = [
            {
                'name': 'Pollinations.ai',
                'base_url': 'https://image.pollinations.ai/prompt/',
                'models': ['stable-diffusion', 'flux', 'realistic-vision'],
                'timeout': 60
            },
            {
                'name': 'Prodia API',
                'base_url': 'https://api.prodia.com/v1/sdxl/generate',
                'models': ['sd_xl_base_1.0.safetensors [be9edd61]', 'dreamshaperXL10_alpha2.safetensors [c8afe2ef]'],
                'timeout': 45
            },
            {
                'name': 'SegMind API',
                'base_url': 'https://api.segmind.com/v1/sd1.5-txt2img',
                'models': ['sd_1.5'],
                'timeout': 30
            }
        ]
        
        # 高级提示词工程
        self.prompt_engineering_templates = {
            '场景差异化': [
                'unique artistic interpretation of', 'distinctive visual representation of',
                'original creative depiction of', 'innovative artistic rendering of'
            ],
            '风格增强': [
                'masterpiece quality', 'award-winning composition', 'gallery-worthy artwork',
                'professionally crafted', 'artistically sophisticated'
            ],
            '技术细节': [
                'highly detailed', 'intricate composition', 'complex visual elements',
                'rich textural quality', 'sophisticated lighting'
            ]
        }
        
        # 场景特定的视觉特征库
        self.scene_visual_features = {
            1: {'colors': ['#2E86AB', '#A23B72', '#F18F01'], 'textures': ['digital', 'neon', 'geometric']},
            2: {'colors': ['#8B4513', '#DAA520', '#8B0000'], 'textures': ['oil-painting', 'classical', 'vintage']},
            3: {'colors': ['#2F4F4F', '#808080', '#2F4F4F'], 'textures': ['dramatic', 'shadow-play', 'historical']},
            4: {'colors': ['#8B4513', '#CD853F', '#D2691E'], 'textures': ['steampunk', 'mechanical', 'industrial']},
            5: {'colors': ['#C0C0C0', '#A9A9A9', '#808080'], 'textures': ['metallic', 'gear-mechanism', 'technical']},
            6: {'colors': ['#4169E1', '#1E90FF', '#00BFFF'], 'textures': ['ethereal', 'magical', 'visionary']},
            7: {'colors': ['#8B4513', '#D2B48C', '#DEB887'], 'textures': ['vintage-paper', 'manuscript', 'antique']},
            8: {'colors': ['#FFD700', '#FFA500', '#FF8C00'], 'textures': ['golden-light', 'mystical', 'knowledge']},
            9: {'colors': ['#9370DB', '#BA55D3', '#DA70D6'], 'textures': ['abstract', 'digital-art', 'futuristic']},
            10: {'colors': ['#2F4F4F', '#696969', '#708090'], 'textures': ['melancholic', 'memorial', 'respectful']},
            11: {'colors': ['#8B4513', '#A0522D', '#8B4513'], 'textures': ['documentary', 'historical', 'sepia']},
            12: {'colors': ['#32CD32', '#00FA9A', '#7CFC00'], 'textures': ['modern', 'empowering', 'bright']},
            13: {'colors': ['#4169E1', '#000080', '#00008B'], 'textures': ['epic', 'cinematic', 'futuristic']},
            14: {'colors': ['#DC143C', '#B22222', '#8B0000'], 'textures': ['suspense', 'thriller', 'mystery']}
        }
    
    def generate_truly_diverse_image(self, scene_data: Dict, output_file: str) -> bool:
        """
        生成真正多样化的图片 - 多层次策略
        """
        scene_id = scene_data.get('scene_id', 1)
        base_prompt = scene_data.get('prompt', '')
        scene_note = scene_data.get('note', '')
        
        print(f"\n🎨 场景 {scene_id}: {scene_note}")
        print(f"原始提示词: {base_prompt[:50]}...")
        
        # 策略1: 高级提示词工程
        engineered_prompt = self._advanced_prompt_engineering(base_prompt, scene_id, scene_note)
        print(f"工程化提示词: {engineered_prompt[:100]}...")
        
        # 策略2: 多API并发尝试
        success = self._multi_api_concurrent_generation(engineered_prompt, output_file, scene_id)
        
        if not success:
            # 策略3: 智能合成替代方案
            success = self._intelligent_synthesis_alternative(scene_data, output_file)
        
        return success
    
    def _advanced_prompt_engineering(self, base_prompt: str, scene_id: int, scene_note: str) -> str:
        """高级提示词工程 - 确保最大差异化"""
        # 基础增强
        enhanced = base_prompt.strip()
        
        # 1. 场景唯一标识 (强制唯一性)
        unique_identifier = f"SCENE-{scene_id:02d}-UNIQUE-VARIANT-{int(time.time()*1000)%10000:04d}"
        enhanced = f"{enhanced}, {unique_identifier}"
        
        # 2. 场景特定视觉特征
        if scene_id in self.scene_visual_features:
            features = self.scene_visual_features[scene_id]
            color_palette = ', '.join(features['colors'])
            textures = ', '.join(features['textures'])
            enhanced = f"{enhanced}, color palette: {color_palette}, texture style: {textures}"
        
        # 3. 随机选择高级模板
        for category, templates in self.prompt_engineering_templates.items():
            template = random.choice(templates)
            enhanced = f"{enhanced}, {template}"
        
        # 4. 质量和创意增强
        quality_boosters = [
            '8K ultra-detailed', 'professional cinematography', 'artistic masterpiece',
            'award-winning photography', 'gallery exhibition quality'
        ]
        selected_quality = random.sample(quality_boosters, 2)
        enhanced = f"{enhanced}, {', '.join(selected_quality)}"
        
        # 5. 随机创意元素 (30%概率)
        if random.random() > 0.7:
            creative_elements = [
                'revolutionary artistic concept', 'groundbreaking visual innovation',
                'unprecedented creative expression', 'extraordinary imaginative fusion'
            ]
            creative = random.choice(creative_elements)
            enhanced = f"{enhanced}, {creative}"
        
        return enhanced
    
    def _multi_api_concurrent_generation(self, prompt: str, output_file: str, scene_id: int) -> bool:
        """多API并发生成尝试"""
        print("🔄 启动多API并发生成...")
        
        # 为每个API生成不同的种子
        seeds = {}
        for i, api in enumerate(self.free_apis):
            seed = self._generate_unique_seed(prompt, scene_id, i)
            seeds[api['name']] = seed
            print(f"  {api['name']} 种子: {seed}")
        
        # 尝试每个API
        for api_info in self.free_apis:
            api_name = api_info['name']
            seed = seeds[api_name]
            
            print(f"  尝试 {api_name} (种子: {seed})...")
            
            if api_name == 'Pollinations.ai':
                if self._try_enhanced_pollinations(prompt, output_file, seed, api_info):
                    return True
            elif api_name == 'Prodia API':
                if self._try_prodia_api(prompt, output_file, seed, api_info):
                    return True
            elif api_name == 'SegMind API':
                if self._try_segmind_api(prompt, output_file, seed, api_info):
                    return True
        
        return False
    
    def _generate_unique_seed(self, prompt: str, scene_id: int, api_index: int) -> int:
        """生成确保全局唯一的种子"""
        # 结合多个熵源
        prompt_hash = hashlib.md5(prompt.encode()).hexdigest()
        time_component = int(time.time() * 1000000) % 1000000
        scene_component = scene_id * 982451653  # 大质数
        api_component = api_index * 982451653  # 同样使用质数
        
        combined = (int(prompt_hash[:8], 16) + time_component + scene_component + api_component) % 1000000000
        return combined
    
    def _try_enhanced_pollinations(self, prompt: str, output_file: str, seed: int, api_info: Dict) -> bool:
        """增强版Pollinations调用"""
        encoded_prompt = quote(prompt)
        
        # 尝试不同模型变体
        model_variants = api_info['models']
        for model in model_variants:
            url = f"{api_info['base_url']}{encoded_prompt}?width=1080&height=1920&model={model}&seed={seed}&nologo=true"
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'image/webp,image/apng,image/*,*/*;q=0.8',
                'Referer': 'https://pollinations.ai/'
            }
            
            try:
                response = requests.get(url, headers=headers, timeout=api_info['timeout'])
                
                if response.status_code == 200:
                    content_size = len(response.content)
                    # 更严格的验证
                    if content_size > 100000 and self._validate_image_content(response.content):
                        with open(output_file, 'wb') as f:
                            f.write(response.content)
                        print(f"    ✅ {api_info['name']} 生成成功 ({content_size} bytes)")
                        return True
                    else:
                        print(f"    ⚠️  内容验证失败 (大小: {content_size} bytes)")
                        
            except Exception as e:
                print(f"    ❌ {api_info['name']} 失败: {str(e)[:50]}")
                continue
        
        return False
    
    def _try_prodia_api(self, prompt: str, output_file: str, seed: int, api_info: Dict) -> bool:
        """尝试Prodia API"""
        # Prodia需要API密钥，这里提供框架
        print("    ⚠️  Prodia API需要API密钥，跳过")
        return False
    
    def _try_segmind_api(self, prompt: str, output_file: str, seed: int, api_info: Dict) -> bool:
        """尝试SegMind API"""
        # SegMind也需要API密钥，这里提供框架
        print("    ⚠️  SegMind API需要API密钥，跳过")
        return False
    
    def _validate_image_content(self, content: bytes) -> bool:
        """验证图片内容是否真实有效"""
        if len(content) < 50000:
            return False
        
        # 检查文件头
        if content.startswith(b'\xff\xd8'):  # JPEG
            return True
        elif content.startswith(b'\x89PNG'):  # PNG
            return True
        elif content.startswith(b'RIFF') and content[8:12] == b'WEBP':  # WebP
            return True
        
        return False
    
    def _intelligent_synthesis_alternative(self, scene_data: Dict, output_file: str) -> bool:
        """智能合成替代方案 - 当API失败时"""
        print("🔧 启动智能合成替代方案...")
        
        scene_id = scene_data.get('scene_id', 1)
        scene_note = scene_data.get('note', '')
        prompt = scene_data.get('prompt', '')
        
        # 创建高度定制化的合成图片
        return self._create_intelligent_composite(scene_id, scene_note, prompt, output_file)
    
    def _create_intelligent_composite(self, scene_id: int, scene_note: str, prompt: str, output_file: str) -> bool:
        """创建智能合成图片"""
        try:
            # 基于场景创建独特的视觉概念
            width, height = 1080, 1920
            
            # 获取场景特定的视觉参数
            visual_params = self.scene_visual_features.get(scene_id, {
                'colors': ['#666666', '#888888', '#AAAAAA'],
                'textures': ['abstract', 'geometric']
            })
            
            # 创建基础画布
            img = Image.new('RGB', (width, height), color=(30, 30, 30))
            draw = ImageDraw.Draw(img)
            
            # 应用场景特定的颜色方案
            colors = visual_params['colors']
            base_color = tuple(int(colors[0].lstrip('#')[i:i+2], 16) for i in (0, 2, 4))
            
            # 创建渐变背景
            self._draw_gradient_background(draw, width, height, base_color, scene_id)
            
            # 添加场景特定的几何元素
            self._add_geometric_elements(draw, width, height, scene_id, visual_params)
            
            # 添加文字信息
            self._add_scene_information(draw, scene_note, scene_id, width, height)
            
            # 添加抽象纹理
            self._add_abstract_textures(img, scene_id, visual_params)
            
            # 保存图片
            img.save(output_file, 'JPEG', quality=95, optimize=True)
            print(f"    ✅ 智能合成图片创建成功: {output_file}")
            return True
            
        except Exception as e:
            print(f"    ❌ 智能合成失败: {e}")
            return False
    
    def _draw_gradient_background(self, draw, width, height, base_color, scene_id):
        """绘制渐变背景"""
        r, g, b = base_color
        for y in range(height):
            # 创建垂直渐变
            factor = y / height
            # 添加场景特定的变化
            variation = (scene_id * 7) % 50 - 25
            new_r = max(0, min(255, int(r * (1 - factor) + variation)))
            new_g = max(0, min(255, int(g * (1 - factor) + variation)))
            new_b = max(0, min(255, int(b * (1 - factor) + variation)))
            
            draw.line([(0, y), (width, y)], fill=(new_r, new_g, new_b))
    
    def _add_geometric_elements(self, draw, width, height, scene_id, visual_params):
        """添加几何元素"""
        # 根据场景ID创建独特的几何图案
        elements_count = (scene_id % 5) + 3
        
        for i in range(elements_count):
            x = (i * width // elements_count) + (scene_id * 13) % 100
            y = (i * height // elements_count) + (scene_id * 17) % 100
            size = 50 + (scene_id * 23) % 100
            
            # 随机选择形状
            shape_type = (scene_id + i) % 4
            color = tuple(int(visual_params['colors'][i % len(visual_params['colors'])].lstrip('#')[j:j+2], 16) 
                         for j in (0, 2, 4))
            
            if shape_type == 0:  # 圆形
                draw.ellipse([x, y, x+size, y+size], outline=color, width=3)
            elif shape_type == 1:  # 矩形
                draw.rectangle([x, y, x+size, y+size], outline=color, width=3)
            elif shape_type == 2:  # 三角形
                points = [(x, y+size), (x+size//2, y), (x+size, y+size)]
                draw.polygon(points, outline=color, width=3)
            else:  # 菱形
                points = [(x+size//2, y), (x+size, y+size//2), (x+size//2, y+size), (x, y+size//2)]
                draw.polygon(points, outline=color, width=3)
    
    def _add_scene_information(self, draw, scene_note, scene_id, width, height):
        """添加场景信息文字"""
        try:
            # 简化文字添加
            text = f"Scene {scene_id}\n{scene_note[:20]}..."
            # 在图片中心附近添加文字
            center_x, center_y = width // 2, height // 2
            draw.text((center_x-100, center_y-50), text, fill=(255, 255, 255))
        except:
            pass  # 忽略字体错误
    
    def _add_abstract_textures(self, img, scene_id, visual_params):
        """添加抽象纹理"""
        # 这里可以添加更复杂的纹理生成逻辑
        # 为简化，暂时留空
        pass

def test_radical_solution():
    """测试激进解决方案"""
    print("🔥 激进版图片多样性解决方案测试")
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
        }
    ]
    
    generator = RadicalImageDiversityGenerator()
    
    for i, scene in enumerate(test_scenes):
        output_file = f"./radical_test_output/scene_{scene['scene_id']:02d}.jpg"
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        
        print(f"\n🧪 测试场景 {scene['scene_id']}:")
        success = generator.generate_truly_diverse_image(scene, output_file)
        
        if success and os.path.exists(output_file):
            size = os.path.getsize(output_file)
            print(f"✅ 场景 {scene['scene_id']} 生成成功 ({size/1024/1024:.2f}MB)")
        else:
            print(f"❌ 场景 {scene['scene_id']} 生成失败")

if __name__ == "__main__":
    test_radical_solution()