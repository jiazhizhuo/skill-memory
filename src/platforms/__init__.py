"""
Platform Abstraction Layer

提供跨平台的统一接口
"""

from .base import (
    PlatformAdapter,
    PlatformType,
    MemoryEvent,
    QoderCLIAdapter,
    QoderGUIAdapter,
    OpenClawAdapter,
)
from .detector import (
    detect_platform,
    get_adapter,
    is_hook_context,
    get_platform_info,
)

__all__ = [
    # 基类
    "PlatformAdapter",
    "PlatformType",
    "MemoryEvent",
    # 具体实现
    "QoderCLIAdapter",
    "QoderGUIAdapter",
    "OpenClawAdapter",
    # 检测器
    "detect_platform",
    "get_adapter",
    "is_hook_context",
    "get_platform_info",
]
