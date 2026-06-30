"""Qdrant 向量数据库客户端。

封装 Qdrant 操作：
- 创建 collection
- 批量写入
- 检索
- 删除
"""

from typing import Any

from loguru import logger
from qdrant_client import QdrantClient
from qdrant_client.http import models
from qdrant_client.http.models import Distance, VectorParams

from src.core.settings import settings


def get_qdrant_client() -> QdrantClient:
    """获取 Qdrant 客户端（单例）"""
    return QdrantClient(host=settings.qdrant_host, port=settings.qdrant_port)


def ensure_collection(
    client: QdrantClient | None = None,
    collection_name: str | None = None,
    vector_dim: int | None = None,
    recreate: bool = False,
) -> str:
    """确保 collection 存在。

    Args:
        client: Qdrant 客户端
        collection_name: collection 名
        vector_dim: 向量维度
        recreate: 是否重建

    Returns:
        collection 名
    """
    client = client or get_qdrant_client()
    collection_name = collection_name or settings.qdrant_collection
    vector_dim = vector_dim or settings.embedding_dim

    existing = [c.name for c in client.get_collections().collections]

    if collection_name in existing:
        if recreate:
            logger.warning(f"删除已存在的 collection: {collection_name}")
            client.delete_collection(collection_name)
        else:
            logger.info(f"Collection 已存在: {collection_name}")
            return collection_name

    client.create_collection(
        collection_name=collection_name,
        vectors_config=VectorParams(
            size=vector_dim,
            distance=Distance.COSINE,
        ),
        optimizers_config=models.OptimizersConfigDiff(default_segment_number=2),
        hnsw_config=models.HnswConfigDiff(
            m=16,
            ef_construct=100,
            full_scan_threshold=10000,
        ),
    )
    logger.info(f"✓ 创建 collection: {collection_name} (dim={vector_dim})")
    return collection_name


def upsert_chunks(
    chunks: list[dict[str, Any]],
    client: QdrantClient | None = None,
    collection_name: str | None = None,
    batch_size: int = 100,
) -> int:
    """批量写入 chunks 到 Qdrant。

    Args:
        chunks: [{"id": ..., "text": ..., "embedding": [...], "metadata": {...}}]
        client: Qdrant 客户端
        collection_name: collection 名
        batch_size: 批量大小

    Returns:
        写入总数
    """
    client = client or get_qdrant_client()
    collection_name = collection_name or settings.qdrant_collection

    points = []
    for chunk in chunks:
        points.append(
            models.PointStruct(
                id=chunk["id"],
                vector=chunk["embedding"],
                payload={
                    "text": chunk["text"],
                    **chunk.get("metadata", {}),
                },
            )
        )

    total = 0
    for i in range(0, len(points), batch_size):
        batch = points[i : i + batch_size]
        client.upsert(collection_name=collection_name, points=batch)
        total += len(batch)
        logger.debug(f"  写入进度: {total}/{len(points)}")

    logger.info(f"✓ 写入 {total} 个 Chunk 到 Qdrant")
    return total


def search(
    query_vector: list[float],
    client: QdrantClient | None = None,
    collection_name: str | None = None,
    top_k: int = 10,
    filter_conditions: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """向量检索。

    Args:
        query_vector: 查询向量
        client: Qdrant 客户端
        collection_name: collection 名
        top_k: 返回数量
        filter_conditions: 过滤条件

    Returns:
        检索结果 [{"text": ..., "metadata": ..., "score": ...}]
    """
    client = client or get_qdrant_client()
    collection_name = collection_name or settings.qdrant_collection

    search_filter = None
    if filter_conditions:
        must = []
        for key, value in filter_conditions.items():
            if isinstance(value, list):
                must.append(
                    models.FieldCondition(
                        key=key,
                        match=models.MatchAny(any=value),
                    )
                )
            else:
                must.append(
                    models.FieldCondition(
                        key=key,
                        match=models.MatchValue(value=value),
                    )
                )
        search_filter = models.Filter(must=must)

    results = client.search(
        collection_name=collection_name,
        query_vector=query_vector,
        limit=top_k,
        query_filter=search_filter,
        with_payload=True,
    )

    return [
        {
            "text": hit.payload.get("text", ""),
            "metadata": {k: v for k, v in hit.payload.items() if k != "text"},
            "score": hit.score,
        }
        for hit in results
    ]