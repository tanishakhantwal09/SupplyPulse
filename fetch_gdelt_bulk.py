import requests
import pandas as pd
import zipfile
import io
import os

os.makedirs("dataset/raw/gdelt_extra", exist_ok=True)

# Pull last 10 GDELT update files
urls = [
    "http://data.gdeltproject.org/gdeltv2/20260804163000.export.CSV.zip",
    "http://data.gdeltproject.org/gdeltv2/20260803163000.export.CSV.zip",
    "http://data.gdeltproject.org/gdeltv2/20260802163000.export.CSV.zip",
    "http://data.gdeltproject.org/gdeltv2/20260801163000.export.CSV.zip",
    "http://data.gdeltproject.org/gdeltv2/20260731163000.export.CSV.zip",
    "http://data.gdeltproject.org/gdeltv2/20260730163000.export.CSV.zip",
    "http://data.gdeltproject.org/gdeltv2/20260729163000.export.CSV.zip",
    "http://data.gdeltproject.org/gdeltv2/20260728163000.export.CSV.zip",
    "http://data.gdeltproject.org/gdeltv2/20260727163000.export.CSV.zip",
    "http://data.gdeltproject.org/gdeltv2/20260726163000.export.CSV.zip",
]

trading_nations = ['CHN', 'USA', 'DEU', 'JPN', 'KOR', 'SGP',
                   'NLD', 'GBR', 'IND', 'ARE', 'MYS', 'THA']

all_dfs = []

for url in urls:
    try:
        print(f"Downloading {url.split('/')[-1]}...")
        r = requests.get(url, timeout=60)
        z = zipfile.ZipFile(io.BytesIO(r.content))
        with z.open(z.namelist()[0]) as f:
            df = pd.read_csv(f, sep="\t", header=None, low_memory=False)
        filtered = df[df[7].isin(trading_nations) | df[17].isin(trading_nations)]
        all_dfs.append(filtered)
        print(f"  → {len(filtered)} events")
    except Exception as e:
        print(f"  → Failed: {e}")

if all_dfs:
    combined = pd.concat(all_dfs, ignore_index=True)
    combined.to_csv("dataset/raw/gdelt_extra/gdelt_combined.csv", index=False)
    print(f"\nTotal combined events: {len(combined)}")
    print("Saved to dataset/raw/gdelt_extra/gdelt_combined.csv")