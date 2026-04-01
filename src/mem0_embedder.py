"""
MiniMax Embedding 实现
支持 Mem0 的 EmbedderBase 接口
"""

import os
from typing import Literal, Optional

import requests

from mem0.configs.embeddings.base import BaseEmbedderConfig
from mem0.embeddings.base import EmbeddingBase


class MiniMaxEmbedding(EmbeddingBase):
    """
    MiniMax Embedding 实现
    使用 OpenAI-compatible 接口调用 MiniMax embedding API
    """

    def __init__(self, config: Optional[BaseEmbedderConfig] = None):
        super().__init__(config)

        self.config.model = self.config.model or "embo-01"

        api_key = self.config.api_key or os.getenv("MINIMAX_API_KEY") or os.getenv("OPENAI_API_KEY")
        base_url = (
            self.config.openai_base_url
            or os.getenv("MINIMAX_BASE_URL")
            or os.getenv("OPENAI_BASE_URL")
            or "https://api.minimaxi.com/v1"
        )

        self.client = MiniMaxClient(api_key=api_key, base_url=base_url)

    def embed(self, text, memory_action: Optional[Literal["add", "search", "update"]] = None):
        """
        获取文本的 embedding 向量

        Args:
            text (str): 要嵌入的文本
            memory_action: 嵌入类型 (add/search/update)

        Returns:
            list: embedding 向量
        """
        text = text.replace("\n", " ")
        return self.client.embed(text, model=self.config.model)


class MiniMaxClient:
    """MiniMax API 客户端"""

    def __init__(self, api_key: str, base_url: str):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")

    def embed(self, text: str, model: str = "embo-01") -> list:
        """调用 MiniMax embedding API"""
        response = requests.post(
            f"{self.base_url}/embeddings",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "texts": [text],
                "type": "db",
            },
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()
        # MiniMax 返回 {"vectors": [[...]]} 格式
        return data["vectors"][0]
"""
MiniMax Embedding 实现
支持 Mem0 的 EmbedderBase 接口
"""

import os
from typing import Literal, Optional

import requests

from mem0.configs.embeddings.base import BaseEmbedderConfig
from mem0.embeddings.base import EmbeddingBase


class MiniMaxEmbedding(EmbeddingBase):
    """
    MiniMax Embedding 实现
    使用 OpenAI-compatible 接口调用 MiniMax embedding API
    """

    def __init__(self, config: Optional[BaseEmbedderConfig] = None):
        super().__init__(config)

        self.config.model = self.config.model or "embo-01"

        api_key = self.config.api_key or os.getenv("MINIMAX_API_KEY") or os.getenv("OPENAI_API_KEY")
        base_url = (
            self.config.openai_base_url
            or os.getenv("MINIMAX_BASE_URL")
            or os.getenv("OPENAI_BASE_URL")
            or "https://api.minimaxi.com/v1"
        )

        self.client = MiniMaxClient(api_key=api_key, base_url=base_url)

    def embed(self, text, memory_action: Optional[Literal["add", "search", "update"]] = None):
        """
        获取文本的 embedding 向量

        Args:
            text (str): 要嵌入的文本
            memory_action: 嵌入类型 (add/search/update)

        Returns:
            list: embedding 向量
        """
        text = text.replace("\n", " ")
        return self.client.embed(text, model=self.config.model)


class MiniMaxClient:
    """MiniMax API 客户端"""

    def __init__(self, api_key: str, base_url: str):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")

    def embed(self, text: str, model: str = "embo-01") -> list:
        """调用 MiniMax embedding API"""
        response = requests.post(
            f"{self.base_url}/embeddings",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "texts": [text],
                "type": "db",
            },
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()
        # MiniMax 返回 {"vectors": [[...]]} 格式
        return data["vectors"][0]
"""
MiniMax Embedding 实现
支持 Mem0 的 EmbedderBase 接口
"""

import os
from typing import Literal, Optional

import requests

from mem0.configs.embeddings.base import BaseEmbedderConfig
from mem0.embeddings.base import EmbeddingBase


class MiniMaxEmbedding(EmbeddingBase):
    """
    MiniMax Embedding 实现
    使用 OpenAI-compatible 接口调用 MiniMax embedding API
    """

    def __init__(self, config: Optional[BaseEmbedderConfig] = None):
        super().__init__(config)

        self.config.model = self.config.model or "embo-01"

        api_key = self.config.api_key or os.getenv("MINIMAX_API_KEY") or os.getenv("OPENAI_API_KEY")
        base_url = (
            self.config.openai_base_url
            or os.getenv("MINIMAX_BASE_URL")
            or os.getenv("OPENAI_BASE_URL")
            or "https://api.minimaxi.com/v1"
        )

        self.client = MiniMaxClient(api_key=api_key, base_url=base_url)

    def embed(self, text, memory_action: Optional[Literal["add", "search", "update"]] = None):
        """
        获取文本的 embedding 向量

        Args:
            text (str): 要嵌入的文本
            memory_action: 嵌入类型 (add/search/update)

        Returns:
            list: embedding 向量
        """
        text = text.replace("\n", " ")
        return self.client.embed(text, model=self.config.model)


class MiniMaxClient:
    """MiniMax API 客户端"""

    def __init__(self, api_key: str, base_url: str):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")

    def embed(self, text: str, model: str = "embo-01") -> list:
        """调用 MiniMax embedding API"""
        response = requests.post(
            f"{self.base_url}/embeddings",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "texts": [text],
                "type": "db",
            },
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()
        # MiniMax 返回 {"vectors": [[...]]} 格式
        return data["vectors"][0]
