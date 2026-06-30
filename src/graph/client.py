"""Neo4j 客户端。

封装 Neo4j 连接和基本操作。
"""

from functools import lru_cache

from loguru import logger
from neo4j import GraphDatabase

from src.core.settings import settings


@lru_cache
def get_neo4j_driver():
    """获取 Neo4j driver（单例）"""
    driver = GraphDatabase.driver(
        settings.neo4j_uri,
        auth=(settings.neo4j_user, settings.neo4j_password),
    )
    logger.info(f"✓ Neo4j 连接: {settings.neo4j_uri}")
    return driver


def init_constraints():
    """初始化 Neo4j 约束（唯一性 + 索引）"""
    driver = get_neo4j_driver()
    constraints = [
        "CREATE CONSTRAINT IF NOT EXISTS FOR (p:Philosopher) REQUIRE p.name IS UNIQUE",
        "CREATE CONSTRAINT IF NOT EXISTS FOR (c:Concept) REQUIRE c.name IS UNIQUE",
        "CREATE CONSTRAINT IF NOT EXISTS FOR (b:Book) REQUIRE b.title IS UNIQUE",
        "CREATE INDEX IF NOT EXISTS FOR (p:Philosopher) ON (p.era)",
        "CREATE INDEX IF NOT EXISTS FOR (c:Concept) ON (c.school)",
    ]

    with driver.session() as session:
        for cql in constraints:
            try:
                session.run(cql)
            except Exception as e:
                logger.warning(f"约束创建失败（可能已存在）: {e}")

    logger.info("✓ Neo4j 约束初始化完成")


def execute_query(cql: str, parameters: dict | None = None) -> list[dict]:
    """执行 Cypher 查询。"""
    driver = get_neo4j_driver()
    with driver.session() as session:
        result = session.run(cql, parameters or {})
        return [dict(record) for record in result]