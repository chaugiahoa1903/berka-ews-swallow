"""Doi chung: loan_age_k don le, thang tai diem diem so lon nhat, bang danh doi tren khoan im lang.
Chay: python src\silent_group_check.py
"""
import numpy as np
import pandas as pd
from scipy.stats import beta
from sklearn.metrics import roc_auc_score

B, SEED = 2000, 20261118
S = pd.read_csv("data/processed/test_scores_core.csv")


def auc(d, col):
    if d["y"].nunique() < 2:
        return np.nan
    return roc_auc_score(d["y"], d[col])


def boot(df, stat):
    df = df.reset_index(drop=True)
    groups = [g.index.to_numpy() for _, g in df.groupby("loan_id")]
    rng = np.random.default_rng(SEED)
    est, vals = stat(df), []
    for _ in range(B):
        idx = np.concatenate([groups[i] for i in rng.integers(0, len(groups), len(groups))])
        v = stat(df.iloc[idx])
        if not np.isnan(v):
            vals.append(v)
    lo, hi = np.percentile(vals, [2.5, 97.5])
    return est, lo, hi


def cp(x, n, a=0.05):
    lo = 0.0 if x == 0 else beta.ppf(a / 2, x, n - x + 1)
    hi = 1.0 if x == n else beta.ppf(1 - a / 2, x + 1, n - x)
    return lo, hi


def show(label, r):
    print(f"  {label:48s} {r[0]:.3f}  CI95[{r[1]:.3f}, {r[2]:.3f}]")


tabs = []
for yr in (1996, 1997):
    d = S[S["loan_year"] == yr].copy()
    print("\n" + "=" * 70 + f"\nTEST {yr}")
    d0 = d[d["ever_neg"] == 0].copy()
    d0["neg_k"] = -d0["loan_age_k"]
    print("A) Dong chua tung am: AUC cua -loan_age_k DON LE so voi model")
    show("-loan_age_k don le", boot(d0, lambda x: auc(x, "neg_k")))
    show("model core", boot(d0, lambda x: auc(x, "score")))

    silent_ids = d.groupby("loan_id")["ever_neg"].max()
    silent_ids = silent_ids[silent_ids == 0].index
    ds = d[d["loan_id"].isin(silent_ids)]
    top = ds.loc[ds.groupby("loan_id")["score"].idxmax(), ["loan_id", "y", "loan_age_k", "score"]].copy()
    print(f"B) Khoan im lang: {len(top)}; diem lon nhat roi o k=1 cho "
          f"{(top['loan_age_k'] == 1).mean():.1%} khoan (duong: "
          f"{(top.loc[top['y'] == 1, 'loan_age_k'] == 1).mean():.1%}, am: "
          f"{(top.loc[top['y'] == 0, 'loan_age_k'] == 1).mean():.1%})")
    top["r"] = top["score"].rank(pct=True)          # thu hang trong tung fold
    tabs.append(top)

P = pd.concat(tabs, ignore_index=True)
pos = P.loc[P["y"] == 1, "r"].to_numpy()
neg = np.sort(P.loc[P["y"] == 0, "r"].to_numpy())[::-1]
print("\n" + "=" * 70)
print(f"C) Bang danh doi, khoan im lang gop: {len(pos)} duong, {len(neg)} am")
print("   muc bao nham | so am bi bao | so duong bat duoc | recall [CI95 chinh xac] | recall neu chon ngau nhien")
for f in (0.01, 0.02, 0.05, 0.10, 0.20):
    allowed = int(np.floor(f * len(neg)))
    thr = neg[allowed]
    tp, fp = int((pos > thr).sum()), int((neg > thr).sum())
    lo, hi = cp(tp, len(pos))
    print(f"   {f:11.0%} | {fp:12d} | {tp:2d}/{len(pos)}            | "
          f"{tp/len(pos):.2f} [{lo:.2f}, {hi:.2f}]   | {f:.2f}")
