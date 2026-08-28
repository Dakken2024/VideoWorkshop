"""
内容指纹与三级缓存系统
支持基于内容哈希的智能缓存，避免重复生成
"""
import hashlib
import json
import os
import time
import shutil
from pathlib import Path
from typing import Any, Optional
from dataclasses import dataclass


@dataclass
class CacheEntry:
    """缓存条目"""
    key: str
    content_hash: str
    created_at: float
    expires_at: float
    file_path: str
    metadata: dict


class ContentFingerprint:
    """内容指纹生成器"""
    
    @staticmethod
    def generate_text_fingerprint(text: str, style: str = "", seed: int = None) -> str:
        """生成文本内容指纹"""
        content = f"{text}|{style}|{seed or 'none'}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]
    
    @staticmethod
    def generate_image_fingerprint(prompt: str, style: str, size: str, seed: int = None) -> str:
        """生成图像内容指纹"""
        content = f"{prompt}|{style}|{size}|{seed or 'none'}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]
    
    @staticmethod
    def generate_audio_fingerprint(text: str, voice_id: str, speed: float) -> str:
        """生成音频内容指纹"""
        content = f"{text}|{voice_id}|{speed}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]
    
    @staticmethod
    def generate_video_fingerprint(scenes: list, canvas_size: str, fps: int) -> str:
        """生成视频内容指纹"""
        scenes_hash = hashlib.sha256(json.dumps(scenes, sort_keys=True).encode()).hexdigest()[:16]
        content = f"{scenes_hash}|{canvas_size}|{fps}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]


class SmartCache:
    """三级智能缓存系统"""
    
    def __init__(self, cache_dir: str = "cache", max_memory_items: int = 100):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # L1: 内存缓存 (LRU)
        self._memory_cache = {}
        self._memory_order = []
        self.max_memory_items = max_memory_items
        
        # L2: 磁盘缓存索引
        self._disk_index_file = self.cache_dir / "index.json"
        self._disk_index = self._load_disk_index()
        
        # L3: 原始文件存储
        self._files_dir = self.cache_dir / "files"
        self._files_dir.mkdir(exist_ok=True)
        
        # 清理过期缓存
        self._cleanup_expired()
    
    def _load_disk_index(self) -> dict:
        """加载磁盘索引"""
        if self._disk_index_file.exists():
            try:
                with open(self._disk_index_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return {}
        return {}
    
    def _save_disk_index(self):
        """保存磁盘索引"""
        with open(self._disk_index_file, 'w', encoding='utf-8') as f:
            json.dump(self._disk_index, f, ensure_ascii=False, indent=2)
    
    def _cleanup_expired(self):
        """清理过期缓存"""
        now = time.time()
        expired_keys = []
        
        for key, entry in self._disk_index.items():
            if entry.get('expires_at', 0) < now:
                expired_keys.append(key)
        
        for key in expired_keys:
            self._remove_from_disk(key)
    
    def _add_to_memory(self, key: str, value: Any):
        """添加到内存缓存"""
        if key in self._memory_cache:
            self._memory_order.remove(key)
        
        self._memory_cache[key] = value
        self._memory_order.append(key)
        
        # LRU 淘汰
        if len(self._memory_cache) > self.max_memory_items:
            oldest_key = self._memory_order.pop(0)
            del self._memory_cache[oldest_key]
    
    def _save_to_disk(self, key: str, file_path: str, metadata: dict, ttl_hours: int = 24):
        """保存到磁盘缓存"""
        now = time.time()
        entry = {
            'key': key,
            'file_path': str(file_path),
            'created_at': now,
            'expires_at': now + (ttl_hours * 3600),
            'metadata': metadata
        }
        
        self._disk_index[key] = entry
        self._save_disk_index()
    
    def _remove_from_disk(self, key: str):
        """从磁盘移除"""
        if key in self._disk_index:
            entry = self._disk_index[key]
            file_path = Path(entry['file_path'])
            if file_path.exists():
                file_path.unlink()
            del self._disk_index[key]
            self._save_disk_index()
    
    def get(self, key: str) -> Optional[str]:
        """获取缓存文件路径"""
        # L1: 检查内存
        if key in self._memory_cache:
            return self._memory_cache[key]
        
        # L2: 检查磁盘索引
        if key in self._disk_index:
            entry = self._disk_index[key]
            file_path = Path(entry['file_path'])
            
            # 检查是否过期
            if entry.get('expires_at', 0) < time.time():
                self._remove_from_disk(key)
                return None
            
            if file_path.exists():
                # 提升到内存缓存
                self._add_to_memory(key, str(file_path))
                return str(file_path)
            else:
                self._remove_from_disk(key)
        
        return None
    
    def set(self, key: str, file_path: str, metadata: dict = None, ttl_hours: int = 24):
        """设置缓存"""
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        # 复制到缓存目录
        cached_file = self._files_dir / f"{key}_{file_path.name}"
        shutil.copy2(file_path, cached_file)
        
        # 保存到内存和磁盘
        self._add_to_memory(key, str(cached_file))
        self._save_to_disk(key, str(cached_file), metadata or {}, ttl_hours)
    
    def exists(self, key: str) -> bool:
        """检查缓存是否存在"""
        return self.get(key) is not None
    
    def clear(self, older_than_hours: int = None):
        """清理缓存"""
        now = time.time()
        keys_to_remove = []
        
        for key, entry in self._disk_index.items():
            if older_than_hours is None:
                keys_to_remove.append(key)
            elif entry.get('created_at', 0) < (now - older_than_hours * 3600):
                keys_to_remove.append(key)
        
        for key in keys_to_remove:
            self._remove_from_disk(key)
        
        self._memory_cache.clear()
        self._memory_order.clear()
    
    def get_stats(self) -> dict:
        """获取缓存统计信息"""
        total_size = sum(
            Path(entry['file_path']).stat().st_size 
            for entry in self._disk_index.values() 
            if Path(entry['file_path']).exists()
        )
        
        return {
            'memory_items': len(self._memory_cache),
            'disk_items': len(self._disk_index),
            'total_size_mb': round(total_size / 1024 / 1024, 2),
            'max_memory_items': self.max_memory_items
        }


# 全局缓存实例
global_cache = SmartCache()


def cached_result(cache_type: str, ttl_hours: int = 24):
    """缓存装饰器"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            # 生成缓存键
            key_parts = [func.__name__, cache_type]
            key_parts.extend(str(arg) for arg in args)
            key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
            cache_key = hashlib.sha256("|".join(key_parts).encode()).hexdigest()[:16]
            
            # 检查缓存
            cached_path = global_cache.get(cache_key)
            if cached_path:
                print(f"[Cache HIT] {cache_type}: {cache_key}")
                return cached_path
            
            # 执行函数
            result = func(*args, **kwargs)
            
            # 保存到缓存
            if result and os.path.exists(result):
                global_cache.set(cache_key, result, {'type': cache_type}, ttl_hours)
                print(f"[Cache MISS] Saved {cache_type}: {cache_key}")
            
            return result
        return wrapper
    return decorator
