# 哲学家 Persona 实例化

## 意图

把 `src/prompts/personas/*.yaml` 中的 5-6 位哲学家档案
**实例化为可调用的 Agent**，让用户"跟康德学哲学"或"问尼采看问题"。

## 与谁交互

- **依赖**：
  - `src/prompts/personas/<name>.yaml`（persona 字段：style, core_position, key_concepts）
  - `src/rag/rag_chain.py: RAGChain`（每个回答前检索该哲学家作品）
  - `src/core/llm.py: get_llm`（默认 deepseek；尼采等需要"温度"高的可调高）
- **产出**：被辩论厅 / 学习路径 / 角色扮演功能调用
- **数据流**：用户问题 → 加载 persona system → RAG 检索该哲学家作品 → 生成回答

## 关键契约

- 输入：`{philosopher: str, question: str, history?: list[dict]}`
- 输出：`{"response": str, "citations": [...], "philosopher": str}`
- 引用：必须来自该哲学家的著作，标注 `《著作》哲学家 章节`
- 风格：必须贴近 persona.yaml 中 `style` 字段定义的语气

## 参考实现

参照 `src/agents/socrates.py`：
- 单 persona 的 system prompt 来自 `load_prompt("socrates")`
- 通用 `async respond()` 签名

哲学家 persona 与苏格拉底的差异：
- 苏格拉底强制 `model="claude"`（对话质量）
- 哲学家可用 `model="deepseek"`（成本低）
- 苏格拉底追问；哲学家**主张**（立场鲜明）

## 待办

- [ ] 设计 `PhilosopherAgent` 基类（persona + llm + rag）
- [ ] 实现 5 个子类：`PlatoAgent` / `KantAgent` / `HegelAgent` / `NietzscheAgent` / `ZhuangziAgent`
- [ ] 在 `src/prompts/personas/` 补全 6 个 persona YAML（参考 `schelling` 的 schema）
- [ ] 加 persona 一致性评估（防 LLM 漂移到通用回答）