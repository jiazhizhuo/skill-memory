#!/usr/bin/env python3
"""
Skill Memory CLI

Usage:
    memory add <content> [--importance 0.5] [--tier mid|long]
    memory search <query> [--limit 5] [--layer mem0|memory|both]
    memory list [--tier mid|long] [--limit 20]
    memory import --file <path> [--tier long]
    memory import --dir <path> [--tier long]
    memory long
    memory stats
    memory backup
"""

import argparse
import json
import sys
import os
from pathlib import Path
from typing import Optional

# 添加 src 到路径（支持 pip 安装和直接运行）
_cli_dir = Path(__file__).parent
# 尝试多种路径
for _path in [
    _cli_dir,  # pip 安装后
    _cli_dir.parent,  # 直接运行 src/cli.py
    _cli_dir.parent.parent,  # 直接运行 src/memory_cli.py
]:
    if (_path / "config.py").exists():
        sys.path.insert(0, str(_path))
        break
else:
    # 回退：添加 ~/.skill-memory/src
    _home_path = Path.home() / ".skill-memory" / "src"
    if _home_path.exists():
        sys.path.insert(0, str(_home_path))

from config import load_config, get_default_config
from memory_manager import DualLayerMemoryManager
from transcript_parser import TranscriptParser


def cmd_add(manager: DualLayerMemoryManager, args: argparse.Namespace) -> int:
    """添加记忆"""
    result = manager.smart_add(
        content=args.content,
        importance=args.importance,
        auto_categorize=True,
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


def cmd_search(manager: DualLayerMemoryManager, args: argparse.Namespace) -> int:
    """搜索记忆"""
    layers = None
    if args.layer == "mem0":
        layers = ["mem0"]
    elif args.layer == "memory":
        layers = ["memory"]
    else:
        layers = ["mem0", "memory"]

    result = manager.smart_search(
        query=args.query,
        layers=layers,
        limit=args.limit,
    )

    # 格式化输出
    if result["merged"]:
        print("=== Search Results ===")
        for i, item in enumerate(result["merged"], 1):
            print(f"\n{i}. [{item.get('source', 'mem0')}] {item.get('category', 'general')}")
            print(f"   {item['content'][:200]}...")
    else:
        print("No results found")

    return 0


def cmd_list(manager: DualLayerMemoryManager, args: argparse.Namespace) -> int:
    """列出记忆"""
    results = manager.mem0.get_all(limit=args.limit)

    if isinstance(results, list):
        print(f"Total: {len(results)} memories")
        for i, mem in enumerate(results[:args.limit], 1):
            if isinstance(mem, dict):
                print(f"\n{i}. {mem.get('content', '')[:100]}...")
    else:
        print(json.dumps(results, indent=2, ensure_ascii=False))

    return 0


def cmd_import_transcript(manager: DualLayerMemoryManager, args: argparse.Namespace) -> int:
    """导入历史对话"""
    parser = TranscriptParser()

    if not args.file and not args.dir:
        print("Error: must specify --file or --dir", file=sys.stderr)
        return 1

    tier = args.tier or "long"
    imported = 0
    skipped = 0

    if args.file:
        # 单文件导入
        try:
            entries = parser.parse_file(args.file)
            messages = parser.extract_messages(entries)

            # 取最近的
            recent = messages[-50:] if len(messages) > 50 else messages

            # 合并为连贯文本
            lines = []
            for msg in recent:
                if msg.is_meaningful():
                    content = msg.get_text_content()
                    role = msg.role.upper()
                    lines.append(f"**{role}**: {content}")

            content = "\n\n".join(lines)

            if len(content.strip()) > 50:
                result = manager.smart_add(
                    content=content,
                    importance=0.7,
                    metadata={"source": "import", "file": args.file},
                )
                imported = 1
                print(f"Imported: {args.file}")
                print(json.dumps(result, indent=2, ensure_ascii=False))
            else:
                skipped = 1
                print(f"Skipped (too short): {args.file}")

        except Exception as e:
            print(f"Error importing {args.file}: {e}", file=sys.stderr)
            return 1

    elif args.dir:
        # 批量导入目录
        dir_path = Path(args.dir)
        if not dir_path.exists():
            print(f"Error: Directory not found: {args.dir}", file=sys.stderr)
            return 1

        jsonl_files = list(dir_path.glob("*.jsonl"))
        print(f"Found {len(jsonl_files)} transcript files")

        for jsonl_file in jsonl_files:
            try:
                entries = parser.parse_file(str(jsonl_file))
                messages = parser.extract_messages(entries)

                recent = messages[-50:] if len(messages) > 50 else messages

                lines = []
                for msg in recent:
                    if msg.is_meaningful():
                        content = msg.get_text_content()
                        role = msg.role.upper()
                        lines.append(f"**{role}**: {content}")

                content = "\n\n".join(lines)

                if len(content.strip()) > 50:
                    manager.smart_add(
                        content=content,
                        importance=0.6,
                        metadata={"source": "import", "file": str(jsonl_file)},
                    )
                    imported += 1
                    print(f"Imported: {jsonl_file.name}")
                else:
                    skipped += 1
                    print(f"Skipped (too short): {jsonl_file.name}")

            except Exception as e:
                skipped += 1
                print(f"Error: {jsonl_file.name}: {e}")

    print(f"\nSummary: {imported} imported, {skipped} skipped")
    return 0


def cmd_long(manager: DualLayerMemoryManager, args: argparse.Namespace) -> int:
    """查看长期记忆"""
    content = manager.get_long_term_memory()
    if content:
        print(content)
    else:
        print("No long-term memory found")
    return 0


def cmd_stats(manager: DualLayerMemoryManager, args: argparse.Namespace) -> int:
    """查看统计信息"""
    stats = manager.get_stats()
    print(json.dumps(stats, indent=2, ensure_ascii=False))
    return 0


def cmd_backup(manager: DualLayerMemoryManager, args: argparse.Namespace) -> int:
    """备份 MEMORY.md"""
    backup_path = manager.backup_memory_md()
    print(f"Backup saved to: {backup_path}")
    return 0


def cmd_organize(manager: DualLayerMemoryManager, args: argparse.Namespace) -> int:
    """整理记忆"""
    result = manager.organize_memories()
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


def main():
    parser = argparse.ArgumentParser(
        description="Skill Memory CLI - 双层记忆系统",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  memory add "用户偏好深色主题" --importance 0.8
  memory search "代码风格"
  memory import --file ~/.qoder/sessions/xxx/transcript.jsonl
  memory import --dir ~/old-conversations/
  memory list --tier mid --limit 20
  memory long
  memory stats
  memory backup
        """
    )

    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # add
    p_add = subparsers.add_parser("add", help="Add a memory")
    p_add.add_argument("content", help="Memory content")
    p_add.add_argument("--importance", type=float, default=0.5)
    p_add.add_argument("--tier", choices=["mid", "long"], default="mid")

    # search
    p_search = subparsers.add_parser("search", help="Search memories")
    p_search.add_argument("query", help="Search query")
    p_search.add_argument("--limit", type=int, default=5)
    p_search.add_argument("--layer", choices=["mem0", "memory", "both"], default="both")

    # list
    p_list = subparsers.add_parser("list", help="List memories")
    p_list.add_argument("--tier", choices=["mid", "long"])
    p_list.add_argument("--limit", type=int, default=20)

    # import
    p_import = subparsers.add_parser("import", help="Import historical dialogues")
    p_import.add_argument("--file", help="Single transcript file (JSONL)")
    p_import.add_argument("--dir", help="Directory containing transcript files")
    p_import.add_argument("--tier", choices=["mid", "long"])

    # long
    subparsers.add_parser("long", help="View long-term memory")

    # stats
    subparsers.add_parser("stats", help="View statistics")

    # organize
    subparsers.add_parser("organize", help="Organize memories")

    # backup
    subparsers.add_parser("backup", help="Backup MEMORY.md")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    # 初始化管理器
    try:
        config = load_config()
        manager = DualLayerMemoryManager(config)
    except Exception as e:
        print(f"Error initializing: {e}", file=sys.stderr)
        return 1

    # 分发命令
    commands = {
        "add": cmd_add,
        "search": cmd_search,
        "list": cmd_list,
        "import": cmd_import_transcript,
        "long": cmd_long,
        "stats": cmd_stats,
        "organize": cmd_organize,
        "backup": cmd_backup,
    }

    try:
        return commands[args.command](manager, args)
    except Exception as e:
        print(json.dumps({
            "status": "error",
            "error": str(e)
        }, indent=2), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
