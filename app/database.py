import sqlite3
from pathlib import Path
from typing import Iterable

import pandas as pd

from app.config import DB_PATH, ensure_directories
from app.schema import SCHEMA_SQL


MIGRATIONS = {
    "daily_theme_stats": {
        "theme_stage": "ALTER TABLE daily_theme_stats ADD COLUMN theme_stage TEXT",
    },
    "daily_leader_stats": {
        "role_type": "ALTER TABLE daily_leader_stats ADD COLUMN role_type TEXT",
    },
}


def connect_db(db_path: Path = DB_PATH) -> sqlite3.Connection:
    ensure_directories()
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: Path = DB_PATH) -> Path:
    conn = connect_db(db_path)
    try:
        conn.executescript(SCHEMA_SQL)
        _run_migrations(conn)
        conn.commit()
    finally:
        conn.close()
    return db_path


def replace_table(conn: sqlite3.Connection, table_name: str, df: pd.DataFrame):
    if df is None or df.empty:
        return
    trade_date = None
    if "trade_date" in df.columns:
        trade_date = df["trade_date"].iloc[0]
    if trade_date is not None:
        conn.execute(f"DELETE FROM {table_name} WHERE trade_date = ?", (trade_date,))
    df.to_sql(table_name, conn, if_exists="append", index=False)


def replace_by_keys(
    conn: sqlite3.Connection,
    table_name: str,
    df: pd.DataFrame,
    where_columns: Iterable[str],
):
    if df is None or df.empty:
        return
    where_columns = list(where_columns)
    placeholders = " AND ".join([f"{col} = ?" for col in where_columns])
    seen = set()
    for _, row in df.iterrows():
        key = tuple(row[col] for col in where_columns)
        if key in seen:
            continue
        seen.add(key)
        conn.execute(f"DELETE FROM {table_name} WHERE {placeholders}", key)
    df.to_sql(table_name, conn, if_exists="append", index=False)


def _run_migrations(conn: sqlite3.Connection):
    for table_name, migrations in MIGRATIONS.items():
        existing = _get_columns(conn, table_name)
        for column_name, sql in migrations.items():
            if column_name not in existing:
                conn.execute(sql)


def _get_columns(conn: sqlite3.Connection, table_name: str) -> set[str]:
    rows = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
    return {row["name"] for row in rows}
