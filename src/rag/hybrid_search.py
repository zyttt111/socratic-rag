"""混合检索（BM25 + 向量 + RRF 融合）。

RRF (Reciprocal Rank Fusion) 是一种简单有效的多路召回融合方法。
"""

from typing import Any

from langchain_core.documents import Document
from loguru import logger

from src.core.llm import get_embeddings
from src.rag.bm25 import BM25Index
from src.rag.qdrant_client import get_qdrant_client, search as qdrant_search


class HybridSearcher:
    """混合检索器"""

    def __init__(
        self,
        bm25_weight: float = 0.5,
        vector_weight: float = 0.5,
        rrf_k: int = 60,
    ):
        """初始化。

        Args:
            bm25_weight: BM25 权重
            vector_weight: 向量权重
            rrf_k: RRF 算法的 k 参数
        """
        self.bm25_weight = bm25_weight
        self.vector_weight = vector_weight
        self.rrf_k = rrf_k
        self.bm25_index = BM25Index()
        self.embeddings = get_embeddings()

    def index(self, documents: list[Document]):
        """构建 BM25 索引（向量索引假设已写入 Qdrant）。

        Args:
            documents: Document 列表（用于 BM25）
        """
        self.bm25_index.fit(documents)

    def search(
        self,
        query: str,
        top_k: int = 10,
        filter_conditions: dict[str, Any] | None = None,
    ) -> list[dict]:
        """混合检索。

        Args:
            query: 查询文本
            top_k: 返回数量
            filter_conditions: 过滤条件

        Returns:
            融合后的检索结果
        """
        # 1. BM25 检索
        bm25_results = self.bm25_index.search(query, top_k=top_k * 2)

        # 2. 向量检索
        query_vector = self.embeddings.embed_query(query)
        client = get_qdrant_client()
        vector_results = qdrant_search(
            query_vector=query_vector,
            client=client,
            top_k=top_k * 2,
            filter_conditions=filter_conditions,
        )

        # 3. RRF 融合
        fused = self._rrf_fusion(bm25_results, vector_results)

        return fused[:top_k]

    def _rrf_fusion(
        self,
        bm25_results: list[dict],
        vector_results: list[dict],
    ) -> list[dict]:
        """RRF（Reciprocal Rank Fusion）融合。

        score = sum( weight / (k + rank) )
        """
        scores: dict[str, float] = {}
        doc_map: dict[str, dict] = {}

        # BM25 贡献
        for rank, doc in enumerate(bm25_results):
            doc_id = self._doc_id(doc)
            scores[doc_id] = scores.get(doc_id, 0) + self.bm25_weight / (self.rrf_k + rank + 1)
            doc_map[doc_id] = doc

        # 向量贡献
        for rank, doc in enumerate(vector_results):
            doc_id = self._doc_id(doc)
            scores[doc_id] = scores.get(doc_id, 0) + self.vector_weight / (self.rrf_k + rank + 1)
            doc_map[doc_id] = doc

        # 排序
        sorted_ids = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)

        results = []
        for doc_id in sorted_ids:
            doc = doc_map[doc_id]
            doc["rrf_score"] = scores[doc_id]
            results.append(doc)

        return results

    @staticmethod
    def _doc_id(doc: dict) -> str:
        """生成文档唯一 ID（用于融合去重）"""
        # 用文本前 100 字符作为 ID（简化版）
        return doc.get("text", "")[:100]