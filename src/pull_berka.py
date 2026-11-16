# src/pull_berka.py - kéo 8 bảng Berka từ CTU relational repository về data/raw (CSV thô)
from pathlib import Path
import pandas as pd
from sqlalchemy import create_engine

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "raw"
OUT.mkdir(parents=True, exist_ok=True)

# Tài khoản guest công khai, chỉ đọc
HOST, PORT, USER, PWD, DB = "relational.fel.cvut.cz", 3306, "guest", "ctu-relational", "financial"
engine = create_engine(f"mysql+pymysql://{USER}:{PWD}@{HOST}:{PORT}/{DB}")

# `order` là từ khóa SQL nên bọc backtick
TABLES = ["account", "client", "disp", "trans", "`order`", "loan", "card", "district"]

for t in TABLES:
    name = t.strip("`")
    path = OUT / f"{name}.csv"
    first, n = True, 0
    for chunk in pd.read_sql(f"SELECT * FROM {t}", engine, chunksize=100_000):
        chunk.to_csv(path, mode="w" if first else "a", header=first, index=False, encoding="utf-8")
        first, n = False, n + len(chunk)
    print(f"{name:10s} {n:>9,d} dòng -> {path.relative_to(ROOT)}")
