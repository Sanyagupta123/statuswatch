from unittest.mock import patch


def test_health_and_empty_monitors(client):
    assert client.get("/api/health").status_code == 200
    dashboard = client.get("/")
    assert dashboard.status_code == 200
    assert b"StatusWatch" in dashboard.data
    payload=client.get("/api/monitors").get_json()
    assert payload["summary"]["total"]==0


def test_create_monitor_and_validation(client):
    response=client.post("/api/monitors",json={"name":"API","url":"https://example.com/health","interval_seconds":30})
    assert response.status_code==201
    assert response.get_json()["monitor"]["interval_seconds"]==30
    assert client.post("/api/monitors",json={"name":"","url":"https://example.com"}).status_code==400
    assert client.post("/api/monitors",json={"name":"API","url":"https://example.com","interval_seconds":2}).status_code==400


def test_check_history_analytics_incidents_and_unknown_ids(client):
    assert client.post("/api/monitors/999/check").status_code==404
    assert client.get("/api/monitors/999/checks").status_code==404
    assert client.get("/api/monitors/999/analytics").status_code==404
    assert client.get("/api/monitors/999/incidents").status_code==404
    monitor=client.post("/api/monitors",json={"name":"API","url":"https://example.com"}).get_json()["monitor"]
    with patch("statuswatch.monitor.requests.Session") as session_cls:
        response=session_cls.return_value.__enter__.return_value.get.return_value.__enter__.return_value
        response.status_code=200
        result=client.post(f"/api/monitors/{monitor['id']}/check")
    assert result.status_code==200 and result.get_json()["check"]["success"]
    assert len(client.get(f"/api/monitors/{monitor['id']}/checks").get_json()["checks"])==1
    assert client.get(f"/api/monitors/{monitor['id']}/analytics").status_code==200
    assert client.get(f"/api/monitors/{monitor['id']}/incidents").status_code==200
