#!/usr/bin/env python3
"""
Unified Memory Hook - 跨平台统一入口

支持平台：
- qodercli: 通过 hooks.yaml 触发
- qoder GUI: 通过 settings.json Hook 触发  
- openclaw: 通过 API 或文件监控触发

用法:
    # stdin 模式（Qoder Hook）
    echo '{"session_id": "xxx", "prompt": "用户消息"}' | python unified_hook.py
    
    # 命令行模式
    python unified_hook.py --transcript /path/to/transcript.jsonl --session xxx
    
    # 指定平台
    python unified_hook.py --platform qodercli
"""

import json
import os
import sys
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional

# 添加 src 到路径
SKILL_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(SKILL_ROOT / "src"))

from config import load_config
from memory_manager import DualLayerMemoryManager
from transcript_parser import TranscriptParser
from hook_config import load_hook_config
from qdrant_monitor import QdrantMonitor
from platforms import (
    detect_platform,
    get_adapter,
    is_hook_context,
    PlatformType,
    MemoryEvent,
)


class UnifiedMemoryHook:
    """
    跨平台统一 Memory Hook
    
    功能：
    1. 自动检测运行平台
    2. 解析平台特定的输入格式
    3. 提取有价值的对话内容
    4. 保存到双层记忆系统
    """

    def __init__(self, config_path: Optional[str] = None, platform: Optional[PlatformType] = None):
        # Step 1: 确保 Qdrant 正在运行
        self._ensure_qdrant()
        
        # Step 2: 初始化组件
        self.hook_config = load_hook_config(config_path)
        self.config = load_config()
        self.memory_manager = DualLayerMemoryManager(self.config)
        self.parser = TranscriptParser()
        
        # Step 3: 平台适配器
        self.platform_type = platform or detect_platform()
        self.adapter = get_adapter(self.platform_type)

    def _ensure_qdrant(self):
        """确保 Qdrant 正在运行"""
        try:
            monitor = QdrantMonitor()
            success, message = monitor.ensure_running(auto_start=True)
            if not success:
                print(f"WARNING: {message}", file=sys.stderr)
                print("Memory features may be limited until Qdrant is running.", file=sys.stderr)
        except Exception as e:
            print(f"WARNING: Failed to check Qdrant status: {e}", file=sys.stderr)

    def process_events(self, events: List[MemoryEvent]) -> Dict[str, Any]:
        """
        处理事件列表并保存记忆
        
        Args:
            events: MemoryEvent 列表
            
        Returns:
            处理结果
        """
        results = {
            "saved": 0,
            "skipped": 0,
            "errors": [],
            "platform": self.platform_type.value,
            "events_processed": len(events),
        }

        for event in events:
            if not event.is_meaningful():
                results["skipped"] += 1
                continue

            try:
                importance = self._calculate_importance(event.content)
                
                self.memory_manager.smart_add(
                    content=event.content,
                    importance=importance,
                    auto_categorize=self.hook_config.auto_categorize,
                    metadata={
                        "event_type": event.event_type,
                        "session": event.session_id,
                        "source": f"{self.platform_type.value}_hook",
                        "timestamp": event.timestamp or datetime.now().isoformat(),
                    },
                )
                
                results["saved"] += 1
                
                if self.hook_config.verbose:
                    print(f"Saved: {event.content[:50]}... (importance: {importance:.2f})")

            except Exception as e:
                results["errors"].append(str(e))
                results["skipped"] += 1

        results["message"] = f"Saved {results['saved']} memories"
        return results

    def run_from_stdin(self) -> Dict[str, Any]:
        """从 stdin 读取并处理"""
        try:
            input_data = sys.stdin.read()
            if not input_data.strip():
                return {"saved": 0, "message": "No input from stdin"}
            
            events = self.adapter.parse_input(input_data)
            return self.process_events(events)
            
        except Exception as e:
            return {"saved": 0, "errors": [str(e)]}

    def run_from_transcript(self, transcript_path: str, session_id: Optional[str] = None) -> Dict[str, Any]:
        """从 transcript 文件处理"""
        if not transcript_path or not os.path.exists(transcript_path):
            return {"saved": 0, "message": f"Transcript not found: {transcript_path}"}

        try:
            entries = self.parser.parse_file(transcript_path)
            messages = self.parser.extract_messages(entries)
            
            # 取最近的消息
            max_turns = 20
            recent = messages[-max_turns:] if len(messages) > max_turns else messages
            
            # 转换为事件
            events = []
            for msg in recent:
                content = msg.get_text_content()
                if self._should_save(content):
                    events.append(MemoryEvent(
                        event_type=f"{msg.role}_message",
                        content=content,
                        session_id=session_id,
                        metadata={"role": msg.role, "source": "transcript"},
                    ))
            
            return self.process_events(events)
            
        except Exception as e:
            return {"saved": 0, "errors": [str(e)]}

    def _should_save(self, content: str) -> bool:
        """判断内容是否值得保存"""
        min_length = self.hook_config.min_length
        
        if len(content.strip()) < min_length:
            return False
        
        skip_patterns = self.hook_config.skip_patterns
        content_lower = content.lower().strip()
        if any(content_lower.startswith(p.lower()) for p in skip_patterns):
            return False
        
        if content.strip().startswith("http") and len(content.strip()) < 100:
            return False
        
        return True

    def _calculate_importance(self, content: str) -> float:
        """计算内容重要性分数"""
        importance = 0.5
        content_lower = content.lower()

        # 决策/结论
        decision_keywords = ["决定", "采用", "选择", "will use", "decided", "chose",
                            "create", "build", "implement", "using", "implemented",
                            "configured", "设置", "配置"]
        if any(kw in content_lower for kw in decision_keywords):
            importance += 0.2

        # 偏好表达
        preference_keywords = ["prefer", "like", "dislike", "不喜欢", "usually",
                             "习惯", "偏好", "always", "never"]
        if any(kw in content_lower for kw in preference_keywords):
            importance += 0.15

        # 项目信息
        project_keywords = ["project", "项目", "repository", "repo", "代码库",
                           "file", "directory", "module", "workspace"]
        if any(kw in content_lower for kw in project_keywords):
            importance += 0.15

        # 代码/配置
        code_keywords = ["config", "setting", "配置", "code", "function",
                         "class", "variable", "api", "hook", "script"]
        if any(kw in content_lower for kw in code_keywords):
            importance += 0.1

        # 错误/问题
        error_keywords = ["error", "bug", "issue", "problem", "fix",
                         "failed", "失败", "问题"]
        if any(kw in content_lower for kw in error_keywords):
            importance += 0.1

        return min(importance, 1.0)


def main():
    """命令行入口"""
    parser = argparse.ArgumentParser(
        description="Unified Memory Hook - 跨平台记忆保存",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Platforms:
  qodercli   - Qoder CLI (via hooks.yaml)
  qoder      - Qoder GUI (via settings.json)
  openclaw   - OpenClaw (via API or file watcher)

Examples:
  # stdin mode (Qoder Hook)
  echo '{"session_id": "xxx", "prompt": "user message"}' | python unified_hook.py
  
  # transcript mode
  python unified_hook.py --transcript /path/to/session.jsonl
  
  # specify platform
  python unified_hook.py --platform qodercli
        """
    )
    
    parser.add_argument("--config", type=str, help="Config file path")
    parser.add_argument("--transcript", type=str, help="Transcript file path")
    parser.add_argument("--session", type=str, help="Session ID")
    parser.add_argument("--platform", type=str, choices=["qodercli", "qoder", "openclaw"],
                       help="Platform type (auto-detected by default)")
    parser.add_argument("--verbose", action="store_true", help="Verbose output")
    parser.add_argument("--info", action="store_true", help="Show platform info and exit")

    args = parser.parse_args()

    # 显示平台信息
    if args.info:
        from platforms import get_platform_info
        info = get_platform_info()
        print(json.dumps(info, indent=2))
        return 0

    # 确定平台类型
    platform = None
    if args.platform:
        platform_map = {
            "qodercli": PlatformType.QODER_CLI,
            "qoder": PlatformType.QODER_GUI,
            "openclaw": PlatformType.OPENCLAW,
        }
        platform = platform_map[args.platform]

    try:
        hook = UnifiedMemoryHook(config_path=args.config, platform=platform)
        
        if args.verbose:
            hook.hook_config.verbose = True

        # 根据输入方式处理
        if args.transcript:
            result = hook.run_from_transcript(args.transcript, args.session)
        elif is_hook_context() or not sys.stdin.isatty():
            result = hook.run_from_stdin()
        else:
            print("No input provided. Use --transcript or pipe input via stdin.", file=sys.stderr)
            parser.print_help()
            return 1

        # 输出结果
        if args.verbose:
            print(json.dumps(result, indent=2, ensure_ascii=False))
        else:
            print(result.get("message", f"Saved {result.get('saved', 0)} memories"))

        return 0

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
