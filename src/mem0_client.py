"""
Mem0 客户端封装
支持向量存储、语义检索、混合搜索
"""

import os
import json
import time
import hashlib
from pathlib import Path
from typing import List, Optional, Dict, Any, Union
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
import requests

try:
    from mem0 import Memory
    MEM0_AVAILABLE = True
except ImportError:
    MEM0_AVAILABLE = False

# 导入自定义 MiniMax embedder
CUSTOM_EMBEDDER_AVAILABLE = False
MiniMaxEmbedding = None
try:
    # 尝试多种导入路径
    import importlib.util
    spec = importlib.util.find_spec('src.mem0_embedder')
    if spec is None:
        spec = importlib.util.find_spec('mem0_embedder')
    
    if spec is not None:
        from src.mem0_embedder import MiniMaxEmbedding
        CUSTOM_EMBEDDER_AVAILABLE = True
except ImportError:
    try:
        from mem0_embedder import MiniMaxEmbedding
        CUSTOM_EMBEDDER_AVAILABLE = True
    except ImportError:
        pass


@dataclass
class SearchResult:
    """搜索结果"""
    id: str
    content: str
    score: float
    metadata: Dict[str, Any]
    created_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class Mem0Client:
    """
    Mem0 客户端封装
    支持：
    - 本地 Qdrant 后端
    - 多 embedding 提供商
    - 向量 + 关键词混合搜索
    """

    def __init__(
        self,
        api_key: str = "",
        llm_provider: str = "openai",
        embedding_provider: str = "openai",
        llm_model: str = "gpt-4o-mini",
        embedding_model: str = "text-embedding-3-small",
        base_url: Optional[str] = None,
        qdrant_host: str = "localhost",
        qdrant_port: int = 6333,
        collection_name: str = "qoder_memory",
    ):
        # 支持多种 API Key 环境变量
        self.api_key = (
            api_key
            or os.environ.get("SKILL_MEMORY_API_KEY", "")
            or os.environ.get("OPENAI_API_KEY", "")
            or os.environ.get("MINIMAX_API_KEY", "")
        )
        # Mem0 内部需要 OPENAI_API_KEY
        if self.api_key:
            os.environ["OPENAI_API_KEY"] = self.api_key

        self.llm_provider = llm_provider
        self.embedding_provider = embedding_provider
        self.llm_model = llm_model
        self.embedding_model = embedding_model
        # MiniMax API base URL
        self.base_url = base_url or os.environ.get("SKILL_MEMORY_MINIMAX_LLM_BASE_URL", "")
        self.qdrant_host = qdrant_host
        self.qdrant_port = qdrant_port
        self.collection_name = collection_name
        self.vector_weight = 0.7
        self.keyword_weight = 0.3

        # 初始化 Mem0（如果可用）
        self.memory = None
        self._initialized = False

    def _init_memory(self) -> bool:
        """初始化 Mem0"""
        if self._initialized:
            return self.memory is not None

        self._initialized = True

        if not MEM0_AVAILABLE:
            print("Warning: mem0 not installed, using fallback mode")
            return False

        try:
            # 确保 OPENAI_API_KEY 环境变量被设置（Mem0 内部使用）
            if self.api_key:
                os.environ["OPENAI_API_KEY"] = self.api_key

            # 配置 LLM provider
            llm_config = {
                "provider": self.llm_provider if self.llm_provider != "openai" else "openai",
                "config": {
                    "api_key": self.api_key,
                    "model": self.llm_model,
                }
            }
            if self.llm_provider == "minimax":
                llm_config["config"]["model"] = self.llm_model
                if self.base_url:
                    llm_config["config"]["minimax_base_url"] = self.base_url

            # 配置 embedder（使用 openai）
            embedder_config = {
                "provider": "openai",
                "config": {
                    "api_key": self.api_key,
                    "model": self.embedding_model,
                }
            }
            if self.base_url:
                embedder_config["config"]["openai_base_url"] = self.base_url

            config = {
                "llm": llm_config,
                "embedder": embedder_config,
                "vector_store": {
                    "provider": "qdrant",
                    "config": {
                        "host": self.qdrant_host,
                        "port": self.qdrant_port,
                        "collection_name": self.collection_name,
                    }
                }
            }
            self.memory = Memory.from_config(config)

            # 如果使用 MiniMax，自定义 embedder，需要手动替换
            if self.embedding_provider == "minimax" and CUSTOM_EMBEDDER_AVAILABLE:
                from mem0.configs.embeddings.base import BaseEmbedderConfig
                self.memory.embedding_model = MiniMaxEmbedding(BaseEmbedderConfig(
                    api_key=self.api_key,
                    model=self.embedding_model,
                    openai_base_url=self.base_url,
                ))

            return True
        except Exception as e:
            print(f"Warning: Failed to initialize Mem0: {e}")
            return False

    def _get_embedding(self, text: str) -> List[float]:
        """获取文本嵌入向量"""
        if self.embedding_provider == "openai":
            return self._get_openai_embedding(text)
        elif self.embedding_provider == "minimax":
            return self._get_minimax_embedding(text)
        else:
            # 降级：使用哈希作为简单向量
            return self._hash_embedding(text)

    def _get_openai_embedding(self, text: str) -> List[float]:
        """OpenAI Embedding"""
        try:
            response = requests.post(
                "https://api.openai.com/v1/embeddings",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.embedding_model,
                    "input": text,
                },
                timeout=30,
            )
            response.raise_for_status()
            data = response.json()
            return data["data"][0]["embedding"]
        except Exception as e:
            print(f"OpenAI embedding failed: {e}, using hash fallback")
            return self._hash_embedding(text)

    def _get_minimax_embedding(self, text: str) -> List[float]:
        """MiniMax Embedding"""
        try:
            base_url = self.base_url or "https://api.minimax.io/v1"
            response = requests.post(
                f"{base_url}/embeddings",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.embedding_model,
                    "texts": [text],
                    "type": "db",
                },
                timeout=30,
            )
            response.raise_for_status()
            data = response.json()
            if "vectors" in data:
                return data["vectors"][0]
            elif "data" in data:
                return data["data"][0]["embedding"]
        except Exception as e:
            print(f"MiniMax embedding failed: {e}, using hash fallback")
        return self._hash_embedding(text)

    def _hash_embedding(self, text: str) -> List[float]:
        """降级方案：使用 SHA256 哈希生成伪向量"""
        hash_bytes = hashlib.sha256(text.encode()).digest()
        # 生成固定长度的向量（128维）
        import struct
        vector = []
        for i in range(0, min(len(hash_bytes), 128), 4):
            val = struct.unpack('f', hash_bytes[i:i+4])[0]
            vector.append(val)
        # 补齐到128维
        while len(vector) < 128:
            vector.append(0.0)
        # L2 归一化
        import math
        norm = math.sqrt(sum(v*v for v in vector))
        if norm > 0:
            vector = [v/norm for v in vector]
        return vector

    def add(
        self,
        content: str,
        user_id: str = "default",
        metadata: Optional[Dict[str, Any]] = None,
        infer: bool = True,
    ) -> Dict[str, Any]:
        """
        添加记忆

        Args:
            content: 记忆内容
            user_id: 用户 ID
            metadata: 附加元数据
            infer: 是否让 LLM 推断

        Returns:
            包含 id 的字典
        """
        if not self._init_memory():
            # 降级模式：直接存储
            return {
                "id": self._generate_id(content),
                "content": content,
                "metadata": metadata or {},
            }

        try:
            # Mem0 需要 OPENAI_API_KEY 环境变量
            os.environ["OPENAI_API_KEY"] = self.api_key

            result = self.memory.add(
                messages=[{"role": "user", "content": content}],
                user_id=user_id,
                metadata=metadata or {},
                infer=infer,
            )
            return result
        except Exception as e:
            print(f"Mem0 add failed: {e}")
            return {
                "id": self._generate_id(content),
                "content": content,
                "metadata": metadata or {},
            }

    def search(
        self,
        query: str,
        user_id: str = "default",
        limit: int = 5,
    ) -> List[SearchResult]:
        """
        搜索记忆（混合搜索）

        Args:
            query: 查询字符串
            user_id: 用户 ID
            limit: 返回结果数量

        Returns:
            搜索结果列表
        """
        if not self._init_memory():
            return []

        try:
            results = self.memory.search(
                query=query,
                user_id=user_id,
                limit=limit,
            )

            # 统一结果格式
            parsed_results = []

            # 处理不同的返回格式
            if results is None:
                items = []
            elif isinstance(results, dict):
                items = results.get('results', results.get('memories', []))
            elif isinstance(results, list):
                items = results
            else:
                items = []

            for item in items[:limit]:
                if isinstance(item, dict):
                    parsed_results.append(SearchResult(
                        id=item.get("id", ""),
                        content=item.get("content", ""),
                        score=item.get("score", 0.0),
                        metadata=item.get("metadata", {}),
                        created_at=item.get("created_at"),
                    ))
                else:
                    parsed_results.append(SearchResult(
                        id=str(item),
                        content=str(item),
                        score=0.0,
                        metadata={},
                    ))

            return parsed_results
        except Exception as e:
            print(f"Mem0 search failed: {e}")
            return []

    def get_all(
        self,
        user_id: str = "default",
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        获取所有记忆

        Args:
            user_id: 用户 ID
            limit: 返回数量限制

        Returns:
            记忆列表
        """
        if not self._init_memory():
            return []

        try:
            results = self.memory.get_all(user_id=user_id)
            # Mem0 返回 {'results': [...]} 或直接返回列表
            items = results.get('results', []) if isinstance(results, dict) else results
            # 标准化字段名
            for item in items:
                if isinstance(item, dict):
                    # Mem0 使用 'memory' 字段存储内容
                    if 'memory' in item and 'text' not in item:
                        item['text'] = item['memory']
                    if 'data' in item and 'text' not in item:
                        item['text'] = item.pop('data')
            return items[:limit]
        except Exception as e:
            print(f"Mem0 get_all failed: {e}")
            return []

    def delete(self, memory_id: str, user_id: str = "default") -> bool:
        """删除记忆"""
        if not self._init_memory():
            return False

        try:
            self.memory.delete(memory_id, user_id=user_id)
            return True
        except Exception as e:
            print(f"Mem0 delete failed: {e}")
            return False

    def update(
        self,
        memory_id: str,
        content: str,
        user_id: str = "default",
    ) -> bool:
        """更新记忆"""
        if not self._init_memory():
            return False

        try:
            # Mem0 不直接支持 update，先删除再添加
            self.memory.delete(memory_id, user_id=user_id)
            self.memory.add(
                messages=[{"role": "user", "content": content}],
                user_id=user_id,
            )
            return True
        except Exception as e:
            print(f"Mem0 update failed: {e}")
            return False

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        try:
            all_memories = self.get_all(limit=10000)
            return {
                "total": len(all_memories),
                "backend": "mem0" if self._init_memory() else "fallback",
                "qdrant_url": f"http://{self.qdrant_host}:{self.qdrant_port}",
                "collection": self.collection_name,
            }
        except Exception as e:
            return {"error": str(e)}

    def _generate_id(self, content: str) -> str:
        """生成记忆 ID"""
        timestamp = int(time.time())
        return f"mem_{hashlib.md5(content.encode()).hexdigest()[:8]}_{timestamp}"

    def health_check(self) -> bool:
        """检查服务健康状态"""
        try:
            # 检查 Qdrant
            response = requests.get(
                f"http://{self.qdrant_host}:{self.qdrant_port}/health",
                timeout=5,
            )
            return response.status_code == 200
        except Exception:
            return False
"""
Mem0 客户端封装
支持向量存储、语义检索、混合搜索
"""

import os
import json
import time
import hashlib
from pathlib import Path
from typing import List, Optional, Dict, Any, Union
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
import requests

try:
    from mem0 import Memory
    MEM0_AVAILABLE = True
except ImportError:
    MEM0_AVAILABLE = False

# 导入自定义 MiniMax embedder
CUSTOM_EMBEDDER_AVAILABLE = False
MiniMaxEmbedding = None
try:
    # 尝试多种导入路径
    import importlib.util
    spec = importlib.util.find_spec('src.mem0_embedder')
    if spec is None:
        spec = importlib.util.find_spec('mem0_embedder')
    
    if spec is not None:
        from src.mem0_embedder import MiniMaxEmbedding
        CUSTOM_EMBEDDER_AVAILABLE = True
except ImportError:
    try:
        from mem0_embedder import MiniMaxEmbedding
        CUSTOM_EMBEDDER_AVAILABLE = True
    except ImportError:
        pass


