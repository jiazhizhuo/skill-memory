"""
双层记忆管理器
整合 Mem0 向量检索和 MEMORY.md 持久存储
"""

import os
import json
import re
import hashlib
import time
from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime
from dataclasses import dataclass

try:
    from .config import Mem0Config, load_config
    from .mem0_client import Mem0Client, SearchResult
except ImportError:
    from config import Mem0Config, load_config
    from mem0_client import Mem0Client, SearchResult


# 记忆分类关键词
CATEGORY_KEYWORDS = {
    "preference": ["喜欢", "prefer", "不喜欢", "习惯", "通常", "偏好", "风格", "风格"],
    "project": ["项目", "project", "仓库", "repo", "代码库", "git"],
    "domain": ["技术", "python", "javascript", "rust", "架构", "design"],
    "decision": ["决定", "采用", "选择", "decided", "chose", "选择"],
}


@dataclass
class MemoryEntry:
    """记忆条目"""
    id: str
    content: str
    tier: str  # "mid" | "long"
    category: str  # "general" | "preference" | "project" | "domain"
    importance: float
    source: Optional[str] = None
    created_at: Optional[str] = None
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
        if self.created_at is None:
            self.created_at = datetime.now().isoformat()


class DualLayerMemoryManager:
    """
    双层记忆管理器

    第一层：Mem0 + Qdrant（高速检索）
    第二层：MEMORY.md（持久备份）
    """

    def __init__(self, config: Optional[Mem0Config] = None):
        self.config = config or load_config()
        self.mem0 = Mem0Client(
            api_key=self.config.api_key,
            llm_provider=self.config.llm_provider,
            embedding_provider=self.config.embedding_provider,
            llm_model=self.config.llm_model,
            embedding_model=self.config.embedding_model,
            base_url=self.config.base_url,
            qdrant_host=self.config.qdrant_host,
            qdrant_port=self.config.qdrant_port,
            collection_name=self.config.qdrant_collection,
        )

        # 确保目录存在
        self.config.knowledge_dir.mkdir(parents=True, exist_ok=True)

        # 初始化 MEMORY.md
        self._init_memory_md()

    def _init_memory_md(self) -> None:
        """初始化 MEMORY.md 文件"""
        memory_file = self.config.memory_md_path
        if not memory_file.exists():
            memory_file.write_text("# Memory\n\n")
            self._add_category_headers()

    def _add_category_headers(self) -> None:
        """添加分类标题"""
        categories = ["## Preferences\n\n", "## Projects\n\n", "## Domain Knowledge\n\n", "## General\n\n"]
        self.config.memory_md_path.write_text("\n".join(categories))

    def _categorize(self, content: str) -> str:
        """
        根据内容自动分类

        Args:
            content: 记忆内容

        Returns:
            分类名称
        """
        content_lower = content.lower()

        for category, keywords in CATEGORY_KEYWORDS.items():
            for keyword in keywords:
                if keyword in content_lower:
                    return category

        return "general"

    def _calculate_importance(self, content: str, source: Optional[str] = None) -> float:
        """
        计算内容重要性

        Args:
            content: 内容
            source: 来源

        Returns:
            重要性分数 (0-1)
        """
        importance = 0.5

        # 包含决策/结论 → 提高重要性
        decision_keywords = ["决定", "采用", "选择", "will use", "decided", "chose", "选择"]
        if any(kw in content.lower() for kw in decision_keywords):
            importance += 0.2

        # 包含偏好表达 → 提高重要性
        preference_keywords = ["prefer", "like", "dislike", "不喜欢", "usually", "习惯", "偏好"]
        if any(kw in content.lower() for kw in preference_keywords):
            importance += 0.15

        # 包含项目信息 → 提高重要性
        project_keywords = ["project", "项目", "repository", "repo", "代码库"]
        if any(kw in content.lower() for kw in project_keywords):
            importance += 0.15

        # 包含代码/配置 → 提高重要性
        code_keywords = ["config", "setting", "配置", "代码", "implementation"]
        if any(kw in content.lower() for kw in code_keywords):
            importance += 0.1

        # 从重要来源来的 → 提高重要性
        if source in ["user_explicit", "decision"]:
            importance += 0.1

        return min(importance, 1.0)

    def _should_promote(self, importance: float) -> bool:
        """判断是否应该晋升到长期记忆"""
        return importance >= self.config.promotion_threshold

    def _generate_id(self, content: str) -> str:
        """生成记忆 ID"""
        timestamp = int(time.time())
        return f"mem_{hashlib.md5(content.encode()).hexdigest()[:8]}_{timestamp}"

    # === 第一层操作 (Mem0) ===

    def add_to_mem0(
        self,
        content: str,
        tier: str = "mid",
        importance: float = 0.5,
        metadata: Optional[Dict[str, Any]] = None,
        user_id: str = "default",
    ) -> MemoryEntry:
        """
        添加记忆到 Mem0

        Args:
            content: 记忆内容
            tier: 层级 ("mid" | "long")
            importance: 重要性
            metadata: 元数据
            user_id: 用户 ID

        Returns:
            MemoryEntry
        """
        category = self._categorize(content)

        meta = metadata or {}
        meta.update({
            "tier": tier,
            "category": category,
            "importance": importance,
            "source": "mem0",
        })

        result = self.mem0.add(
            content=content,
            user_id=user_id,
            metadata=meta,
            infer=False,  # 禁用 LLM 推断，我们已手动分类
        )

        memory_id = result.get("id", self._generate_id(content))

        return MemoryEntry(
            id=memory_id,
            content=content,
            tier=tier,
            category=category,
            importance=importance,
            source="mem0",
            metadata=meta,
        )

    def search_mem0(
        self,
        query: str,
        limit: int = 5,
        user_id: str = "default",
    ) -> List[MemoryEntry]:
        """
        搜索 Mem0

        Args:
            query: 查询
            limit: 结果数量
            user_id: 用户 ID

        Returns:
            记忆列表
        """
        results = self.mem0.search(query=query, user_id=user_id, limit=limit)

        entries = []
        for result in results:
            meta = result.metadata or {}
            entries.append(MemoryEntry(
                id=result.id,
                content=result.content,
                tier=meta.get("tier", "mid"),
                category=meta.get("category", "general"),
                importance=meta.get("importance", 0.5),
                source="mem0",
                created_at=result.created_at,
                metadata=meta,
            ))

        return entries

    # === 第二层操作 (MEMORY.md) ===

    def add_to_memory_md(
        self,
        content: str,
        category: Optional[str] = None,
        source: Optional[str] = None,
    ) -> bool:
        """
        添加到 MEMORY.md

        Args:
            content: 内容
            category: 分类
            source: 来源

        Returns:
            是否成功
        """
        category = category or self._categorize(content)

        # 构建条目
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        lines = [
            f"\n### {timestamp}",
            content,
        ]
        if source:
            lines.append(f"<!-- source: {source} -->")

        entry_text = "\n".join(lines)

        # 追加到对应分类
        return self._append_to_category(category, entry_text)

    def _append_to_category(self, category: str, entry: str) -> bool:
        """追加内容到指定分类"""
        try:
            memory_file = self.config.memory_md_path
            content = memory_file.read_text()

            # 查找分类位置
            category_header = f"## {category.capitalize()}\n\n"

            if category_header in content:
                # 找到分类，追加
                pos = content.find(category_header) + len(category_header)
                new_content = content[:pos] + entry + "\n" + content[pos:]
            else:
                # 未找到分类，追加到末尾
                new_content = content + f"\n### {category.capitalize()}\n" + entry + "\n"

            memory_file.write_text(new_content)
            return True

        except Exception as e:
            print(f"Failed to append to MEMORY.md: {e}")
            return False

    def search_memory_md(
        self,
        query: str,
        category: Optional[str] = None,
    ) -> List[str]:
        """
        搜索 MEMORY.md

        Args:
            query: 查询关键词
            category: 分类过滤

        Returns:
            匹配的内容列表
        """
        try:
            memory_file = self.config.memory_md_path
            if not memory_file.exists():
                return []

            content = memory_file.read_text()
            lines = content.split("\n")

            # 简单关键词匹配
            results = []
            in_category = category is None

            for i, line in enumerate(lines):
                # 检查分类头
                if line.startswith("## "):
                    cat = line[3:].strip().lower()
                    in_category = category is None or cat == category.lower()
                    continue

                # 匹配关键词
                if in_category and query.lower() in line.lower():
                    # 获取完整条目
                    entry_lines = []
                    for j in range(i, min(i+10, len(lines))):
                        if lines[j].startswith("## ") or lines[j].startswith("### "):
                            break
                        entry_lines.append(lines[j])
                    results.append("\n".join(entry_lines))

            return results[:10]

        except Exception as e:
            print(f"Failed to search MEMORY.md: {e}")
            return []

    def get_long_term_memory(self) -> str:
        """获取长期记忆内容"""
        try:
            memory_file = self.config.memory_md_path
            if memory_file.exists():
                return memory_file.read_text()
            return ""
        except Exception as e:
            print(f"Failed to read MEMORY.md: {e}")
            return ""

    # === 双层统一操作 ===

    def smart_add(
        self,
        content: str,
        importance: Optional[float] = None,
        auto_categorize: bool = True,
        metadata: Optional[Dict[str, Any]] = None,
        user_id: str = "default",
    ) -> Dict[str, Any]:
        """
        智能添加：自动判断层级和分类

        Args:
            content: 内容
            importance: 重要性（自动计算如果为 None）
            auto_categorize: 自动分类
            metadata: 元数据
            user_id: 用户 ID

        Returns:
            结果字典
        """
        # 计算重要性
        if importance is None:
            importance = self._calculate_importance(content)

        category = self._categorize(content) if auto_categorize else "general"

        # 判断层级
        tier = "long" if self._should_promote(importance) else "mid"

        # 添加到 Mem0
        entry = self.add_to_mem0(
            content=content,
            tier=tier,
            importance=importance,
            metadata=metadata,
            user_id=user_id,
        )

        result = {
            "id": entry.id,
            "tier": tier,
            "category": category,
            "importance": importance,
            "promoted": tier == "long",
        }

        # 重要内容同时写入 MEMORY.md
        if tier == "long":
            self.add_to_memory_md(
                content=content,
                category=category,
                source="auto_promotion",
            )
            result["saved_to_md"] = True

        return result

    def smart_search(
        self,
        query: str,
        layers: Optional[List[str]] = None,
        limit: int = 5,
        user_id: str = "default",
    ) -> Dict[str, Any]:
        """
        智能搜索：查询双层记忆

        Args:
            query: 查询
            layers: 搜索哪些层 (["mem0", "memory"])
            limit: 结果数量
            user_id: 用户 ID

        Returns:
            {"mem0": [...], "memory": [...], "merged": [...]}
        """
        if layers is None:
            layers = ["mem0", "memory"]

        result = {
            "mem0": [],
            "memory": [],
            "merged": [],
        }

        # 搜索 Mem0
        if "mem0" in layers:
            mem0_results = self.search_mem0(query=query, limit=limit, user_id=user_id)
            result["mem0"] = [
                {"id": e.id, "content": e.content, "tier": e.tier, "category": e.category}
                for e in mem0_results
            ]

        # 搜索 MEMORY.md
        if "memory" in layers:
            memory_results = self.search_memory_md(query=query)
            result["memory"] = memory_results

        # 合并结果
        merged = []
        seen_contents = set()

        for item in result["mem0"]:
            key = item["content"][:50]  # 使用前50字符去重
            if key not in seen_contents:
                merged.append(item)
                seen_contents.add(key)

        for content in result["memory"][:limit - len(merged)]:
            key = content[:50]
            if key not in seen_contents:
                merged.append({"content": content, "source": "memory_md"})
                seen_contents.add(key)

        result["merged"] = merged

        return result

    # === 统计和管理 ===

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        mem0_stats = self.mem0.get_stats()

        try:
            memory_content = self.config.memory_md_path.read_text()
            line_count = len(memory_content.split("\n"))
            char_count = len(memory_content)
        except Exception:
            line_count = 0
            char_count = 0

        return {
            "mem0": mem0_stats,
            "memory_md": {
                "path": str(self.config.memory_md_path),
                "lines": line_count,
                "chars": char_count,
            },
            "config": {
                "promotion_threshold": self.config.promotion_threshold,
                "mid_ttl_days": self.config.mid_ttl_days,
            },
        }

    def organize_memories(self) -> Dict[str, Any]:
        """
        整理记忆（聚类、去重）

        Returns:
            整理结果
        """
        # TODO: 实现更智能的记忆整理
        return {"status": "not_implemented", "message": "Memory organization is planned for future versions"}

    def backup_memory_md(self, backup_path: Optional[Path] = None) -> Path:
        """备份 MEMORY.md"""
        if backup_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = self.config.knowledge_dir / f"MEMORY_backup_{timestamp}.md"

        source = self.config.memory_md_path
        if source.exists():
            backup_path.write_text(source.read_text())

        return backup_path
"""
双层记忆管理器
整合 Mem0 向量检索和 MEMORY.md 持久存储
"""

import os
import json
import re
import hashlib
import time
from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime
from dataclasses import dataclass

try:
    from .config import Mem0Config, load_config
    from .mem0_client import Mem0Client, SearchResult
except ImportError:
    from config import Mem0Config, load_config
    from mem0_client import Mem0Client, SearchResult


# 记忆分类关键词
CATEGORY_KEYWORDS = {
    "preference": ["喜欢", "prefer", "不喜欢", "习惯", "通常", "偏好", "风格", "风格"],
    "project": ["项目", "project", "仓库", "repo", "代码库", "git"],
    "domain": ["技术", "python", "javascript", "rust", "架构", "design"],
    "decision": ["决定", "采用", "选择", "decided", "chose", "选择"],
}


@dataclass
class MemoryEntry:
    """记忆条目"""
    id: str
    content: str
    tier: str  # "mid" | "long"
    category: str  # "general" | "preference" | "project" | "domain"
    importance: float
    source: Optional[str] = None
    created_at: Optional[str] = None
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
        if self.created_at is None:
            self.created_at = datetime.now().isoformat()


class DualLayerMemoryManager:
    """
    双层记忆管理器

    第一层：Mem0 + Qdrant（高速检索）
    第二层：MEMORY.md（持久备份）
    """

    def __init__(self, config: Optional[Mem0Config] = None):
        self.config = config or load_config()
        self.mem0 = Mem0Client(
            api_key=self.config.api_key,
            llm_provider=self.config.llm_provider,
            embedding_provider=self.config.embedding_provider,
            llm_model=self.config.llm_model,
            embedding_model=self.config.embedding_model,
            base_url=self.config.base_url,
            qdrant_host=self.config.qdrant_host,
            qdrant_port=self.config.qdrant_port,
            collection_name=self.config.qdrant_collection,
        )

        # 确保目录存在
        self.config.knowledge_dir.mkdir(parents=True, exist_ok=True)

        # 初始化 MEMORY.md
        self._init_memory_md()

    def _init_memory_md(self) -> None:
        """初始化 MEMORY.md 文件"""
        memory_file = self.config.memory_md_path
        if not memory_file.exists():
            memory_file.write_text("# Memory\n\n")
            self._add_category_headers()

    def _add_category_headers(self) -> None:
        """添加分类标题"""
        categories = ["## Preferences\n\n", "## Projects\n\n", "## Domain Knowledge\n\n", "## General\n\n"]
        self.config.memory_md_path.write_text("\n".join(categories))

    def _categorize(self, content: str) -> str:
        """
        根据内容自动分类

        Args:
            content: 记忆内容

        Returns:
            分类名称
        """
        content_lower = content.lower()

        for category, keywords in CATEGORY_KEYWORDS.items():
            for keyword in keywords:
                if keyword in content_lower:
                    return category

        return "general"

    def _calculate_importance(self, content: str, source: Optional[str] = None) -> float:
        """
        计算内容重要性

        Args:
            content: 内容
            source: 来源

        Returns:
            重要性分数 (0-1)
        """
        importance = 0.5

        # 包含决策/结论 → 提高重要性
        decision_keywords = ["决定", "采用", "选择", "will use", "decided", "chose", "选择"]
        if any(kw in content.lower() for kw in decision_keywords):
            importance += 0.2

        # 包含偏好表达 → 提高重要性
        preference_keywords = ["prefer", "like", "dislike", "不喜欢", "usually", "习惯", "偏好"]
        if any(kw in content.lower() for kw in preference_keywords):
            importance += 0.15

        # 包含项目信息 → 提高重要性
        project_keywords = ["project", "项目", "repository", "repo", "代码库"]
        if any(kw in content.lower() for kw in project_keywords):
            importance += 0.15

        # 包含代码/配置 → 提高重要性
        code_keywords = ["config", "setting", "配置", "代码", "implementation"]
        if any(kw in content.lower() for kw in code_keywords):
            importance += 0.1

        # 从重要来源来的 → 提高重要性
        if source in ["user_explicit", "decision"]:
            importance += 0.1

        return min(importance, 1.0)

    def _should_promote(self, importance: float) -> bool:
        """判断是否应该晋升到长期记忆"""
        return importance >= self.config.promotion_threshold

    def _generate_id(self, content: str) -> str:
        """生成记忆 ID"""
        timestamp = int(time.time())
        return f"mem_{hashlib.md5(content.encode()).hexdigest()[:8]}_{timestamp}"

    # === 第一层操作 (Mem0) ===

    def add_to_mem0(
        self,
        content: str,
        tier: str = "mid",
        importance: float = 0.5,
        metadata: Optional[Dict[str, Any]] = None,
        user_id: str = "default",
    ) -> MemoryEntry:
        """
        添加记忆到 Mem0

        Args:
            content: 记忆内容
            tier: 层级 ("mid" | "long")
            importance: 重要性
            metadata: 元数据
            user_id: 用户 ID

        Returns:
            MemoryEntry
        """
        category = self._categorize(content)

        meta = metadata or {}
        meta.update({
            "tier": tier,
            "category": category,
            "importance": importance,
            "source": "mem0",
        })

        result = self.mem0.add(
            content=content,
            user_id=user_id,
            metadata=meta,
            infer=False,  # 禁用 LLM 推断，我们已手动分类
        )

        memory_id = result.get("id", self._generate_id(content))

        return MemoryEntry(
            id=memory_id,
            content=content,
            tier=tier,
            category=category,
            importance=importance,
            source="mem0",
            metadata=meta,
        )

    def search_mem0(
        self,
        query: str,
        limit: int = 5,
        user_id: str = "default",
    ) -> List[MemoryEntry]:
        """
        搜索 Mem0

        Args:
            query: 查询
            limit: 结果数量
            user_id: 用户 ID

        Returns:
            记忆列表
        """
        results = self.mem0.search(query=query, user_id=user_id, limit=limit)

        entries = []
        for result in results:
            meta = result.metadata or {}
            entries.append(MemoryEntry(
                id=result.id,
                content=result.content,
                tier=meta.get("tier", "mid"),
                category=meta.get("category", "general"),
                importance=meta.get("importance", 0.5),
                source="mem0",
                created_at=result.created_at,
                metadata=meta,
            ))

        return entries

    # === 第二层操作 (MEMORY.md) ===

    def add_to_memory_md(
        self,
        content: str,
        category: Optional[str] = None,
        source: Optional[str] = None,
    ) -> bool:
        """
        添加到 MEMORY.md

        Args:
            content: 内容
            category: 分类
            source: 来源

        Returns:
            是否成功
        """
        category = category or self._categorize(content)

        # 构建条目
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        lines = [
            f"\n### {timestamp}",
            content,
        ]
        if source:
            lines.append(f"<!-- source: {source} -->")

        entry_text = "\n".join(lines)

        # 追加到对应分类
        return self._append_to_category(category, entry_text)

    def _append_to_category(self, category: str, entry: str) -> bool:
        """追加内容到指定分类"""
        try:
            memory_file = self.config.memory_md_path
            content = memory_file.read_text()

            # 查找分类位置
            category_header = f"## {category.capitalize()}\n\n"

            if category_header in content:
                # 找到分类，追加
                pos = content.find(category_header) + len(category_header)
                new_content = content[:pos] + entry + "\n" + content[pos:]
            else:
                # 未找到分类，追加到末尾
                new_content = content + f"\n### {category.capitalize()}\n" + entry + "\n"

            memory_file.write_text(new_content)
            return True

        except Exception as e:
            print(f"Failed to append to MEMORY.md: {e}")
            return False

    def search_memory_md(
        self,
        query: str,
        category: Optional[str] = None,
    ) -> List[str]:
        """
        搜索 MEMORY.md

        Args:
            query: 查询关键词
            category: 分类过滤

        Returns:
            匹配的内容列表
        """
        try:
            memory_file = self.config.memory_md_path
            if not memory_file.exists():
                return []

            content = memory_file.read_text()
            lines = content.split("\n")

            # 简单关键词匹配
            results = []
            in_category = category is None

            for i, line in enumerate(lines):
                # 检查分类头
                if line.startswith("## "):
                    cat = line[3:].strip().lower()
                    in_category = category is None or cat == category.lower()
                    continue

                # 匹配关键词
                if in_category and query.lower() in line.lower():
                    # 获取完整条目
                    entry_lines = []
                    for j in range(i, min(i+10, len(lines))):
                        if lines[j].startswith("## ") or lines[j].startswith("### "):
                            break
                        entry_lines.append(lines[j])
                    results.append("\n".join(entry_lines))

            return results[:10]

        except Exception as e:
            print(f"Failed to search MEMORY.md: {e}")
            return []

    def get_long_term_memory(self) -> str:
        """获取长期记忆内容"""
        try:
            memory_file = self.config.memory_md_path
            if memory_file.exists():
                return memory_file.read_text()
            return ""
        except Exception as e:
            print(f"Failed to read MEMORY.md: {e}")
            return ""

    # === 双层统一操作 ===

    def smart_add(
        self,
        content: str,
        importance: Optional[float] = None,
        auto_categorize: bool = True,
        metadata: Optional[Dict[str, Any]] = None,
        user_id: str = "default",
    ) -> Dict[str, Any]:
        """
        智能添加：自动判断层级和分类

        Args:
            content: 内容
            importance: 重要性（自动计算如果为 None）
            auto_categorize: 自动分类
            metadata: 元数据
            user_id: 用户 ID

        Returns:
            结果字典
        """
        # 计算重要性
        if importance is None:
            importance = self._calculate_importance(content)

        category = self._categorize(content) if auto_categorize else "general"

        # 判断层级
        tier = "long" if self._should_promote(importance) else "mid"

        # 添加到 Mem0
        entry = self.add_to_mem0(
            content=content,
            tier=tier,
            importance=importance,
            metadata=metadata,
            user_id=user_id,
        )

        result = {
            "id": entry.id,
            "tier": tier,
            "category": category,
            "importance": importance,
            "promoted": tier == "long",
        }

        # 重要内容同时写入 MEMORY.md
        if tier == "long":
            self.add_to_memory_md(
                content=content,
                category=category,
                source="auto_promotion",
            )
            result["saved_to_md"] = True

        return result

    def smart_search(
        self,
        query: str,
        layers: Optional[List[str]] = None,
        limit: int = 5,
        user_id: str = "default",
    ) -> Dict[str, Any]:
        """
        智能搜索：查询双层记忆

        Args:
            query: 查询
            layers: 搜索哪些层 (["mem0", "memory"])
            limit: 结果数量
            user_id: 用户 ID

        Returns:
            {"mem0": [...], "memory": [...], "merged": [...]}
        """
        if layers is None:
            layers = ["mem0", "memory"]

        result = {
            "mem0": [],
            "memory": [],
            "merged": [],
        }

        # 搜索 Mem0
        if "mem0" in layers:
            mem0_results = self.search_mem0(query=query, limit=limit, user_id=user_id)
            result["mem0"] = [
                {"id": e.id, "content": e.content, "tier": e.tier, "category": e.category}
                for e in mem0_results
            ]

        # 搜索 MEMORY.md
        if "memory" in layers:
            memory_results = self.search_memory_md(query=query)
            result["memory"] = memory_results

        # 合并结果
        merged = []
        seen_contents = set()

        for item in result["mem0"]:
            key = item["content"][:50]  # 使用前50字符去重
            if key not in seen_contents:
                merged.append(item)
                seen_contents.add(key)

        for content in result["memory"][:limit - len(merged)]:
            key = content[:50]
            if key not in seen_contents:
                merged.append({"content": content, "source": "memory_md"})
                seen_contents.add(key)

        result["merged"] = merged

        return result

    # === 统计和管理 ===

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        mem0_stats = self.mem0.get_stats()

        try:
            memory_content = self.config.memory_md_path.read_text()
            line_count = len(memory_content.split("\n"))
            char_count = len(memory_content)
        except Exception:
            line_count = 0
            char_count = 0

        return {
            "mem0": mem0_stats,
            "memory_md": {
                "path": str(self.config.memory_md_path),
                "lines": line_count,
                "chars": char_count,
            },
            "config": {
                "promotion_threshold": self.config.promotion_threshold,
                "mid_ttl_days": self.config.mid_ttl_days,
            },
        }

    def organize_memories(self) -> Dict[str, Any]:
        """
        整理记忆（聚类、去重）

        Returns:
            整理结果
        """
        # TODO: 实现更智能的记忆整理
        return {"status": "not_implemented", "message": "Memory organization is planned for future versions"}

    def backup_memory_md(self, backup_path: Optional[Path] = None) -> Path:
        """备份 MEMORY.md"""
        if backup_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = self.config.knowledge_dir / f"MEMORY_backup_{timestamp}.md"

        source = self.config.memory_md_path
        if source.exists():
            backup_path.write_text(source.read_text())

        return backup_path
"""
双层记忆管理器
整合 Mem0 向量检索和 MEMORY.md 持久存储
"""

import os
import json
import re
import hashlib
import time
from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime
from dataclasses import dataclass

try:
    from .config import Mem0Config, load_config
    from .mem0_client import Mem0Client, SearchResult
except ImportError:
    from config import Mem0Config, load_config
    from mem0_client import Mem0Client, SearchResult


# 记忆分类关键词
CATEGORY_KEYWORDS = {
    "preference": ["喜欢", "prefer", "不喜欢", "习惯", "通常", "偏好", "风格", "风格"],
    "project": ["项目", "project", "仓库", "repo", "代码库", "git"],
    "domain": ["技术", "python", "javascript", "rust", "架构", "design"],
    "decision": ["决定", "采用", "选择", "decided", "chose", "选择"],
}


@dataclass
class MemoryEntry:
    """记忆条目"""
    id: str
    content: str
    tier: str  # "mid" | "long"
    category: str  # "general" | "preference" | "project" | "domain"
    importance: float
    source: Optional[str] = None
    created_at: Optional[str] = None
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
        if self.created_at is None:
            self.created_at = datetime.now().isoformat()


class DualLayerMemoryManager:
    """
    双层记忆管理器

    第一层：Mem0 + Qdrant（高速检索）
    第二层：MEMORY.md（持久备份）
    """

    def __init__(self, config: Optional[Mem0Config] = None):
        self.config = config or load_config()
        self.mem0 = Mem0Client(
            api_key=self.config.api_key,
            llm_provider=self.config.llm_provider,
            embedding_provider=self.config.embedding_provider,
            llm_model=self.config.llm_model,
            embedding_model=self.config.embedding_model,
            base_url=self.config.base_url,
            qdrant_host=self.config.qdrant_host,
            qdrant_port=self.config.qdrant_port,
            collection_name=self.config.qdrant_collection,
        )

        # 确保目录存在
        self.config.knowledge_dir.mkdir(parents=True, exist_ok=True)

        # 初始化 MEMORY.md
        self._init_memory_md()

    def _init_memory_md(self) -> None:
        """初始化 MEMORY.md 文件"""
        memory_file = self.config.memory_md_path
        if not memory_file.exists():
            memory_file.write_text("# Memory\n\n")
            self._add_category_headers()

    def _add_category_headers(self) -> None:
        """添加分类标题"""
        categories = ["## Preferences\n\n", "## Projects\n\n", "## Domain Knowledge\n\n", "## General\n\n"]
        self.config.memory_md_path.write_text("\n".join(categories))

    def _categorize(self, content: str) -> str:
        """
        根据内容自动分类

        Args:
            content: 记忆内容

        Returns:
            分类名称
        """
        content_lower = content.lower()

        for category, keywords in CATEGORY_KEYWORDS.items():
            for keyword in keywords:
                if keyword in content_lower:
                    return category

        return "general"

    def _calculate_importance(self, content: str, source: Optional[str] = None) -> float:
        """
        计算内容重要性

        Args:
            content: 内容
            source: 来源

        Returns:
            重要性分数 (0-1)
        """
        importance = 0.5

        # 包含决策/结论 → 提高重要性
        decision_keywords = ["决定", "采用", "选择", "will use", "decided", "chose", "选择"]
        if any(kw in content.lower() for kw in decision_keywords):
            importance += 0.2

        # 包含偏好表达 → 提高重要性
        preference_keywords = ["prefer", "like", "dislike", "不喜欢", "usually", "习惯", "偏好"]
        if any(kw in content.lower() for kw in preference_keywords):
            importance += 0.15

        # 包含项目信息 → 提高重要性
        project_keywords = ["project", "项目", "repository", "repo", "代码库"]
        if any(kw in content.lower() for kw in project_keywords):
            importance += 0.15

        # 包含代码/配置 → 提高重要性
        code_keywords = ["config", "setting", "配置", "代码", "implementation"]
        if any(kw in content.lower() for kw in code_keywords):
            importance += 0.1

        # 从重要来源来的 → 提高重要性
        if source in ["user_explicit", "decision"]:
            importance += 0.1

        return min(importance, 1.0)

    def _should_promote(self, importance: float) -> bool:
        """判断是否应该晋升到长期记忆"""
        return importance >= self.config.promotion_threshold

    def _generate_id(self, content: str) -> str:
        """生成记忆 ID"""
        timestamp = int(time.time())
        return f"mem_{hashlib.md5(content.encode()).hexdigest()[:8]}_{timestamp}"

    # === 第一层操作 (Mem0) ===

    def add_to_mem0(
        self,
        content: str,
        tier: str = "mid",
        importance: float = 0.5,
        metadata: Optional[Dict[str, Any]] = None,
        user_id: str = "default",
    ) -> MemoryEntry:
        """
        添加记忆到 Mem0

        Args:
            content: 记忆内容
            tier: 层级 ("mid" | "long")
            importance: 重要性
            metadata: 元数据
            user_id: 用户 ID

        Returns:
            MemoryEntry
        """
        category = self._categorize(content)

        meta = metadata or {}
        meta.update({
            "tier": tier,
            "category": category,
            "importance": importance,
            "source": "mem0",
        })

        result = self.mem0.add(
            content=content,
            user_id=user_id,
            metadata=meta,
            infer=False,  # 禁用 LLM 推断，我们已手动分类
        )

        memory_id = result.get("id", self._generate_id(content))

        return MemoryEntry(
            id=memory_id,
            content=content,
            tier=tier,
            category=category,
            importance=importance,
            source="mem0",
            metadata=meta,
        )

    def search_mem0(
        self,
        query: str,
        limit: int = 5,
        user_id: str = "default",
    ) -> List[MemoryEntry]:
        """
        搜索 Mem0

        Args:
            query: 查询
            limit: 结果数量
            user_id: 用户 ID

        Returns:
            记忆列表
        """
        results = self.mem0.search(query=query, user_id=user_id, limit=limit)

        entries = []
        for result in results:
            meta = result.metadata or {}
            entries.append(MemoryEntry(
                id=result.id,
                content=result.content,
                tier=meta.get("tier", "mid"),
                category=meta.get("category", "general"),
                importance=meta.get("importance", 0.5),
                source="mem0",
                created_at=result.created_at,
                metadata=meta,
            ))

        return entries

    # === 第二层操作 (MEMORY.md) ===

    def add_to_memory_md(
        self,
        content: str,
        category: Optional[str] = None,
        source: Optional[str] = None,
    ) -> bool:
        """
        添加到 MEMORY.md

        Args:
            content: 内容
            category: 分类
            source: 来源

        Returns:
            是否成功
        """
        category = category or self._categorize(content)

        # 构建条目
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        lines = [
            f"\n### {timestamp}",
            content,
        ]
        if source:
            lines.append(f"<!-- source: {source} -->")

        entry_text = "\n".join(lines)

        # 追加到对应分类
        return self._append_to_category(category, entry_text)

    def _append_to_category(self, category: str, entry: str) -> bool:
        """追加内容到指定分类"""
        try:
            memory_file = self.config.memory_md_path
            content = memory_file.read_text()

            # 查找分类位置
            category_header = f"## {category.capitalize()}\n\n"

            if category_header in content:
                # 找到分类，追加
                pos = content.find(category_header) + len(category_header)
                new_content = content[:pos] + entry + "\n" + content[pos:]
            else:
                # 未找到分类，追加到末尾
                new_content = content + f"\n### {category.capitalize()}\n" + entry + "\n"

            memory_file.write_text(new_content)
            return True

        except Exception as e:
            print(f"Failed to append to MEMORY.md: {e}")
            return False

    def search_memory_md(
        self,
        query: str,
        category: Optional[str] = None,
    ) -> List[str]:
        """
        搜索 MEMORY.md

        Args:
            query: 查询关键词
            category: 分类过滤

        Returns:
            匹配的内容列表
        """
        try:
            memory_file = self.config.memory_md_path
            if not memory_file.exists():
                return []

            content = memory_file.read_text()
            lines = content.split("\n")

            # 简单关键词匹配
            results = []
            in_category = category is None

            for i, line in enumerate(lines):
                # 检查分类头
                if line.startswith("## "):
                    cat = line[3:].strip().lower()
                    in_category = category is None or cat == category.lower()
                    continue

                # 匹配关键词
                if in_category and query.lower() in line.lower():
                    # 获取完整条目
                    entry_lines = []
                    for j in range(i, min(i+10, len(lines))):
                        if lines[j].startswith("## ") or lines[j].startswith("### "):
                            break
                        entry_lines.append(lines[j])
                    results.append("\n".join(entry_lines))

            return results[:10]

        except Exception as e:
            print(f"Failed to search MEMORY.md: {e}")
            return []

    def get_long_term_memory(self) -> str:
        """获取长期记忆内容"""
        try:
            memory_file = self.config.memory_md_path
            if memory_file.exists():
                return memory_file.read_text()
            return ""
        except Exception as e:
            print(f"Failed to read MEMORY.md: {e}")
            return ""

    # === 双层统一操作 ===

    def smart_add(
        self,
        content: str,
        importance: Optional[float] = None,
        auto_categorize: bool = True,
        metadata: Optional[Dict[str, Any]] = None,
        user_id: str = "default",
    ) -> Dict[str, Any]:
        """
        智能添加：自动判断层级和分类

        Args:
            content: 内容
            importance: 重要性（自动计算如果为 None）
            auto_categorize: 自动分类
            metadata: 元数据
            user_id: 用户 ID

        Returns:
            结果字典
        """
        # 计算重要性
        if importance is None:
            importance = self._calculate_importance(content)

        category = self._categorize(content) if auto_categorize else "general"

        # 判断层级
        tier = "long" if self._should_promote(importance) else "mid"

        # 添加到 Mem0
        entry = self.add_to_mem0(
            content=content,
            tier=tier,
            importance=importance,
            metadata=metadata,
            user_id=user_id,
        )

        result = {
            "id": entry.id,
            "tier": tier,
            "category": category,
            "importance": importance,
            "promoted": tier == "long",
        }

        # 重要内容同时写入 MEMORY.md
        if tier == "long":
            self.add_to_memory_md(
                content=content,
                category=category,
                source="auto_promotion",
            )
            result["saved_to_md"] = True

        return result

    def smart_search(
        self,
        query: str,
        layers: Optional[List[str]] = None,
        limit: int = 5,
        user_id: str = "default",
    ) -> Dict[str, Any]:
        """
        智能搜索：查询双层记忆

        Args:
            query: 查询
            layers: 搜索哪些层 (["mem0", "memory"])
            limit: 结果数量
            user_id: 用户 ID

        Returns:
            {"mem0": [...], "memory": [...], "merged": [...]}
        """
        if layers is None:
            layers = ["mem0", "memory"]

        result = {
            "mem0": [],
            "memory": [],
            "merged": [],
        }

        # 搜索 Mem0
        if "mem0" in layers:
            mem0_results = self.search_mem0(query=query, limit=limit, user_id=user_id)
            result["mem0"] = [
                {"id": e.id, "content": e.content, "tier": e.tier, "category": e.category}
                for e in mem0_results
            ]

        # 搜索 MEMORY.md
        if "memory" in layers:
            memory_results = self.search_memory_md(query=query)
            result["memory"] = memory_results

        # 合并结果
        merged = []
        seen_contents = set()

        for item in result["mem0"]:
            key = item["content"][:50]  # 使用前50字符去重
            if key not in seen_contents:
                merged.append(item)
                seen_contents.add(key)

        for content in result["memory"][:limit - len(merged)]:
            key = content[:50]
            if key not in seen_contents:
                merged.append({"content": content, "source": "memory_md"})
                seen_contents.add(key)

        result["merged"] = merged

        return result

    # === 统计和管理 ===

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        mem0_stats = self.mem0.get_stats()

        try:
            memory_content = self.config.memory_md_path.read_text()
            line_count = len(memory_content.split("\n"))
            char_count = len(memory_content)
        except Exception:
            line_count = 0
            char_count = 0

        return {
            "mem0": mem0_stats,
            "memory_md": {
                "path": str(self.config.memory_md_path),
                "lines": line_count,
                "chars": char_count,
            },
            "config": {
                "promotion_threshold": self.config.promotion_threshold,
                "mid_ttl_days": self.config.mid_ttl_days,
            },
        }

    def organize_memories(self) -> Dict[str, Any]:
        """
        整理记忆（聚类、去重）

        Returns:
            整理结果
        """
        # TODO: 实现更智能的记忆整理
        return {"status": "not_implemented", "message": "Memory organization is planned for future versions"}

    def backup_memory_md(self, backup_path: Optional[Path] = None) -> Path:
        """备份 MEMORY.md"""
        if backup_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = self.config.knowledge_dir / f"MEMORY_backup_{timestamp}.md"

        source = self.config.memory_md_path
        if source.exists():
            backup_path.write_text(source.read_text())

        return backup_path
