"""一键运行 RAGAS 评估。

读取 data/eval/questions.yaml，跑评估，输出报告。
"""

import sys
from pathlib import Path

import yaml
from loguru import logger

from src.core.settings import settings
from src.evaluation.evaluator import Evaluator


def load_eval_questions(eval_file: str = "data/eval/questions.yaml") -> tuple[list, list]:
    """加载评估题。

    Returns:
        (questions, ground_truths)
    """
    eval_path = Path(eval_file)
    if not eval_path.exists():
        logger.error(f"评估文件不存在: {eval_path}")
        return [], []

    with open(eval_path, encoding="utf-8") as f:
        data = yaml.safe_load(f)

    questions = [item["question"] for item in data]
    ground_truths = [item["standard_answer"] for item in data]

    logger.info(f"✓ 加载 {len(questions)} 道评估题")
    return questions, ground_truths


def main():
    """CLI 入口"""
    import argparse

    parser = argparse.ArgumentParser(description="运行 RAGAS 评估")
    parser.add_argument(
        "--eval-file",
        default="data/eval/questions.yaml",
        help="评估文件",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="输出目录（默认 docs/eval_reports）",
    )
    args = parser.parse_args()

    logger.info("=" * 60)
    logger.info("📊 RAGAS 评估")
    logger.info("=" * 60)

    questions, ground_truths = load_eval_questions(args.eval_file)
    if not questions:
        sys.exit(1)

    evaluator = Evaluator()
    results = evaluator.run(
        questions=questions,
        ground_truths=ground_truths,
        output_dir=args.output,
    )

    logger.info("\n" + "=" * 60)
    logger.info("📈 评估结果")
    logger.info("=" * 60)
    logger.info(f"  Context Precision: {results['context_precision']:.3f}")
    logger.info(f"  Context Recall:    {results['context_recall']:.3f}")
    logger.info(f"  Faithfulness:      {results['faithfulness']:.3f}")
    logger.info(f"  Answer Relevancy:  {results['answer_relevancy']:.3f}")
    logger.info(f"\n  报告: {results['report_path']}")

    logger.info("\n💡 优化建议：")
    if results["context_precision"] < 0.7:
        logger.info("  - Context Precision 偏低 → 优化切分粒度 / 启用 Rerank")
    if results["context_recall"] < 0.7:
        logger.info("  - Context Recall 偏低 → 优化 BM25 / 增加 Embedding 召回")
    if results["faithfulness"] < 0.85:
        logger.info("  - Faithfulness 偏低 → 加强 Prompt 中的引用约束")
    if results["answer_relevancy"] < 0.7:
        logger.info("  - Answer Relevancy 偏低 → 优化 Prompt 让答案更聚焦")


if __name__ == "__main__":
    main()