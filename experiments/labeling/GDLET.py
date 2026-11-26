import pandas as pd
df = pd.read_parquet('dataset/final/master_enriched.parquet')
df['year'] = pd.to_datetime(df['event_date']).dt.year
print(df['year'].value_counts().sort_index())