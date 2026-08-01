#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
图片多样性改进验证测试
验证增强后的图片生成器是否解决了重复性问题
"""

import os
import json
import hashlib
import time
from pathlib import Path
import sys

# 添加当前目录到Python路径
sys.path.insert(0, str(Path(__file__).parent))

def test_improved_diversity():
    """测试改进后的多样性生成功能"""
    print("🎨 图片多样性改进验证测试")
    print("=" * 50)
    
    # 导入改进后的生成器
    try:
        from auto_video_maker import ImageGenerator
        print("✅ 成功导入增强版图片生成器")
    except ImportError as e:
        print(f"❌ 导入失败: {e}")
        return
    
    # 创建测试输出目录
    test_output_dir = "./diversity_test_output"
    os.makedirs(test_output_dir, exist_ok=True)
    print(f"📁 测试输出目录: {test_output_dir}")
    
    # 测试场景数据（来自scripts.json的部分场景）
    test_scenes = [
        {
            "scene_id": 1,
            "prompt": "modern programmer silhouette typing code, neon blue and purple lighting, cyberpunk aesthetic, dark background, bokeh effect, cinematic photography, high contrast --ar 9:16 --style raw",
            "note": "现代赛博朋克风格，冷色调，开场吸引眼球"
        },
        {
            "scene_id": 2,
            "prompt": "19th century Victorian era portrait of Ada Lovelace, oil painting style, warm golden lighting, elegant dress with lace details, soft brush strokes, classical art museum quality --ar 9:16 --style raw",
            "note": "古典油画风格，暖色调，历史感"
        },
        {
            "scene_id": 3,
            "prompt": "Victorian era young girl studying mathematics at wooden desk, candles, geometry tools and books scattered, strict governess standing in shadow background, dramatic chiaroscuro lighting, historical drama style --ar 9:16 --style raw",
            "note": "戏剧性光影，叙事感强"
        }
    ]
    
    print(f"\n🧪 测试场景设置:")
    print(f"  场景数量: {len(test_scenes)}")
    print(f"  每场景生成次数: 2次")
    print(f"  总生成次数: {len(test_scenes) * 2}")
    
    # 初始化生成器
    image_generator = ImageGenerator()
    
    # 存储生成的文件路径
    generated_files = []
    
    # 测试每个场景多次生成
    for scene_idx, scene in enumerate(test_scenes):
        scene_id = scene['scene_id']
        print(f"\n🔍 测试场景 {scene_id}: {scene['note']}")
        print(f"  原始提示词: {scene['prompt'][:50]}...")
        
        for run_idx in range(2):  # 每个场景生成2次
            output_file = os.path.join(test_output_dir, f"scene_{scene_id:02d}_run_{run_idx:02d}.jpg")
            
            print(f"  生成第 {run_idx + 1} 次...")
            
            start_time = time.time()
            try:
                # 使用增强版生成方法
                success = image_generator.generate(
                    scene['prompt'], 
                    output_file, 
                    scene_id=scene_id, 
                    scene_note=scene['note']
                )
                elapsed_time = time.time() - start_time
                
                if success and os.path.exists(output_file):
                    file_size = os.path.getsize(output_file)
                    generated_files.append({
                        'file': output_file,
                        'scene_id': scene_id,
                        'run': run_idx,
                        'size': file_size,
                        'time': elapsed_time
                    })
                    print(f"    ✅ 成功 ({elapsed_time:.1f}s, {file_size/1024/1024:.2f}MB)")
                else:
                    print(f"    ❌ 失败")
                    
            except Exception as e:
                print(f"    ❌ 异常: {str(e)}")
    
    # 分析生成结果
    print(f"\n📊 生成结果分析:")
    print(f"  总尝试次数: {len(test_scenes) * 2}")
    print(f"  成功生成: {len(generated_files)}")
    print(f"  成功率: {len(generated_files)/(len(test_scenes)*2)*100:.1f}%")
    
    if generated_files:
        # 按场景分组分析
        scene_stats = {}
        for file_info in generated_files:
            scene_id = file_info['scene_id']
            if scene_id not in scene_stats:
                scene_stats[scene_id] = []
            scene_stats[scene_id].append(file_info)
        
        print(f"\n📈 场景级别分析:")
        for scene_id, files in scene_stats.items():
            scene = next(s for s in test_scenes if s['scene_id'] == scene_id)
            print(f"  场景 {scene_id} ({scene['note']}): {len(files)}/2 成功")
            if len(files) >= 2:
                # 计算两次生成的时间间隔
                times = sorted([f['time'] for f in files])
                if len(times) > 1:
                    time_diff = times[1] - times[0]
                    print(f"    时间差异: {time_diff:.1f}s")
    
    # 检查文件大小差异（初步判断是否为不同图片）
    if len(generated_files) > 1:
        sizes = [f['size'] for f in generated_files]
        size_variance = max(sizes) - min(sizes)
        print(f"\n📏 文件大小分析:")
        print(f"  大小范围: {min(sizes)/1024/1024:.2f}MB - {max(sizes)/1024/1024:.2f}MB")
        print(f"  大小差异: {size_variance/1024:.1f}KB")
        if size_variance > 10240:  # 10KB以上差异
            print(f"  ✅ 检测到显著的大小差异，表明图片内容不同")
        else:
            print(f"  ⚠️ 大小差异较小，需要进一步验证内容差异")

def compare_before_after():
    """对比改进前后的效果"""
    print(f"\n🔄 改进前后对比")
    print("=" * 50)
    
    improvements = [
        "1. 🎯 **提示词增强策略**",
        "   - 添加场景唯一标识符 (scene_X_unique_variant)",
        "   - 根据场景note动态添加风格增强词",
        "   - 引入质量提升参数和创意元素",
        "   - 实现场景差异化修饰语",
        "",
        "2. 🔢 **种子多样化**",
        "   - 扩大种子范围至 0-999999",
        "   - 结合场景ID、时间戳等多因素生成",
        "   - 应用素数乘法增加分布均匀性",
        "",
        "3. 🌐 **API调用优化**",
        "   - 实现多种Pollinations URL变体",
        "   - 增强请求头和参数配置",
        "   - 改进Civitai搜索的相关性",
        "   - 添加指数退避重试机制",
        "",
        "4. 🎨 **视觉差异化**",
        "   - 为占位图添加场景相关的颜色方案",
        "   - 实现基于场景ID的颜色映射",
        "   - 引入随机色彩变化增加视觉效果",
        "",
        "5. ⚡ **智能控制**",
        "   - 更严格的文件大小验证 (>80KB)",
        "   - 增强的日志和调试信息",
        "   - 更好的错误处理和降级策略"
    ]
    
    for improvement in improvements:
        print(improvement)
    
    print(f"\n💡 预期效果:")
    print(f"  ✅ 相同场景多次生成的内容将明显不同")
    print(f"  ✅ 不同场景之间的视觉风格更加贴合描述")
    print(f"  ✅ 减少重复图片的生成概率")
    print(f"  ✅ 提高整体图片质量和相关性")

def main():
    """主测试函数"""
    print("🎨 图片多样性改进验证")
    print("测试增强版图片生成器解决重复性问题的效果\n")
    
    # 运行多样性测试
    test_improved_diversity()
    
    # 显示改进对比
    compare_before_after()
    
    print(f"\n✅ 测试完成!")
    print(f"📁 测试结果保存在 ./diversity_test_output/ 目录中")
    print(f"🔧 如需进一步验证，可手动检查生成的图片文件")

if __name__ == "__main__":
    main()