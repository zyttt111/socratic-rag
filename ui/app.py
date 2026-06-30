"""Streamlit UI 入口。

5 Tab 设计：
- 📖 书房：上传 + 阅读
- 🤔 苏格拉底：反问模式
- 💭 辩论厅：哲学家同台辩论
- 🕸️ 知识图谱：Neo4j 可视化
- 📚 学习工具：笔记 + 推荐 + 评估
"""

import sys
from pathlib import Path

# 添加 src 到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st

from src.core.settings import settings


def setup_page():
    """配置 Streamlit 页面"""
    st.set_page_config(
        page_title="哲学学习 Agent",
        page_icon="📚",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    # 自定义 CSS
    st.markdown(
        """
        <style>
        .main {
            padding: 2rem;
        }
        h1 {
            color: #2c3e50;
        }
        .stTabs [data-baseweb="tab-list"] {
            gap: 2rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_header():
    """渲染头部"""
    col1, col2, col3 = st.columns([1, 6, 1])
    with col1:
        st.markdown("# 📚")
    with col2:
        st.markdown(
            "<h1 style='text-align: center; margin: 0;'>哲学学习 Agent</h1>",
            unsafe_allow_html=True,
        )
        st.markdown(
            "<p style='text-align: center; color: gray; margin: 0;'>苏格拉底式反问 · 哲学家同台辩论 · 知识图谱</p>",
            unsafe_allow_html=True,
        )
    with col3:
        st.markdown("# 🤔")


def tab_reading_room():
    """Tab 1：书房（阅读 + 上传）"""
    st.header("📖 书房")

    col1, col2 = st.columns([2, 1])

    with col1:
        st.subheader("💬 哲学问答")
        question = st.text_input(
            "你的哲学问题",
            placeholder="例如：康德如何反驳休谟的怀疑论？",
            label_visibility="collapsed",
        )

        col_btn1, col_btn2, col_btn3 = st.columns([1, 1, 4])
        with col_btn1:
            ask_btn = st.button("🔍 提问", type="primary")
        with col_btn2:
            socrates_btn = st.button("🤔 苏格拉底模式")

        if ask_btn and question:
            with st.spinner("思考中..."):
                from src.rag.rag_chain import RAGChain

                rag = RAGChain()
                result = rag.query(question, top_k=5)

                st.markdown("### 📜 回答")
                st.markdown(result["answer"])

                st.markdown("### 📚 引用")
                for src in result["sources"]:
                    st.markdown(
                        f"- **[{src['index']}]** {src['philosopher']}《{src['book']}》{src['location']}"
                    )

                # 调试用
                with st.expander("🔍 检索细节"):
                    for ctx in result["contexts"]:
                        st.markdown(f"**Score: {ctx.get('rrf_score', ctx.get('score', 0)):.3f}**")
                        st.text(ctx["text"][:300] + "...")

        elif socrates_btn and question:
            with st.spinner("苏格拉底思考中..."):
                import asyncio

                from src.agents.socrates import SocratesAgent

                agent = SocratesAgent()
                result = asyncio.run(agent.respond(question))

                st.markdown("### 🤔 苏格拉底")
                st.info(result["response"])
                if result.get("questions"):
                    st.markdown("**追问：**")
                    for q in result["questions"]:
                        st.markdown(f"- {q}")

    with col2:
        st.subheader("📚 我的书架")
        st.info("💡 暂无书籍\n\n运行 `uv run phil-download` 下载书籍")

        # 上传区
        st.subheader("📤 上传书籍")
        uploaded_file = st.file_uploader(
            "支持 .txt / .pdf / .md",
            type=["txt", "pdf", "md"],
            label_visibility="collapsed",
        )
        if uploaded_file:
            target = settings.raw_dir / uploaded_file.name
            target.parent.mkdir(parents=True, exist_ok=True)
            with open(target, "wb") as f:
                f.write(uploaded_file.getbuffer())
            st.success(f"✓ 已保存: {uploaded_file.name}")
            st.info("运行 `uv run phil-rebuild` 处理")


def tab_socrates():
    """Tab 2：苏格拉底反问模式"""
    st.header("🤔 苏格拉底模式")
    st.markdown(
        """
        **苏格拉底从不给答案，只追问。**

        5 步反问法：
        1. **澄清前提**：你说的 X 具体指什么？
        2. **举反例**：如果情况相反，会怎样？
        3. **推到极端**：如果所有人都这样，会怎样？
        4. **区分概念**：你说的 X 和 Y 有什么不同？
        5. **回到原点**：我们为什么要讨论 X？
        """
    )

    if "socrates_chat" not in st.session_state:
        st.session_state.socrates_chat = []

    # 显示历史
    for msg in st.session_state.socrates_chat:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])

    # 输入
    if question := st.chat_input("你的哲学困惑..."):
        # 添加用户消息
        st.session_state.socrates_chat.append({"role": "user", "content": question})
        with st.chat_message("user"):
            st.write(question)

        # 生成反问
        with st.chat_message("assistant"):
            with st.spinner("苏格拉底思考中..."):
                import asyncio

                from src.agents.socrates import SocratesAgent

                agent = SocratesAgent()
                result = asyncio.run(
                    agent.respond(
                        question,
                        conversation_history=st.session_state.socrates_chat,
                    )
                )
                st.write(result["response"])
                st.session_state.socrates_chat.append(
                    {"role": "assistant", "content": result["response"]}
                )

    if st.button("🗑️ 清空对话"):
        st.session_state.socrates_chat = []
        st.rerun()


def tab_debate():
    """Tab 3：哲学家辩论厅"""
    st.header("💭 哲学家辩论厅")

    st.markdown("选择议题，让 5 位哲学家同台辩论")

    topic = st.text_input("辩论议题", value="什么是自由？")

    philosophers = ["苏格拉底", "康德", "黑格尔", "尼采", "海德格尔", "庄子"]

    st.markdown("**参与的哲学家**：" + " · ".join(philosophers))

    if st.button("🎭 开始辩论", type="primary"):
        with st.spinner("辩论进行中..."):
            # TODO: 接入 Multi-Agent 辩论
            st.info("Multi-Agent 辩论功能开发中...")
            st.markdown(
                """
                **示例输出**：

                > **苏格拉底**：自由是什么？我们首先要问的是，你说的"自由"是行动的自由还是意志的自由？
                
                > **康德**：自由必须建立在理性之上，是摆脱感性冲动的"先验自由"。
                
                > **尼采**：自由是权力意志的彰显！不是道德的束缚，而是创造的勇气！
                
                > **庄子**：北冥有鱼... 逍遥游才是真正的自由，无待于外。
                """
            )


def tab_knowledge_graph():
    """Tab 4：知识图谱"""
    st.header("🕸️ 知识图谱")

    st.markdown(
        """
        在 Neo4j Browser（http://localhost:7474）查看完整图谱可视化。
        
        下方是核心统计。
        """
    )

    col1, col2, col3 = st.columns(3)

    # TODO: 接入 Neo4j 查询
    try:
        from src.graph.client import execute_query

        philosopher_count = execute_query("MATCH (p:Philosopher) RETURN count(p) AS c")[0]["c"]
        concept_count = execute_query("MATCH (c:Concept) RETURN count(c) AS c")[0]["c"]
        book_count = execute_query("MATCH (b:Book) RETURN count(b) AS c")[0]["c"]

        with col1:
            st.metric("哲学家", philosopher_count)
        with col2:
            st.metric("概念", concept_count)
        with col3:
            st.metric("著作", book_count)
    except Exception as e:
        st.warning(f"⚠️ Neo4j 未连接: {e}")

    # 概念查询
    st.subheader("🔍 概念查询")
    concept = st.text_input("输入概念名", value="现象学")

    if concept and st.button("查询"):
        try:
            from src.graph.client import execute_query

            result = execute_query(
                """
                MATCH (c:Concept {name: $name})<-[:DISCUSSED]-(p:Philosopher)
                OPTIONAL MATCH (c)-[:RELATED_TO]->(r:Concept)
                RETURN c.name AS concept,
                       collect(DISTINCT p.name) AS philosophers,
                       collect(DISTINCT r.name) AS related
                """,
                {"name": concept},
            )
            if result:
                r = result[0]
                st.markdown(f"**{r['concept']}**")
                st.markdown(f"- 相关哲学家：{', '.join(r['philosophers'])}")
                if r["related"]:
                    st.markdown(f"- 相关概念：{', '.join(r['related'])}")
            else:
                st.info("未找到该概念")
        except Exception as e:
            st.error(f"查询失败: {e}")


def tab_learning_tools():
    """Tab 5：学习工具"""
    st.header("📚 学习工具")

    tab1, tab2, tab3 = st.tabs(["📝 我的笔记", "🎯 学习路径推荐", "📊 RAGAS 评估"])

    with tab1:
        st.subheader("我的笔记")
        st.info("💡 接入 MemoryManager 后启用")

        # 简化版笔记
        note_concept = st.text_input("概念")
        note_content = st.text_area("笔记内容")
        if st.button("💾 保存笔记"):
            try:
                from src.agents.memory import MemoryManager

                memory = MemoryManager()
                memory.save_note("default_user", "philosophy", note_concept, note_content)
                st.success("✓ 已保存")
            except Exception as e:
                st.error(f"保存失败: {e}")

    with tab2:
        st.subheader("主动阅读推荐")
        if st.button("🎯 生成推荐"):
            with st.spinner("分析中..."):
                import asyncio

                from src.agents.recommender import LearningRecommender

                rec = LearningRecommender()
                result = asyncio.run(rec.recommend("default_user"))

                st.markdown("### 📚 推荐学习")
                for r in result["recommendations"]:
                    with st.expander(f"**{r['concept']}** - {r['philosopher']}"):
                        st.markdown(f"📖 **{r['book']}**")
                        st.markdown(f"💡 {r['reason']}")

    with tab3:
        st.subheader("RAGAS 评估")
        st.markdown("运行 `uv run phil-eval` 启动评估")
        st.info("评估结果会保存到 docs/eval_reports/")

        st.markdown(
            """
            **4 个核心指标**：
            - **Context Precision**：检索段落的相关性
            - **Context Recall**：相关段落的召回率
            - **Faithfulness**：答案忠于原文（最关键）
            - **Answer Relevancy**：答案切题性
            
            **目标分数**：
            - Context Precision ≥ 0.75
            - Faithfulness ≥ 0.85
            """
        )


def main():
    """主入口"""
    setup_page()
    render_header()

    tab1, tab2, tab3, tab4, tab5 = st.tabs(
        [
            "📖 书房",
            "🤔 苏格拉底",
            "💭 辩论厅",
            "🕸️ 知识图谱",
            "📚 学习工具",
        ]
    )

    with tab1:
        tab_reading_room()
    with tab2:
        tab_socrates()
    with tab3:
        tab_debate()
    with tab4:
        tab_knowledge_graph()
    with tab5:
        tab_learning_tools()

    # 侧边栏
    with st.sidebar:
        st.markdown("### ⚙️ 系统状态")
        st.markdown(f"- **环境**: {settings.app_env}")
        st.markdown(f"- **Qdrant**: {settings.qdrant_host}:{settings.qdrant_port}")
        st.markdown(f"- **Neo4j**: {settings.neo4j_uri}")

        st.markdown("### 🔗 链接")
        st.markdown("- [Neo4j Browser](http://localhost:7474)")
        st.markdown("- [Qdrant Dashboard](http://localhost:6333/dashboard)")
        st.markdown("- [API Docs](http://localhost:8000/docs)")

        st.markdown("### 📖 帮助")
        st.code(
            "uv run phil-download  # 下载数据\n"
            "uv run phil-init      # 初始化数据库\n"
            "uv run phil-rebuild   # 重建索引\n"
            "uv run phil-eval      # 跑评估\n"
            "uv run phil-ui        # 启动界面",
            language="bash",
        )


if __name__ == "__main__":
    main()