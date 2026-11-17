"""Cham diem mot thang replay bang model da luu; ghi mart.alerts va mart.run_log; in 1 dong JSON.
Chi cham cac khoan giai ngan SAU thoi ky huan luyen (replay ngoai mau).
Chay: python src\score_month.py --month 1997-06 [--dry]
"""
import argparse
import datetime
import json
import os
import sys
import numpy as np
import pandas as pd
import pyodbc
import joblib
import lr_lib as L
import warnings
warnings.filterwarnings("ignore")

ap = argparse.ArgumentParser()
ap.add_argument("--month", required=True, help="YYYY-MM")
ap.add_argument("--model", default="models/lr_core_train1993_96.joblib")
ap.add_argument("--dry", action="store_true", help="khong ghi vao SQL Server")
a = ap.parse_args()

y, mth = map(int, a.month.split("-"))
start = datetime.date(y, mth, 1)
end = datetime.date(y + (mth == 12), mth % 12 + 1, 1)

bundle = joblib.load(a.model)
feats, scaler, model, t = bundle["features"], bundle["scaler"], bundle["model"], bundle["threshold"]
assert feats == L.FEATURES, "bo dac trung cua model khac lr_lib"
orig_year = max(bundle["train_years"]) + 1            # chi cham khoan giai ngan nam nay

conn = pyodbc.connect(
    f"DRIVER={{ODBC Driver 18 for SQL Server}};SERVER={os.environ.get('SWALLOW_SQL_SERVER', 'localhost')};"
    "DATABASE=Swallow;Trusted_Connection=yes;TrustServerCertificate=yes;")

# Chi doc cot dac trung + dieu kien hop le tai moc as-of (khong doc nhan)
sql = """
SELECT loan_id, account_id, as_of_date, loan_age_k, hist_bal_min, hist_bal_avg, hist_neg_share,
       hist_penalty_cnt, lm_credit_ratio, lm_debit_ratio, loan_burden, loan_amount, loan_duration
FROM clean.asof_features
WHERE as_of_date >= ? AND as_of_date < ? AND is_pre_event = 1 AND loan_year = ?
"""
df = pd.read_sql(sql, conn, params=[str(start), str(end), orig_year])

# ---------- kiem tra chat luong du lieu ----------
msgs = []
if len(df) == 0:
    msgs.append("khong co dong nao de cham diem")
if df.duplicated("loan_id").any():
    msgs.append("loan_id bi trung trong thang")
must = [c for c in df.columns if c not in ("lm_debit_ratio", "as_of_date")]
num = df[must].apply(pd.to_numeric, errors="coerce")
if num.isna().any().any():
    msgs.append("null/khong phai so o: " + ",".join(num.columns[num.isna().any()]))
elif not np.isfinite(num.to_numpy(dtype=float)).all():
    msgs.append("co gia tri vo han o dac trung")
if len(df) and pd.to_datetime(df["as_of_date"]).max() > pd.Timestamp("1998-12-31"):
    msgs.append("as_of_date vuot 1998-12-31")
n_imputed = int(df["lm_debit_ratio"].isna().sum()) if len(df) else 0
dq_ok = not msgs

n_alerts, max_score = 0, None
X = None
if dq_ok:
    X = L.prepare(df)
    X["score"] = L.predict(scaler, model, X[feats].to_numpy())
    X["alert"] = (X["score"] > t).astype(int)
    contrib = scaler.transform(X[feats].to_numpy()) * model.coef_[0]
    names = np.array(feats)
    order = np.argsort(-contrib, axis=1)[:, :3]
    X["top_drivers"] = ["; ".join(f"{names[j]}({contrib[i, j]:+.2f})" for j in order[i] if contrib[i, j] > 0)
                        for i in range(len(X))]
    n_alerts, max_score = int(X["alert"].sum()), float(X["score"].max())

result = {"replay_month": a.month, "originated_year": orig_year, "n_scored": int(len(df)),
          "n_alerts": n_alerts, "dq_ok": bool(dq_ok), "dq_message": "; ".join(msgs),
          "threshold": round(float(t), 4), "max_score": None if max_score is None else round(max_score, 4),
          "n_imputed_lm_debit_ratio": n_imputed, "dry_run": bool(a.dry)}

# ---------- ghi SQL Server ----------
if not a.dry:
    cur = conn.cursor()
    cur.execute("IF SCHEMA_ID('mart') IS NULL EXEC('CREATE SCHEMA mart')")
    cur.execute("""
    IF OBJECT_ID('mart.alerts') IS NULL CREATE TABLE mart.alerts (
        replay_month CHAR(7) NOT NULL, loan_id INT NOT NULL, account_id INT NOT NULL,
        as_of_date DATE NOT NULL, loan_age_k INT NOT NULL, score FLOAT NOT NULL, threshold FLOAT NOT NULL,
        alert BIT NOT NULL, ever_neg BIT NOT NULL, hist_bal_min FLOAT, hist_bal_avg FLOAT,
        hist_neg_share FLOAT, hist_penalty_cnt FLOAT, loan_burden FLOAT,
        top_drivers NVARCHAR(200), scored_at DATETIME2 NOT NULL, model_file NVARCHAR(200) NOT NULL,
        CONSTRAINT pk_alerts PRIMARY KEY (replay_month, loan_id))""")
    cur.execute("""
    IF OBJECT_ID('mart.run_log') IS NULL CREATE TABLE mart.run_log (
        run_id INT IDENTITY PRIMARY KEY, run_ts DATETIME2 NOT NULL, replay_month CHAR(7) NOT NULL,
        n_scored INT NOT NULL, n_alerts INT NOT NULL, dq_ok BIT NOT NULL, dq_message NVARCHAR(400),
        model_file NVARCHAR(200) NOT NULL, threshold FLOAT NOT NULL)""")
    now = datetime.datetime.now()
    if dq_ok:
        cur.execute("DELETE FROM mart.alerts WHERE replay_month = ?", a.month)   # chay lai khong bi nhan doi
        rows = [(a.month, int(r.loan_id), int(r.account_id), r.as_of_date, int(r.loan_age_k), float(r.score),
                 float(t), int(r.alert), int(r.ever_neg), float(r.hist_bal_min), float(r.hist_bal_avg),
                 float(r.hist_neg_share), float(r.hist_penalty_cnt), float(r.loan_burden), r.top_drivers,
                 now, os.path.basename(a.model)) for r in X.itertuples()]
        cur.fast_executemany = True
        cur.executemany("""INSERT INTO mart.alerts (replay_month, loan_id, account_id, as_of_date, loan_age_k,
            score, threshold, alert, ever_neg, hist_bal_min, hist_bal_avg, hist_neg_share, hist_penalty_cnt,
            loan_burden, top_drivers, scored_at, model_file) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", rows)
    cur.execute("""INSERT INTO mart.run_log (run_ts, replay_month, n_scored, n_alerts, dq_ok, dq_message, model_file, threshold)
                   VALUES (?,?,?,?,?,?,?,?)""", now, a.month, len(df), n_alerts, int(dq_ok),
                "; ".join(msgs)[:400], os.path.basename(a.model), float(t))
    conn.commit()
conn.close()

if dq_ok and len(X):
    print(X.loc[X["alert"] == 1, ["loan_id", "loan_age_k", "score", "ever_neg", "top_drivers"]]
          .sort_values("score", ascending=False).head(5).to_string(index=False), file=sys.stderr)
print(json.dumps(result, ensure_ascii=False))          # dong cuoi cung cho n8n doc

