"""FastAPI 后端。

包含：
- 文件上传（异步任务）
- 进度查询
- 问答接口
- 知识图谱查询
"""

from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from loguru import logger

from src.core.settings import settings

app = FastAPI(
    title="Philosophy Agent API",
    description="哲学学习 RAG + Agent API",
    version="0.1.0",
)


@app.get("/")
async def root():
    """根路径"""
    return {
        "name": "Philosophy Agent",
        "version": "0.1.0",
        "docs": "/docs",
    }


@app.get("/health")
async def health():
    """健康检查"""
    return {"status": "ok"}


@app.post("/api/upload")
async def upload_book(file: UploadFile = File(...)):
    """上传书籍（异步处理）。

    TODO: 集成 Celery
    """
    # 1. 验证文件类型
    if not file.filename.endswith((".txt", ".pdf", ".md")):
        raise HTTPException(status_code=400, detail="仅支持 .txt / .pdf / .md")

    # 2. 保存文件
    target = settings.raw_dir / file.filename
    target.parent.mkdir(parents=True, exist_ok=True)

    with open(target, "wb") as f:
        content = await file.read()
        f.write(content)

    logger.info(f"✓ 上传: {target} ({len(content)} bytes)")

    # 3. TODO: 启动后台抽取任务
    # task = extract_task.delay(str(target))
    # return {"task_id": task.id, "status": "queued"}

    return {
        "status": "uploaded",
        "file": file.filename,
        "size": len(content),
        "next_step": "运行 phil-rebuild 处理",
    }


@app.get("/api/books")
async def list_books():
    """列出已上传的书籍"""
    books = []
    if settings.raw_dir.exists():
        for f in settings.raw_dir.iterdir():
            if f.is_file():
                books.append(
                    {
                        "name": f.name,
                        "size": f.stat().st_size,
                        "modified": f.stat().st_mtime,
                    }
                )
    return {"books": books}


@app.post("/api/query")
async def query(question: str):
    """问答接口"""
    from src.rag.rag_chain import RAGChain

    rag = RAGChain()
    return rag.query(question, top_k=5)


@app.get("/api/graph/concept/{concept_name}")
async def get_concept_graph(concept_name: str):
    """获取概念相关图谱"""
    from src.graph.client import execute_query

    cql = """
    MATCH (c:Concept {name: $name})<-[:DISCUSSED]-(p:Philosopher)
    OPTIONAL MATCH (c)-[:RELATED_TO]->(related:Concept)
    RETURN c.name AS concept,
           collect(DISTINCT p.name) AS philosophers,
           collect(DISTINCT related.name) AS related_concepts
    """
    results = execute_query(cql, {"name": concept_name})
    return results[0] if results else {"concept": concept_name, "philosophers": [], "related_concepts": []}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "src.api.main:app",
        host="0.0.0.0",
        port=settings.api_port,
        reload=settings.app_env == "development",
    )