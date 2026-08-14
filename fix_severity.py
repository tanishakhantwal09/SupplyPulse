import pandas as pd

df = pd.read_csv('dataset/final/master_enriched.csv', low_memory=False)
print('Before:')
print(df['severity'].value_counts())

def reassign_severity(row):
    g = float(row['goldstein_scale']) if pd.notna(row['goldstein_scale']) else 0
    t = float(row['avg_tone']) if pd.notna(row['avg_tone']) else 0
    m = int(row['num_mentions']) if pd.notna(row['num_mentions']) else 0
    if g <= -5 or (t <= -8 and m >= 20) or m >= 100:
        return 'critical'
    elif g <= -3 or (t <= -5 and m >= 10) or m >= 40:
        return 'high'
    elif g <= -1 or t <= -3 or m >= 10:
        return 'medium'
    else:
        return 'low'

df['severity'] = df.apply(reassign_severity, axis=1)
print('After:')
print(df['severity'].value_counts())
df.to_csv('dataset/final/master_enriched.csv', index=False)
print('Saved.')