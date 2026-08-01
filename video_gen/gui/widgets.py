#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
通用 GUI 组件
"""

import tkinter as tk
from tkinter import ttk
from typing import Optional, Callable


class LogWidget(ttk.Frame):
    """日志显示组件"""

    def __init__(self, parent, height=8):
        super().__init__(parent)
        self.text = tk.Text(self, height=height, wrap=tk.WORD,
                            font=("Consolas", 9), bg="#1e1e1e", fg="#d4d4d4",
                            insertbackground="white", state=tk.DISABLED)
        scrollbar = ttk.Scrollbar(self, orient=tk.VERTICAL, command=self.text.yview)
        self.text.configure(yscrollcommand=scrollbar.set)

        self.text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    def log(self, message: str):
        """添加日志"""
        import datetime
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        self.text.configure(state=tk.NORMAL)
        self.text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.text.see(tk.END)
        self.text.configure(state=tk.DISABLED)
        self.update_idletasks()

    def clear(self):
        """清空日志"""
        self.text.configure(state=tk.NORMAL)
        self.text.delete(1.0, tk.END)
        self.text.configure(state=tk.DISABLED)


class ProgressBar(ttk.Frame):
    """进度条组件"""

    def __init__(self, parent):
        super().__init__(parent)
        self.progress_var = tk.DoubleVar()
        self.bar = ttk.Progressbar(self, variable=self.progress_var, maximum=100, mode="determinate")
        self.label = ttk.Label(self, text="就绪", width=40, anchor=tk.W)

        self.label.pack(side=tk.LEFT, padx=(0, 10))
        self.bar.pack(side=tk.LEFT, fill=tk.X, expand=True)

    def set_progress(self, value: int, message: str = ""):
        """设置进度"""
        self.progress_var.set(value)
        if message:
            self.label.configure(text=message)
        self.update_idletasks()

    def reset(self, message: str = "就绪"):
        """重置"""
        self.progress_var.set(0)
        self.label.configure(text=message)
        self.update_idletasks()


class SectionFrame(ttk.LabelFrame):
    """带标题的分组框架"""

    def __init__(self, parent, title: str, padding: int = 10):
        super().__init__(parent, text=title, padding=padding)
        self.columnconfigure(1, weight=1)

    def add_row(self, label: str, widget: tk.Widget, col_span: int = 1):
        """添加一行：标签 + 控件"""
        row = self.grid_size()[1]
        lbl = ttk.Label(self, text=label, width=15, anchor=tk.W)
        lbl.grid(row=row, column=0, sticky=tk.W, padx=(0, 10), pady=3)
        widget.grid(row=row, column=1, columnspan=col_span, sticky=tk.EW, pady=3)


class ConfigEntry(ttk.Frame):
    """带标签的配置输入框"""

    def __init__(self, parent, label: str, default: str = "",
                 width: int = 40, show: str = None):
        super().__init__(parent)
        self.columnconfigure(1, weight=1)

        ttk.Label(self, text=label, width=15, anchor=tk.W).grid(row=0, column=0, padx=(0, 10))
        self.var = tk.StringVar(value=default)
        self.entry = ttk.Entry(self, textvariable=self.var, width=width, show=show)
        self.entry.grid(row=0, column=1, sticky=tk.EW)

    def get(self) -> str:
        return self.var.get()

    def set(self, value: str):
        self.var.set(value)


class ActionButton(ttk.Button):
    """统一风格的按钮"""

    def __init__(self, parent, text: str, command: Callable,
                 style: str = ""):
        super().__init__(parent, text=text, command=command)
        if style:
            self.configure(style=style)


class ToggleButton(ttk.Frame):
    """开关按钮"""

    def __init__(self, parent, text: str, default: bool = False,
                 on_change: Optional[Callable] = None):
        super().__init__(parent)
        self.on_change = on_change
        self.var = tk.BooleanVar(value=default)

        ttk.Label(self, text=text, width=15, anchor=tk.W).pack(side=tk.LEFT, padx=(0, 10))
        self.cb = ttk.Checkbutton(self, variable=self.var, command=self._on_change)
        self.cb.pack(side=tk.LEFT)

    def _on_change(self):
        if self.on_change:
            self.on_change(self.var.get())

    def get(self) -> bool:
        return self.var.get()

    def set(self, value: bool):
        self.var.set(value)


class ApiKeyEntry(ttk.Frame):
    """API Key 输入框（带显示/隐藏切换）"""

    def __init__(self, parent, label: str, default: str = ""):
        super().__init__(parent)
        self.columnconfigure(1, weight=1)

        ttk.Label(self, text=label, width=15, anchor=tk.W).grid(row=0, column=0, padx=(0, 10))
        self.var = tk.StringVar(value=default)
        self.entry = ttk.Entry(self, textvariable=self.var, width=40, show="*")
        self.entry.grid(row=0, column=1, sticky=tk.EW, padx=(0, 5))

        self.show_var = tk.BooleanVar(value=False)
        self.toggle_btn = ttk.Checkbutton(self, text="显示", variable=self.show_var,
                                          command=self._toggle_show)
        self.toggle_btn.grid(row=0, column=2)

    def _toggle_show(self):
        self.entry.configure(show="" if self.show_var.get() else "*")

    def get(self) -> str:
        return self.var.get()

    def set(self, value: str):
        self.var.set(value)