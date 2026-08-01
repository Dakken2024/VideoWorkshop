#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Saabor AI Builds - 自动视频生成器
方案 C: 分段音频生成 + 静音插入（绕过 SSML 限制）
"""

import asyncio
import os
import json
import requests
import random
import time
import re
import hashlib
import subprocess
from pathlib import Path
from pydub import AudioSegment
from PIL import Image, ImageDraw, ImageFilter, ImageEnhance

# MoviePy 导入（兼容 2.0）
try:
    from moviepy import (
        AudioFileClip,
        concatenate_audioclips,
        concatenate_videoclips,
        CompositeVideoClip,
        TextClip,
        ImageClip,
        vfx
    )
    from moviepy.video.VideoClip import ColorClip
except ImportError:
    from moviepy.editor import (
        AudioFileClip,
        concatenate_audioclips,
        concatenate_videoclips,
        CompositeVideoClip,
        TextClip,
        ImageClip,
        ColorClip
    )
    from moviepy.video import fx as vfx

import edge_tts

# ================= 配置区域 =================
OUTPUT_DIR = "./output"
SCRIPT_FILE = "scripts.json"

# 停顿配置（通过静音实现，不依赖 SSML）
PAUSE_CONFIG = {
    'short': 300,      # 短停顿 300ms（顿号、连接词）
    'medium': 500,     # 中停顿 500ms（逗号）
    'long': 800,       # 长停顿 800ms（句号、问号、感叹号）
    'paragraph': 1200  # 段落停顿 1200ms
}

# TTS 语音配置
VOICE_CONFIG = {
    'primary': 'zh-CN-XiaoxiaoNeural',
    'fallback': 'zh-CN-YunxiNeural',
    'rate': '+0%',
    'volume': '+0%'
}

# 创建输出目录
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ================= 日志工具 =================

def log(level, message):
    """统一日志输出（兼容 Windows 编码）"""
    icons = {
        'INFO': '[INFO]',
        'SUCCESS': '[SUCCESS]',
        'WARNING': '[WARNING]',
        'ERROR': '[ERROR]',
        'DEBUG': '[DEBUG]'
    }
    safe_message = message.encode('gbk', errors='ignore').decode('gbk')
    print(f"{icons.get(level, '[INFO]')} {safe_message}")

# ================= JSON 脚本加载 =================

def load_script_from_json(script_file):
    """从 JSON 文件加载脚本配置"""
    try:
        with open(script_file, 'r', encoding='utf-8') as f:
            script_data = json.load(f)
        
        meta = script_data.get('meta', {})
        project_name = meta.get('title', 'Untitled_Project')
        project_name = re.sub(r'[^\w\u4e00-\u9fa5]', '_', project_name)
        
        voice_setting = meta.get('voice_setting', VOICE_CONFIG['primary'])
        
        scenes = script_data.get('scenes', [])
        script_scenes = []
        
        for scene in scenes:
            script_scenes.append({
                "text": scene.get('text', ''),
                "prompt": scene.get('prompt', ''),
                "duration": scene.get('duration_sec', 5),
                "scene_id": scene.get('scene_id', 0),
                "reference_url": scene.get('reference_url', ''),
                "note": scene.get('note', '')
            })
        
        return {
            'project_name': project_name,
            'voice': voice_setting,
            'scenes': script_scenes,
            'meta': meta
        }
    
    except FileNotFoundError:
        log('ERROR', f'未找到脚本文件：{script_file}')
        return None
    except json.JSONDecodeError as e:
        log('ERROR', f'JSON 格式错误：{e}')
        return None
    except Exception as e:
        log('ERROR', f'加载脚本时出错：{e}')
        return None

# ================= 中文停顿分析器（核心） =================

class ChinesePauseAnalyzer:
    """
    中文文本停顿分析器
    根据标点符号和语义分析，计算每个文本片段需要的停顿时长
    """
    
    def __init__(self, config=None):
        self.config = config or PAUSE_CONFIG
    
    def analyze_text(self, text):
        """
        分析文本，返回 (清理后的文本，停顿时长 ms)
        
        规则：
        - 句号、问号、感叹号 → 长停顿
        - 逗号、分号 → 中停顿
        - 顿号 → 短停顿
        - 连接词 → 短停顿
        """
        # 清理文本（移除可能残留的 SSML 标签）
        clean_text = re.sub(r'<[^>]+>', '', text)
        clean_text = clean_text.strip()
        
        if not clean_text:
            return clean_text, 0
        
        # 获取最后一个字符判断停顿
        last_char = clean_text[-1]
        
        # 长停顿标点
        if last_char in ['。', '！', '？', '!', '?']:
            return clean_text, self.config['long']
        
        # 中停顿标点
        if last_char in ['，', '；', ',', ';']:
            return clean_text, self.config['medium']
        
        # 短停顿标点
        if last_char in ['、']:
            return clean_text, self.config['short']
        
        # 连接词结尾
        connecting_words = ['但是', '然而', '不过', '所以', '因此']
        for word in connecting_words:
            if clean_text.endswith(word):
                return clean_text, self.config['short']
        
        # 默认无停顿
        return clean_text, 0
    
    def get_pause_audio(self, duration_ms):
        """生成指定时长的静音音频"""
        if duration_ms <= 0:
            return AudioSegment.silent(duration=0)
        return AudioSegment.silent(duration=duration_ms)

# ================= 音频生成器（分段 + 静音插入） =================

class AudioGenerator:
    """
    分段音频生成器
    不使用 SSML，通过后期插入静音实现停顿
    """
    
    def __init__(self, voice_config=None):
        self.voice_config = voice_config or VOICE_CONFIG
        self.pause_analyzer = ChinesePauseAnalyzer()
        self.current_voice = self.voice_config['primary']
    
    async def generate_segment(self, text, output_file, scene_id=None):
        """生成单个场景的音频片段（纯文本，无 SSML）"""
        scene_info = f"场景 {scene_id}" if scene_id else "未知场景"
        
        # 清理文本（确保无 SSML 标签）
        clean_text = re.sub(r'<[^>]+>', '', text).strip()
        
        if not clean_text:
            log('WARNING', f'{scene_info}: 文本为空，跳过')
            return False
        
        try:
            log('DEBUG', f'{scene_info}: 生成音频 ({self.current_voice})')
            communicate = edge_tts.Communicate(
                clean_text, 
                voice=self.current_voice,
                rate=self.voice_config['rate'],
                volume=self.voice_config['volume']
            )
            await communicate.save(output_file)
            
            if os.path.exists(output_file) and os.path.getsize(output_file) > 1000:
                log('SUCCESS', f'{scene_info}: 音频生成成功')
                return True
            else:
                log('WARNING', f'{scene_info}: 生成的文件异常')
        except Exception as e:
            log('WARNING', f'{scene_info}: 生成失败 - {str(e)[:80]}')
        
        # 尝试备选语音
        if self.current_voice != self.voice_config['fallback']:
            log('WARNING', f'{scene_info}: 切换到备选语音 {self.voice_config["fallback"]}')
            self.current_voice = self.voice_config['fallback']
            return await self.generate_segment(text, output_file, scene_id)
        
        log('ERROR', f'{scene_info}: 所有方案失败')
        return False
    
    async def generate_all_segments(self, scenes, output_dir):
        """生成所有场景的音频片段"""
        segment_files = []
        segment_durations = []
        pause_durations = []
        
        log('INFO', f'开始生成 {len(scenes)} 个音频片段...')
        
        for i, scene in enumerate(scenes):
            segment_file = os.path.join(output_dir, f"segment_{i:03d}.mp3")
            text = scene["text"]
            scene_id = scene.get("scene_id", i + 1)
            
            success = await self.generate_segment(text, segment_file, scene_id)
            
            if success and os.path.exists(segment_file):
                segment_files.append(segment_file)
                try:
                    audio_clip = AudioFileClip(segment_file)
                    segment_durations.append(audio_clip.duration)
                    audio_clip.close()
                except:
                    segment_durations.append(5.0)
                
                # 分析文本计算停顿时长
                _, pause_ms = self.pause_analyzer.analyze_text(text)
                pause_durations.append(pause_ms)
            else:
                log('ERROR', f'场景 {scene_id} 音频生成失败')
                segment_files.append(None)
                segment_durations.append(5.0)
                pause_durations.append(0)
        
        return segment_files, segment_durations, pause_durations
    
    def concatenate_with_pauses(self, segment_files, pause_durations, output_file):
        """
        拼接音频片段，并在片段之间插入静音停顿
        这是绕过 SSML 限制的核心方法
        """
        valid_segments = [f for f in segment_files if f and os.path.exists(f)]
        
        if not valid_segments:
            log('ERROR', '没有有效的音频片段可拼接')
            return False
        
        try:
            log('INFO', f'拼接 {len(valid_segments)} 个音频片段...')
            
            # 加载第一个音频
            combined = AudioSegment.from_file(valid_segments[0])
            
            # 依次添加停顿和后续音频
            for i in range(1, len(valid_segments)):
                # 获取前一个文本的停顿时长
                pause_ms = pause_durations[i - 1] if i - 1 < len(pause_durations) else 0
                
                # 添加停顿（静音）
                if pause_ms > 0:
                    pause_audio = AudioSegment.silent(duration=pause_ms)
                    combined += pause_audio
                    log('DEBUG', f'  插入停顿：{pause_ms}ms')
                
                # 添加下一个音频
                next_audio = AudioSegment.from_file(valid_segments[i])
                combined += next_audio
            
            # 导出拼接后的音频
            combined.export(output_file, format="mp3", bitrate="192k")
            
            log('SUCCESS', f'音频拼接完成：{output_file}')
            log('INFO', f'  总时长：{len(combined):.2f}ms ({len(combined)/1000:.2f}秒)')
            return True
            
        except Exception as e:
            log('ERROR', f'音频拼接失败：{e}')
            import traceback
            log('DEBUG', f'详细错误:\n{traceback.format_exc()}')
            return False

# ================= 图片生成器（多源策略） =================

class ImageGenerator:
    """终极版图片生成器 - 彻底解决重复性问题"""
    
    def __init__(self):
        # 扩展的用户代理池
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/120.0.2210.91 Safari/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        ]
        
        # 场景视觉特征数据库
        self.scene_visual_database = {
            1: {'theme': 'cyberpunk', 'colors': ['#00FFFF', '#FF00FF', '#0000FF'], 'elements': ['grid', 'circuit', 'binary']},
            2: {'theme': 'victorian', 'colors': ['#8B4513', '#DAA520', '#8B0000'], 'elements': ['oval', 'floral', 'curved']},
            3: {'theme': 'historical', 'colors': ['#2F4F4F', '#808080', '#2F4F4F'], 'elements': ['rectangular', 'linear', 'shadow']},
            4: {'theme': 'steampunk', 'colors': ['#8B4513', '#CD853F', '#D2691E'], 'elements': ['gear', 'mechanical', 'brass']},
            5: {'theme': 'mechanical', 'colors': ['#C0C0C0', '#A9A9A9', '#808080'], 'elements': ['gear_system', 'precision', 'industrial']},
            6: {'theme': 'visionary', 'colors': ['#4169E1', '#1E90FF', '#00BFFF'], 'elements': ['light_beam', 'future', 'inspiration']},
            7: {'theme': 'manuscript', 'colors': ['#8B4513', '#D2B48C', '#DEB887'], 'elements': ['text_lines', 'parchment', 'quill']},
            8: {'theme': 'mathematical', 'colors': ['#FFD700', '#FFA500', '#FF8C00'], 'elements': ['formula', 'numbers', 'equation']},
            9: {'theme': 'futuristic', 'colors': ['#9370DB', '#BA55D3', '#DA70D6'], 'elements': ['digital_art', 'symbols', 'abstract']},
            10: {'theme': 'memorial', 'colors': ['#2F4F4F', '#696969', '#708090'], 'elements': ['gravestone', 'leaves', 'respectful']},
            11: {'theme': 'discovery', 'colors': ['#8B4513', '#A0522D', '#8B4513'], 'elements': ['document', 'archive', 'research']},
            12: {'theme': 'empowerment', 'colors': ['#32CD32', '#00FA9A', '#7CFC00'], 'elements': ['diverse_figures', 'bright', 'modern']},
            13: {'theme': 'brand_vision', 'colors': ['#4169E1', '#000080', '#00008B'], 'elements': ['cityscape', 'data', 'logo']},
            14: {'theme': 'mystery', 'colors': ['#DC143C', '#B22222', '#8B0000'], 'elements': ['enigma', 'spotlight', 'suspense']}
        }
        
        # 高级质量增强模板
        self.quality_templates = [
            'masterpiece quality, professional photography, gallery worthy',
            'award winning composition, artistic excellence, studio quality',
            '8K resolution, perfect lighting, exceptional detail',
            'cinematic masterpiece, dramatic composition, high definition'
        ]
    
    def generate(self, prompt, output_file, scene_id=None, scene_note=None, seed=None):
        """终极图片生成方法 - 四重保障策略

        Args:
            prompt: 基础提示词
            output_file: 输出文件路径
            scene_id: 场景ID
            scene_note: 场景说明
            seed: 随机种子（可选，用于帧间一致性）
        """
        log('INFO', f'场景 {scene_id}: 开始终极多样性生成')

        # 策略1: 提示词工程（如果未提供seed则使用完整增强，否则使用简化版）
        if seed is not None:
            # 使用传入的seed，简化提示词以避免URL过长
            engineered_prompt = self._simple_prompt_engineering(prompt, scene_id)
        else:
            engineered_prompt = self._ultimate_prompt_engineering(prompt, scene_id, scene_note)
        log('DEBUG', f'工程化提示词长度: {len(engineered_prompt)} 字符')

        # 策略2: 智能多API轮询（传入seed）
        if self._intelligent_multi_api_generation(engineered_prompt, output_file, scene_id, seed):
            log('SUCCESS', f'场景 {scene_id}: API生成成功')
            return True

        # 策略3: 本地智能合成
        if self._local_smart_synthesis(scene_id, scene_note, output_file):
            log('SUCCESS', f'场景 {scene_id}: 本地合成成功')
            return True

        # 策略4: 高级占位图
        self._create_ultimate_placeholder(scene_id, scene_note, output_file)
        log('WARNING', f'场景 {scene_id}: 使用高级占位图')
        return True  # 占位图总是成功
    
    def _ultimate_prompt_engineering(self, base_prompt: str, scene_id: int, scene_note: str) -> str:
        """终极提示词工程 - 确保绝对唯一性"""
        enhanced = base_prompt.strip()
        
        # 1. 强制全局唯一标识符
        timestamp = int(time.time() * 1000000) % 1000000000
        unique_signature = f"ABSOLUTELY_UNIQUE_SCENE_{scene_id:03d}_TIMESTAMP_{timestamp}_VERSION_{random.randint(10000, 99999)}"
        enhanced = f"{enhanced}, {unique_signature}"
        
        # 2. 场景特定视觉特征注入
        if scene_id in self.scene_visual_database:
            features = self.scene_visual_database[scene_id]
            color_palette = ', '.join(features['colors'])
            thematic_elements = ', '.join(features['elements'])
            enhanced = f"{enhanced}, dominant colors: {color_palette}, thematic elements: {thematic_elements}, {features['theme']} aesthetic"
        
        # 3. 高级质量模板
        quality_template = random.choice(self.quality_templates)
        enhanced = f"{enhanced}, {quality_template}"
        
        # 4. 技术规格强化
        technical_specs = [
            '8K ultra-high resolution', 'professional studio lighting',
            'perfect composition and framing', 'crystal clear sharpness',
            'balanced color grading', 'cinematic depth of field'
        ]
        selected_specs = random.sample(technical_specs, 3)
        enhanced = f"{enhanced}, {', '.join(selected_specs)}"
        
        # 5. 创意助推器
        creative_boosters = [
            'revolutionary artistic concept', 'groundbreaking visual innovation',
            'unprecedented creative expression', 'extraordinary imaginative fusion',
            'innovative artistic breakthrough', 'visionary creative approach'
        ]
        creative_booster = random.choice(creative_boosters)
        enhanced = f"{enhanced}, {creative_booster}"
        
        return enhanced

    def _simple_prompt_engineering(self, base_prompt: str, scene_id: int) -> str:
        """简化版提示词工程 - 用于帧生成，避免URL过长"""
        enhanced = base_prompt.strip()

        # 只添加最基本的电影效果描述
        cinematic_enhancements = [
            'cinematic composition',
            '35mm film look',
            'professional photography'
        ]

        # 随机选择1-2个增强描述
        selected = random.sample(cinematic_enhancements, min(2, len(cinematic_enhancements)))
        enhanced = f"{enhanced}, {', '.join(selected)}"

        return enhanced

    def _intelligent_multi_api_generation(self, prompt: str, output_file: str, scene_id: int, seed: int = None) -> bool:
        """智能多API生成"""
        log('DEBUG', f'启动智能多API轮询，场景 {scene_id}')

        # 更新后的API配置（使用gen端点和API密钥）
        api_configs = [
            {
                'name': 'Gen Pollinations (flux)',
                'base_url': 'https://gen.pollinations.ai/image/',
                'params': {
                    'model': 'flux',
                    'width': '1080',
                    'height': '1920',
                    'enhance': 'false',
                    'key': 'pk_WyzA9ElvE2wF2Nqu'
                },
                'supports_commands': True,
                'timeout': 60,
                'success_weight': 0.4
            },
            {
                'name': 'Gen Pollinations (flux-realism)',
                'base_url': 'https://gen.pollinations.ai/image/',
                'params': {
                    'model': 'flux-realism',
                    'width': '1080',
                    'height': '1920',
                    'enhance': 'false',
                    'key': 'pk_WyzA9ElvE2wF2Nqu'
                },
                'supports_commands': True,
                'timeout': 60,
                'success_weight': 0.35
            },
            {
                'name': 'Gen Pollinations (turbo)',
                'base_url': 'https://gen.pollinations.ai/image/',
                'params': {
                    'model': 'turbo',
                    'width': '1080',
                    'height': '1920',
                    'enhance': 'false',
                    'key': 'pk_WyzA9ElvE2wF2Nqu'
                },
                'supports_commands': True,
                'timeout': 60,
                'success_weight': 0.3
            },
            {
                'name': 'Gen Pollinations (sdxl)',
                'base_url': 'https://gen.pollinations.ai/image/',
                'params': {
                    'model': 'sdxl',
                    'width': '1080',
                    'height': '1920',
                    'enhance': 'false',
                    'key': 'pk_WyzA9ElvE2wF2Nqu'
                },
                'supports_commands': True,
                'timeout': 60,
                'success_weight': 0.25
            },
            {
                'name': 'Alternative Pollinations',
                'url_template': 'https://pollinations.ai/p/{prompt}?width=1080&height=1920&seed={seed}',
                'timeout': 45,
                'success_weight': 0.2
            }
        ]

        # 为每个API生成种子（如果传入了seed则使用该seed，否则生成新的）
        api_seeds = {}
        for i, config in enumerate(api_configs):
            if seed is not None:
                # 使用传入的seed，但为不同API添加偏移以增加多样性
                api_seed = seed + i * 100
            else:
                api_seed = self._generate_ultimate_seed(prompt, scene_id, i)
            api_seeds[config['name']] = api_seed
            log('DEBUG', f'  {config["name"]} 种子: {api_seed}')
        
        # 按权重排序并尝试
        sorted_apis = sorted(api_configs, key=lambda x: x['success_weight'], reverse=True)
        
        for api_config in sorted_apis:
            if self._execute_single_api_call(api_config, prompt, output_file, api_seeds[api_config['name']], scene_id):
                return True
        
        return False
    
    def _generate_ultimate_seed(self, prompt: str, scene_id: int, api_index: int) -> int:
        """生成终极种子 - 确保全局唯一"""
        # 多因子种子生成
        prompt_hash = hashlib.md5(prompt.encode()).hexdigest()
        time_factor = int(time.time() * 1000000) % 1000000000
        scene_factor = scene_id * 15485863  # 大质数
        api_factor = api_index * 32452843   # 另一个大质数
        random_factor = random.randint(1000000, 999999999)
        
        # 组合所有因子
        ultimate_seed = (int(prompt_hash[:10], 16) + time_factor + scene_factor + 
                        api_factor + random_factor) % 2147483647  # 32位整数范围
        return ultimate_seed
    
    def _execute_single_api_call(self, api_config: dict, prompt: str, output_file: str, seed: int, scene_id: int) -> bool:
        """执行单个API调用 - 支持gen.pollinations.ai新格式"""
        try:
            # 处理提示词（添加特殊指令和换行符）
            processed_prompt = prompt.strip()
            if api_config.get('supports_commands', False):
                if '--ar' not in processed_prompt.lower():
                    processed_prompt += ' --ar 9:16'
                if '--style' not in processed_prompt.lower():
                    processed_prompt += ' --style raw'
                # 添加换行符以匹配示例格式
                processed_prompt += '\n'
            
            # 构造URL
            if 'base_url' in api_config:
                # 使用gen.pollinations.ai格式
                encoded_prompt = requests.utils.quote(processed_prompt)
                base_url = api_config['base_url'] + encoded_prompt
                
                # 添加查询参数
                params = api_config['params'].copy()
                params['seed'] = str(seed)
                param_string = '&'.join([f"{k}={v}" for k, v in params.items()])
                url = f"{base_url}?{param_string}"
            else:
                # 使用传统格式
                encoded_prompt = requests.utils.quote(processed_prompt)
                url = api_config['url_template'].format(prompt=encoded_prompt, seed=seed)
            
            # 设置增强的请求头
            headers = {
                'User-Agent': random.choice(self.user_agents),
                'Accept': 'image/webp,image/apng,image/*,*/*;q=0.8',
                'Referer': 'https://pollinations.ai/' if 'pollinations' in url.lower() else '',
                'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,en-US;q=0.7',
                'Cache-Control': 'no-cache',
                'Sec-Fetch-Dest': 'image',
                'Sec-Fetch-Mode': 'no-cors',
                'Sec-Fetch-Site': 'cross-site'
            }
            
            log('DEBUG', f'构造URL: {url}')
            
            # 发送请求
            response = requests.get(url, headers=headers, timeout=api_config['timeout'])
            
            if response.status_code == 200:
                content = response.content
                content_size = len(content)
                
                # 验证返回内容是否为有效图片
                if not self._is_valid_image(content, content_size):
                    log('DEBUG', f'{api_config["name"]} 返回内容不是有效图片')
                    return False
                
                # 保存图片
                with open(output_file, 'wb') as f:
                    f.write(content)
                log('SUCCESS', f'{api_config["name"]} 生成成功: {content_size} bytes')
                return True
            else:
                log('DEBUG', f'{api_config["name"]} 请求失败: {response.status_code}')
                # 401错误表示认证问题，直接跳过
                if response.status_code == 401:
                    log('ERROR', f'{api_config["name"]} 认证失败，请检查API密钥')
                    return False
                
        except Exception as e:
            log('DEBUG', f'{api_config["name"]} 异常: {str(e)[:100]}')
        
        return False
    
    def _is_valid_image(self, content: bytes, size: int) -> bool:
        """验证内容是否为有效的图片格式"""
        # 最小大小检查（至少10KB，排除错误页面）
        if size < 10240:
            return False
        
        # 文件头验证
        valid_headers = [
            b'\xff\xd8',      # JPEG
            b'\x89PNG',       # PNG
            b'RIFF'           # WebP开始
        ]
        
        # 检查是否以有效的图片头开始
        header_valid = any(content.startswith(header) for header in valid_headers)
        
        # 特殊检查WebP格式
        if not header_valid and content.startswith(b'RIFF') and len(content) > 12 and content[8:12] == b'WEBP':
            header_valid = True
        
        if not header_valid:
            return False
        
        # 检查是否是HTML错误页面（以<!DOCTYPE或<html开头）
        if content.startswith(b'<!DOCTYPE') or content.startswith(b'<html'):
            return False
        
        return True
    
    def _validate_ultimate_quality(self, content: bytes, size: int) -> bool:
        """终极质量验证"""
        # 最小大小检查
        if size < 100000:  # 100KB阈值
            return False
        
        # 文件头验证
        valid_headers = [
            b'\xff\xd8',      # JPEG
            b'\x89PNG',       # PNG
            b'RIFF'           # WebP开始
        ]
        
        header_valid = any(content.startswith(header) for header in valid_headers)
        if not header_valid and not (content.startswith(b'RIFF') and len(content) > 12 and content[8:12] == b'WEBP'):
            return False
        
        # 内容熵检查（避免纯色或简单图案）
        if len(content) > 1000:
            sample = content[:1000]
            entropy = len(set(sample)) / len(sample)
            if entropy < 0.4:  # 熵值过低可能是占位图
                return False
        
        # 避免已知的占位图模式
        if b'placeholder' in content.lower() or b'default' in content.lower():
            return False
        
        return True
        
    def _local_smart_synthesis(self, scene_id: int, scene_note: str, output_file: str) -> bool:
        """本地智能合成 - 当API失败时的备选方案"""
        try:
            log('INFO', f'启动本地智能合成，场景 {scene_id}')
                
            # 获取场景特征
            features = self.scene_visual_database.get(scene_id, {
                'theme': 'default',
                'colors': ['#666666', '#888888', '#AAAAAA'],
                'elements': ['geometric', 'abstract']
            })
                
            # 创建智能合成图片
            img = self._create_intelligent_composite(features, scene_id, scene_note)
            img.save(output_file, 'JPEG', quality=95, optimize=True)
                
            log('SUCCESS', f'本地合成完成: {output_file}')
            return True
                
        except Exception as e:
            log('ERROR', f'本地合成失败: {str(e)}')
            return False
        
    def _create_intelligent_composite(self, features: dict, scene_id: int, scene_note: str):
        """创建智能合成图片"""
        width, height = 1080, 1920
            
        # 创建基础画布
        img = Image.new('RGB', (width, height), color=(20, 20, 20))
        draw = ImageDraw.Draw(img)
            
        # 应用主题渐变背景
        self._apply_intelligent_gradient(draw, width, height, features['colors'], scene_id)
            
        # 添加主题元素
        self._add_theme_elements(draw, width, height, features, scene_id)
            
        # 添加装饰性图案
        self._add_decorative_motifs(draw, width, height, scene_id)
            
        # 添加信息文字
        self._add_informative_overlay(draw, scene_note, scene_id, width, height)
            
        # 应用智能滤镜
        img = self._apply_smart_filters(img, scene_id)
            
        return img
        
    def _apply_intelligent_gradient(self, draw, width, height, colors, scene_id):
        """应用智能渐变"""
        # 解析颜色
        parsed_colors = []
        for color_str in colors:
            if color_str.startswith('#'):
                rgb = tuple(int(color_str.lstrip('#')[j:j+2], 16) for j in (0, 2, 4))
                parsed_colors.append(rgb)
            else:
                parsed_colors.append((100, 100, 100))
            
        # 创建复杂渐变
        for y in range(height):
            factor = y / height
            # 添加场景特定变化
            variation = ((scene_id * 13) % 100) - 50
                
            # 多层颜色混合
            if len(parsed_colors) >= 2:
                r1, g1, b1 = parsed_colors[0]
                r2, g2, b2 = parsed_colors[1]
                r = int(r1 * (1 - factor) + r2 * factor + variation)
                g = int(g1 * (1 - factor) + g2 * factor + variation)
                b = int(b1 * (1 - factor) + b2 * factor + variation)
            else:
                r, g, b = parsed_colors[0]
                r = max(0, min(255, r + variation))
                g = max(0, min(255, g + variation))
                b = max(0, min(255, b + variation))
                
            # 添加微调噪声
            noise = (hash(str(y) + str(scene_id)) % 21) - 10
            r = max(0, min(255, r + noise))
            g = max(0, min(255, g + noise))
            b = max(0, min(255, b + noise))
                
            draw.line([(0, y), (width, y)], fill=(r, g, b))
        
    def _add_theme_elements(self, draw, width, height, features, scene_id):
        """添加主题元素"""
        elements = features['elements']
        colors = features['colors']
            
        # 添加多个元素
        element_count = 6 + (scene_id % 6)
            
        for i in range(element_count):
            # 计算位置（加入场景特定偏移）
            x = (i * width // element_count + (scene_id * 17) % 150) % width
            y = (i * height // element_count + (scene_id * 19) % 150) % height
            size = 40 + (scene_id * 23 + i * 7) % 100
                
            # 选择颜色和元素类型
            color_index = (scene_id + i) % len(colors)
            element_index = (scene_id + i) % len(elements)
                
            if colors[color_index].startswith('#'):
                color = tuple(int(colors[color_index].lstrip('#')[j:j+2], 16) for j in (0, 2, 4))
            else:
                color = (150, 150, 150)
                
            element = elements[element_index]
                
            # 绘制元素
            self._draw_intelligent_element(draw, x, y, size, color, element, scene_id, i)
        
    def _draw_intelligent_element(self, draw, x, y, size, color, element, scene_id, index):
        """绘制智能元素"""
        import math
        if element in ['circle', 'circular', 'oval']:
            draw.ellipse([x, y, x+size, y+size], outline=color, width=3)
        elif element in ['square', 'rectangle', 'rectangular']:
            draw.rectangle([x, y, x+size, y+size], outline=color, width=3)
        elif element in ['triangle', 'triangular']:
            points = [(x, y+size), (x+size//2, y), (x+size, y+size)]
            draw.polygon(points, outline=color, width=3)
        elif element in ['diamond', 'rhombus']:
            points = [(x+size//2, y), (x+size, y+size//2), (x+size//2, y+size), (x, y+size//2)]
            draw.polygon(points, outline=color, width=3)
        elif element in ['grid', 'circuit']:
            # 绘制电路板风格网格
            grid_size = size // 6
            for gx in range(6):
                for gy in range(6):
                    if (gx + gy + scene_id + index) % 4 == 0:
                        px, py = x + gx * grid_size, y + gy * grid_size
                        draw.rectangle([px, py, px+grid_size, py+grid_size], outline=color, width=2)
        elif element in ['gear', 'mechanical']:
            # 绘制齿轮
            teeth = 6 + (scene_id % 6)
            center_x, center_y = x + size//2, y + size//2
            radius = size // 2
            for i in range(teeth):
                angle = (i * 2 * math.pi) / teeth
                tooth_length = radius // 4
                x1 = center_x + radius * math.cos(angle)
                y1 = center_y + radius * math.sin(angle)
                x2 = center_x + (radius + tooth_length) * math.cos(angle)
                y2 = center_y + (radius + tooth_length) * math.sin(angle)
                draw.line([x1, y1, x2, y2], fill=color, width=3)
        
    def _add_decorative_motifs(self, draw, width, height, scene_id):
        """添加装饰性图案"""
        # 添加随机装饰线
        for i in range(15):
            if (i + scene_id) % 4 == 0:
                x1 = random.randint(0, width)
                y1 = random.randint(0, height)
                x2 = random.randint(0, width)
                y2 = random.randint(0, height)
                alpha = 80 + (scene_id * 13 + i * 7) % 120
                draw.line([x1, y1, x2, y2], fill=(200, 200, 200, alpha), width=1)
        
    def _add_informative_overlay(self, draw, scene_note, scene_id, width, height):
        """添加信息覆盖层"""
        try:
            text = f"Scene {scene_id}"
            if scene_note:
                text += f"\n{scene_note[:35]}..."
                
            # 在中心位置添加文字
            center_x, center_y = width // 2, height // 2
            draw.text((center_x-140, center_y-40), text, fill=(255, 255, 255))
        except:
            pass
        
    def _apply_smart_filters(self, img, scene_id):
        """应用智能滤镜"""
        # 根据场景ID应用不同滤镜
        filter_type = scene_id % 5
            
        if filter_type == 0:
            # 轻微模糊
            img = img.filter(ImageFilter.GaussianBlur(radius=0.8))
        elif filter_type == 1:
            # 锐化
            img = img.filter(ImageFilter.SHARPEN)
        elif filter_type == 2:
            # 对比度增强
            from PIL import ImageEnhance
            enhancer = ImageEnhance.Contrast(img)
            img = enhancer.enhance(1.3)
        elif filter_type == 3:
            # 饱和度调整
            from PIL import ImageEnhance
            enhancer = ImageEnhance.Color(img)
            img = enhancer.enhance(1.2)
        # filter_type == 4: 无滤镜
            
        return img
        
    def _create_ultimate_placeholder(self, scene_id: int, scene_note: str, output_file: str):
        """创建终极占位图 - 集成增强本地生成器"""
        try:
            # 优先尝试增强本地生成器
            from enhanced_local_generator import EnhancedLocalGenerator
            generator = EnhancedLocalGenerator()
            
            success = generator.generate_enhanced_image(
                prompt=f"Placeholder for scene {scene_id}",
                output_file=output_file,
                scene_id=scene_id,
                scene_note=scene_note
            )
            
            if success:
                log('SUCCESS', f'增强本地合成完成: {output_file}')
                return
            else:
                raise Exception("增强生成器返回失败")
                
        except Exception as e:
            log('WARNING', f'增强本地生成失败，使用传统占位图: {e}')
            # 降级到传统占位图
            self._create_traditional_placeholder(scene_id, scene_note, output_file)
    
    def _create_traditional_placeholder(self, scene_id: int, scene_note: str, output_file: str):
        """创建传统占位图 - 保持原有逻辑"""
        try:
            # 获取场景特征
            features = self.scene_visual_database.get(scene_id, {
                'colors': ['#444444', '#555555', '#666666']
            })
                
            # 创建有意义的占位图
            img = self._create_meaningful_placeholder(features, scene_id, scene_note)
            img.save(output_file, 'JPEG', quality=90)
            log('SUCCESS', f'传统占位图创建完成: {output_file}')
                
        except Exception as e:
            log('ERROR', f'创建传统占位图失败: {str(e)}')
            # 创建最基本的占位图作为最后备选
            self._create_basic_placeholder(output_file, scene_id)
        
    def _create_meaningful_placeholder(self, features: dict, scene_id: int, scene_note: str):
        """创建有意义的占位图"""
        width, height = 1080, 1920
        img = Image.new('RGB', (width, height), color=(30, 30, 40))
        draw = ImageDraw.Draw(img)
            
        # 添加场景特定的颜色区域
        colors = features.get('colors', ['#444444', '#555555', '#666666'])
            
        # 创建分层颜色背景
        section_height = height // len(colors)
        for i, color_str in enumerate(colors):
            if color_str.startswith('#'):
                color = tuple(int(color_str.lstrip('#')[j:j+2], 16) for j in (0, 2, 4))
                y1 = i * section_height
                y2 = (i + 1) * section_height
                draw.rectangle([0, y1, width, y2], fill=color)
            
        # 添加几何装饰
        self._add_placeholder_decorations(draw, width, height, scene_id)
            
        # 添加文字信息
        try:
            text = f"Scene {scene_id}\n{scene_note[:40]}..."
            draw.text((50, height//2-60), text, fill=(255, 255, 255))
        except:
            pass
            
        return img
        
    def _add_placeholder_decorations(self, draw, width, height, scene_id):
        """添加占位图装饰"""
        # 添加简单的几何图案
        for i in range(8):
            x = (i * width // 8 + scene_id * 13) % width
            y = (i * height // 8 + scene_id * 17) % height
            size = 20 + (scene_id * 7) % 30
            draw.ellipse([x, y, x+size, y+size], outline=(100, 100, 100), width=1)
        
    def _create_basic_placeholder(self, output_file: str, scene_id: int):
        """创建基本占位图"""
        width, height = 1080, 1920
        # 创建带有场景ID的简单占位图
        img = Image.new('RGB', (width, height), color=(
            50 + (scene_id * 15) % 100,
            50 + (scene_id * 25) % 100,
            50 + (scene_id * 35) % 100
        ))
        img.save(output_file, 'JPEG', quality=85)
        
    def _generate_diversity_seed(self, prompt, scene_id=None):
        """生成确保多样性的种子"""
        # 使用更大的种子范围和更多因素
        prompt_hash = hashlib.md5(prompt.encode()).hexdigest()
        base_seed = int(prompt_hash[:8], 16) % 1000000  # 0-999999
            
        scene_factor = (scene_id or 0) * 137 if scene_id is not None else 0
        time_factor = int(time.time()) % 1000
            
        final_seed = (base_seed + scene_factor + time_factor) % 1000000
        return final_seed
    
    def _try_enhanced_pollinations(self, prompt, output_file, seed):
        """增强版Pollinations.ai调用 - 集成优化策略"""
        # 导入优化版API（如果可用）
        try:
            from optimized_pollinations_api import OptimizedPollinationsAPI
            optimizer = OptimizedPollinationsAPI()
            return optimizer.generate_image(prompt, output_file, scene_id=getattr(self, '_current_scene_id', None))
        except ImportError:
            # 使用内置优化版本
            return self._internal_enhanced_pollinations(prompt, output_file, seed)
    
    def _internal_enhanced_pollinations(self, prompt, output_file, seed):
        """内置优化版Pollinations调用"""
        # 更新后的URL变体（优先使用gen端点）
        processed_prompt = prompt.strip()
        # 添加必要的指令和换行符
        if '--ar' not in processed_prompt.lower():
            processed_prompt += ' --ar 9:16'
        if '--style' not in processed_prompt.lower():
            processed_prompt += ' --style raw'
        processed_prompt += '\n'  # 添加换行符匹配示例格式
        
        encoded = requests.utils.quote(processed_prompt)
        url_variants = [
            # 优先尝试gen端点（带认证）
            f"https://gen.pollinations.ai/image/{encoded}?model=zimage&width=1080&height=1920&enhance=false&seed={seed}&key=pk_WyzA9ElvE2wF2Nqu",
            # 备选方案（统一使用gen端点）
            f"https://gen.pollinations.ai/image/{encoded}?model=zimage&width=1080&height=1920&enhance=false&seed={seed+1}&key=pk_WyzA9ElvE2wF2Nqu",
            f"https://gen.pollinations.ai/image/{encoded}?model=zimage&width=1080&height=1920&enhance=false&seed={seed+2}&key=pk_WyzA9ElvE2wF2Nqu",
            f"https://pollinations.ai/p/{encoded}?width=1080&height=1920&seed={seed}"
        ]
        
        # 增强的请求头配置
        headers = {
            'Accept': 'image/webp,image/apng,image/*,*/*;q=0.8',
            'User-Agent': random.choice(self.user_agents),
            'Referer': 'https://pollinations.ai/',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,en-US;q=0.7',
            'Accept-Encoding': 'gzip, deflate, br',
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'Sec-Fetch-Dest': 'image',
            'Sec-Fetch-Mode': 'no-cors',
            'Sec-Fetch-Site': 'cross-site',
            'Pragma': 'no-cache'
        }
        
        # 智能轮询策略
        for i, url in enumerate(url_variants):
            for attempt in range(4):  # 增加重试次数
                try:
                    if attempt > 0:
                        # 更智能的指数退避
                        base_delay = 1.0 + (i * 0.5)  # 不同URL基础延迟不同
                        delay = (base_delay * (2 ** attempt)) + random.uniform(0.5, 2.5)
                        delay = min(delay, 30.0)  # 最大延迟30秒
                        time.sleep(delay)
                        log('DEBUG', f'  等待 {delay:.1f}s 后重试...')
                    
                    # 流式下载减少内存占用
                    response = requests.get(url, headers=headers, timeout=60, stream=True)
                    
                    if response.status_code == 200:
                        content = response.content
                        content_size = len(content)
                        
                        # 严格的质量验证
                        if self._validate_image_quality(content, content_size):
                            with open(output_file, 'wb') as f:
                                f.write(content)
                            log('SUCCESS', f'优化Pollinations生成成功: {output_file}')
                            log('DEBUG', f'  URL索引: {i}, 种子: {seed}, 大小: {content_size} bytes')
                            return True
                        else:
                            log('WARNING', f'图片质量不合格 ({content_size} bytes)')
                    else:
                        log('DEBUG', f'请求失败: {response.status_code} (URL {i+1})')
                        
                except requests.exceptions.Timeout:
                    log('DEBUG', f'Timeout (URL {i+1}, 尝试 {attempt + 1})')
                except requests.exceptions.ConnectionError:
                    log('DEBUG', f'连接错误 (URL {i+1}, 尝试 {attempt + 1})')
                except Exception as e:
                    log('DEBUG', f'异常 (URL {i+1}, 尝试 {attempt + 1}): {str(e)[:100]}')
        
        return False
    
    def _validate_image_quality(self, content: bytes, size: int) -> bool:
        """严格验证图片质量"""
        # 最小大小检查
        if size < 80000:  # 80KB阈值
            return False
        
        # 文件头验证
        valid_headers = [
            b'\xff\xd8',      # JPEG
            b'\x89PNG',       # PNG
            b'RIFF',          # WebP开始
            b'GIF8'           # GIF
        ]
        
        header_valid = any(content.startswith(header) for header in valid_headers)
        if not header_valid:
            # 特殊处理WebP格式
            if not (content.startswith(b'RIFF') and len(content) > 12 and content[8:12] == b'WEBP'):
                return False
        
        # 内容熵检查
        if len(content) > 1000:
            sample = content[:1000]
            entropy = len(set(sample)) / len(sample)
            if entropy < 0.3:  # 熵值过低可能是占位图
                return False
        
        return True
    
    def _try_civitai_with_enhancement(self, prompt, output_file, scene_id=None):
        """增强版Civitai调用"""
        try:
            # 从提示词提取搜索关键词
            search_keywords = self._extract_civitai_keywords(prompt)
            
            url = "https://civitai.com/api/v1/images"
            params = {
                'limit': 15,  # 增加结果数量
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
                
                # 过滤高质量图片
                valid_images = []
                for item in items:
                    img_url = item.get('url')
                    if img_url and item.get('nsfw', 'None') == 'None':
                        width = item.get('width', 0)
                        height = item.get('height', 0)
                        if width >= 800 and height >= 1200:
                            valid_images.append({
                                'url': img_url,
                                'width': width,
                                'height': height,
                                'item': item
                            })
                
                # 随机选择避免总是选同一张
                if valid_images:
                    selected_image = random.choice(valid_images)
                    img_response = requests.get(selected_image['url'], headers=headers, timeout=30)
                    
                    if img_response.status_code == 200 and len(img_response.content) > 80000:
                        with open(output_file, 'wb') as f:
                            f.write(img_response.content)
                        log('SUCCESS', f'增强Civitai生成成功：{output_file}')
                        return True
                        
        except Exception as e:
            log('DEBUG', f'增强Civitai失败：{str(e)[:100]}')
        
        return False
    
    def _extract_civitai_keywords(self, prompt):
        """提取Civitai搜索关键词"""
        keywords = []
        prompt_lower = prompt.lower()
        
        # 关键词映射
        keyword_mapping = {
            'portrait': ['portrait', '人物', '肖像', '人像'],
            'landscape': ['landscape', '风景', '景色', '自然'],
            'historical': ['historical', '历史', '古典', '古代'],
            'modern': ['modern', '现代', '当代', '时尚'],
            'cyberpunk': ['cyberpunk', '赛博朋克', '科幻', '未来'],
            'painting': ['painting', '油画', '绘画', '艺术'],
            'digital': ['digital', '数字', '数码', '电子']
        }
        
        for en_key, cn_keys in keyword_mapping.items():
            if any(key in prompt_lower for key in cn_keys):
                keywords.append(en_key)
        
        return keywords[:3]  # 最多返回3个关键词
    
    def _create_contextual_placeholder(self, output_file, scene_id=None):
        """创建场景化占位图（增加差异化）"""
        try:
            # 基于场景ID生成独特颜色
            base_colors = [
                (255, 100, 100), (100, 255, 100), (100, 100, 255),
                (255, 200, 100), (200, 100, 255), (100, 255, 200),
                (255, 100, 200), (200, 255, 100), (100, 200, 255),
                (255, 150, 50), (150, 255, 50), (50, 150, 255)
            ]
            
            if scene_id is not None:
                color_index = scene_id % len(base_colors)
            else:
                color_index = random.randint(0, len(base_colors) - 1)
            
            base_color = base_colors[color_index]
            
            # 添加随机变化增加视觉差异
            variation = random.randint(-40, 40)
            color = tuple(max(0, min(255, c + variation)) for c in base_color)
            
            clip = ColorClip(size=(1080, 1920), color=color)
            clip.save_frame(output_file)
            clip.close()
            
            log('WARNING', f'场景化占位图生成成功：{output_file}')
            log('DEBUG', f'  场景ID: {scene_id}, 颜色: RGB{color}')
            
        except Exception as e:
            log('ERROR', f'占位图生成失败：{e}')

# ================= 视频合成器 =================

class VideoCompositor:
    """视频合成器（无字幕功能 - 字幕将在剪映中后期添加）
    
    支持智能码率控制，根据场景复杂度自动优化编码参数
    支持GPU硬件加速（NVIDIA NVENC）
    """
    
    def __init__(self, output_dir, use_gpu=None):
        """初始化视频合成器
        
        Args:
            output_dir: 输出目录
            use_gpu: 是否使用GPU加速，None表示自动检测
        """
        self.output_dir = output_dir
        self.encoding_report = {}
        self.gpu_available = False
        self.gpu_encoder = None
        
        # GPU检测
        if use_gpu is None:
            self.gpu_available, self.gpu_encoder = self._detect_gpu()
        elif use_gpu:
            self.gpu_available, self.gpu_encoder = self._detect_gpu()
            if not self.gpu_available:
                log('WARNING', 'GPU加速已启用但未检测到可用GPU，将使用CPU编码')
        else:
            self.gpu_available = False
        
        if self.gpu_available:
            log('INFO', f'✅ GPU硬件加速已启用: {self.gpu_encoder}')
        else:
            log('INFO', '使用CPU编码（libx264）')
    
    def _detect_gpu(self):
        """检测可用的GPU编码器
        
        Returns:
            tuple: (是否可用, 编码器名称)
        """
        gpu_encoders = [
            ('h264_nvenc', 'NVIDIA NVENC'),
            ('h264_qsv', 'Intel Quick Sync'),
            ('h264_videotoolbox', 'Apple VideoToolbox'),
            ('h264_amf', 'AMD AMF')
        ]
        
        for encoder, name in gpu_encoders:
            try:
                result = subprocess.run(
                    ['ffmpeg', '-hide_banner', '-encoders'],
                    capture_output=True, text=True, timeout=10
                )
                if encoder in result.stdout:
                    log('DEBUG', f'检测到GPU编码器: {name} ({encoder})')
                    return True, encoder
            except Exception as e:
                log('DEBUG', f'检测GPU编码器 {encoder} 失败: {str(e)[:50]}')
                continue
        
        return False, None
    
    def _analyze_scene_complexity(self, scenes):
        """分析场景复杂度以确定最佳编码参数"""
        if not scenes:
            return {'complexity': 'medium', 'recommended_crf': 23, 'recommended_preset': 'slow'}
        
        complexity_score = 0
        motion_score = 0
        
        complex_keywords = [
            'detailed', 'intricate', 'busy', 'crowd', 'multiple', 'complex', 
            'texture', 'pattern', 'ornate', 'elaborate', 'rich', 'layered'
        ]
        simple_keywords = [
            'minimal', 'simple', 'clean', 'solid', 'gradient', 'blur', 
            'plain', 'smooth', 'uniform', 'single', 'basic'
        ]
        motion_keywords = [
            'action', 'movement', 'dynamic', 'fast', 'motion', 'running',
            'flying', 'falling', 'explosion', 'battle', 'chase'
        ]
        
        for scene in scenes:
            prompt = scene.get('prompt', '').lower()
            text = scene.get('text', '').lower()
            combined = prompt + ' ' + text
            
            for kw in complex_keywords:
                if kw in combined:
                    complexity_score += 1
            
            for kw in simple_keywords:
                if kw in combined:
                    complexity_score -= 1
            
            for kw in motion_keywords:
                if kw in combined:
                    motion_score += 1
        
        avg_complexity = complexity_score / len(scenes)
        avg_motion = motion_score / len(scenes)
        
        combined_score = avg_complexity + avg_motion * 0.5
        
        if combined_score > 1.5:
            complexity = 'high'
            crf = 21
            preset = 'slow'
        elif combined_score < -0.5:
            complexity = 'low'
            crf = 25
            preset = 'medium'
        else:
            complexity = 'medium'
            crf = 23
            preset = 'slow'
        
        return {
            'complexity': complexity,
            'recommended_crf': crf,
            'recommended_preset': preset,
            'complexity_score': round(avg_complexity, 2),
            'motion_score': round(avg_motion, 2),
            'scene_count': len(scenes)
        }
    
    def create(self, audio_file, image_files, scene_durations, output_file, scenes=None):
        """合成视频（无字幕 - 字幕将在剪映中后期添加）
        
        Args:
            audio_file: 音频文件路径
            image_files: 图片文件路径列表
            scene_durations: 场景持续时间列表
            output_file: 输出视频文件路径
            scenes: 场景信息列表（用于智能编码优化）
        """
        log('INFO', '开始合成视频（无字幕 - 请在剪映中添加字幕）...')
        
        # 分析场景复杂度
        complexity_analysis = self._analyze_scene_complexity(scenes) if scenes else {}
        log('INFO', f"场景复杂度分析: {complexity_analysis.get('complexity', 'medium')}")
        log('DEBUG', f"推荐CRF: {complexity_analysis.get('recommended_crf', 23)}, Preset: {complexity_analysis.get('recommended_preset', 'slow')}")
        
        # 标准化路径并检查音频文件
        audio_path = os.path.normpath(audio_file)
        log('DEBUG', f'检查音频文件路径: {audio_path}')
        
        # 检查多种可能的音频文件名
        audio_candidates = [
            audio_path,
            os.path.join(self.output_dir, "voiceover.mp3"),
            os.path.join(self.output_dir, "complete_voiceover.mp3"),
            os.path.join(self.output_dir, "segment_000.mp3")
        ]
        
        found_audio = None
        for candidate in audio_candidates:
            if os.path.exists(candidate):
                found_audio = candidate
                log('INFO', f'找到音频文件: {candidate}')
                break
        
        if not found_audio:
            log('ERROR', f'音频文件不存在，检查了以下路径:')
            for candidate in audio_candidates:
                log('ERROR', f'  - {candidate}')
            return False
        
        # 使用找到的音频文件
        audio_file = found_audio
        
        try:
            audio = AudioFileClip(audio_file)
            total_audio_duration = audio.duration
            log('INFO', f'音频时长：{total_audio_duration:.2f}秒')
        except Exception as e:
            log('ERROR', f'音频加载失败：{e}')
            return False
        
        # 计算总场景时长
        total_scene_duration = sum(scene_durations)
        
        # 存储视频片段
        video_clips = []
        
        for i, (img_path, base_duration) in enumerate(zip(image_files, scene_durations)):
            if not img_path or not os.path.exists(img_path):
                log('WARNING', f'跳过无效图片：{img_path}')
                continue
            
            # 按比例分配时长
            actual_duration = (base_duration / total_scene_duration) * total_audio_duration
            
            # 创建视频片段
            clip = ImageClip(img_path).with_duration(actual_duration)
            
            # 淡入淡出效果
            if i == 0:
                clip = clip.with_effects([vfx.FadeIn(0.5)])
            elif i == len(image_files) - 1:
                clip = clip.with_effects([vfx.FadeOut(0.5)])
            else:
                clip = clip.with_effects([vfx.FadeIn(0.3), vfx.FadeOut(0.3)])
            
            video_clips.append(clip)
            log('DEBUG', f'场景 {i+1}: {base_duration}s → {actual_duration:.2f}s')
        
        if not video_clips:
            log('ERROR', '没有有效的视频片段')
            audio.close()
            return False
        
        # 合成视频片段
        final_video = concatenate_videoclips(video_clips, method="compose")
        
        # 添加水印
        try:
            # 尝试多种字体以避免Arial不可用的问题
            fonts_to_try = ['Arial', 'SimHei', 'Microsoft YaHei', 'sans-serif', None]
            watermark_clip = None
            
            for font_name in fonts_to_try:
                try:
                    watermark_kwargs = {
                        'text': "Saabor AI Builds",
                        'fontsize': 20,
                        'color': 'white'
                    }
                    if font_name:
                        watermark_kwargs['font'] = font_name
                        
                    watermark_clip = (TextClip(**watermark_kwargs)
                                    .with_position(('right', 'bottom'), relative=True)
                                    .with_duration(final_video.duration)
                                    .with_opacity(0.6))
                    break
                except Exception:
                    continue
            
            if watermark_clip:
                final_video = CompositeVideoClip([final_video, watermark_clip])
                log('SUCCESS', '水印添加成功')
            else:
                log('INFO', '跳过水印（无可用字体）')
                
        except Exception as e:
            log('WARNING', f'水印添加失败：{e}')
        
        final_video = final_video.with_audio(audio)
        
        # 微信视频号优化配置 - 使用智能码率控制
        log('INFO', '应用微信视频号优化配置（智能码率控制）...')
        
        # 根据场景复杂度确定编码参数
        crf = complexity_analysis.get('recommended_crf', 23)
        preset = complexity_analysis.get('recommended_preset', 'slow')
        complexity = complexity_analysis.get('complexity', 'medium')
        
        # 根据GPU可用性选择编码器和参数
        if self.gpu_available and self.gpu_encoder:
            # GPU编码配置
            log('INFO', f'使用GPU编码: {self.gpu_encoder}')
            log('INFO', f'智能编码参数: CQ={crf}, 复杂度={complexity}')
            
            # NVENC使用不同的preset和参数
            if self.gpu_encoder == 'h264_nvenc':
                # NVIDIA NVENC preset映射
                nvenc_preset_map = {
                    'slow': 'p6',      # 最慢但质量最好
                    'medium': 'p4',    # 平衡
                    'fast': 'p1'       # 最快
                }
                nvenc_preset = nvenc_preset_map.get(preset, 'p4')
                
                final_video.write_videofile(
                    output_file,
                    fps=30,
                    codec=self.gpu_encoder,
                    audio_codec='aac',
                    ffmpeg_params=[
                        '-preset', nvenc_preset,
                        '-rc:v', 'vbr',
                        '-cq:v', str(crf),
                        '-b:v', '0',
                        '-profile:v', 'high',
                        '-level', '4.1',
                        '-pix_fmt', 'yuv420p',
                        '-movflags', '+faststart',
                    ],
                    audio_bitrate='128k',
                    logger=None
                )
            else:
                # 其他GPU编码器（QSV, VideoToolbox, AMF）
                final_video.write_videofile(
                    output_file,
                    fps=30,
                    codec=self.gpu_encoder,
                    audio_codec='aac',
                    ffmpeg_params=[
                        '-profile:v', 'high',
                        '-level', '4.1',
                        '-pix_fmt', 'yuv420p',
                        '-movflags', '+faststart',
                    ],
                    audio_bitrate='128k',
                    logger=None
                )
        else:
            # CPU编码配置
            log('INFO', f'使用CPU编码: libx264')
            log('INFO', f'智能编码参数: CRF={crf}, Preset={preset}, 复杂度={complexity}')
            
            final_video.write_videofile(
                output_file,
                fps=30,
                codec='libx264',
                audio_codec='aac',
                preset=preset,
                ffmpeg_params=[
                    '-crf', str(crf),
                    '-profile:v', 'high',
                    '-level', '4.1',
                    '-pix_fmt', 'yuv420p',
                    '-movflags', '+faststart',
                    '-threads', '0',
                ],
                audio_bitrate='128k',
                logger=None
            )
        
        audio.close()
        for clip in video_clips:
            clip.close()
        
        # 获取优化后的文件大小
        file_size_mb = os.path.getsize(output_file) / (1024 * 1024)
        
        # 生成编码报告
        actual_codec = self.gpu_encoder if self.gpu_available else 'libx264'
        self.encoding_report = {
            'output_file': output_file,
            'file_size_mb': round(file_size_mb, 2),
            'duration_sec': round(total_audio_duration, 2),
            'scene_count': len(image_files),
            'encoding_settings': {
                'fps': 30,
                'codec': actual_codec,
                'profile': 'high',
                'level': '4.1',
                'crf': crf,
                'preset': preset,
                'audio_bitrate': '128k',
                'faststart': True,
                'gpu_accelerated': self.gpu_available,
                'gpu_encoder': self.gpu_encoder if self.gpu_available else None
            },
            'complexity_analysis': complexity_analysis,
            'wechat_optimized': True
        }
        
        log('SUCCESS', f'视频合成完成：{output_file}')
        log('INFO', f'文件大小：{file_size_mb:.1f}MB')
        
        if self.gpu_available:
            log('INFO', f'编码方式：GPU加速 ({self.gpu_encoder})')
            log('INFO', f'智能优化：CQ={crf} | 复杂度={complexity}')
        else:
            log('INFO', f'编码方式：CPU (libx264)')
            log('INFO', f'智能优化：CRF={crf} | Preset={preset} | 复杂度={complexity}')
        
        log('INFO', '优化特性：智能码率控制 | 30fps | FastStart | H.264 High Profile')
        log('INFO', '提示：请在剪映中导入视频并添加字幕')
        
        # 验证微信视频号兼容性
        compatibility = self._validate_wechat_compatibility(output_file)
        if compatibility['is_compatible']:
            log('SUCCESS', '✅ 微信视频号兼容性验证通过')
        else:
            log('WARNING', '⚠️ 微信视频号兼容性警告:')
            for issue in compatibility.get('issues', []):
                log('WARNING', f'  - {issue}')
        
        self.encoding_report['wechat_compatibility'] = compatibility
        return True
    
    def _validate_wechat_compatibility(self, video_path):
        """验证视频是否符合微信视频号要求"""
        issues = []
        warnings = []
        
        try:
            # 检查文件是否存在
            if not os.path.exists(video_path):
                return {'is_compatible': False, 'issues': ['视频文件不存在']}
            
            # 获取文件大小
            file_size_mb = os.path.getsize(video_path) / (1024 * 1024)
            
            # 检查文件大小限制 (微信视频号最大1GB)
            if file_size_mb > 1000:
                issues.append(f'文件过大 ({file_size_mb:.1f}MB > 1000MB)')
            elif file_size_mb > 500:
                warnings.append(f'文件较大 ({file_size_mb:.1f}MB)，建议控制在500MB以内')
            
            # 使用ffprobe检查视频信息
            import subprocess
            import json as json_module
            
            try:
                result = subprocess.run([
                    'ffprobe', '-v', 'quiet',
                    '-print_format', 'json',
                    '-show_format', '-show_streams',
                    video_path
                ], capture_output=True, text=True, encoding='utf-8', timeout=30)
                
                if result.returncode == 0:
                    info = json_module.loads(result.stdout)
                    
                    # 检查视频流
                    video_stream = next(
                        (s for s in info.get('streams', []) if s.get('codec_type') == 'video'),
                        None
                    )
                    
                    if video_stream:
                        # 检查编码格式
                        codec = video_stream.get('codec_name', '')
                        if codec != 'h264':
                            issues.append(f'视频编码不是H.264 (当前: {codec})')
                        
                        # 检查分辨率
                        width = int(video_stream.get('width', 0))
                        height = int(video_stream.get('height', 0))
                        
                        if not ((width == 1080 and height == 1920) or (width == 1920 and height == 1080)):
                            if width != 1080 or height != 1920:
                                warnings.append(f'分辨率非推荐 (当前: {width}x{height}，推荐: 1080x1920)')
                        
                        # 检查帧率
                        fps_str = video_stream.get('r_frame_rate', '0/1')
                        try:
                            if '/' in fps_str:
                                num, den = map(int, fps_str.split('/'))
                                fps = num / den if den != 0 else 0
                            else:
                                fps = float(fps_str)
                            
                            if fps < 24:
                                warnings.append(f'帧率较低 ({fps:.1f}fps)，建议至少24fps')
                            elif fps > 60:
                                warnings.append(f'帧率过高 ({fps:.1f}fps)，微信视频号最高支持60fps')
                        except:
                            pass
                        
                        # 检查Profile
                        profile = video_stream.get('profile', '')
                        if profile and profile not in ['High', 'Main', 'Baseline']:
                            warnings.append(f'H.264 Profile可能不兼容 (当前: {profile})')
                    
                    # 检查音频流
                    audio_stream = next(
                        (s for s in info.get('streams', []) if s.get('codec_type') == 'audio'),
                        None
                    )
                    
                    if audio_stream:
                        audio_codec = audio_stream.get('codec_name', '')
                        if audio_codec != 'aac':
                            issues.append(f'音频编码不是AAC (当前: {audio_codec})')
                    
                    # 检查码率
                    bitrate = int(info.get('format', {}).get('bit_rate', 0)) / 1000
                    if bitrate > 10000:
                        issues.append(f'码率过高 ({bitrate:.0f}kbps > 10000kbps)')
                    elif bitrate > 6000:
                        warnings.append(f'码率较高 ({bitrate:.0f}kbps)，建议控制在6000kbps以内')
                    
                    # 检查时长
                    duration = float(info.get('format', {}).get('duration', 0))
                    if duration > 3600:
                        issues.append(f'视频过长 ({duration:.0f}秒 > 3600秒)')
                    
            except subprocess.TimeoutExpired:
                warnings.append('视频信息获取超时，跳过详细检查')
            except FileNotFoundError:
                warnings.append('ffprobe不可用，跳过详细检查')
            except Exception as e:
                warnings.append(f'视频信息获取失败: {str(e)[:50]}')
            
        except Exception as e:
            issues.append(f'验证过程出错: {str(e)[:50]}')
        
        return {
            'is_compatible': len(issues) == 0,
            'issues': issues,
            'warnings': warnings,
            'file_size_mb': round(file_size_mb, 2) if 'file_size_mb' in dir() else 0
        }
    
    def save_encoding_report(self, output_path=None):
        """保存编码报告到JSON文件
        
        Args:
            output_path: 报告保存路径，默认保存在视频同目录下
            
        Returns:
            str: 报告文件路径
        """
        if not self.encoding_report:
            log('WARNING', '没有编码报告可保存')
            return None
        
        if output_path is None:
            video_path = self.encoding_report.get('output_file', '')
            if video_path:
                output_path = video_path.replace('.mp4', '_encoding_report.json')
            else:
                output_path = os.path.join(self.output_dir, 'encoding_report.json')
        
        try:
            # 添加报告生成时间
            self.encoding_report['generated_at'] = datetime.now().isoformat()
            self.encoding_report['optimizer_version'] = '2.0'
            self.encoding_report['platform_target'] = '微信视频号'
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(self.encoding_report, f, ensure_ascii=False, indent=2)
            
            log('SUCCESS', f'编码报告已保存: {output_path}')
            return output_path
            
        except Exception as e:
            log('ERROR', f'保存编码报告失败: {str(e)}')
            return None
    
    def get_encoding_summary(self):
        """获取编码摘要信息
        
        Returns:
            str: 编码摘要文本
        """
        if not self.encoding_report:
            return "无编码报告"
        
        report = self.encoding_report
        lines = [
            "=" * 50,
            "视频编码报告",
            "=" * 50,
            f"输出文件: {report.get('output_file', 'N/A')}",
            f"文件大小: {report.get('file_size_mb', 0):.2f} MB",
            f"视频时长: {report.get('duration_sec', 0):.2f} 秒",
            f"场景数量: {report.get('scene_count', 0)}",
            "",
            "编码设置:",
            f"  - 编码器: {report.get('encoding_settings', {}).get('codec', 'N/A')}",
            f"  - CRF: {report.get('encoding_settings', {}).get('crf', 'N/A')}",
            f"  - Preset: {report.get('encoding_settings', {}).get('preset', 'N/A')}",
            f"  - 帧率: {report.get('encoding_settings', {}).get('fps', 'N/A')} fps",
            f"  - 音频码率: {report.get('encoding_settings', {}).get('audio_bitrate', 'N/A')}",
            "",
            "复杂度分析:",
            f"  - 级别: {report.get('complexity_analysis', {}).get('complexity', 'N/A')}",
            f"  - 复杂度分数: {report.get('complexity_analysis', {}).get('complexity_score', 'N/A')}",
            f"  - 运动分数: {report.get('complexity_analysis', {}).get('motion_score', 'N/A')}",
            "",
            "微信视频号兼容性:",
        ]
        
        compatibility = report.get('wechat_compatibility', {})
        if compatibility.get('is_compatible'):
            lines.append("  ✅ 完全兼容")
        else:
            lines.append("  ⚠️ 存在问题:")
            for issue in compatibility.get('issues', []):
                lines.append(f"    - {issue}")
        
        for warning in compatibility.get('warnings', []):
            lines.append(f"  💡 {warning}")
        
        lines.append("=" * 50)
        
        return "\n".join(lines)

# ================= 主程序 =================

async def main():
    print("=" * 70)
    log('INFO', '🚀 Saabor AI Builds - 自动视频生成器')
    log('INFO', '方案 C: 分段音频 + 静音插入（绕过 SSML 限制）')
    print("=" * 70)
    
    script_config = load_script_from_json(SCRIPT_FILE)
    if script_config is None:
        exit(1)
    
    project_name = script_config['project_name']
    scenes = script_config['scenes']
    meta = script_config['meta']
    
    log('INFO', f'项目：{project_name}')
    log('INFO', f'主题：{meta.get("topic", "Unknown")}')
    log('INFO', f'语音：{VOICE_CONFIG["primary"]}')
    log('INFO', f'场景：{len(scenes)} 个')
    log('INFO', f'停顿策略：基于标点符号插入静音')
    print("=" * 70)
    
    audio_gen = AudioGenerator(VOICE_CONFIG)
    image_gen = ImageGenerator()
    video_comp = VideoCompositor(OUTPUT_DIR)
    
    # 步骤 1: 生成音频片段
    print("\n" + "=" * 70)
    log('INFO', '步骤 1/4: 生成音频片段')
    print("=" * 70)
    segment_files, segment_durations, pause_durations = await audio_gen.generate_all_segments(scenes, OUTPUT_DIR)
    
    # 步骤 2: 生成完整音频（移除SSML标签）
    print("\n" + "=" * 70)
    log('INFO', '步骤 2/4: 生成完整音频')
    print("=" * 70)
    audio_output = os.path.join(OUTPUT_DIR, "voiceover.mp3")
    
    # 直接使用edge-tts生成完整音频，不使用SSML标签
    full_text = ""
    for i, scene in enumerate(scenes):
        text = scene['text']
        # 简单的自然停顿，不使用SSML标签
        if text.endswith(('。', '！', '？')):
            full_text += text + " "
        elif text.endswith('，'):
            full_text += text + " "
        else:
            full_text += text + " "
    
    # 生成完整音频
    try:
        communicate = edge_tts.Communicate(
            text=full_text.strip(),
            voice=VOICE_CONFIG["primary"],
            rate="+0%",
            volume="+0%"
        )
        await communicate.save(audio_output)
        log('SUCCESS', f'完整音频生成成功：{audio_output}')
    except Exception as e:
        log('ERROR', f'音频生成失败：{e}')
        return
    
    # 步骤 3: 生成图片
    print("\n" + "=" * 70)
    log('INFO', '步骤 3/4: 生成图片（增强多样性）')
    print("=" * 70)
    image_files = []
    for i, scene in enumerate(scenes):
        img_path = os.path.join(OUTPUT_DIR, f"scene_{i:03d}.jpg")
        scene_id = scene.get('scene_id', i + 1)
        scene_note = scene.get('note', '')
        log('INFO', f'场景 {scene_id}: {scene_note}')
        log('DEBUG', f'  原始提示词长度: {len(scene["prompt"])} 字符')
        
        # 传递场景ID和note以增强多样性
        image_gen.generate(scene["prompt"], img_path, scene_id=scene_id, scene_note=scene_note)
        image_files.append(img_path)
    
    # 步骤 4: 合成视频
    print("\n" + "=" * 70)
    log('INFO', '步骤 4/4: 合成视频（含字幕）')
    print("=" * 70)
    video_output = os.path.join(OUTPUT_DIR, f"{project_name}.mp4")
    # 传递场景信息以便生成字幕
    video_comp.create(audio_output, image_files, segment_durations, video_output, scenes=scenes)
    
    # 完成报告
    print("\n" + "=" * 70)
    log('SUCCESS', '🎉 所有任务完成！')
    print("=" * 70)
    print(f"\n📁 输出目录：{os.path.abspath(OUTPUT_DIR)}")
    print(f"🎬 视频文件：{video_output}")
    print(f"🎵 音频文件：{audio_output}")
    
    print("\n💡 后续建议:")
    print("   1. 导入剪映添加自动字幕")
    print("   2. 添加背景音乐 (音量 10-15%)")
    print("   3. 手动替换关键历史图片 (参考 reference_url)")
    print("   4. 导出 1080P 竖屏视频发布视频号")
    
    print("\n📚 参考资源:")
    for i, scene in enumerate(scenes):
        ref = scene.get('reference_url', '')
        if ref:
            print(f"   场景 {i+1}: {ref}")
    
    print("=" * 70)

if __name__ == "__main__":
    asyncio.run(main())