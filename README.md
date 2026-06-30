# Socratic RAG · Philosophy Learning Agent

> **Socratic RAG** — Let AI read philosophy with you, the Socratic way
> Questioning · Debate · Knowledge Graph · Cross-cultural Comparison

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![GitHub stars](https://img.shields.io/github/stars/zyttt111/socratic-rag?style=social)](https://github.com/zyttt111/socratic-rag)
[![RAGAS](https://img.shields.io/badge/RAGAS-eval-success)](docs/eval_reports/)

> 🤖 "AI shouldn't read philosophy for you. It should read philosophy *with* you." — inspired by Socrates

---

## ✨ 项目特点

| 特性 | 说明 |
|---|---|
| 🤖 **苏格拉底反问** | 不直接给答案，用 5 步反问法引导你思考 |
| 💭 **哲学家辩论** | 5 位哲学家 Agent 同台辩论"自由"等议题 |
| 🕸️ **知识图谱** | Neo4j 可视化概念-哲学家-著作关系 |
| 📚 **学术引证** | 每个论点都引用原文，定位到段落 |
| 🌍 **跨文化对比** | 海德格尔 vs 庄子，康德 vs 王阳明 |
| 📖 **概念谱系** | 一个概念的"家谱"，从起源到当代 |
| 🎓 **思想实验** | 电车难题、洞穴寓言、庄周梦蝶 |

---

## 🚀 快速开始（5 分钟跑起来）

### 前置依赖

- Python 3.11+
- [uv](https://docs.astral.sh/uv/)（包管理，比 pip 快 100 倍）
- Docker（用于 Qdrant + Neo4j + Redis）

### 安装

```bash
# 1. 克隆仓库
git clone git@github.com:zyttt111/socratic-rag.git
cd socratic-rag

# 2. 安装依赖（uv 自动创建虚拟环境）
uv sync

# 3. 配置 API key
cp .env.example .env
# 编辑 .env，填入 DEEPSEEK_API_KEY

# 4. 启动依赖服务（Qdrant + Neo4j + Redis）
docker-compose up -d

# 5. 下载哲学原著（10 本经典，从公开源）
uv run phil-download

# 6. 一键构建知识库（Embedding + 概念抽取）
uv run phil-rebuild
# 耗时约 30-60 分钟

# 7. 启动界面
uv run phil-ui
# 浏览器打开 http://localhost:8501
```

---

## 🏗️ 架构

```
┌──────────────────────────────────────────────────────────┐
│  UI 层 (Streamlit)                                        │
│  ├─ 📖 书房  🤔 苏格拉底  💭 辩论厅  🕸️ 图谱  📚 工具  │
└─────────────────────────┬────────────────────────────────┘
                          │
┌─────────────────────────▼────────────────────────────────┐
│  API 层 (FastAPI)                                         │
│  ├─ /upload  /progress  /query  /debate  /graph         │
└─────────────────────────┬────────────────────────────────┘
                          │
┌──────────────┬──────────▼──────────┬─────────────────────┐
│  RAG 检索    │  Agent 推理           │  知识图谱            │
│  ├─ BM25    │  ├─ 苏格拉底          │  ├─ 概念节点         │
│  ├─ 向量    │  ├─ 辩论主持人         │  ├─ 哲学家节点       │
│  └─ 图增强  │  └─ 学习路径推荐       │  └─ 关系三元组       │
└──────────────┴──────────┬──────────┴─────────────────────┘
                          │
┌─────────────────────────▼────────────────────────────────┐
│  数据层                                                    │
│  ├─ Qdrant（向量库）  ├─ Neo4j（图谱）  ├─ SQLite（笔记）│
└──────────────────────────────────────────────────────────┘
```

---

## 📁 项目结构

```
philosophy-agent-python/
├── README.md                  # 项目说明
├── pyproject.toml             # uv 项目配置
├── docker-compose.yml         # Qdrant + Neo4j + Redis
├── .env.example               # API key 模板
│
├── src/                       # 核心代码
│   ├── core/                  # LLM 调用、配置
│   ├── data/                  # 数据处理（PDF/切分）
│   ├── rag/                   # RAG 检索（BM25/向量/图增强）
│   ├── prompts/               # 提示词（5 个哲学家 persona）
│   ├── agents/                # Agent 逻辑
│   │   ├── tools/             # Agent 工具
│   │   ├── graph/             # LangGraph 工作流
│   │   ├── debate/            # Multi-Agent 辩论
│   │   └── philosophers/      # 5 个哲学家实现
│   ├── graph/                 # Neo4j 操作
│   ├── evaluation/            # RAGAS 评估
│   ├── export/                # Anki/Markdown 导出
│   └── api/                   # FastAPI 后端
│
├── data/                      # 数据（按需下载，不提交 Git）
│   ├── yaml/                  # 哲学家/概念/著作档案 ✅ 上传
│   ├── eval/                  # 评估集 ✅ 上传
│   ├── raw/                   # 原著原文 ❌ 运行时下载
│   ├── processed/             # 切分结果
│   └── calibration/SEP/       # SEP 校准源
│
├── scripts/                   # 工具脚本
│   ├── download_data.py       # 一键下载 10 本经典
│   ├── init_db.py             # 一键初始化 Qdrant + Neo4j
│   ├── rebuild_index.py       # 一键重建索引
│   └── run_eval.py            # 一键跑 RAGAS
│
├── ui/                        # Streamlit 界面
├── tests/                     # 测试
├── notebooks/                 # 学习笔记
└── docs/                      # 文档 + 博客
```

---

## 📚 哲学原著清单（默认 10 本）

| 哲学家 | 著作 | 时代 | 重要概念 |
|---|---|---|---|
| 柏拉图 | 《理想国》 | 公元前 380 | 理念论、洞穴寓言、哲人王 |
| 亚里士多德 | 《尼各马可伦理学》 | 公元前 340 | 德性、中庸、幸福论 |
| 笛卡尔 | 《第一哲学沉思集》 | 1641 | 我思故我在、二元论 |
| 康德 | 《纯粹理性批判》 | 1781 | 先天综合判断、物自体、二律背反 |
| 黑格尔 | 《精神现象学》 | 1807 | 绝对精神、辩证法、主奴意识 |
| 叔本华 | 《作为意志和表象的世界》 | 1818 | 意志、悲观主义 |
| 尼采 | 《查拉图斯特拉如是说》 | 1883 | 永恒轮回、权力意志、超人 |
| 海德格尔 | 《存在与时间》 | 1927 | 此在、存在论差异、烦 |
| 萨特 | 《存在与虚无》 | 1943 | 存在先于本质、自由 |
| 庄子 | 《庄子》 | 公元前 300 | 逍遥、齐物、道 |

> **原著来源**：英文版 [Project Gutenberg](https://www.gutenberg.org/)，中文译本 [汉译世界学术名著丛书](https://www.cp.com.cn/)

---

## 🎯 12 个差异化亮点

1. ✅ **学术引证** — 每个论点引用原文，定位到段落
2. ✅ **苏格拉底反问** — 5 步反问法，不给答案只追问
3. ✅ **Neo4j 知识图谱** — 概念-哲学家-著作三元组
4. ✅ **Multi-Agent 辩论** — 5 位哲学家同台辩论
5. ✅ **个人学习记忆** — 记录你的阅读历史和偏好
6. ✅ **主动阅读计划** — 根据你的进度推荐下一步
7. ✅ **角色扮演** — 让苏格拉底教你 vs 让康德教你
8. ✅ **RAGAS 评估** — 自动评估答案质量
9. ✅ **中英德三语** — 输出多语言
10. ✅ **思想实验模拟** — 电车难题、洞穴寓言、庄周梦蝶
11. ✅ **跨文化对比** — 海德格尔 vs 庄子
12. ✅ **多格式输出** — Markdown / Anki 卡片 / Mermaid 思维导图

---

## 🛠️ 技术栈

| 层 | 选型 | 理由 |
|---|---|---|
| LLM | DeepSeek-V3 + Claude Sonnet 4.5 | 性价比 + 中文哲学 SOTA |
| Embedding | bge-large-zh-v1.5（本地）| 中文 SOTA + 免费 |
| RAG 框架 | LangChain 0.3 + LlamaIndex 0.12 | 生态成熟 |
| Agent | LangGraph 0.2 | 状态机风格，适合 Java 思维 |
| 向量库 | Qdrant 1.12 | Rust 实现，毫秒级检索 |
| 知识图谱 | Neo4j 5.x | 唯一成熟选择 |
| 后端 | FastAPI | 类型注解接近 Java |
| 前端 | Streamlit | 不写 HTML 也能出 demo |
| 包管理 | uv | 比 pip 快 100 倍 |

---

## 📖 文档导航

- [哲学 RAG 数据策略](docs/data-strategy.md)
- [评估体系](docs/evaluation-strategy.md)
- [知识抽取架构](docs/knowledge-extraction-architecture.md)
- [抽取工具与成本](docs/extraction-tooling-cost.md)
- [知识库形态与 Git](docs/knowledge-base-form-and-git.md)
- [上传即用与哲学 UX](docs/upload-and-philosophy-ux.md)
- [完整 6 周计划](../sessions/mvs_137f1fb402304ae0abf96aee7400e01d/workspace/philosophy-agent-plan/philosophy-agent-python-plan.md)

---

## 🎓 学习路径（6 周）

| 周 | 主题 | 关键产出 |
|---|---|---|
| W1 | Python 基础 + RAG 最小闭环 | "什么是现象学"能查到原文 |
| W2 | 提示工程 + 学术引证 | 5 个哲学家风格模板 |
| W3 | Agent 基础 + 苏格拉底 | 能反问 5 轮 |
| W4 | Multi-Agent 辩论 | 5 位哲学家辩论 |
| W5 | Neo4j + RAGAS | 图谱可视化 + 评估 |
| W6 | 前端 + 博客 | Streamlit + 3 篇博客 |

详见 [完整计划](docs/)。

---

## 🤝 贡献指南

欢迎贡献：

- 📚 **新增哲学家档案**（在 `data/yaml/philosophers/` 加 YAML）
- 🔍 **新增评估题**（在 `data/eval/` 加 YAML）
- 🐛 **修 Bug / 优化 Prompt**
- 🌐 **多语言翻译**

---

## 📄 License

MIT License - 详见 [LICENSE](LICENSE)

---

## 🙏 致谢

- [LangChain](https://github.com/langchain-ai/langchain) - RAG 框架
- [Qdrant](https://github.com/qdrant/qdrant) - 向量数据库
- [Neo4j](https://github.com/neo4j/neo4j) - 知识图谱
- [DeepSeek](https://www.deepseek.com/) - 中文 SOTA LLM
- [Stanford Encyclopedia of Philosophy](https://plato.stanford.edu/) - 校准源

---

> **不是让 AI 替你读哲学，而是让 AI 陪你读哲学。**
> 
> *— 苏格拉底*