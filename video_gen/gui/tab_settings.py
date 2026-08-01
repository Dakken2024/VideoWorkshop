#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API 设置标签页 - 所有 API 配置管理
"""

import tkinter as tk
from tkinter import ttk, messagebox
import os
from typing import TYPE_CHECKING

from ..config import DEFAULT_CONFIG, AIConfig, SearchConfig, ImageAPIConfig, VoiceConfig
from ..utils.logger import logger
from .widgets import SectionFrame, ApiKeyEntry, ConfigEntry, ToggleButton

if TYPE_CHECKING:
    from .app import VideoWorkshopGUI


class SettingsTab(ttk.Frame):
    """API 设置"""

    def __init__(self, parent, app: "VideoWorkshopGUI"):
        super().__init__(parent)
        self.app = app
        self._build_ui()

    def _build_ui(self):
        canvas = tk.Canvas(self)
        scrollbar = ttk.Scrollbar(self, orient=tk.VERTICAL, command=canvas.yview)
        scroll_frame = ttk.Frame(canvas)

        scroll_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scroll_frame, anchor=tk.NW)
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # === 1. 文生图 API ===
        img_frame = SectionFrame(scroll_frame, "文生图 API", padding=15)
        img_frame.pack(fill=tk.X, padx=15, pady=10)

        self.img_default_var = tk.StringVar(value="Pollinations (免费)")
        ttk.Label(img_frame, text="默认服务商:", width=15, anchor=tk.W).grid(row=0, column=0, sticky=tk.W, padx=(0, 10), pady=3)
        ttk.Label(img_frame, text="Pollinations (免费)", foreground="green").grid(row=0, column=1, sticky=tk.W, pady=3)

        self.img_custom_group = ttk.LabelFrame(img_frame, text="自定义 API", padding=10)
        self.img_custom_group.grid(row=1, column=0, columnspan=3, sticky=tk.EW, pady=(10, 0))
        self.img_custom_group.columnconfigure(1, weight=1)

        self.img_url_entry = ConfigEntry(self.img_custom_group, "服务地址", default="", width=50)
        self.img_url_entry.grid(row=0, column=0, columnspan=3, sticky=tk.EW, pady=3)

        self.img_key_entry = ApiKeyEntry(self.img_custom_group, "API密钥", default="")
        self.img_key_entry.grid(row=1, column=0, columnspan=3, sticky=tk.EW, pady=3)

        self.img_model_entry = ConfigEntry(self.img_custom_group, "模型", default="flux")
        self.img_model_entry.grid(row=2, column=0, columnspan=3, sticky=tk.EW, pady=3)

        ttk.Button(img_frame, text="测试连接", command=self._test_image_api).grid(row=3, column=0, pady=10)

        # === 2. AI 大模型 ===
        ai_frame = SectionFrame(scroll_frame, "AI 大模型", padding=15)
        ai_frame.pack(fill=tk.X, padx=15, pady=10)

        self.ai_enabled = ToggleButton(ai_frame, "启用 AI", default=False)
        self.ai_enabled.pack(fill=tk.X, pady=2)

        self.ai_provider = ConfigEntry(ai_frame, "服务商", default="DeepSeek")
        self.ai_provider.pack(fill=tk.X, pady=2)

        self.ai_url = ConfigEntry(ai_frame, "接口地址", default="https://api.deepseek.com", width=50)
        self.ai_url.pack(fill=tk.X, pady=2)

        self.ai_key = ApiKeyEntry(ai_frame, "API密钥")
        self.ai_key.pack(fill=tk.X, pady=2)

        self.ai_model = ConfigEntry(ai_frame, "模型", default=DEFAULT_CONFIG.ai.model)
        self.ai_model.pack(fill=tk.X, pady=2)

        # 模块开关
        modules_frame = ttk.LabelFrame(ai_frame, text="启用模块", padding=10)
        modules_frame.pack(fill=tk.X, pady=(10, 0))

        self.module_content = ToggleButton(modules_frame, "内容创作", default=False)
        self.module_content.pack(fill=tk.X, pady=2)
        self.module_script = ToggleButton(modules_frame, "脚本生成", default=False)
        self.module_script.pack(fill=tk.X, pady=2)
        self.module_prompt = ToggleButton(modules_frame, "提示词增强", default=False)
        self.module_prompt.pack(fill=tk.X, pady=2)

        ttk.Button(ai_frame, text="测试连接", command=self._test_ai).pack(pady=10)

        # === 3. 搜索 API ===
        search_frame = SectionFrame(scroll_frame, "搜索 API", padding=15)
        search_frame.pack(fill=tk.X, padx=15, pady=10)

        self.serpapi_key = ApiKeyEntry(search_frame, "SerpAPI Key")
        self.serpapi_key.pack(fill=tk.X, pady=2)

        self.tavily_key = ApiKeyEntry(search_frame, "Tavily Key")
        self.tavily_key.pack(fill=tk.X, pady=2)

        ttk.Button(search_frame, text="测试搜索", command=self._test_search).pack(pady=10)

        # === 4. 语音合成 ===
        voice_frame = SectionFrame(scroll_frame, "语音合成", padding=15)
        voice_frame.pack(fill=tk.X, padx=15, pady=10)

        self.voice_default_var = tk.StringVar(value="edge-tts")
        ttk.Label(voice_frame, text="默认服务:", width=15, anchor=tk.W).grid(row=0, column=0, sticky=tk.W, padx=(0, 10), pady=3)
        ttk.Label(voice_frame, text="edge-tts (免费)", foreground="green").grid(row=0, column=1, sticky=tk.W, pady=3)

        self.voice_custom_group = ttk.LabelFrame(voice_frame, text="自定义语音 API", padding=10)
        self.voice_custom_group.grid(row=1, column=0, columnspan=3, sticky=tk.EW, pady=(10, 0))
        self.voice_custom_group.columnconfigure(1, weight=1)

        self.voice_url = ConfigEntry(self.voice_custom_group, "服务地址", default="", width=50)
        self.voice_url.grid(row=0, column=0, columnspan=3, sticky=tk.EW, pady=3)

        self.voice_key = ApiKeyEntry(self.voice_custom_group, "API密钥")
        self.voice_key.grid(row=1, column=0, columnspan=3, sticky=tk.EW, pady=3)

        self.voice_model = ConfigEntry(self.voice_custom_group, "模型", default="")
        self.voice_model.grid(row=2, column=0, columnspan=3, sticky=tk.EW, pady=3)

        # === 保存按钮 ===
        btn_frame = ttk.Frame(scroll_frame)
        btn_frame.pack(fill=tk.X, padx=15, pady=20)

        ttk.Button(btn_frame, text="💾 保存配置", command=self._save_config).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="🔄 恢复默认", command=self._reset_config).pack(side=tk.LEFT, padx=5)

        # 加载现有配置
        self._load_config()

    def _load_config(self):
        """加载现有配置"""
        config = DEFAULT_CONFIG

        # AI
        self.ai_enabled.set(config.ai.enabled)
        self.ai_url.set(config.ai.base_url)
        self.ai_key.set(config.ai.api_key)
        self.ai_model.set(config.ai.model)
        self.module_content.set(config.ai.modules.get("content_generation", False))
        self.module_script.set(config.ai.modules.get("script_generation", False))
        self.module_prompt.set(config.ai.modules.get("prompt_enhancement", False))

        # Search
        self.serpapi_key.set(config.search.serpapi_key)
        self.tavily_key.set(config.search.tavily_key)

        # Image API
        if config.image_api.providers:
            self.img_url_entry.set(config.image_api.providers[1].base_url if len(config.image_api.providers) > 1 else "")
            self.img_key_entry.set(config.image_api.providers[1].api_key if len(config.image_api.providers) > 1 else "")

        # Voice
        self.voice_url.set(config.voice.custom_base_url)
        self.voice_key.set(config.voice.custom_api_key)
        self.voice_model.set(config.voice.custom_model)

    def _save_config(self):
        """保存配置"""
        config = DEFAULT_CONFIG

        # AI
        config.ai.enabled = self.ai_enabled.get()
        config.ai.base_url = self.ai_url.get()
        config.ai.api_key = self.ai_key.get()
        config.ai.model = self.ai_model.get()
        config.ai.modules["content_generation"] = self.module_content.get()
        config.ai.modules["script_generation"] = self.module_script.get()
        config.ai.modules["prompt_enhancement"] = self.module_prompt.get()

        # Search
        config.search.serpapi_key = self.serpapi_key.get()
        config.search.tavily_key = self.tavily_key.get()

        # Image API
        if len(config.image_api.providers) > 1:
            config.image_api.providers[1].base_url = self.img_url_entry.get()
            config.image_api.providers[1].api_key = self.img_key_entry.get()
            config.image_api.providers[1].model = self.img_model_entry.get()

        # Voice
        config.voice.custom_base_url = self.voice_url.get()
        config.voice.custom_api_key = self.voice_key.get()
        config.voice.custom_model = self.voice_model.get()

        # 保存到环境变量文件
        self._save_env_file(config)

        self.app.log("✅ 配置已保存")
        messagebox.showinfo("成功", "配置已保存！")

    def _save_env_file(self, config):
        """保存配置到 .env 文件"""
        env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
        with open(env_path, "w", encoding="utf-8") as f:
            f.write(f"# Video Workshop Configuration\n")
            f.write(f"# Generated at: {__import__('datetime').datetime.now().isoformat()}\n\n")
            f.write(f"# AI\n")
            f.write(f"AI_API_KEY={config.ai.api_key}\n")
            f.write(f"AI_BASE_URL={config.ai.base_url}\n")
            f.write(f"AI_MODEL={config.ai.model}\n\n")
            f.write(f"# Search\n")
            f.write(f"SERPAPI_KEY={config.search.serpapi_key}\n")
            f.write(f"TAVILY_KEY={config.search.tavily_key}\n\n")
            f.write(f"# Voice\n")
            f.write(f"VOICE_BASE_URL={config.voice.custom_base_url}\n")
            f.write(f"VOICE_API_KEY={config.voice.custom_api_key}\n")
        self.app.log(f"配置已写入: {env_path}")

    def _reset_config(self):
        """恢复默认配置"""
        if messagebox.askyesno("确认", "确定要恢复默认配置吗？"):
            config = DEFAULT_CONFIG
            config.ai = AIConfig()
            config.search = SearchConfig()
            config.voice = VoiceConfig()
            self._load_config()
            self.app.log("配置已恢复默认")

    def _test_image_api(self):
        """测试文生图 API"""
        self.app.log("测试文生图 API...")
        messagebox.showinfo("提示", "文生图 API 测试功能需在运行时验证，请尝试生成视频")

    def _test_ai(self):
        """测试 AI 连接"""
        api_key = self.ai_key.get()
        if not api_key:
            messagebox.showwarning("提示", "请先填写 API Key")
            return

        def run():
            from ..ai.deepseek import DeepSeekClient
            from ..config import AIConfig

            config = AIConfig(
                enabled=True,
                api_key=api_key,
                base_url=self.ai_url.get(),
                model=self.ai_model.get(),
            )
            client = DeepSeekClient(config)
            try:
                self.app.root.after(0, self.app.log, "正在测试 AI 连接...")
                response = client.chat([
                    {"role": "user", "content": "回复'连接成功'即可，不要其他内容"}
                ])
                self.app.root.after(0, self.app.log, f"✅ AI 连接成功: {response.content}")
                self.app.root.after(0, messagebox.showinfo, "成功", "AI 连接测试通过！")
            except Exception as e:
                self.app.root.after(0, self.app.log, f"❌ AI 连接失败: {e}")
                self.app.root.after(0, messagebox.showerror, "失败", f"连接失败: {e}")

        import threading
        thread = threading.Thread(target=run, daemon=True)
        thread.start()

    def _test_search(self):
        """测试搜索"""
        serpapi_key = self.serpapi_key.get()
        tavily_key = self.tavily_key.get()

        if not serpapi_key and not tavily_key:
            messagebox.showwarning("提示", "请至少配置一个搜索 API Key")
            return

        def run():
            from ..ai.search import SearchManager
            from ..config import SearchConfig

            config = SearchConfig(serpapi_key=serpapi_key, tavily_key=tavily_key)
            search = SearchManager(config)

            try:
                self.app.root.after(0, self.app.log, "正在测试搜索...")
                results = search.search("测试搜索", max_results=3)
                if results:
                    msg = f"搜索成功，返回 {len(results)} 条结果:\n"
                    for r in results[:3]:
                        msg += f"  - {r.title}\n"
                    self.app.root.after(0, self.app.log, f"✅ 搜索成功: {len(results)} 条结果")
                    self.app.root.after(0, messagebox.showinfo, "成功", msg)
                else:
                    self.app.root.after(0, self.app.log, "搜索未返回结果")
                    self.app.root.after(0, messagebox.showinfo, "提示", "搜索未返回结果")
            except Exception as e:
                self.app.root.after(0, self.app.log, f"❌ 搜索失败: {e}")
                self.app.root.after(0, messagebox.showerror, "失败", f"搜索失败: {e}")

        import threading
        thread = threading.Thread(target=run, daemon=True)
        thread.start()