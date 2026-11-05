"""WSGI web API. Endpoints: GET /health, GET /metrics, GET/POST /expenses, GET /summary."""
import hmac
import json
import time
from urllib.parse import parse_qs

from . import database, service
from .config import Config
from .logging_config import setup

log = setup(Config.LOG_LEVEL)
START = time.time()
METRICS = {"requests": 0, "errors": 0, "by_status": {}}


def _json(start_response, status, payload):
    body = json.dumps(payload).encode()
    start_response(status, [("Content-Type", "application/json"),
                            ("Content-Length", str(len(body))),
                            ("X-Content-Type-Options", "nosniff")])
    return [body]


def _authorised(environ):
    if not Config.API_KEY:
        return True
    sent = environ.get("HTTP_X_API_KEY", "")
    return hmac.compare_digest(sent, Config.API_KEY)


def app(environ, start_response):
    method, path = environ["REQUEST_METHOD"], environ.get("PATH_INFO", "/")
    began = time.time()
    status = "200 OK"
    try:
        if path == "/health":
            conn = database.connect(Config.DB_PATH)
            conn.execute("SELECT 1")
            conn.close()
            result = _json(start_response, status, {
                "status": "ok", "env": Config.ENV, "version": Config.VERSION,
                "uptime_s": int(time.time() - START)})
        elif path == "/metrics":
            result = _json(start_response, status, METRICS)
        elif path == "/expenses" and method == "GET":
            q = {k: v[0] for k, v in parse_qs(environ.get("QUERY_STRING", "")).items()}
            conn = database.connect(Config.DB_PATH)
            rows = service.list_expenses(conn, q.get("category"), q.get("month"))
            conn.close()
            result = _json(start_response, status, [dict(r) for r in rows])
        elif path == "/expenses" and method == "POST":
            if not _authorised(environ):
                status = "401 Unauthorized"
                result = _json(start_response, status, {"error": "invalid or missing API key"})
            else:
                size = int(environ.get("CONTENT_LENGTH") or 0)
                if size > 10_000:
                    status = "413 Payload Too Large"
                    result = _json(start_response, status, {"error": "payload too large"})
                else:
                    data = json.loads(environ["wsgi.input"].read(size) or b"{}")
                    conn = database.connect(Config.DB_PATH)
                    new_id = service.add_expense(conn, data.get("amount"), data.get("category"),
                                                 data.get("note", ""), data.get("date"))
                    conn.close()
                    status = "201 Created"
                    result = _json(start_response, status, {"id": new_id})
        elif path == "/summary":
            q = {k: v[0] for k, v in parse_qs(environ.get("QUERY_STRING", "")).items()}
            conn = database.connect(Config.DB_PATH)
            rows = service.summary_by_category(conn, q.get("month"))
            conn.close()
            result = _json(start_response, status, [dict(r) for r in rows])
        else:
            status = "404 Not Found"
            result = _json(start_response, status, {"error": "not found"})
    except (service.ValidationError, json.JSONDecodeError) as err:
        status = "400 Bad Request"
        result = _json(start_response, status, {"error": str(err)})
    except Exception:
        log.exception("unhandled error on %s %s", method, path)
        status = "500 Internal Server Error"
        result = _json(start_response, status, {"error": "internal error"})

    code = status[:3]
    METRICS["requests"] += 1
    METRICS["by_status"][code] = METRICS["by_status"].get(code, 0) + 1
    if code.startswith(("4", "5")):
        METRICS["errors"] += 1
    log.info("%s %s %s %.1fms", method, path, code, (time.time() - began) * 1000)
    return result
