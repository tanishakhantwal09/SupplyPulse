import pandas as pd
import os

os.makedirs("dataset/clean", exist_ok=True)

gdelt_columns = [
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

print("Loading bulk GDELT data...")
df = pd.read_csv("dataset/raw/gdelt_extra/gdelt_combined.csv", 
                 low_memory=False, header=None)

# Assign column names
if len(df.columns) <= len(gdelt_columns):
    df.columns = gdelt_columns[:len(df.columns)]

print(f"Total events loaded: {len(df)}")

# Keep useful columns
keep_cols = [
    "GLOBALEVENTID", "SQLDATE", "Actor1Name", "Actor1CountryCode",
    "Actor2Name", "Actor2CountryCode", "EventCode", "EventRootCode",
    "GoldsteinScale", "NumMentions", "NumArticles", "AvgTone",
    "ActionGeo_FullName", "ActionGeo_CountryCode",
    "ActionGeo_Lat", "ActionGeo_Long", "SOURCEURL"
]

existing_cols = [c for c in keep_cols if c in df.columns]
df = df[existing_cols]

# Drop rows missing location
df.dropna(subset=["ActionGeo_Lat", "ActionGeo_Long"], inplace=True)

# Filter negative tone (disruptions = negative news)
if "AvgTone" in df.columns:
    df = df[df["AvgTone"] < -2]

# Filter significant events only
if "NumMentions" in df.columns:
    df = df[df["NumMentions"] >= 3]

# Add severity label
if "GoldsteinScale" in df.columns:
    df["severity"] = pd.cut(
        df["GoldsteinScale"],
        bins=[-11, -5, -2, 0, 11],
        labels=["critical", "high", "medium", "low"]
    )

# Add disruption type based on EventRootCode
disruption_map = {
    1: "verbal_cooperation",
    2: "material_cooperation", 
    3: "verbal_conflict",
    4: "material_conflict",
    5: "protest",
    6: "demand",
    7: "disapprove",
    8: "threaten",
    9: "investigate",
    10: "sanction",
    11: "coerce",
    12: "assault",
    13: "fight",
    14: "mass_violence"
}

if "EventRootCode" in df.columns:
    df["disruption_type"] = df["EventRootCode"].map(
        lambda x: disruption_map.get(int(x), "other") 
        if pd.notna(x) else "unknown"
    )

# Remove duplicates
df.drop_duplicates(subset=["GLOBALEVENTID"], inplace=True)

print(f"Events after filtering: {len(df)}")
print(f"\nSeverity breakdown:")
print(df["severity"].value_counts())
print(f"\nDisruption types:")
print(df["disruption_type"].value_counts().head(8))

# Save
df.to_csv("dataset/clean/gdelt_bulk_clean.csv", index=False)
print(f"\nSaved to dataset/clean/gdelt_bulk_clean.csv")