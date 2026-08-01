#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
最小化视频合成修复工具
直接使用FFmpeg命令行工具进行视频合成
"""

import os
import subprocess
import json
from pathlib import Path
import sys

def get_ffmpeg_path():
    """获取FFmpeg路径"""
    # 常见的FFmpeg位置
    possible_paths = [
        "ffmpeg",  # 系统PATH中
        "./ffmpeg/bin/ffmpeg.exe",  # 本地ffmpeg目录
        "C:/ffmpeg/bin/ffmpeg.exe",  # 标准安装位置
    ]
    
    for path in possible_paths:
        try:
            result = subprocess.run([path, "-version"], 
                                  capture_output=True, 
                                  text=True, 
                                  timeout=5)
            if result.returncode == 0:
                return path
        except:
            continue
    
    return None

def create_video_with_ffmpeg(audio_file, image_files, output_file, durations=None):
    """使用FFmpeg创建视频"""
    
    print("🎬 使用FFmpeg创建视频...")
    
    # 检查FFmpeg
    ffmpeg_path = get_ffmpeg_path()
    if not ffmpeg_path:
        print("❌ 未找到FFmpeg，请先安装FFmpeg")
        return False
    
    print(f"✅ 找到FFmpeg: {ffmpeg_path}")
    
    # 标准化路径
    audio_path = os.path.abspath(audio_file)
    output_path = os.path.abspath(output_file)
    
    # 检查输入文件
    if not os.path.exists(audio_path):
        print(f"❌ 音频文件不存在: {audio_path}")
        return False
    
    valid_images = []
    for img in image_files:
        img_path = os.path.abspath(img)
        if os.path.exists(img_path):
            valid_images.append(img_path)
        else:
            print(f"⚠️  图片不存在，跳过: {img_path}")
    
    if not valid_images:
        print("❌ 没有有效的图片文件")
        return False
    
    print(f"✅ 找到 {len(valid_images)} 个有效图片")
    
    # 如果没有提供持续时间，平均分配
    if not durations or len(durations) != len(valid_images):
        # 获取音频时长
        try:
            probe_cmd = [ffmpeg_path, "-i", audio_path, "-show_entries", "format=duration", "-v quiet", "-of", "csv=p=0"]
            result = subprocess.run(probe_cmd, capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                audio_duration = float(result.stdout.strip())
                avg_duration = audio_duration / len(valid_images)
                durations = [avg_duration] * len(valid_images)
                print(f"✅ 音频时长: {audio_duration:.2f}秒，平均每张图片: {avg_duration:.2f}秒")
            else:
                durations = [5.0] * len(valid_images)  # 默认5秒
        except Exception as e:
            print(f"⚠️  无法获取音频时长: {e}")
            durations = [5.0] * len(valid_images)
    
    # 创建临时文件列表
    temp_list_file = "./output/temp_file_list.txt"
    with open(temp_list_file, 'w', encoding='utf-8') as f:
        for img_path, duration in zip(valid_images, durations):
            # FFmpeg需要双引号包围路径中的空格
            escaped_path = img_path.replace('\\', '/').replace(':', '\\:').replace('[', '\\[').replace(']', '\\]')
            f.write(f"file '{escaped_path}'\nduration {duration:.3f}\n")
        # 添加最后一个文件（FFmpeg要求）
        f.write(f"file '{valid_images[-1].replace('\\', '/').replace(':', '\\:').replace('[', '\\[').replace(']', '\\]')}'\n")
    
    try:
        # 第一步：创建无声视频
        print("🔧 创建无声视频...")
        silent_video = "./output/temp_silent.mp4"
        
        cmd1 = [
            ffmpeg_path,
            "-f", "concat",
            "-safe", "0",
            "-i", temp_list_file,
            "-vf", "scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2:white",
            "-r", "1",  # 降低帧率减少文件大小
            "-pix_fmt", "yuv420p",
            "-y",  # 覆盖输出文件
            silent_video
        ]
        
        print("执行命令:", " ".join(cmd1))
        result1 = subprocess.run(cmd1, capture_output=True, text=True, timeout=300)
        
        if result1.returncode != 0:
            print(f"❌ 无声视频创建失败: {result1.stderr}")
            return False
        
        print("✅ 无声视频创建成功")
        
        # 第二步：合并音频
        print("🔊 合并音频...")
        
        cmd2 = [
            ffmpeg_path,
            "-i", silent_video,
            "-i", audio_path,
            "-c:v", "copy",
            "-c:a", "aac",
            "-strict", "experimental",
            "-y",  # 覆盖输出文件
            output_path
        ]
        
        print("执行命令:", " ".join(cmd2))
        result2 = subprocess.run(cmd2, capture_output=True, text=True, timeout=300)
        
        if result2.returncode != 0:
            print(f"❌ 音频合并失败: {result2.stderr}")
            return False
        
        print("✅ 音频合并成功")
        
        # 清理临时文件
        try:
            os.remove(temp_list_file)
            os.remove(silent_video)
        except:
            pass
        
        if os.path.exists(output_path):
            file_size = os.path.getsize(output_path)
            print(f"🎉 视频合成完成: {output_path} ({file_size:,} bytes)")
            return True
        else:
            print("❌ 视频文件未生成")
            return False
            
    except subprocess.TimeoutExpired:
        print("❌ FFmpeg执行超时")
        return False
    except Exception as e:
        print(f"❌ 视频合成出错: {e}")
        return False

def fix_existing_project():
    """修复现有的项目文件"""
    
    print("🔧 修复现有项目...")
    
    # 检查output目录
    output_dir = "./output"
    if not os.path.exists(output_dir):
        print("❌ output目录不存在")
        return False
    
    # 查找音频文件
    audio_candidates = [
        os.path.join(output_dir, "complete_voiceover.mp3"),  # 优先使用完整音频
        os.path.join(output_dir, "voiceover.mp3"),
        os.path.join(output_dir, "segment_000.mp3"),  # 如果voiceover不存在，使用第一个片段
    ]
    
    audio_file = None
    for candidate in audio_candidates:
        if os.path.exists(candidate):
            audio_file = candidate
            break
    
    if not audio_file:
        print("❌ 未找到音频文件")
        return False
    
    print(f"✅ 找到音频文件: {audio_file}")
    
    # 查找图片文件
    image_files = []
    for i in range(20):  # 假设最多20个场景
        img_path = os.path.join(output_dir, f"scene_{i:03d}.jpg")
        if os.path.exists(img_path):
            image_files.append(img_path)
    
    if not image_files:
        print("❌ 未找到图片文件")
        return False
    
    print(f"✅ 找到 {len(image_files)} 个图片文件")
    
    # 生成输出文件名
    project_name = "修复版视频"
    # 尝试从脚本文件获取项目名
    script_file = "./scripts.json"
    if os.path.exists(script_file):
        try:
            with open(script_file, 'r', encoding='utf-8') as f:
                script_data = json.load(f)
                project_name = script_data.get('project_name', project_name)
        except:
            pass
    
    output_file = os.path.join(output_dir, f"{project_name}_修复版.mp4")
    
    # 执行合成
    return create_video_with_ffmpeg(audio_file, image_files, output_file)

if __name__ == "__main__":
    print("🚀 最小化视频合成修复工具")
    print("=" * 50)
    
    success = fix_existing_project()
    
    print("\n" + "=" * 50)
    if success:
        print("🎉 视频修复成功！")
        print("💡 建议:")
        print("1. 检查生成的视频文件质量")
        print("2. 如需更好效果，可安装完整MoviePy环境")
        print("3. 确保FFmpeg已正确安装")
    else:
        print("❌ 视频修复失败")
        print("💡 建议:")
        print("1. 确认FFmpeg已安装并加入系统PATH")
        print("2. 检查output目录中的文件是否完整")
        print("3. 手动重新运行音频和图片生成步骤")