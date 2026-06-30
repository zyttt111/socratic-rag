"""测试核心 LLM 配置。

注意：这些测试需要 DEEPSEEK_API_KEY 环境变量。
"""

import pytest

from src.core.settings import settings


def test_settings_loaded():
    """测试配置加载"""
    assert settings is not None
    assert settings.deepseek_model is not None
    assert settings.embedding_dim > 0


def test_data_dirs_exist():
    """测试数据目录存在"""
    assert settings.data_dir.exists()
    assert settings.yaml_dir.exists()


@pytest.mark.skipif(not settings.deepseek_api_key, reason="需要 DEEPSEEK_API_KEY")
def test_deepseek_connection():
    """测试 DeepSeek 连接"""
    from src.core.llm import get_llm

    llm = get_llm(model="deepseek")
    response = llm.invoke("用一句话介绍哲学。")
    assert response.content
    assert len(response.content) > 0


@pytest.mark.skipif(not settings.deepseek_api_key, reason="需要 DEEPSEEK_API_KEY")
def test_embeddings_loaded():
    """测试 Embedding 加载（首次运行会下载模型）"""
    from src.core.llm import get_embeddings

    embeddings = get_embeddings()
    vector = embeddings.embed_query("哲学是什么？")
    assert len(vector) == settings.embedding_dim