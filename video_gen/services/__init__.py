#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""AI 服务模块"""

# 从 src 导入优化后的服务
import sys
from pathlib import Path

src_path = Path(__file__).parent.parent.parent / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

try:
    from services.director_agent import DirectorAgent, Scene, Transition, BGMRecommendation
    __all__ = ["DirectorAgent", "Scene", "Transition", "BGMRecommendation"]
except ImportError as e:
    print(f"警告：无法导入 director_agent: {e}")
    __all__ = []
