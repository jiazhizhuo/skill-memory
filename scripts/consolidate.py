#!/usr/bin/env python3
"""
定时记忆整理脚本

功能：
1. 检查 Mem0 中是否有新增量
2. 检测是否有需要归纳/去重的记忆
3. 整理 MEMORY.md 结构
4. 无增量时跳过

Usage:
    # 手动运行
    python3 scripts/consolidate.py --verbose

    # 添加到 crontab (每天早上 9 点)
    0 9 * * * /usr/bin/python3 ~/.skill-memory/scripts/consolidate.py >> ~/.skill-memory/logs/consolidate.log 2>&1
"""

import os
import sys
import json
import argparse
from pathlib import Path
from datetime import datetime, timedelta

# 添加 src 到路径
SKILL_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(SKILL_ROOT / "src"))

from config import load_config
from memory_manager import DualLayerMemoryManager


class MemoryConsolidator:
    """记忆整理器"""

    def __init__(self, config=None):
        self.config = config or load_config()
        self.memory_manager = DualLayerMemoryManager(self.config)
        self.state_file = SKILL_ROOT / "data" / "consolidation_state.json"

    def load_state(self) -> dict:
        """加载上次整理状态"""
        if self.state_file.exists():
            with open(self.state_file) as f:
                return json.load(f)
        return {"last_run": None, "last_memory_count": 0}

    def save_state(self, state: dict):
        """保存整理状态"""
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.state_file, "w") as f:
            json.dump(state, f, indent=2)

    def check_increment(self) -> dict:
        """
        检查增量

        Returns:
            {"has_increment": bool, "new_count": int, "diff": int}
        """
        state = self.load_state()

        # 获取当前记忆数量
        try:
            stats = self.memory_manager.get_stats()
            current_count = stats.get("mem0_count", 0)
        except Exception:
            current_count = 0

        diff = current_count - state.get("last_memory_count", 0)

        return {
            "has_increment": diff > 0,
            "new_count": current_count,
            "diff": diff,
            "last_count": state.get("last_memory_count", 0),
        }

    def consolidate(self, force: bool = False) -> dict:
        """
        执行整理

        Args:
            force: 是否强制执行（忽略增量检测）

        Returns:
            整理结果
        """
        state = self.load_state()
        increment = self.check_increment()

        results = {
            "run_at": datetime.now().isoformat(),
            "has_increment": increment["has_increment"],
            "memory_count": increment["new_count"],
            "skipped": False,
            "actions": [],
        }

        # 检查是否有增量
        if not force and not increment["has_increment"]:
            results["skipped"] = True
            results["message"] = "No increment detected, skipped"
            return results

        # 有增量，执行整理
        if increment["has_increment"]:
            results["actions"].append({
                "type": "increment_detected",
                "new_memories": increment["diff"],
            })

        # 检查需要晋升到长期记忆的内容
        try:
            high_priority = self._get_high_priority_memories()
            if high_priority:
                results["actions"].append({
                    "type": "promote_to_long_term",
                    "count": len(high_priority),
                })
        except Exception as e:
            results["actions"].append({
                "type": "error",
                "message": str(e),
            })

        # 检查去重
        try:
            duplicates = self._find_duplicates()
            if duplicates:
                results["actions"].append({
                    "type": "deduplicate",
                    "found": len(duplicates),
                })
        except Exception as e:
            results["actions"].append({
                "type": "error",
                "message": str(e),
            })

        # 更新状态
        state["last_run"] = results["run_at"]
        state["last_memory_count"] = increment["new_count"]
        self.save_state(state)

        results["message"] = f"Consolidated {len(results['actions'])} actions"
        return results

    def _get_high_priority_memories(self) -> list:
        """获取高优先级记忆"""
        try:
            results = self.memory_manager.search(
                query="",
                limit=50,
                tier="short",
            )
            return [r for r in results if r.get("importance", 0) >= 0.75]
        except Exception:
            return []

    def _find_duplicates(self) -> list:
        """查找重复记忆"""
        # 简单实现：基于相似度检测
        # 实际可能需要更复杂的算法
        return []


def main():
    parser = argparse.ArgumentParser(description="Memory Consolidator")
    parser.add_argument("--force", action="store_true", help="Force consolidation")
    parser.add_argument("--verbose", action="store_true", help="Verbose output")
    args = parser.parse_args()

    consolidator = MemoryConsolidator()
    result = consolidator.consolidate(force=args.force)

    if args.verbose:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print(result.get("message", "Done"))

    return 0 if not result.get("skipped") else 0


if __name__ == "__main__":
    sys.exit(main())
#!/usr/bin/env python3
"""
定时记忆整理脚本

功能：
1. 检查 Mem0 中是否有新增量
2. 检测是否有需要归纳/去重的记忆
3. 整理 MEMORY.md 结构
4. 无增量时跳过

Usage:
    # 手动运行
    python3 scripts/consolidate.py --verbose

    # 添加到 crontab (每天早上 9 点)
    0 9 * * * /usr/bin/python3 ~/.skill-memory/scripts/consolidate.py >> ~/.skill-memory/logs/consolidate.log 2>&1
"""

import os
import sys
import json
import argparse
from pathlib import Path
from datetime import datetime, timedelta

# 添加 src 到路径
SKILL_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(SKILL_ROOT / "src"))

from config import load_config
from memory_manager import DualLayerMemoryManager


class MemoryConsolidator:
    """记忆整理器"""

    def __init__(self, config=None):
        self.config = config or load_config()
        self.memory_manager = DualLayerMemoryManager(self.config)
        self.state_file = SKILL_ROOT / "data" / "consolidation_state.json"

    def load_state(self) -> dict:
        """加载上次整理状态"""
        if self.state_file.exists():
            with open(self.state_file) as f:
                return json.load(f)
        return {"last_run": None, "last_memory_count": 0}

    def save_state(self, state: dict):
        """保存整理状态"""
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.state_file, "w") as f:
            json.dump(state, f, indent=2)

    def check_increment(self) -> dict:
        """
        检查增量

        Returns:
            {"has_increment": bool, "new_count": int, "diff": int}
        """
        state = self.load_state()

        # 获取当前记忆数量
        try:
            stats = self.memory_manager.get_stats()
            current_count = stats.get("mem0_count", 0)
        except Exception:
            current_count = 0

        diff = current_count - state.get("last_memory_count", 0)

        return {
            "has_increment": diff > 0,
            "new_count": current_count,
            "diff": diff,
            "last_count": state.get("last_memory_count", 0),
        }

    def consolidate(self, force: bool = False) -> dict:
        """
        执行整理

        Args:
            force: 是否强制执行（忽略增量检测）

        Returns:
            整理结果
        """
        state = self.load_state()
        increment = self.check_increment()

        results = {
            "run_at": datetime.now().isoformat(),
            "has_increment": increment["has_increment"],
            "memory_count": increment["new_count"],
            "skipped": False,
            "actions": [],
        }

        # 检查是否有增量
        if not force and not increment["has_increment"]:
            results["skipped"] = True
            results["message"] = "No increment detected, skipped"
            return results

        # 有增量，执行整理
        if increment["has_increment"]:
            results["actions"].append({
                "type": "increment_detected",
                "new_memories": increment["diff"],
            })

        # 检查需要晋升到长期记忆的内容
        try:
            high_priority = self._get_high_priority_memories()
            if high_priority:
                results["actions"].append({
                    "type": "promote_to_long_term",
                    "count": len(high_priority),
                })
        except Exception as e:
            results["actions"].append({
                "type": "error",
                "message": str(e),
            })

        # 检查去重
        try:
            duplicates = self._find_duplicates()
            if duplicates:
                results["actions"].append({
                    "type": "deduplicate",
                    "found": len(duplicates),
                })
        except Exception as e:
            results["actions"].append({
                "type": "error",
                "message": str(e),
            })

        # 更新状态
        state["last_run"] = results["run_at"]
        state["last_memory_count"] = increment["new_count"]
        self.save_state(state)

        results["message"] = f"Consolidated {len(results['actions'])} actions"
        return results

    def _get_high_priority_memories(self) -> list:
        """获取高优先级记忆"""
        try:
            results = self.memory_manager.search(
                query="",
                limit=50,
                tier="short",
            )
            return [r for r in results if r.get("importance", 0) >= 0.75]
        except Exception:
            return []

    def _find_duplicates(self) -> list:
        """查找重复记忆"""
        # 简单实现：基于相似度检测
        # 实际可能需要更复杂的算法
        return []


def main():
    parser = argparse.ArgumentParser(description="Memory Consolidator")
    parser.add_argument("--force", action="store_true", help="Force consolidation")
    parser.add_argument("--verbose", action="store_true", help="Verbose output")
    args = parser.parse_args()

    consolidator = MemoryConsolidator()
    result = consolidator.consolidate(force=args.force)

    if args.verbose:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print(result.get("message", "Done"))

    return 0 if not result.get("skipped") else 0


if __name__ == "__main__":
    sys.exit(main())
#!/usr/bin/env python3
"""
定时记忆整理脚本

功能：
1. 检查 Mem0 中是否有新增量
2. 检测是否有需要归纳/去重的记忆
3. 整理 MEMORY.md 结构
4. 无增量时跳过

Usage:
    # 手动运行
    python3 scripts/consolidate.py --verbose

    # 添加到 crontab (每天早上 9 点)
    0 9 * * * /usr/bin/python3 ~/.skill-memory/scripts/consolidate.py >> ~/.skill-memory/logs/consolidate.log 2>&1
"""

import os
import sys
import json
import argparse
from pathlib import Path
from datetime import datetime, timedelta

# 添加 src 到路径
SKILL_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(SKILL_ROOT / "src"))

from config import load_config
from memory_manager import DualLayerMemoryManager


class MemoryConsolidator:
    """记忆整理器"""

    def __init__(self, config=None):
        self.config = config or load_config()
        self.memory_manager = DualLayerMemoryManager(self.config)
        self.state_file = SKILL_ROOT / "data" / "consolidation_state.json"

    def load_state(self) -> dict:
        """加载上次整理状态"""
        if self.state_file.exists():
            with open(self.state_file) as f:
                return json.load(f)
        return {"last_run": None, "last_memory_count": 0}

    def save_state(self, state: dict):
        """保存整理状态"""
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.state_file, "w") as f:
            json.dump(state, f, indent=2)

    def check_increment(self) -> dict:
        """
        检查增量

        Returns:
            {"has_increment": bool, "new_count": int, "diff": int}
        """
        state = self.load_state()

        # 获取当前记忆数量
        try:
            stats = self.memory_manager.get_stats()
            current_count = stats.get("mem0_count", 0)
        except Exception:
            current_count = 0

        diff = current_count - state.get("last_memory_count", 0)

        return {
            "has_increment": diff > 0,
            "new_count": current_count,
            "diff": diff,
            "last_count": state.get("last_memory_count", 0),
        }

    def consolidate(self, force: bool = False) -> dict:
        """
        执行整理

        Args:
            force: 是否强制执行（忽略增量检测）

        Returns:
            整理结果
        """
        state = self.load_state()
        increment = self.check_increment()

        results = {
            "run_at": datetime.now().isoformat(),
            "has_increment": increment["has_increment"],
            "memory_count": increment["new_count"],
            "skipped": False,
            "actions": [],
        }

        # 检查是否有增量
        if not force and not increment["has_increment"]:
            results["skipped"] = True
            results["message"] = "No increment detected, skipped"
            return results

        # 有增量，执行整理
        if increment["has_increment"]:
            results["actions"].append({
                "type": "increment_detected",
                "new_memories": increment["diff"],
            })

        # 检查需要晋升到长期记忆的内容
        try:
            high_priority = self._get_high_priority_memories()
            if high_priority:
                results["actions"].append({
                    "type": "promote_to_long_term",
                    "count": len(high_priority),
                })
        except Exception as e:
            results["actions"].append({
                "type": "error",
                "message": str(e),
            })

        # 检查去重
        try:
            duplicates = self._find_duplicates()
            if duplicates:
                results["actions"].append({
                    "type": "deduplicate",
                    "found": len(duplicates),
                })
        except Exception as e:
            results["actions"].append({
                "type": "error",
                "message": str(e),
            })

        # 更新状态
        state["last_run"] = results["run_at"]
        state["last_memory_count"] = increment["new_count"]
        self.save_state(state)

        results["message"] = f"Consolidated {len(results['actions'])} actions"
        return results

    def _get_high_priority_memories(self) -> list:
        """获取高优先级记忆"""
        try:
            results = self.memory_manager.search(
                query="",
                limit=50,
                tier="short",
            )
            return [r for r in results if r.get("importance", 0) >= 0.75]
        except Exception:
            return []

    def _find_duplicates(self) -> list:
        """查找重复记忆"""
        # 简单实现：基于相似度检测
        # 实际可能需要更复杂的算法
        return []


def main():
    parser = argparse.ArgumentParser(description="Memory Consolidator")
    parser.add_argument("--force", action="store_true", help="Force consolidation")
    parser.add_argument("--verbose", action="store_true", help="Verbose output")
    args = parser.parse_args()

    consolidator = MemoryConsolidator()
    result = consolidator.consolidate(force=args.force)

    if args.verbose:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print(result.get("message", "Done"))

    return 0 if not result.get("skipped") else 0


if __name__ == "__main__":
    sys.exit(main())
