"""Sample-based monitor statistics; these do not estimate wall-clock availability."""
from .database import get_recent_checks


def get_analytics(monitor_id, history_limit=100, sample_limit=1000):
    from flask import g
    rows = g.db.execute("SELECT success,latency_ms FROM checks WHERE monitor_id=? ORDER BY checked_at DESC,id DESC LIMIT ?",
                        (monitor_id, sample_limit)).fetchall()
    total = len(rows)
    successful = sum(row["success"] for row in rows)
    latencies = [row["latency_ms"] for row in rows if row["success"] and row["latency_ms"] is not None]
    return {
        "sample_count": total,
        "successful_checks": successful,
        "failed_checks": total - successful,
        "sampled_success_rate_percent": round(successful / total * 100, 2) if total else None,
        "latency_ms": {"average": round(sum(latencies)/len(latencies), 2) if latencies else None,
                       "minimum": min(latencies) if latencies else None,
                       "maximum": max(latencies) if latencies else None},
        "recent_checks": get_recent_checks(monitor_id, history_limit),
        "availability_note": "Sampled check success rate; this is not wall-clock availability.",
    }
