from unittest.mock import MagicMock, patch

import requests

from statuswatch.monitor import check_url


@patch("statuswatch.monitor.validate_destination")
@patch("statuswatch.monitor.requests.Session")
def test_successful_http_response(mock_session_cls, _validate):
    response = MagicMock(status_code=204)
    mock_session_cls.return_value.__enter__.return_value.get.return_value.__enter__.return_value = response
    result = check_url("https://example.com")
    assert result["success"] is True
    assert result["status_code"] == 204
    mock_session_cls.return_value.__enter__.return_value.get.assert_called_once_with(
        "https://example.com", timeout=8, allow_redirects=False, stream=True)


@patch("statuswatch.monitor.validate_destination")
@patch("statuswatch.monitor.requests.Session")
def test_http_error_is_recorded_as_failure(mock_session_cls, _validate):
    mock_session_cls.return_value.__enter__.return_value.get.return_value.__enter__.return_value = MagicMock(status_code=503)
    result = check_url("https://example.com")
    assert result["success"] is False
    assert result["error"] == "HTTP 503"


@patch("statuswatch.monitor.validate_destination")
@patch("statuswatch.monitor.requests.Session")
def test_timeout_and_network_errors_are_recorded(mock_session_cls, _validate):
    mock_session_cls.return_value.__enter__.return_value.get.side_effect = requests.Timeout("slow")
    result = check_url("https://example.com")
    assert not result["success"] and "Timeout" in result["error"]
    mock_session_cls.return_value.__enter__.return_value.get.side_effect = requests.ConnectionError("offline")
    result = check_url("https://example.com")
    assert not result["success"] and "ConnectionError" in result["error"]


def test_private_and_local_destinations_are_rejected():
    from statuswatch.monitor import validate_destination
    import pytest
    for url in ("http://127.0.0.1", "http://10.0.0.4", "http://localhost", "file:///etc/passwd"):
        with pytest.raises(ValueError):
            validate_destination(url)
