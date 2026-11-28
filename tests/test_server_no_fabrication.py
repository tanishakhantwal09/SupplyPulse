"""The dev server must never invent a result or a live signal."""
import json
import threading
import urllib.error
import urllib.request

import pytest

import server
from tests.sample_events import SHANGHAI_CRITICAL, UNKNOWN_PORT


def test_failed_run_returns_error_not_ningbo():
    code, body = server.run_pipeline(UNKNOWN_PORT)
    assert code == 500
    assert body["success"] is False
    assert "UnknownPortError" in body["error"]
    text = json.dumps(body)
    assert "Ningbo" not in text and "91%" not in text and "result" not in body


def test_good_run_returns_the_real_result():
    code, body = server.run_pipeline(SHANGHAI_CRITICAL)
    assert code == 200 and body["success"] is True
    assert body["result"]["recommended_alternate_port"] == "Port of Shenzhen"   # capped plan: most ships


def test_no_live_event_means_no_live_data(monkeypatch):
    import experiments.live_demo as live
    monkeypatch.setattr(live, "fetch_live_gdelt_event", lambda **kw: (None, None))
    r = server.fetch_live()
    assert r["live"] is False and r["message"] == "no live data"
    assert "event" not in r


def test_live_fetch_error_means_no_live_data(monkeypatch):
    import experiments.live_demo as live

    def boom(**kw):
        raise ConnectionError("GDELT down")
    monkeypatch.setattr(live, "fetch_live_gdelt_event", boom)
    r = server.fetch_live()
    assert r["live"] is False and r["success"] is False and "event" not in r


@pytest.fixture
def running_server():
    httpd = server.socketserver.TCPServer(("127.0.0.1", 0), server.SupplyPulseAPIHandler)
    t = threading.Thread(target=httpd.serve_forever, daemon=True)
    t.start()
    yield f"http://127.0.0.1:{httpd.server_address[1]}"
    httpd.shutdown()
    httpd.server_close()


def _post(url, payload):
    req = urllib.request.Request(url, data=json.dumps(payload).encode(), method="POST",
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())


def test_http_missing_event_is_400(running_server):
    code, body = _post(f"{running_server}/api/run-pipeline", {})
    assert code == 400 and body["success"] is False


def test_http_status_reports_real_model(running_server):
    with urllib.request.urlopen(f"{running_server}/api/status") as resp:
        body = json.loads(resp.read())
    assert body["llm_model"] == "openai/gpt-oss-20b"
    assert "120b" not in json.dumps(body).lower()  # not the old "gpt-oss-120b" claim (timestamps may contain 120)


def test_retired_results_are_labelled(running_server):
    with urllib.request.urlopen(f"{running_server}/api/evaluation") as resp:
        body = json.loads(resp.read())
    assert "RETIRED" in body["retired_note"]
    assert "RETIRED" in body["supplypulse"]["_status"]["status"]
