import pandas as pd
import os

os.makedirs("dataset/master", exist_ok=True)

print("Merging all GDELT clean files...")

df1 = pd.read_csv("dataset/clean/gdelt_clean.csv", low_memory=False)
df2 = pd.read_csv("dataset/clean/gdelt_bulk_clean.csv", low_memory=False)

print(f"File 1 (first pull): {len(df1)} events")
print(f"File 2 (bulk pull): {len(df2)} events")

# Merge
combined = pd.concat([df1, df2], ignore_index=True)

# Remove duplicates by event ID
if "GLOBALEVENTID" in combined.columns:
    combined.drop_duplicates(subset=["GLOBALEVENTID"], inplace=True)

print(f"Combined after dedup: {len(combined)} events")

# Add a clean date column
if "SQLDATE" in combined.columns:
    combined["date_clean"] = pd.to_datetime(
        combined["SQLDATE"].astype(str), format="%Y%m%d", errors="coerce"
    )

# Add source label
combined["data_source"] = "GDELT"

# Save master real dataset
combined.to_csv("dataset/master/real_data.csv", index=False)

print(f"\nMaster real dataset saved: dataset/master/real_data.csv")
print(f"Total real events: {len(combined)}")
print(f"\nSeverity breakdown:")
print(combined["severity"].value_counts())
print(f"\nDate range:")
print(f"  Earliest: {combined['date_clean'].min()}")
print(f"  Latest:   {combined['date_clean'].max()}")