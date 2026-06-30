"""数据处理模块。

包含：
- loader: PDF/文本加载
- splitter: 文本切分
- cleaner: 文本清洗
"""

from src.data.loader import load_book, load_directory
from src.data.splitter import split_text, split_by_chapter
from src.data.cleaner import clean_text

__all__ = ["load_book", "load_directory", "split_text", "split_by_chapter", "clean_text"]