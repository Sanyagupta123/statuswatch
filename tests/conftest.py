import pytest

from statuswatch import create_app


@pytest.fixture
def app(tmp_path, monkeypatch):
    monkeypatch.setattr("statuswatch.monitor.validate_destination", lambda url: None)
    return create_app({"TESTING": True, "DATABASE": str(tmp_path / "test.sqlite3")})


@pytest.fixture
def client(app):
    return app.test_client()
