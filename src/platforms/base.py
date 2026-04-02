"""
Platform Abstraction Layer

支持多平台的统一抽象接口：
- qodercli: 通过 hooks.yaml 触发
- qoder GUI: 通过 settings.json Hook 触发
- openclaw: 通过 API 或文件监控触发
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional
import json
import os
import sys


class PlatformType(Enum):
    """支持的平台类型"""
    QODER_CLI = "qodercli"
    QODER_GUI = "qoder"
    OPENCLAW = "openclaw"
    UNKNOWN = "unknown"


@dataclass
class MemoryEvent:
    """记忆事件 - 平台无关的事件模型"""
    event_type: str  # "user_message", "assistant_message", "session_end"
    content: str
    session_id: Optional[str] = None
    timestamp: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # 原始数据（调试用）
    raw_data: Optional[Dict[str, Any]] = None
    
    def is_meaningful(self) -> bool:
        """判断是否有意义的内容（非空、非系统消息等）"""
        if not self.content or len(self.content.strip()) < 10:
            return False
        # 过滤系统消息
        system_keywords = ["system", "error", "timeout"]
        if any(kw in self.content.lower() for kw in system_keywords):
            return False
        return True


class PlatformAdapter(ABC):
    """平台适配器基类"""
    
    @property
    @abstractmethod
    def platform_type(self) -> PlatformType:
        """返回平台类型"""
        pass
    
    @property
    @abstractmethod
    def name(self) -> str:
        """返回平台名称"""
        pass
    
    @abstractmethod
    def get_session_id(self) -> Optional[str]:
        """获取当前会话 ID"""
        pass
    
    @abstractmethod
    def get_transcript_path(self) -> Optional[Path]:
        """获取 transcript 文件路径"""
        pass
    
    @abstractmethod
    def parse_input(self, input_data: Any) -> List[MemoryEvent]:
        """解析输入数据为事件列表"""
        pass
    
    def get_config_path(self) -> Optional[Path]:
        """获取平台配置文件路径"""
        return None
    
    def is_available(self) -> bool:
        """检查平台是否可用"""
        return True


class QoderCLIAdapter(PlatformAdapter):
    """qodercli 适配器
    
    qodercli 通过 hooks.yaml 配置，使用 stdin 传递 JSON 数据：
    {"session_id": "xxx", "prompt": "用户消息"}
    """
    
    def __init__(self):
        self._stdin_data: Optional[Dict] = None
    
    @property
    def platform_type(self) -> PlatformType:
        return PlatformType.QODER_CLI
    
    @property
    def name(self) -> str:
        return "qodercli"
    
    def get_session_id(self) -> Optional[str]:
        if self._stdin_data:
            return self._stdin_data.get("session_id")
        return os.environ.get("QODER_SESSION_ID")
    
    def get_transcript_path(self) -> Optional[Path]:
        # qodercli 的 transcript 存储在 ~/.qoder/projects/<project>/<session>.jsonl
        session_id = self.get_session_id()
        if session_id:
            # 尝试从环境变量获取项目路径
            cwd = os.environ.get("QODER_CWD", os.getcwd())
            project_hash = cwd.replace("/", "-").lstrip("-")
            base_path = Path.home() / ".qoder" / "projects" / f"-{project_hash}"
            if base_path.exists():
                return base_path / f"{session_id}.jsonl"
        return None
    
    def get_config_path(self) -> Optional[Path]:
        return Path.home() / ".qoder" / "hooks.yaml"
    
    def parse_input(self, input_data: Any) -> List[MemoryEvent]:
        """解析 stdin JSON 输入"""
        events = []
        
        if isinstance(input_data, str):
            try:
                self._stdin_data = json.loads(input_data)
            except json.JSONDecodeError:
                # 可能是行分隔的 JSONL
                for line in input_data.strip().split("\n"):
                    if line.strip():
                        try:
                            data = json.loads(line)
                            events.extend(self._parse_data(data))
                        except:
                            pass
                return events
        else:
            self._stdin_data = input_data
        
        if self._stdin_data:
            events.extend(self._parse_data(self._stdin_data))
        
        return events
    
    def _parse_data(self, data: Dict) -> List[MemoryEvent]:
        """解析单个数据对象"""
        events = []
        
        # UserPromptSubmit 事件
        if "prompt" in data:
            events.append(MemoryEvent(
                event_type="user_message",
                content=data["prompt"],
                session_id=data.get("session_id"),
                metadata={"source": "stdin"},
                raw_data=data
            ))
        
        # session_id 单独传递
        if "session_id" in data and not events:
            events.append(MemoryEvent(
                event_type="session_start",
                content="",
                session_id=data["session_id"],
                metadata={"source": "stdin"},
                raw_data=data
            ))
        
        return events
    
    def is_available(self) -> bool:
        """检查是否在 qodercli 环境中运行"""
        # 检查环境变量或 stdin
        return (
            os.environ.get("QODER_SESSION_ID") is not None or
            not sys.stdin.isatty()
        )


class QoderGUIAdapter(PlatformAdapter):
    """Qoder GUI 适配器
    
    Qoder GUI 通过 settings.json 配置 Hook，使用 stdin 传递 JSON 数据
    """
    
    def __init__(self):
        self._stdin_data: Optional[Dict] = None
    
    @property
    def platform_type(self) -> PlatformType:
        return PlatformType.QODER_GUI
    
    @property
    def name(self) -> str:
        return "qoder"
    
    def get_session_id(self) -> Optional[str]:
        if self._stdin_data:
            return self._stdin_data.get("session_id")
        return None
    
    def get_transcript_path(self) -> Optional[Path]:
        # Qoder GUI 的 transcript 存储位置
        base = Path.home() / "Library" / "Application Support" / "Qoder"
        if base.exists():
            # 查找最新的 session
            # TODO: 实现更精确的查找逻辑
            pass
        return None
    
    def get_config_path(self) -> Optional[Path]:
        return Path.home() / "Library" / "Application Support" / "Qoder" / "User" / "settings.json"
    
    def parse_input(self, input_data: Any) -> List[MemoryEvent]:
        """解析 stdin JSON 输入（与 CLI 格式相同）"""
        events = []
        
        if isinstance(input_data, str):
            try:
                self._stdin_data = json.loads(input_data)
            except json.JSONDecodeError:
                return events
        else:
            self._stdin_data = input_data
        
        if self._stdin_data:
            # Qoder GUI 使用相同格式
            if "prompt" in self._stdin_data:
                events.append(MemoryEvent(
                    event_type="user_message",
                    content=self._stdin_data["prompt"],
                    session_id=self._stdin_data.get("session_id"),
                    metadata={"source": "stdin"},
                    raw_data=self._stdin_data
                ))
        
        return events
    
    def is_available(self) -> bool:
        """检查是否在 Qoder GUI 环境中"""
        config_path = self.get_config_path()
        return config_path.exists() if config_path else False


class OpenClawAdapter(PlatformAdapter):
    """OpenClaw 适配器
    
    OpenClaw 可能通过以下方式集成：
    1. 直接调用 Python API
    2. HTTP API 触发
    3. 文件监控（监控 transcript.jsonl）
    """
    
    def __init__(self, api_endpoint: Optional[str] = None):
        self.api_endpoint = api_endpoint or os.environ.get("OPENCLAW_API_ENDPOINT")
        self._transcript_path: Optional[Path] = None
    
    @property
    def platform_type(self) -> PlatformType:
        return PlatformType.OPENCLAW
    
    @property
    def name(self) -> str:
        return "openclaw"
    
    def get_session_id(self) -> Optional[str]:
        return os.environ.get("OPENCLAW_SESSION_ID")
    
    def get_transcript_path(self) -> Optional[Path]:
        if self._transcript_path:
            return self._transcript_path
        return Path(os.environ.get("OPENCLAW_TRANSCRIPT_PATH", ""))
    
    def set_transcript_path(self, path: Path):
        """设置 transcript 路径"""
        self._transcript_path = path
    
    def parse_input(self, input_data: Any) -> List[MemoryEvent]:
        """解析 OpenClaw 格式的输入
        
        OpenClaw transcript 格式可能不同，需要适配
        """
        events = []
        
        if isinstance(input_data, str):
            try:
                data = json.loads(input_data)
                events.extend(self._parse_openclaw_format(data))
            except json.JSONDecodeError:
                # 可能是 JSONL 格式
                for line in input_data.strip().split("\n"):
                    if line.strip():
                        try:
                            data = json.loads(line)
                            events.extend(self._parse_openclaw_format(data))
                        except:
                            pass
        elif isinstance(input_data, dict):
            events.extend(self._parse_openclaw_format(input_data))
        elif isinstance(input_data, list):
            for item in input_data:
                events.extend(self._parse_openclaw_format(item))
        
        return events
    
    def _parse_openclaw_format(self, data: Dict) -> List[MemoryEvent]:
        """解析 OpenClaw 特定格式"""
        events = []
        
        # OpenClaw 可能的格式（需要根据实际情况调整）
        if "content" in data:
            events.append(MemoryEvent(
                event_type=data.get("type", "message"),
                content=data["content"],
                session_id=data.get("session_id"),
                timestamp=data.get("timestamp"),
                metadata={"source": "openclaw"},
                raw_data=data
            ))
        elif "message" in data:
            events.append(MemoryEvent(
                event_type="message",
                content=data["message"],
                session_id=data.get("session_id"),
                metadata={"source": "openclaw"},
                raw_data=data
            ))
        
        return events
    
    def is_available(self) -> bool:
        """检查 OpenClaw 是否可用"""
        return (
            os.environ.get("OPENCLAW_SESSION_ID") is not None or
            self.api_endpoint is not None or
            self.get_transcript_path() is not None
        )
