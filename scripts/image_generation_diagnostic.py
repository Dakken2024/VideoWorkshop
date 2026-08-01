#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
图片生成问题诊断和修复工具
分析多线程请求过快导致的API限制问题
"""

import asyncio
import time
import threading
from concurrent.futures import ThreadPoolExecutor
import requests
import json
from typing import List, Dict, Optional
import traceback

class ImageGenerationDiagnostic:
    """图片生成诊断工具"""
    
    def __init__(self):
        self.api_endpoints = [
            "https://image.pollinations.ai/prompt/",
            "https://civitai.com/api/v1/images"
        ]
        self.request_delays = {
            'conservative': 2.0,    # 保守模式：2秒间隔
            'moderate': 1.0,        # 中等模式：1秒间隔  
            'aggressive': 0.5       # 激进模式：0.5秒间隔
        }
        self.max_retries = 3
        self.timeout = 30
        
    def diagnose_api_access(self):
        """诊断API访问状态"""
        print("🔍 开始API访问诊断...")
        print("=" * 50)
        
        results = {}
        
        # 测试不同API端点
        test_prompts = [
            "beautiful landscape",
            "portrait of a person",
            "abstract art"
        ]
        
        for i, prompt in enumerate(test_prompts):
            print(f"\n🧪 测试请求 {i+1}: {prompt}")
            
            # 测试不同的请求间隔
            for mode, delay in self.request_delays.items():
                print(f"  📊 测试 {mode} 模式 (间隔: {delay}s)")
                
                try:
                    start_time = time.time()
                    response = self._test_single_request(prompt, delay)
                    elapsed = time.time() - start_time
                    
                    if response and response.status_code == 200:
                        print(f"    ✅ 成功: 响应时间 {elapsed:.2f}s")
                        results[f"{mode}_{i}"] = {
                            'status': 'success',
                            'response_time': elapsed,
                            'delay_used': delay
                        }
                    else:
                        print(f"    ❌ 失败: 状态码 {response.status_code if response else '无响应'}")
                        results[f"{mode}_{i}"] = {
                            'status': 'failed',
                            'error': f"Status: {response.status_code if response else 'No Response'}",
                            'delay_used': delay
                        }
                        
                except Exception as e:
                    print(f"    ❌ 异常: {str(e)}")
                    results[f"{mode}_{i}"] = {
                        'status': 'error',
                        'error': str(e),
                        'delay_used': delay
                    }
                    
                # 避免连续请求过快
                time.sleep(1)
                
        return results
        
    def _test_single_request(self, prompt: str, delay: float):
        """测试单次请求"""
        url = f"https://image.pollinations.ai/prompt/{prompt}?width=1080&height=1920"
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        time.sleep(delay)  # 请求前延迟
        
        try:
            response = requests.get(url, headers=headers, timeout=self.timeout)
            return response
        except Exception as e:
            print(f"      请求异常: {str(e)}")
            return None
            
    def analyze_results(self, results: Dict):
        """分析诊断结果"""
        print("\n📊 诊断结果分析:")
        print("=" * 50)
        
        success_rates = {}
        avg_response_times = {}
        
        # 统计各模式成功率
        for mode in self.request_delays.keys():
            mode_results = [v for k, v in results.items() if k.startswith(mode)]
            if mode_results:
                success_count = sum(1 for r in mode_results if r['status'] == 'success')
                total_count = len(mode_results)
                success_rate = success_count / total_count * 100
                
                avg_time = sum(r['response_time'] for r in mode_results if r['status'] == 'success') / max(success_count, 1)
                
                success_rates[mode] = success_rate
                avg_response_times[mode] = avg_time
                
                print(f"{mode.upper()} 模式:")
                print(f"  成功率: {success_rate:.1f}% ({success_count}/{total_count})")
                print(f"  平均响应时间: {avg_time:.2f}s")
                print(f"  使用间隔: {self.request_delays[mode]}s")
                
        # 推荐最佳模式
        print("\n🎯 推荐配置:")
        if success_rates:
            best_mode = max(success_rates.keys(), key=lambda x: success_rates[x])
            print(f"推荐使用: {best_mode.upper()} 模式")
            print(f"请求间隔: {self.request_delays[best_mode]} 秒")
            print(f"预期成功率: {success_rates[best_mode]:.1f}%")
            
        return success_rates, avg_response_times

class OptimizedImageGenerator:
    """优化的图片生成器"""
    
    def __init__(self, delay_mode='conservative'):
        self.delay_mode = delay_mode
        self.base_delay = {
            'conservative': 2.0,
            'moderate': 1.0, 
            'aggressive': 0.5
        }.get(delay_mode, 2.0)
        
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        
        # 请求历史记录
        self.request_history = []
        self.max_history = 10
        
    def generate_image_with_retry(self, prompt: str, output_path: str, max_retries: int = 3):
        """带重试机制的图片生成"""
        for attempt in range(max_retries):
            try:
                print(f"  🔄 尝试第 {attempt + 1} 次生成: {prompt[:50]}...")
                
                # 检查请求频率
                self._check_rate_limit()
                
                # 构造API请求
                url = f"https://image.pollinations.ai/prompt/{prompt}?width=1080&height=1920"
                
                response = self.session.get(url, timeout=30)
                
                if response.status_code == 200:
                    # 保存图片
                    with open(output_path, 'wb') as f:
                        f.write(response.content)
                    
                    # 记录成功请求
                    self._record_request(time.time(), 'success')
                    
                    print(f"  ✅ 图片生成成功: {output_path}")
                    return True
                    
                elif response.status_code == 530:
                    print(f"  ⚠️  Cloudflare防护: {response.status_code}")
                    self._record_request(time.time(), 'rate_limited')
                    
                else:
                    print(f"  ❌ 请求失败: {response.status_code}")
                    self._record_request(time.time(), 'failed')
                    
            except Exception as e:
                print(f"  ❌ 异常: {str(e)}")
                self._record_request(time.time(), 'error')
                
            # 重试前等待
            if attempt < max_retries - 1:
                wait_time = self.base_delay * (2 ** attempt)  # 指数退避
                print(f"  ⏳ 等待 {wait_time:.1f} 秒后重试...")
                time.sleep(wait_time)
                
        return False
        
    def _check_rate_limit(self):
        """检查请求频率限制"""
        if len(self.request_history) >= 2:
            recent_requests = self.request_history[-2:]
            time_diff = recent_requests[1]['timestamp'] - recent_requests[0]['timestamp']
            
            # 如果两次请求间隔小于最小间隔，需要等待
            min_interval = self.base_delay
            if time_diff < min_interval:
                wait_time = min_interval - time_diff
                print(f"  ⏸️  频率控制: 等待 {wait_time:.2f} 秒")
                time.sleep(wait_time)
                
    def _record_request(self, timestamp: float, status: str):
        """记录请求历史"""
        self.request_history.append({
            'timestamp': timestamp,
            'status': status
        })
        
        # 保持历史记录在限制范围内
        if len(self.request_history) > self.max_history:
            self.request_history.pop(0)
            
    def get_stats(self):
        """获取统计信息"""
        if not self.request_history:
            return {}
            
        total = len(self.request_history)
        success = sum(1 for r in self.request_history if r['status'] == 'success')
        rate_limited = sum(1 for r in self.request_history if r['status'] == 'rate_limited')
        failed = sum(1 for r in self.request_history if r['status'] in ['failed', 'error'])
        
        return {
            'total_requests': total,
            'success_rate': success / total * 100,
            'rate_limited': rate_limited,
            'failures': failed
        }

def demonstrate_optimized_approach():
    """演示优化后的处理方式"""
    print("\n🚀 优化方案演示:")
    print("=" * 50)
    
    # 1. 诊断当前API状态
    diagnostic = ImageGenerationDiagnostic()
    results = diagnostic.diagnose_api_access()
    success_rates, response_times = diagnostic.analyze_results(results)
    
    # 2. 推荐最优配置
    if success_rates:
        best_mode = max(success_rates.keys(), key=lambda x: success_rates[x])
        print(f"\n🔧 推荐配置:")
        print(f"   延迟模式: {best_mode}")
        print(f"   请求间隔: {diagnostic.request_delays[best_mode]} 秒")
        print(f"   预期成功率: {success_rates[best_mode]:.1f}%")
        
        # 3. 演示优化后的生成器
        print(f"\n🤖 使用优化生成器测试:")
        generator = OptimizedImageGenerator(delay_mode=best_mode)
        
        test_prompts = [
            "sunset landscape with mountains",
            "portrait of happy person",
            "abstract colorful art"
        ]
        
        successful_generations = 0
        for i, prompt in enumerate(test_prompts):
            output_path = f"test_image_{i+1}.jpg"
            success = generator.generate_image_with_retry(prompt, output_path, max_retries=2)
            if success:
                successful_generations += 1
                
        stats = generator.get_stats()
        print(f"\n📈 生成统计:")
        print(f"   成功生成: {successful_generations}/{len(test_prompts)}")
        print(f"   总请求次数: {stats.get('total_requests', 0)}")
        print(f"   成功率: {stats.get('success_rate', 0):.1f}%")

def create_fixed_gui_code():
    """生成修复后的GUI代码片段"""
    fixed_code = '''
# 修复后的批量图片生成方法
async def _batch_generate_worker(self, scenes):
    """优化的批量生成工作者 - 带频率控制"""
    results = []
    total = len(scenes)
    
    # 使用优化的图片生成器
    from optimized_image_generator import OptimizedImageGenerator
    image_generator = OptimizedImageGenerator(delay_mode='conservative')
    
    for i, scene in enumerate(scenes):
        # 更新进度
        progress = (i + 1) / total * 100
        self.update_ui_safely(self._update_generation_progress, i+1, total, progress)
        
        # 生成单个图片
        try:
            prompt = scene.get('prompt', '')
            output_name = self.convert_title_to_filename(self.current_title)
            output_path = os.path.join(self.output_dir, datetime.now().strftime("%Y%m"), output_name)
            os.makedirs(output_path, exist_ok=True)
            image_path = os.path.join(output_path, f"scene_{i:03d}.jpg")
            
            # 使用优化的生成器
            success = image_generator.generate_image_with_retry(
                prompt, image_path, max_retries=3
            )
            
            if success:
                results.append((i, image_path, True))
                self.update_ui_safely(self.append_log, f"✅ 场景 {i+1} 生成成功\n")
            else:
                results.append((i, "生成失败", False))
                self.update_ui_safely(self.append_log, f"❌ 场景 {i+1} 生成失败\n")
                
        except Exception as e:
            results.append((i, str(e), False))
            self.update_ui_safely(self.append_log, f"❌ 场景 {i+1} 异常: {str(e)}\n")
            
        # 场景间延迟 - 避免请求过频
        await asyncio.sleep(2.0)  # 保守间隔2秒
        
    return results
'''
    
    print("\n📋 修复后的核心代码:")
    print(fixed_code)

if __name__ == "__main__":
    print("🖼️  图片生成问题诊断工具")
    print("=" * 60)
    
    try:
        demonstrate_optimized_approach()
        create_fixed_gui_code()
        
        print(f"\n✅ 诊断完成!")
        print(f"💡 建议:")
        print(f"   1. 增加请求间隔时间")
        print(f"   2. 实现指数退避重试机制") 
        print(f"   3. 添加请求频率监控")
        print(f"   4. 使用会话复用减少连接开销")
        
    except KeyboardInterrupt:
        print(f"\n⚠️  诊断被用户中断")
    except Exception as e:
        print(f"\n❌ 诊断过程中发生错误: {str(e)}")
        traceback.print_exc()