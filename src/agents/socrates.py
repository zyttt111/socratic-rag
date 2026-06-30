"""苏格拉底反问 Agent。

不是给答案，是追问。
5 步反问法 + 限制回答 3 句话。
"""

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from loguru import logger

from src.core.llm import get_llm
from src.prompts.loader import load_prompt
from src.rag.rag_chain import RAGChain


class SocratesAgent:
    """苏格拉底反问 Agent"""

    def __init__(self, rag_chain: RAGChain | None = None):
        """初始化。

        Args:
            rag_chain: RAG 链（用于检索背景资料）
        """
        self.rag_chain = rag_chain or RAGChain()
        # 苏格拉底反问用 Claude（多轮对话最佳）
        self.llm = get_llm(model="claude", temperature=0.3)
        self.prompt = load_prompt("socrates")

    async def respond(
        self,
        user_question: str,
        conversation_history: list[dict] | None = None,
    ) -> dict:
        """生成反问。

        Args:
            user_question: 用户问题
            conversation_history: 对话历史 [{"role": "user/assistant", "content": ...}]

        Returns:
            {"response": ..., "questions": [...], "step": int}
        """
        # 1. 检索背景资料（不直接给答案用，只给反问时参考）
        retrieval = self.rag_chain.searcher.search(user_question, top_k=3)
        context_text = self.rag_chain._format_contexts(retrieval)

        # 2. 构造对话历史
        messages = [SystemMessage(content=self.prompt["zh"]["system"])]

        if conversation_history:
            for msg in conversation_history[-6:]:  # 保留最近 6 轮
                if msg["role"] == "user":
                    messages.append(HumanMessage(content=msg["content"]))
                elif msg["role"] == "assistant":
                    messages.append(AIMessage(content=msg["content"]))

        # 3. 当前问题 + 背景
        user_msg = self.prompt["zh"]["user"].format(
            question=user_question,
            context=context_text,
        )
        messages.append(HumanMessage(content=user_msg))

        # 4. 生成反问
        response = await self.llm.ainvoke(messages)

        return {
            "response": response.content,
            "questions": self._extract_questions(response.content),
            "step": len(conversation_history) // 2 + 1 if conversation_history else 1,
        }

    @staticmethod
    def _extract_questions(text: str) -> list[str]:
        """提取文本中的所有问句"""
        import re

        sentences = re.split(r"[。！？]", text)
        questions = [s.strip() for s in sentences if "？" in s or "?" in s]
        return [q for q in questions if len(q) > 5]