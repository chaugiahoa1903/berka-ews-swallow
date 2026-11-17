"""Kiem tra bo du lieu truoc khi modeling (chi doc, khong huan luyen).
Chay: python src\check_dataset.py
"""
import pandas as pd

df = pd.read_csv("data/processed/model_rows.csv")

print("== 1) cac dong lm_debit_ratio bi null ==")
cols = ["loan_id", "loan_age_k", "as_of_date", "hist_debit_avg_m",
        "lm_debit_sum", "lm_n_trans", "hist_n_trans"]
print(df.loc[df["lm_debit_ratio"].isna(), cols].to_string(index=False))

print("\n== 2) is_pre_event so voi vi tri dong tuong doi voi event_k ==")
has_ev = df["event_k"].notna()
rel = pd.Series("no_event", index=df.index)
rel[has_ev & (df["loan_age_k"] < df["event_k"])] = "k<event_k"
rel[has_ev & (df["loan_age_k"] == df["event_k"])] = "k=event_k"
rel[has_ev & (df["loan_age_k"] > df["event_k"])] = "k>event_k"
print(pd.crosstab(rel, df["is_pre_event"]))

print("\n== 3) khoan vay label_ambiguous theo nam ==")
amb = df.groupby("loan_id").agg(loan_year=("loan_year", "first"),
                                amb=("label_ambiguous", "max"))
print(amb.groupby("loan_year")["amb"].agg(["size", "sum"]).rename(
    columns={"size": "n_loans", "sum": "n_ambiguous"}))

# Dong du dieu kien: nam <= 1997, khong mo ho, chi lay dong truoc moc (hoac khong co moc)
elig = (df["loan_year"] <= 1997) & (df["label_ambiguous"].astype(int) == 0) \
       & rel.isin(["no_event", "k<event_k"])
y = (rel == "k<event_k").astype(int)

print("\n== 4) so luong theo fold (nhan chinh: dong truoc moc cua khoan co moc = 1) ==")
folds = [("fold1", range(1993, 1996), 1996), ("fold2", range(1993, 1997), 1997)]
for name, tr_years, te_year in folds:
    tr = elig & df["loan_year"].isin(list(tr_years))
    te = elig & (df["loan_year"] == te_year)
    for tag, m in (("train", tr), ("test ", te)):
        d = df[m]
        pos_loans = d.loc[y[m] == 1, "loan_id"].nunique()
        print(f"{name} {tag}: rows={len(d):5d}  pos_rows={int(y[m].sum()):4d}  "
              f"loans={d['loan_id'].nunique():3d}  pos_loans={pos_loans:3d}  "
              f"pos_row_rate={y[m].mean():.3f}")
