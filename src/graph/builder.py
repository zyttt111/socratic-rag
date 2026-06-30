"""知识图谱构建器。

从 YAML 构建 Neo4j 图谱。
"""

from pathlib import Path

import yaml
from loguru import logger

from src.graph.client import get_neo4j_driver


def build_graph_from_yaml(
    yaml_dir: str = "data/yaml",
    clear_existing: bool = False,
):
    """从 YAML 构建图谱。

    Args:
        yaml_dir: YAML 根目录
        clear_existing: 是否清空现有数据
    """
    yaml_dir = Path(yaml_dir)
    driver = get_neo4j_driver()

    with driver.session() as session:
        if clear_existing:
            logger.warning("清空现有图谱...")
            session.run("MATCH (n) DETACH DELETE n")

        # 1. 加载哲学家
        philosophers_dir = yaml_dir / "philosophers"
        if philosophers_dir.exists():
            for yaml_file in philosophers_dir.glob("*.yaml"):
                _load_philosopher(session, yaml_file)

        # 2. 加载著作
        books_dir = yaml_dir / "books"
        if books_dir.exists():
            for yaml_file in books_dir.glob("*.yaml"):
                _load_book(session, yaml_file)

        # 3. 加载概念
        concepts_dir = yaml_dir / "concepts"
        if concepts_dir.exists():
            for yaml_file in concepts_dir.glob("*.yaml"):
                _load_concept(session, yaml_file)

    logger.info("✓ 知识图谱构建完成")


def _load_philosopher(session, yaml_file: Path):
    """加载哲学家 YAML"""
    with open(yaml_file, encoding="utf-8") as f:
        data = yaml.safe_load(f)

    if not data:
        return

    # 单个哲学家
    for key, philo in data.items():
        if not isinstance(philo, dict):
            continue

        session.run(
            """
            MERGE (p:Philosopher {name: $name})
            SET p.name_en = $name_en,
                p.era = $era,
                p.school = $school,
                p.style = $style,
                p.core_position = $core_position
            """,
            {
                "name": philo.get("zh", {}).get("name", key),
                "name_en": philo.get("en", {}).get("name", key),
                "era": philo.get("zh", {}).get("era", ""),
                "school": philo.get("zh", {}).get("school", ""),
                "style": philo.get("zh", {}).get("style", ""),
                "core_position": philo.get("zh", {}).get("core_position", ""),
            },
        )
        logger.debug(f"  ✓ 哲学家: {philo.get('zh', {}).get('name', key)}")


def _load_book(session, yaml_file: Path):
    """加载著作 YAML"""
    with open(yaml_file, encoding="utf-8") as f:
        data = yaml.safe_load(f)

    if not data:
        return

    for book_id, book in data.items():
        if not isinstance(book, dict):
            continue

        session.run(
            """
            MERGE (b:Book {title: $title})
            SET b.title_en = $title_en,
                b.year = $year,
                b.translator = $translator,
                b.publisher = $publisher,
                b.language = $language,
                b.school = $school
            WITH b
            MATCH (p:Philosopher {name: $philosopher})
            MERGE (p)-[:WROTE]->(b)
            """,
            {
                "title": book.get("title", book_id),
                "title_en": book.get("title_en", ""),
                "year": book.get("year", 0),
                "translator": book.get("translator", ""),
                "publisher": book.get("publisher", ""),
                "language": book.get("language", "zh"),
                "school": book.get("school", ""),
                "philosopher": book.get("philosopher", ""),
            },
        )
        logger.debug(f"  ✓ 著作: {book.get('title', book_id)}")


def _load_concept(session, yaml_file: Path):
    """加载概念 YAML"""
    with open(yaml_file, encoding="utf-8") as f:
        data = yaml.safe_load(f)

    if not data:
        return

    for concept_id, concept in data.items():
        if not isinstance(concept, dict):
            continue

        session.run(
            """
            MERGE (c:Concept {name: $name})
            SET c.definition = $definition,
                c.school = $school,
                c.related_philosophers = $related_philosophers
            """,
            {
                "name": concept.get("name", concept_id),
                "definition": concept.get("definition", ""),
                "school": concept.get("school", ""),
                "related_philosophers": concept.get("related_philosophers", []),
            },
        )

        # 关系：概念 → 哲学家
        for philo in concept.get("related_philosophers", []):
            session.run(
                """
                MATCH (c:Concept {name: $concept})
                MATCH (p:Philosopher {name: $philosopher})
                MERGE (p)-[:DISCUSSED]->(c)
                """,
                {"concept": concept.get("name", concept_id), "philosopher": philo},
            )

        # 关系：概念 → 概念
        for rel in concept.get("related_concepts", []):
            session.run(
                """
                MATCH (c1:Concept {name: $c1})
                MATCH (c2:Concept {name: $c2})
                MERGE (c1)-[:RELATED_TO]->(c2)
                """,
                {"c1": concept.get("name", concept_id), "c2": rel},
            )

        logger.debug(f"  ✓ 概念: {concept.get('name', concept_id)}")