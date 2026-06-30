"""一键初始化数据库。

创建 Qdrant collection + Neo4j 约束 + 索引。
"""

import sys

from loguru import logger

from src.core.settings import settings
from src.graph.builder import build_graph_from_yaml
from src.graph.client import init_constraints
from src.rag.qdrant_client import ensure_collection, get_qdrant_client


def init_all(
    recreate_collections: bool = False,
    rebuild_graph: bool = False,
):
    """初始化所有数据库。

    Args:
        recreate_collections: 是否重建 Qdrant collection
        rebuild_graph: 是否重建 Neo4j 图谱
    """
    logger.info("=" * 60)
    logger.info("🚀 初始化数据库")
    logger.info("=" * 60)

    # 1. Qdrant
    logger.info("\n[1/3] Qdrant 向量库...")
    try:
        client = get_qdrant_client()
        ensure_collection(client=client, recreate=recreate_collections)
        logger.info("  ✓ Qdrant 初始化完成")
    except Exception as e:
        logger.error(f"  ✗ Qdrant 失败: {e}")
        logger.info("  请确认 Qdrant 已启动：docker-compose up -d qdrant")
        return False

    # 2. Neo4j 约束
    logger.info("\n[2/3] Neo4j 知识图谱...")
    try:
        init_constraints()
        logger.info("  ✓ Neo4j 约束初始化完成")
    except Exception as e:
        logger.error(f"  ✗ Neo4j 失败: {e}")
        logger.info("  请确认 Neo4j 已启动：docker-compose up -d neo4j")
        return False

    # 3. 从 YAML 构建图谱
    if rebuild_graph:
        logger.info("\n[3/3] 从 YAML 构建知识图谱...")
        try:
            build_graph_from_yaml(
                yaml_dir=str(settings.yaml_dir),
                clear_existing=True,
            )
            logger.info("  ✓ 知识图谱构建完成")
        except Exception as e:
            logger.error(f"  ✗ 图谱构建失败: {e}")
            return False
    else:
        logger.info("\n[3/3] 跳过图谱重建（使用 --rebuild-graph 启用）")

    logger.info("\n" + "=" * 60)
    logger.info("✅ 所有数据库初始化完成！")
    logger.info("=" * 60)
    logger.info(f"\n📊 Qdrant: http://localhost:6333/dashboard")
    logger.info(f"📊 Neo4j Browser: http://localhost:7474")
    logger.info(f"   用户名: {settings.neo4j_user}")
    logger.info(f"   密码: {settings.neo4j_password}")

    return True


def main():
    """CLI 入口"""
    import argparse

    parser = argparse.ArgumentParser(description="初始化数据库")
    parser.add_argument(
        "--recreate-collections",
        action="store_true",
        help="重建 Qdrant collections",
    )
    parser.add_argument(
        "--rebuild-graph",
        action="store_true",
        help="从 YAML 重建知识图谱",
    )
    args = parser.parse_args()

    success = init_all(
        recreate_collections=args.recreate_collections,
        rebuild_graph=args.rebuild_graph,
    )
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()