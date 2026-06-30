"""测试 RAG 检索。

注意：这些测试需要 Qdrant 和 DeepSeek API。
"""

import pytest

from src.core.settings import settings


@pytest.mark.skipif(not settings.deepseek_api_key, reason="需要 DEEPSEEK_API_KEY")
def test_rag_chain_query():
    """测试 RAG 查询（需要先有数据）"""
    from src.rag.rag_chain import RAGChain

    rag = RAGChain()
    # 注意：需要先运行 phil-rebuild 写入数据
    result = rag.query("什么是现象学？", top_k=3)

    assert "answer" in result
    assert "contexts" in result
    assert "sources" in result


def test_prompts_loadable():
    """测试 Prompt 加载"""
    from src.prompts.loader import list_prompts, load_prompt

    prompts = list_prompts()
    assert "academic_qa" in prompts
    assert "socrates" in prompts

    p = load_prompt("academic_qa")
    assert "system" in p
    assert "user" in p