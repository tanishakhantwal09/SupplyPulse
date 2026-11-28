"""Every API endpoint must return STRICT JSON (no NaN / Infinity), as a browser requires.

Regression for the 27 Nov 2026 bug: /api/events returned "decision_alternate_route": NaN,
the browser could not parse it, and the dashboard showed "API server offline".
"""
import json
import threading
import urllib.error
import urllib.request

import numpy as np
import pandas as pd
import pytest

import server
from tests.sample_events import SHANGHAI_CRITICAL, UNKNOWN_PORT


def strict_loads(text):
    """json.loads that fails on NaN, Infinity and -Infinity, like JSON.parse in a browser."""
    def reject(constant):
        raise ValueError(f"non-standard JSON constant: {constant}")
    return json.loads(text, parse_constant=reject)


@pytest.fixture
def base_url():
    httpd = server.socketserver.TCPServer(("127.0.0.1", 0), server.SupplyPulseAPIHandler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{httpd.server_address[1]}"
    httpd.shutdown()
    httpd.server_close()


def call(url, payload=None, raw=None):
    data = raw if raw is not None else (json.dumps(payload).encode() if payload is not None else None)
    req = urllib.request.Request(url, data=data, method="POST" if data is not None else "GET",
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.status, strict_loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        return e.code, strict_loads(e.read().decode())


BAD_ROW = {"event_id": np.int64(7), "decision_alternate_route": float("nan"), "x_inf": float("inf"),
           "x_neg_inf": -np.inf, "x_np_nan": np.float64("nan"), "x_na": pd.NA, "x_nat": pd.NaT,
           "event_date": pd.Timestamp("2026-03-01"), "nested": {"a": [1.0, float("nan")]}}


def test_to_strict_json_cleans_every_non_finite_value():
    clean = server.to_strict_json(BAD_ROW)
    assert clean["decision_alternate_route"] is None and clean["x_inf"] is None
    assert clean["x_neg_inf"] is None and clean["x_np_nan"] is None
    assert clean["x_na"] is None and clean["x_nat"] is None
    assert clean["event_id"] == 7 and clean["nested"] == {"a": [1.0, None]}
    strict_loads(server.strict_dumps(BAD_ROW))


def test_strict_dumps_never_emits_nan():
    assert "NaN" not in server.strict_dumps([float("nan")])
    with pytest.raises(ValueError):
        json.dumps([float("nan")], allow_nan=False)  # what strict_dumps relies on


@pytest.mark.parametrize("path", ["/api/status", "/api/ports", "/api/routes", "/api/commodities",
                                  "/api/events", "/api/evaluation"])
def test_every_get_endpoint_returns_strict_json(base_url, path):
    code, body = call(base_url + path)
    assert code == 200 and body is not None


def test_unknown_endpoints_return_strict_json_errors(base_url):
    assert call(base_url + "/api/nope")[0] == 404
    assert call(base_url + "/api/nope", payload={})[0] == 404


def test_events_with_nan_become_null(base_url, monkeypatch):
    monkeypatch.setattr(server, "load_dev_events", lambda n=30: [BAD_ROW, BAD_ROW])
    code, body = call(base_url + "/api/events")
    assert code == 200 and body["total"] == 2
    assert body["events"][0]["decision_alternate_route"] is None


def test_real_development_events_are_strict_json(base_url):
    if not server.DEV_SET.exists():
        pytest.skip("development Parquet file not present")
    code, body = call(base_url + "/api/events")
    assert code == 200 and body["total"] == server.EVENTS_SHOWN
    raw = pd.DataFrame(server.load_dev_events())
    if raw["decision_alternate_route"].isna().any():  # the original bug: these were NaN
        assert any(e["decision_alternate_route"] is None for e in body["events"])


def test_run_pipeline_endpoint_success_and_errors_are_strict_json(base_url):
    code, body = call(base_url + "/api/run-pipeline", {"event": SHANGHAI_CRITICAL})
    assert code == 200 and body["success"] is True
    code, body = call(base_url + "/api/run-pipeline", {"event": UNKNOWN_PORT})
    assert code == 500 and body["success"] is False
    assert call(base_url + "/api/run-pipeline", {})[0] == 400
    assert call(base_url + "/api/run-pipeline", raw=b"{not json")[0] == 400


def test_run_pipeline_accepts_an_event_with_nan_fields(base_url):
    # A dashboard event can carry null where the dataset had NaN.
    event = {**SHANGHAI_CRITICAL, "decision_alternate_route": None}
    code, body = call(base_url + "/api/run-pipeline", {"event": event})
    assert code == 200 and body["success"] is True


def test_fetch_live_endpoint_is_strict_json(base_url, monkeypatch):
    import experiments.live_demo as live
    monkeypatch.setattr(live, "fetch_live_gdelt_event",
                        lambda **kw: ({**BAD_ROW, "data_source": "GDELT_LIVE_API"}, "20261128000000"))
    code, body = call(base_url + "/api/fetch-live", {})
    assert code == 200 and body["live"] is True and body["event"]["x_inf"] is None
