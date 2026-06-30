"""BM25 传统检索。

使用 rank_bm25 实现轻量级 BM25。
中文需要先分词。
"""

from typing import List

import jieba
from langchain_core.documents import Document
from loguru import logger
from rank_bm25 import BM25Okapi


class BM25Index:
    """BM25 索引"""

    def __init__(self, use_jieba: bool = True):
        """初始化。

        Args:
            use_jieba: 是否使用 jieba 中文分词
        """
        self.use_jieba = use_jieba
        self.bm25 = None
        self.documents: List[Document] = []

    def _tokenize(self, text: str) -> List[str]:
        """分词"""
        if self.use_jieba:
            return list(jieba.cut_for_search(text))
        else:
            return text.lower().split()

    def fit(self, documents: List[Document]):
        """构建索引。

        Args:
            documents: Document 列表
        """
        self.documents = documents
        tokenized_corpus = [self._tokenize(doc.page_content) for doc in documents]
        self.bm25 = BM25Okapi(tokenized_corpus)
        logger.info(f"✓ BM25 索引构建完成 ({len(documents)} 个文档)")

    def search(self, query: str, top_k: int = 10) -> List[dict]:
        """检索。

        Args:
            query: 查询文本
            top_k: 返回数量

        Returns:
            [{"text": ..., "metadata": ..., "score": ...}, ...]
        """
        if self.bm25 is None:
            raise ValueError("BM25 索引未构建，请先调用 fit()")

        tokenized_query = self._tokenize(query)
        scores = self.bm25.get_scores(tokenized_query)

        # 取 top_k
        top_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:top_k]

        results = []
        for idx in top_indices:
            results.append(
                {
                    "text": self.documents[idx].page_content,
                    "metadata": self.documents[idx].metadata,
                    "score": float(scores[idx]),
                }
            )

        return results