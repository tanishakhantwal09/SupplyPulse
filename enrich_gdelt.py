import pandas as pd
import numpy as np
import json
import os
import math
import gc
from datetime import datetime

# ── Setup ─────────────────────────────────────────────────────────────────────
os.makedirs("dataset/enriched", exist_ok=True)
os.makedirs("dataset/final", exist_ok=True)

# ── Load reference databases ──────────────────────────────────────────────────
print("Loading reference databases...")
with open("dataset/reference/ports.json") as f:
    ports = json.load(f)
with open("dataset/reference/routes.json") as f:
    routes = json.load(f)
with open("dataset/reference/commodities.json") as f:
    commodities = json.load(f)

print(f"  Ports loaded:       {len(ports)}")
print(f"  Routes loaded:      {len(routes)}")
print(f"  Commodities loaded: {len(commodities)}")

# ── GDELT column names ────────────────────────────────────────────────────────
GDELT_COLS = [
    "GLOBALEVENTID", "SQLDATE", "MonthYear", "Year", "FractionDate",
    "Actor1Code", "Actor1Name", "Actor1CountryCode", "Actor1KnownGroupCode",
    "Actor1EthnicCode", "Actor1Religion1Code", "Actor1Religion2Code",
    "Actor1Type1Code", "Actor1Type2Code", "Actor1Type3Code",
    "Actor2Code", "Actor2Name", "Actor2CountryCode", "Actor2KnownGroupCode",
    "Actor2EthnicCode", "Actor2Religion1Code", "Actor2Religion2Code",
    "Actor2Type1Code", "Actor2Type2Code", "Actor2Type3Code",
    "IsRootEvent", "EventCode", "EventRootCode", "EventBaseCode",
    "QuadClass", "GoldsteinScale", "NumMentions", "NumSources",
    "NumArticles", "AvgTone", "Actor1Geo_Type", "Actor1Geo_FullName",
    "Actor1Geo_CountryCode", "Actor1Geo_ADM1Code", "Actor1Geo_ADM2Code",
    "Actor1Geo_Lat", "Actor1Geo_Long", "Actor1Geo_FeatureID",
    "Actor2Geo_Type", "Actor2Geo_FullName", "Actor2Geo_CountryCode",
    "Actor2Geo_ADM1Code", "Actor2Geo_ADM2Code", "Actor2Geo_Lat",
    "Actor2Geo_Long", "Actor2Geo_FeatureID", "ActionGeo_Type",
    "ActionGeo_FullName", "ActionGeo_CountryCode", "ActionGeo_ADM1Code",
    "ActionGeo_ADM2Code", "ActionGeo_Lat", "ActionGeo_Long",
    "ActionGeo_FeatureID", "DATEADDED", "SOURCEURL"
]

# ── Helper: Haversine distance (nautical miles) ───────────────────────────────
def haversine_nm(lat1, lon1, lat2, lon2):
    R = 3440.065  # Earth radius in nautical miles
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2
    return 2 * R * math.asin(math.sqrt(a))

# ── Helper: Find nearest port ─────────────────────────────────────────────────
def find_nearest_port(lat, lon, max_nm=800):
    nearest = None
    min_dist = float('inf')
    for port in ports:
        try:
            dist = haversine_nm(lat, lon, port['lat'], port['lon'])
            if dist < min_dist:
                min_dist = dist
                nearest = port
        except:
            continue
    if nearest and min_dist <= max_nm:
        return nearest, round(min_dist, 1)
    return None, None

# ── Helper: Find affected routes ──────────────────────────────────────────────
def find_affected_routes(port_id):
    affected = []
    for route in routes:
        if port_id in route.get('key_ports', []):
            affected.append(route['route_id'])
    return affected

# ── Helper: Find affected commodities ────────────────────────────────────────
def find_affected_commodities(port_id, route_ids):
    affected_commodities = set()
    port = next((p for p in ports if p['port_id'] == port_id), None)
    if port:
        affected_commodities.update(port.get('commodities', []))
    for route_id in route_ids:
        route = next((r for r in routes if r['route_id'] == route_id), None)
        if route:
            affected_commodities.update(route.get('primary_commodities', []))
    return list(affected_commodities)[:5]

# ── Helper: Estimate freight impact ──────────────────────────────────────────
FREIGHT_IMPACT = {
    'critical': {'min': 35, 'max': 65, 'mean': 48},
    'high':     {'min': 15, 'max': 35, 'mean': 24},
    'medium':   {'min': 5,  'max': 15, 'mean': 9},
    'low':      {'min': 1,  'max': 5,  'mean': 3},
}

def estimate_freight_impact(severity, num_mentions):
    base = FREIGHT_IMPACT.get(severity, FREIGHT_IMPACT['medium'])
    mention_multiplier = min(1.5, 1 + (num_mentions / 100))
    impact = base['mean'] * mention_multiplier
    return round(min(impact, base['max']), 2)

# ── Helper: Estimate affected vessels ────────────────────────────────────────
def estimate_vessels(port, severity):
    capacity_map = {
        'mega_hub':     {'critical': 350, 'high': 180, 'medium': 80,  'low': 25},
        'major_hub':    {'critical': 180, 'high': 90,  'medium': 40,  'low': 12},
        'regional_hub': {'critical': 80,  'high': 40,  'medium': 18,  'low': 6},
        'chokepoint':   {'critical': 500, 'high': 250, 'medium': 100, 'low': 30},
        'alternate_route': {'critical': 50, 'high': 25, 'medium': 10, 'low': 3},
    }
    port_type = port.get('port_type', 'regional_hub')
    vessels = capacity_map.get(port_type, capacity_map['regional_hub'])
    return vessels.get(severity, 40)

# ── Helper: Generate agent decision ──────────────────────────────────────────
def generate_agent_decision(port, severity, affected_routes,
                             freight_impact, vessels_affected, duration_hrs):
    reroute       = severity in ['critical', 'high']
    alt_ports     = port.get('alternate_ports', [])
    alt_port_name = None
    if alt_ports:
        alt = next((p for p in ports if p['port_id'] == alt_ports[0]), None)
        if alt:
            alt_port_name = alt['name']

    alt_route = None
    if affected_routes:
        primary_route = next(
            (r for r in routes if r['route_id'] == affected_routes[0]), None
        )
        if primary_route:
            alt_route_id = primary_route.get('alternate_route')
            if alt_route_id:
                alt_r = next(
                    (r for r in routes if r['route_id'] == alt_route_id), None
                )
                if alt_r:
                    alt_route = alt_r['name']

    add_transit_days = 0
    if reroute and affected_routes:
        primary_route = next(
            (r for r in routes if r['route_id'] == affected_routes[0]), None
        )
        if primary_route:
            normal   = primary_route.get('avg_transit_days', 20)
            alternate = primary_route.get('alternate_transit_days', 30)
            add_transit_days = max(0, alternate - normal)

    estimated_cost = int(freight_impact * vessels_affected * np.random.uniform(8000, 25000))

    confidence = {
        'critical': 0.91, 'high': 0.82,
        'medium':   0.71, 'low':  0.58
    }.get(severity, 0.70)

    return {
        "reroute":                  reroute,
        "alternate_port":           alt_port_name,
        "alternate_route":          alt_route,
        "additional_transit_days":  add_transit_days,
        "inventory_reallocation":   severity in ['critical', 'high'],
        "financial_alert":          freight_impact > 20,
        "estimated_cost_usd":       estimated_cost,
        "delay_recommended":        severity == 'medium',
        "confidence_score":         confidence,
    }

# ── Helper: Assign severity ───────────────────────────────────────────────────
def assign_severity(goldstein, tone, mentions):
    score = 0
    if goldstein <= -7:    score += 3
    elif goldstein <= -4:  score += 2
    elif goldstein <= -1:  score += 1
    if tone <= -8:         score += 2
    elif tone <= -4:       score += 1
    if mentions >= 50:     score += 2
    elif mentions >= 15:   score += 1
    if score >= 6:   return 'critical'
    elif score >= 4: return 'high'
    elif score >= 2: return 'medium'
    else:            return 'low'

# ── Helper: Estimate duration ─────────────────────────────────────────────────
DURATION_MAP = {
    'critical': 144, 'high': 72, 'medium': 36, 'low': 12
}

# ── Main enrichment function ──────────────────────────────────────────────────
def enrich_chunk(chunk):
    results = []
    for _, row in chunk.iterrows():
        try:
            lat = float(row.get('ActionGeo_Lat', 0) or 0)
            lon = float(row.get('ActionGeo_Long', 0) or 0)
            if lat == 0 and lon == 0:
                continue

            goldstein = float(row.get('GoldsteinScale', 0) or 0)
            tone      = float(row.get('AvgTone', 0) or 0)
            mentions  = int(row.get('NumMentions', 0) or 0)

            # Filter — only negative significant events
            if tone >= -2 or mentions < 3:
                continue

            severity     = assign_severity(goldstein, tone, mentions)
            port, dist   = find_nearest_port(lat, lon)
            if not port:
                continue

            affected_routes      = find_affected_routes(port['port_id'])
            affected_commodities = find_affected_commodities(
                port['port_id'], affected_routes
            )
            freight_impact  = estimate_freight_impact(severity, mentions)
            vessels         = estimate_vessels(port, severity)
            duration        = DURATION_MAP.get(severity, 48)
            decision        = generate_agent_decision(
                port, severity, affected_routes,
                freight_impact, vessels, duration
            )

            results.append({
                # Original event data
                "event_id":            str(row.get('GLOBALEVENTID', '')),
                "event_date":          str(row.get('SQLDATE', '')),
                "event_location":      str(row.get('ActionGeo_FullName', '')),
                "event_country":       str(row.get('ActionGeo_CountryCode', '')),
                "event_lat":           round(lat, 4),
                "event_lon":           round(lon, 4),
                "goldstein_scale":     round(goldstein, 2),
                "avg_tone":            round(tone, 2),
                "num_mentions":        mentions,
                "source_url":          str(row.get('SOURCEURL', '')),
                "data_source":         "GDELT_real",

                # Enriched data
                "severity":            severity,
                "nearest_port_id":     port['port_id'],
                "nearest_port_name":   port['name'],
                "nearest_port_country":port['country'],
                "distance_to_port_nm": dist,
                "port_type":           port['port_type'],
                "port_strategic_importance": port['strategic_importance'],
                "affected_routes":     json.dumps(affected_routes),
                "affected_commodities":json.dumps(affected_commodities),
                "freight_impact_pct":  freight_impact,
                "vessels_affected":    vessels,
                "duration_hours":      duration,

                # Agent decision
                "decision_reroute":          decision['reroute'],
                "decision_alternate_port":   decision['alternate_port'],
                "decision_alternate_route":  decision['alternate_route'],
                "decision_transit_days_added": decision['additional_transit_days'],
                "decision_inventory_realloc": decision['inventory_reallocation'],
                "decision_financial_alert":  decision['financial_alert'],
                "decision_estimated_cost_usd": decision['estimated_cost_usd'],
                "decision_delay_recommended": decision['delay_recommended'],
                "decision_confidence":       decision['confidence_score'],
            })
        except Exception:
            continue
    return pd.DataFrame(results)

# ── Process each year ─────────────────────────────────────────────────────────
CHUNK_SIZE = 50000
years = range(2020, 2027)

print(f"\nStarting enrichment pipeline...")
print(f"Chunk size: {CHUNK_SIZE:,} rows")
print(f"Processing years: 2020-2026\n")

grand_total = 0

for year in years:
    input_path  = f"dataset/raw/gdelt_master/gdelt_{year}.csv"
    output_path = f"dataset/enriched/enriched_{year}.csv"

    if not os.path.exists(input_path):
        print(f"Year {year} — file not found, skipping")
        continue

    if os.path.exists(output_path):
        existing = pd.read_csv(output_path)
        print(f"Year {year} — already enriched ({len(existing):,} events) ✅")
        grand_total += len(existing)
        continue

    print(f"{'='*55}")
    print(f"Processing year {year}...")

    year_results = []
    chunk_num    = 0
    year_raw     = 0

    for chunk in pd.read_csv(
        input_path,
        sep=",",
        header=0,
        low_memory=False,
        chunksize=CHUNK_SIZE,
        encoding='utf-8',
        encoding_errors='ignore'
    ):
        chunk_num += 1
        year_raw  += len(chunk)

        # Assign column names if needed
        if len(chunk.columns) <= len(GDELT_COLS):
            chunk.columns = GDELT_COLS[:len(chunk.columns)]

        enriched_chunk = enrich_chunk(chunk)
        if len(enriched_chunk) > 0:
            year_results.append(enriched_chunk)

        print(f"  Chunk {chunk_num:>3} — "
              f"{year_raw:>7,} raw processed → "
              f"{sum(len(r) for r in year_results):>6,} enriched")

        # Free memory after each chunk
        del chunk
        gc.collect()

    if year_results:
        year_df = pd.concat(year_results, ignore_index=True)
        year_df.drop_duplicates(subset=['event_id'], inplace=True)
        year_df.to_csv(output_path, index=False)
        grand_total += len(year_df)
        print(f"\nYear {year} complete:")
        print(f"  Raw events processed: {year_raw:,}")
        print(f"  Enriched events:      {len(year_df):,}")
        print(f"  Retention rate:       {len(year_df)/year_raw*100:.1f}%")
        print(f"  Severity breakdown:")
        print(year_df['severity'].value_counts().to_string())
        del year_results, year_df
        gc.collect()
    else:
        print(f"Year {year} — no events passed filtering")

print(f"\n{'='*55}")
print(f"ENRICHMENT COMPLETE")
print(f"Total enriched events: {grand_total:,}")
print(f"Files saved in: dataset/enriched/")
print(f"\nNext step: run merge_enriched.py to create final dataset")