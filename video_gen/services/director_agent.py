"""
LLM 导演 Agent - 智能镜头语言生成
分析脚本并输出分镜指令、运镜效果、转场方式
"""
import json
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from enum import Enum


class ShotType(Enum):
    """镜头类型"""
    EXTREME_CLOSE_UP = "extreme_close_up"  # 特写
    CLOSE_UP = "close_up"  # 近景
    MEDIUM_SHOT = "medium_shot"  # 中景
    FULL_SHOT = "full_shot"  # 全景
    LONG_SHOT = "long_shot"  # 远景
    ESTABLISHING = "establishing"  # 定场镜头


class CameraMovement(Enum):
    """运镜方式"""
    STATIC = "static"  # 固定
    PAN_LEFT = "pan_left"  # 左摇
    PAN_RIGHT = "pan_right"  # 右摇
    TILT_UP = "tilt_up"  # 上摇
    TILT_DOWN = "tilt_down"  # 下摇
    ZOOM_IN = "zoom_in"  # 推近
    ZOOM_OUT = "zoom_out"  # 拉远
    DOLLY_IN = "dolly_in"  # 推进
    DOLLY_OUT = "dolly_out"  # 拉出
    TRACKING = "tracking"  # 跟随
    ORBIT = "orbit"  # 环绕


class TransitionType(Enum):
    """转场类型"""
    CUT = "cut"  # 硬切
    FADE_IN = "fade_in"  # 淡入
    FADE_OUT = "fade_out"  # 淡出
    CROSS_DISSOLVE = "cross_dissolve"  # 交叉溶解
    WIPE_LEFT = "wipe_left"  # 左擦除
    WIPE_RIGHT = "wipe_right"  # 右擦除
    BLUR_TRANSITION = "blur_transition"  # 模糊转场
    ZOOM_TRANSITION = "zoom_transition"  # 缩放转场


@dataclass
class ShotInstruction:
    """单镜头指令"""
    scene_id: int
    shot_type: ShotType
    camera_movement: CameraMovement
    duration: float  # 秒
    description: str  # 镜头描述
    focus_point: str = ""  # 焦点位置
    mood: str = ""  # 情绪氛围
    notes: str = ""  # 备注
    
    def to_dict(self) -> dict:
        return {
            'scene_id': self.scene_id,
            'shot_type': self.shot_type.value,
            'camera_movement': self.camera_movement.value,
            'duration': self.duration,
            'description': self.description,
            'focus_point': self.focus_point,
            'mood': self.mood,
            'notes': self.notes
        }


@dataclass
class SceneDirector:
    """场景导演信息"""
    scene_id: int
    script_text: str
    shots: List[ShotInstruction] = field(default_factory=list)
    transition_in: TransitionType = TransitionType.CUT
    transition_out: TransitionType = TransitionType.CUT
    bgm_mood: str = ""  # 背景音乐情绪
    sfx_cues: List[str] = field(default_factory=list)  # 音效提示
    
    def to_dict(self) -> dict:
        return {
            'scene_id': self.scene_id,
            'script_text': self.script_text,
            'shots': [s.to_dict() for s in self.shots],
            'transition_in': self.transition_in.value,
            'transition_out': self.transition_out.value,
            'bgm_mood': self.bgm_mood,
            'sfx_cues': self.sfx_cues
        }


class DirectorAgent:
    """导演 Agent"""
    
    def __init__(self, llm_client=None):
        self.llm_client = llm_client
        self.system_prompt = """你是一位专业的电影导演和分镜师。
你的任务是将视频脚本转换为详细的分镜指令。

对于每个场景，你需要：
1. 选择合适的镜头类型（特写、近景、中景、全景、远景）
2. 设计运镜方式（固定、推拉摇移、跟随等）
3. 确定镜头时长
4. 指定转场效果
5. 建议背景音乐情绪和音效

请根据脚本内容的情绪、节奏和重点来设计镜头语言。"""
    
    def analyze_script(self, script: str, scenes: List[Dict]) -> List[SceneDirector]:
        """分析脚本并生成分镜"""
        if self.llm_client:
            return self._analyze_with_llm(script, scenes)
        else:
            return self._analyze_with_rules(script, scenes)
    
    def _analyze_with_llm(self, script: str, scenes: List[Dict]) -> List[SceneDirector]:
        """使用 LLM 分析脚本"""
        prompt = f"""请分析以下视频脚本并生成分镜指令：

完整脚本：
{script}

场景列表：
{json.dumps(scenes, ensure_ascii=False, indent=2)}

请以 JSON 格式返回分镜结果，包含每个场景的：
- scene_id: 场景 ID
- shots: 镜头列表，每个镜头包含 shot_type, camera_movement, duration, description
- transition_in/out: 转场类型
- bgm_mood: 背景音乐情绪
- sfx_cues: 音效提示

JSON 格式示例：
[
  {{
    "scene_id": 1,
    "shots": [
      {{"shot_type": "establishing", "camera_movement": "static", "duration": 3.0, "description": "开场全景"}}
    ],
    "transition_in": "fade_in",
    "transition_out": "cut",
    "bgm_mood": "calm",
    "sfx_cues": ["ambient wind"]
  }}
]"""
        
        try:
            response = self.llm_client.chat(prompt, system=self.system_prompt)
            result = json.loads(response)
            
            directors = []
            for item in result:
                scene = SceneDirector(
                    scene_id=item['scene_id'],
                    script_text="",
                    transition_in=TransitionType(item.get('transition_in', 'cut')),
                    transition_out=TransitionType(item.get('transition_out', 'cut')),
                    bgm_mood=item.get('bgm_mood', ''),
                    sfx_cues=item.get('sfx_cues', [])
                )
                
                for shot_data in item.get('shots', []):
                    shot = ShotInstruction(
                        scene_id=item['scene_id'],
                        shot_type=ShotType(shot_data.get('shot_type', 'medium_shot')),
                        camera_movement=CameraMovement(shot_data.get('camera_movement', 'static')),
                        duration=shot_data.get('duration', 3.0),
                        description=shot_data.get('description', ''),
                        focus_point=shot_data.get('focus_point', ''),
                        mood=shot_data.get('mood', ''),
                        notes=shot_data.get('notes', '')
                    )
                    scene.shots.append(shot)
                
                directors.append(scene)
            
            return directors
        
        except Exception as e:
            print(f"LLM analysis failed: {e}, falling back to rule-based")
            return self._analyze_with_rules(script, scenes)
    
    def _analyze_with_rules(self, script: str, scenes: List[Dict]) -> List[SceneDirector]:
        """基于规则的分析（备用方案）"""
        directors = []
        
        for i, scene in enumerate(scenes):
            text = scene.get('text', '')
            word_count = len(text.split())
            estimated_duration = word_count / 3.0  # 假设每秒 3 个字
            
            # 简单规则：根据文本长度决定镜头
            if word_count < 20:
                shot_type = ShotType.CLOSE_UP
                movement = CameraMovement.STATIC
            elif word_count < 50:
                shot_type = ShotType.MEDIUM_SHOT
                movement = CameraMovement.SLOW_PAN
            else:
                shot_type = ShotType.FULL_SHOT
                movement = CameraMovement.TRACKING
            
            # 首尾场景特殊处理
            trans_in = TransitionType.FADE_IN if i == 0 else TransitionType.CUT
            trans_out = TransitionType.FADE_OUT if i == len(scenes) - 1 else TransitionType.CROSS_DISSOLVE
            
            director = SceneDirector(
                scene_id=scene.get('id', i),
                script_text=text,
                shots=[
                    ShotInstruction(
                        scene_id=scene.get('id', i),
                        shot_type=shot_type,
                        camera_movement=movement,
                        duration=estimated_duration,
                        description=text[:50] + "..." if len(text) > 50 else text
                    )
                ],
                transition_in=trans_in,
                transition_out=trans_out,
                bgm_mood="neutral",
                sfx_cues=[]
            )
            
            directors.append(director)
        
        return directors
    
    def enhance_image_prompt(self, base_prompt: str, shot: ShotInstruction) -> str:
        """增强图像生成提示词，加入镜头语言"""
        shot_keywords = {
            ShotType.EXTREME_CLOSE_UP: "extreme close-up shot, macro detail",
            ShotType.CLOSE_UP: "close-up shot, detailed facial features",
            ShotType.MEDIUM_SHOT: "medium shot, waist-up framing",
            ShotType.FULL_SHOT: "full body shot, complete figure",
            ShotType.LONG_SHOT: "long shot, distant view",
            ShotType.ESTABLISHING: "wide establishing shot, scenic view"
        }
        
        movement_keywords = {
            CameraMovement.STATIC: "static camera",
            CameraMovement.PAN_LEFT: "camera panning left",
            CameraMovement.PAN_RIGHT: "camera panning right",
            CameraMovement.TILT_UP: "camera tilting up",
            CameraMovement.TILT_DOWN: "camera tilting down",
            CameraMovement.ZOOM_IN: "zooming in effect",
            CameraMovement.ZOOM_OUT: "zooming out effect",
            CameraMovement.DOLLY_IN: "dolly in movement",
            CameraMovement.DOLLY_OUT: "dolly out movement",
            CameraMovement.TRACKING: "tracking shot, following movement",
            CameraMovement.ORBIT: "orbiting camera movement"
        }
        
        enhanced = base_prompt
        
        if shot.shot_type in shot_keywords:
            enhanced += f", {shot_keywords[shot.shot_type]}"
        
        if shot.camera_movement in movement_keywords:
            enhanced += f", {movement_keywords[shot.camera_movement]}"
        
        if shot.mood:
            enhanced += f", {shot.mood} atmosphere"
        
        return enhanced
    
    def get_transition_params(self, transition: TransitionType) -> Dict[str, Any]:
        """获取转场参数"""
        params = {
            TransitionType.CUT: {'type': 'cut', 'duration': 0},
            TransitionType.FADE_IN: {'type': 'fade', 'direction': 'in', 'duration': 1.0},
            TransitionType.FADE_OUT: {'type': 'fade', 'direction': 'out', 'duration': 1.0},
            TransitionType.CROSS_DISSOLVE: {'type': 'dissolve', 'duration': 0.5},
            TransitionType.WIPE_LEFT: {'type': 'wipe', 'direction': 'left', 'duration': 0.5},
            TransitionType.WIPE_RIGHT: {'type': 'wipe', 'direction': 'right', 'duration': 0.5},
            TransitionType.BLUR_TRANSITION: {'type': 'blur', 'duration': 0.5},
            TransitionType.ZOOM_TRANSITION: {'type': 'zoom', 'duration': 0.5}
        }
        return params.get(transition, params[TransitionType.CUT])


# 全局导演 Agent 实例
director_agent = DirectorAgent()


def direct_scene(script: str, scenes: List[Dict], llm_client=None) -> List[SceneDirector]:
    """快捷函数：导演分镜"""
    agent = DirectorAgent(llm_client)
    return agent.analyze_script(script, scenes)
