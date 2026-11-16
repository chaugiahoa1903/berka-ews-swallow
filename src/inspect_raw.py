# src/inspect_raw.py - xem nhanh cột, kiểu dữ liệu, null của các bảng chính
from pathlib import Path
import pandas as pd

RAW = Path(__file__).resolve().parent.parent / "data" / "raw"

for name in ["loan", "account", "trans", "client"]:
    df = pd.read_csv(RAW / f"{name}.csv", nrows=200_000 if name == "trans" else None)
    print(f"\n=== {name} ===")
    print(df.head(3).to_string())
    print("null:", df.isna().sum()[lambda s: s > 0].to_dict())

loan = pd.read_csv(RAW / "loan.csv")
print("\nloan.status:", loan["status"].value_counts().to_dict())
