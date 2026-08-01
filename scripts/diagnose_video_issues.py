#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
视频合成问题诊断和修复工具
"""

import os
import sys
import platform
from pathlib import Path

def diagnose_path_issues():
    """诊断路径相关问题"""
    
    print("🔍 路径问题诊断")
    print("=" * 40)
    
    # 检查当前工作目录
    cwd = os.getcwd()
    print(f"当前工作目录: {cwd}")
    
    # 检查输出目录
    output_dir = "./output"
    abs_output_dir = os.path.abspath(output_dir)
    print(f"输出目录路径: {abs_output_dir}")
    print(f"输出目录存在: {os.path.exists(abs_output_dir)}")
    
    # 检查音频文件
    voiceover_path = os.path.join(output_dir, "voiceover.mp3")
    abs_voiceover_path = os.path.abspath(voiceover_path)
    print(f"音频文件路径: {abs_voiceover_path}")
    print(f"音频文件存在: {os.path.exists(abs_voiceover_path)}")
    
    # 检查路径分隔符
    print(f"系统路径分隔符: {os.sep}")
    print(f"系统路径分隔符列表: {os.pathsep}")
    
    # 测试路径标准化
    test_paths = [
        "./output/voiceover.mp3",
        ".\\output\\voiceover.mp3", 
        os.path.join(".", "output", "voiceover.mp3"),
        str(Path("./output/voiceover.mp3"))
    ]
    
    print("\n路径标准化测试:")
    for path in test_paths:
        normalized = os.path.normpath(path)
        absolute = os.path.abspath(normalized)
        print(f"  原始: {path}")
        print(f"  标准化: {normalized}")
        print(f"  绝对路径: {absolute}")
        print()

def check_moviepy_compatibility():
    """检查MoviePy兼容性问题"""
    
    print("🎬 MoviePy兼容性检查")
    print("=" * 40)
    
    try:
        import moviepy
        print(f"MoviePy版本: {moviepy.__version__}")
        
        # 检查关键模块
        from moviepy.editor import AudioFileClip, ImageClip, concatenate_videoclips, CompositeVideoClip, TextClip
        from moviepy.video.tools.drawing import ColorClip
        print("✅ 关键模块导入成功")
        
        # 检查FFmpeg
        try:
            from moviepy.config import check_for_codec
            ffmpeg_available = check_for_codec('libx264')
            print(f"FFmpeg可用性: {ffmpeg_available}")
        except Exception as e:
            print(f"FFmpeg检查失败: {e}")
            
    except ImportError as e:
        print(f"❌ MoviePy导入失败: {e}")
        return False
    except Exception as e:
        print(f"❌ MoviePy兼容性问题: {e}")
        return False
    
    return True

def test_path_normalization():
    """测试路径标准化功能"""
    
    print("🔧 路径标准化测试")
    print("=" * 40)
    
    # 创建测试函数
    def normalize_output_path(base_dir, filename):
        """标准化输出路径"""
        # 使用pathlib处理路径
        path_obj = Path(base_dir) / filename
        normalized_path = str(path_obj.resolve())
        return normalized_path
    
    def safe_join_path(*parts):
        """安全的路径拼接"""
        # 统一使用正斜杠，然后标准化
        combined = '/'.join(str(part).replace('\\', '/') for part in parts)
        return os.path.normpath(combined)
    
    # 测试用例
    test_cases = [
        ("./output", "voiceover.mp3"),
        (".\\output", "voiceover.mp3"),
        ("output", "voiceover.mp3"),
        ("./output/", "voiceover.mp3")
    ]
    
    print("路径处理测试:")
    for base_dir, filename in test_cases:
        result1 = normalize_output_path(base_dir, filename)
        result2 = safe_join_path(base_dir, filename)
        print(f"  输入: {base_dir} + {filename}")
        print(f"  Path方法: {result1}")
        print(f"  安全拼接: {result2}")
        print(f"  文件存在: {os.path.exists(result1)}")
        print()

def create_fixed_video_compositor():
    """创建修复版视频合成器"""
    
    print("🔧 创建修复版视频合成器")
    print("=" * 40)
    
    fixed_code = '''
import os
from pathlib import Path
from moviepy.editor import *

class FixedVideoCompositor:
    """修复版视频合成器 - 解决路径和兼容性问题"""
    
    def __init__(self, output_dir="./output"):
        self.output_dir = Path(output_dir).resolve()
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def normalize_path(self, path):
        """标准化路径处理"""
        if isinstance(path, str):
            # 统一路径分隔符并标准化
            normalized = path.replace('\\\\', '/').replace('\\'', '/')
            return str(Path(normalized).resolve())
        return str(Path(path).resolve())
    
    def check_file_exists(self, filepath):
        """安全检查文件存在性"""
        try:
            normalized_path = self.normalize_path(filepath)
            return os.path.exists(normalized_path) and os.path.isfile(normalized_path)
        except Exception as e:
            print(f"文件检查错误: {e}")
            return False
    
    def create(self, audio_file, image_files, scene_durations, output_file):
        """修复版视频合成"""
        print("🎬 开始修复版视频合成...")
        
        # 标准化所有路径
        audio_path = self.normalize_path(audio_file)
        output_path = self.normalize_path(output_file)
        
        print(f"音频文件: {audio_path}")
        print(f"输出文件: {output_path}")
        
        # 检查音频文件
        if not self.check_file_exists(audio_path):
            print(f"❌ 音频文件不存在: {audio_path}")
            return False
        
        try:
            # 安全加载音频
            print("🔊 加载音频文件...")
            audio = AudioFileClip(audio_path)
            total_audio_duration = audio.duration
            print(f"音频时长: {total_audio_duration:.2f}秒")
            
        except Exception as e:
            print(f"❌ 音频加载失败: {e}")
            return False
        
        try:
            # 处理图片文件
            print("🖼️  处理图片文件...")
            valid_clips = []
            total_scene_duration = sum(scene_durations)
            
            for i, (img_path, base_duration) in enumerate(zip(image_files, scene_durations)):
                if not img_path:
                    print(f"⚠️  跳过空图片路径 - 场景 {i+1}")
                    continue
                    
                img_normalized = self.normalize_path(img_path)
                
                if not self.check_file_exists(img_normalized):
                    print(f"⚠️  图片文件不存在: {img_normalized}")
                    continue
                
                try:
                    # 计算实际时长
                    actual_duration = (base_duration / total_scene_duration) * total_audio_duration
                    
                    # 创建图片剪辑
                    clip = ImageClip(img_normalized).with_duration(actual_duration)
                    valid_clips.append(clip)
                    print(f"✅ 场景 {i+1}: {img_normalized} ({actual_duration:.2f}秒)")
                    
                except Exception as e:
                    print(f"❌ 场景 {i+1} 处理失败: {e}")
                    continue
            
            if not valid_clips:
                print("❌ 没有有效的视频片段")
                audio.close()
                return False
            
            # 拼接视频
            print("🔗 拼接视频片段...")
            try:
                final_video = concatenate_videoclips(valid_clips, method="compose")
            except Exception as e:
                print(f"❌ 视频拼接失败: {e}")
                # 清理资源
                for clip in valid_clips:
                    clip.close()
                audio.close()
                return False
            
            # 添加音频
            print("🔊 添加音频轨道...")
            final_video = final_video.with_audio(audio)
            
            # 导出视频
            print("💾 导出最终视频...")
            final_video.write_videofile(
                output_path,
                fps=24,
                codec='libx264',
                audio_codec='aac',
                temp_audiofile=None,  # 避免临时音频文件问题
                remove_temp=True,
                verbose=False,
                logger=None
            )
            
            # 清理资源
            print("🧹 清理资源...")
            audio.close()
            for clip in valid_clips:
                clip.close()
            final_video.close()
            
            if self.check_file_exists(output_path):
                file_size = os.path.getsize(output_path)
                print(f"✅ 视频合成成功: {output_path} ({file_size:,} bytes)")
                return True
            else:
                print("❌ 视频文件未生成")
                return False
                
        except Exception as e:
            print(f"❌ 视频合成过程出错: {e}")
            import traceback
            traceback.print_exc()
            return False
'''
    
    print("修复版视频合成器代码:")
    print(fixed_code)
    return fixed_code

def generate_immediate_fix():
    """生成立即可用的修复方案"""
    
    print("⚡ 立即修复方案")
    print("=" * 40)
    
    immediate_actions = [
        "1. 统一使用Path对象处理所有路径",
        "2. 在加载文件前先检查文件存在性",
        "3. 使用temp_audiofile=None避免临时文件问题", 
        "4. 添加详细的错误处理和日志",
        "5. 标准化路径分隔符处理"
    ]
    
    print("推荐立即采取的措施:")
    for action in immediate_actions:
        print(f"   {action}")
    
    print("\n临时解决方案:")
    print("   - 手动检查output目录中的voiceover.mp3是否存在")
    print("   - 确保所有图片文件路径正确")
    print("   - 重新运行音频生成步骤")

if __name__ == "__main__":
    print("🚀 视频合成问题诊断工具")
    print("=" * 50)
    print(f"运行环境: {platform.system()} {platform.release()}")
    print(f"Python版本: {sys.version}")
    print()
    
    # 诊断路径问题
    diagnose_path_issues()
    
    # 检查兼容性
    moviepy_ok = check_moviepy_compatibility()
    
    # 测试路径处理
    test_path_normalization()
    
    # 生成修复代码
    create_fixed_video_compositor()
    
    # 提供立即修复建议
    generate_immediate_fix()
    
    print("\n" + "=" * 50)
    print("💡 建议:")
    if not moviepy_ok:
        print("1. 更新MoviePy到最新版本: pip install --upgrade moviepy")
    print("2. 使用提供的修复版视频合成器替换原有代码")
    print("3. 确保FFmpeg正确安装并可在系统路径中找到")