"""文本切分。

哲学文本的特殊切分策略：
- 按章节切分（保持论证完整）
- 按句子切分（避免切断概念）
- 自定义分隔符（中文友好）
"""

import re
from typing import List

from langchain_core.documents import Document
from langchain_text_splitters import (
    RecursiveCharacterTextSplitter,
    SentenceTransformersTokenTextSplitter,
)
from loguru import logger

from src.core.settings import settings


def split_text(
    documents: List[Document],
    chunk_size: int | None = None,
    chunk_overlap: int | None = None,
) -> List[Document]:
    """切分文本为 Chunk。

    Args:
        documents: Document 列表
        chunk_size: Chunk 大小（字符数），默认 512
        chunk_overlap: 重叠大小，默认 50

    Returns:
        切分后的 Document 列表
    """
    chunk_size = chunk_size or settings.chunk_size
    chunk_overlap = chunk_overlap or settings.chunk_overlap

    # 中文友好的分隔符
    separators = [
        "\n\n\n",   # 章节
        "\n\n",     # 段落
        "\n",       # 换行
        "。",       # 中文句号
        "！",       # 中文感叹号
        "？",       # 中文问号
        "；",       # 中文分号
        ". ",       # 英文句号
        "! ",       # 英文感叹号
        "? ",       # 英文问号
        "; ",       # 英文分号
        " ",        # 空格
        "",         # 字符
    ]

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=separators,
        length_function=len,
        is_separator_regex=False,
    )

    chunks = splitter.split_documents(documents)
    logger.info(f"✓ 切分为 {len(chunks)} 个 Chunk (size={chunk_size}, overlap={chunk_overlap})")
    return chunks


def split_by_chapter(text: str, book_id: str) -> List[Document]:
    """按章节切分（保留章节边界）。

    Args:
        text: 全文
        book_id: 书籍标识

    Returns:
        每个章节一个 Document
    """
    # 章节匹配模式（兼容中文 / 英文 / 德文）
    chapter_patterns = [
        r"^第[一二三四五六七八九十百千]+章[\s\S]*?(?=^第[一二三四五六七八九十百千]+章|\Z)",
        r"^Chapter\s+\d+[\s\S]*?(?=^Chapter\s+\d+|\Z)",
        r"^Kapitel\s+\d+[\s\S]*?(?=^Kapitel\s+\d+|\Z)",
        r"^§\s*\d+[\s\S]*?(?=^§\s*\d+|\Z)",  # 海德格尔式 §7
    ]

    chapters = []
    for pattern in chapter_patterns:
        matches = re.findall(pattern, text, re.MULTILINE)
        if matches and len(matches) >= 3:  # 至少识别出 3 章
            for i, chapter_text in enumerate(matches):
                chapters.append(
                    Document(
                        page_content=chapter_text.strip(),
                        metadata={
                            "book_id": book_id,
                            "chapter_index": i,
                            "chapter_type": pattern[:20],
                        },
                    )
                )
            break

    if not chapters:
        # 没识别到章节，按段落切
        logger.warning(f"未识别到章节结构: {book_id}，按段落切分")
        return split_text([Document(page_content=text, metadata={"book_id": book_id})])

    logger.info(f"✓ 识别到 {len(chapters)} 个章节")
    return chapters


def split_for_embedding(
    documents: List[Document],
    model_name: str | None = None,
) -> List[Document]:
    """基于 Embedding 模型 token 数切分（更精确）。

    Args:
        documents: Document 列表
        model_name: Embedding 模型名（用于精确切分）

    Returns:
        切分后的 Document
    """
    model_name = model_name or settings.embedding_model
    try:
        splitter = SentenceTransformersTokenTextSplitter(
            model_name=model_name,
            chunk_overlap=settings.chunk_overlap,
            tokens_per_chunk=settings.chunk_size,
        )
        return splitter.split_documents(documents)
    except Exception as e:
        logger.warning(f"Embedding 切分失败，回退到普通切分: {e}")
        return split_text(documents)