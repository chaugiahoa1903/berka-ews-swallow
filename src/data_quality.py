# src/data_quality.py - báo cáo chất lượng dữ liệu trên staging, ghi ra reports/data_quality.md
import os
from pathlib import Path
from urllib.parse import quote_plus
import pandas as pd
from sqlalchemy import create_engine, text

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "reports"
OUT.mkdir(exist_ok=True)
SERVER = os.getenv("SWALLOW_SQL_SERVER", "localhost")
base = (f"DRIVER={{ODBC Driver 18 for SQL Server}};SERVER={SERVER};"
        "Trusted_Connection=yes;TrustServerCertificate=yes;DATABASE=Swallow;")
engine = create_engine("mssql+pyodbc:///?odbc_connect=" + quote_plus(base))
q = lambda sql: pd.read_sql(text(sql), engine)

TABLES = ["account", "client", "disp", "trans", "order", "loan", "card", "district"]
parts = ["# Data quality report (staging, Berka qua CTU relational repository)\n"]
def add(title, df):
    parts.append(f"## {title}\n```\n{df.to_string(index=False)}\n```\n")

# 1. Null theo cột, tính trên toàn bộ bảng
rows = []
for t in TABLES:
    cols = q(f"SELECT COLUMN_NAME AS c FROM INFORMATION_SCHEMA.COLUMNS "
             f"WHERE TABLE_SCHEMA='stg' AND TABLE_NAME='{t}' ORDER BY ORDINAL_POSITION")["c"]
    sel = ", ".join(f"SUM(CASE WHEN [{c}] IS NULL THEN 1 ELSE 0 END) AS [{c}]" for c in cols)
    r = q(f"SELECT COUNT(*) AS n_rows_, {sel} FROM stg.[{t}]").iloc[0]
    rows += [(t, c, int(r["n_rows_"]), int(r[c])) for c in cols]
nulls = pd.DataFrame(rows, columns=["table", "column", "rows", "nulls"])
nulls["null_pct"] = (100 * nulls["nulls"] / nulls["rows"]).round(2)
add("Cột có null (toàn bộ bảng)", nulls[nulls["nulls"] > 0])

# 2. Mã Czech trong trans
for col in ["type", "operation", "k_symbol"]:
    add(f"trans.{col}", q(f"SELECT ISNULL([{col}], '<NULL>') AS value, COUNT(*) AS n "
                          f"FROM stg.trans GROUP BY [{col}] ORDER BY n DESC"))

# 3. Trùng khóa chính
pk = {"account": "account_id", "client": "client_id", "disp": "disp_id", "trans": "trans_id",
      "order": "order_id", "loan": "loan_id", "card": "card_id"}
dups = []
for t, k in pk.items():
    try:
        d = q(f"SELECT COUNT(*) - COUNT(DISTINCT [{k}]) AS d FROM stg.[{t}]").iloc[0, 0]
        dups.append((t, k, int(d)))
    except Exception as e:
        dups.append((t, k, f"lỗi: {str(e)[:60]}"))
add("Trùng khóa chính (0 là tốt)", pd.DataFrame(dups, columns=["table", "key", "duplicates"]))

# 4. Khoảng ngày
add("Khoảng ngày", pd.concat([
    q(f"SELECT '{t}' AS tbl, MIN([date]) AS min_date, MAX([date]) AS max_date FROM stg.[{t}]")
    for t in ["trans", "loan", "account"]]))

# 5. Mồ côi khóa ngoại
add("Mồ côi khóa ngoại (0 là tốt)", q("""
SELECT 'loan -> account' AS chk, COUNT(*) AS orphans FROM stg.loan l
  LEFT JOIN stg.account a ON a.account_id = l.account_id WHERE a.account_id IS NULL
UNION ALL
SELECT 'trans -> account', COUNT(*) FROM stg.trans t
  LEFT JOIN stg.account a ON a.account_id = t.account_id WHERE a.account_id IS NULL"""))

# 6. Xem trước censoring: khoản vay chưa kết thúc tính đến 1999-01-01
add("loan: status và số khoản chưa kết thúc theo ngày (date + duration >= 1999-01-01)", q("""
SELECT status, COUNT(*) AS n,
  SUM(CASE WHEN DATEADD(month, TRY_CONVERT(int, duration), TRY_CONVERT(date, [date])) >= '1999-01-01'
           THEN 1 ELSE 0 END) AS unfinished_by_date
FROM stg.loan GROUP BY status ORDER BY status"""))

(OUT / "data_quality.md").write_text("\n".join(parts), encoding="utf-8")
print("\n".join(parts))
