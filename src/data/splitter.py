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


def split_by_chapter(text: str, book_id: str) -> list:
    """按章节切分（保留章节边界）。

    支持中文/英文/德文章节标题，以及无编号的导论/绪论/结束语。
    无法识别章节结构时，回退到按空行段落切分。

    Args:
        text: 全文
        book_id: 书籍标识

    Returns:
        每个章节一个 Document
    """
    # ---- 合并所有章节标题模式为一条正则 ----
    # 匹配以下形式的行（独立成行或行首）：
    #   第X章 / 第一章 / 导论 / 绪论 / 引言 / 前言 / 序 / 结束语 / 结论 / 附录 / 后记
    #   Chapter X / CHAPTER X
    #   Kapitel X
    #   § X / §X
    # 每个匹配块从当前标题行开始，到下一个标题行（或文末）结束
    _CN_NUM = r"第[一二三四五六七八九十百千\d]+章"
    _CN_WORD = r"(?:导[论言]|绪[论言]|引[言论]|前[言]|序[言]?|结束语|结[论语]|附[录记]|后[记]|跋|补[编遗]|凡例)"
    _CN = rf"(?:{_CN_NUM}|{_CN_WORD})"
    _EN = r"Chapter\s+\d+"
    _DE = r"Kapitel\s+\d+"
    _SECTION = r"§\s*\d+"

    heading = rf"(?:{_CN}|{_EN}|{_DE}|{_SECTION})"
    pattern = re.compile(rf"^({heading})\b.*$", re.MULTILINE)

    # 找到所有标题行位置
    matches = list(pattern.finditer(text))
    if len(matches) < 2:
        logger.warning(f"未识别到章节结构: {book_id}，按空行段落切分")
        paragraphs = [p.strip() for p in re.split(r"\n{2,}", text) if p.strip()]
        if not paragraphs:
            return [Document(page_content=text, metadata={"book_id": book_id})]
        return [
            Document(
                page_content=p,
                metadata={"book_id": book_id, "chunk_index": i},
            )
            for i, p in enumerate(paragraphs)
        ]

    # 按标题位置切分
    chapters = []
    for i, m in enumerate(matches):
        start = m.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        chapter_text = text[start:end].strip()
        if not chapter_text:
            continue
        chapters.append(
            Document(
                page_content=chapter_text,
                metadata={
                    "book_id": book_id,
                    "chapter_index": i,
                    "chapter_title": m.group(1).strip() if m.group(1) else m.group(0).strip(),
                },
            )
        )

    logger.info(f"✓ 识别到 {len(chapters)} 个章节 (pattern={pattern.pattern[:60]}...)")
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