"""核心配置和 LLM 调用。

包含：
- settings: 全局配置（Pydantic Settings）
- llm: DeepSeek / Claude 封装
- i18n: 中英德三语
- config: 配置加载
"""

from src.core.settings import settings
from src.core.llm import get_llm, get_embeddings, get_reranker

__all__ = ["settings", "get_llm", "get_embeddings", "get_reranker"]