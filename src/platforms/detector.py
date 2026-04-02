"""
Platform Auto-Detection

自动检测当前运行环境，返回对应的平台适配器
"""

import os
import sys
from pathlib import Path
from typing import Optional

from .base import (
    PlatformAdapter,
    PlatformType,
    QoderCLIAdapter,
    QoderGUIAdapter,
    OpenClawAdapter,
)


def detect_platform() -> PlatformType:
    """自动检测当前平台
    
    检测优先级：
    1. 环境变量显式指定
    2. Qoder CLI 标志
    3. Qoder GUI 标志
    4. OpenClaw 标志
    5. 未知平台
    """
    # 1. 环境变量显式指定
    explicit = os.environ.get("SKILL_MEMORY_PLATFORM", "").lower()
    if explicit:
        platform_map = {
            "qodercli": PlatformType.QODER_CLI,
            "qoder_cli": PlatformType.QODER_CLI,
            "qoder": PlatformType.QODER_GUI,
            "qoder_gui": PlatformType.QODER_GUI,
            "openclaw": PlatformType.OPENCLAW,
        }
        if explicit in platform_map:
            return platform_map[explicit]
    
    # 2. Qoder CLI 标志
    if os.environ.get("QODER_SESSION_ID"):
        return PlatformType.QODER_CLI
    
    # 3. Qoder GUI 标志
    qoder_gui_settings = (
        Path.home() / "Library" / "Application Support" / "Qoder" / "User" / "settings.json"
    )
    if qoder_gui_settings.exists():
        # 可能是 GUI 环境，但需要进一步确认
        pass
    
    # 4. OpenClaw 标志
    if os.environ.get("OPENCLAW_SESSION_ID") or os.environ.get("OPENCLAW_API_ENDPOINT"):
        return PlatformType.OPENCLAW
    
    # 5. 检查 stdin（Hook 触发时 stdin 非空）
    if not sys.stdin.isatty():
        # 有 stdin 输入，可能是 Hook 触发
        # 默认假设是 Qoder CLI
        return PlatformType.QODER_CLI
    
    return PlatformType.UNKNOWN


def get_adapter(platform: Optional[PlatformType] = None) -> PlatformAdapter:
    """获取平台适配器
    
    Args:
        platform: 指定平台类型，默认自动检测
    
    Returns:
        对应的平台适配器实例
    """
    if platform is None:
        platform = detect_platform()
    
    adapters = {
        PlatformType.QODER_CLI: QoderCLIAdapter,
        PlatformType.QODER_GUI: QoderGUIAdapter,
        PlatformType.OPENCLAW: OpenClawAdapter,
    }
    
    adapter_class = adapters.get(platform, QoderCLIAdapter)
    return adapter_class()


def is_hook_context() -> bool:
    """判断是否在 Hook 上下文中运行
    
    Hook 上下文特征：
    - stdin 非空（有数据传入）
    - 通过环境变量传递了 session_id
    """
    return (
        not sys.stdin.isatty() or
        os.environ.get("QODER_SESSION_ID") is not None or
        os.environ.get("OPENCLAW_SESSION_ID") is not None
    )


def get_platform_info() -> dict:
    """获取平台信息（调试用）"""
    platform = detect_platform()
    adapter = get_adapter(platform)
    
    return {
        "platform": platform.value,
        "adapter": adapter.name,
        "is_hook_context": is_hook_context(),
        "session_id": adapter.get_session_id(),
        "transcript_path": str(adapter.get_transcript_path()) if adapter.get_transcript_path() else None,
        "config_path": str(adapter.get_config_path()) if adapter.get_config_path() else None,
        "available": adapter.is_available(),
    }
