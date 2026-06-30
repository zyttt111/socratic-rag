"""文档加载器。

支持：
- .txt（纯文本，Project Gutenberg / 商业电子书）
- .pdf（PDF，使用 MinerU 解析）
- .md（Markdown）
- 整个目录
"""

from pathlib import Path
from typing import List

from langchain_core.documents import Document
from langchain_community.document_loaders import (
    DirectoryLoader,
    PyPDFLoader,
    TextLoader,
    UnstructuredMarkdownLoader,
)
from loguru import logger


def load_book(file_path: str | Path) -> List[Document]:
    """加载单个文件。

    Args:
        file_path: 文件路径

    Returns:
        Document 列表
    """
    file_path = Path(file_path)
    if not file_path.exists():
        raise FileNotFoundError(f"文件不存在: {file_path}")

    suffix = file_path.suffix.lower()
    logger.info(f"加载文件: {file_path} (类型: {suffix})")

    if suffix == ".pdf":
        loader = PyPDFLoader(str(file_path))
    elif suffix == ".md":
        loader = UnstructuredMarkdownLoader(str(file_path))
    elif suffix in [".txt", ".text"]:
        loader = TextLoader(str(file_path), encoding="utf-8")
    else:
        # 默认按文本处理
        loader = TextLoader(str(file_path), encoding="utf-8")

    documents = loader.load()
    logger.info(f"  ✓ 加载 {len(documents)} 个 Document")
    return documents


def load_directory(
    directory: str | Path,
    glob_pattern: str = "**/*.txt",
    recursive: bool = True,
) -> List[Document]:
    """加载整个目录。

    Args:
        directory: 目录路径
        glob_pattern: 文件匹配模式
        recursive: 是否递归

    Returns:
        Document 列表
    """
    directory = Path(directory)
    if not directory.exists():
        raise FileNotFoundError(f"目录不存在: {directory}")

    loader = DirectoryLoader(
        str(directory),
        glob=glob_pattern,
        recursive=recursive,
        loader_cls=TextLoader,
        loader_kwargs={"encoding": "utf-8"},
        show_progress=True,
    )

    documents = loader.load()
    logger.info(f"✓ 从 {directory} 加载 {len(documents)} 个文件")
    return documents


def load_pdf_with_mineru(pdf_path: str | Path) -> str:
    """使用 MinerU 解析 PDF（高质量，适合扫描版）。

    Args:
        pdf_path: PDF 文件路径

    Returns:
        Markdown 文本
    """
    # TODO: 集成 MinerU
    # from magic_pdf import MagicPDF
    # processor = MagicPDF()
    # result = processor.process(str(pdf_path))
    # return result.to_markdown()

    # 临时用 PyPDFLoader
    documents = load_book(pdf_path)
    return "\n\n".join(doc.page_content for doc in documents)