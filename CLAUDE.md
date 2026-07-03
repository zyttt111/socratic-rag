# CLAUDE.md — Philosophy Agent 协作手册

> 给 Claude（Code / Cowork）的项目级规约。每次会话自动加载，请勿要求用户复述。

## 1. 项目定位

哲学学习 RAG + Agent：**陪读哲学，不替读哲学**。

- 5 位核心哲学家：苏格拉底 / 柏拉图 / 康德 / 黑格尔 / 尼采 / 海德格尔 / 庄子（谢林为扩展）
- 苏格拉底反问（不给答案，只追问）+ 哲学家辩论 + 知识图谱
- **反幻觉原则**：每个论点必须引用原文出处，标注到段落

## 2. 启动顺序（严格遵守）

```bash
docker-compose up -d       # Qdrant + Neo4j + Redis
cp .env.example .env       # 填 DEEPSEEK_API_KEY 与 ANTHROPIC_API_KEY
uv sync
uv run phil-download       # 下载 10 本原著
uv run phil-rebuild        # 构建 Qdrant 索引 + Neo4j 图谱
uv run phil-ui             # Streamlit → http://localhost:8501
```

不按顺序跑会导致 Qdrant / Neo4j 报连接错。

## 3. 架构速查

| 层 | 入口 |
|---|---|
| UI | `ui/app.py` (Streamlit，5 Tab) |
| API | `src/api/main.py` (FastAPI，port 8000) |
| RAG | `src/rag/` (BM25 + Qdrant + RRF 融合) |
| Agent | `src/agents/` (LangGraph 工作流) |
| 图谱 | `src/graph/` (Neo4j) |
| 配置 | `src/core/settings.py` (Pydantic Settings 单例) |

**5 个 CLI 入口**（在 `pyproject.toml`）：
- `phil-init` → `scripts/init_db.py`（初始化数据库 + `--rebuild-graph` 重建图谱）
- `phil-download` → `scripts/download_data.py`
- `phil-rebuild` → `scripts/rebuild_index.py`
- `phil-eval` → `scripts/run_eval.py`
- `phil-ui` → `ui/app.py`

## 4. LLM 调用规范（强制）

**所有 LLM 调用必须经工厂函数**，禁止直接 import。

```python
from src.core.llm import get_llm

llm = get_llm(model="deepseek", temperature=0.1)  # 默认
llm = get_llm(model="claude",  temperature=0.3)  # 苏格拉底/审计专用
```

- **苏格拉底反问 / 概念审计 / 关系抽取** → `claude`
- **学术问答 / 辩论发言 / 元数据抽取** → `deepseek`
- 流式调用：`stream_llm()`；token 计数：`count_tokens()`
- Embedding：`get_embeddings()`（单例缓存，bge-large-zh-v1.5）
- Rerank：`get_reranker()`（可选，bge-reranker-large）

## 5. Prompt 与引证规范

### Prompt 文件位置

`src/prompts/*.yaml`（含 `src/prompts/personas/*.yaml`）

### 双语结构（强制）

```yaml
zh:
  system: |
    ...
  user: |
    ...{question}...{context}...
en:
  system: |
    ...
  user: |
    ...
```

加载：`from src.prompts.loader import load_prompt; load_prompt("name", language="zh")`
回退顺序：`language` → `"zh"` → `_default_prompt()`

### 占位符规范

- `{question}` 用户问题
- `{context}` 检索到的背景（已格式化，含 `[1][2][3]` 引证标签）
- `{history}` 对话历史
- **禁止用 f-string 硬编码**这些占位符

### 引证格式（学术 QA 必备）

答案中每个论点必须带标签 `[1][2][3]`，最终引用清单格式：

```
[1] 《理想国》柏拉图 第七卷 514a-517a 洞穴寓言
[2] 《纯粹理性批判》康德 导言 §1-§7
```

标签映射的 `metadata` 字段：`book`、`philosopher`、`section` / `location`。

## 6. YAML 数据 Schema

图谱种子数据位置：`data/yaml/{philosophers,books,concepts}/*.yaml`
图谱构建器：`src/graph/builder.py: build_graph_from_yaml()`

### 哲学家（必填字段）

```yaml
<id>:
  zh:
    name:        # 中文名（Neo4j 节点 ID 必须与 books.yaml 的 philosopher 字段一致）
    name_en:
    era:         # 年份区间，公元前用负数
    school:
    language:
    nationality:
    style: |      # 多行字符串
    core_position: |
    key_concepts: [..]
    major_works: [..]
    influences:    [..]  # 留空也要写 []
    influenced_by: [..]
    influenced:    [..]
    famous_quotes: [..]
  en:
    name: ...
```

### 著作（必填字段）

`title, title_en, philosopher, philosopher_en, year, year_zh, translator, publisher, language, school, era, sep_entry, core_concepts[], chapters[]`

### 概念（必填字段）

`name, name_en, definition, school, related_philosophers[], related_concepts[], primary_source, sep_entry`

### 评估题（必填字段）

`id, question, philosopher, must_cite[], standard_answer, common_errors[]`

**警告**：修改 books.yaml 的 `philosopher` 中文名时，必须同步修改 philosophers.yaml 的 `zh.name`，否则 Neo4j `MERGE` 创建孤儿节点。

## 7. Anti-Patterns（4 条最高频错误）

| 错误 | 后果 | 正确做法 |
|---|---|---|
| ❌ 在 `src/agents/{debate,philosophers,graph,tools}/` 空目录里自行猜测实现 | 与已有 Agent 风格不一致 | 先读 `src/agents/socrates.py`，复用 `RAGChain` |
| ❌ 直接 `from langchain_anthropic import ChatAnthropic` | 绕过 settings、绕过 retry 装饰器 | 必须走 `get_llm(model="...")` |
| ❌ 改 Prompt 只改 zh 或 en 一个语种 | 切换语言时报错 | 双语同步；占位符保持一致 |
| ❌ 切分 chunk 时不写入 `metadata.book / section` | 学术引证就废了 | `split_text()` 后立即补 `metadata` |

## 8. 目录速查表

```
CLAUDE.md                 ← 本文件（每次会话自动加载）
pyproject.toml            ← 5 个 CLI 入口定义
docker-compose.yml        ← Qdrant + Neo4j + Redis
.env / .env.example       ← API Key（git 忽略）

src/core/llm.py           ← LLM 工厂（必须用 get_llm）
src/core/settings.py      ← 配置单例（必须用 settings / get_settings）
src/prompts/loader.py     ← Prompt 加载器
src/prompts/*.yaml        ← Prompt 模板（双语）
src/prompts/personas/     ← 5 位哲学家 persona

src/rag/rag_chain.py      ← RAG 主链（学术问答 + 引证）
src/rag/hybrid_search.py  ← BM25 + 向量 + RRF 融合
src/rag/qdrant_client.py  ← Qdrant 封装

src/agents/socrates.py    ← 苏格拉底 Agent（参考实现）
src/agents/recommender.py ← 学习推荐 Agent
src/agents/memory.py      ← MemoryManager（SQLite）

src/graph/builder.py      ← YAML → Neo4j 图谱构建
src/graph/client.py       ← Neo4j 驱动

src/data/{loader,cleaner,splitter}.py  ← 数据处理
src/evaluation/evaluator.py             ← RAGAS

scripts/init_db.py        ← phil-init
scripts/rebuild_index.py  ← phil-rebuild
scripts/download_data.py  ← phil-download
scripts/run_eval.py       ← phil-eval

data/yaml/philosophers/   ← 哲学家档案（git 提交）
data/yaml/books/          ← 著作档案（git 提交）
data/yaml/concepts/       ← 概念档案（git 提交）
data/raw/                 ← 原著（运行时下载，git 忽略）
data/processed/           ← 切分缓存（git 忽略）
data/eval/                ← RAGAS 评估题（git 提交）

docs/                     ← 架构 / 评估报告 / 博客草稿
tests/                    ← pytest-asyncio 测试
notebooks/                ← 学习笔记
```

## 9. 评估与发布

- 评估工具：RAGAS（`src/evaluation/evaluator.py`），输出到 `docs/eval_reports/`
- 4 指标阈值：**Context Precision ≥ 0.75**，**Faithfulness ≥ 0.85**
- 新增功能后必须跑 `phil-rebuild`（增量）和 `phil-eval`

## 10. 协作约定

- 中文回复（用户偏好；技术术语保留英文）
- 代码注释默认 1 行，**只解释 why，不解释 what**
- 不要主动 commit / push，等用户明确要求
- 不要 add emoji 到文件，除非用户明确要求
- 改完代码后，简短说明"改了什么 + 下一步"，不写大段总结