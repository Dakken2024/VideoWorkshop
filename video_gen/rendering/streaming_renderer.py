"""
流式渲染引擎
支持分片渲染、显存优化、进度回调
"""
import os
import gc
import asyncio
from pathlib import Path
from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass


@dataclass
class RenderChunk:
    """渲染分片"""
    chunk_id: int
    start_frame: int
    end_frame: int
    scenes: List[Dict]
    output_path: str


@dataclass
class RenderProgress:
    """渲染进度"""
    current_chunk: int
    total_chunks: int
    current_frame: int
    total_frames: int
    percentage: float
    message: str
    memory_usage_mb: float


class StreamingRenderer:
    """流式渲染器"""
    
    def __init__(self, output_dir: str = "output", 
                 chunk_size: int = 30,  # 每 chunk 最多帧数
                 max_memory_mb: int = 4096,  # 最大内存限制
                 cleanup_interval: int = 5):  # 每 n 个 chunk 清理一次
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.chunk_size = chunk_size
        self.max_memory_mb = max_memory_mb
        self.cleanup_interval = cleanup_interval
        
        self.temp_dir = self.output_dir / "temp"
        self.temp_dir.mkdir(exist_ok=True)
        
        self._progress_callback: Optional[Callable[[RenderProgress], None]] = None
    
    def set_progress_callback(self, callback: Callable[[RenderProgress], None]):
        """设置进度回调"""
        self._progress_callback = callback
    
    def _estimate_memory_usage(self, width: int, height: int, frames: int) -> float:
        """估算内存使用 (MB)"""
        frame_size_mb = (width * height * 4) / 1024 / 1024
        return frame_size_mb * frames
    
    def _split_into_chunks(self, scenes: List[Dict], fps: int) -> List[RenderChunk]:
        """将场景分割为渲染分片"""
        chunks = []
        current_chunk_scenes = []
        current_frame_count = 0
        chunk_id = 0
        start_frame = 0
        
        for i, scene in enumerate(scenes):
            duration = scene.get('duration', 3.0)
            scene_frames = int(duration * fps)
            
            if current_frame_count + scene_frames > self.chunk_size:
                if current_chunk_scenes:
                    chunk = RenderChunk(
                        chunk_id=chunk_id,
                        start_frame=start_frame,
                        end_frame=start_frame + current_frame_count,
                        scenes=current_chunk_scenes,
                        output_path=str(self.temp_dir / f"chunk_{chunk_id}.mp4")
                    )
                    chunks.append(chunk)
                    chunk_id += 1
                
                current_chunk_scenes = [scene]
                current_frame_count = scene_frames
                start_frame = sum(int(s.get('duration', 3.0) * fps) for s in scenes[:i])
            else:
                current_chunk_scenes.append(scene)
                current_frame_count += scene_frames
        
        if current_chunk_scenes:
            chunk = RenderChunk(
                chunk_id=chunk_id,
                start_frame=start_frame,
                end_frame=start_frame + current_frame_count,
                scenes=current_chunk_scenes,
                output_path=str(self.temp_dir / f"chunk_{chunk_id}.mp4")
            )
            chunks.append(chunk)
        
        return chunks
    
    def _get_memory_usage(self) -> float:
        """获取当前内存使用 (MB)"""
        try:
            import psutil
            process = psutil.Process(os.getpid())
            return process.memory_info().rss / 1024 / 1024
        except:
            return 0.0
    
    def _render_chunk(self, chunk: RenderChunk, fps: int, 
                      canvas_size: tuple, progress_offset: float) -> RenderProgress:
        """渲染单个分片"""
        from src.rendering.video_renderer import VideoRenderer
        from PIL import Image
        import numpy as np
        
        renderer = VideoRenderer(canvas_size[0], canvas_size[1], fps)
        
        total_frames = sum(int(s.get('duration', 3.0) * fps) for s in chunk.scenes)
        
        try:
            frame_offset = 0
            for i, scene in enumerate(chunk.scenes):
                image_path = scene.get('image_path')
                duration = scene.get('duration', 3.0)
                
                if image_path and os.path.exists(image_path):
                    img = Image.open(image_path).convert('RGB')
                    img = img.resize(canvas_size)
                    frames = int(duration * fps)
                    
                    for f in range(frames):
                        renderer.add_frame(np.array(img), duration=1/fps)
                    
                    frame_offset += frames
                
                percentage = progress_offset + ((i + 1) / len(chunk.scenes)) * (1.0 / len(chunk.scenes))
                
                progress = RenderProgress(
                    current_chunk=chunk.chunk_id,
                    total_chunks=1,
                    current_frame=frame_offset,
                    total_frames=total_frames,
                    percentage=round(percentage * 100, 2),
                    message=f"Rendering chunk {chunk.chunk_id}, scene {i+1}/{len(chunk.scenes)}",
                    memory_usage_mb=self._get_memory_usage()
                )
                
                if self._progress_callback:
                    self._progress_callback(progress)
            
            renderer.export(chunk.output_path)
            
        finally:
            del renderer
            gc.collect()
        
        return progress
    
    def _merge_chunks(self, chunks: List[RenderChunk], output_path: str):
        """合并所有分片"""
        import subprocess
        
        concat_file = self.temp_dir / "concat_list.txt"
        with open(concat_file, 'w') as f:
            for chunk in chunks:
                if os.path.exists(chunk.output_path):
                    f.write(f"file '{chunk.output_path}'\n")
        
        try:
            cmd = [
                'ffmpeg', '-y',
                '-f', 'concat',
                '-safe', '0',
                '-i', str(concat_file),
                '-c', 'copy',
                output_path
            ]
            subprocess.run(cmd, check=True, capture_output=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            print("FFmpeg not available, chunks not merged")
        
        if concat_file.exists():
            concat_file.unlink()
    
    def render(self, scenes: List[Dict], fps: int, canvas_size: tuple,
               output_path: str) -> str:
        """流式渲染完整视频"""
        print(f"Starting streaming render: {len(scenes)} scenes, {canvas_size}, {fps}fps")
        
        chunks = self._split_into_chunks(scenes, fps)
        print(f"Split into {len(chunks)} chunks")
        
        for i, chunk in enumerate(chunks):
            progress_offset = i / len(chunks)
            
            self._render_chunk(chunk, fps, canvas_size, progress_offset)
            
            if (i + 1) % self.cleanup_interval == 0:
                gc.collect()
                print(f"Memory cleaned after chunk {i+1}")
        
        self._merge_chunks(chunks, output_path)
        gc.collect()
        
        print(f"Streaming render completed: {output_path}")
        return output_path
    
    async def render_async(self, scenes: List[Dict], fps: int, canvas_size: tuple,
                           output_path: str) -> str:
        """异步流式渲染"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, 
            lambda: self.render(scenes, fps, canvas_size, output_path)
        )
    
    def cleanup_temp(self):
        """清理临时文件"""
        import shutil
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
            self.temp_dir.mkdir(exist_ok=True)


def render_streaming(scenes: List[Dict], fps: int, canvas_size: tuple,
                     output_path: str, callback: Callable = None) -> str:
    """快捷函数：流式渲染"""
    renderer = StreamingRenderer()
    if callback:
        renderer.set_progress_callback(callback)
    return renderer.render(scenes, fps, canvas_size, output_path)
