#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
素材资产管理模块 - 标签化素材库管理

功能：
1. 素材入库（图片/音频/视频）
2. 标签管理（添加/删除/搜索）
3. 素材检索（按标签/类型/时间）
4. 素材预览信息
5. 使用统计
"""

import os
import sys
import json
import shutil
import hashlib
from datetime import datetime
from typing import Dict, List, Optional, Set
from dataclasses import dataclass, field
from pathlib import Path

# 处理导入路径
try:
    from video_gen.utils.logger import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)


@dataclass
class AssetItem:
    """素材项"""
    id: str
    file_path: str
    asset_type: str  # image, audio, video
    tags: Set[str] = field(default_factory=set)
    created_at: str = ""
    size_bytes: int = 0
    duration_sec: float = 0.0  # 音视频时长
    dimensions: tuple = (0, 0)  # 宽高 (图片/视频)
    usage_count: int = 0
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "file_path": self.file_path,
            "asset_type": self.asset_type,
            "tags": list(self.tags),
            "created_at": self.created_at,
            "size_bytes": self.size_bytes,
            "duration_sec": self.duration_sec,
            "dimensions": self.dimensions,
            "usage_count": self.usage_count
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "AssetItem":
        return cls(
            id=data["id"],
            file_path=data["file_path"],
            asset_type=data["asset_type"],
            tags=set(data.get("tags", [])),
            created_at=data.get("created_at", ""),
            size_bytes=data.get("size_bytes", 0),
            duration_sec=data.get("duration_sec", 0.0),
            dimensions=tuple(data.get("dimensions", (0, 0))),
            usage_count=data.get("usage_count", 0)
        )


class AssetManager:
    """
    素材资产管理器
    
    提供素材的入库、检索、标签管理等功能
    """
    
    def __init__(self, assets_dir: str = "./assets"):
        self.assets_dir = Path(assets_dir)
        self.index_file = self.assets_dir / "asset_index.json"
        self.assets: Dict[str, AssetItem] = {}
        
        # 确保目录存在
        self.assets_dir.mkdir(parents=True, exist_ok=True)
        (self.assets_dir / "images").mkdir(exist_ok=True)
        (self.assets_dir / "audio").mkdir(exist_ok=True)
        (self.assets_dir / "video").mkdir(exist_ok=True)
        
        # 加载索引
        self._load_index()
    
    def _load_index(self):
        """加载素材索引"""
        if self.index_file.exists():
            try:
                with open(self.index_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for item_id, item_data in data.items():
                        self.assets[item_id] = AssetItem.from_dict(item_data)
                logger.info(f"已加载 {len(self.assets)} 个素材")
            except Exception as e:
                logger.error(f"加载素材索引失败：{e}")
                self.assets = {}
    
    def _save_index(self):
        """保存素材索引"""
        try:
            data = {item_id: item.to_dict() for item_id, item in self.assets.items()}
            with open(self.index_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            logger.debug("素材索引已保存")
        except Exception as e:
            logger.error(f"保存素材索引失败：{e}")
    
    def _generate_id(self, file_path: str) -> str:
        """生成素材 ID（基于文件内容哈希）"""
        hasher = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                hasher.update(chunk)
        return hasher.hexdigest()[:16]
    
    def _get_asset_type(self, file_path: str) -> str:
        """根据文件扩展名判断素材类型"""
        ext = Path(file_path).suffix.lower()
        image_exts = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp"}
        audio_exts = {".mp3", ".wav", ".ogg", ".m4a", ".aac"}
        video_exts = {".mp4", ".avi", ".mov", ".mkv", ".webm"}
        
        if ext in image_exts:
            return "image"
        elif ext in audio_exts:
            return "audio"
        elif ext in video_exts:
            return "video"
        else:
            raise ValueError(f"不支持的文件类型：{ext}")
    
    def _get_file_info(self, file_path: str) -> dict:
        """获取文件基本信息"""
        stat = os.stat(file_path)
        info = {
            "size_bytes": stat.st_size,
            "duration_sec": 0.0,
            "dimensions": (0, 0)
        }
        
        # 尝试获取更多信息（需要 opencv 或 mutagen）
        asset_type = self._get_asset_type(file_path)
        
        if asset_type == "image":
            try:
                from PIL import Image
                with Image.open(file_path) as img:
                    info["dimensions"] = img.size
            except ImportError:
                pass
            except Exception as e:
                logger.debug(f"读取图片尺寸失败：{e}")
        
        elif asset_type == "audio":
            try:
                import mutagen
                audio = mutagen.File(file_path)
                if audio:
                    info["duration_sec"] = audio.info.length
            except ImportError:
                pass
            except Exception as e:
                logger.debug(f"读取音频时长失败：{e}")
        
        elif asset_type == "video":
            try:
                import cv2
                cap = cv2.VideoCapture(file_path)
                if cap.isOpened():
                    info["dimensions"] = (
                        int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
                        int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                    )
                    fps = cap.get(cv2.CAP_PROP_FPS)
                    frames = cap.get(cv2.CAP_PROP_FRAME_COUNT)
                    if fps > 0:
                        info["duration_sec"] = frames / fps
                    cap.release()
            except ImportError:
                pass
            except Exception as e:
                logger.debug(f"读取视频信息失败：{e}")
        
        return info
    
    def add_asset(self, file_path: str, tags: Optional[List[str]] = None, 
                  move_to_library: bool = True) -> Optional[AssetItem]:
        """
        添加素材到库
        
        Args:
            file_path: 素材文件路径
            tags: 标签列表
            move_to_library: 是否移动到素材库目录
            
        Returns:
            AssetItem 或 None
        """
        if not os.path.exists(file_path):
            logger.error(f"文件不存在：{file_path}")
            return None
        
        try:
            # 生成 ID
            asset_id = self._generate_id(file_path)
            
            # 检查是否已存在
            if asset_id in self.assets:
                logger.warning(f"素材已存在：{asset_id}")
                return self.assets[asset_id]
            
            # 获取类型
            asset_type = self._get_asset_type(file_path)
            
            # 获取文件信息
            file_info = self._get_file_info(file_path)
            
            # 确定目标路径
            if move_to_library:
                type_dir = self.assets_dir / f"{asset_type}s"
                dest_path = type_dir / f"{asset_id}{Path(file_path).suffix}"
                shutil.copy2(file_path, dest_path)
                final_path = str(dest_path)
            else:
                final_path = os.path.abspath(file_path)
            
            # 创建素材项
            asset = AssetItem(
                id=asset_id,
                file_path=final_path,
                asset_type=asset_type,
                tags=set(tags or []),
                created_at=datetime.now().isoformat(),
                **file_info
            )
            
            # 添加到索引
            self.assets[asset_id] = asset
            self._save_index()
            
            logger.info(f"素材已添加：{asset_id} ({asset_type})")
            return asset
            
        except Exception as e:
            logger.error(f"添加素材失败：{e}")
            return None
    
    def remove_asset(self, asset_id: str, delete_file: bool = False) -> bool:
        """
        移除素材
        
        Args:
            asset_id: 素材 ID
            delete_file: 是否删除文件
            
        Returns:
            是否成功
        """
        if asset_id not in self.assets:
            logger.warning(f"素材不存在：{asset_id}")
            return False
        
        asset = self.assets[asset_id]
        
        if delete_file and os.path.exists(asset.file_path):
            try:
                os.remove(asset.file_path)
                logger.debug(f"已删除文件：{asset.file_path}")
            except Exception as e:
                logger.error(f"删除文件失败：{e}")
        
        del self.assets[asset_id]
        self._save_index()
        logger.info(f"素材已移除：{asset_id}")
        return True
    
    def search_assets(self, query: str = "", tags: Optional[List[str]] = None,
                      asset_type: Optional[str] = None,
                      limit: int = 50) -> List[AssetItem]:
        """
        搜索素材
        
        Args:
            query: 搜索关键词（匹配文件名）
            tags: 标签过滤（AND 关系）
            asset_type: 类型过滤
            limit: 返回数量限制
            
        Returns:
            素材列表
        """
        results = []
        
        for asset in self.assets.values():
            # 类型过滤
            if asset_type and asset.asset_type != asset_type:
                continue
            
            # 标签过滤
            if tags:
                if not all(tag in asset.tags for tag in tags):
                    continue
            
            # 关键词搜索
            if query:
                filename = Path(asset.file_path).name.lower()
                if query.lower() not in filename:
                    continue
            
            results.append(asset)
            
            if len(results) >= limit:
                break
        
        return results
    
    def get_all_tags(self) -> Set[str]:
        """获取所有标签"""
        all_tags = set()
        for asset in self.assets.values():
            all_tags.update(asset.tags)
        return all_tags
    
    def add_tags(self, asset_id: str, tags: List[str]) -> bool:
        """添加标签"""
        if asset_id not in self.assets:
            return False
        
        asset = self.assets[asset_id]
        asset.tags.update(tags)
        self._save_index()
        return True
    
    def remove_tags(self, asset_id: str, tags: List[str]) -> bool:
        """移除标签"""
        if asset_id not in self.assets:
            return False
        
        asset = self.assets[asset_id]
        asset.tags.difference_update(tags)
        self._save_index()
        return True
    
    def increment_usage(self, asset_id: str):
        """增加使用计数"""
        if asset_id in self.assets:
            self.assets[asset_id].usage_count += 1
            self._save_index()
    
    def get_asset(self, asset_id: str) -> Optional[AssetItem]:
        """获取单个素材"""
        return self.assets.get(asset_id)
    
    def get_stats(self) -> dict:
        """获取统计信息"""
        stats = {
            "total_count": len(self.assets),
            "by_type": {"image": 0, "audio": 0, "video": 0},
            "total_size_mb": 0,
            "tag_count": len(self.get_all_tags())
        }
        
        for asset in self.assets.values():
            stats["by_type"][asset.asset_type] += 1
            stats["total_size_mb"] += asset.size_bytes / (1024 * 1024)
        
        return stats


# 全局单例
_global_manager: Optional[AssetManager] = None


def get_asset_manager(assets_dir: str = "./assets") -> AssetManager:
    """获取全局素材管理器实例"""
    global _global_manager
    if _global_manager is None:
        _global_manager = AssetManager(assets_dir)
    return _global_manager
