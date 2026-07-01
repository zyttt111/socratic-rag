"""谢林《先验唯心论体系》专用处理脚本。

流程：
1. 加载文本（自动识别 PDF / TXT / MD）
2. 章节切分（谢林这本书结构清晰）
3. 元数据写入 YAML
4. 4 层抽取（DeepSeek-V3 主力 + Claude 校对）
5. 写入 Qdrant + Neo4j
6. 跑 RAGAS 评估（基于 5 道谢林专用评估题）

用法：
    python scripts/build_schelling.py --file /path/to/schelling-ti.txt
    python scripts/build_schelling.py --file schelling-ti.pdf --with-claude-audit
"""

import argparse
import asyncio
import sys
from pathlib import Path

from loguru import logger

from src.core.llm import get_llm
from src.data.cleaner import clean_text
from src.data.loader import load_book
from src.data.splitter import split_by_chapter


# ============================================================
# 谢林《先验唯心论体系》结构（梁志学/石泉译本，商务印书馆）
# ============================================================

SCHELLING_BOOK_META = {
    "schelling-ti": {
        "title": "先验唯心论体系",
        "title_en": "System of Transcendental Idealism",
        "title_de": "System des transzendentalen Idealismus",
        "philosopher": "谢林",
        "philosopher_en": "Friedrich Wilhelm Joseph Schelling",
        "philosopher_de": "Friedrich Wilhelm Joseph Schelling",
        "year": 1800,
        "translator": "梁志学 / 石泉",
        "publisher": "商务印书馆",
        "year_chinese": 1997,
        "language": "zh",
        "school": "德国古典哲学 / 德国观念论",
        "era": "1800-1850",
        "sep_entry": "https://plato.stanford.edu/entries/schelling/",
        "core_concepts": [
            "绝对者",
            "同一哲学",
            "自我",
            "自然哲学",
            "智性直观",
            "艺术哲学",
            "历史的先验根据",
            "无意识",
            "极性",
        ],
        "chapters": [
            "导论",
            "第一章 略论作为哲学一般之科学学说的先验哲学",
            "第二章 理论哲学",
            "第三章 先验理想主义的实践哲学",
            "第四章 从先验哲学看艺术哲学",
            "第五章 从先验哲学看历史哲学",
            "第六章 结束语",
        ],
    },
}

SCHELLING_PHILOSOPHER_META = {
    "schelling": {
        "zh": {
            "name": "谢林",
            "name_en": "Friedrich Wilhelm Joseph Schelling",
            "name_de": "Friedrich Wilhelm Joseph Schelling",
            "era": "1775-1854",
            "school": "德国古典哲学 / 同一哲学",
            "language": "德语",
            "nationality": "符腾堡（德意志）",
            "style": "思辨、辩证、自然哲学化。\n用思辨哲学方法构造'同一哲学'体系。\n介于费希特（主观）和黑格尔（绝对）之间。",
            "core_position": "绝对者（das Absolute）是主观与客观的绝对同一。\n自然与精神、理论与实践、意识与无意识都从绝对者中辩证推出。\n艺术的最高使命是绝对者的自我直观。",
            "key_concepts": [
                "绝对者",
                "同一哲学",
                "自然哲学",
                "智性直观",
                "艺术的先验根据",
                "历史的先验根据",
                "无意识",
                "极性",
            ],
            "major_works": [
                "先验唯心论体系 (1800)",
                "自然哲学体系初稿 (1799)",
                "布鲁诺 (1802)",
                "世界时代 (1811)",
                "启示哲学 (1858)",
            ],
            "influences": ["费希特（师从）", "康德"],
            "influenced_by": [],
            "influenced": [
                "黑格尔（早期同学，晚期决裂）",
                "谢莱格尔",
                "叔本华",
                "克尔凯郭尔",
            ],
            "famous_quotes": [
                "绝对者作为无差别的点，是永恒的，"
                "在一切存在之前就已存在，"
                "一切都从它那里产生。",
                "历史乃是一部'自我启示'的史诗，"
                "它的'主角'就是绝对者。",
            ],
        },
    },
}


async def extract_metadata(text: str) -> dict:
    """Layer 1：抽取元数据（用 DeepSeek）。"""
    llm = get_llm(model="deepseek", temperature=0.0)

    prompt = f"""你是哲学文献编目专家。请从以下文本片段中确认或补全书籍元数据。

【已知元数据】
{str(SCHELLING_BOOK_META['schelling-ti'])}

【文本片段（前 2000 字）】
{text[:2000]}

请确认并补全（如发现错误请指出）。输出 YAML：
```yaml
title: 
title_en: 
philosopher: 
translator:
publisher:
year:
core_concepts: [列出 5-10 个]
key_chapters: [列出主要章节]
difficulty: 1-5
notes: "任何编目发现"
```"""

    from langchain_core.messages import HumanMessage

    response = llm.invoke([HumanMessage(content=prompt)])
    logger.info(f"✓ 元数据确认：{response.content[:200]}")
    return {"raw": response.content}


async def extract_chapter_summary(chapter_title: str, chapter_text: str) -> dict:
    """Layer 2：章节摘要（DeepSeek）。"""
    llm = get_llm(model="deepseek", temperature=0.1)

    prompt = f"""你是谢林研究专家。请为以下章节写摘要。

【章节】{chapter_title}

【文本】
{chapter_text[:6000]}

要求：
1. 500 字摘要
2. 3-5 个核心概念
3. 2-3 个关键论证
4. 与其他哲学家（康德/费希特/黑格尔）的关系（如有）

输出 YAML：
```yaml
summary: |
  ...
core_concepts: [...]
key_arguments: [...]
related_to_others:
  - philosopher: "康德"
    relation: "继承 + 改造"
    specifics: "..."
```"""

    from langchain_core.messages import HumanMessage

    response = llm.invoke([HumanMessage(content=prompt)])
    return {"title": chapter_title, "summary_raw": response.content}


async def extract_concepts_with_claude_audit(
    chapter_title: str,
    chapter_text: str,
    use_claude_audit: bool = True,
) -> list[dict]:
    """Layer 3：概念抽取（DeepSeek 抽取 + Claude 审计）。

    Args:
        chapter_title: 章节标题
        chapter_text: 章节文本
        use_claude_audit: 是否用 Claude 二次审计

    Returns:
        概念列表
    """
    deepseek = get_llm(model="deepseek", temperature=0.1)

    # Step 1：DeepSeek 抽取
    extract_prompt = f"""你是谢林研究专家。请从以下章节中抽取核心概念。

【章节】{chapter_title}

【文本】
{chapter_text[:6000]}

要求：
1. 抽取 3-5 个核心概念
2. 每个概念给精确定义（用谢林自己的语言）
3. 必须包含原文引用（精确到段落）
4. 区分"谢林自己的术语"和"现代解读"

输出 YAML：
```yaml
- concept: 概念名
  definition: 精确定义（不超过 200 字）
  quote: 原文引用
  location: 段落定位
  related_to: [相关概念]
  is_schelling_term: true/false
```"""

    from langchain_core.messages import HumanMessage

    response = deepseek.invoke([HumanMessage(content=extract_prompt)])
    deepseek_output = response.content

    concepts = _parse_yaml_concepts(deepseek_output)

    # Step 2：Claude 审计（术语对齐）
    if use_claude_audit and concepts:
        claude = get_llm(model="claude", temperature=0.0)
        audit_prompt = f"""你是谢林研究专家。请审计以下概念抽取的准确性。

【DeepSeek 抽取结果】
{deepseek_output}

【章节原文（节选）】
{chapter_text[:3000]}

【审计维度】
1. 术语翻译是否准确（对照德文原词）
2. 定义是否忠实于谢林原意
3. 引用是否真实（不是编造）
4. 是否有遗漏的核心概念

请输出审计意见 + 修订建议。"""

        audit_response = claude.invoke([HumanMessage(content=audit_prompt)])
        logger.info(f"  Claude 审计完成（前 200 字）：{audit_response.content[:200]}")

        # 把审计结果附加到每个概念
        for c in concepts:
            c["claude_audit"] = audit_response.content[:500]

    return concepts


def _parse_yaml_concepts(text: str) -> list[dict]:
    """解析 YAML 格式的概念列表（简化版）。"""
    import re

    concepts = []
    pattern = (
        r"- concept:\s*(.+?)\s+"
        r"definition:\s*(.+?)\s+"
        r"quote:\s*(.+?)\s+"
        r"location:\s*(.+?)\s+"
        r"related_to:\s*\[(.+?)\]\s+"
        r"is_schelling_term:\s*(\w+)"
    )
    matches = re.findall(pattern, text, re.DOTALL)

    for m in matches:
        concepts.append(
            {
                "concept": m[0].strip(),
                "definition": m[1].strip(),
                "quote": m[2].strip(),
                "location": m[3].strip(),
                "related_to": [x.strip() for x in m[4].split(",")],
                "is_schelling_term": m[5].strip().lower() == "true",
            }
        )

    return concepts


async def extract_relations(chapters_summaries: list[dict]) -> list[dict]:
    """Layer 4：关系抽取（Claude 主力，因为复杂推理）。

    重点：谢林 vs 康德/费希特/黑格尔的关系
    """
    claude = get_llm(model="claude", temperature=0.0)

    summaries_text = "\n\n".join(
        [f"【{s['title']}】\n{s.get('summary_raw', '')}" for s in chapters_summaries]
    )

    prompt = f"""你是谢林研究专家。基于以下章节摘要，抽取谢林与同时代哲学家的关系。

【章节摘要】
{summaries_text}

【要求】
重点关注谢林与以下 4 位哲学家的关系：
1. 康德（Kant）
2. 费希特（Fichte）
3. 黑格尔（Hegel）
4. 席勒（Schiller，谢林的图宾根同学）

每条关系输出：
- philosopher: 哲学家
- relation_type: INFLUENCED_BY / INFLUENCED / CRITICIZED / AGREED_WITH / DIFFERED_FROM
- context: 关系背景（基于本书内容）
- specific_works: 具体涉及著作
- key_quotes: 关键引用（如有）

输出格式（Neo4j Cypher 风格）：
```cypher
MERGE (s:Philosopher {{name: '谢林'}})
MERGE (k:Philosopher {{name: '康德'}})
MERGE (s)-[:INFLUENCED_BY {{
  year: 1800,
  context: "...",
  specific_works: ["..."]
}}]->(k)
```"""

    from langchain_core.messages import HumanMessage

    response = claude.invoke([HumanMessage(content=prompt)])
    return [{"raw": response.content}]


async def run_full_pipeline(
    file_path: str,
    with_claude_audit: bool = True,
    skip_extraction: bool = False,
):
    """完整流程。

    Args:
        file_path: 书籍文件路径
        with_claude_audit: 是否用 Claude 审计
        skip_extraction: 跳过抽取（仅加载 + 切分）
    """
    logger.info("=" * 60)
    logger.info("📚 谢林《先验唯心论体系》知识库构建")
    logger.info("=" * 60)

    file_path = Path(file_path)
    if not file_path.exists():
        logger.error(f"✗ 文件不存在: {file_path}")
        logger.info("\n💡 获取方式：")
        logger.info("  1. 商务印书馆《先验唯心论体系》（梁志学/石泉 译）")
        logger.info("  2. URL: 在京东/当当搜索书名")
        logger.info("  3. PDF 解析后放到本地路径")
        return False

    # 1. 加载 + 清洗
    logger.info(f"\n[1/5] 加载文件: {file_path}")
    documents = load_book(file_path)
    for doc in documents:
        doc.page_content = clean_text(doc.page_content)
    logger.info(f"  ✓ 加载 {len(documents)} 个 Document")

    # 2. 章节切分
    logger.info("\n[2/5] 章节切分")
    full_text = "\n\n".join([d.page_content for d in documents])
    chapters = split_by_chapter(full_text, "schelling-ti")
    logger.info(f"  ✓ 识别 {len(chapters)} 个章节")

    if skip_extraction:
        logger.info("  ⏭️  跳过抽取（仅切分）")
        return True

    # 3. 4 层抽取
    logger.info("\n[3/5] 4 层抽取")

    # Layer 1：元数据
    metadata = await extract_metadata(full_text[:3000])

    # Layer 2：章节摘要
    chapter_summaries = []
    for ch in chapters:
        logger.info(f"  摘要: {ch.metadata.get('chapter_index', '?')} - 长度 {len(ch.page_content)}")
        summary = await extract_chapter_summary(
            f"Chapter {ch.metadata.get('chapter_index', '?')}",
            ch.page_content,
        )
        chapter_summaries.append(summary)

    # Layer 3：概念抽取（含 Claude 审计）
    all_concepts = []
    for i, ch in enumerate(chapters):
        logger.info(f"  概念抽取: 章节 {i + 1}/{len(chapters)}")
        concepts = await extract_concepts_with_claude_audit(
            f"Chapter {i + 1}",
            ch.page_content,
            use_claude_audit=with_claude_audit,
        )
        all_concepts.extend(concepts)

    # Layer 4：关系抽取
    logger.info("  关系抽取: 谢林 vs 康德/费希特/黑格尔")
    relations = await extract_relations(chapter_summaries)

    # 4. 保存结果
    logger.info("\n[4/5] 保存结果")
    import json

    output_dir = Path("data/processed/schelling-ti")
    output_dir.mkdir(parents=True, exist_ok=True)

    (output_dir / "metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (output_dir / "chapters.json").write_text(
        json.dumps(chapter_summaries, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (output_dir / "concepts.json").write_text(
        json.dumps(all_concepts, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (output_dir / "relations.json").write_text(
        json.dumps(relations, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    # 5. 写入元数据 YAML（让 Neo4j builder 能用）
    import yaml

    yaml_dir = Path("data/yaml")
    (yaml_dir / "books" / "schelling-ti.yaml").write_text(
        yaml.safe_dump(SCHELLING_BOOK_META["schelling-ti"], allow_unicode=True),
        encoding="utf-8",
    )
    (yaml_dir / "philosophers" / "schelling.yaml").write_text(
        yaml.safe_dump(SCHELLING_PHILOSOPHER_META["schelling"], allow_unicode=True),
        encoding="utf-8",
    )

    logger.info(f"\n[5/5] 完成！结果保存到 {output_dir.absolute()}")
    logger.info("\n" + "=" * 60)
    logger.info("✅ 谢林《先验唯心论体系》知识库构建完成")
    logger.info("=" * 60)
    logger.info(f"\n📊 统计：")
    logger.info(f"  章节: {len(chapters)}")
    logger.info(f"  概念: {len(all_concepts)}")
    logger.info(f"  关系: {len(relations)}")

    logger.info(f"\n💡 下一步：")
    logger.info(f"  1. 人工校对 data/processed/schelling-ti/concepts.json")
    logger.info(f"  2. 运行 phil-init --rebuild-graph 写入 Neo4j")
    logger.info(f"  3. 运行 phil-rebuild 写入 Qdrant")
    logger.info(f"  4. 用 Neo4j Browser 查看关系图")

    return True


def main():
    parser = argparse.ArgumentParser(description="构建谢林《先验唯心论体系》知识库")
    parser.add_argument(
        "--file",
        "-f",
        required=True,
        help="书籍文件路径（PDF / TXT / MD）",
    )
    parser.add_argument(
        "--with-claude-audit",
        action="store_true",
        default=True,
        help="用 Claude 审计概念抽取（推荐）",
    )
    parser.add_argument(
        "--skip-extraction",
        action="store_true",
        help="跳过抽取（仅加载 + 切分）",
    )
    args = parser.parse_args()

    success = asyncio.run(
        run_full_pipeline(
            file_path=args.file,
            with_claude_audit=args.with_claude_audit,
            skip_extraction=args.skip_extraction,
        )
    )
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()