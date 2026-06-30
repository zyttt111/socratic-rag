"""个人学习记忆。

记录用户的：
- 阅读历史
- 偏好
- 进度
- 提问历史

用 SQLite 持久化。
"""

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

from loguru import logger


class MemoryManager:
    """学习记忆管理"""

    def __init__(self, db_path: str = "data/memory.db"):
        """初始化。

        Args:
            db_path: SQLite 数据库路径
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        """初始化数据库表"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS reading_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    philosopher TEXT,
                    book TEXT,
                    concept TEXT,
                    question TEXT,
                    answer TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS preferences (
                    user_id TEXT PRIMARY KEY,
                    favorite_philosophers TEXT,
                    learning_goals TEXT,
                    language TEXT DEFAULT 'zh'
                )
                """
            )

            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS notes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    book_id TEXT,
                    concept TEXT,
                    content TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

    def record_reading(
        self,
        user_id: str,
        philosopher: str,
        book: str,
        concept: str,
        question: str,
        answer: str,
    ):
        """记录一次阅读。"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO reading_history
                (user_id, philosopher, book, concept, question, answer)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (user_id, philosopher, book, concept, question, answer),
            )
        logger.info(f"✓ 记录阅读: {user_id} - {philosopher} - {concept}")

    def get_user_history(self, user_id: str, limit: int = 20) -> list[dict]:
        """获取用户阅读历史。"""
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(
                """
                SELECT philosopher, book, concept, question, timestamp
                FROM reading_history
                WHERE user_id = ?
                ORDER BY timestamp DESC
                LIMIT ?
                """,
                (user_id, limit),
            ).fetchall()

        return [
            {
                "philosopher": r[0],
                "book": r[1],
                "concept": r[2],
                "question": r[3],
                "timestamp": r[4],
            }
            for r in rows
        ]

    def save_note(
        self,
        user_id: str,
        book_id: str,
        concept: str,
        content: str,
    ):
        """保存笔记。"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO notes (user_id, book_id, concept, content)
                VALUES (?, ?, ?, ?)
                """,
                (user_id, book_id, concept, content),
            )

    def get_notes(self, user_id: str, concept: str | None = None) -> list[dict[str, Any]]:
        """获取笔记。"""
        with sqlite3.connect(self.db_path) as conn:
            if concept:
                rows = conn.execute(
                    """
                    SELECT book_id, concept, content, timestamp
                    FROM notes
                    WHERE user_id = ? AND concept = ?
                    ORDER BY timestamp DESC
                    """,
                    (user_id, concept),
                ).fetchall()
            else:
                rows = conn.execute(
                    """
                    SELECT book_id, concept, content, timestamp
                    FROM notes
                    WHERE user_id = ?
                    ORDER BY timestamp DESC
                    """,
                    (user_id,),
                ).fetchall()

        return [
            {
                "book_id": r[0],
                "concept": r[1],
                "content": r[2],
                "timestamp": r[3],
            }
            for r in rows
        ]

    def set_preferences(
        self,
        user_id: str,
        favorite_philosophers: list[str] | None = None,
        learning_goals: list[str] | None = None,
        language: str = "zh",
    ):
        """设置用户偏好。"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO preferences
                (user_id, favorite_philosophers, learning_goals, language)
                VALUES (?, ?, ?, ?)
                """,
                (
                    user_id,
                    json.dumps(favorite_philosophers or []),
                    json.dumps(learning_goals or []),
                    language,
                ),
            )

    def get_preferences(self, user_id: str) -> dict[str, Any]:
        """获取用户偏好。"""
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT favorite_philosophers, learning_goals, language FROM preferences WHERE user_id = ?",
                (user_id,),
            ).fetchone()

        if row:
            return {
                "favorite_philosophers": json.loads(row[0]),
                "learning_goals": json.loads(row[1]),
                "language": row[2],
            }
        return {"favorite_philosophers": [], "learning_goals": [], "language": "zh"}