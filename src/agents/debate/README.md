# Multi-Agent 哲学家辩论

## 意图

让 N 位哲学家（柏拉图 / 康德 / 黑格尔 / 尼采 / 海德格尔 / 庄子...）就同一议题多轮发言，
形成"同台辩论"效果，输出有立场的对话流。

## 与谁交互

- **依赖**：
  - `src/rag/rag_chain.py: RAGChain`（每位哲学家发言前检索原文支撑）
  - `src/prompts/debate.yaml`（辩论主持 prompt）
  - `src/prompts/personas/*.yaml`（每位哲学家的 system prompt）
  - `src/agents/socrates.py`（参考实现风格）
- **产出**：被 `ui/app.py:tab_debate()` 调用（目前是 mock 输出，见 `ui/app.py:201` 占位）
- **数据流**：议题 → 加载 personas → 串行/并行发言 → 拼接输出

## 关键契约

- 输入：`{topic: str, philosophers: list[str], rounds: int = 2}`
- 输出：`{"transcript": [{"philosopher": str, "round": int, "content": str, "citations": [...]}, ...]}`
- LLM：每位哲学家用 `get_llm(model="deepseek")`（辩论量大）+ persona system prompt

## 参考实现

参照 `src/agents/socrates.py` 的模式：
- 构造注入 `RAGChain`
- `async def respond(...)` 命名风格
- 返回 dict 而非裸字符串

但辩论是**多方**而非一对一，需要：
- 状态管理（每轮发言顺序、上下文累积）
- 推荐用 LangGraph 状态机（见 `src/agents/graph/README.md`）

## 待办

- [ ] 定义 `DebateOrchestrator` 类
- [ ] 集成 `src/prompts/personas/*.yaml`
- [ ] 用 LangGraph 编排多轮发言
- [ ] 替换 `ui/app.py:tab_debate()` 的 mock 输出
- [ ] 加 RAGAS 评估：辩论质量、立场一致性