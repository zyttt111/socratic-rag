"""测试文本处理。"""

from langchain_core.documents import Document

from src.data.cleaner import clean_text
from src.data.splitter import split_text


def test_clean_text():
    """测试文本清洗"""
    raw = """
    *** START OF THE PROJECT GUTENBERG EBOOK ***
    
    这是一段正文内容。
    
    
    第二段。
    
    *** END OF THE PROJECT GUTENBERG EBOOK ***
    """
    cleaned = clean_text(raw)
    assert "START OF THE PROJECT GUTENBERG" not in cleaned
    assert "END OF THE PROJECT GUTENBERG" not in cleaned
    assert "这是一段正文内容" in cleaned


def test_split_text():
    """测试文本切分"""
    docs = [
        Document(
            page_content="这是第一段。这是第二段。这是第三段。" * 50,
            metadata={"book": "test"},
        )
    ]
    chunks = split_text(docs, chunk_size=100, chunk_overlap=20)
    assert len(chunks) > 1
    for chunk in chunks:
        assert len(chunk.page_content) <= 120  # 允许一些 overlap