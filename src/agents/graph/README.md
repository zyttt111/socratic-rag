# LangGraph 工作流

## 意图

用 LangGraph 状态机编排**多步、多 Agent、有循环**的工作流，
比如"学习路径推荐 → 苏格拉底反问 → 评估掌握度 → 推荐下一步"。

## 与谁交互

- **依赖**：
  - `langgraph>=0.2.0`（见 `pyproject.toml`）
  - 所有 `src/agents/*.py`（作为节点 Node）
  - `src/rag/rag_chain.py: RAGChain`（检索节点）
- **产出**：被 `ui/app.py` 各 Tab 调用，或作为子流程嵌入更大 Agent
- **数据流**：用户输入 → 状态机状态更新 → 路由判断 → 节点执行 → 最终输出

## 关键契约

- 状态 Schema：用 TypedDict 定义 `WorkflowState`
- 节点签名：`async def node(state: WorkflowState) -> dict`（返回状态增量）
- 边：条件边（conditional edges）基于 `state["route"]` 决定下一步

## 参考实现

参照 `src/agents/socrates.py` 的 `respond()` 方法作为最简"单节点工作流"。
LangGraph 升级版的关键差异：
- 状态在节点间传递（不丢失 history）
- 条件路由（"如果回答模糊，回到反问节点"）
- 循环（"反问 5 步法"是天然的循环）

## 待办

- [ ] 定义 `WorkflowState` TypedDict
- [ ] 实现第一个工作流：`SocraticLoop`（5 步反问状态机）
- [ ] 实现 `DebateFlow`（多哲学家轮替发言）
- [ ] 实现 `LearningPath`（推荐 → 反问 → 评估 → 再推荐）
- [ ] 加状态可视化（langgraph 的 draw 方法）