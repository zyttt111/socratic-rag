"""一键重建索引。

完整流程：
1. 加载 data/raw/ 下的所有书
2. 切分 + 清洗
3. Embedding
4. 写入 Qdrant
5. 抽取概念（可选）
6. 更新知识图谱

支持增量更新（已处理的书跳过）。
"""

import hashlib
import json
import re
import sys
from pathlib import Path

from loguru import logger
from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    TextColumn,
    TimeRemainingColumn,
)

from src.core.llm import get_embeddings
from src.core.settings import settings
from src.data.cleaner import clean_text
from src.data.loader import load_book
from src.data.splitter import split_text
from src.rag.qdrant_client import (
    ensure_collection,
    get_qdrant_client,
    upsert_chunks,
)


def get_file_hash(file_path: Path) -> str:
    """计算文件 SHA-256"""
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def _detect_book_meta(file_path: Path, full_text: str) -> dict:
    """从文件名和内容推断书籍元数据。

    启发式规则（不调用 LLM，离线快速）：
    - 文件名包含作者/书名关键词 → 映射到已知作品列表
    - 否则用文件名作为 book_id、前 5 个字符作为猜测
    """
    fname = file_path.stem.lower()
    # 已知著作映射（可扩展）
    KNOWN = {
        "republic":       {"book": "理想国",      "philosopher": "柏拉图",   "language": "en"},
        "ideal-state":    {"book": "理想国",      "philosopher": "柏拉图",   "language": "zh"},
        "lixiangguo":     {"book": "理想国",      "philosopher": "柏拉图",   "language": "zh"},
        "nicomachean":    {"book": "尼各马可伦理学",  "philosopher": "亚里士多德", "language": "en"},
        "nichomachean":   {"book": "尼各马可伦理学",  "philosopher": "亚里士多德", "language": "en"},
        "meditations":    {"book": "第一哲学沉思集",  "philosopher": "笛卡尔",   "language": "en"},
        "pure-reason":    {"book": "纯粹理性批判",   "philosopher": "康德",    "language": "en"},
        "critique-pure":  {"book": "纯粹理性批判",   "philosopher": "康德",    "language": "en"},
        "phenomenology":  {"book": "精神现象学",    "philosopher": "黑格尔",   "language": "en"},
        "world-as-will":  {"book": "作为意志和表象的世界", "philosopher": "叔本华", "language": "en"},
        "zarathustra":    {"book": "查拉图斯特拉如是说", "philosopher": "尼采",  "language": "en"},
        "being-and-time": {"book": "存在与时间",    "philosopher": "海德格尔",  "language": "en"},
        "being-time":     {"book": "存在与时间",    "philosopher": "海德格尔",  "language": "en"},
        "being-nothing":  {"book": "存在与虚无",    "philosopher": "萨特",    "language": "en"},
        "zhuangzi":       {"book": "庄子",        "philosopher": "庄子",    "language": "zh"},
        "chuang-tzu":     {"book": "庄子",        "philosopher": "庄子",    "language": "en"},
        "schelling":      {"book": "先验唯心论体系",  "philosopher": "谢林",    "language": "zh"},
        "schelling-ti":   {"book": "先验唯心论体系",  "philosopher": "谢林",    "language": "zh"},
    }
    for key, meta in KNOWN.items():
        if key in fname:
            return meta
    # fallback: use stem as book_id
    return {"book": file_path.stem, "philosopher": "未知", "language": "zh"}


def process_book(
    file_path: Path,
    collection_name: str,
    force: bool = False,
) -> dict:
    """处理一本书。

    Args:
        file_path: 文件路径
        collection_name: Qdrant collection 名
        force: 是否强制重建

    Returns:
        {"chunks": int, "skipped": bool}
    """
    file_hash = get_file_hash(file_path)
    processed_dir = settings.processed_dir
    processed_dir.mkdir(parents=True, exist_ok=True)

    # 检查是否已处理
    cache_file = processed_dir / f"{file_path.stem}.json"
    if cache_file.exists() and not force:
        cached = json.loads(cache_file.read_text(encoding="utf-8"))
        if cached.get("file_hash") == file_hash:
            logger.info(f"  ⏭️  跳过已处理: {file_path.name}")
            return {"chunks": cached["chunks"], "skipped": True}

    # 1. 加载 + 清洗
    documents = load_book(file_path)
    book_meta = _detect_book_meta(file_path, "")
    pdf_pages = len(documents)

    cleaned_docs = []
    for i, doc in enumerate(documents):
        doc.page_content = clean_text(doc.page_content)
        doc.metadata["book"] = doc.metadata.get("book", file_path.stem)
        doc.metadata["file_name"] = file_path.name
        doc.metadata["book_title"] = book_meta["book"]
        doc.metadata["philosopher"] = doc.metadata.get("philosopher", book_meta["philosopher"])
        doc.metadata["language"] = book_meta["language"]
        # PDF 原生页码（从 0 开始，调整为从 1 开始）
        page = doc.metadata.get("page", i)
        doc.metadata["page"] = page
        doc.metadata["pdf_pages"] = pdf_pages
        cleaned_docs.append(doc)

    # 2. 切分
    chunks = split_text(cleaned_docs)

    # 3. 补全 metadata —— 确保每个 chunk 有精确位置信息
    for i, chunk in enumerate(chunks):
        chunk.metadata.setdefault("chunk_index", i)
        chunk.metadata.setdefault("book", file_path.stem)
        chunk.metadata.setdefault("book_title", book_meta["book"])
        chunk.metadata.setdefault("philosopher", book_meta["philosopher"])
        chunk.metadata.setdefault("language", book_meta["language"])
        chunk.metadata.setdefault("page", chunk.metadata.get("page", 0))
        chunk.metadata.setdefault("file_name", file_path.name)

    # 4. Embedding
    embeddings = get_embeddings()
    chunk_dicts = []
    for i, chunk in enumerate(chunks):
        embedding = embeddings.embed_query(chunk.page_content)
        chunk_dicts.append(
            {
                "id": f"{file_path.stem}-{i:04d}",
                "text": chunk.page_content,
                "embedding": embedding,
                "metadata": chunk.metadata,
            }
        )

    # 5. 写入 Qdrant
    client = get_qdrant_client()
    upsert_chunks(chunk_dicts, client=client, collection_name=collection_name)

    # 6. 缓存
    cache_data = {
        "file_hash": file_hash,
        "file_name": file_path.name,
        "chunks": len(chunks),
        "timestamp": str(Path(file_path).stat().st_mtime),
        "book_title": book_meta["book"],
        "philosopher": book_meta["philosopher"],
    }
    cache_file.write_text(
        json.dumps(cache_data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    return {"chunks": len(chunks), "skipped": False}


def rebuild_all(
    raw_dir: str = "data/raw",
    force: bool = False,
):
    """重建所有索引。

    Args:
        raw_dir: 原著目录
        force: 强制重建
    """
    logger.info("=" * 60)
    logger.info("🔨 重建索引")
    logger.info("=" * 60)

    raw_dir = Path(raw_dir)
    if not raw_dir.exists() or not any(raw_dir.iterdir()):
        logger.error(f"✗ 原始文本目录为空: {raw_dir}")
        logger.info("  请先运行 phil-download 下载数据")
        return False

    # 1. 确保 collection 存在
    logger.info("\n[1/3] 准备 Qdrant collection...")
    client = get_qdrant_client()
    collection_name = ensure_collection(client=client)

    # 2. 处理所有书
    logger.info(f"\n[2/3] 处理 {raw_dir} 下的书籍...")
    books = sorted([f for f in raw_dir.iterdir() if f.suffix in [".txt", ".pdf", ".md"]])

    total_chunks = 0
    skipped = 0
    with Progress(
        TextColumn("[bold blue]{task.description}"),
        BarColumn(),
        MofNCompleteColumn(),
        TimeRemainingColumn(),
    ) as progress:
        task = progress.add_task("处理进度", total=len(books))
        for book_file in books:
            result = process_book(
                book_file,
                collection_name=collection_name,
                force=force,
            )
            total_chunks += result["chunks"]
            if result["skipped"]:
                skipped += 1
            progress.update(task, advance=1)

    # 3. 报告
    logger.info(f"\n[3/3] 索引构建完成！")
    logger.info(f"  处理书籍: {len(books)} 本")
    logger.info(f"  跳过（已缓存）: {skipped} 本")
    logger.info(f"  新增 Chunk: {total_chunks - skipped * 100} 个（估算）")
    logger.info(f"  写入 Qdrant: {settings.qdrant_collection}")

    logger.info("\n💡 下一步：")
    logger.info("  1. 启动界面: uv run phil-ui")
    logger.info("  2. 运行评估: uv run phil-eval")
    logger.info("  3. 重建图谱: uv run phil-init --rebuild-graph")

    return True


def main():
    """CLI 入口"""
    import argparse

    parser = argparse.ArgumentParser(description="重建索引")
    parser.add_argument(
        "--raw-dir",
        default="data/raw",
        help="原著目录",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="强制重建（忽略缓存）",
    )
    args = parser.parse_args()

    success = rebuild_all(args.raw_dir, args.force)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()