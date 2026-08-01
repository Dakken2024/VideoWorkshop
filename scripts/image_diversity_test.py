#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
图片多样性测试和对比分析
验证改进后的图片生成器是否解决了重复性问题
"""

import os
import json
import hashlib
import time
from pathlib import Path
from PIL import Image
import numpy as np

def load_test_scenes():
    """加载测试场景数据"""
    script_file = Path("scripts.json")
    if not script_file.exists():
        print("❌ 未找到 scripts.json 文件")
        return []
    
    with open(script_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    return data.get('scenes', [])

def calculate_image_hash(image_path):
    """计算图片哈希值用于去重检测"""
    try:
        with Image.open(image_path) as img:
            # 转换为统一格式
            img = img.convert('RGB')
            # 缩放到固定尺寸进行比较
            img_small = img.resize((32, 32))
            # 转换为numpy数组
            arr = np.array(img_small)
            # 计算平均哈希
            avg = arr.mean()
            # 生成二进制哈希
            hash_bits = (arr > avg).flatten()
            # 转换为十六进制字符串
            hash_hex = ''.join(['1' if bit else '0' for bit in hash_bits])
            return hashlib.md5(hash_hex.encode()).hexdigest()
    except Exception as e:
        print(f"计算图片哈希失败 {image_path}: {e}")
        return None

def analyze_image_diversity(image_files):
    """分析图片多样性"""
    print("\n📊 图片多样性分析")
    print("=" * 40)
    
    if not image_files:
        print("❌ 没有图片文件可供分析")
        return
    
    hashes = []
    file_sizes = []
    dimensions = []
    
    for img_path in image_files:
        if not os.path.exists(img_path):
            continue
            
        # 计算哈希
        img_hash = calculate_image_hash(img_path)
        if img_hash:
            hashes.append((img_path, img_hash))
        
        # 获取文件大小
        size = os.path.getsize(img_path)
        file_sizes.append((img_path, size))
        
        # 获取图片尺寸
        try:
            with Image.open(img_path) as img:
                dimensions.append((img_path, img.size))
        except Exception as e:
            print(f"读取图片尺寸失败 {img_path}: {e}")
    
    # 分析重复性
    hash_values = [h[1] for h in hashes]
    unique_hashes = set(hash_values)
    
    print(f"📊 统计信息:")
    print(f"  总图片数: {len(image_files)}")
    print(f"  唯一哈希数: {len(unique_hashes)}")
    print(f"  重复率: {(1 - len(unique_hashes)/len(hash_values))*100:.1f}%" if hash_values else "N/A")
    
    # 显示重复的图片
    if len(unique_hashes) < len(hash_values):
        print(f"\n🔍 重复图片检测:")
        hash_count = {}
        for path, hash_val in hashes:
            hash_count[hash_val] = hash_count.get(hash_val, []) + [path]
        
        for hash_val, paths in hash_count.items():
            if len(paths) > 1:
                print(f"  重复组 ({len(paths)}张相同):")
                for path in paths[:3]:  # 只显示前3个
                    print(f"    - {Path(path).name}")
                if len(paths) > 3:
                    print(f"    ... 还有 {len(paths)-3} 张")
    
    # 文件大小分析
    if file_sizes:
        sizes = [size for _, size in file_sizes]
        print(f"\n📁 文件大小分析:")
        print(f"  平均大小: {np.mean(sizes)/1024/1024:.2f} MB")
        print(f"  最小大小: {min(sizes)/1024/1024:.2f} MB")
        print(f"  最大大小: {max(sizes)/1024/1024:.2f} MB")
        print(f"  大小标准差: {np.std(sizes)/1024/1024:.2f} MB")
    
    # 尺寸分析
    if dimensions:
        widths = [dim[1][0] for dim in dimensions]
        heights = [dim[1][1] for dim in dimensions]
        print(f"\n📐 尺寸分析:")
        print(f"  平均宽度: {np.mean(widths):.0f}px")
        print(f"  平均高度: {np.mean(heights):.0f}px")
        print(f"  宽高比一致性: {'是' if len(set(widths)) == 1 and len(set(heights)) == 1 else '否'}")

def compare_generation_methods():
    """对比不同生成方法的效果"""
    print("\n🔄 生成方法对比测试")
    print("=" * 40)
    
    scenes = load_test_scenes()
    if not scenes:
        return
    
    # 只测试前3个场景以节省时间
    test_scenes = scenes[:3]
    
    print("🧪 对比测试设置:")
    print(f"  测试场景数: {len(test_scenes)}")
    print(f"  每场景生成次数: 2次")
    print(f"  总生成次数: {len(test_scenes) * 2}")
    
    # 导入生成器
    try:
        from auto_video_maker import ImageGenerator
        from enhanced_image_generator import EnhancedImageGenerator
    except ImportError as e:
        print(f"❌ 导入生成器失败: {e}")
        return
    
    # 创建输出目录
    test_dirs = {
        'original': './test_output/original',
        'enhanced': './test_output/enhanced'
    }
    
    for dir_path in test_dirs.values():
        os.makedirs(dir_path, exist_ok=True)
    
    # 测试原始生成器
    print(f"\n🔍 测试原始生成器:")
    original_files = []
    original_generator = ImageGenerator()
    
    for i, scene in enumerate(test_scenes):
        for j in range(2):  # 每个场景生成2次
            output_file = os.path.join(test_dirs['original'], f"scene_{i:02d}_run_{j:02d}.jpg")
            prompt = scene['prompt']
            
            start_time = time.time()
            success = original_generator.generate(prompt, output_file)
            elapsed = time.time() - start_time
            
            if success and os.path.exists(output_file):
                original_files.append(output_file)
                print(f"  场景{i+1}-{j+1}: 成功 ({elapsed:.1f}s)")
            else:
                print(f"  场景{i+1}-{j+1}: 失败")
    
    # 测试增强生成器
    print(f"\n🎨 测试增强生成器:")
    enhanced_files = []
    enhanced_generator = EnhancedImageGenerator()
    
    for i, scene in enumerate(test_scenes):
        for j in range(2):  # 每个场景生成2次
            output_file = os.path.join(test_dirs['enhanced'], f"scene_{i:02d}_run_{j:02d}.jpg")
            
            start_time = time.time()
            success = enhanced_generator.generate_diverse_image(scene, output_file, i*2+j)
            elapsed = time.time() - start_time
            
            if success and os.path.exists(output_file):
                enhanced_files.append(output_file)
                print(f"  场景{i+1}-{j+1}: 成功 ({elapsed:.1f}s)")
            else:
                print(f"  场景{i+1}-{j+1}: 失败")
    
    # 分析结果
    print(f"\n📈 对比分析结果:")
    print(f"  原始方法成功: {len(original_files)}/{len(test_scenes)*2}")
    print(f"  增强方法成功: {len(enhanced_files)}/{len(test_scenes)*2}")
    
    if original_files:
        print(f"\n🔍 原始方法多样性分析:")
        analyze_image_diversity(original_files)
    
    if enhanced_files:
        print(f"\n🎨 增强方法多样性分析:")
        analyze_image_diversity(enhanced_files)

def generate_recommendation_report():
    """生成改进建议报告"""
    print("\n📋 图片多样性优化建议")
    print("=" * 50)
    
    recommendations = [
        "1. 🎯 **提示词增强策略**",
        "   - 为每个场景添加唯一标识符",
        "   - 根据场景note动态添加风格增强词",
        "   - 引入质量提升参数和创意元素",
        "",
        "2. 🔢 **种子多样化**",
        "   - 使用更大范围的随机种子 (0-999999)",
        "   - 结合场景ID、索引等多个因素生成种子",
        "   - 应用素数乘法增加分布均匀性",
        "",
        "3. 🌐 **多源API策略**",
        "   - 实现Pollinations.ai的多种URL变体",
        "   - 增强Civitai搜索的上下文相关性",
        "   - 添加备用图片源提高成功率",
        "",
        "4. 🎨 **视觉差异化**",
        "   - 为占位图添加场景相关的颜色方案",
        "   - 实现基于场景内容的颜色映射",
        "   - 引入渐变和纹理增强视觉效果",
        "",
        "5. ⚡ **智能频率控制**",
        "   - 实施指数退避算法",
        "   - 添加请求间随机延迟",
        "   - 监控API响应状态优化调用策略"
    ]
    
    for rec in recommendations:
        print(rec)

def main():
    """主测试函数"""
    print("🎨 图片多样性测试和分析")
    print("验证改进方案对图片重复性问题的解决效果\n")
    
    # 运行对比测试
    compare_generation_methods()
    
    # 生成建议报告
    generate_recommendation_report()
    
    print(f"\n✅ 测试完成!")
    print(f"📁 测试结果保存在 ./test_output/ 目录中")

if __name__ == "__main__":
    main()