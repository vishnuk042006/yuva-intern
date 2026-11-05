import io
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import pytest
from expense_tracker import api
from expense_tracker.config import Config


@pytest.fixture(autouse=True)
def setup(tmp_path, monkeypatch):
    monkeypatch.setattr(Config, "DB_PATH", str(tmp_path / "t.db"))
    monkeypatch.setattr(Config, "API_KEY", "")


def call(method, path, body=None, query="", headers=None):
    raw = json.dumps(body).encode() if body is not None else b""
    env = {"REQUEST_METHOD": method, "PATH_INFO": path, "QUERY_STRING": query,
           "CONTENT_LENGTH": str(len(raw)), "wsgi.input": io.BytesIO(raw)}
    env.update(headers or {})
    out = {}
    def sr(status, hdrs):
        out["status"] = status
    data = b"".join(api.app(env, sr))
    return out["status"], json.loads(data)


def test_health():
    status, body = call("GET", "/health")
    assert status.startswith("200") and body["status"] == "ok"


def test_create_and_list():
    status, body = call("POST", "/expenses", {"amount": 99, "category": "food", "date": "2026-10-01"})
    assert status.startswith("201")
    status, rows = call("GET", "/expenses")
    assert len(rows) == 1 and rows[0]["amount"] == 99


def test_validation_error_is_400():
    status, body = call("POST", "/expenses", {"amount": -1, "category": "food"})
    assert status.startswith("400") and "greater than zero" in body["error"]


def test_bad_json_is_400():
    env = {"REQUEST_METHOD": "POST", "PATH_INFO": "/expenses", "QUERY_STRING": "",
           "CONTENT_LENGTH": "3", "wsgi.input": io.BytesIO(b"{{{")}
    out = {}
    api.app(env, lambda s, h: out.update(status=s))
    assert out["status"].startswith("400")


def test_api_key_enforced(monkeypatch):
    monkeypatch.setattr(Config, "API_KEY", "secret")
    status, _ = call("POST", "/expenses", {"amount": 5, "category": "x"})
    assert status.startswith("401")
    status, _ = call("POST", "/expenses", {"amount": 5, "category": "x"},
                     headers={"HTTP_X_API_KEY": "secret"})
    assert status.startswith("201")


def test_unknown_path_404_and_metrics():
    status, _ = call("GET", "/nope")
    assert status.startswith("404")
    status, m = call("GET", "/metrics")
    assert m["requests"] >= 1


def test_summary():
    call("POST", "/expenses", {"amount": 10, "category": "food"})
    call("POST", "/expenses", {"amount": 5, "category": "food"})
    _, rows = call("GET", "/summary")
    assert rows[0]["total"] == 15
