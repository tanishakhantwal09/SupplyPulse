import requests
import json
import os
import time
from datetime import datetime, timedelta

PORTWATCH_BASE_URL = "https://services9.arcgis.com/weJ1QsnbMYJlCHdG/ArcGIS/rest/services/Daily_Ports_Data/FeatureServer/0/query"
CACHE_FILE = "dataset/reference/portwatch_cache.json"
PORTS_REFERENCE_FILE = "dataset/reference/ports.json"

# Port name (as used in ports.json) -> IMF PortWatch portid.
# Verified 2026-09-14 against the live Daily_Ports_Data FeatureServer —
# each entry was resolved with a `portname LIKE '%term%' AND ISO3='...'`
# query and hand-checked against the returned portname/country.
# The 6 SupplyPulse "ports" not listed here are canals/straits/bypass
# routes (Suez Canal, Panama Canal, Strait of Malacca, Cape of Good Hope,
# Lombok Strait, Cape Horn) — PortWatch's Daily_Ports_Data service tracks
# cargo-handling ports, not transit chokepoints, so these have no live
# entry and always use the static fallback from ports.json.
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

_ports_reference_cache = None


def _load_vessel_capacity(port_name: str):
    """Look up the port's static vessel_capacity (daily throughput proxy)
    from ports.json — used to normalize live portcalls into a 0-1 ratio."""
    global _ports_reference_cache
    if _ports_reference_cache is None:
        try:
            with open(PORTS_REFERENCE_FILE) as f:
                _ports_reference_cache = {p['name']: p.get('vessel_capacity', 0) for p in json.load(f)}
        except Exception:
            _ports_reference_cache = {}
    return _ports_reference_cache.get(port_name, 0)


def fetch_portwatch_utilization(port_name: str):
    """
    Fetch live port congestion/utilization from IMF PortWatch API.
    Free academic API — satellite AIS-derived vessel port calls, updated daily.
    Reference: IMF PortWatch (2023) portwatch.imf.org

    Utilization = trailing 7-day average daily port calls / static vessel_capacity
    from ports.json (both are "vessels/day" throughput proxies, so the ratio
    is a live analogue of the same congestion signal BPR consumes).

    Returns utilization as float >= 0.0 (uncapped — a value above 1.0 means the
    port is running above its calibrated capacity, which is a legitimate
    congestion signal) or None if no live data is available.
    Falls back to static data in ports.json when this returns None.
    """
    cache = load_cache()
    cache_key = port_name.lower().replace(" ", "_")

    if cache_key in cache:
        cached = cache[cache_key]
        try:
            cached_time = datetime.fromisoformat(cached['timestamp'])
            if datetime.now() - cached_time < timedelta(days=7):
                return cached['utilization']
        except (KeyError, ValueError):
            pass

    try:
        port_id = PORT_NAME_MAP.get(port_name)
        if not port_id:
            return None

        capacity = _load_vessel_capacity(port_name)
        if not capacity:
            return None

        params = {
            'where': f"portid='{port_id}'",
            'outFields': 'portid,portname,portcalls,date',
            'orderByFields': 'date DESC',
            'resultRecordCount': 7,
            'f': 'json'
        }

        response = requests.get(PORTWATCH_BASE_URL, params=params, timeout=10)

        if response.status_code == 200:
            data = response.json()
            features = data.get('features', [])

            if features:
                daily_calls = [
                    f['attributes'].get('portcalls', 0) or 0
                    for f in features
                ]
                avg_daily_calls = sum(daily_calls) / len(daily_calls)
                utilization = round(avg_daily_calls / capacity, 3)

                cache[cache_key] = {
                    'utilization':     utilization,
                    'timestamp':       datetime.now().isoformat(),
                    'source':          'portwatch_live',
                    'avg_daily_calls': round(avg_daily_calls, 1),
                    'sample_days':     len(daily_calls),
                    'port_name':       port_name,
                }
                save_cache(cache)
                return utilization

    except Exception as e:
        print(f"  [PortWatch API] Could not fetch {port_name}: {e}")

    return None  # Trigger static fallback


def load_cache() -> dict:
    try:
        if os.path.exists(CACHE_FILE):
            with open(CACHE_FILE) as f:
                return json.load(f)
    except Exception:
        pass
    return {}


def save_cache(cache: dict):
    try:
        os.makedirs(os.path.dirname(CACHE_FILE), exist_ok=True)
        with open(CACHE_FILE, 'w') as f:
            json.dump(cache, f, indent=2)
    except Exception:
        pass


def get_port_utilization(port_name: str, static_utilization: float):
    """
    Get port utilization — tries PortWatch live first, falls back to static.
    Returns (utilization, source) where source is 'portwatch_live' or 'static'.
    """
    live = fetch_portwatch_utilization(port_name)
    if live is not None:
        return live, 'portwatch_live'
    return static_utilization, 'static'


if __name__ == "__main__":
    for name in ["Port of Singapore", "Port of Shanghai", "Suez Canal (Northern Entry)"]:
        start = time.time()
        result = fetch_portwatch_utilization(name)
        print(f"{name}: {result} ({time.time() - start:.2f}s)")
