"""Xuat bang dac trung as-of + nhan khau hoc tu SQL Server ra CSV de modeling.
Chay: python src\export_dataset.py
"""
import os
import warnings
import pandas as pd
import pyodbc

warnings.filterwarnings("ignore", message=".*pandas only supports SQLAlchemy.*")

SERVER = os.environ.get("SWALLOW_SQL_SERVER", "localhost")
conn = pyodbc.connect(
    f"DRIVER={{ODBC Driver 18 for SQL Server}};SERVER={SERVER};DATABASE=Swallow;"
    "Trusted_Connection=yes;TrustServerCertificate=yes;"
)

# Mot dong = (khoan vay, thang k) tai moc as-of; gan them gioi tinh va tuoi tai ngay vay
sql = """
SELECT f.*, d.gender, d.age_at_loan_y
FROM clean.asof_features f
JOIN clean.loan_demographics d ON d.loan_id = f.loan_id
"""
df = pd.read_sql(sql, conn)
conn.close()

df["is_female"] = (df["gender"] == "F").astype(int)

os.makedirs("data/processed", exist_ok=True)
out = "data/processed/model_rows.csv"
df.to_csv(out, index=False)

# --- kiem tra nhanh ---
print("shape:", df.shape, "(ky vong 13773 dong)")
print("so khoan vay:", df["loan_id"].nunique())
print("cot:", list(df.columns))
print("tong null theo cot (chi hien cot co null):")
nulls = df.isna().sum()
print(nulls[nulls > 0] if (nulls > 0).any() else "  khong co null")

per_loan = df.groupby("loan_id").agg(
    loan_year=("loan_year", "first"),
    is_bad=("is_bad", "first"),
    has_event=("event_k", lambda s: s.notna().any()),
)
print("\nkhoan vay theo nam giai ngan:")
print(per_loan.groupby("loan_year").agg(
    n_loans=("is_bad", "size"), n_bad=("is_bad", "sum"), n_with_event=("has_event", "sum")))
print("\nDa ghi:", out)
