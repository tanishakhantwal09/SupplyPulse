import pandas as pd
df = pd.read_parquet('dataset/final/validation_set_REAL_ONLY.parquet')
sample = df.sample(n=100, random_state=42).reset_index(drop=True)
cols = ['event_id', 'event_date', 'source_url', 'event_location', 'nearest_port_name']
available = [c for c in cols if c in sample.columns]
sample[available].to_csv('experiments/labeling/labels_solo.csv', index=False)
print("Created experiments/labeling/labels_solo.csv with 100 events.")