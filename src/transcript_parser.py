"""
Transcript 解析器
支持解析 Qoder 和 OpenClaw 的 transcript.jsonl 格式
"""

import json
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Optional, Union, Dict, Any
from datetime import datetime


@dataclass
class ContentBlock:
    """消息内容块"""
    type: str  # "text" | "toolCall" | "toolResult"
    text: Optional[str] = None
    name: Optional[str] = None
    arguments: Optional[Dict[str, Any]] = None
    tool_use_id: Optional[str] = None

    @staticmethod
    def from_dict(data: Union[Dict, str]) -> "ContentBlock":
        """从字典创建"""
        if isinstance(data, str):
            return ContentBlock(type="text", text=data)
        return ContentBlock(
            type=data.get("type", "text"),
            text=data.get("text"),
            name=data.get("name"),
            arguments=data.get("arguments"),
            tool_use_id=data.get("tool_use_id"),
        )


@dataclass
class Message:
    """对话消息"""
    role: str  # "user" | "assistant" | "system" | "tool"
    content: Union[str, List[ContentBlock]]
    model: Optional[str] = None
    timestamp: Optional[str] = None
    tool_calls: Optional[List[Dict]] = None

    def get_text_content(self) -> str:
        """获取纯文本内容"""
        if isinstance(self.content, str):
            return self.content

        text_parts = []
        for block in self.content:
            if isinstance(block, ContentBlock):
                if block.type == "text" and block.text:
                    text_parts.append(block.text)
                elif block.type == "toolCall" and block.name:
                    text_parts.append(f"[使用工具: {block.name}]")
            elif isinstance(block, dict):
                if block.get("type") == "text":
                    text_parts.append(block.get("text", ""))
                elif block.get("type") == "toolCall":
                    text_parts.append(f"[使用工具: {block.get('name', 'unknown')}]")
        return "\n".join(text_parts)

    def is_meaningful(self, min_length: int = 20) -> bool:
        """判断消息是否有意义"""
        text = self.get_text_content()
        return len(text.strip()) >= min_length


@dataclass
class DialogueEntry:
    """对话条目（transcript.jsonl 中的单行）"""
    type: str  # "message" | "session" | "system"
    message: Optional[Message] = None
    metadata: Optional[Dict[str, Any]] = None
    timestamp: Optional[str] = None


class TranscriptParser:
    """
    Transcript 解析器
    支持 Qoder 和 OpenClaw 格式
    """

    # 支持的格式
    SUPPORTED_FORMATS = ["qoder", "openclaw", "generic"]

    def __init__(self):
        self.format = None

    def detect_format(self, first_line: str) -> str:
        """检测格式"""
        try:
            data = json.loads(first_line)
            if "type" in data:
                if data.get("type") == "message" and "message" in data:
                    return "openclaw"
                elif "role" in data:
                    return "qoder"
                elif "message" in data:
                    return "qoder"
            return "generic"
        except json.JSONDecodeError:
            return "generic"

    def parse_file(self, file_path: str) -> List[DialogueEntry]:
        """
        解析 transcript.jsonl 文件

        Args:
            file_path: 文件路径

        Returns:
            对话条目列表
        """
        entries = []
        path = Path(file_path)

        if not path.exists():
            raise FileNotFoundError(f"Transcript file not found: {file_path}")

        with open(path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        if not lines:
            return []

        # 检测格式
        self.format = self.detect_format(lines[0].strip())

        for line in lines:
            line = line.strip()
            if not line:
                continue

            try:
                entry = self._parse_line(line)
                if entry:
                    entries.append(entry)
            except json.JSONDecodeError:
                continue

        return entries

    def _parse_line(self, line: str) -> Optional[DialogueEntry]:
        """解析单行"""
        data = json.loads(line)

        if self.format == "openclaw":
            return self._parse_openclaw(data)
        elif self.format == "qoder":
            return self._parse_qoder(data)
        else:
            return self._parse_generic(data)

    def _parse_openclaw(self, data: Dict) -> Optional[DialogueEntry]:
        """解析 OpenClaw 格式"""
        if data.get("type") == "message":
            msg_data = data.get("message", {})
            role = msg_data.get("role", "")

            if role not in ["user", "assistant", "system", "tool"]:
                return None

            content = msg_data.get("content", "")
            if isinstance(content, list):
                content_blocks = [ContentBlock.from_dict(c) for c in content]
            else:
                content_blocks = [ContentBlock(type="text", text=content)]

            message = Message(
                role=role,
                content=content_blocks,
                model=msg_data.get("model"),
                timestamp=msg_data.get("timestamp"),
            )

            return DialogueEntry(
                type="message",
                message=message,
                metadata={"format": "openclaw"},
            )

        return None

    def _parse_qoder(self, data: Dict) -> Optional[DialogueEntry]:
        """解析 Qoder 格式"""
        # Qoder 格式:
        # {"type": "user"|"assistant", "message": {"role": "...", "content": [...]}}
        # 或 {"type": "message", "message": {...}}

        # 优先取顶层 type
        top_type = data.get("type", "")

        # 获取 message 对象
        if "message" in data:
            msg_data = data.get("message", {})
        else:
            msg_data = data

        # 确定 role：优先用顶层的 type，其次用 message.role
        role = top_type if top_type in ["user", "assistant", "system", "tool"] else msg_data.get("role", "")

        if role not in ["user", "assistant", "system", "tool"]:
            return None

        content = msg_data.get("content", "")
        if isinstance(content, list):
            # 过滤掉 thinking 类型，只保留 text
            content_blocks = []
            for c in content:
                if isinstance(c, dict) and c.get("type") == "text":
                    content_blocks.append(ContentBlock.from_dict(c))
            if not content_blocks:
                content_blocks = [ContentBlock(type="text", text=str(content))]
        else:
            content_blocks = [ContentBlock(type="text", text=content)]

        message = Message(
            role=role,
            content=content_blocks,
            model=msg_data.get("model"),
            timestamp=msg_data.get("timestamp") or data.get("timestamp"),
        )

        return DialogueEntry(
            type="message",
            message=message,
            metadata={"format": "qoder", "sessionId": data.get("sessionId")},
        )

    def _parse_generic(self, data: Dict) -> Optional[DialogueEntry]:
        """解析通用格式"""
        role = data.get("role", data.get("type", ""))
        content = data.get("content", data.get("text", ""))

        if not role:
            return None

        message = Message(
            role=role,
            content=content,
        )

        return DialogueEntry(
            type="message",
            message=message,
        )

    def extract_messages(
        self,
        entries: List[DialogueEntry],
        roles: Optional[List[str]] = None,
    ) -> List[Message]:
        """
        从条目中提取消息

        Args:
            entries: 对话条目
            roles: 过滤的角色，None 表示全部

        Returns:
            消息列表
        """
        if roles is None:
            roles = ["user", "assistant"]

        messages = []
        for entry in entries:
            if entry.message and entry.message.role in roles:
                messages.append(entry.message)

        return messages

    def to_memory_format(
        self,
        entries: List[DialogueEntry],
        max_turns: int = 50,
        include_tools: bool = False,
    ) -> str:
        """
        转换为可导入的记忆格式

        Args:
            entries: 对话条目
            max_turns: 最大对话轮数
            include_tools: 是否包含工具调用

        Returns:
            格式化后的文本
        """
        messages = self.extract_messages(entries)
        recent = messages[-max_turns:] if len(messages) > max_turns else messages

        lines = []
        for msg in recent:
            if not msg.is_meaningful():
                continue

            role = msg.role.upper()
            content = msg.get_text_content()

            if content.strip():
                lines.append(f"**{role}**: {content}")

        return "\n\n".join(lines)

    def summarize_conversation(
        self,
        entries: List[DialogueEntry],
        max_turns: int = 20,
    ) -> str:
        """
        生成对话摘要（简化版本）

        Args:
            entries: 对话条目
            max_turns: 用于摘要的最大轮数

        Returns:
            摘要文本
        """
        messages = self.extract_messages(entries, roles=["user", "assistant"])
        recent = messages[-max_turns:] if len(messages) > max_turns else messages

        # 简单摘要：取用户消息
        user_messages = [m.get_text_content() for m in recent if m.role == "user"]
        summary = "\n".join(f"- {msg[:200]}" for msg in user_messages[-10:] if msg.strip())

        return summary or "No meaningful conversation found"

    def get_statistics(self, entries: List[DialogueEntry]) -> Dict[str, Any]:
        """获取对话统计"""
        messages = self.extract_messages(entries)

        stats = {
            "total_messages": len(messages),
            "user_messages": len([m for m in messages if m.role == "user"]),
            "assistant_messages": len([m for m in messages if m.role == "assistant"]),
            "tool_messages": len([m for m in messages if m.role == "tool"]),
            "format": self.format or "unknown",
        }

        # 计算总 token（近似）
        total_chars = sum(len(m.get_text_content()) for m in messages)
        stats["total_chars"] = total_chars
        stats["estimated_tokens"] = total_chars // 4

        return stats
"""
Transcript 解析器
支持解析 Qoder 和 OpenClaw 的 transcript.jsonl 格式
"""

import json
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Optional, Union, Dict, Any
from datetime import datetime


@dataclass
class ContentBlock:
    """消息内容块"""
    type: str  # "text" | "toolCall" | "toolResult"
    text: Optional[str] = None
    name: Optional[str] = None
    arguments: Optional[Dict[str, Any]] = None
    tool_use_id: Optional[str] = None

    @staticmethod
    def from_dict(data: Union[Dict, str]) -> "ContentBlock":
        """从字典创建"""
        if isinstance(data, str):
            return ContentBlock(type="text", text=data)
        return ContentBlock(
            type=data.get("type", "text"),
            text=data.get("text"),
            name=data.get("name"),
            arguments=data.get("arguments"),
            tool_use_id=data.get("tool_use_id"),
        )


@dataclass
class Message:
    """对话消息"""
    role: str  # "user" | "assistant" | "system" | "tool"
    content: Union[str, List[ContentBlock]]
    model: Optional[str] = None
    timestamp: Optional[str] = None
    tool_calls: Optional[List[Dict]] = None

    def get_text_content(self) -> str:
        """获取纯文本内容"""
        if isinstance(self.content, str):
            return self.content

        text_parts = []
        for block in self.content:
            if isinstance(block, ContentBlock):
                if block.type == "text" and block.text:
                    text_parts.append(block.text)
                elif block.type == "toolCall" and block.name:
                    text_parts.append(f"[使用工具: {block.name}]")
            elif isinstance(block, dict):
                if block.get("type") == "text":
                    text_parts.append(block.get("text", ""))
                elif block.get("type") == "toolCall":
                    text_parts.append(f"[使用工具: {block.get('name', 'unknown')}]")
        return "\n".join(text_parts)

    def is_meaningful(self, min_length: int = 20) -> bool:
        """判断消息是否有意义"""
        text = self.get_text_content()
        return len(text.strip()) >= min_length


@dataclass
class DialogueEntry:
    """对话条目（transcript.jsonl 中的单行）"""
    type: str  # "message" | "session" | "system"
    message: Optional[Message] = None
    metadata: Optional[Dict[str, Any]] = None
    timestamp: Optional[str] = None


class TranscriptParser:
    """
    Transcript 解析器
    支持 Qoder 和 OpenClaw 格式
    """

    # 支持的格式
    SUPPORTED_FORMATS = ["qoder", "openclaw", "generic"]

    def __init__(self):
        self.format = None

    def detect_format(self, first_line: str) -> str:
        """检测格式"""
        try:
            data = json.loads(first_line)
            if "type" in data:
                if data.get("type") == "message" and "message" in data:
                    return "openclaw"
                elif "role" in data:
                    return "qoder"
                elif "message" in data:
                    return "qoder"
            return "generic"
        except json.JSONDecodeError:
            return "generic"

    def parse_file(self, file_path: str) -> List[DialogueEntry]:
        """
        解析 transcript.jsonl 文件

        Args:
            file_path: 文件路径

        Returns:
            对话条目列表
        """
        entries = []
        path = Path(file_path)

        if not path.exists():
            raise FileNotFoundError(f"Transcript file not found: {file_path}")

        with open(path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        if not lines:
            return []

        # 检测格式
        self.format = self.detect_format(lines[0].strip())

        for line in lines:
            line = line.strip()
            if not line:
                continue

            try:
                entry = self._parse_line(line)
                if entry:
                    entries.append(entry)
            except json.JSONDecodeError:
                continue

        return entries

    def _parse_line(self, line: str) -> Optional[DialogueEntry]:
        """解析单行"""
        data = json.loads(line)

        if self.format == "openclaw":
            return self._parse_openclaw(data)
        elif self.format == "qoder":
            return self._parse_qoder(data)
        else:
            return self._parse_generic(data)

    def _parse_openclaw(self, data: Dict) -> Optional[DialogueEntry]:
        """解析 OpenClaw 格式"""
        if data.get("type") == "message":
            msg_data = data.get("message", {})
            role = msg_data.get("role", "")

            if role not in ["user", "assistant", "system", "tool"]:
                return None

            content = msg_data.get("content", "")
            if isinstance(content, list):
                content_blocks = [ContentBlock.from_dict(c) for c in content]
            else:
                content_blocks = [ContentBlock(type="text", text=content)]

            message = Message(
                role=role,
                content=content_blocks,
                model=msg_data.get("model"),
                timestamp=msg_data.get("timestamp"),
            )

            return DialogueEntry(
                type="message",
                message=message,
                metadata={"format": "openclaw"},
            )

        return None

    def _parse_qoder(self, data: Dict) -> Optional[DialogueEntry]:
        """解析 Qoder 格式"""
        # Qoder 格式:
        # {"type": "user"|"assistant", "message": {"role": "...", "content": [...]}}
        # 或 {"type": "message", "message": {...}}

        # 优先取顶层 type
        top_type = data.get("type", "")

        # 获取 message 对象
        if "message" in data:
            msg_data = data.get("message", {})
        else:
            msg_data = data

        # 确定 role：优先用顶层的 type，其次用 message.role
        role = top_type if top_type in ["user", "assistant", "system", "tool"] else msg_data.get("role", "")

        if role not in ["user", "assistant", "system", "tool"]:
            return None

        content = msg_data.get("content", "")
        if isinstance(content, list):
            # 过滤掉 thinking 类型，只保留 text
            content_blocks = []
            for c in content:
                if isinstance(c, dict) and c.get("type") == "text":
                    content_blocks.append(ContentBlock.from_dict(c))
            if not content_blocks:
                content_blocks = [ContentBlock(type="text", text=str(content))]
        else:
            content_blocks = [ContentBlock(type="text", text=content)]

        message = Message(
            role=role,
            content=content_blocks,
            model=msg_data.get("model"),
            timestamp=msg_data.get("timestamp") or data.get("timestamp"),
        )

        return DialogueEntry(
            type="message",
            message=message,
            metadata={"format": "qoder", "sessionId": data.get("sessionId")},
        )

    def _parse_generic(self, data: Dict) -> Optional[DialogueEntry]:
        """解析通用格式"""
        role = data.get("role", data.get("type", ""))
        content = data.get("content", data.get("text", ""))

        if not role:
            return None

        message = Message(
            role=role,
            content=content,
        )

        return DialogueEntry(
            type="message",
            message=message,
        )

    def extract_messages(
        self,
        entries: List[DialogueEntry],
        roles: Optional[List[str]] = None,
    ) -> List[Message]:
        """
        从条目中提取消息

        Args:
            entries: 对话条目
            roles: 过滤的角色，None 表示全部

        Returns:
            消息列表
        """
        if roles is None:
            roles = ["user", "assistant"]

        messages = []
        for entry in entries:
            if entry.message and entry.message.role in roles:
                messages.append(entry.message)

        return messages

    def to_memory_format(
        self,
        entries: List[DialogueEntry],
        max_turns: int = 50,
        include_tools: bool = False,
    ) -> str:
        """
        转换为可导入的记忆格式

        Args:
            entries: 对话条目
            max_turns: 最大对话轮数
            include_tools: 是否包含工具调用

        Returns:
            格式化后的文本
        """
        messages = self.extract_messages(entries)
        recent = messages[-max_turns:] if len(messages) > max_turns else messages

        lines = []
        for msg in recent:
            if not msg.is_meaningful():
                continue

            role = msg.role.upper()
            content = msg.get_text_content()

            if content.strip():
                lines.append(f"**{role}**: {content}")

        return "\n\n".join(lines)

    def summarize_conversation(
        self,
        entries: List[DialogueEntry],
        max_turns: int = 20,
    ) -> str:
        """
        生成对话摘要（简化版本）

        Args:
            entries: 对话条目
            max_turns: 用于摘要的最大轮数

        Returns:
            摘要文本
        """
        messages = self.extract_messages(entries, roles=["user", "assistant"])
        recent = messages[-max_turns:] if len(messages) > max_turns else messages

        # 简单摘要：取用户消息
        user_messages = [m.get_text_content() for m in recent if m.role == "user"]
        summary = "\n".join(f"- {msg[:200]}" for msg in user_messages[-10:] if msg.strip())

        return summary or "No meaningful conversation found"

    def get_statistics(self, entries: List[DialogueEntry]) -> Dict[str, Any]:
        """获取对话统计"""
        messages = self.extract_messages(entries)

        stats = {
            "total_messages": len(messages),
            "user_messages": len([m for m in messages if m.role == "user"]),
            "assistant_messages": len([m for m in messages if m.role == "assistant"]),
            "tool_messages": len([m for m in messages if m.role == "tool"]),
            "format": self.format or "unknown",
        }

        # 计算总 token（近似）
        total_chars = sum(len(m.get_text_content()) for m in messages)
        stats["total_chars"] = total_chars
        stats["estimated_tokens"] = total_chars // 4

        return stats
"""
Transcript 解析器
支持解析 Qoder 和 OpenClaw 的 transcript.jsonl 格式
"""

import json
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Optional, Union, Dict, Any
from datetime import datetime


@dataclass
class ContentBlock:
    """消息内容块"""
    type: str  # "text" | "toolCall" | "toolResult"
    text: Optional[str] = None
    name: Optional[str] = None
    arguments: Optional[Dict[str, Any]] = None
    tool_use_id: Optional[str] = None

    @staticmethod
    def from_dict(data: Union[Dict, str]) -> "ContentBlock":
        """从字典创建"""
        if isinstance(data, str):
            return ContentBlock(type="text", text=data)
        return ContentBlock(
            type=data.get("type", "text"),
            text=data.get("text"),
            name=data.get("name"),
            arguments=data.get("arguments"),
            tool_use_id=data.get("tool_use_id"),
        )


@dataclass
class Message:
    """对话消息"""
    role: str  # "user" | "assistant" | "system" | "tool"
    content: Union[str, List[ContentBlock]]
    model: Optional[str] = None
    timestamp: Optional[str] = None
    tool_calls: Optional[List[Dict]] = None

    def get_text_content(self) -> str:
        """获取纯文本内容"""
        if isinstance(self.content, str):
            return self.content

        text_parts = []
        for block in self.content:
            if isinstance(block, ContentBlock):
                if block.type == "text" and block.text:
                    text_parts.append(block.text)
                elif block.type == "toolCall" and block.name:
                    text_parts.append(f"[使用工具: {block.name}]")
            elif isinstance(block, dict):
                if block.get("type") == "text":
                    text_parts.append(block.get("text", ""))
                elif block.get("type") == "toolCall":
                    text_parts.append(f"[使用工具: {block.get('name', 'unknown')}]")
        return "\n".join(text_parts)

    def is_meaningful(self, min_length: int = 20) -> bool:
        """判断消息是否有意义"""
        text = self.get_text_content()
        return len(text.strip()) >= min_length


@dataclass
class DialogueEntry:
    """对话条目（transcript.jsonl 中的单行）"""
    type: str  # "message" | "session" | "system"
    message: Optional[Message] = None
    metadata: Optional[Dict[str, Any]] = None
    timestamp: Optional[str] = None


class TranscriptParser:
    """
    Transcript 解析器
    支持 Qoder 和 OpenClaw 格式
    """

    # 支持的格式
    SUPPORTED_FORMATS = ["qoder", "openclaw", "generic"]

    def __init__(self):
        self.format = None

    def detect_format(self, first_line: str) -> str:
        """检测格式"""
        try:
            data = json.loads(first_line)
            if "type" in data:
                if data.get("type") == "message" and "message" in data:
                    return "openclaw"
                elif "role" in data:
                    return "qoder"
                elif "message" in data:
                    return "qoder"
            return "generic"
        except json.JSONDecodeError:
            return "generic"

    def parse_file(self, file_path: str) -> List[DialogueEntry]:
        """
        解析 transcript.jsonl 文件

        Args:
            file_path: 文件路径

        Returns:
            对话条目列表
        """
        entries = []
        path = Path(file_path)

        if not path.exists():
            raise FileNotFoundError(f"Transcript file not found: {file_path}")

        with open(path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        if not lines:
            return []

        # 检测格式
        self.format = self.detect_format(lines[0].strip())

        for line in lines:
            line = line.strip()
            if not line:
                continue

            try:
                entry = self._parse_line(line)
                if entry:
                    entries.append(entry)
            except json.JSONDecodeError:
                continue

        return entries

    def _parse_line(self, line: str) -> Optional[DialogueEntry]:
        """解析单行"""
        data = json.loads(line)

        if self.format == "openclaw":
            return self._parse_openclaw(data)
        elif self.format == "qoder":
            return self._parse_qoder(data)
        else:
            return self._parse_generic(data)

    def _parse_openclaw(self, data: Dict) -> Optional[DialogueEntry]:
        """解析 OpenClaw 格式"""
        if data.get("type") == "message":
            msg_data = data.get("message", {})
            role = msg_data.get("role", "")

            if role not in ["user", "assistant", "system", "tool"]:
                return None

            content = msg_data.get("content", "")
            if isinstance(content, list):
                content_blocks = [ContentBlock.from_dict(c) for c in content]
            else:
                content_blocks = [ContentBlock(type="text", text=content)]

            message = Message(
                role=role,
                content=content_blocks,
                model=msg_data.get("model"),
                timestamp=msg_data.get("timestamp"),
            )

            return DialogueEntry(
                type="message",
                message=message,
                metadata={"format": "openclaw"},
            )

        return None

    def _parse_qoder(self, data: Dict) -> Optional[DialogueEntry]:
        """解析 Qoder 格式"""
        # Qoder 格式:
        # {"type": "user"|"assistant", "message": {"role": "...", "content": [...]}}
        # 或 {"type": "message", "message": {...}}

        # 优先取顶层 type
        top_type = data.get("type", "")

        # 获取 message 对象
        if "message" in data:
            msg_data = data.get("message", {})
        else:
            msg_data = data

        # 确定 role：优先用顶层的 type，其次用 message.role
        role = top_type if top_type in ["user", "assistant", "system", "tool"] else msg_data.get("role", "")

        if role not in ["user", "assistant", "system", "tool"]:
            return None

        content = msg_data.get("content", "")
        if isinstance(content, list):
            # 过滤掉 thinking 类型，只保留 text
            content_blocks = []
            for c in content:
                if isinstance(c, dict) and c.get("type") == "text":
                    content_blocks.append(ContentBlock.from_dict(c))
            if not content_blocks:
                content_blocks = [ContentBlock(type="text", text=str(content))]
        else:
            content_blocks = [ContentBlock(type="text", text=content)]

        message = Message(
            role=role,
            content=content_blocks,
            model=msg_data.get("model"),
            timestamp=msg_data.get("timestamp") or data.get("timestamp"),
        )

        return DialogueEntry(
            type="message",
            message=message,
            metadata={"format": "qoder", "sessionId": data.get("sessionId")},
        )

    def _parse_generic(self, data: Dict) -> Optional[DialogueEntry]:
        """解析通用格式"""
        role = data.get("role", data.get("type", ""))
        content = data.get("content", data.get("text", ""))

        if not role:
            return None

        message = Message(
            role=role,
            content=content,
        )

        return DialogueEntry(
            type="message",
            message=message,
        )

    def extract_messages(
        self,
        entries: List[DialogueEntry],
        roles: Optional[List[str]] = None,
    ) -> List[Message]:
        """
        从条目中提取消息

        Args:
            entries: 对话条目
            roles: 过滤的角色，None 表示全部

        Returns:
            消息列表
        """
        if roles is None:
            roles = ["user", "assistant"]

        messages = []
        for entry in entries:
            if entry.message and entry.message.role in roles:
                messages.append(entry.message)

        return messages

    def to_memory_format(
        self,
        entries: List[DialogueEntry],
        max_turns: int = 50,
        include_tools: bool = False,
    ) -> str:
        """
        转换为可导入的记忆格式

        Args:
            entries: 对话条目
            max_turns: 最大对话轮数
            include_tools: 是否包含工具调用

        Returns:
            格式化后的文本
        """
        messages = self.extract_messages(entries)
        recent = messages[-max_turns:] if len(messages) > max_turns else messages

        lines = []
        for msg in recent:
            if not msg.is_meaningful():
                continue

            role = msg.role.upper()
            content = msg.get_text_content()

            if content.strip():
                lines.append(f"**{role}**: {content}")

        return "\n\n".join(lines)

    def summarize_conversation(
        self,
        entries: List[DialogueEntry],
        max_turns: int = 20,
    ) -> str:
        """
        生成对话摘要（简化版本）

        Args:
            entries: 对话条目
            max_turns: 用于摘要的最大轮数

        Returns:
            摘要文本
        """
        messages = self.extract_messages(entries, roles=["user", "assistant"])
        recent = messages[-max_turns:] if len(messages) > max_turns else messages

        # 简单摘要：取用户消息
        user_messages = [m.get_text_content() for m in recent if m.role == "user"]
        summary = "\n".join(f"- {msg[:200]}" for msg in user_messages[-10:] if msg.strip())

        return summary or "No meaningful conversation found"

    def get_statistics(self, entries: List[DialogueEntry]) -> Dict[str, Any]:
        """获取对话统计"""
        messages = self.extract_messages(entries)

        stats = {
            "total_messages": len(messages),
            "user_messages": len([m for m in messages if m.role == "user"]),
            "assistant_messages": len([m for m in messages if m.role == "assistant"]),
            "tool_messages": len([m for m in messages if m.role == "tool"]),
            "format": self.format or "unknown",
        }

        # 计算总 token（近似）
        total_chars = sum(len(m.get_text_content()) for m in messages)
        stats["total_chars"] = total_chars
        stats["estimated_tokens"] = total_chars // 4

        return stats
