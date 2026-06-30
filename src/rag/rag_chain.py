"""RAG 主链。

整合检索 → Prompt → LLM → 答案。
支持普通问答和学术引证模式。
"""

from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from loguru import logger

from src.core.llm import get_llm
from src.prompts.loader import load_prompt
from src.rag.hybrid_search import HybridSearcher


class RAGChain:
    """RAG 主链"""

    def __init__(self, searcher: HybridSearcher | None = None):
        """初始化。

        Args:
            searcher: 混合检索器
        """
        self.searcher = searcher or HybridSearcher()
        self.llm = get_llm(model="deepseek", temperature=0.1)

    def query(
        self,
        question: str,
        top_k: int = 5,
        prompt_name: str = "academic_qa",
        filter_conditions: dict[str, Any] | None = None,
        language: str = "zh",
    ) -> dict[str, Any]:
        """RAG 查询。

        Args:
            question: 用户问题
            top_k: 检索数量
            prompt_name: Prompt 模板名
            filter_conditions: 过滤条件
            language: 输出语言

        Returns:
            {"answer": ..., "contexts": [...], "sources": [...]}
        """
        # 1. 检索
        contexts = self.searcher.search(question, top_k=top_k, filter_conditions=filter_conditions)

        if not contexts:
            logger.warning(f"未检索到相关内容: {question}")
            return {
                "answer": "抱歉，知识库中未找到相关内容。",
                "contexts": [],
                "sources": [],
            }

        # 2. 加载 Prompt
        prompt = load_prompt(prompt_name, language=language)

        # 3. 构造 context
        context_text = self._format_contexts(contexts)

        # 4. 调用 LLM
        messages = [
            SystemMessage(content=prompt["system"]),
            HumanMessage(
                content=prompt["user"].format(
                    question=question,
                    context=context_text,
                )
            ),
        ]
        response = self.llm.invoke(messages)

        # 5. 提取来源
        sources = self._extract_sources(contexts)

        return {
            "answer": response.content,
            "contexts": contexts,
            "sources": sources,
        }

    @staticmethod
    def _format_contexts(contexts: list[dict]) -> str:
        """格式化检索结果为 Prompt context"""
        formatted = []
        for i, ctx in enumerate(contexts, 1):
            meta = ctx.get("metadata", {})
            philosopher = meta.get("philosopher", "未知")
            book = meta.get("book", "未知")
            location = meta.get("section", meta.get("location", ""))
            text = ctx.get("text", "")
            formatted.append(
                f"[{i}] 《{book}》{philosopher} {location}\n{text}\n"
            )
        return "\n".join(formatted)

    @staticmethod
    def _extract_sources(contexts: list[dict]) -> list[dict]:
        """提取引用来源"""
        sources = []
        for i, ctx in enumerate(contexts, 1):
            meta = ctx.get("metadata", {})
            sources.append(
                {
                    "index": i,
                    "philosopher": meta.get("philosopher"),
                    "book": meta.get("book"),
                    "location": meta.get("section", meta.get("location")),
                    "score": ctx.get("rrf_score", ctx.get("score", 0)),
                }
            )
        return sources