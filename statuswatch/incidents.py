"""Incident state transitions driven by consecutive sampled results."""
from .database import has_open_incident, open_incident, recent_successes, resolve_open_incident


def apply_incident_transition(monitor_id, success, reason, failure_threshold=2, recovery_threshold=2):
    """Open after N consecutive failures; resolve after N consecutive successes."""
    streak = recent_successes(monitor_id, failure_threshold if not success else recovery_threshold)
    if not success and len(streak) >= failure_threshold and all(value == 0 for value in streak):
        if not has_open_incident(monitor_id):
            open_incident(monitor_id, reason)
            return "opened"
    if success and len(streak) >= recovery_threshold and all(value == 1 for value in streak):
        if has_open_incident(monitor_id):
            resolve_open_incident(monitor_id)
            return "resolved"
    return None
