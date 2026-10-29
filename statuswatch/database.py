"""SQLite persistence. Timestamps are ISO 8601 UTC strings."""
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from flask import current_app, g


def utc_now():
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def get_db():
    if "db" not in g:
        path = current_app.config["DATABASE"]
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        g.db = sqlite3.connect(path, detect_types=sqlite3.PARSE_DECLTYPES)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


def close_db(_error=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    get_db().executescript("""
        CREATE TABLE IF NOT EXISTS monitors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            url TEXT NOT NULL,
            interval_seconds INTEGER NOT NULL DEFAULT 60,
            enabled INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS checks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            monitor_id INTEGER NOT NULL REFERENCES monitors(id) ON DELETE CASCADE,
            checked_at TEXT NOT NULL,
            status_code INTEGER,
            latency_ms REAL,
            error TEXT,
            success INTEGER NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_checks_monitor_time ON checks(monitor_id, checked_at DESC);
        CREATE TABLE IF NOT EXISTS incidents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            monitor_id INTEGER NOT NULL REFERENCES monitors(id) ON DELETE CASCADE,
            started_at TEXT NOT NULL,
            resolved_at TEXT,
            reason TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_incidents_monitor_time ON incidents(monitor_id, started_at DESC);
    """)
    get_db().commit()


def _dict(row):
    return dict(row) if row is not None else None


def create_monitor(name, url, interval_seconds=60):
    db = get_db()
    cursor = db.execute("INSERT INTO monitors(name,url,interval_seconds,created_at) VALUES(?,?,?,?)",
                        (name, url, interval_seconds, utc_now()))
    db.commit()
    return get_monitor(cursor.lastrowid)


def get_monitor(monitor_id):
    return _dict(get_db().execute("""SELECT m.*, (SELECT success FROM checks c WHERE c.monitor_id=m.id
        ORDER BY checked_at DESC,id DESC LIMIT 1) AS latest_success,
        (SELECT latency_ms FROM checks c WHERE c.monitor_id=m.id ORDER BY checked_at DESC,id DESC LIMIT 1) AS latest_latency_ms,
        (SELECT checked_at FROM checks c WHERE c.monitor_id=m.id ORDER BY checked_at DESC,id DESC LIMIT 1) AS last_checked_at,
        EXISTS(SELECT 1 FROM incidents i WHERE i.monitor_id=m.id AND i.resolved_at IS NULL) AS open_incident
        FROM monitors m WHERE m.id=?""", (monitor_id,)).fetchone())


def get_monitors():
    rows = get_db().execute("""SELECT m.*, (SELECT success FROM checks c WHERE c.monitor_id=m.id
        ORDER BY checked_at DESC,id DESC LIMIT 1) AS latest_success,
        (SELECT latency_ms FROM checks c WHERE c.monitor_id=m.id ORDER BY checked_at DESC,id DESC LIMIT 1) AS latest_latency_ms,
        (SELECT checked_at FROM checks c WHERE c.monitor_id=m.id ORDER BY checked_at DESC,id DESC LIMIT 1) AS last_checked_at,
        EXISTS(SELECT 1 FROM incidents i WHERE i.monitor_id=m.id AND i.resolved_at IS NULL) AS open_incident
        FROM monitors m ORDER BY m.id DESC""").fetchall()
    return [_dict(row) for row in rows]


def record_check(monitor_id, status_code, latency_ms, error):
    success = int(error is None and status_code is not None and 200 <= status_code < 400)
    checked_at = utc_now()
    db = get_db()
    cursor = db.execute("INSERT INTO checks(monitor_id,checked_at,status_code,latency_ms,error,success) VALUES(?,?,?,?,?,?)",
                        (monitor_id, checked_at, status_code, latency_ms, error, success))
    db.commit()
    return _dict(db.execute("SELECT * FROM checks WHERE id=?", (cursor.lastrowid,)).fetchone())


def get_recent_checks(monitor_id, limit=100):
    rows = get_db().execute("SELECT * FROM checks WHERE monitor_id=? ORDER BY checked_at DESC,id DESC LIMIT ?",
                            (monitor_id, limit)).fetchall()
    return [_dict(row) for row in rows]


def recent_successes(monitor_id, limit):
    rows = get_db().execute("SELECT success FROM checks WHERE monitor_id=? ORDER BY checked_at DESC,id DESC LIMIT ?",
                            (monitor_id, limit)).fetchall()
    return [row["success"] for row in rows]


def get_incidents(monitor_id, limit=100):
    rows = get_db().execute("SELECT * FROM incidents WHERE monitor_id=? ORDER BY started_at DESC,id DESC LIMIT ?",
                            (monitor_id, limit)).fetchall()
    return [_dict(row) for row in rows]


def open_incident(monitor_id, reason):
    db = get_db()
    cursor = db.execute("INSERT INTO incidents(monitor_id,started_at,reason) VALUES(?,?,?)",
                        (monitor_id, utc_now(), reason[:500]))
    db.commit()
    return cursor.lastrowid


def resolve_open_incident(monitor_id):
    db = get_db()
    db.execute("UPDATE incidents SET resolved_at=? WHERE monitor_id=? AND resolved_at IS NULL",
               (utc_now(), monitor_id))
    db.commit()


def has_open_incident(monitor_id):
    return get_db().execute("SELECT 1 FROM incidents WHERE monitor_id=? AND resolved_at IS NULL LIMIT 1",
                            (monitor_id,)).fetchone() is not None
