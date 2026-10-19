import json
import os
import sqlite3
import time
from typing import Any, Dict, List, Optional

DB_PATH = "task_history.db"


def get_db_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with get_db_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS task_history (
                id TEXT PRIMARY KEY,
                title TEXT,
                datamodel TEXT,
                llm_model TEXT,
                lang_mode TEXT,
                char_count INTEGER,
                status TEXT,
                created_at TEXT,
                input_text TEXT,
                result_json TEXT,
                error TEXT
            )
            """
        )
        conn.commit()


def save_or_update_task(
    task_id: str,
    title: str,
    datamodel: str,
    llm_model: str,
    lang_mode: str,
    char_count: int,
    status: str,
    created_at: Optional[str] = None,
    input_text: str = "",
    result: Optional[Dict[str, Any]] = None,
    error: Optional[str] = None,
) -> None:
    init_db()
    if not created_at:
        created_at = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())

    result_str = json.dumps(result, ensure_ascii=False) if result else None

    with get_db_connection() as conn:
        conn.execute(
            """
            INSERT INTO task_history (
                id, title, datamodel, llm_model, lang_mode, char_count,
                status, created_at, input_text, result_json, error
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                status = excluded.status,
                result_json = coalesce(excluded.result_json, task_history.result_json),
                error = coalesce(excluded.error, task_history.error)
            """,
            (
                task_id,
                title,
                datamodel,
                llm_model,
                lang_mode,
                char_count,
                status,
                created_at,
                input_text,
                result_str,
                error,
            ),
        )
        conn.commit()


def update_task_result(
    task_id: str,
    status: str,
    result: Optional[Dict[str, Any]] = None,
    error: Optional[str] = None,
) -> None:
    init_db()
    result_str = json.dumps(result, ensure_ascii=False) if result else None
    with get_db_connection() as conn:
        conn.execute(
            """
            UPDATE task_history
            SET status = ?, result_json = coalesce(?, result_json), error = ?
            WHERE id = ?
            """,
            (status, result_str, error, task_id),
        )
        conn.commit()


def get_task(task_id: str) -> Optional[Dict[str, Any]]:
    init_db()
    with get_db_connection() as conn:
        cur = conn.execute("SELECT * FROM task_history WHERE id = ?", (task_id,))
        row = cur.fetchone()
        if not row:
            return None
        d = dict(row)
        if d.get("result_json"):
            try:
                d["result"] = json.loads(d["result_json"])
            except Exception:
                d["result"] = None
        else:
            d["result"] = None
        return d


def list_tasks(limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
    init_db()
    with get_db_connection() as conn:
        cur = conn.execute(
            """
            SELECT id, title, datamodel, llm_model, lang_mode, char_count,
                   status, created_at, error,
                   CASE WHEN result_json IS NOT NULL THEN 1 ELSE 0 END as has_result
            FROM task_history
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
            """,
            (limit, offset),
        )
        return [dict(row) for row in cur.fetchall()]


def delete_task(task_id: str) -> bool:
    init_db()
    with get_db_connection() as conn:
        cur = conn.execute("DELETE FROM task_history WHERE id = ?", (task_id,))
        conn.commit()
        return cur.rowcount > 0


def clear_all_tasks() -> bool:
    init_db()
    with get_db_connection() as conn:
        conn.execute("DELETE FROM task_history")
        conn.commit()
        return True


def get_stats() -> Dict[str, Any]:
    init_db()
    with get_db_connection() as conn:
        cur = conn.execute("SELECT count(*) as total, sum(char_count) as total_chars FROM task_history")
        r1 = cur.fetchone()
        total = r1["total"] or 0
        total_chars = r1["total_chars"] or 0

        cur = conn.execute("SELECT count(*) as completed FROM task_history WHERE status = 'completed'")
        completed = cur.fetchone()["completed"] or 0

        cur = conn.execute("SELECT count(*) as stopped FROM task_history WHERE status = 'stopped'")
        stopped = cur.fetchone()["stopped"] or 0

        cur = conn.execute("SELECT count(*) as failed FROM task_history WHERE status = 'failed'")
        failed = cur.fetchone()["failed"] or 0

        return {
            "total": total,
            "completed": completed,
            "stopped": stopped,
            "failed": failed,
            "total_chars": total_chars,
        }
