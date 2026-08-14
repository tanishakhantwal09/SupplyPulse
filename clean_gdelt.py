import pandas as pd
import os

os.makedirs("dataset/clean", exist_ok=True)

print("Loading raw GDELT data...")
df = pd.read_csv("dataset/raw/gdelt_raw.csv", low_memory=False)

# Assign proper column names (GDELT 2.0 schema)
gdelt_columns = [
    "GLOBALEVENTID", "SQLDATE", "MonthYear", "Year", "FractionDate",
    "Actor1Code", "Actor1Name", "Actor1CountryCode", "Actor1KnownGroupCode",
    "Actor1EthnicCode", "Actor1Religion1Code", "Actor1Religion2Code",
    "Actor1Type1Code", "Actor1Type2Code", "Actor1Type3Code",
    "Actor2Code", "Actor2Name", "Actor2CountryCode", "Actor2KnownGroupCode",
    "Actor2EthnicCode", "Actor2Religion1Code", "Actor2Religion2Code",
    "Actor2Type1Code", "Actor2Type2Code", "Actor2Type3Code",
    "IsRootEvent", "EventCode", "EventBaseCode", "EventRootCode",
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

# Apply column names if count matches
if len(df.columns) == len(gdelt_columns):
    df.columns = gdelt_columns
else:
    print(f"Column count mismatch: {len(df.columns)} vs {len(gdelt_columns)}, using positional")
    df.columns = gdelt_columns[:len(df.columns)]

print(f"Total events loaded: {len(df)}")

# Keep only useful columns
keep_cols = [
    "GLOBALEVENTID", "SQLDATE", "Actor1Name", "Actor1CountryCode",
    "Actor2Name", "Actor2CountryCode", "EventCode", "EventRootCode",
    "GoldsteinScale", "NumMentions", "NumArticles", "AvgTone",
    "ActionGeo_FullName", "ActionGeo_CountryCode",
    "ActionGeo_Lat", "ActionGeo_Long", "SOURCEURL"
]

existing_cols = [c for c in keep_cols if c in df.columns]
df = df[existing_cols]

# Drop rows with no location data
df.dropna(subset=["ActionGeo_Lat", "ActionGeo_Long"], inplace=True)

# Filter for negative tone events (disruptions are negative news)
if "AvgTone" in df.columns:
    df = df[df["AvgTone"] < -2]

# Filter for high mention count (more mentions = more significant event)
if "NumMentions" in df.columns:
    df = df[df["NumMentions"] >= 3]

# Add disruption severity label based on GoldsteinScale
# GoldsteinScale: -10 (most destabilizing) to +10 (most stabilizing)
if "GoldsteinScale" in df.columns:
    df["severity"] = pd.cut(
        df["GoldsteinScale"],
        bins=[-11, -5, -2, 0, 11],
        labels=["critical", "high", "medium", "low"]
    )

print(f"Events after filtering: {len(df)}")

# Save cleaned data
df.to_csv("dataset/clean/gdelt_clean.csv", index=False)
print(f"Saved to dataset/clean/gdelt_clean.csv")
print("\nSample of your real disruption data:")
print(df.head(3).to_string())