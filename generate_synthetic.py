import pandas as pd
import numpy as np
import os
import json

os.makedirs("dataset/synthetic", exist_ok=True)
os.makedirs("dataset/scenarios", exist_ok=True)

np.random.seed(42)

print("Loading real data...")
df = pd.read_csv("dataset/master/real_data.csv", low_memory=False)
print(f"Real events loaded: {len(df)}")

# ── Extract real distributions ──────────────────────────────────────────────

# Severity distribution from real data
severity_dist = df["severity"].value_counts(normalize=True).to_dict()

# Country distribution from real data
country_dist = df["ActionGeo_CountryCode"].value_counts(normalize=True)
top_countries = country_dist.head(15).to_dict()

# GoldsteinScale stats from real data
goldstein_mean = df["GoldsteinScale"].mean()
goldstein_std  = df["GoldsteinScale"].std()

# AvgTone stats
tone_mean = df["AvgTone"].mean()
tone_std  = df["AvgTone"].std()

# NumMentions stats
mentions_mean = df["NumMentions"].mean()
mentions_std  = df["NumMentions"].std()

print(f"\nReal data distributions extracted:")
print(f"  Severity: {severity_dist}")
print(f"  Top countries: {list(top_countries.keys())[:5]}")
print(f"  GoldsteinScale mean: {goldstein_mean:.2f}, std: {goldstein_std:.2f}")

# ── Major ports for scenario generation ─────────────────────────────────────
ports = [
    {"name": "Port of Shanghai",    "country": "CHN", "lat": 31.2304, "lon": 121.4737},
    {"name": "Port of Singapore",   "country": "SGP", "lat":  1.2897, "lon": 103.8501},
    {"name": "Port of Rotterdam",   "country": "NLD", "lat": 51.9244, "lon":   4.4777},
    {"name": "Port of Los Angeles", "country": "USA", "lat": 33.7295, "lon": -118.2620},
    {"name": "Port of Hamburg",     "country": "DEU", "lat": 53.5753, "lon":   9.9835},
    {"name": "Port of Busan",       "country": "KOR", "lat": 35.1796, "lon": 129.0756},
    {"name": "Port of Dubai",       "country": "ARE", "lat": 25.2048, "lon":  55.2708},
    {"name": "Port of Tokyo",       "country": "JPN", "lat": 35.6762, "lon": 139.6503},
    {"name": "Port of Mumbai",      "country": "IND", "lat": 18.9322, "lon":  72.8264},
    {"name": "Port of Felixstowe",  "country": "GBR", "lat": 51.9600, "lon":   1.3500},
    {"name": "Port of Klang",       "country": "MYS", "lat":  3.0000, "lon": 101.4000},
    {"name": "Port of Laem Chabang","country": "THA", "lat": 13.0783, "lon": 100.8800},
]

# ── Disruption types with realistic freight impact ───────────────────────────
disruption_types = [
    {"type": "typhoon",              "severity_weights": [0.4, 0.4, 0.15, 0.05], "avg_duration_hrs": 72,  "freight_impact_pct": 25},
    {"type": "port_strike",          "severity_weights": [0.2, 0.4, 0.30, 0.10], "avg_duration_hrs": 120, "freight_impact_pct": 35},
    {"type": "geopolitical_tension", "severity_weights": [0.3, 0.4, 0.20, 0.10], "avg_duration_hrs": 240, "freight_impact_pct": 20},
    {"type": "equipment_failure",    "severity_weights": [0.1, 0.3, 0.40, 0.20], "avg_duration_hrs": 48,  "freight_impact_pct": 15},
    {"type": "pandemic_restriction", "severity_weights": [0.5, 0.3, 0.15, 0.05], "avg_duration_hrs": 336, "freight_impact_pct": 45},
    {"type": "canal_blockage",       "severity_weights": [0.6, 0.3, 0.08, 0.02], "avg_duration_hrs": 168, "freight_impact_pct": 60},
    {"type": "port_congestion",      "severity_weights": [0.1, 0.2, 0.40, 0.30], "avg_duration_hrs": 96,  "freight_impact_pct": 18},
    {"type": "cyberattack",          "severity_weights": [0.3, 0.4, 0.20, 0.10], "avg_duration_hrs": 60,  "freight_impact_pct": 30},
]

severity_labels = ["critical", "high", "medium", "low"]

# Alternative routes per region
alt_routes = {
    "CHN": ["Port of Busan", "Port of Tokyo", "Port of Singapore"],
    "SGP": ["Port of Klang", "Port of Laem Chabang", "Port of Mumbai"],
    "NLD": ["Port of Hamburg", "Port of Felixstowe", "Port of Rotterdam"],
    "USA": ["Port of Long Beach", "Port of Seattle", "Port of New York"],
    "DEU": ["Port of Rotterdam", "Port of Antwerp", "Port of Hamburg"],
    "KOR": ["Port of Shanghai", "Port of Tokyo", "Port of Singapore"],
    "ARE": ["Port of Mumbai", "Port of Singapore", "Port of Jeddah"],
    "JPN": ["Port of Busan", "Port of Shanghai", "Port of Singapore"],
    "IND": ["Port of Colombo", "Port of Singapore", "Port of Dubai"],
    "GBR": ["Port of Rotterdam", "Port of Antwerp", "Port of Hamburg"],
    "MYS": ["Port of Singapore", "Port of Laem Chabang", "Port of Jakarta"],
    "THA": ["Port of Klang", "Port of Singapore", "Port of Ho Chi Minh"],
}

# ── Generate synthetic scenarios ─────────────────────────────────────────────
N_SYNTHETIC = 2000
scenarios = []

for i in range(N_SYNTHETIC):
    port     = ports[i % len(ports)]
    d_type   = disruption_types[i % len(disruption_types)]
    severity = np.random.choice(severity_labels, p=d_type["severity_weights"])

    # Scale values from real distributions
    goldstein = np.clip(np.random.normal(goldstein_mean, goldstein_std), -10, 0)
    tone      = np.clip(np.random.normal(tone_mean, tone_std), -20, -0.5)
    mentions  = max(3, int(np.random.normal(mentions_mean, mentions_std)))

    duration  = int(d_type["avg_duration_hrs"] * np.random.uniform(0.5, 1.8))
    freight_impact = round(
        d_type["freight_impact_pct"] * np.random.uniform(0.7, 1.4), 2
    )

    alts = alt_routes.get(port["country"], ["Port of Singapore", "Port of Rotterdam"])

    scenario = {
        "scenario_id":        f"SYN_{i+1:04d}",
        "data_source":        "synthetic",
        "disruption_type":    d_type["type"],
        "affected_port":      port["name"],
        "country_code":       port["country"],
        "latitude":           port["lat"] + np.random.uniform(-0.5, 0.5),
        "longitude":          port["lon"] + np.random.uniform(-0.5, 0.5),
        "severity":           severity,
        "duration_hours":     duration,
        "goldstein_scale":    round(goldstein, 2),
        "avg_tone":           round(tone, 2),
        "num_mentions":       mentions,
        "freight_impact_pct": freight_impact,
        "alternative_routes": alts,
        "rerouting_required": severity in ["critical", "high"],
        "estimated_cost_usd": int(freight_impact * np.random.uniform(50000, 500000)),
    }
    scenarios.append(scenario)

# Save as CSV
syn_df = pd.DataFrame(scenarios)
syn_df.to_csv("dataset/synthetic/synthetic_scenarios.csv", index=False)

# Save first 100 as JSON (for agent consumption)
with open("dataset/scenarios/sample_scenarios.json", "w") as f:
    json.dump(scenarios[:100], f, indent=2)

print(f"Synthetic scenarios generated: {len(syn_df)}")
print(f"\nSeverity breakdown:")
print(syn_df["severity"].value_counts())
print(f"\nDisruption types:")
print(syn_df["disruption_type"].value_counts())
print(f"\nSample scenario:")
print(json.dumps(scenarios[0], indent=2))
print(f"\nSaved to dataset/synthetic/synthetic_scenarios.csv")
print(f"Sample JSON saved to dataset/scenarios/sample_scenarios.json")