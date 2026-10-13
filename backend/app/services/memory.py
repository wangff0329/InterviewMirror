import json
import sqlite3
from contextlib import closing
from datetime import datetime

from app.config import Settings
from app.schemas import InterviewSessionAnalysis, InterviewSessionTurn, MemoryItem


def init_memory_database(settings: Settings) -> None:
    with closing(sqlite3.connect(settings.database_path)) as connection:
        with connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS interview_sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    job_description TEXT NOT NULL,
                    analysis_json TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS interview_turns (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id INTEGER NOT NULL,
                    question TEXT NOT NULL,
                    answer TEXT NOT NULL,
                    evaluation_json TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (session_id) REFERENCES interview_sessions(id)
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS memory_items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    memory_type TEXT NOT NULL,
                    content TEXT NOT NULL,
                    confidence REAL NOT NULL,
                    source_session_id INTEGER,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (source_session_id) REFERENCES interview_sessions(id)
                )
                """
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_memory_items_user ON memory_items(user_id, updated_at DESC)"
            )


def create_memory(settings: Settings, user_id: int, memory: MemoryItem) -> MemoryItem:
    now = datetime.now().isoformat(timespec="seconds")
    with closing(sqlite3.connect(settings.database_path)) as connection:
        with connection:
            existing = connection.execute(
                """
                SELECT id FROM memory_items
                WHERE user_id = ? AND memory_type = ? AND content = ?
                """,
                (user_id, memory.memory_type, memory.content.strip()),
            ).fetchone()
            if existing:
                connection.execute(
                    """
                    UPDATE memory_items
                    SET confidence = MAX(confidence, ?),
                        source_session_id = COALESCE(?, source_session_id),
                        updated_at = ?
                    WHERE id = ? AND user_id = ?
                    """,
                    (
                        memory.confidence,
                        memory.source_session_id,
                        now,
                        existing[0],
                        user_id,
                    ),
                )
                return memory.model_copy(
                    update={"id": existing[0], "created_at": None, "updated_at": now}
                )
            cursor = connection.execute(
                """
                INSERT INTO memory_items
                    (user_id, memory_type, content, confidence, source_session_id, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    user_id,
                    memory.memory_type,
                    memory.content.strip(),
                    memory.confidence,
                    memory.source_session_id,
                    now,
                    now,
                ),
            )
            return memory.model_copy(update={"id": cursor.lastrowid, "created_at": now, "updated_at": now})


def update_memory(
    settings: Settings, user_id: int, memory_id: int, memory: MemoryItem
) -> MemoryItem | None:
    now = datetime.now().isoformat(timespec="seconds")
    with closing(sqlite3.connect(settings.database_path)) as connection:
        with connection:
            cursor = connection.execute(
                """
                UPDATE memory_items
                SET memory_type = ?, content = ?, confidence = ?, updated_at = ?
                WHERE id = ? AND user_id = ?
                """,
                (
                    memory.memory_type,
                    memory.content.strip(),
                    memory.confidence,
                    now,
                    memory_id,
                    user_id,
                ),
            )
            if cursor.rowcount == 0:
                return None
    return memory.model_copy(update={"id": memory_id, "updated_at": now})


def list_memories(
    settings: Settings, user_id: int, memory_type: str | None = None
) -> list[MemoryItem]:
    query = """
        SELECT id, memory_type, content, confidence, source_session_id, created_at, updated_at
        FROM memory_items
        WHERE user_id = ?
    """
    parameters: list[object] = [user_id]
    if memory_type:
        query += " AND memory_type = ?"
        parameters.append(memory_type)
    query += " ORDER BY updated_at DESC, id DESC"
    with closing(sqlite3.connect(settings.database_path)) as connection:
        rows = connection.execute(query, parameters).fetchall()
    return [
        MemoryItem(
            id=row[0],
            memory_type=row[1],
            content=row[2],
            confidence=row[3],
            source_session_id=row[4],
            created_at=row[5],
            updated_at=row[6],
        )
        for row in rows
    ]


def delete_memory(settings: Settings, user_id: int, memory_id: int) -> bool:
    with closing(sqlite3.connect(settings.database_path)) as connection, connection:
        cursor = connection.execute(
            "DELETE FROM memory_items WHERE id = ? AND user_id = ?",
            (memory_id, user_id),
        )
    return cursor.rowcount > 0


def save_interview_session(
    settings: Settings,
    user_id: int,
    job_description: str,
    turns: list[InterviewSessionTurn],
    analysis: InterviewSessionAnalysis,
) -> int:
    now = datetime.now().isoformat(timespec="seconds")
    analysis_json = analysis.model_dump_json()
    with closing(sqlite3.connect(settings.database_path)) as connection:
        with connection:
            cursor = connection.execute(
                """
                INSERT INTO interview_sessions (user_id, job_description, analysis_json, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (user_id, job_description.strip(), analysis_json, now),
            )
            session_id = cursor.lastrowid
            connection.executemany(
                """
                INSERT INTO interview_turns (session_id, question, answer, evaluation_json)
                VALUES (?, ?, ?, ?)
                """,
                [
                    (session_id, turn.question, turn.answer, turn.evaluation.model_dump_json())
                    for turn in turns
                ],
            )
    extracted = [
        ("strength", item) for item in analysis.strengths
    ] + [
        ("weakness", item) for item in analysis.priorities
    ] + [
        ("plan", item) for item in analysis.next_practice_plan
    ]
    for memory_type, content in extracted:
        create_memory(
            settings,
            user_id,
            MemoryItem(
                memory_type=memory_type,
                content=content,
                confidence=0.8,
                source_session_id=session_id,
            ),
        )
    return session_id


def list_interview_sessions(settings: Settings, user_id: int) -> list[dict]:
    with closing(sqlite3.connect(settings.database_path)) as connection:
        rows = connection.execute(
            """
            SELECT id, job_description, analysis_json, created_at
            FROM interview_sessions
            WHERE user_id = ?
            ORDER BY created_at DESC, id DESC
            """,
            (user_id,),
        ).fetchall()
    return [
        {
            "id": row[0],
            "job_description": row[1],
            "analysis": json.loads(row[2]),
            "created_at": row[3],
        }
        for row in rows
    ]
