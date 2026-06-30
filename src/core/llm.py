"""LLM 调用封装。

统一封装 DeepSeek-V3 和 Claude，支持：
- 普通调用
- 异步调用
- 流式输出
- 自动重试
- Token 计数
"""

from functools import lru_cache
from typing import AsyncIterator, Iterator

from langchain_anthropic import ChatAnthropic
from langchain_deepseek import ChatDeepSeek
from langchain_huggingface import HuggingFaceEmbeddings
from loguru import logger
from sentence_transformers import CrossEncoder
from tenacity import retry, stop_after_attempt, wait_exponential

from src.core.settings import settings


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=10),
)
def get_llm(
    model: str = "deepseek",
    temperature: float = 0.1,
    max_tokens: int = 4000,
    streaming: bool = False,
):
    """获取 LLM 实例。

    Args:
        model: "deepseek" / "claude"
        temperature: 0-1，越低越稳定
        max_tokens: 最大输出 token
        streaming: 是否流式输出

    Returns:
        LangChain ChatModel 实例
    """
    if model == "deepseek":
        if not settings.deepseek_api_key:
            raise ValueError("DEEPSEEK_API_KEY 未配置，请在 .env 中设置")
        return ChatDeepSeek(
            model=settings.deepseek_model,
            api_key=settings.deepseek_api_key,
            base_url=settings.deepseek_base_url,
            temperature=temperature,
            max_tokens=max_tokens,
            streaming=streaming,
        )
    elif model == "claude":
        if not settings.anthropic_api_key:
            raise ValueError("ANTHROPIC_API_KEY 未配置，请在 .env 中设置")
        return ChatAnthropic(
            model=settings.claude_model,
            api_key=settings.anthropic_api_key,
            temperature=temperature,
            max_tokens=max_tokens,
            streaming=streaming,
        )
    else:
        raise ValueError(f"不支持的 model: {model}")


@lru_cache
def get_embeddings():
    """获取 Embedding 模型（单例）。

    使用 bge-large-zh-v1.5，本地免费，中文 SOTA。
    """
    logger.info(f"加载 Embedding 模型: {settings.embedding_model}")
    return HuggingFaceEmbeddings(
        model_name=settings.embedding_model,
        model_kwargs={"device": settings.embedding_device},
        encode_kwargs={"normalize_embeddings": True},
    )


@lru_cache
def get_reranker():
    """获取 Rerank 模型（单例，可选）。

    使用 bge-reranker-large，提升检索精度 10-15%。
    """
    if not settings.use_rerank:
        return None
    logger.info(f"加载 Rerank 模型: {settings.rerank_model}")
    return CrossEncoder(settings.rerank_model, device=settings.embedding_device)


def count_tokens(text: str, model: str = "deepseek") -> int:
    """估算 token 数量。

    简单实现：中文 1.5 token/字，英文 1 token/词。
    """
    import re

    # 粗略估算：中文按字符，英文按词
    chinese_chars = len(re.findall(r"[\u4e00-\u9fff]", text))
    english_words = len(re.findall(r"\b[a-zA-Z]+\b", text))
    return int(chinese_chars * 1.5 + english_words)


async def stream_llm(prompt: str, model: str = "deepseek") -> AsyncIterator[str]:
    """异步流式调用 LLM。

    Args:
        prompt: 完整 prompt
        model: "deepseek" / "claude"

    Yields:
        文本片段
    """
    from langchain_core.messages import HumanMessage

    llm = get_llm(model=model, streaming=True)
    async for chunk in llm.astream([HumanMessage(content=prompt)]):
        if chunk.content:
            yield chunk.content