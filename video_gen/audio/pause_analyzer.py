#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
中文停顿分析器 - 根据标点符号和语义分析计算停顿时长
"""

import re
from typing import Tuple, List
from ..config import AudioConfig, DEFAULT_CONFIG


class ChinesePauseAnalyzer:
    """
    中文文本停顿分析器
    根据标点符号和语义分析，计算每个文本片段需要的停顿时长
    """

    def __init__(self, config: AudioConfig = None):
        self.config = config or DEFAULT_CONFIG.audio

    def analyze_text(self, text: str) -> Tuple[str, int]:
        """
        分析文本，返回 (清理后的文本，停顿时长 ms)

        规则：
        - 句号、问号、感叹号 → 长停顿
        - 逗号、分号 → 中停顿
        - 顿号 → 短停顿
        - 连接词 → 短停顿
        """
        clean_text = re.sub(r'<[^>]+>', '', text).strip()

        if not clean_text:
            return clean_text, 0

        last_char = clean_text[-1]

        # 长停顿标点
        if last_char in ['。', '！', '？', '!', '?']:
            return clean_text, self.config.pause_long

        # 中停顿标点
        if last_char in ['，', '；', ',', ';']:
            return clean_text, self.config.pause_medium

        # 短停顿标点
        if last_char in ['、']:
            return clean_text, self.config.pause_short

        # 连接词结尾
        connecting_words = ['但是', '然而', '不过', '所以', '因此']
        for word in connecting_words:
            if clean_text.endswith(word):
                return clean_text, self.config.pause_short

        # 默认无停顿
        return clean_text, 0

    def analyze_all(self, texts: List[str]) -> List[Tuple[str, int]]:
        """批量分析多个文本"""
        return [self.analyze_text(t) for t in texts]

    def get_total_pause_duration(self, texts: List[str]) -> int:
        """获取所有文本的总停顿时长"""
        total = 0
        for text in texts:
            _, pause = self.analyze_text(text)
            total += pause
        return total