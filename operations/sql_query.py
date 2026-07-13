"""Run an arbitrary SQL query against a DB file under /data."""
from __future__ import annotations

import sqlite3

from core.config import settings
from core.logging import get_logger
from core.security import validate_path

logger = get_logger(__name__)


def handle_run_sql_query(db_filename: str, query: str) -> str:
    db_path = validate_path(db_filename, settings.data_dir)
    if not db_path.exists():
        raise FileNotFoundError(f"{db_path} not found")

    with sqlite3.connect(db_path) as conn:
        cur = conn.cursor()
        cur.execute(query)
        result = cur.fetchall()
        conn.commit()

    result_file = validate_path("sql_query_result.txt", settings.data_dir)
    result_file.write_text(str(result), encoding="utf-8")
    return "Operation 'run_sql_query' completed: query executed and result saved."
