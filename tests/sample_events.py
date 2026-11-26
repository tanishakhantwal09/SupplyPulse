"""Hand-built test events (not from the dataset, so no Parquet file is needed).

The news-signal values are chosen so the gate says PROCEED, except where noted.
"""

STRONG_SIGNAL = {"num_mentions": 60, "goldstein_scale": -8.0, "avg_tone": -9.0}  # gate score 0.905

SHANGHAI_CRITICAL = {
    "event_id": "TEST_SHANGHAI",
    "event_date": "2026-03-01",
    "data_source": "TEST",
    "nearest_port_id": "P001",
    "nearest_port_name": "Port of Shanghai",
    "nearest_port_country": "China",
    "severity": "critical",
    "vessels_affected": 350,        # enrich_gdelt.py rule for a critical mega_hub
    "duration_hours": 144,          # enrich_gdelt.py DURATION_MAP['critical']
    "freight_impact_pct": 48.0,
    "affected_routes": ["R001"],
    "affected_commodities": ["electronics", "textiles", "machinery"],
    **STRONG_SIGNAL,
}

SUEZ_CRITICAL = {
    **SHANGHAI_CRITICAL,
    "event_id": "TEST_SUEZ",
    "nearest_port_id": "P045",
    "nearest_port_name": "Suez Canal (Northern Entry)",
    "nearest_port_country": "Egypt",
    "vessels_affected": 500,        # enrich_gdelt.py rule for a critical chokepoint
    "affected_commodities": ["oil", "chemicals"],
}

ROTTERDAM_HIGH = {
    **SHANGHAI_CRITICAL,
    "event_id": "TEST_ROTTERDAM",
    "event_date": "2025-06-01",
    "nearest_port_id": "P021",
    "nearest_port_name": "Port of Rotterdam",
    "nearest_port_country": "Netherlands",
    "severity": "high",
    "vessels_affected": 90,
    "duration_hours": 72,
    "freight_impact_pct": 24.0,
    "affected_commodities": ["chemicals", "machinery"],
}

WEAK_SIGNAL = {**SHANGHAI_CRITICAL, "event_id": "TEST_WEAK",
               "num_mentions": 3, "goldstein_scale": -1.0, "avg_tone": -2.5}  # gate score 0.120

UNKNOWN_PORT = {**SHANGHAI_CRITICAL, "event_id": "TEST_UNKNOWN",
                "nearest_port_id": "P999", "nearest_port_name": "Nowhere"}

USER_SIMULATED = {**WEAK_SIGNAL, "event_id": "TEST_SIM", "data_source": "USER_SIMULATION"}
