"""SQLite storage for bed snapshots (standard library only)."""
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path

from . import config

COLUMNS = ["facility_id", "ward", "timestamp", "capacity", "occupied", "admissions", "discharges"]

SCHEMA = """
CREATE TABLE IF NOT EXISTS snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    facility_id TEXT NOT NULL,
    ward TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    capacity INTEGER NOT NULL,
    occupied INTEGER NOT NULL,
    admissions INTEGER NOT NULL DEFAULT 0,
    discharges INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_snapshots_facility_time ON snapshots (facility_id, ward, timestamp);
CREATE INDEX IF NOT EXISTS idx_snapshots_time ON snapshots (timestamp);
"""


def db_path() -> Path:
    return config.DB_PATH


@contextmanager
def connect():
    path = db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    with connect() as conn:
        conn.executescript(SCHEMA)


def to_iso(ts: datetime) -> str:
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    return ts.astimezone(timezone.utc).isoformat(timespec="seconds")


def insert_snapshots(rows: list[dict]) -> int:
    data = [tuple(to_iso(r[c]) if c == "timestamp" else r[c] for c in COLUMNS) for r in rows]
    with connect() as conn:
        conn.executemany(
            f"INSERT INTO snapshots ({', '.join(COLUMNS)}) VALUES ({', '.join('?' * len(COLUMNS))})",
            data)
    return len(data)


def count() -> int:
    with connect() as conn:
        return conn.execute("SELECT COUNT(*) FROM snapshots").fetchone()[0]


def latest() -> dict[str, dict[str, dict]]:
    """The newest snapshot of every ward, as {facility_id: {ward: row}}."""
    sql = """
        SELECT s.* FROM snapshots s
        JOIN (SELECT facility_id, ward, MAX(timestamp) AS ts FROM snapshots GROUP BY facility_id, ward) m
          ON s.facility_id = m.facility_id AND s.ward = m.ward AND s.timestamp = m.ts
        ORDER BY s.id
    """
    out: dict[str, dict[str, dict]] = {}
    with connect() as conn:
        for row in conn.execute(sql):
            out.setdefault(row["facility_id"], {})[row["ward"]] = dict(row)
    return out


def history(facility_id: str | None = None, hours: int = 72) -> list[dict]:
    since = to_iso(datetime.now(timezone.utc) - timedelta(hours=hours))
    sql = "SELECT * FROM snapshots WHERE timestamp >= ?"
    args: list = [since]
    if facility_id:
        sql += " AND facility_id = ?"
        args.append(facility_id)
    with connect() as conn:
        return [dict(r) for r in conn.execute(sql + " ORDER BY timestamp, id", args)]
