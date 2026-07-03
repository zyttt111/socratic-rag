"""全局配置（Pydantic Settings）

从 .env 文件加载，支持环境变量覆盖。
"""

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """全局配置"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ========================
    # LLM
    # ========================
    deepseek_api_key: str = Field(default="")
    deepseek_base_url: str = Field(default="https://api.deepseek.com/v1")
    deepseek_model: str = Field(default="deepseek-chat")

    anthropic_api_key: str = Field(default="")
    claude_model: str = Field(default="claude-sonnet-4-5")

    # ========================
    # Embedding
    # ========================
    embedding_model: str = Field(default="BAAI/bge-large-zh-v1.5")
    embedding_device: str = Field(default="cpu")
    embedding_dim: int = Field(default=1024)

    rerank_model: str = Field(default="BAAI/bge-reranker-large")
    use_rerank: bool = Field(default=False)

    # ========================
    # 数据库
    # ========================
    qdrant_host: str = Field(default="localhost")
    qdrant_port: int = Field(default=6333)
    qdrant_mode: str = Field(default="local")
    qdrant_path: str = Field(default="data/qdrant_local")
    qdrant_collection: str = Field(default="philosophy_chunks")

    neo4j_uri: str = Field(default="bolt://localhost:7687")
    neo4j_user: str = Field(default="neo4j")
    neo4j_password: str = Field(default="phil_password")

    redis_url: str = Field(default="redis://localhost:6379/0")

    # ========================
    # 抽取
    # ========================
    extraction_concurrency: int = Field(default=20)
    extraction_batch_size: int = Field(default=5)
    chunk_size: int = Field(default=512)
    chunk_overlap: int = Field(default=50)

    # ========================
    # 服务
    # ========================
    app_env: str = Field(default="development")
    log_level: str = Field(default="INFO")
    ui_port: int = Field(default=8501)
    api_port: int = Field(default=8000)

    eval_batch_size: int = Field(default=10)
    eval_output_dir: str = Field(default="docs/eval_reports")

    # ========================
    # 路径
    # ========================
    project_root: Path = Path(__file__).parent.parent.parent
    data_dir: Path = project_root / "data"
    raw_dir: Path = data_dir / "raw"
    processed_dir: Path = data_dir / "processed"
    yaml_dir: Path = data_dir / "yaml"
    eval_dir: Path = data_dir / "eval"


@lru_cache
def get_settings() -> Settings:
    """获取全局配置（单例）"""
    return Settings()


settings = get_settings()