from statuswatch.analytics import get_analytics
from statuswatch.database import create_monitor, record_check


def test_analytics_calculate_sample_rate_and_success_latency(app):
    with app.app_context():
        monitor=create_monitor("API","https://example.com")
        record_check(monitor["id"],200,20,None)
        record_check(monitor["id"],503,99,"HTTP 503")
        record_check(monitor["id"],200,10,None)
        result=get_analytics(monitor["id"])
        assert result["sample_count"]==3
        assert result["sampled_success_rate_percent"]==66.67
        assert result["latency_ms"]=={"average":15.0,"minimum":10.0,"maximum":20.0}


def test_empty_history_has_no_success_rate(app):
    with app.app_context():
        monitor=create_monitor("API","https://example.com")
        result=get_analytics(monitor["id"])
        assert result["sampled_success_rate_percent"] is None
        assert result["latency_ms"]["average"] is None
