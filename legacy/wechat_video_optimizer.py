#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
微信视频号优化工具
提供视频质量分析、优化建议、格式验证、场景复杂度分析等功能
"""

import os
import json
import subprocess
import re
from datetime import datetime


class SceneComplexityAnalyzer:
    """场景复杂度分析器"""
    
    COMPLEX_KEYWORDS = [
        'detailed', 'intricate', 'busy', 'crowd', 'multiple', 'complex', 
        'texture', 'pattern', 'ornate', 'elaborate', 'rich', 'layered',
        '细节', '复杂', '繁华', '人群', '纹理', '图案'
    ]
    
    SIMPLE_KEYWORDS = [
        'minimal', 'simple', 'clean', 'solid', 'gradient', 'blur', 
        'plain', 'smooth', 'uniform', 'single', 'basic',
        '简约', '简单', '干净', '纯色', '渐变', '模糊'
    ]
    
    MOTION_KEYWORDS = [
        'action', 'movement', 'dynamic', 'fast', 'motion', 'running',
        'flying', 'falling', 'explosion', 'battle', 'chase',
        '动作', '运动', '动态', '快速', '移动'
    ]
    
    def analyze_scenes(self, scenes):
        """分析场景列表的复杂度
        
        Args:
            scenes: 场景列表，每个场景包含prompt和text字段
            
        Returns:
            dict: 包含复杂度分析和推荐的编码参数
        """
        if not scenes:
            return {'complexity': 'medium', 'recommended_crf': 23}
        
        complexity_scores = []
        motion_scores = []
        
        for scene in scenes:
            prompt = scene.get('prompt', '').lower()
            text = scene.get('text', '').lower()
            combined_text = prompt + ' ' + text
            
            complexity_score = 0
            motion_score = 0
            
            for keyword in self.COMPLEX_KEYWORDS:
                if keyword in combined_text:
                    complexity_score += 1
            
            for keyword in self.SIMPLE_KEYWORDS:
                if keyword in combined_text:
                    complexity_score -= 1
            
            for keyword in self.MOTION_KEYWORDS:
                if keyword in combined_text:
                    motion_score += 1
            
            complexity_scores.append(complexity_score)
            motion_scores.append(motion_score)
        
        avg_complexity = sum(complexity_scores) / len(scenes) if scenes else 0
        avg_motion = sum(motion_scores) / len(scenes) if scenes else 0
        
        complexity_level = self._determine_complexity_level(avg_complexity, avg_motion)
        
        return {
            'complexity': complexity_level,
            'average_complexity_score': round(avg_complexity, 2),
            'average_motion_score': round(avg_motion, 2),
            'scene_count': len(scenes),
            'high_complexity_scenes': sum(1 for s in complexity_scores if s > 1),
            'simple_scenes': sum(1 for s in complexity_scores if s < -1),
            'motion_intensive_scenes': sum(1 for s in motion_scores if s > 0),
            'recommended_crf': self._get_recommended_crf(complexity_level),
            'recommended_preset': self._get_recommended_preset(complexity_level),
            'encoding_tips': self._get_encoding_tips(complexity_level, avg_motion)
        }
    
    def _determine_complexity_level(self, complexity_score, motion_score):
        """确定复杂度级别"""
        combined_score = complexity_score + motion_score * 0.5
        
        if combined_score > 1.5:
            return 'high'
        elif combined_score < -0.5:
            return 'low'
        else:
            return 'medium'
    
    def _get_recommended_crf(self, complexity):
        """根据复杂度获取推荐的CRF值"""
        crf_map = {
            'high': 21,      # 复杂场景需要更低的CRF保持细节
            'medium': 23,    # 平衡
            'low': 25        # 简单场景可以用更高的CRF
        }
        return crf_map.get(complexity, 23)
    
    def _get_recommended_preset(self, complexity):
        """根据复杂度获取推荐的preset"""
        preset_map = {
            'high': 'slow',      # 复杂场景需要更精细的压缩
            'medium': 'medium',  # 平衡
            'low': 'fast'        # 简单场景可以快速编码
        }
        return preset_map.get(complexity, 'medium')
    
    def _get_encoding_tips(self, complexity, motion_score):
        """获取编码建议"""
        tips = []
        
        if complexity == 'high':
            tips.append("场景复杂度较高，建议使用较低的CRF值保持细节")
            tips.append("编码时间可能较长，请耐心等待")
        
        if motion_score > 0.5:
            tips.append("包含较多运动场景，建议确保帧率稳定在30fps")
            tips.append("运动场景可能需要更高的码率")
        
        if complexity == 'low':
            tips.append("场景相对简单，可以适当提高CRF值减小文件大小")
        
        if not tips:
            tips.append("场景复杂度适中，使用默认配置即可")
        
        return tips


class WeChatVideoOptimizer:
    """微信视频号优化器"""
    
    WECHAT_REQUIREMENTS = {
        'max_file_size_mb': 1000,
        'max_bitrate_kbps': 10000,
        'recommended_resolution': (1080, 1920),
        'supported_codecs': ['h264'],
        'supported_audio_codecs': ['aac'],
        'fps_range': (24, 60),
        'max_duration_sec': 3600
    }
    
    QUALITY_PRESETS = {
        'high': {
            'crf': 20,
            'preset': 'slow',
            'audio_bitrate': '192k',
            'description': '高质量 - 文件较大，画质最佳'
        },
        'balanced': {
            'crf': 23,
            'preset': 'medium',
            'audio_bitrate': '128k',
            'description': '平衡模式 - 推荐用于微信视频号'
        },
        'small': {
            'crf': 26,
            'preset': 'fast',
            'audio_bitrate': '96k',
            'description': '小文件 - 适合长视频'
        }
    }
    
    def __init__(self, ffmpeg_path='ffmpeg'):
        self.ffmpeg_path = ffmpeg_path
        self.ffprobe_path = ffmpeg_path.replace('ffmpeg', 'ffprobe')
        self.scene_analyzer = SceneComplexityAnalyzer()
    
    def analyze_video(self, video_path):
        """分析视频文件"""
        if not os.path.exists(video_path):
            return {'error': '文件不存在'}
        
        try:
            result = subprocess.run([
                self.ffprobe_path, '-v', 'quiet',
                '-print_format', 'json',
                '-show_format', '-show_streams',
                video_path
            ], capture_output=True, text=True, encoding='utf-8')
            
            if result.returncode != 0:
                return {'error': f'FFprobe执行失败: {result.stderr}'}
            
            info = json.loads(result.stdout)
            
            video_stream = next(
                (s for s in info['streams'] if s['codec_type'] == 'video'), 
                None
            )
            audio_stream = next(
                (s for s in info['streams'] if s['codec_type'] == 'audio'), 
                None
            )
            
            analysis = {
                'file_path': video_path,
                'file_size_mb': float(info['format']['size']) / (1024 * 1024),
                'duration_sec': float(info['format']['duration']),
                'overall_bitrate_kbps': int(info['format']['bit_rate']) / 1000,
                'format': info['format']['format_name'],
                'video': {},
                'audio': {},
                'issues': [],
                'recommendations': []
            }
            
            if video_stream:
                analysis['video'] = {
                    'codec': video_stream['codec_name'],
                    'width': int(video_stream['width']),
                    'height': int(video_stream['height']),
                    'fps': eval(video_stream.get('r_frame_rate', '0/1')),
                    'profile': video_stream.get('profile', 'Unknown'),
                    'level': video_stream.get('level', 'Unknown'),
                    'bitrate_kbps': int(video_stream.get('bit_rate', 0)) / 1000 if 'bit_rate' in video_stream else None
                }
            
            if audio_stream:
                analysis['audio'] = {
                    'codec': audio_stream['codec_name'],
                    'sample_rate': int(audio_stream.get('sample_rate', 0)),
                    'channels': int(audio_stream.get('channels', 0)),
                    'bitrate_kbps': int(audio_stream.get('bit_rate', 0)) / 1000 if 'bit_rate' in audio_stream else None
                }
            
            analysis['issues'] = self._check_issues(analysis)
            analysis['recommendations'] = self._generate_recommendations(analysis)
            
            return analysis
            
        except Exception as e:
            return {'error': str(e)}
    
    def _check_issues(self, analysis):
        """检查视频问题"""
        issues = []
        
        if analysis['file_size_mb'] > self.WECHAT_REQUIREMENTS['max_file_size_mb']:
            issues.append(f"文件过大 ({analysis['file_size_mb']:.1f}MB > {self.WECHAT_REQUIREMENTS['max_file_size_mb']}MB)")
        
        if analysis['overall_bitrate_kbps'] > self.WECHAT_REQUIREMENTS['max_bitrate_kbps']:
            issues.append(f"码率过高 ({analysis['overall_bitrate_kbps']:.0f}kbps > {self.WECHAT_REQUIREMENTS['max_bitrate_kbps']}kbps)")
        
        video = analysis.get('video', {})
        if video:
            width = video.get('width', 0)
            height = video.get('height', 0)
            recommended = self.WECHAT_REQUIREMENTS['recommended_resolution']
            
            if (width, height) != recommended and (height, width) != recommended:
                issues.append(f"分辨率非推荐 ({width}x{height} ≠ {recommended[0]}x{recommended[1]})")
            
            if video.get('codec') not in self.WECHAT_REQUIREMENTS['supported_codecs']:
                issues.append(f"视频编码不兼容 ({video.get('codec')})")
            
            fps = video.get('fps', 0)
            fps_range = self.WECHAT_REQUIREMENTS['fps_range']
            if not (fps_range[0] <= fps <= fps_range[1]):
                issues.append(f"帧率不在推荐范围 ({fps}fps)")
        
        audio = analysis.get('audio', {})
        if audio:
            if audio.get('codec') not in self.WECHAT_REQUIREMENTS['supported_audio_codecs']:
                issues.append(f"音频编码不兼容 ({audio.get('codec')})")
        
        return issues
    
    def _generate_recommendations(self, analysis):
        """生成优化建议"""
        recommendations = []
        
        video = analysis.get('video', {})
        
        if video.get('fps', 0) < 30:
            recommendations.append("建议提升帧率到30fps以获得更流畅的播放体验")
        
        if analysis['file_size_mb'] > 50:
            recommendations.append("建议使用CRF模式重新编码以减小文件体积")
        
        if video.get('profile') != 'High':
            recommendations.append("建议使用H.264 High Profile以获得更好的压缩效率")
        
        if analysis['overall_bitrate_kbps'] > 5000:
            recommendations.append("当前码率较高，建议降低到3-5Mbps以平衡画质和文件大小")
        
        if not recommendations:
            recommendations.append("视频配置良好，适合微信视频号发布")
        
        return recommendations
    
    def get_optimal_encoding_params(self, duration_sec, quality='balanced'):
        """获取最优编码参数"""
        preset = self.QUALITY_PRESETS.get(quality, self.QUALITY_PRESETS['balanced'])
        
        params = {
            'fps': 30,
            'codec': 'libx264',
            'preset': preset['preset'],
            'audio_codec': 'aac',
            'audio_bitrate': preset['audio_bitrate'],
            'ffmpeg_params': [
                '-crf', str(preset['crf']),
                '-profile:v', 'high',
                '-level', '4.1',
                '-pix_fmt', 'yuv420p',
                '-movflags', '+faststart',
                '-threads', '0',
            ]
        }
        
        return params
    
    def estimate_file_size(self, duration_sec, quality='balanced'):
        """估算文件大小"""
        preset = self.QUALITY_PRESETS.get(quality, self.QUALITY_PRESETS['balanced'])
        crf = preset['crf']
        
        crf_bitrate_map = {
            18: 8000,
            20: 6000,
            23: 4000,
            26: 2500,
            28: 1800
        }
        
        estimated_bitrate = crf_bitrate_map.get(crf, 4000)
        audio_bitrate = int(preset['audio_bitrate'].replace('k', ''))
        
        total_bitrate = estimated_bitrate + audio_bitrate
        file_size_mb = (total_bitrate * duration_sec) / (8 * 1024)
        
        return {
            'estimated_size_mb': round(file_size_mb, 1),
            'estimated_bitrate_kbps': total_bitrate,
            'quality_preset': quality
        }
    
    def generate_report(self, video_path, output_path=None):
        """生成优化报告"""
        analysis = self.analyze_video(video_path)
        
        if 'error' in analysis:
            return analysis
        
        report = {
            'generated_at': datetime.now().isoformat(),
            'video_analysis': analysis,
            'wechat_compatibility': {
                'is_compatible': len(analysis['issues']) == 0,
                'issues_count': len(analysis['issues']),
                'recommendations_count': len(analysis['recommendations'])
            },
            'optimization_suggestions': {
                'current_quality': self._assess_quality(analysis),
                'suggested_preset': 'balanced',
                'estimated_improvement': self._estimate_improvement(analysis)
            }
        }
        
        if output_path:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(report, f, ensure_ascii=False, indent=2)
        
        return report
    
    def _assess_quality(self, analysis):
        """评估视频质量等级"""
        video = analysis.get('video', {})
        bitrate = analysis.get('overall_bitrate_kbps', 0)
        
        if bitrate > 6000 and video.get('fps', 0) >= 30:
            return 'high'
        elif bitrate > 3000:
            return 'medium'
        else:
            return 'low'
    
    def _estimate_improvement(self, analysis):
        """估算优化改进"""
        current_size = analysis.get('file_size_mb', 0)
        
        if current_size > 100:
            return {
                'size_reduction': '30-40%',
                'quality_impact': 'minimal',
                'loading_speed': '+50%'
            }
        elif current_size > 50:
            return {
                'size_reduction': '20-30%',
                'quality_impact': 'none',
                'loading_speed': '+30%'
            }
        else:
            return {
                'size_reduction': '10-20%',
                'quality_impact': 'none',
                'loading_speed': '+20%'
            }


def main():
    """测试函数"""
    optimizer = WeChatVideoOptimizer()
    
    test_video = "./output/test.mp4"
    if os.path.exists(test_video):
        report = optimizer.generate_report(test_video)
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print("测试视频不存在，请指定一个视频文件路径")


if __name__ == "__main__":
    main()
