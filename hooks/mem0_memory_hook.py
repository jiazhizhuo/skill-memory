#!/usr/bin/env python3
"""
Qoder Mem0 Memory Hook

配置驱动的记忆保存 Hook，支持多种触发模式。

触发时机：
1. AgentResponseComplete - AI 回复完成时（自动触发）
2. Stop - /stop 命令执行时（手动触发）

配置: ~/.skill-memory/config/hook.toml
"""

import json
import os
import sys
import argparse
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any, List

# 添加 src 到路径
SKILL_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(SKILL_ROOT / "src"))

from config import load_config
from memory_manager import DualLayerMemoryManager
from transcript_parser import TranscriptParser
from hook_config import load_hook_config


class Mem0MemoryHook:
    """
    Memory Hook 实现类
    支持配置驱动的多模式触发
    """

    def __init__(self, config_path: Optional[str] = None):
        self.hook_config = load_hook_config(config_path)
        self.config = load_config()
        self.memory_manager = DualLayerMemoryManager(self.config)
        self.parser = TranscriptParser()

    def detect_mode(self, event_data: Dict) -> str:
        """
        检测触发模式

        Args:
            event_data: Hook 事件数据

        Returns:
            "single" 或 "transcript"
        """
        mode = self.hook_config.hook_mode

        if mode == "auto":
            # 自动检测
            if "user_message" in event_data or "assistant_message" in event_data:
                return "single"
            elif "transcript" in event_data or "transcript_path" in event_data:
                return "transcript"
            else:
                # 默认单条模式
                return "single"
        elif mode in ("single", "agent_response"):
            return "single"
        else:
            return "transcript"

    def parse_event(self, event_data: Dict) -> Dict[str, Any]:
        """
        解析 Hook 事件数据

        AgentResponseComplete 提供的字段：
        - user_message: str (用户消息)
        - assistant_message: str (AI 回复)
        - session_key: str (会话标识)

        Stop 提供的字段：
        - last_assistant_message: str
        - transcript_path: str
        - session_key: str
        - transcript: list (完整 transcript)
        """
        mode = self.detect_mode(event_data)

        if mode == "single":
            return {
                "mode": "single",
                "user_message": event_data.get("user_message", ""),
                "assistant_message": event_data.get("assistant_message", ""),
                "session_key": event_data.get("session_key", "unknown"),
                "timestamp": event_data.get("timestamp", datetime.now().isoformat()),
            }

        # transcript 模式
        return {
            "mode": "transcript",
            "last_message": event_data.get("last_assistant_message", ""),
            "transcript_path": event_data.get("transcript_path", ""),
            "session_key": event_data.get("session_key", "unknown"),
            "timestamp": event_data.get("timestamp", datetime.now().isoformat()),
            "transcript": event_data.get("transcript"),
        }

    def should_save(self, content: str) -> bool:
        """
        判断内容是否值得保存
        """
        min_length = self.hook_config.min_length

        # 跳过太短的内容
        if len(content.strip()) < min_length:
            return False

        # 跳过命令类内容
        skip_patterns = self.hook_config.skip_patterns
        content_lower = content.lower().strip()
        if any(content_lower.startswith(p.lower()) for p in skip_patterns):
            return False

        # 跳过纯 URL
        if content.strip().startswith("http") and len(content.strip()) < 100:
            return False

        return True

    def extract_from_single_message(
        self,
        user_message: str,
        assistant_message: str,
    ) -> List[Dict[str, Any]]:
        """
        从单条消息对提取内容 (AgentResponseComplete 模式)

        Returns:
            [{"content": str, "role": str, "importance": float}, ...]
        """
        results = []
        max_per_round = self.hook_config.max_per_round

        # 组合对话内容
        combined = f"User: {user_message}\n\nAssistant: {assistant_message}"

        if self.should_save(combined):
            importance = self._calculate_importance(combined)
            results.append({
                "content": combined,
                "role": "user+assistant",
                "importance": importance,
            })

        # 如果只有用户消息有意义
        if user_message and self.should_save(user_message) and not results:
            importance = self._calculate_importance(user_message) * 0.8
            results.append({
                "content": user_message,
                "role": "user",
                "importance": importance,
            })

        # 如果只有助手消息有意义
        if assistant_message and self.should_save(assistant_message) and not results:
            importance = self._calculate_importance(assistant_message)
            results.append({
                "content": assistant_message,
                "role": "assistant",
                "importance": importance,
            })

        # 限制条数
        return results[:max_per_round]

    def extract_from_transcript(
        self,
        transcript_path: str,
        max_turns: int = 20,
    ) -> List[Dict[str, Any]]:
        """
        从 transcript 中提取关键信息 (Stop 模式)

        Returns:
            [{"content": str, "role": str, "importance": float}, ...]
        """
        if not transcript_path or not os.path.exists(transcript_path):
            return []

        try:
            entries = self.parser.parse_file(transcript_path)
            messages = self.parser.extract_messages(entries)

            # 取最近的消息
            recent = messages[-max_turns:] if len(messages) > max_turns else messages

            key_contents = []
            for msg in recent:
                content = msg.get_text_content()
                if self.should_save(content):
                    importance = self._calculate_importance(content)
                    key_contents.append({
                        "content": content,
                        "role": msg.role,
                        "importance": importance,
                    })

            # 限制条数
            max_per_round = self.hook_config.max_per_round
            return key_contents[:max_per_round]

        except Exception as e:
            print(f"Error extracting information: {e}", file=sys.stderr)
            return []

    def _calculate_importance(self, content: str) -> float:
        """
        计算内容重要性分数
        """
        importance = 0.5
        content_lower = content.lower()

        # 包含决策/结论 → 提高重要性
        decision_keywords = ["决定", "采用", "选择", "will use", "decided", "chose",
                            "create", "build", "implement", "using", "implemented",
                            "configured", "设置", "配置"]
        if any(kw in content_lower for kw in decision_keywords):
            importance += 0.2

        # 包含偏好表达 → 提高重要性
        preference_keywords = ["prefer", "like", "dislike", "不喜欢", "usually",
                             "习惯", "偏好", "always", "never", "usually"]
        if any(kw in content_lower for kw in preference_keywords):
            importance += 0.15

        # 包含项目信息 → 提高重要性
        project_keywords = ["project", "项目", "repository", "repo", "代码库",
                           "file", "directory", "module", "workspace"]
        if any(kw in content_lower for kw in project_keywords):
            importance += 0.15

        # 包含代码/配置 → 提高重要性
        code_keywords = ["config", "setting", "配置", "code", "function",
                         "class", "variable", "api", "hook", "script"]
        if any(kw in content_lower for kw in code_keywords):
            importance += 0.1

        # 包含错误/问题 → 提高重要性
        error_keywords = ["error", "bug", "issue", "problem", "fix", "issue",
                         "failed", "失败", "问题"]
        if any(kw in content_lower for kw in error_keywords):
            importance += 0.1

        return min(importance, 1.0)

    def run(self, event_data: Dict) -> Dict[str, Any]:
        """
        执行 Hook

        Args:
            event_data: Hook 事件数据

        Returns:
            执行结果
        """
        parsed = self.parse_event(event_data)
        mode = parsed["mode"]

        results = {
            "saved": 0,
            "skipped": 0,
            "errors": [],
            "mode": mode,
            "session_key": parsed["session_key"],
            "timestamp": parsed["timestamp"],
        }

        # 根据模式提取内容
        if mode == "single":
            key_contents = self.extract_from_single_message(
                parsed["user_message"],
                parsed["assistant_message"],
            )
        else:
            key_contents = self.extract_from_transcript(parsed["transcript_path"])

        if not key_contents:
            results["message"] = "No meaningful content to save"
            return results

        # 保存每条内容
        for item in key_contents:
            try:
                save_result = self.memory_manager.smart_add(
                    content=item["content"],
                    importance=item["importance"],
                    auto_categorize=self.hook_config.auto_categorize,
                    metadata={
                        "role": item["role"],
                        "session": parsed["session_key"],
                        "source": f"hook_{mode}",
                    },
                )

                results["saved"] += 1

                if self.hook_config.verbose:
                    print(f"Saved: {item['content'][:50]}... (importance: {item['importance']:.2f})")

            except Exception as e:
                results["errors"].append(str(e))
                results["skipped"] += 1

        results["message"] = f"Saved {results['saved']} memories"
        return results


def main():
    """命令行入口"""
    parser = argparse.ArgumentParser(description="Qoder Mem0 Memory Hook")
    parser.add_argument("--config", type=str, help="Config file path")
    parser.add_argument("--transcript", type=str, help="Transcript path")
    parser.add_argument("--session", type=str, help="Session key")
    parser.add_argument("--last-message", type=str, help="Last assistant message")
    parser.add_argument("--user-message", type=str, help="User message")
    parser.add_argument("--assistant-message", type=str, help="Assistant message")
    parser.add_argument("--verbose", action="store_true", help="Verbose output")

    args = parser.parse_args()

    event_data = {
        "transcript_path": args.transcript,
        "session_key": args.session,
        "last_assistant_message": args.last_message,
        "user_message": args.user_message,
        "assistant_message": args.assistant_message,
    }

    # 过滤空值
    event_data = {k: v for k, v in event_data.items() if v}

    try:
        hook = Mem0MemoryHook(config_path=args.config)

        # 如果命令行指定了 verbose，覆盖配置
        if args.verbose:
            hook.hook_config.verbose = True

        result = hook.run(event_data)

        if args.verbose:
            print(json.dumps(result, indent=2, ensure_ascii=False))
        else:
            print(result.get("message", f"Saved {result.get('saved', 0)} memories"))

        return 0

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
#!/usr/bin/env python3
"""
Qoder Mem0 Memory Hook

配置驱动的记忆保存 Hook，支持多种触发模式。

触发时机：
1. AgentResponseComplete - AI 回复完成时（自动触发）
2. Stop - /stop 命令执行时（手动触发）

配置: ~/.skill-memory/config/hook.toml
"""

import json
import os
import sys
import argparse
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any, List

# 添加 src 到路径
SKILL_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(SKILL_ROOT / "src"))

from config import load_config
from memory_manager import DualLayerMemoryManager
from transcript_parser import TranscriptParser
from hook_config import load_hook_config


class Mem0MemoryHook:
    """
    Memory Hook 实现类
    支持配置驱动的多模式触发
    """

    def __init__(self, config_path: Optional[str] = None):
        self.hook_config = load_hook_config(config_path)
        self.config = load_config()
        self.memory_manager = DualLayerMemoryManager(self.config)
        self.parser = TranscriptParser()

    def detect_mode(self, event_data: Dict) -> str:
        """
        检测触发模式

        Args:
            event_data: Hook 事件数据

        Returns:
            "single" 或 "transcript"
        """
        mode = self.hook_config.hook_mode

        if mode == "auto":
            # 自动检测
            if "user_message" in event_data or "assistant_message" in event_data:
                return "single"
            elif "transcript" in event_data or "transcript_path" in event_data:
                return "transcript"
            else:
                # 默认单条模式
                return "single"
        elif mode in ("single", "agent_response"):
            return "single"
        else:
            return "transcript"

    def parse_event(self, event_data: Dict) -> Dict[str, Any]:
        """
        解析 Hook 事件数据

        AgentResponseComplete 提供的字段：
        - user_message: str (用户消息)
        - assistant_message: str (AI 回复)
        - session_key: str (会话标识)

        Stop 提供的字段：
        - last_assistant_message: str
        - transcript_path: str
        - session_key: str
        - transcript: list (完整 transcript)
        """
        mode = self.detect_mode(event_data)

        if mode == "single":
            return {
                "mode": "single",
                "user_message": event_data.get("user_message", ""),
                "assistant_message": event_data.get("assistant_message", ""),
                "session_key": event_data.get("session_key", "unknown"),
                "timestamp": event_data.get("timestamp", datetime.now().isoformat()),
            }

        # transcript 模式
        return {
            "mode": "transcript",
            "last_message": event_data.get("last_assistant_message", ""),
            "transcript_path": event_data.get("transcript_path", ""),
            "session_key": event_data.get("session_key", "unknown"),
            "timestamp": event_data.get("timestamp", datetime.now().isoformat()),
            "transcript": event_data.get("transcript"),
        }

    def should_save(self, content: str) -> bool:
        """
        判断内容是否值得保存
        """
        min_length = self.hook_config.min_length

        # 跳过太短的内容
        if len(content.strip()) < min_length:
            return False

        # 跳过命令类内容
        skip_patterns = self.hook_config.skip_patterns
        content_lower = content.lower().strip()
        if any(content_lower.startswith(p.lower()) for p in skip_patterns):
            return False

        # 跳过纯 URL
        if content.strip().startswith("http") and len(content.strip()) < 100:
            return False

        return True

    def extract_from_single_message(
        self,
        user_message: str,
        assistant_message: str,
    ) -> List[Dict[str, Any]]:
        """
        从单条消息对提取内容 (AgentResponseComplete 模式)

        Returns:
            [{"content": str, "role": str, "importance": float}, ...]
        """
        results = []
        max_per_round = self.hook_config.max_per_round

        # 组合对话内容
        combined = f"User: {user_message}\n\nAssistant: {assistant_message}"

        if self.should_save(combined):
            importance = self._calculate_importance(combined)
            results.append({
                "content": combined,
                "role": "user+assistant",
                "importance": importance,
            })

        # 如果只有用户消息有意义
        if user_message and self.should_save(user_message) and not results:
            importance = self._calculate_importance(user_message) * 0.8
            results.append({
                "content": user_message,
                "role": "user",
                "importance": importance,
            })

        # 如果只有助手消息有意义
        if assistant_message and self.should_save(assistant_message) and not results:
            importance = self._calculate_importance(assistant_message)
            results.append({
                "content": assistant_message,
                "role": "assistant",
                "importance": importance,
            })

        # 限制条数
        return results[:max_per_round]

    def extract_from_transcript(
        self,
        transcript_path: str,
        max_turns: int = 20,
    ) -> List[Dict[str, Any]]:
        """
        从 transcript 中提取关键信息 (Stop 模式)

        Returns:
            [{"content": str, "role": str, "importance": float}, ...]
        """
        if not transcript_path or not os.path.exists(transcript_path):
            return []

        try:
            entries = self.parser.parse_file(transcript_path)
            messages = self.parser.extract_messages(entries)

            # 取最近的消息
            recent = messages[-max_turns:] if len(messages) > max_turns else messages

            key_contents = []
            for msg in recent:
                content = msg.get_text_content()
                if self.should_save(content):
                    importance = self._calculate_importance(content)
                    key_contents.append({
                        "content": content,
                        "role": msg.role,
                        "importance": importance,
                    })

            # 限制条数
            max_per_round = self.hook_config.max_per_round
            return key_contents[:max_per_round]

        except Exception as e:
            print(f"Error extracting information: {e}", file=sys.stderr)
            return []

    def _calculate_importance(self, content: str) -> float:
        """
        计算内容重要性分数
        """
        importance = 0.5
        content_lower = content.lower()

        # 包含决策/结论 → 提高重要性
        decision_keywords = ["决定", "采用", "选择", "will use", "decided", "chose",
                            "create", "build", "implement", "using", "implemented",
                            "configured", "设置", "配置"]
        if any(kw in content_lower for kw in decision_keywords):
            importance += 0.2

        # 包含偏好表达 → 提高重要性
        preference_keywords = ["prefer", "like", "dislike", "不喜欢", "usually",
                             "习惯", "偏好", "always", "never", "usually"]
        if any(kw in content_lower for kw in preference_keywords):
            importance += 0.15

        # 包含项目信息 → 提高重要性
        project_keywords = ["project", "项目", "repository", "repo", "代码库",
                           "file", "directory", "module", "workspace"]
        if any(kw in content_lower for kw in project_keywords):
            importance += 0.15

        # 包含代码/配置 → 提高重要性
        code_keywords = ["config", "setting", "配置", "code", "function",
                         "class", "variable", "api", "hook", "script"]
        if any(kw in content_lower for kw in code_keywords):
            importance += 0.1

        # 包含错误/问题 → 提高重要性
        error_keywords = ["error", "bug", "issue", "problem", "fix", "issue",
                         "failed", "失败", "问题"]
        if any(kw in content_lower for kw in error_keywords):
            importance += 0.1

        return min(importance, 1.0)

    def run(self, event_data: Dict) -> Dict[str, Any]:
        """
        执行 Hook

        Args:
            event_data: Hook 事件数据

        Returns:
            执行结果
        """
        parsed = self.parse_event(event_data)
        mode = parsed["mode"]

        results = {
            "saved": 0,
            "skipped": 0,
            "errors": [],
            "mode": mode,
            "session_key": parsed["session_key"],
            "timestamp": parsed["timestamp"],
        }

        # 根据模式提取内容
        if mode == "single":
            key_contents = self.extract_from_single_message(
                parsed["user_message"],
                parsed["assistant_message"],
            )
        else:
            key_contents = self.extract_from_transcript(parsed["transcript_path"])

        if not key_contents:
            results["message"] = "No meaningful content to save"
            return results

        # 保存每条内容
        for item in key_contents:
            try:
                save_result = self.memory_manager.smart_add(
                    content=item["content"],
                    importance=item["importance"],
                    auto_categorize=self.hook_config.auto_categorize,
                    metadata={
                        "role": item["role"],
                        "session": parsed["session_key"],
                        "source": f"hook_{mode}",
                    },
                )

                results["saved"] += 1

                if self.hook_config.verbose:
                    print(f"Saved: {item['content'][:50]}... (importance: {item['importance']:.2f})")

            except Exception as e:
                results["errors"].append(str(e))
                results["skipped"] += 1

        results["message"] = f"Saved {results['saved']} memories"
        return results


def main():
    """命令行入口"""
    parser = argparse.ArgumentParser(description="Qoder Mem0 Memory Hook")
    parser.add_argument("--config", type=str, help="Config file path")
    parser.add_argument("--transcript", type=str, help="Transcript path")
    parser.add_argument("--session", type=str, help="Session key")
    parser.add_argument("--last-message", type=str, help="Last assistant message")
    parser.add_argument("--user-message", type=str, help="User message")
    parser.add_argument("--assistant-message", type=str, help="Assistant message")
    parser.add_argument("--verbose", action="store_true", help="Verbose output")

    args = parser.parse_args()

    event_data = {
        "transcript_path": args.transcript,
        "session_key": args.session,
        "last_assistant_message": args.last_message,
        "user_message": args.user_message,
        "assistant_message": args.assistant_message,
    }

    # 过滤空值
    event_data = {k: v for k, v in event_data.items() if v}

    try:
        hook = Mem0MemoryHook(config_path=args.config)

        # 如果命令行指定了 verbose，覆盖配置
        if args.verbose:
            hook.hook_config.verbose = True

        result = hook.run(event_data)

        if args.verbose:
            print(json.dumps(result, indent=2, ensure_ascii=False))
        else:
            print(result.get("message", f"Saved {result.get('saved', 0)} memories"))

        return 0

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
#!/usr/bin/env python3
"""
Qoder Mem0 Memory Hook

配置驱动的记忆保存 Hook，支持多种触发模式。

触发时机：
1. AgentResponseComplete - AI 回复完成时（自动触发）
2. Stop - /stop 命令执行时（手动触发）

配置: ~/.skill-memory/config/hook.toml
"""

import json
import os
import sys
import argparse
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any, List

# 添加 src 到路径
SKILL_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(SKILL_ROOT / "src"))

from config import load_config
from memory_manager import DualLayerMemoryManager
from transcript_parser import TranscriptParser
from hook_config import load_hook_config


class Mem0MemoryHook:
    """
    Memory Hook 实现类
    支持配置驱动的多模式触发
    """

    def __init__(self, config_path: Optional[str] = None):
        self.hook_config = load_hook_config(config_path)
        self.config = load_config()
        self.memory_manager = DualLayerMemoryManager(self.config)
        self.parser = TranscriptParser()

    def detect_mode(self, event_data: Dict) -> str:
        """
        检测触发模式

        Args:
            event_data: Hook 事件数据

        Returns:
            "single" 或 "transcript"
        """
        mode = self.hook_config.hook_mode

        if mode == "auto":
            # 自动检测
            if "user_message" in event_data or "assistant_message" in event_data:
                return "single"
            elif "transcript" in event_data or "transcript_path" in event_data:
                return "transcript"
            else:
                # 默认单条模式
                return "single"
        elif mode in ("single", "agent_response"):
            return "single"
        else:
            return "transcript"

    def parse_event(self, event_data: Dict) -> Dict[str, Any]:
        """
        解析 Hook 事件数据

        AgentResponseComplete 提供的字段：
        - user_message: str (用户消息)
        - assistant_message: str (AI 回复)
        - session_key: str (会话标识)

        Stop 提供的字段：
        - last_assistant_message: str
        - transcript_path: str
        - session_key: str
        - transcript: list (完整 transcript)
        """
        mode = self.detect_mode(event_data)

        if mode == "single":
            return {
                "mode": "single",
                "user_message": event_data.get("user_message", ""),
                "assistant_message": event_data.get("assistant_message", ""),
                "session_key": event_data.get("session_key", "unknown"),
                "timestamp": event_data.get("timestamp", datetime.now().isoformat()),
            }

        # transcript 模式
        return {
            "mode": "transcript",
            "last_message": event_data.get("last_assistant_message", ""),
            "transcript_path": event_data.get("transcript_path", ""),
            "session_key": event_data.get("session_key", "unknown"),
            "timestamp": event_data.get("timestamp", datetime.now().isoformat()),
            "transcript": event_data.get("transcript"),
        }

    def should_save(self, content: str) -> bool:
        """
        判断内容是否值得保存
        """
        min_length = self.hook_config.min_length

        # 跳过太短的内容
        if len(content.strip()) < min_length:
            return False

        # 跳过命令类内容
        skip_patterns = self.hook_config.skip_patterns
        content_lower = content.lower().strip()
        if any(content_lower.startswith(p.lower()) for p in skip_patterns):
            return False

        # 跳过纯 URL
        if content.strip().startswith("http") and len(content.strip()) < 100:
            return False

        return True

    def extract_from_single_message(
        self,
        user_message: str,
        assistant_message: str,
    ) -> List[Dict[str, Any]]:
        """
        从单条消息对提取内容 (AgentResponseComplete 模式)

        Returns:
            [{"content": str, "role": str, "importance": float}, ...]
        """
        results = []
        max_per_round = self.hook_config.max_per_round

        # 组合对话内容
        combined = f"User: {user_message}\n\nAssistant: {assistant_message}"

        if self.should_save(combined):
            importance = self._calculate_importance(combined)
            results.append({
                "content": combined,
                "role": "user+assistant",
                "importance": importance,
            })

        # 如果只有用户消息有意义
        if user_message and self.should_save(user_message) and not results:
            importance = self._calculate_importance(user_message) * 0.8
            results.append({
                "content": user_message,
                "role": "user",
                "importance": importance,
            })

        # 如果只有助手消息有意义
        if assistant_message and self.should_save(assistant_message) and not results:
            importance = self._calculate_importance(assistant_message)
            results.append({
                "content": assistant_message,
                "role": "assistant",
                "importance": importance,
            })

        # 限制条数
        return results[:max_per_round]

    def extract_from_transcript(
        self,
        transcript_path: str,
        max_turns: int = 20,
    ) -> List[Dict[str, Any]]:
        """
        从 transcript 中提取关键信息 (Stop 模式)

        Returns:
            [{"content": str, "role": str, "importance": float}, ...]
        """
        if not transcript_path or not os.path.exists(transcript_path):
            return []

        try:
            entries = self.parser.parse_file(transcript_path)
            messages = self.parser.extract_messages(entries)

            # 取最近的消息
            recent = messages[-max_turns:] if len(messages) > max_turns else messages

            key_contents = []
            for msg in recent:
                content = msg.get_text_content()
                if self.should_save(content):
                    importance = self._calculate_importance(content)
                    key_contents.append({
                        "content": content,
                        "role": msg.role,
                        "importance": importance,
                    })

            # 限制条数
            max_per_round = self.hook_config.max_per_round
            return key_contents[:max_per_round]

        except Exception as e:
            print(f"Error extracting information: {e}", file=sys.stderr)
            return []

    def _calculate_importance(self, content: str) -> float:
        """
        计算内容重要性分数
        """
        importance = 0.5
        content_lower = content.lower()

        # 包含决策/结论 → 提高重要性
        decision_keywords = ["决定", "采用", "选择", "will use", "decided", "chose",
                            "create", "build", "implement", "using", "implemented",
                            "configured", "设置", "配置"]
        if any(kw in content_lower for kw in decision_keywords):
            importance += 0.2

        # 包含偏好表达 → 提高重要性
        preference_keywords = ["prefer", "like", "dislike", "不喜欢", "usually",
                             "习惯", "偏好", "always", "never", "usually"]
        if any(kw in content_lower for kw in preference_keywords):
            importance += 0.15

        # 包含项目信息 → 提高重要性
        project_keywords = ["project", "项目", "repository", "repo", "代码库",
                           "file", "directory", "module", "workspace"]
        if any(kw in content_lower for kw in project_keywords):
            importance += 0.15

        # 包含代码/配置 → 提高重要性
        code_keywords = ["config", "setting", "配置", "code", "function",
                         "class", "variable", "api", "hook", "script"]
        if any(kw in content_lower for kw in code_keywords):
            importance += 0.1

        # 包含错误/问题 → 提高重要性
        error_keywords = ["error", "bug", "issue", "problem", "fix", "issue",
                         "failed", "失败", "问题"]
        if any(kw in content_lower for kw in error_keywords):
            importance += 0.1

        return min(importance, 1.0)

    def run(self, event_data: Dict) -> Dict[str, Any]:
        """
        执行 Hook

        Args:
            event_data: Hook 事件数据

        Returns:
            执行结果
        """
        parsed = self.parse_event(event_data)
        mode = parsed["mode"]

        results = {
            "saved": 0,
            "skipped": 0,
            "errors": [],
            "mode": mode,
            "session_key": parsed["session_key"],
            "timestamp": parsed["timestamp"],
        }

        # 根据模式提取内容
        if mode == "single":
            key_contents = self.extract_from_single_message(
                parsed["user_message"],
                parsed["assistant_message"],
            )
        else:
            key_contents = self.extract_from_transcript(parsed["transcript_path"])

        if not key_contents:
            results["message"] = "No meaningful content to save"
            return results

        # 保存每条内容
        for item in key_contents:
            try:
                save_result = self.memory_manager.smart_add(
                    content=item["content"],
                    importance=item["importance"],
                    auto_categorize=self.hook_config.auto_categorize,
                    metadata={
                        "role": item["role"],
                        "session": parsed["session_key"],
                        "source": f"hook_{mode}",
                    },
                )

                results["saved"] += 1

                if self.hook_config.verbose:
                    print(f"Saved: {item['content'][:50]}... (importance: {item['importance']:.2f})")

            except Exception as e:
                results["errors"].append(str(e))
                results["skipped"] += 1

        results["message"] = f"Saved {results['saved']} memories"
        return results


def main():
    """命令行入口"""
    parser = argparse.ArgumentParser(description="Qoder Mem0 Memory Hook")
    parser.add_argument("--config", type=str, help="Config file path")
    parser.add_argument("--transcript", type=str, help="Transcript path")
    parser.add_argument("--session", type=str, help="Session key")
    parser.add_argument("--last-message", type=str, help="Last assistant message")
    parser.add_argument("--user-message", type=str, help="User message")
    parser.add_argument("--assistant-message", type=str, help="Assistant message")
    parser.add_argument("--verbose", action="store_true", help="Verbose output")

    args = parser.parse_args()

    event_data = {
        "transcript_path": args.transcript,
        "session_key": args.session,
        "last_assistant_message": args.last_message,
        "user_message": args.user_message,
        "assistant_message": args.assistant_message,
    }

    # 过滤空值
    event_data = {k: v for k, v in event_data.items() if v}

    try:
        hook = Mem0MemoryHook(config_path=args.config)

        # 如果命令行指定了 verbose，覆盖配置
        if args.verbose:
            hook.hook_config.verbose = True

        result = hook.run(event_data)

        if args.verbose:
            print(json.dumps(result, indent=2, ensure_ascii=False))
        else:
            print(result.get("message", f"Saved {result.get('saved', 0)} memories"))

        return 0

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
