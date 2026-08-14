import requests
import pandas as pd
import zipfile
import io
import os

os.makedirs("dataset/raw", exist_ok=True)

print("Fetching GDELT event data directly...")

# GDELT 2.0 Event files - these are always publicly accessible
# Using recent master file list to get latest available file
MASTER_URL = "http://data.gdeltproject.org/gdeltv2/lastupdate.txt"

try:
    response = requests.get(MASTER_URL, timeout=15)
    lines = response.text.strip().split("\n")
    
    # Get the export file URL (first line contains event data)
    export_line = [l for l in lines if "export" in l.lower()][0]
    zip_url = export_line.split(" ")[-1].strip()
    
    print(f"Downloading from: {zip_url}")
    
    zip_response = requests.get(zip_url, timeout=60)
    z = zipfile.ZipFile(io.BytesIO(zip_response.content))
    csv_filename = z.namelist()[0]
    
    with z.open(csv_filename) as f:
        df = pd.read_csv(f, sep="\t", header=None, low_memory=False)
    
    print(f"Total events downloaded: {len(df)}")
    
    # GDELT column 27 is EventCode - filter for supply chain relevant codes
    # Actor1CountryCode col 7, Actor2CountryCode col 17
    # EventRootCode col 28: 14=PROTEST, 19=DEMAND, 20=APPEAL
    # We want transport/trade disruption events
    
    # Filter by event codes related to disruptions (GDELT CAMEO codes)
    # 14 = PROTEST, 15 = EXHIBIT FORCE, 17 = COERCE, 18 = ASSAULT
    # Also filter where columns contain shipping-related text
    
    df.columns = range(len(df.columns))
    
    # Keep events from major trading nations
    trading_nations = ['CHN', 'USA', 'DEU', 'JPN', 'KOR', 'SGP', 
                       'NLD', 'GBR', 'IND', 'ARE', 'MYS', 'THA']
    
    filtered = df[df[7].isin(trading_nations) | df[17].isin(trading_nations)]
    
    print(f"Events involving major trading nations: {len(filtered)}")
    
    # Save raw filtered
    filtered.to_csv("dataset/raw/gdelt_raw.csv", index=False)
    print(f"Saved to dataset/raw/gdelt_raw.csv")

except Exception as e:
    print(f"Error: {e}")
    print("Trying backup approach...")
    
    # Backup: use GDELT 1.0 which is simpler
    url = "http://data.gdeltproject.org/events/20240115.export.CSV.zip"
    try:
        r = requests.get(url, timeout=60)
        z = zipfile.ZipFile(io.BytesIO(r.content))
        with z.open(z.namelist()[0]) as f:
            df = pd.read_csv(f, sep="\t", header=None, low_memory=False)
        df.to_csv("dataset/raw/gdelt_raw.csv", index=False)
        print(f"Backup successful. {len(df)} events saved.")
    except Exception as e2:
        print(f"Backup also failed: {e2}")