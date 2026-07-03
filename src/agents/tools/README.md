# Agent 工具集

## 意图

给 LangGraph / LangChain Agent 提供"可调用的工具"，
让 LLM 能**主动查知识库、查图谱、查历史笔记**而不只是纯文本生成。

## 与谁交互

- **依赖**：
  - `langchain.tools` 的 `@tool` 装饰器
  - `src/rag/rag_chain.py`（检索工具）
  - `src/graph/client.py: execute_query`（Cypher 查询工具）
  - `src/agents/memory.py: MemoryManager`（笔记读写工具）
- **产出**：被 `src/agents/graph/` 工作流中的 LLM 节点调用
- **数据流**：LLM 决定调工具 → 工具执行 → 结果回传 LLM → LLM 继续推理

## 关键契约

每个工具函数：
- 用 `@tool` 装饰器（LangChain 协议）
- 必须有 docstring（LLM 据此决定何时调用）
- 输入输出用 Pydantic BaseModel 约束
- 返回结构化 dict，不要返回裸字符串

## 推荐工具清单

| 工具名 | 输入 | 输出 | 依赖 |
|---|---|---|---|
| `search_philosophy` | query, top_k | `{text, citations}[]` | RAGChain |
| `query_concept_graph` | concept_name | `{philosophers[], related[]}` | Neo4j |
| `save_note` | concept, content | `{note_id}` | MemoryManager |
| `get_user_history` | user_id | `[{concept, timestamp}]` | MemoryManager |
| `cross_cultural_compare` | phil_a, phil_b, topic | `{response, citations}[]` | academic_qa prompt |

## 参考实现

暂无参考；建议先复制 `src/rag/rag_chain.py: RAGChain.query()` 的核心逻辑包成工具。
苏格拉底 Agent（`src/agents/socrates.py`）目前没用工具——直接调 RAGChain 即可，
升级到 Agent 模式时才需要工具。

## 待办

- [ ] 定义 `ToolResult` Pydantic 模型
- [ ] 实现 `search_philosophy`（基于 RAGChain）
- [ ] 实现 `query_concept_graph`（基于 Neo4j）
- [ ] 把现有 Agent 改造为"使用工具的 Agent"
- [ ] 工具调用日志（评估 LLM 选工具的合理性）