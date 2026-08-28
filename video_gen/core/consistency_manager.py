"""
角色与风格一致性锁定系统
确保多场景生成中角色外观、服装、风格的连续性
"""
import json
import hashlib
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field


@dataclass
class CharacterProfile:
    """角色档案"""
    name: str
    description: str  # 角色详细描述
    appearance: str  # 外貌特征
    clothing: str  # 服装描述
    style_keywords: List[str] = field(default_factory=list)
    reference_images: List[str] = field(default_factory=list)
    seed: Optional[int] = None  # 固定随机种子
    
    def to_prompt_suffix(self) -> str:
        """生成提示词后缀"""
        parts = [
            f"Character: {self.name}",
            f"Appearance: {self.appearance}",
            f"Clothing: {self.clothing}",
        ]
        if self.style_keywords:
            parts.append(f"Style: {', '.join(self.style_keywords)}")
        return ". ".join(parts)
    
    def to_dict(self) -> dict:
        return {
            'name': self.name,
            'description': self.description,
            'appearance': self.appearance,
            'clothing': self.clothing,
            'style_keywords': self.style_keywords,
            'reference_images': self.reference_images,
            'seed': self.seed
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'CharacterProfile':
        return cls(**data)


@dataclass
class StyleLock:
    """风格锁定配置"""
    art_style: str  # 艺术风格 (e.g., "anime", "realistic", "watercolor")
    color_palette: str  # 色彩基调
    lighting: str  # 光照风格
    composition: str  # 构图风格
    mood: str  # 情绪氛围
    negative_prompt: str = ""  # 负面提示词
    
    def to_prompt_suffix(self) -> str:
        """生成风格提示词后缀"""
        parts = [
            f"Art Style: {self.art_style}",
            f"Color Palette: {self.color_palette}",
            f"Lighting: {self.lighting}",
            f"Mood: {self.mood}",
        ]
        if self.composition:
            parts.append(f"Composition: {self.composition}")
        result = ". ".join(parts)
        if self.negative_prompt:
            result += f". Negative: {self.negative_prompt}"
        return result
    
    def to_dict(self) -> dict:
        return {
            'art_style': self.art_style,
            'color_palette': self.color_palette,
            'lighting': self.lighting,
            'composition': self.composition,
            'mood': self.mood,
            'negative_prompt': self.negative_prompt
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'StyleLock':
        return cls(**data)


class ConsistencyManager:
    """一致性管理器"""
    
    def __init__(self, profiles_dir: str = "profiles"):
        self.profiles_dir = Path(profiles_dir)
        self.profiles_dir.mkdir(parents=True, exist_ok=True)
        
        self.characters: Dict[str, CharacterProfile] = {}
        self.styles: Dict[str, StyleLock] = {}
        
        self._load_profiles()
    
    def _load_profiles(self):
        """加载已保存的角色和风格配置"""
        char_file = self.profiles_dir / "characters.json"
        style_file = self.profiles_dir / "styles.json"
        
        if char_file.exists():
            with open(char_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.characters = {
                    name: CharacterProfile.from_dict(profile)
                    for name, profile in data.items()
                }
        
        if style_file.exists():
            with open(style_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.styles = {
                    name: StyleLock.from_dict(style)
                    for name, style in data.items()
                }
    
    def _save_profiles(self):
        """保存角色和风格配置"""
        char_file = self.profiles_dir / "characters.json"
        style_file = self.profiles_dir / "styles.json"
        
        with open(char_file, 'w', encoding='utf-8') as f:
            json.dump(
                {name: char.to_dict() for name, char in self.characters.items()},
                f, ensure_ascii=False, indent=2
            )
        
        with open(style_file, 'w', encoding='utf-8') as f:
            json.dump(
                {name: style.to_dict() for name, style in self.styles.items()},
                f, ensure_ascii=False, indent=2
            )
    
    def register_character(self, profile: CharacterProfile) -> str:
        """注册角色"""
        self.characters[profile.name] = profile
        self._save_profiles()
        return profile.name
    
    def register_style(self, name: str, style: StyleLock) -> str:
        """注册风格"""
        self.styles[name] = style
        self._save_profiles()
        return name
    
    def get_character(self, name: str) -> Optional[CharacterProfile]:
        """获取角色配置"""
        return self.characters.get(name)
    
    def get_style(self, name: str) -> Optional[StyleLock]:
        """获取风格配置"""
        return self.styles.get(name)
    
    def enhance_prompt(self, prompt: str, character_name: str = None, style_name: str = None) -> str:
        """增强提示词，添加角色和风格一致性描述"""
        enhanced = prompt
        
        if character_name and character_name in self.characters:
            char = self.characters[character_name]
            enhanced += "\n\n" + char.to_prompt_suffix()
        
        if style_name and style_name in self.styles:
            style = self.styles[style_name]
            enhanced += "\n\n" + style.to_prompt_suffix()
        
        return enhanced
    
    def get_fixed_seed(self, character_name: str = None) -> Optional[int]:
        """获取固定种子值"""
        if character_name and character_name in self.characters:
            return self.characters[character_name].seed
        return None
    
    def create_character_from_description(self, name: str, description: str, 
                                          style_keywords: List[str] = None) -> CharacterProfile:
        """从描述创建角色档案"""
        # 简单解析描述提取特征（可升级为 LLM 解析）
        profile = CharacterProfile(
            name=name,
            description=description,
            appearance=description,  # 简化处理
            clothing="casual modern clothing",
            style_keywords=style_keywords or [],
            seed=42  # 默认固定种子
        )
        return self.register_character(profile)
    
    def list_characters(self) -> List[str]:
        """列出所有角色"""
        return list(self.characters.keys())
    
    def list_styles(self) -> List[str]:
        """列出所有风格"""
        return list(self.styles.keys())
    
    def delete_character(self, name: str) -> bool:
        """删除角色"""
        if name in self.characters:
            del self.characters[name]
            self._save_profiles()
            return True
        return False
    
    def delete_style(self, name: str) -> bool:
        """删除风格"""
        if name in self.styles:
            del self.styles[name]
            self._save_profiles()
            return True
        return False


# 全局一致性管理器实例
consistency_manager = ConsistencyManager()


def lock_character(name: str, description: str, style_keywords: List[str] = None) -> str:
    """快捷函数：锁定角色"""
    profile = consistency_manager.create_character_from_description(
        name, description, style_keywords
    )
    return profile.name


def lock_style(name: str, art_style: str, color_palette: str = "natural",
               lighting: str = "soft", mood: str = "calm") -> str:
    """快捷函数：锁定风格"""
    style = StyleLock(
        art_style=art_style,
        color_palette=color_palette,
        lighting=lighting,
        composition="",
        mood=mood,
        negative_prompt=""
    )
    return consistency_manager.register_style(name, style)


def apply_consistency(prompt: str, character: str = None, style: str = None) -> str:
    """快捷函数：应用一致性到提示词"""
    return consistency_manager.enhance_prompt(prompt, character, style)
