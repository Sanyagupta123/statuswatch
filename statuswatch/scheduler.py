"""Background scheduler with one non-overlapping job per enabled monitor."""
from apscheduler.schedulers.background import BackgroundScheduler
from flask import current_app

from .database import get_monitors


def schedule_monitor(scheduler, monitor):
    job_id = f"monitor-{monitor['id']}"
    if scheduler.get_job(job_id):
        scheduler.remove_job(job_id)
    scheduler.add_job(_scheduled_check, "interval", seconds=monitor["interval_seconds"],
                      args=[monitor["id"]], id=job_id, replace_existing=True,
                      max_instances=1, coalesce=True, misfire_grace_time=15)


def _scheduled_check(monitor_id):
    # Each monitor gets its own app context and errors are isolated by the job boundary.
    app = _app_ref
    if app is None:
        return
    with app.app_context():
        from . import _perform_check
        from .database import get_monitor
        try:
            monitor = get_monitor(monitor_id)
            if monitor and monitor["enabled"]:
                _perform_check(monitor)
        except Exception:
            app.logger.exception("Scheduled check failed for monitor %s", monitor_id)


_app_ref = None


def start_scheduler(app):
    """Start once and schedule all existing enabled monitors."""
    global _app_ref
    existing = app.extensions.get("statuswatch_scheduler")
    if existing and existing.running:
        return existing
    scheduler = BackgroundScheduler(daemon=True)
    _app_ref = app
    with app.app_context():
        for monitor in get_monitors():
            if monitor["enabled"]:
                schedule_monitor(scheduler, monitor)
    scheduler.start()
    app.extensions["statuswatch_scheduler"] = scheduler
    return scheduler
