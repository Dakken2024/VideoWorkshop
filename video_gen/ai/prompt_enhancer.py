#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Prompt 优化器 - 智能提示词增强模块

功能：
1. 文生图提示词优化（扩展细节、风格化）
2. 角色一致性维护
3. 场景连贯性优化
4. 多语言支持
"""

import json
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass

from ..config import DEFAULT_CONFIG
from ..utils.logger import logger


@dataclass
class PromptEnhancementResult:
    """提示词优化结果"""
    original: str
    enhanced: str
    style: str
    model_used: str
    confidence: float  # 0-1，置信度


class PromptEnhancer:
    """
    Prompt 优化器
    
    使用 LLM 对文生图提示词进行智能优化，提升生成质量。
    """

    def __init__(self, ai_client=None):
        """
        Args:
            ai_client: AI 客户端（DeepSeekClient 或 OpenRouterClient）
        """
        self.ai = ai_client
        self._style_templates = self._load_style_templates()

    def _load_style_templates(self) -> Dict[str, str]:
        """加载预设风格模板"""
        return {
            "default": {
                "name": "默认",
                "description": "清晰、详细、适合 AI 绘画",
                "keywords": ["detailed", "clear", "high quality", "professional"],
            },
            "cinematic": {
                "name": "电影感",
                "description": "电影级画面、戏剧性光线、高对比度",
                "keywords": ["cinematic", "dramatic lighting", "high contrast", "film grain", "anamorphic lens"],
            },
            "anime": {
                "name": "日系动漫",
                "description": "日系动漫风格、赛璐璐上色、精致线条",
                "keywords": ["anime style", "cel shading", "clean lines", "vibrant colors", "studio ghibli"],
            },
            "realistic": {
                "name": "超写实",
                "description": "照片级真实感、8K 分辨率、精细细节",
                "keywords": ["photorealistic", "8k", "hyper detailed", "unreal engine 5", "ray tracing"],
            },
            "artistic": {
                "name": "艺术风格",
                "description": "油画质感、艺术笔触、印象派风格",
                "keywords": ["oil painting", "artistic", "impressionism", "brush strokes", "masterpiece"],
            },
            "cyberpunk": {
                "name": "赛博朋克",
                "description": "霓虹灯、未来科技、暗色调",
                "keywords": ["cyberpunk", "neon lights", "futuristic", "dark atmosphere", "blade runner"],
            },
            "minimalist": {
                "name": "极简主义",
                "description": "简洁构图、留白、现代感",
                "keywords": ["minimalist", "clean composition", "negative space", "modern", "simple"],
            },
        }

    def enhance(self, prompt: str, style: str = "default",
                context: str = "",
                progress_callback: Optional[Callable] = None) -> PromptEnhancementResult:
        """
        优化单个提示词

        Args:
            prompt: 原始提示词（中英文均可）
            style: 风格类型
            context: 上下文信息（可选，用于保持连贯性）
            progress_callback: 进度回调

        Returns:
            PromptEnhancementResult
        """
        if not self.ai:
            # 无 AI 时返回原始提示词
            logger.warning("未配置 AI 客户端，使用原始提示词")
            return PromptEnhancementResult(
                original=prompt,
                enhanced=prompt,
                style=style,
                model_used="none",
                confidence=0.5
            )

        style_info = self._style_templates.get(style, self._style_templates["default"])
        
        system_prompt = self._build_system_prompt(style_info)
        user_prompt = self._build_user_prompt(prompt, context)

        try:
            response = self.ai.chat(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.7,
                max_tokens=512,
                progress_callback=progress_callback
            )

            enhanced = response.content.strip()
            # 清理可能的多余内容
            enhanced = self._clean_output(enhanced)

            return PromptEnhancementResult(
                original=prompt,
                enhanced=enhanced,
                style=style,
                model_used=response.model,
                confidence=0.9
            )

        except Exception as e:
            logger.error(f"提示词优化失败：{e}")
            return PromptEnhancementResult(
                original=prompt,
                enhanced=prompt,
                style=style,
                model_used="error",
                confidence=0.0
            )

    def enhance_batch(self, prompts: List[str], style: str = "default",
                      context: str = "",
                      progress_callback: Optional[Callable] = None) -> List[PromptEnhancementResult]:
        """
        批量优化提示词（保持风格一致性）

        Args:
            prompts: 提示词列表
            style: 统一风格
            context: 整体上下文（用于保持一致性）
            progress_callback: 进度回调 (current, total, message)

        Returns:
            优化结果列表
        """
        results = []
        total = len(prompts)

        for i, prompt in enumerate(prompts):
            if progress_callback:
                progress_callback(i + 1, total, f"优化提示词 {i+1}/{total}")

            # 添加序列上下文，保持一致性
            seq_context = f"这是第 {i+1}/{total} 个场景。{context}" if context else f"这是第 {i+1}/{total} 个场景。"
            
            result = self.enhance(prompt, style, seq_context)
            results.append(result)

        return results

    def _build_system_prompt(self, style_info: Dict) -> str:
        """构建系统提示词"""
        return f"""你是一个专业的 AI 绘画提示词优化专家。
你的任务是将用户提供的简单提示词扩展为详细、专业、适合 Midjourney/Stable Diffusion/Flux 的高质量英文提示词。

## 输出要求
1. **只输出优化后的英文提示词**，不要包含任何解释、说明或其他内容
2. 保持原意不变，但添加丰富的视觉细节
3. 必须包含以下元素：
   - 主体描述（subject）
   - 环境/背景（environment/background）
   - 光线（lighting）
   - 色彩（color palette）
   - 构图（composition）
   - 艺术风格（art style）
   - 渲染质量（render quality）

## 目标风格
- 名称：{style_info['name']}
- 描述：{style_info['description']}
- 关键词：{', '.join(style_info['keywords'])}

## 重要规则
- 输出必须是纯英文
- 不包含 ```json 或 ```markdown 等标记
- 不包含"以下是优化后的提示词"等前缀
- 长度控制在 50-150 词之间"""

    def _build_user_prompt(self, prompt: str, context: str) -> str:
        """构建用户提示词"""
        base = f"请优化以下提示词：{prompt}"
        if context:
            base += f"\n\n上下文信息：{context}"
        return base

    def _clean_output(self, output: str) -> str:
        """清理输出，去除多余内容"""
        import re
        
        # 去除代码块标记
        output = re.sub(r'^```(?:english)?\s*', '', output, flags=re.MULTILINE)
        output = re.sub(r'\s*```$', '', output, flags=re.MULTILINE)
        
        # 去除常见前缀
        prefixes = [
            r"^优化后的提示词[:：]?\s*",
            r"^enhanced prompt[:：]?\s*",
            r"^以下是[:：]?\s*",
            r"^here is[:：]?\s*",
        ]
        for prefix in prefixes:
            output = re.sub(prefix, '', output, flags=re.IGNORECASE)
        
        return output.strip()

    def ensure_consistency(self, prompts: List[str], 
                          character_desc: str = "",
                          style: str = "default") -> List[str]:
        """
        确保多个提示词之间的角色和风格一致性

        Args:
            prompts: 原始提示词列表
            character_desc: 角色描述（用于保持一致性）
            style: 统一风格

        Returns:
            一致性优化后的提示词列表
        """
        if not self.ai or len(prompts) < 2:
            return prompts

        # 构建一致性提示词
        system_prompt = f"""你是一个专业的 AI 绘画提示词一致性优化专家。
你需要确保一组提示词中的角色、风格、色调保持一致。

## 任务
1. 分析所有提示词的共同元素
2. 确保角色外观一致（如果提供了角色描述）
3. 保持统一的色彩基调和艺术风格
4. 输出优化后的提示词列表（JSON 格式）

## 输出格式
```json
[
  "optimized prompt 1",
  "optimized prompt 2",
  ...
]
```"""

        user_prompt = f"""角色描述：{character_desc if character_desc else '无特定角色'}

原始提示词列表：
{json.dumps(prompts, ensure_ascii=False, indent=2)}

请优化这些提示词，确保角色和风格的一致性。"""

        try:
            response = self.ai.chat(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.5,
                max_tokens=2048,
            )
            
            # 提取 JSON
            import re
            json_pattern = r"```(?:json)?\s*\n?([\s\S]*?)\n?```"
            matches = re.findall(json_pattern, response.content)
            if matches:
                return json.loads(matches[0].strip())
            
            # 尝试直接解析
            try:
                return json.loads(response.content.strip())
            except:
                return prompts

        except Exception as e:
            logger.error(f"一致性优化失败：{e}")
            return prompts
