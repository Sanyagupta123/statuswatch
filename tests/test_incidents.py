from statuswatch.database import create_monitor, get_incidents, record_check
from statuswatch.incidents import apply_incident_transition


def test_incident_opens_once_after_two_failures_and_recovers(app):
    with app.app_context():
        monitor = create_monitor("API", "https://example.com")
        record_check(monitor["id"], 503, 10, "HTTP 503")
        assert apply_incident_transition(monitor["id"], False, "HTTP 503") is None
        record_check(monitor["id"], 503, 12, "HTTP 503")
        assert apply_incident_transition(monitor["id"], False, "HTTP 503") == "opened"
        record_check(monitor["id"], 503, 12, "HTTP 503")
        assert apply_incident_transition(monitor["id"], False, "HTTP 503") is None
        assert len(get_incidents(monitor["id"])) == 1
        record_check(monitor["id"], 200, 9, None)
        assert apply_incident_transition(monitor["id"], True, "ok") is None
        record_check(monitor["id"], 200, 8, None)
        assert apply_incident_transition(monitor["id"], True, "ok") == "resolved"
        incident = get_incidents(monitor["id"])[0]
        assert incident["started_at"] and incident["resolved_at"]
