"""Agent 模块。

包含：
- tools: Agent 工具
- graph: LangGraph 工作流
- socrates: 苏格拉底反问 Agent
- debate: Multi-Agent 辩论
- memory: 个人学习记忆
- recommender: 主动推荐
"""

from src.agents.socrates import SocratesAgent
from src.agents.memory import MemoryManager
from src.agents.recommender import LearningRecommender

__all__ = ["SocratesAgent", "MemoryManager", "LearningRecommender"]