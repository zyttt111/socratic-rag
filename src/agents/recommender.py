"""主动阅读推荐。

基于用户历史和当前概念，推荐下一步阅读。
"""

from langchain_core.messages import HumanMessage, SystemMessage
from loguru import logger

from src.agents.memory import MemoryManager
from src.core.llm import get_llm


class LearningRecommender:
    """学习推荐器"""

    def __init__(self, memory: MemoryManager | None = None):
        """初始化。

        Args:
            memory: 记忆管理器
        """
        self.memory = memory or MemoryManager()
        self.llm = get_llm(model="deepseek", temperature=0.5)

    async def recommend(
        self,
        user_id: str,
        current_concept: str | None = None,
    ) -> dict:
        """推荐下一步学习。

        Args:
            user_id: 用户 ID
            current_concept: 当前正在学习的概念

        Returns:
            {"recommendations": [...], "reasoning": ...}
        """
        # 1. 获取用户历史
        history = self.memory.get_user_history(user_id, limit=30)
        prefs = self.memory.get_preferences(user_id)

        if not history:
            return {
                "recommendations": [
                    {"concept": "现象学", "reason": "入门经典主题"},
                    {"concept": "柏拉图理念论", "reason": "西方哲学根基"},
                ],
                "reasoning": "暂无学习历史，从经典主题开始",
            }

        # 2. 用 LLM 生成推荐
        history_text = "\n".join(
            [
                f"- {h['philosopher']} - {h['book']} - {h['concept']}"
                for h in history[:15]
            ]
        )

        prompt = f"""你是哲学学习推荐专家。

【用户已学历史】
{history_text}

【当前概念】
{current_concept or "无"}

【用户偏好】
- 喜欢的哲学家：{', '.join(prefs['favorite_philosophers']) or '未知'}
- 学习目标：{', '.join(prefs['learning_goals']) or '未知'}

请基于以上信息，推荐 5 个下一步应该学习的概念，按优先级排序：

要求：
1. 与已学概念有逻辑递进关系
2. 覆盖不同哲学家（不要只推一个哲学家）
3. 每个推荐附理由（为什么推荐）
4. 推荐要具体（概念名 + 哲学家 + 著作）

输出格式（YAML）：
```yaml
- concept: 概念名
  philosopher: 哲学家
  book: 著作
  reason: 1-2 句理由
```"""

        messages = [
            SystemMessage(content="你是哲学学习推荐专家。"),
            HumanMessage(content=prompt),
        ]

        response = await self.llm.ainvoke(messages)

        # 3. 解析 YAML（简化版，正则提取）
        recommendations = self._parse_yaml_response(response.content)

        return {
            "recommendations": recommendations,
            "reasoning": response.content,
        }

    @staticmethod
    def _parse_yaml_response(text: str) -> list[dict]:
        """解析 YAML 响应（简化版）"""
        import re

        recommendations = []
        pattern = r"- concept:\s*([^\n]+)\s+philosopher:\s*([^\n]+)\s+book:\s*([^\n]+)\s+reason:\s*([^\n]+)"
        matches = re.findall(pattern, text)

        for m in matches:
            recommendations.append(
                {
                    "concept": m[0].strip(),
                    "philosopher": m[1].strip(),
                    "book": m[2].strip(),
                    "reason": m[3].strip(),
                }
            )

        return recommendations[:5]