"""Paths and reference data (50 ports, 10 routes, 8 commodities).

Everything is loaded with absolute paths, so the agents work from any
working directory (the old code called os.chdir() at import time).
"""
import json
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REFERENCE_DIR = ROOT / "dataset" / "reference"
DATA_DIR = ROOT / "dataset" / "final"


@lru_cache(maxsize=None)
def _load(name):
    with open(REFERENCE_DIR / name, encoding="utf-8") as f:
        return json.load(f)


def ports():
    return _load("ports.json")


def routes():
    return _load("routes.json")


def commodities():
    return _load("commodities.json")


def port_by_id(port_id):
    return next((p for p in ports() if p["port_id"] == port_id), None)


def routes_calling_at(port_id):
    """Route ids whose key_ports include the port: the same rule as
    enrich_gdelt.find_affected_routes(), which builds the dataset's affected_routes column."""
    return [r["route_id"] for r in routes() if port_id in r.get("key_ports", [])]


def port_by_name(name):
    return next((p for p in ports() if p["name"] == name), None)
