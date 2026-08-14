import pandas as pd
import numpy as np
import os

os.makedirs("dataset/final", exist_ok=True)

np.random.seed(42)

print("Loading datasets...")
real_df = pd.read_csv("dataset/master/real_data.csv", low_memory=False)
syn_df  = pd.read_csv("dataset/synthetic/synthetic_scenarios.csv")

print(f"Real events:      {len(real_df)}")
print(f"Synthetic events: {len(syn_df)}")

# ── Split real data 70/30 ────────────────────────────────────────────────────
real_df = real_df.sample(frac=1, random_state=42).reset_index(drop=True)

split_idx        = int(len(real_df) * 0.70)
real_train       = real_df.iloc[:split_idx]
real_validation  = real_df.iloc[split_idx:]

print(f"\nReal data split:")
print(f"  Training   (70%): {len(real_train)} events")
print(f"  Validation (30%): {len(real_validation)} events  ← LOCKED, never touched during development")

# ── Training set = real_train + all synthetic ────────────────────────────────
# Align columns before concat
common_cols = [
    "data_source", "severity",
    "ActionGeo_Lat", "ActionGeo_Long",
    "GoldsteinScale", "AvgTone", "NumMentions"
]

# Rename synthetic columns to match real
syn_rename = {
    "latitude":      "ActionGeo_Lat",
    "longitude":     "ActionGeo_Long",
    "goldstein_scale": "GoldsteinScale",
    "avg_tone":      "AvgTone",
    "num_mentions":  "NumMentions",
}
syn_aligned = syn_df.rename(columns=syn_rename)

# Add missing columns with NaN
for col in common_cols:
    if col not in real_train.columns:
        real_train[col] = None
    if col not in syn_aligned.columns:
        syn_aligned[col] = None

training_set = pd.concat(
    [real_train[common_cols], syn_aligned[common_cols]],
    ignore_index=True
)

print(f"\nFinal training set: {len(training_set)} total events")
print(f"  → {len(real_train)} real + {len(syn_aligned)} synthetic")

# ── Save ─────────────────────────────────────────────────────────────────────
training_set.to_csv("dataset/final/training_set.csv", index=False)
real_validation.to_csv("dataset/final/validation_set_REAL_ONLY.csv", index=False)
syn_df.to_csv("dataset/final/synthetic_full.csv", index=False)

print(f"\n✅ Final dataset ready:")
print(f"   dataset/final/training_set.csv              ← {len(training_set)} events (train on this)")
print(f"   dataset/final/validation_set_REAL_ONLY.csv  ← {len(real_validation)} events (test on this)")
print(f"   dataset/final/synthetic_full.csv            ← {len(syn_df)} synthetic scenarios")

print(f"\nValidation set severity breakdown:")
print(real_validation["severity"].value_counts())