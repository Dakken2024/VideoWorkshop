#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
流水线功能测试 - 验证各模块集成正确性
"""

import os
import sys
import json
import tempfile
import unittest

# 确保 video_gen 模块可导入
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from video_gen.config import (
    AppConfig, PathConfig, VideoEncodingConfig,
    SubtitleConfig, AudioConfig, ImageConfig, DEFAULT_CONFIG
)
from video_gen.utils.file_utils import (
    ensure_dir, safe_read_json, safe_write_json,
    title_to_filename, get_output_dir
)
from video_gen.utils.validators import validate_script, validate_config
from video_gen.video.effects import apply_ken_burns_effect, create_fade_frames
from video_gen.video.encoder import VideoEncoder
from video_gen.audio.pause_analyzer import ChinesePauseAnalyzer


class TestConfig(unittest.TestCase):
    """测试配置模块"""

    def test_default_config(self):
        """测试默认配置创建"""
        config = AppConfig()
        self.assertIsNotNone(config.paths)
        self.assertIsNotNone(config.video)
        self.assertIsNotNone(config.subtitle)
        self.assertIsNotNone(config.audio)
        self.assertIsNotNone(config.image)

    def test_subtitle_config_defaults(self):
        """测试字幕默认配置"""
        config = SubtitleConfig()
        self.assertTrue(config.enabled)
        self.assertEqual(config.font_size, 36)
        self.assertEqual(config.output_format, "srt")
        self.assertEqual(config.position, "bottom")
        self.assertEqual(config.max_chars_per_line, 20)
        self.assertIn("Microsoft YaHei", config.preferred_fonts)

    def test_video_config_defaults(self):
        """测试视频编码默认配置"""
        config = VideoEncodingConfig()
        self.assertEqual(config.fps, 30)
        self.assertEqual(config.crf, 23)
        self.assertEqual(config.codec, "libx264")
        self.assertTrue(config.faststart)

    def test_audio_config_defaults(self):
        """测试音频默认配置"""
        config = AudioConfig()
        self.assertEqual(config.voice, "zh-CN-XiaoxiaoNeural")
        self.assertIsNotNone(config.fallback_voice)
        self.assertEqual(config.pause_short, 300)
        self.assertEqual(config.pause_long, 800)

    def test_image_config_defaults(self):
        """测试图片默认配置"""
        config = ImageConfig()
        self.assertEqual(config.width, 1080)
        self.assertEqual(config.height, 1920)
        self.assertEqual(config.max_retries, 3)


class TestValidators(unittest.TestCase):
    """测试验证器"""

    def test_validate_script_empty(self):
        """测试空脚本验证"""
        result = validate_script("")
        self.assertFalse(result.is_valid)
        self.assertGreater(len(result.errors), 0)

    def test_validate_script_invalid_json(self):
        """测试无效 JSON 验证"""
        result = validate_script("{invalid json}")
        self.assertFalse(result.is_valid)
        self.assertIn("JSON 解析错误", result.errors[0])

    def test_validate_script_valid(self):
        """测试有效脚本验证"""
        script = json.dumps({
            "meta": {"title": "Test"},
            "scenes": [
                {"scene_id": 1, "text": "文本", "prompt": "提示词", "duration_sec": 5}
            ]
        })
        result = validate_script(script)
        self.assertTrue(result.is_valid)
        self.assertIsNotNone(result.data)

    def test_validate_script_missing_scenes(self):
        """测试缺少场景的脚本验证"""
        script = json.dumps({"meta": {"title": "Test"}, "scenes": []})
        result = validate_script(script)
        self.assertFalse(result.is_valid)

    def test_validate_config(self):
        """测试配置验证"""
        config = {"width": 1080, "height": 1920, "fps": 30, "crf": 23}
        result = validate_config(config)
        self.assertTrue(result.is_valid)

    def test_validate_config_invalid_crf(self):
        """测试无效 CRF 验证"""
        config = {"width": 1080, "height": 1920, "fps": 30, "crf": 100}
        result = validate_config(config)
        self.assertFalse(result.is_valid)


class TestFileUtils(unittest.TestCase):
    """测试文件工具"""

    def test_ensure_dir(self):
        """测试目录创建"""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_dir = os.path.join(tmpdir, "test", "nested", "dir")
            created = ensure_dir(test_dir)
            self.assertTrue(os.path.exists(created))

    def test_safe_read_json_nonexistent(self):
        """测试读取不存在的文件"""
        result = safe_read_json("/nonexistent/file.json")
        self.assertIsNone(result)

    def test_safe_read_json_valid(self):
        """测试读取有效 JSON 文件"""
        with tempfile.NamedTemporaryFile(
            suffix=".json", delete=False, mode="w"
        ) as f:
            json.dump({"key": "value"}, f)
            path = f.name

        try:
            result = safe_read_json(path)
            self.assertEqual(result, {"key": "value"})
        finally:
            os.unlink(path)

    def test_safe_write_json(self):
        """测试写入 JSON 文件"""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "test.json")
            success = safe_write_json(path, {"key": "value"})
            self.assertTrue(success)
            self.assertTrue(os.path.exists(path))

    def test_title_to_filename_pinyin(self):
        """测试中文标题转拼音文件名"""
        try:
            filename = title_to_filename("测试标题")
            self.assertIsNotNone(filename)
            self.assertGreater(len(filename), 0)
        except ImportError:
            pass  # pypinyin not installed

    def test_title_to_filename_ascii(self):
        """测试英文标题转文件名"""
        filename = title_to_filename("Hello World")
        self.assertIn("Hello", filename)
        self.assertIn("World", filename)


class TestEffects(unittest.TestCase):
    """测试视频特效"""

    def test_ken_burns_initial(self):
        """测试 Ken Burns 效果初始状态"""
        from PIL import Image
        img = Image.new("RGB", (100, 100))
        result = apply_ken_burns_effect(img, 0.0)
        self.assertEqual(result.size, (100, 100))

    def test_ken_burns_end(self):
        """测试 Ken Burns 效果结束状态"""
        from PIL import Image
        img = Image.new("RGB", (100, 100))
        result = apply_ken_burns_effect(img, 1.0)
        self.assertEqual(result.size, (100, 100))

    def test_create_fade_frames(self):
        """测试淡入淡出帧创建"""
        from PIL import Image
        img1 = Image.new("RGB", (100, 100), color=(255, 0, 0))
        img2 = Image.new("RGB", (100, 100), color=(0, 0, 255))
        frames = create_fade_frames(img1, img2, 5)
        self.assertEqual(len(frames), 5)


class TestPauseAnalyzer(unittest.TestCase):
    """测试中文停顿分析器"""

    def setUp(self):
        self.analyzer = ChinesePauseAnalyzer()

    def test_analyze_empty(self):
        """测试空文本"""
        text, pause = self.analyzer.analyze_text("")
        self.assertEqual(text, "")
        self.assertEqual(pause, 0)

    def test_analyze_period(self):
        """测试句号停顿"""
        text, pause = self.analyzer.analyze_text("这是句号。")
        self.assertEqual(pause, 800)  # pause_long

    def test_analyze_comma(self):
        """测试逗号停顿"""
        text, pause = self.analyzer.analyze_text("这是逗号，")
        self.assertEqual(pause, 500)  # pause_medium

    def test_analyze_no_pause(self):
        """测试无停顿"""
        text, pause = self.analyzer.analyze_text("中间文字")
        self.assertEqual(pause, 0)


class TestVideoEncoder(unittest.TestCase):
    """测试视频编码器"""

    def setUp(self):
        self.encoder = VideoEncoder()

    def test_get_ffmpeg_params(self):
        """测试获取 FFmpeg 参数"""
        params = self.encoder.get_ffmpeg_params()
        self.assertIn("fps", params)
        self.assertIn("codec", params)
        self.assertIn("audio_codec", params)
        self.assertIn("ffmpeg_params", params)

    def test_ffmpeg_params_contains_crf(self):
        """测试 CRF 参数存在"""
        params = self.encoder.get_ffmpeg_params()
        ffmpeg_params = params["ffmpeg_params"]
        # 检查是否有 crf 参数（CPU 模式）或 cq 参数（GPU 模式）
        has_crf = any("-crf" in str(p) or "-cq" in str(p) for p in ffmpeg_params)
        self.assertTrue(has_crf)


def run_pipeline_tests():
    """运行流水线测试"""
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestConfig))
    suite.addTest(unittest.makeSuite(TestValidators))
    suite.addTest(unittest.makeSuite(TestFileUtils))
    suite.addTest(unittest.makeSuite(TestEffects))
    suite.addTest(unittest.makeSuite(TestPauseAnalyzer))
    suite.addTest(unittest.makeSuite(TestVideoEncoder))

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
    success = run_pipeline_tests()
    sys.exit(0 if success else 1)