"""Bao cao canh bao cua mot thang replay (chi doc mart.alerts); in 1 dong JSON.
Chay: python src\alert_report.py --month 1997-06 [--top 10] [--top-cont 5]
Moi = chua tung co alert=1 o cac thang truoc; dang tiep dien = da tung bao dong truoc do.
Chi dung dung neu cac thang truoc da duoc chay that (khong --dry) va nam trong mart.alerts.
"""
import argparse
import json
import os
import pyodbc

ap = argparse.ArgumentParser()
ap.add_argument("--month", required=True, help="YYYY-MM")
ap.add_argument("--top", type=int, default=10, help="so khoan moi liet ke toi da")
ap.add_argument("--top-cont", type=int, default=5, help="so khoan dang tiep dien liet ke toi da")
a = ap.parse_args()

conn = pyodbc.connect(
    f"DRIVER={{ODBC Driver 18 for SQL Server}};SERVER={os.environ.get('SWALLOW_SQL_SERVER', 'localhost')};"
    "DATABASE=Swallow;Trusted_Connection=yes;TrustServerCertificate=yes;")
cur = conn.cursor()

cur.execute("SELECT COUNT(*) FROM mart.alerts WHERE replay_month = ?", a.month)
n_scored = int(cur.fetchone()[0])
cur.execute("SELECT COUNT(DISTINCT replay_month) FROM mart.alerts WHERE replay_month < ?", a.month)
prior_months = int(cur.fetchone()[0])

cur.execute("""
SELECT a.loan_id, a.score, a.top_drivers,
       (SELECT MIN(p.replay_month) FROM mart.alerts p
        WHERE p.loan_id = a.loan_id AND p.alert = 1
          AND p.replay_month < a.replay_month) AS first_alert_month
FROM mart.alerts a
WHERE a.replay_month = ? AND a.alert = 1
ORDER BY a.score DESC, a.loan_id""", a.month)
rows = cur.fetchall()
conn.close()

new = [r for r in rows if r.first_alert_month is None]
cont = [r for r in rows if r.first_alert_month is not None]
result = {
    "replay_month": a.month,
    "found": n_scored > 0,
    "n_scored": n_scored,
    "n_alerts": len(rows),
    "n_new": len(new),
    "n_continuing": len(cont),
    "prior_months_in_table": prior_months,
    "new_alerts": [{"loan_id": int(r.loan_id), "score": round(float(r.score), 4),
                    "top_drivers": r.top_drivers} for r in new[:a.top]],
    "continuing_alerts": [{"loan_id": int(r.loan_id), "score": round(float(r.score), 4),
                           "first_alert_month": r.first_alert_month,
                           "top_drivers": r.top_drivers} for r in cont[:a.top_cont]],
}
print(json.dumps(result))
