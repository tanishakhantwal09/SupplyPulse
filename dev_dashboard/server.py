"""SupplyPulse development API server (plain http.server, port 5001).

Honesty rules (BUILD_PLAN 4a, Stage 1):
- A failed run returns success: false and the error. It never returns an invented result.
- /api/fetch-live returns only a real GDELT event, or live: false with "no live data".
- Events shown in the dashboard come from the DEVELOPMENT set, never the held-out set.
The FastAPI backend replaces this server in Stage 4.
"""
import http.server
import json
import os
import socketserver
import sys
import time
import traceback
import urllib.parse

import pandas as pd

PARENT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, PARENT_DIR)

from agents import llm_utils  # noqa: E402
from agents.reference_data import DATA_DIR, REFERENCE_DIR  # noqa: E402

PORT = 5001
DEV_SET = DATA_DIR / "training_set.parquet"  # development set (BUILD_PLAN section 2)
EVENTS_SHOWN = 30
LIVE_HOURS_BACK = 2  # ASSUMPTION: scan the last 2 hours (8 GDELT files) so a request stays short.
RESULTS_DIR = os.path.join(PARENT_DIR, "experiments", "results")


def load_dev_events(n=EVENTS_SHOWN):
    if not DEV_SET.exists():
        return []
    return pd.read_parquet(DEV_SET).head(n).to_dict(orient="records")


def run_pipeline(event):
    """Run the real pipeline. Returns (http_code, body). Never invents a result."""
    from agents.langgraph_orchestrator import run_supplypulse

    try:
        result = run_supplypulse(event)
    except Exception as e:  # noqa: BLE001 - every failure is reported as a failure
        return 500, {"success": False, "error": f"{type(e).__name__}: {e}",
                     "traceback": traceback.format_exc(), "event": event}
    return 200, {"success": True, "result": result, "event": event}


def fetch_live():
    """Return a real live GDELT event, or live: false. Never invents a signal."""
    try:
        from experiments.live_demo import fetch_live_gdelt_event

        event, ts = fetch_live_gdelt_event(hours_back=LIVE_HOURS_BACK, require_proceed=False)
    except Exception as e:  # noqa: BLE001
        return {"success": False, "live": False, "message": "no live data",
                "error": f"{type(e).__name__}: {e}"}
    if event is None:
        return {"success": True, "live": False, "message": "no live data",
                "hours_scanned": LIVE_HOURS_BACK}
    return {"success": True, "live": True, "source": "GDELT 2.0 export files",
            "gdelt_file_timestamp": ts, "event": event}


def read_result(name):
    path = os.path.join(RESULTS_DIR, name)
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


class SupplyPulseAPIHandler(http.server.BaseHTTPRequestHandler):
    def _send_cors_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def do_OPTIONS(self):
        self.send_response(200)
        self._send_cors_headers()
        self.end_headers()

    def _respond_json(self, data, code=200):
        self.send_response(code)
        self._send_cors_headers()
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(data, default=str).encode("utf-8"))

    def _reference(self, name):
        with open(REFERENCE_DIR / name, encoding="utf-8") as f:
            return json.load(f)

    def do_GET(self):
        path = urllib.parse.urlparse(self.path).path
        try:
            if path == "/api/status":
                self._respond_json({
                    "status": "online",
                    "system": "SupplyPulse development API",
                    "llm_provider": "Groq",
                    "llm_model": llm_utils.MODEL_NAME,
                    "llm_enabled": not llm_utils.no_llm(),
                    "agents_count": 4,
                    "timestamp": time.time(),
                })
            elif path == "/api/ports":
                self._respond_json(self._reference("ports.json"))
            elif path == "/api/routes":
                self._respond_json(self._reference("routes.json"))
            elif path == "/api/commodities":
                self._respond_json(self._reference("commodities.json"))
            elif path == "/api/events":
                events = load_dev_events()
                self._respond_json({"total": len(events), "source": "development set", "events": events})
            elif path == "/api/evaluation":
                self._respond_json({
                    "supplypulse": read_result("formal_evaluation.json"),
                    "brintrup_baseline": read_result("brintrup_baseline.json"),
                    "retired_note": ("These results are RETIRED: labels are circular and the cost per "
                                     "analysis is an ASSUMPTION. See docs/RETIRED.md."),
                })
            else:
                self._respond_json({"success": False, "error": "Endpoint not found"}, 404)
        except Exception as e:  # noqa: BLE001
            self._respond_json({"success": False, "error": str(e), "traceback": traceback.format_exc()}, 500)

    def do_POST(self):
        path = urllib.parse.urlparse(self.path).path
        try:
            length = int(self.headers.get("Content-Length", 0))
            raw = self.rfile.read(length) if length else b""
            body = json.loads(raw.decode("utf-8")) if raw else {}
        except (ValueError, UnicodeDecodeError) as e:
            self._respond_json({"success": False, "error": f"Bad JSON body: {e}"}, 400)
            return
        try:
            if path == "/api/run-pipeline":
                event = body.get("event")
                if not event:
                    self._respond_json({"success": False, "error": "No event given. Send {\"event\": {...}}."}, 400)
                    return
                code, payload = run_pipeline(event)
                self._respond_json(payload, code)
            elif path == "/api/fetch-live":
                self._respond_json(fetch_live())
            else:
                self._respond_json({"success": False, "error": "Endpoint not found"}, 404)
        except Exception as e:  # noqa: BLE001
            self._respond_json({"success": False, "error": str(e), "traceback": traceback.format_exc()}, 500)


def run_server():
    with socketserver.TCPServer(("", PORT), SupplyPulseAPIHandler) as httpd:
        print(f"SupplyPulse development API at http://localhost:{PORT}")
        httpd.serve_forever()


if __name__ == "__main__":
    run_server()
