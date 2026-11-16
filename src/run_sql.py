# src/run_sql.py - chạy file .sql (tách batch theo dòng GO), in các bảng kết quả
import os, re, sys
from pathlib import Path
import pandas as pd
import pyodbc

SERVER = os.getenv("SWALLOW_SQL_SERVER", "localhost")
conn = pyodbc.connect(f"DRIVER={{ODBC Driver 18 for SQL Server}};SERVER={SERVER};"
                      "Trusted_Connection=yes;TrustServerCertificate=yes;DATABASE=Swallow;",
                      autocommit=True)
conn.execute("SET NOCOUNT ON")

for f in sys.argv[1:]:
    print(f"\n##### {f}")
    sql = Path(f).read_text(encoding="utf-8-sig")
    for batch in re.split(r"^\s*GO\s*$", sql, flags=re.M | re.I):
        if not batch.strip():
            continue
        cur = conn.cursor()
        cur.execute(batch)
        while True:
            if cur.description:
                cols = [c[0] for c in cur.description]
                print(pd.DataFrame([tuple(r) for r in cur.fetchall()], columns=cols).to_string(index=False), "\n")
            if not cur.nextset():
                break
    print(f"OK {f}")
