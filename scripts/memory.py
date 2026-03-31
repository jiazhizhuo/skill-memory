#!/usr/bin/env python3
"""
skill-memory CLI entry point.

Inspired by OpenClaw's memory commands:
- MEMORY.md (long-term)
- memory/YYYY-MM-DD.md (daily notes)
- Hybrid search with MMR and temporal decay
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

from scripts.mem0_client import Mem0Client
from scripts.tier_manager import TierManager, MemoryTier


def cmd_add(client: Mem0Client, args: argparse.Namespace) -> str:
    """Add memory to mid-term or long-term."""
    tier = args.tier or "mid"

    if args.important or args.importance >= 0.8:
        tier = "long"

    result = client.add(
        content=args.content,
        tier=tier,
        metadata={"importance": args.importance}
    )

    return json.dumps({
        "status": "success",
        "action": "add",
        "id": result["id"],
        "tier": tier,
        "content": result["content"]
    }, indent=2, ensure_ascii=False)


def cmd_search(client: Mem0Client, args: argparse.Namespace) -> str:
    """Search memories with hybrid search."""
    results = client.search(
        query=args.query,
        tier=args.tier,
        limit=args.limit
    )

    return json.dumps({
        "status": "success",
        "action": "search",
        "query": args.query,
        "count": len(results),
        "results": results
    }, indent=2, ensure_ascii=False)


def cmd_list(client: Mem0Client, args: argparse.Namespace) -> str:
    """List all memories."""
    results = client.get_all(
        tier=args.tier,
        limit=args.limit
    )

    return json.dumps({
        "status": "success",
        "action": "list",
        "count": len(results),
        "results": [
            {
                "id": r.get("id"),
                "content": r.get("memory", r.get("text", "")),
                "tier": r.get("metadata", {}).get("tier", "unknown")
            }
            for r in results
        ]
    }, indent=2, ensure_ascii=False)


def cmd_delete(client: Mem0Client, args: argparse.Namespace) -> str:
    """Delete a memory by ID."""
    success = client.delete(args.memory_id)

    return json.dumps({
        "status": "success" if success else "error",
        "action": "delete",
        "id": args.memory_id
    }, indent=2, ensure_ascii=False)


def cmd_stats(client: Mem0Client, args: argparse.Namespace) -> str:
    """Get memory statistics."""
    all_memories = client.get_all(limit=1000)

    stats = {
        "total": len(all_memories),
        "by_tier": {
            "working": 0,
            "mid": 0,
            "long": 0
        }
    }

    for mem in all_memories:
        tier = mem.get("metadata", {}).get("tier", "unknown")
        if tier in stats["by_tier"]:
            stats["by_tier"][tier] += 1

    return json.dumps({
        "status": "success",
        "action": "stats",
        "stats": stats,
        "timestamp": datetime.now().isoformat()
    }, indent=2, ensure_ascii=False)


def cmd_today(client: Mem0Client, args: argparse.Namespace) -> str:
    """Get today's daily notes (OpenClaw style: memory/YYYY-MM-DD.md)."""
    today = datetime.now().strftime("%Y-%m-%d")

    return json.dumps({
        "status": "success",
        "action": "today",
        "date": today,
        "note": f"Daily notes for {today} would be stored in memory/{today}.md"
    }, indent=2, ensure_ascii=False)


def cmd_long(client: Mem0Client, args: argparse.Namespace) -> str:
    """Get long-term memory (like MEMORY.md)."""
    results = client.get_all(tier="long", limit=100)

    return json.dumps({
        "status": "success",
        "action": "long_term",
        "count": len(results),
        "results": results,
        "note": "Long-term memories are permanent (like OpenClaw's MEMORY.md)"
    }, indent=2, ensure_ascii=False)


def main():
    parser = argparse.ArgumentParser(
        description="skill-memory: OpenClaw-style 3-tier memory system",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  memory add "用户喜欢简洁的代码风格"
  memory add "重要项目信息" --tier long
  memory add "临时笔记" --importance 0.3
  memory search "代码风格偏好"
  memory list --tier mid
  memory today
  memory long
  memory stats
  memory delete abc123
        """
    )

    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # add
    p_add = subparsers.add_parser("add", help="Add a memory")
    p_add.add_argument("content", help="Memory content")
    p_add.add_argument("--tier", choices=["working", "mid", "long"], help="Memory tier")
    p_add.add_argument("--important", action="store_true", help="Mark as important (long-term)")
    p_add.add_argument("--importance", type=float, default=0.5, help="Importance (0-1)")

    # search
    p_search = subparsers.add_parser("search", help="Search memories")
    p_search.add_argument("query", help="Search query")
    p_search.add_argument("--tier", choices=["working", "mid", "long"], help="Filter by tier")
    p_search.add_argument("--limit", type=int, default=5, help="Max results")

    # list
    p_list = subparsers.add_parser("list", help="List all memories")
    p_list.add_argument("--tier", choices=["working", "mid", "long"], help="Filter by tier")
    p_list.add_argument("--limit", type=int, default=100, help="Max results")

    # delete
    p_delete = subparsers.add_parser("delete", help="Delete a memory")
    p_delete.add_argument("memory_id", help="Memory ID to delete")

    # stats
    subparsers.add_parser("stats", help="Get memory statistics")

    # today
    subparsers.add_parser("today", help="Get today's daily notes")

    # long
    subparsers.add_parser("long", help="Get long-term memories")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    # Initialize clients
    user_id = "default"
    client = Mem0Client(user_id=user_id)

    # Dispatch
    commands = {
        "add": cmd_add,
        "search": cmd_search,
        "list": cmd_list,
        "delete": cmd_delete,
        "stats": cmd_stats,
        "today": cmd_today,
        "long": cmd_long,
    }

    try:
        result = commands[args.command](client, args)
        print(result)
    except Exception as e:
        print(json.dumps({
            "status": "error",
            "error": str(e)
        }, indent=2))
        sys.exit(1)


if __name__ == "__main__":
    main()
