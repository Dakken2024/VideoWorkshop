#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
运行所有测试 - 统一测试入口
"""

import os
import sys
import unittest
import importlib

# 确保 video_gen 模块可导入
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))


def discover_tests():
    """发现所有测试用例"""
    test_dir = os.path.dirname(os.path.abspath(__file__))
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # 手动加载测试模块
    test_modules = [
        "test_subtitle_import",
        "test_pipeline",
    ]

    for module_name in test_modules:
        try:
            module = importlib.import_module(f"video_gen.tests.{module_name}")
            # 加载 TestCase 子类
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if isinstance(attr, type) and issubclass(attr, unittest.TestCase):
                    suite.addTest(loader.loadTestsFromTestCase(attr))
        except ImportError as e:
            print(f"跳过 {module_name}: {e}")

    return suite


def main():
    """主函数"""
    print("=" * 60)
    print("Video Workshop - 测试套件")
    print("=" * 60)

    suite = discover_tests()
    runner = unittest.TextTestRunner(verbosity=2)

    print(f"\n发现 {suite.countTestCases()} 个测试用例\n")
    result = runner.run(suite)

    print(f"\n{'=' * 60}")
    print(f"总计: {result.testsRun} 个测试")
    if result.wasSuccessful():
        print("结果: 全部通过!")
    else:
        print(f"失败: {len(result.failures)}, 错误: {len(result.errors)}")
    print(f"{'=' * 60}")

    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())