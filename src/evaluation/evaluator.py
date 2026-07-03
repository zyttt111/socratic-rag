"""RAGAS 评估。

自动评估 RAG 系统质量：
- Context Precision
- Context Recall
- Faithfulness
- Answer Relevancy
"""

from pathlib import Path

from datasets import Dataset
from loguru import logger

# ragas 0.4.x 仍从 langchain_community.chat_models 引用 vertexai，但
# langchain-community >=0.4 已移除该模块。我们只用 DeepSeek / Anthropic，
# 所以在 import ragas 前 monkey-patch 一个空壳，避免依赖 vertexai 失败。
try:
    import langchain_community.chat_models as _lcms
    if not hasattr(_lcms, "vertexai"):
        import types
        _stub = types.ModuleType("langchain_community.chat_models.vertexai")
        class _Stub:
            pass
        _stub.ChatVertexAI = _Stub
        _lcms.vertexai = _stub  # type: ignore[attr-defined]
        import sys as _sys
        _sys.modules.setdefault(
            "langchain_community.chat_models.vertexai", _stub
        )
except Exception:  # pragma: no cover
    pass

from ragas import evaluate
from ragas.metrics import answer_relevancy, context_precision, context_recall, faithfulness

from src.core.settings import settings
from src.rag.rag_chain import RAGChain


class Evaluator:
    """评估器"""

    def __init__(self, rag_chain: RAGChain | None = None):
        """初始化。

        Args:
            rag_chain: RAG 链
        """
        self.rag_chain = rag_chain or RAGChain()

    def run(
        self,
        questions: list[str],
        ground_truths: list[str],
        output_dir: str | None = None,
    ) -> dict:
        """运行评估。

        Args:
            questions: 问题列表
            ground_truths: 标准答案列表
            output_dir: 输出目录

        Returns:
            评估结果
        """
        output_dir = output_dir or settings.eval_output_dir
        Path(output_dir).mkdir(parents=True, exist_ok=True)

        results = []
        for i, (q, gt) in enumerate(zip(questions, ground_truths)):
            logger.info(f"评估 [{i + 1}/{len(questions)}]: {q[:50]}...")
            result = self.rag_chain.query(q, top_k=5)
            results.append(
                {
                    "question": q,
                    "answer": result["answer"],
                    "contexts": [c["text"] for c in result["contexts"]],
                    "ground_truth": gt,
                }
            )

        # 转 Dataset
        dataset = Dataset.from_list(results)

        # RAGAS 评估
        logger.info("运行 RAGAS 评估...")
        scores = evaluate(
            dataset,
            metrics=[
                context_precision,
                context_recall,
                faithfulness,
                answer_relevancy,
            ],
        )

        # 输出报告
        report_path = Path(output_dir) / f"eval_report_{Path(__file__).stem}.json"
        scores.to_pandas().to_json(report_path, orient="records", force_ascii=False, indent=2)
        logger.info(f"✓ 评估报告: {report_path}")

        return {
            "context_precision": float(scores["context_precision"].mean()),
            "context_recall": float(scores["context_recall"].mean()),
            "faithfulness": float(scores["faithfulness"].mean()),
            "answer_relevancy": float(scores["answer_relevancy"].mean()),
            "report_path": str(report_path),
        }