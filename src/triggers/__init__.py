"""
Trigger Mechanism Abstraction

提供统一的触发机制接口
"""

from .base import (
    Trigger,
    StdinTrigger,
    FileWatcherTrigger,
    APITrigger,
)

__all__ = [
    "Trigger",
    "StdinTrigger",
    "FileWatcherTrigger",
    "APITrigger",
]
