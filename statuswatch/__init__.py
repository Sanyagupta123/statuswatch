"""StatusWatch application factory and REST API."""
from pathlib import Path

from flask import Flask, jsonify, render_template, request

from .analytics import get_analytics
from .database import (close_db, create_monitor, get_db, get_incidents,
                       get_monitor, get_monitors, get_recent_checks,
                       init_db, record_check)
from .incidents import apply_incident_transition
from .monitor import check_url


def create_app(test_config=None):
    project_root = Path(__file__).resolve().parent.parent
    app = Flask(
        __name__,
        instance_relative_config=True,
        template_folder=str(project_root / "templates"),
        static_folder=str(project_root / "static"),
    )
    Path(app.instance_path).mkdir(parents=True, exist_ok=True)
    app.config.from_mapping(
        DATABASE=str(Path(app.instance_path) / "statuswatch.sqlite3"),
        CHECK_TIMEOUT=8,
        FAILURE_THRESHOLD=2,
        RECOVERY_THRESHOLD=2,
        TESTING=False,
    )
    if test_config:
        app.config.update(test_config)
    app.teardown_appcontext(close_db)

    with app.app_context():
        init_db()

    @app.get("/")
    def dashboard():
        return render_template("index.html")

    @app.get("/api/health")
    def health():
        return jsonify(status="ok", service="StatusWatch")

    @app.get("/api/monitors")
    def list_monitors():
        monitors = get_monitors()
        return jsonify(monitors=monitors, summary=_summary(monitors))

    @app.post("/api/monitors")
    def add_monitor():
        data = request.get_json(silent=True)
        if not isinstance(data, dict):
            return _error("Request body must be a JSON object.", 400)
        name = data.get("name")
        url = data.get("url")
        interval = data.get("interval_seconds", 60)
        if not isinstance(name, str) or not name.strip() or len(name.strip()) > 80:
            return _error("Name is required and must be 1–80 characters.", 400)
        if not isinstance(url, str):
            return _error("A valid HTTP or HTTPS URL is required.", 400)
        if isinstance(interval, bool) or not isinstance(interval, int) or not 15 <= interval <= 86400:
            return _error("interval_seconds must be an integer from 15 to 86400.", 400)
        try:
            check_url(url, timeout=app.config["CHECK_TIMEOUT"], dry_run=True)
        except ValueError as exc:
            return _error(str(exc), 400)
        monitor = create_monitor(name.strip(), url.strip(), interval)
        scheduler = app.extensions.get("statuswatch_scheduler")
        if scheduler:
            from .scheduler import schedule_monitor
            schedule_monitor(scheduler, monitor)
        return jsonify(monitor=monitor), 201

    @app.post("/api/monitors/<int:monitor_id>/check")
    def run_check(monitor_id):
        monitor = get_monitor(monitor_id)
        if not monitor:
            return _error("Monitor not found.", 404)
        result = _perform_check(monitor)
        return jsonify(check=result), 200

    @app.get("/api/monitors/<int:monitor_id>/checks")
    def check_history(monitor_id):
        if not get_monitor(monitor_id):
            return _error("Monitor not found.", 404)
        return jsonify(checks=get_recent_checks(monitor_id, limit=100))

    @app.get("/api/monitors/<int:monitor_id>/analytics")
    def monitor_analytics(monitor_id):
        if not get_monitor(monitor_id):
            return _error("Monitor not found.", 404)
        return jsonify(analytics=get_analytics(monitor_id))

    @app.get("/api/monitors/<int:monitor_id>/incidents")
    def monitor_incidents(monitor_id):
        if not get_monitor(monitor_id):
            return _error("Monitor not found.", 404)
        return jsonify(incidents=get_incidents(monitor_id, limit=100))

    return app


def _perform_check(monitor):
    from flask import current_app
    outcome = check_url(monitor["url"], timeout=current_app.config["CHECK_TIMEOUT"])
    record = record_check(monitor["id"], outcome["status_code"],
                          outcome["latency_ms"], outcome["error"])
    apply_incident_transition(
        monitor["id"], outcome["success"], outcome["error"] or
        (f"HTTP {outcome['status_code']}" if outcome["status_code"] else "Check failed"),
        current_app.config["FAILURE_THRESHOLD"], current_app.config["RECOVERY_THRESHOLD"])
    record["success"] = outcome["success"]
    return record


def _summary(monitors):
    # A monitor's latest sampled result determines its current display state.
    online = sum(1 for item in monitors if item["latest_success"] == 1)
    down = sum(1 for item in monitors if item["latest_success"] == 0)
    open_incidents = sum(item["open_incident"] for item in monitors)
    return {"total": len(monitors), "online": online, "down": down,
            "open_incidents": open_incidents}


def _error(message, status):
    return jsonify(error={"message": message}), status
