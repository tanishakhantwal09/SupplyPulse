"""IMF PortWatch client: live port utilisation with a static fallback.

Source: IMF PortWatch (2023), portwatch.imf.org, Daily_Ports_Data service
(satellite AIS-derived daily port calls).

Utilisation = trailing 7-day average daily port calls / static vessel_capacity
from ports.json (both are vessels-per-day throughput proxies).

Returned source labels:
  'portwatch_live'   fetched from the API in this call
  'portwatch_cache'  a cached API value up to CACHE_MAX_AGE_DAYS old
  'static'           the static current_utilization in ports.json
"""
import json
import os
import time
from datetime import datetime, timedelta

import requests

from agents.reference_data import REFERENCE_DIR, ports

PORTWATCH_BASE_URL = (
    "https://services9.arcgis.com/weJ1QsnbMYJlCHdG/ArcGIS/rest/services/"
    "Daily_Ports_Data/FeatureServer/0/query"
)
CACHE_FILE = REFERENCE_DIR / "portwatch_cache.json"
CACHE_MAX_AGE_DAYS = 7      # ASSUMPTION: PortWatch updates daily; a week-old value is still usable.
TRAILING_DAYS = 7           # ASSUMPTION: 7-day average smooths day-to-day noise.
REQUEST_TIMEOUT_SECONDS = 10  # ASSUMPTION

# Port name (as in ports.json) -> IMF PortWatch portid.
# Verified 2026-09-14 against the live Daily_Ports_Data FeatureServer with a
# `portname LIKE '%term%' AND ISO3='...'` query, hand-checked by name/country.
# The 6 SupplyPulse "ports" not listed are canals/straits/bypass routes; PortWatch
# Daily_Ports_Data tracks cargo ports, not chokepoints, so they use the static value.
PORT_NAME_MAP = {
    "Port of Shanghai":               "port1188",
    "Port of Singapore":              "port1201",
    "Port of Ningbo-Zhoushan":        "port824",
    "Port of Shenzhen":               "port1189",
    "Port of Guangzhou":              "port2401",
    "Port of Busan":                  "port1065",
    "Port of Tokyo-Yokohama":         "port1417",
    "Port of Osaka-Kobe":             "port581",
    "Port of Tanjung Pelepas":        "port1269",
    "Port Klang":                     "port960",
    "Port of Ho Chi Minh":            "port1291",
    "Port of Laem Chabang":           "port1197",
    "Port of Jakarta (Tanjung Priok)": "port514",
    "Port of Mumbai (JNPT)":          "port776",
    "Port of Mundra":                 "port777",
    "Port of Colombo":                "port254",
    "Port of Jebel Ali (Dubai)":      "port744",
    "Port of Salalah":                "port746",
    "Port of Jeddah":                 "port518",
    "Port Said":                      "port192",
    "Port of Rotterdam":              "port1114",
    "Port of Antwerp-Bruges":         "port57",
    "Port of Hamburg":                "port446",
    "Port of Felixstowe":             "port343",
    "Port of Southampton":            "port1216",
    "Port of Barcelona":              "port118",
    "Port of Valencia":               "port1348",
    "Port of Genoa":                  "port387",
    # Verified 2026-11-26: PortWatch has ONE entry, port664 = "Los Angeles-Long Beach",
    # covering both ports. Its port calls are therefore divided by the COMBINED
    # capacity of both ports (see _capacity_for), not by each port's own capacity,
    # which used to count the same traffic twice.
    "Port of Los Angeles":            "port664",
    "Port of Long Beach":             "port664",
    "Port of Seattle-Tacoma":         "port1248",
    "Port of New York-New Jersey":    "port815",
    "Port of Savannah":               "port1170",
    "Port of Houston":                "port481",
    "Port of Vancouver":              "port1350",
    "Port of Santos":                 "port1160",
    "Port of Callao":                 "port1045",
    "Port of Colon":                  "port1035",
    "Port of Durban":                 "port311",
    "Port of Cape Town":              "port215",
    "Port of Lagos (Apapa)":          "port626",
    "Port of Melbourne":              "port729",
    "Port of Sydney (Botany)":        "port1243",
    "Port of Brisbane":               "port174",
}


def _capacity_for(port_name):
    """Daily vessel capacity used to normalise PortWatch calls.

    When several SupplyPulse ports share one PortWatch id, their capacities are summed.
    """
    port_id = PORT_NAME_MAP.get(port_name)
    if not port_id:
        return 0
    sharing = [n for n, pid in PORT_NAME_MAP.items() if pid == port_id]
    caps = {p["name"]: p.get("vessel_capacity", 0) for p in ports()}
    return sum(caps.get(n, 0) for n in sharing)


def load_cache():
    try:
        if os.path.exists(CACHE_FILE):
            with open(CACHE_FILE) as f:
                return json.load(f)
    except Exception:
        pass
    return {}


def save_cache(cache):
    try:
        os.makedirs(os.path.dirname(CACHE_FILE), exist_ok=True)
        with open(CACHE_FILE, "w") as f:
            json.dump(cache, f, indent=2)
    except Exception:
        pass


def fetch_portwatch_utilization(port_name):
    """Return (utilisation, source) or (None, None) when no live data is available."""
    cache = load_cache()
    cache_key = port_name.lower().replace(" ", "_")
    port_id = PORT_NAME_MAP.get(port_name)
    capacity = _capacity_for(port_name)
    if not port_id or not capacity:
        return None, None

    cached = cache.get(cache_key)
    if cached and cached.get("portid") == port_id and cached.get("capacity_used") == capacity:
        try:
            if datetime.now() - datetime.fromisoformat(cached["timestamp"]) < timedelta(days=CACHE_MAX_AGE_DAYS):
                return cached["utilization"], "portwatch_cache"
        except (KeyError, ValueError):
            pass

    try:
        params = {
            "where": f"portid='{port_id}'",
            "outFields": "portid,portname,portcalls,date",
            "orderByFields": "date DESC",
            "resultRecordCount": TRAILING_DAYS,
            "f": "json",
        }
        response = requests.get(PORTWATCH_BASE_URL, params=params, timeout=REQUEST_TIMEOUT_SECONDS)
        if response.status_code == 200:
            features = response.json().get("features", [])
            if features:
                daily_calls = [f["attributes"].get("portcalls", 0) or 0 for f in features]
                avg_daily_calls = sum(daily_calls) / len(daily_calls)
                utilization = round(avg_daily_calls / capacity, 3)
                cache[cache_key] = {
                    "utilization": utilization,
                    "timestamp": datetime.now().isoformat(),
                    "source": "portwatch_live",
                    "portid": port_id,
                    "capacity_used": capacity,
                    "avg_daily_calls": round(avg_daily_calls, 1),
                    "sample_days": len(daily_calls),
                    "port_name": port_name,
                }
                save_cache(cache)
                return utilization, "portwatch_live"
    except Exception as e:  # network down, bad JSON, ...
        print(f"  [PortWatch API] Could not fetch {port_name}: {e}")
    return None, None


def get_port_utilization(port_name, static_utilization):
    """Return (utilisation, source). Falls back to the static value when PortWatch is unavailable."""
    from agents.llm_utils import static_util

    if not static_util():
        live, source = fetch_portwatch_utilization(port_name)
        if live is not None:
            return live, source
    return static_utilization, "static"


if __name__ == "__main__":
    for name in ["Port of Singapore", "Port of Long Beach", "Suez Canal (Northern Entry)"]:
        start = time.time()
        print(name, fetch_portwatch_utilization(name), f"({time.time() - start:.2f}s)")
