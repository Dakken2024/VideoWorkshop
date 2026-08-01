#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
字幕自动导入功能测试
验证 SubtitleImporter 各功能模块的正确性
"""

import os
import sys
import json
import tempfile
import unittest

# 确保 video_gen 模块可导入
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from video_gen.subtitle_importer import SubtitleImporter
from video_gen.config import SubtitleConfig
from video_gen.video.subtitle import SubtitleGenerator, SubtitleEntry, SubtitleEmbedder


class TestSubtitleEntry(unittest.TestCase):
    """测试字幕条目数据模型"""

    def test_srt_block_format(self):
        """测试 SRT 格式块生成"""
        entry = SubtitleEntry(
            index=1,
            start_time=0.0,
            end_time=5.5,
            text="这是一个测试字幕"
        )
        block = entry.to_srt_block()
        self.assertIn("1", block)
        self.assertIn("00:00:00,000 --> 00:00:05,500", block)
        self.assertIn("这是一个测试字幕", block)

    def test_ass_dialogue_format(self):
        """测试 ASS 对话行格式"""
        entry = SubtitleEntry(
            index=1,
            start_time=0.0,
            end_time=5.5,
            text="测试字幕"
        )
        dialogue = entry.to_ass_dialogue()
        self.assertIn("Dialogue:", dialogue)
        self.assertIn("0:00:00.00", dialogue)
        self.assertIn("0:00:05.50", dialogue)
        self.assertIn("测试字幕", dialogue)


class TestSubtitleGenerator(unittest.TestCase):
    """测试字幕生成器"""

    def setUp(self):
        self.config = SubtitleConfig()
        self.generator = SubtitleGenerator(self.config)

    def test_generate_from_scenes_empty(self):
        """测试空场景列表"""
        entries = self.generator.generate_from_scenes([])
        self.assertEqual(len(entries), 0)

    def test_generate_from_scenes_single(self):
        """测试单个场景生成"""
        scenes = [
            {"scene_id": 1, "text": "测试场景", "duration_sec": 5}
        ]
        entries = self.generator.generate_from_scenes(scenes)
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0].text, "测试场景")
        self.assertEqual(entries[0].start_time, 0.0)
        self.assertEqual(entries[0].end_time, 5.0)

    def test_generate_from_scenes_multi(self):
        """测试多个场景生成"""
        scenes = [
            {"scene_id": 1, "text": "第一场景", "duration_sec": 5},
            {"scene_id": 2, "text": "第二场景", "duration_sec": 3},
        ]
        entries = self.generator.generate_from_scenes(scenes)
        self.assertEqual(len(entries), 2)
        self.assertEqual(entries[0].start_time, 0.0)
        self.assertEqual(entries[0].end_time, 5.0)
        self.assertEqual(entries[1].start_time, 5.0)
        self.assertEqual(entries[1].end_time, 8.0)

    def test_generate_with_exact_timing(self):
        """测试精确时间轴对齐"""
        scenes = [
            {"scene_id": 1, "text": "场景A", "duration_sec": 5},
            {"scene_id": 2, "text": "场景B", "duration_sec": 5},
        ]
        durations = [4.0, 6.0]
        entries = self.generator.generate_from_scenes(
            scenes, scene_audio_durations=durations
        )
        self.assertEqual(len(entries), 2)
        self.assertEqual(entries[0].end_time, 4.0)
        self.assertEqual(entries[1].start_time, 4.0)
        self.assertEqual(entries[1].end_time, 10.0)

    def test_generate_with_proportional_timing(self):
        """测试按比例分配时间轴"""
        scenes = [
            {"scene_id": 1, "text": "场景A", "duration_sec": 5},
            {"scene_id": 2, "text": "场景B", "duration_sec": 5},
        ]
        audio_duration = 20.0
        entries = self.generator.generate_from_scenes(
            scenes, audio_duration=audio_duration
        )
        self.assertEqual(len(entries), 2)
        self.assertEqual(entries[0].end_time, 10.0)
        self.assertEqual(entries[1].end_time, 20.0)

    def test_auto_wrap_short_text(self):
        """测试短文本不换行"""
        text = "短文本"
        wrapped = self.generator._auto_wrap(text)
        self.assertEqual(wrapped, text)

    def test_auto_wrap_long_text(self):
        """测试长文本自动换行"""
        text = "这是一个很长很长的测试文本，用于验证自动换行功能是否正常工作。"
        wrapped = self.generator._auto_wrap(text)
        lines = wrapped.split('\n')
        for line in lines:
            self.assertLessEqual(len(line), self.config.max_chars_per_line)

    def test_split_text(self):
        """测试文本分句"""
        text = "第一句。第二句？第三句！"
        sentences = self.generator._split_text(text)
        self.assertGreaterEqual(len(sentences), 1)

    def test_generate_srt(self):
        """测试 SRT 文件生成"""
        entries = [
            SubtitleEntry(index=1, start_time=0.0, end_time=5.0, text="第一句"),
            SubtitleEntry(index=2, start_time=5.0, end_time=10.0, text="第二句"),
        ]
        with tempfile.NamedTemporaryFile(suffix=".srt", delete=False, mode="w") as f:
            output_path = f.name

        try:
            success = self.generator.generate_srt(entries, output_path)
            self.assertTrue(success)
            self.assertTrue(os.path.exists(output_path))

            with open(output_path, "r", encoding="utf-8") as f:
                content = f.read()
            self.assertIn("第一句", content)
            self.assertIn("第二句", content)
            self.assertIn("00:00:00,000 --> 00:00:05,000", content)
        finally:
            if os.path.exists(output_path):
                os.unlink(output_path)

    def test_generate_ass(self):
        """测试 ASS 文件生成"""
        entries = [
            SubtitleEntry(index=1, start_time=0.0, end_time=5.0, text="测试字幕"),
        ]
        with tempfile.NamedTemporaryFile(suffix=".ass", delete=False, mode="w") as f:
            output_path = f.name

        try:
            success = self.generator.generate_ass(entries, output_path)
            self.assertTrue(success)
            self.assertTrue(os.path.exists(output_path))

            with open(output_path, "r", encoding="utf-8") as f:
                content = f.read()
            self.assertIn("[Script Info]", content)
            self.assertIn("[V4+ Styles]", content)
            self.assertIn("[Events]", content)
            self.assertIn("测试字幕", content)
        finally:
            if os.path.exists(output_path):
                os.unlink(output_path)


class TestSubtitleImporter(unittest.TestCase):
    """测试字幕自动导入器"""

    def setUp(self):
        self.config = SubtitleConfig()
        self.importer = SubtitleImporter(self.config)

    def test_auto_detect_video_not_found(self):
        """测试空目录中自动检测视频"""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = self.importer.auto_detect_video(tmpdir)
            self.assertIsNone(result)

    def test_auto_detect_video_found(self):
        """测试目录中检测到视频文件"""
        with tempfile.TemporaryDirectory() as tmpdir:
            video_path = os.path.join(tmpdir, "test.mp4")
            open(video_path, "w").close()
            result = self.importer.auto_detect_video(tmpdir)
            self.assertEqual(result, video_path)

    def test_auto_detect_script_not_found(self):
        """测试空目录中自动检测脚本"""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = self.importer.auto_detect_script(tmpdir)
            self.assertIsNone(result)

    def test_auto_detect_script_found(self):
        """测试目录中检测到脚本文件"""
        with tempfile.TemporaryDirectory() as tmpdir:
            script_path = os.path.join(tmpdir, "scripts.json")
            with open(script_path, "w", encoding="utf-8") as f:
                json.dump({"scenes": []}, f)
            result = self.importer.auto_detect_script(tmpdir)
            self.assertEqual(result, script_path)

    def test_verify_import_missing_video(self):
        """测试验证不存在的视频"""
        report = self.importer.verify_import("/path/to/nonexistent.mp4")
        self.assertFalse(report["verification_passed"])
        self.assertIn("视频文件不存在", report["issues"])


class TestSubtitleManager(unittest.TestCase):
    """测试字幕管理器"""

    def setUp(self):
        self.config = SubtitleConfig()
        from video_gen.video.subtitle import SubtitleManager
        self.manager = SubtitleManager(self.config)

    def test_process_disabled(self):
        """测试字幕禁用时跳过"""
        self.config.enabled = False
        result = self.manager.process([], "/fake/video.mp4", "/fake/output.mp4")
        self.assertFalse(result)


def run_all_tests():
    """运行所有测试"""
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestSubtitleEntry))
    suite.addTest(unittest.makeSuite(TestSubtitleGenerator))
    suite.addTest(unittest.makeSuite(TestSubtitleImporter))
    suite.addTest(unittest.makeSuite(TestSubtitleManager))

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    print(f"\n{'=' * 50}")
    print(f"测试结果: {result.testsRun} 个测试")
    if result.wasSuccessful():
        print("全部通过!")
    else:
        print(f"失败: {len(result.failures)}, 错误: {len(result.errors)}")
    print(f"{'=' * 50}")

    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)