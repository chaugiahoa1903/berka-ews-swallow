"""So sanh cap core vs demo, va gia tri cong them cua model trong nhom luat "im lang".
Chay: python src\compare_models.py
"""
import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score

B, SEED = 2000, 20261118
core = pd.read_csv("data/processed/test_scores_core.csv")
demo = pd.read_csv("data/processed/test_scores_demo.csv")
assert (core[["loan_id", "loan_age_k"]].to_numpy() == demo[["loan_id", "loan_age_k"]].to_numpy()).all()
S = core.rename(columns={"score": "score_core"})
S["score_demo"] = demo["score"].to_numpy()


def auc(d, col):
    if d["y"].nunique() < 2:
        return np.nan
    return roc_auc_score(d["y"], d[col])


def boot(df, stat):
    df = df.reset_index(drop=True)
    groups = [g.index.to_numpy() for _, g in df.groupby("loan_id")]
    rng = np.random.default_rng(SEED)
    est = stat(df)
    vals = []
    for _ in range(B):
        idx = np.concatenate([groups[i] for i in rng.integers(0, len(groups), len(groups))])
        v = stat(df.iloc[idx])
        if not np.isnan(v):
            vals.append(v)
    lo, hi = np.percentile(vals, [2.5, 97.5])
    return est, lo, hi


def show(label, r):
    print(f"  {label:50s} {r[0]:.3f}  CI95[{r[1]:.3f}, {r[2]:.3f}]")


loan_tabs = []
for yr in (1996, 1997):
    d = S[S["loan_year"] == yr]
    print("\n" + "=" * 70 + f"\nTEST {yr}: {d['loan_id'].nunique()} khoan, {len(d)} dong")
    print("1) AUC cap dong, so sanh cap (bootstrap theo khoan)")
    show("AUC core", boot(d, lambda x: auc(x, "score_core")))
    show("AUC demo", boot(d, lambda x: auc(x, "score_demo")))
    show("chenh lech demo - core (0 = khong khac)", boot(d, lambda x: auc(x, "score_demo") - auc(x, "score_core")))

    d0 = d[d["ever_neg"] == 0]
    print(f"2) Chi dong chua tung am: {len(d0)} dong, {int(d0['y'].sum())} dong duong, "
          f"{d0.loc[d0['y'] == 1, 'loan_id'].nunique()} khoan duong (luat = 0.5 theo dinh nghia)")
    show("AUC core trong nhom chua tung am", boot(d0, lambda x: auc(x, "score_core")))
    show("AUC demo trong nhom chua tung am", boot(d0, lambda x: auc(x, "score_demo")))

    g = d.groupby("loan_id")
    L = pd.DataFrame({"loan_id": g["y"].max().index, "year": yr, "y": g["y"].max().to_numpy(),
                      "silent": (g["ever_neg"].max() == 0).to_numpy(),
                      "max_core": g["score_core"].max().to_numpy(),
                      "max_demo": g["score_demo"].max().to_numpy()})
    Ls = L[L["silent"]].copy()
    print(f"3) Cap khoan vay, chi khoan luat im lang: {len(Ls)} khoan, "
          f"{int(Ls['y'].sum())} duong, {int((1 - Ls['y']).sum())} am (diem lon nhat cua khoan)")
    show("AUC core (khoan im lang)", boot(Ls, lambda x: auc(x, "max_core")))
    show("AUC demo (khoan im lang)", boot(Ls, lambda x: auc(x, "max_demo")))
    Ls["r_core"] = Ls["max_core"].rank(pct=True)
    Ls["r_demo"] = Ls["max_demo"].rank(pct=True)
    loan_tabs.append(Ls)

P = pd.concat(loan_tabs, ignore_index=True)
print("\n" + "=" * 70 + f"\nGOP 1996+1997, khoan im lang: {len(P)} khoan, "
      f"{int(P['y'].sum())} duong, {int((1 - P['y']).sum())} am (thu hang phan tram trong tung fold)")
show("AUC core", boot(P, lambda x: auc(x, "r_core")))
show("AUC demo", boot(P, lambda x: auc(x, "r_demo")))
