# src/load_staging.py - nạp 8 CSV thô vào SQL Server, schema stg (toàn bộ cột là chữ, chưa ép kiểu)
import os
from pathlib import Path
from urllib.parse import quote_plus
import pandas as pd
import pyodbc
from sqlalchemy import create_engine, text, types

RAW = Path(__file__).resolve().parent.parent / "data" / "raw"
SERVER = os.getenv("SWALLOW_SQL_SERVER", "localhost")   # Express thường là .\SQLEXPRESS
DB = "Swallow"
base = (f"DRIVER={{ODBC Driver 18 for SQL Server}};SERVER={SERVER};"
        "Trusted_Connection=yes;TrustServerCertificate=yes;")

# tạo database và schema nếu chưa có
with pyodbc.connect(base + "DATABASE=master;", autocommit=True) as cn:
    cn.execute(f"IF DB_ID('{DB}') IS NULL CREATE DATABASE {DB}")
with pyodbc.connect(base + f"DATABASE={DB};", autocommit=True) as cn:
    cn.execute("IF SCHEMA_ID('stg') IS NULL EXEC('CREATE SCHEMA stg')")

engine = create_engine("mssql+pyodbc:///?odbc_connect=" + quote_plus(base + f"DATABASE={DB};"),
                       fast_executemany=True)

for name in ["account", "client", "disp", "trans", "order", "loan", "card", "district"]:
    # giữ nguyên giá trị gốc: chỉ ô rỗng mới thành NULL
    df = pd.read_csv(RAW / f"{name}.csv", dtype=str, keep_default_na=False, na_values=[""])
    df.to_sql(name, engine, schema="stg", if_exists="replace", index=False,
              chunksize=50_000, dtype={c: types.NVARCHAR(64) for c in df.columns})
    with engine.connect() as c:
        n = c.execute(text(f"SELECT COUNT(*) FROM stg.[{name}]")).scalar()
    print(f"stg.{name:9s} csv={len(df):>9,d}  sql={n:>9,d}  {'OK' if n == len(df) else 'LỆCH'}")
