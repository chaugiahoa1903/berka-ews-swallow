"""Baseline luat: canh bao khi tung co so du am (hist_bal_min < 0). Chi danh gia tren test.
Chay: python src\baseline_rule.py
"""
import numpy as np
import pandas as pd

df = pd.read_csv("data/processed/model_rows.csv")
elig = (df["loan_year"] <= 1997) & (df["label_ambiguous"].astype(int) == 0) & (df["is_pre_event"] == 1)
d = df[elig & df["loan_year"].isin([1996, 1997])].copy()
d["alert"] = d["hist_bal_min"] < 0

# Thong tin cap khoan vay
first_alert = d[d["alert"]].groupby("loan_id")["loan_age_k"].min()
L = d.groupby("loan_id").agg(year=("loan_year", "first"), event_k=("event_k", "first")).reset_index()
L["alert_k"] = L["loan_id"].map(first_alert)
L["pos"] = L["event_k"].notna()
L["alerted"] = L["alert_k"].notna()
L["lead"] = L["event_k"] - L["alert_k"]          # chi co nghia voi khoan duong da duoc canh bao


def metrics(pos, alerted, lead):
    recall = alerted[pos].mean() if pos.any() else np.nan
    fpr = alerted[~pos].mean() if (~pos).any() else np.nan
    n_alert = alerted.sum()
    prec = (alerted & pos).sum() / n_alert if n_alert else np.nan
    ld = lead[pos & alerted]
    med_lead = np.median(ld) if len(ld) else np.nan
    return np.array([recall, fpr, prec, med_lead], dtype=float)


def boot(Ls, B, seed=20261118):
    pos, al, ld = Ls["pos"].to_numpy(), Ls["alerted"].to_numpy(), Ls["lead"].to_numpy()
    rng = np.random.default_rng(seed)
    n = len(Ls)
    out = np.empty((B, 4))
    for b in range(B):
        i = rng.integers(0, n, n)                  # resample theo KHOAN VAY, khong theo dong
        out[b] = metrics(pos[i], al[i], ld[i])
    return np.nanpercentile(out, [2.5, 97.5], axis=0)


names = ["recall", "false_alarm_rate", "precision", "median_lead_m"]
for label, sub in [("fold1 test (1996)", L[L.year == 1996]),
                   ("fold2 test (1997)", L[L.year == 1997]),
                   ("gop 1996+1997", L)]:
    pos, al, ld = sub["pos"].to_numpy(), sub["alerted"].to_numpy(), sub["lead"].to_numpy()
    est = metrics(pos, al, ld)
    ci2000 = boot(sub, 2000)
    ci1000 = boot(sub, 1000)
    print(f"\n== {label}: {len(sub)} khoan, {int(pos.sum())} duong, {int((~pos).sum())} am ==")
    print(f"  duoc canh bao: {int((al & pos).sum())}/{int(pos.sum())} duong, "
          f"{int((al & ~pos).sum())}/{int((~pos).sum())} am")
    for j, nm in enumerate(names):
        print(f"  {nm:18s} {est[j]:.3f}  CI95(B=2000) [{ci2000[0, j]:.3f}, {ci2000[1, j]:.3f}]"
              f"  | B=1000 [{ci1000[0, j]:.3f}, {ci1000[1, j]:.3f}]")
