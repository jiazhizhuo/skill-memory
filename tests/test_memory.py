"""
测试 Transcript Parser
"""

import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from transcript_parser import TranscriptParser, Message


def test_parser():
    """测试解析器"""
    parser = TranscriptParser()

    # 测试 OpenClaw 格式
    openclaw_data = [
        json.dumps({
            "type": "message",
            "message": {
                "role": "user",
                "content": "I prefer dark theme"
            }
        }),
        json.dumps({
            "type": "message",
            "message": {
                "role": "assistant",
                "content": [{"type": "text", "text": "I'll set dark theme for you."}]
            }
        }),
    ]

    # 模拟解析
    parser.format = "openclaw"
    entries = []
    for line in openclaw_data:
        entries.append(parser._parse_line(line))

    assert len(entries) == 2
    assert entries[0].message.role == "user"
    assert entries[1].message.role == "assistant"
    print("✓ OpenClaw format parsing OK")


def test_message_extraction():
    """测试消息提取"""
    parser = TranscriptParser()

    # 模拟消息
    messages = [
        Message(role="user", content="Hello"),
        Message(role="assistant", content="Hi there!"),
        Message(role="user", content="How are you?"),
    ]

    # 提取
    filtered = parser.extract_messages(
        [{"type": "message", "message": m} for m in messages],
        roles=["user"]
    )

    assert len(filtered) == 2
    print("✓ Message extraction OK")


def test_importance_keywords():
    """测试重要性关键词"""
    from memory_manager import DualLayerMemoryManager

    # 简单测试
    manager = DualLayerMemoryManager()

    # 测试分类
    assert manager._categorize("I prefer dark theme") == "preference"
    assert manager._categorize("Project structure is complex") == "project"
    print("✓ Categorization OK")

    # 测试重要性
    imp = manager._calculate_importance("I decided to use React for this project")
    assert imp > 0.5
    print("✓ Importance calculation OK")


if __name__ == "__main__":
    test_parser()
    test_message_extraction()
    test_importance_keywords()
    print("\n✓ All tests passed!")
"""
测试 Transcript Parser
"""

import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from transcript_parser import TranscriptParser, Message


def test_parser():
    """测试解析器"""
    parser = TranscriptParser()

    # 测试 OpenClaw 格式
    openclaw_data = [
        json.dumps({
            "type": "message",
            "message": {
                "role": "user",
                "content": "I prefer dark theme"
            }
        }),
        json.dumps({
            "type": "message",
            "message": {
                "role": "assistant",
                "content": [{"type": "text", "text": "I'll set dark theme for you."}]
            }
        }),
    ]

    # 模拟解析
    parser.format = "openclaw"
    entries = []
    for line in openclaw_data:
        entries.append(parser._parse_line(line))

    assert len(entries) == 2
    assert entries[0].message.role == "user"
    assert entries[1].message.role == "assistant"
    print("✓ OpenClaw format parsing OK")


def test_message_extraction():
    """测试消息提取"""
    parser = TranscriptParser()

    # 模拟消息
    messages = [
        Message(role="user", content="Hello"),
        Message(role="assistant", content="Hi there!"),
        Message(role="user", content="How are you?"),
    ]

    # 提取
    filtered = parser.extract_messages(
        [{"type": "message", "message": m} for m in messages],
        roles=["user"]
    )

    assert len(filtered) == 2
    print("✓ Message extraction OK")


def test_importance_keywords():
    """测试重要性关键词"""
    from memory_manager import DualLayerMemoryManager

    # 简单测试
    manager = DualLayerMemoryManager()

    # 测试分类
    assert manager._categorize("I prefer dark theme") == "preference"
    assert manager._categorize("Project structure is complex") == "project"
    print("✓ Categorization OK")

    # 测试重要性
    imp = manager._calculate_importance("I decided to use React for this project")
    assert imp > 0.5
    print("✓ Importance calculation OK")


if __name__ == "__main__":
    test_parser()
    test_message_extraction()
    test_importance_keywords()
    print("\n✓ All tests passed!")
"""
测试 Transcript Parser
"""

import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from transcript_parser import TranscriptParser, Message


def test_parser():
    """测试解析器"""
    parser = TranscriptParser()

    # 测试 OpenClaw 格式
    openclaw_data = [
        json.dumps({
            "type": "message",
            "message": {
                "role": "user",
                "content": "I prefer dark theme"
            }
        }),
        json.dumps({
            "type": "message",
            "message": {
                "role": "assistant",
                "content": [{"type": "text", "text": "I'll set dark theme for you."}]
            }
        }),
    ]

    # 模拟解析
    parser.format = "openclaw"
    entries = []
    for line in openclaw_data:
        entries.append(parser._parse_line(line))

    assert len(entries) == 2
    assert entries[0].message.role == "user"
    assert entries[1].message.role == "assistant"
    print("✓ OpenClaw format parsing OK")


def test_message_extraction():
    """测试消息提取"""
    parser = TranscriptParser()

    # 模拟消息
    messages = [
        Message(role="user", content="Hello"),
        Message(role="assistant", content="Hi there!"),
        Message(role="user", content="How are you?"),
    ]

    # 提取
    filtered = parser.extract_messages(
        [{"type": "message", "message": m} for m in messages],
        roles=["user"]
    )

    assert len(filtered) == 2
    print("✓ Message extraction OK")


def test_importance_keywords():
    """测试重要性关键词"""
    from memory_manager import DualLayerMemoryManager

    # 简单测试
    manager = DualLayerMemoryManager()

    # 测试分类
    assert manager._categorize("I prefer dark theme") == "preference"
    assert manager._categorize("Project structure is complex") == "project"
    print("✓ Categorization OK")

    # 测试重要性
    imp = manager._calculate_importance("I decided to use React for this project")
    assert imp > 0.5
    print("✓ Importance calculation OK")


if __name__ == "__main__":
    test_parser()
    test_message_extraction()
    test_importance_keywords()
    print("\n✓ All tests passed!")
