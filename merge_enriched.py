import pandas as pd
import numpy as np
import os

os.makedirs("dataset/final", exist_ok=True)

print("Merging all enriched yearly files...")

all_dfs = []
for year in range(2020, 2027):
    path = f"dataset/enriched/enriched_{year}.csv"
    if os.path.exists(path):
        df = pd.read_csv(path, low_memory=False)
        df['year'] = year
        all_dfs.append(df)
        print(f"  {year}: {len(df):,} events loaded")

print(f"\nCombining all years...")
master = pd.concat(all_dfs, ignore_index=True)
master.drop_duplicates(subset=['event_id'], inplace=True)

print(f"Total after dedup: {len(master):,}")

# ── Clean date column ─────────────────────────────────────────────────────────
master['event_date'] = pd.to_datetime(
    master['event_date'].astype(str),
    format='%Y%m%d', errors='coerce'
)

# ── 70/30 split ───────────────────────────────────────────────────────────────
print(f"\nSplitting 70/30...")
master = master.sample(frac=1, random_state=42).reset_index(drop=True)
split  = int(len(master) * 0.70)

train = master.iloc[:split]
valid = master.iloc[split:]

train.to_csv("dataset/final/training_set.csv", index=False)
valid.to_csv("dataset/final/validation_set_REAL_ONLY.csv", index=False)
master.to_csv("dataset/final/master_enriched.csv", index=False)

print(f"\n{'='*55}")
print(f"FINAL DATASET READY")
print(f"{'='*55}")
print(f"Total enriched events:  {len(master):,}")
print(f"Training set (70%):     {len(train):,}")
print(f"Validation set (30%):   {len(valid):,}")
print(f"\nSeverity breakdown (full dataset):")
print(master['severity'].value_counts())
print(f"\nTop affected ports:")
print(master['nearest_port_name'].value_counts().head(10))
print(f"\nTop affected routes:")
import json
all_routes = []
for r in master['affected_routes'].dropna():
    try:
        all_routes.extend(json.loads(r))
    except:
        continue
print(pd.Series(all_routes).value_counts().head(10))
print(f"\nDecision breakdown:")
print(f"  Reroute required:     {master['decision_reroute'].sum():,} events")
print(f"  Financial alert:      {master['decision_financial_alert'].sum():,} events")
print(f"  Inventory realloc:    {master['decision_inventory_realloc'].sum():,} events")
print(f"\nFiles saved:")
print(f"  dataset/final/master_enriched.csv")
print(f"  dataset/final/training_set.csv")
print(f"  dataset/final/validation_set_REAL_ONLY.csv")