import requests
import pandas as pd
import zipfile
import io
import os
import time
from datetime import datetime, timedelta

# ── Configuration ─────────────────────────────────────────────────────────────
START_DATE    = datetime(2020, 1, 1)
END_DATE      = datetime(2026, 8, 7)
SNAPSHOTS     = ["090000", "163000"]  # 2 files per day — morning + evening
DELAY_SECONDS = 1.5                   # polite delay between requests
OUTPUT_DIR    = "dataset/raw/gdelt_master"
PROGRESS_LOG  = "dataset/raw/gdelt_master/progress.txt"

TRADING_NATIONS = [
    'CHN', 'USA', 'DEU', 'JPN', 'KOR', 'SGP',
    'NLD', 'GBR', 'IND', 'ARE', 'MYS', 'THA',
    'FRA', 'ITA', 'BRA', 'AUS', 'CAN', 'RUS',
    'SAU', 'ZAF', 'IDN', 'VNM', 'PAK', 'BGD',
    'EGY', 'NGA', 'MEX', 'ARG', 'TUR', 'POL'
]

os.makedirs(OUTPUT_DIR, exist_ok=True)

# ── Load already completed files from progress log ───────────────────────────
completed = set()
if os.path.exists(PROGRESS_LOG):
    with open(PROGRESS_LOG, "r") as f:
        completed = set(line.strip() for line in f.readlines())
    print(f"Resuming — {len(completed)} files already downloaded\n")
else:
    print("Starting fresh download\n")

# ── Generate all file timestamps ─────────────────────────────────────────────
all_files = []
current = START_DATE
while current <= END_DATE:
    for snapshot in SNAPSHOTS:
        all_files.append((current.year, current.strftime("%Y%m%d") + snapshot))
    current += timedelta(days=1)

total_files = len(all_files)
remaining   = [(yr, ts) for yr, ts in all_files if ts not in completed]

print(f"Total files to fetch:     {total_files}")
print(f"Already downloaded:       {len(completed)}")
print(f"Remaining:                {len(remaining)}")
print(f"Estimated time:           {len(remaining) * 2.5 / 60:.0f} minutes")
print(f"Trading nations monitored: {len(TRADING_NATIONS)}")
print(f"\nKey events this dataset covers:")
print(f"  2020      — COVID-19 global supply chain collapse")
print(f"  Mar 2021  — Suez Canal blockage (Ever Given)")
print(f"  2021-2022 — Global semiconductor & container shortage")
print(f"  Feb 2022  — Russia-Ukraine war, Black Sea disruption")
print(f"  2022-2023 — Taiwan Strait tensions, chip export restrictions")
print(f"  2023-2024 — Red Sea crisis, Houthi attacks, Cape rerouting")
print(f"  2024      — Panama Canal drought")
print(f"  2025-2026 — Latest geopolitical disruptions")
print(f"\nStarting download...\n")

# ── Download year by year ─────────────────────────────────────────────────────
years = list(range(START_DATE.year, END_DATE.year + 1))

for year in years:
    year_files  = [(yr, ts) for yr, ts in remaining if yr == year]
    year_output = os.path.join(OUTPUT_DIR, f"gdelt_{year}.csv")

    if not year_files:
        print(f"Year {year} — already complete ✅")
        continue

    print(f"\n{'='*55}")
    print(f"Year {year} — {len(year_files)} files to download")
    print(f"{'='*55}")

    year_dfs    = []
    success     = 0
    failed      = 0

    # Load existing year file if resuming mid-year
    if os.path.exists(year_output):
        existing = pd.read_csv(year_output, low_memory=False)
        year_dfs.append(existing)
        print(f"  Loaded existing {year} data: {len(existing)} events")

    for i, (yr, date_str) in enumerate(year_files):
        url = f"http://data.gdeltproject.org/gdeltv2/{date_str}.export.CSV.zip"

        try:
            r = requests.get(url, timeout=45)

            if r.status_code != 200:
                print(f"  ❌ {date_str[:8]} {date_str[8:]} — HTTP {r.status_code}")
                failed += 1
                continue

            z = zipfile.ZipFile(io.BytesIO(r.content))
            with z.open(z.namelist()[0]) as f:
                df = pd.read_csv(f, sep="\t", header=None, low_memory=False)

            # Filter for trading nations
            filtered = df[
                df[7].isin(TRADING_NATIONS) |
                df[17].isin(TRADING_NATIONS)
            ]

            if len(filtered) > 0:
                year_dfs.append(filtered)

            # Mark as completed
            with open(PROGRESS_LOG, "a") as log:
                log.write(date_str + "\n")
            completed.add(date_str)

            success += 1
            print(f"  ✅ {date_str[:8]} {date_str[8:]} — {len(filtered):>4} events  [{i+1}/{len(year_files)}]")

        except zipfile.BadZipFile:
            print(f"  ❌ {date_str[:8]} {date_str[8:]} — Bad zip file")
            failed += 1
        except Exception as e:
            print(f"  ❌ {date_str[:8]} {date_str[8:]} — Error: {str(e)[:50]}")
            failed += 1

        time.sleep(DELAY_SECONDS)

        # Save year file every 20 files to protect against crashes
        if len(year_dfs) > 0 and (i + 1) % 20 == 0:
            checkpoint = pd.concat(year_dfs, ignore_index=True)
            checkpoint.drop_duplicates(inplace=True)
            checkpoint.to_csv(year_output, index=False)
            print(f"  💾 Checkpoint saved — {len(checkpoint)} events so far")

    # Save final year file
    if year_dfs:
        year_combined = pd.concat(year_dfs, ignore_index=True)
        year_combined.drop_duplicates(inplace=True)
        year_combined.to_csv(year_output, index=False)
        print(f"\n  Year {year} complete:")
        print(f"  Total events saved: {len(year_combined)}")
        print(f"  Success: {success} | Failed: {failed}")
    else:
        print(f"\n  Year {year} — no data collected")

# ── Final summary ─────────────────────────────────────────────────────────────
print(f"\n{'='*55}")
print(f"DOWNLOAD COMPLETE")
print(f"{'='*55}")

total_events = 0
for year in years:
    year_output = os.path.join(OUTPUT_DIR, f"gdelt_{year}.csv")
    if os.path.exists(year_output):
        df = pd.read_csv(year_output, low_memory=False)
        print(f"  {year}: {len(df):>7} events — {year_output}")
        total_events += len(df)

print(f"\nTotal raw events across all years: {total_events:,}")
print(f"Files saved in: {OUTPUT_DIR}")
print(f"\nNext step: run clean_gdelt_master.py to clean and structure this data")