#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
视频优化验证脚本
用于测试和验证微信视频号优化效果
"""

import os
import sys
import json
import subprocess
from datetime import datetime


def check_ffmpeg():
    """检查FFmpeg是否可用"""
    try:
        result = subprocess.run(['ffmpeg', '-version'], capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ FFmpeg 可用")
            return True
    except FileNotFoundError:
        pass
    
    print("❌ FFmpeg 不可用，请安装FFmpeg")
    return False


def check_moviepy():
    """检查MoviePy是否可用"""
    try:
        from moviepy import __version__
        print(f"✅ MoviePy 可用 (版本: {__version__})")
        return True
    except ImportError:
        print("❌ MoviePy 不可用，请运行: pip install moviepy")
        return False


def check_edge_tts():
    """检查Edge-TTS是否可用"""
    try:
        import edge_tts
        print("✅ Edge-TTS 可用")
        return True
    except ImportError:
        print("❌ Edge-TTS 不可用，请运行: pip install edge-tts")
        return False


def verify_optimization_config():
    """验证优化配置"""
    print("\n📋 验证优化配置...")
    
    config_path = "video_config.json"
    if os.path.exists(config_path):
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        wechat_config = config.get('wechat_channels', {})
        
        print(f"  分辨率: {wechat_config.get('resolution')}")
        print(f"  帧率: {wechat_config.get('fps')} fps")
        print(f"  编码器: {wechat_config.get('codec')}")
        print(f"  CRF: {wechat_config.get('crf')}")
        print(f"  Preset: {wechat_config.get('preset')}")
        print(f"  音频码率: {wechat_config.get('audio_bitrate')}")
        print(f"  FastStart: {wechat_config.get('faststart')}")
        return True
    else:
        print(f"❌ 配置文件不存在: {config_path}")
        return False


def test_encoding_params():
    """测试编码参数"""
    print("\n🧪 测试编码参数...")
    
    try:
        from moviepy import ColorClip
        
        test_output = "test_encoding_output.mp4"
        
        clip = ColorClip(size=(1080, 1920), color=(100, 150, 200), duration=2)
        
        clip.write_videofile(
            test_output,
            fps=30,
            codec='libx264',
            preset='slow',
            ffmpeg_params=[
                '-crf', '23',
                '-profile:v', 'high',
                '-level', '4.1',
                '-pix_fmt', 'yuv420p',
                '-movflags', '+faststart',
                '-threads', '0',
            ],
            audio_bitrate='128k',
            logger=None
        )
        
        file_size = os.path.getsize(test_output)
        print(f"✅ 编码测试成功")
        print(f"  测试文件大小: {file_size / 1024:.1f} KB")
        
        os.remove(test_output)
        return True
        
    except Exception as e:
        print(f"❌ 编码测试失败: {str(e)}")
        return False


def analyze_existing_video(video_path):
    """分析现有视频"""
    if not os.path.exists(video_path):
        print(f"❌ 视频文件不存在: {video_path}")
        return
    
    print(f"\n📊 分析视频: {os.path.basename(video_path)}")
    
    try:
        from wechat_video_optimizer import WeChatVideoOptimizer
        
        optimizer = WeChatVideoOptimizer()
        report = optimizer.generate_report(video_path)
        
        if 'error' in report:
            print(f"❌ 分析失败: {report['error']}")
            return
        
        analysis = report.get('video_analysis', {})
        
        print(f"\n基本信息:")
        print(f"  文件大小: {analysis.get('file_size_mb', 0):.1f} MB")
        print(f"  时长: {analysis.get('duration_sec', 0):.1f} 秒")
        print(f"  总码率: {analysis.get('overall_bitrate_kbps', 0):.0f} kbps")
        
        video = analysis.get('video', {})
        if video:
            print(f"\n视频信息:")
            print(f"  编码: {video.get('codec')}")
            print(f"  分辨率: {video.get('width')}x{video.get('height')}")
            print(f"  帧率: {video.get('fps', 0):.1f} fps")
            print(f"  Profile: {video.get('profile')}")
        
        audio = analysis.get('audio', {})
        if audio:
            print(f"\n音频信息:")
            print(f"  编码: {audio.get('codec')}")
            print(f"  采样率: {audio.get('sample_rate', 0)} Hz")
            print(f"  声道数: {audio.get('channels')}")
        
        issues = analysis.get('issues', [])
        if issues:
            print(f"\n⚠️ 发现问题:")
            for issue in issues:
                print(f"  - {issue}")
        
        recommendations = analysis.get('recommendations', [])
        if recommendations:
            print(f"\n💡 优化建议:")
            for rec in recommendations:
                print(f"  - {rec}")
        
        compatibility = report.get('wechat_compatibility', {})
        is_compatible = compatibility.get('is_compatible', False)
        print(f"\n微信视频号兼容性: {'✅ 兼容' if is_compatible else '❌ 不兼容'}")
        
    except ImportError:
        print("❌ 无法导入优化器模块")
    except Exception as e:
        print(f"❌ 分析失败: {str(e)}")


def main():
    """主函数"""
    print("=" * 60)
    print("微信视频号优化验证工具")
    print("=" * 60)
    
    print("\n🔍 检查依赖...")
    
    checks = [
        check_ffmpeg(),
        check_moviepy(),
        check_edge_tts(),
    ]
    
    if not all(checks):
        print("\n❌ 部分依赖缺失，请先安装")
        return
    
    verify_optimization_config()
    
    test_encoding_params()
    
    if len(sys.argv) > 1:
        video_path = sys.argv[1]
        analyze_existing_video(video_path)
    else:
        print("\n💡 提示: 可以传入视频文件路径进行详细分析")
        print("   用法: python verify_optimization.py <video_path>")
    
    print("\n" + "=" * 60)
    print("验证完成")
    print("=" * 60)


if __name__ == "__main__":
    main()
