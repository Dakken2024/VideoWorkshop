from moviepy import *

# 测试基本功能
print("✅ 基本导入成功")

# 创建简单的颜色剪辑测试
try:
    clip = ColorClip(size=(1080, 1920), color=(255, 0, 0)).with_duration(2)
    print("✅ ColorClip 创建成功")
    
    # 测试保存
    clip.save_frame("./output/test_frame.jpg", t=1)
    print("✅ 帧保存成功")
    
    # 测试简单视频导出
    clip.write_videofile("./output/test_video.mp4", fps=24)
    print("✅ 视频导出成功")
    
except Exception as e:
    print(f"❌ 错误: {e}")