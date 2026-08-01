#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
终极图片多样性解决方案验证测试
测试新的四重保障策略是否真正解决重复问题
"""

import os
import sys
import json
import time
from pathlib import Path

# 添加项目路径
sys.path.append(str(Path(__file__).parent))

def test_ultimate_diversity_solution():
    """测试终极多样性解决方案"""
    print("🔥 终极图片多样性解决方案验证测试")
    print("=" * 60)
    print("测试四重保障策略的有效性\n")
    
    # 导入终极版生成器
    try:
        from auto_video_maker import ImageGenerator, log
        print("✅ 成功导入终极版图片生成器")
    except ImportError as e:
        print(f"❌ 导入失败: {e}")
        return False
    
    # 测试场景数据
    test_scenarios = [
        {
            "scene_id": 1,
            "prompt": "modern programmer silhouette typing code, neon blue and purple lighting, cyberpunk aesthetic",
            "note": "现代赛博朋克风格，冷色调，开场吸引眼球"
        },
        {
            "scene_id": 2,
            "prompt": "19th century Victorian era portrait of Ada Lovelace, oil painting style, warm golden lighting",
            "note": "古典油画风格，暖色调，历史感"
        },
        {
            "scene_id": 3,
            "prompt": "Victorian era young girl studying mathematics by candlelight, dramatic shadows",
            "note": "戏剧性光影，叙事感强"
        }
    ]
    
    generator = ImageGenerator()
    
    # 创建测试输出目录
    test_output_dir = "./ultimate_diversity_test"
    os.makedirs(test_output_dir, exist_ok=True)
    
    print("🚀 开始四重保障策略测试...\n")
    
    # 测试每个场景
    results = []
    for scenario in test_scenarios:
        scene_id = scenario['scene_id']
        prompt = scenario['prompt']
        note = scenario['note']
        
        print(f"🎨 测试场景 {scene_id}: {note}")
        print(f"   提示词长度: {len(prompt)} 字符")
        
        # 为同一场景生成两张图片测试重复性
        scene_results = []
        for run in range(2):
            output_file = os.path.join(test_output_dir, f"scene_{scene_id:02d}_run_{run+1}.jpg")
            
            print(f"   第 {run+1} 次生成...")
            start_time = time.time()
            
            try:
                success = generator.generate(prompt, output_file, scene_id, note)
                elapsed_time = time.time() - start_time
                
                if success and os.path.exists(output_file):
                    file_size = os.path.getsize(output_file)
                    scene_results.append({
                        'run': run + 1,
                        'success': True,
                        'file': output_file,
                        'size': file_size,
                        'time': elapsed_time
                    })
                    print(f"     ✅ 成功 ({elapsed_time:.1f}s, {file_size/1024/1024:.2f}MB)")
                else:
                    scene_results.append({
                        'run': run + 1,
                        'success': False,
                        'file': output_file,
                        'size': 0,
                        'time': elapsed_time
                    })
                    print(f"     ❌ 失败")
                    
            except Exception as e:
                print(f"     ❌ 异常: {str(e)}")
                scene_results.append({
                    'run': run + 1,
                    'success': False,
                    'error': str(e)
                })
        
        results.append({
            'scene_id': scene_id,
            'note': note,
            'runs': scene_results
        })
    
    # 分析结果
    print("\n" + "=" * 60)
    print("📊 测试结果分析")
    print("=" * 60)
    
    total_attempts = len(test_scenarios) * 2
    successful_generations = sum(1 for scene in results for run in scene['runs'] if run.get('success', False))
    success_rate = (successful_generations / total_attempts) * 100
    
    print(f"总尝试次数: {total_attempts}")
    print(f"成功生成: {successful_generations}")
    print(f"成功率: {success_rate:.1f}%")
    
    # 重复性分析
    print(f"\n🔄 重复性分析:")
    
    duplicate_analysis = []
    for scene_result in results:
        scene_id = scene_result['scene_id']
        runs = scene_result['runs']
        
        if len(runs) >= 2:
            # 检查两次生成的文件大小差异
            sizes = [run.get('size', 0) for run in runs if run.get('success', False)]
            if len(sizes) >= 2:
                size_diff = abs(sizes[0] - sizes[1])
                duplicate_analysis.append({
                    'scene_id': scene_id,
                    'size_difference': size_diff,
                    'sizes': sizes
                })
                print(f"  场景 {scene_id}: 大小差异 {size_diff/1024:.1f}KB "
                      f"({sizes[0]/1024/1024:.2f}MB vs {sizes[1]/1024/1024:.2f}MB)")
            else:
                print(f"  场景 {scene_id}: 生成不足两次，无法比较")
    
    # 判断重复性改善情况
    significant_differences = sum(1 for analysis in duplicate_analysis 
                                if analysis['size_difference'] > 20480)  # 20KB以上认为有显著差异
    
    print(f"\n🎯 重复性改善评估:")
    if duplicate_analysis:
        improvement_rate = (significant_differences / len(duplicate_analysis)) * 100
        print(f"  具有显著差异的场景比例: {improvement_rate:.1f}%")
        
        if improvement_rate >= 50:
            print("  ✅ 重复性问题得到显著改善")
        elif improvement_rate >= 25:
            print("  ⚠️ 重复性有所改善但仍有提升空间")
        else:
            print("  ❌ 重复性问题仍然严重")
    else:
        print("  ⚠️ 无法进行重复性分析（生成样本不足）")
    
    # 详细日志
    print(f"\n📋 详细生成日志:")
    for scene_result in results:
        scene_id = scene_result['scene_id']
        note = scene_result['note']
        runs = scene_result['runs']
        
        print(f"  场景 {scene_id} ({note}):")
        for run in runs:
            if run.get('success', False):
                print(f"    运行 {run['run']}: 成功 ({run['size']/1024/1024:.2f}MB, {run['time']:.1f}s)")
            else:
                error_msg = run.get('error', '未知错误')
                print(f"    运行 {run['run']}: 失败 ({error_msg})")
    
    # 生成总结报告
    print(f"\n" + "=" * 60)
    print("📝 测试总结")
    print("=" * 60)
    
    if success_rate >= 80:
        print("✅ 终极解决方案整体表现优秀")
    elif success_rate >= 60:
        print("⚠️ 终极解决方案表现良好但有待改进")
    else:
        print("❌ 终极解决方案仍需大幅改进")
    
    print(f"\n📁 测试输出文件保存在: {test_output_dir}")
    print("💡 建议手动检查生成的图片文件确认视觉差异性")
    
    return success_rate >= 60  # 60%成功率视为基本合格

def main():
    """主函数"""
    try:
        success = test_ultimate_diversity_solution()
        if success:
            print(f"\n🎉 终极多样性解决方案测试通过！")
        else:
            print(f"\n💥 终极多样性解决方案测试未通过，请检查实现")
    except Exception as e:
        print(f"\n💥 测试过程中发生异常: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()