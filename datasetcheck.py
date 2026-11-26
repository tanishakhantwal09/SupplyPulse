import pandas as pd
from pathlib import Path
from pandas.api.types import is_numeric_dtype

root = Path(__file__).parent
names = {"master": "master_enriched.parquet",
         "train": "training_set.parquet",
         "val": "validation_set_REAL_ONLY.parquet"}

with open(root / "dataset_summary.txt", "w", encoding="utf-8") as out:
    for key, fname in names.items():
        hits = [p for p in root.rglob(fname) if "venv" not in p.parts]
        if not hits:
            print("NOT FOUND:", fname, file=out)
            print("NOT FOUND:", fname)
            continue
        path = hits[0]
        df = pd.read_parquet(path)
        print("=====", key, path, df.shape, file=out)
        print(df.dtypes.to_string(), file=out)
        print("\nNULLS\n", df.isna().sum().to_string(), file=out)
        print("\nHEAD\n", df.head(5).T.to_string(), file=out)
        for c in df.columns:
            if not is_numeric_dtype(df[c]) and df[c].nunique() <= 40:
                print("\nCOUNTS", c, "\n", df[c].value_counts().head(15).to_string(), file=out)
        print("\nDESCRIBE\n", df.describe().T.to_string(), file=out)
        print("Loaded", key, df.shape)
print("Done. Attach dataset_summary.txt")