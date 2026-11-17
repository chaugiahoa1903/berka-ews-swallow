"""Logistic regression L2 (bo dac trung 'core', khong nhan khau hoc).
Chay: python src\model_lr.py          (bo core)
      python src\model_lr.py demo     (core + is_female + age_at_loan_y)
"""
import sys
import warnings
import numpy as np
import pandas as pd
from scipy.stats import beta
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import roc_auc_score

warnings.filterwarnings("ignore")
USE_DEMO = "demo" in sys.argv
SEED = 20261118
B_CI = 2000          # bootstrap cho lead time, AUC
B_COEF = 1000        # bootstrap huan luyen lai cho he so
FA_BUDGET = 0.01     # gia dinh chi phi: toi da 1% khoan am bi bao nham (o validation)
CS = np.logspace(-4, 2, 13); SCORES = []

df = pd.read_csv("data/processed/model_rows.csv")
df["lm_debit_ratio"] = df["lm_debit_ratio"].fillna(1.0)       # 0/0 -> khong lech
df["ever_neg"] = (df["hist_bal_min"] < 0).astype(int)

FEATURES = ["ever_neg", "hist_bal_avg", "hist_neg_share", "hist_penalty_cnt",
            "lm_credit_ratio", "lm_debit_ratio", "loan_burden",
            "loan_amount", "loan_duration", "loan_age_k"]
if USE_DEMO:
    FEATURES += ["is_female", "age_at_loan_y"]

elig = (df["loan_year"] <= 1997) & (df["label_ambiguous"].astype(int) == 0) & (df["is_pre_event"] == 1)
D = df[elig].reset_index(drop=True)
D["y"] = D["event_k"].notna().astype(int)        # dong truoc moc cua khoan co moc = 1
assert D[FEATURES].isna().sum().sum() == 0, "con null trong dac trung"
print("Bo dac trung:", FEATURES)
print("Dong du dieu kien:", len(D), "| khoan:", D["loan_id"].nunique())


def fit_lr(X, y, C):
    sc = StandardScaler().fit(X)
    m = LogisticRegression(C=C, max_iter=5000).fit(sc.transform(X), y)   # L2 la mac dinh
    return sc, m


def predict(sc, m, X):
    return m.predict_proba(sc.transform(X))[:, 1]


def row_loss(y, p):
    p = np.clip(p, 1e-12, 1 - 1e-12)
    return -(y * np.log(p) + (1 - y) * np.log(1 - p))


def cluster_mean_se(loss, ids):
    s = pd.DataFrame({"l": loss, "id": ids}).groupby("id")["l"].agg(["sum", "count"])
    N = s["count"].sum()
    m = s["sum"].sum() / N
    resid = s["sum"] - m * s["count"]
    L = len(s)
    se = np.sqrt(L / (L - 1) * (resid ** 2).sum()) / N
    return m, se


def val_scores_for(C, val_years):
    parts = []
    for vy in val_years:
        tr, va = D[D["loan_year"] < vy], D[D["loan_year"] == vy]
        sc, m = fit_lr(tr[FEATURES].to_numpy(), tr["y"].to_numpy(), C)
        parts.append(pd.DataFrame({"loan_id": va["loan_id"].to_numpy(), "y": va["y"].to_numpy(),
                                   "score": predict(sc, m, va[FEATURES].to_numpy())}))
    return pd.concat(parts, ignore_index=True)


def select_C(train_years):
    val_years = [y for y in train_years if y >= 1995]
    rows = []
    for C in CS:
        v = val_scores_for(C, val_years)
        m, se = cluster_mean_se(row_loss(v["y"].to_numpy(), v["score"].to_numpy()), v["loan_id"].to_numpy())
        rows.append((C, m, se))
    tab = pd.DataFrame(rows, columns=["C", "val_logloss", "se"])
    best = tab["val_logloss"].idxmin()
    limit = tab.loc[best, "val_logloss"] + tab.loc[best, "se"]
    ok = tab[tab["val_logloss"] <= limit]
    C_star = ok["C"].min()                       # 1-SE: regularization manh nhat con trong 1 SE
    tab["chon"] = np.where(tab["C"] == C_star, "<== 1-SE", np.where(tab.index == best, "min", ""))
    return C_star, tab, val_scores_for(C_star, val_years), val_years


def pick_threshold(v):
    mx = v.groupby("loan_id").agg(y=("y", "max"), s=("score", "max"))
    neg = np.sort(mx.loc[mx["y"] == 0, "s"].to_numpy())[::-1]
    allowed = int(np.floor(FA_BUDGET * len(neg)))
    return neg[allowed], len(neg), allowed        # canh bao khi score > t


def cp(x, n, a=0.05):                             # Clopper-Pearson chinh xac
    lo = 0.0 if x == 0 else beta.ppf(a / 2, x, n - x + 1)
    hi = 1.0 if x == n else beta.ppf(1 - a / 2, x + 1, n - x)
    return lo, hi


def summarize(L, name, label):
    pos = L["pos"].to_numpy()
    al = L[f"{name}_k"].notna().to_numpy()
    P, N = int(pos.sum()), int((~pos).sum())
    tp, fp = int((al & pos).sum()), int((al & ~pos).sum())
    r, f = cp(tp, P), cp(fp, N)
    s = (f"  [{label}] recall {tp}/{P}={tp/P:.3f} CI[{r[0]:.3f},{r[1]:.3f}] | "
         f"bao nham {fp}/{N}={fp/N:.3f} CI[{f[0]:.3f},{f[1]:.3f}]")
    if tp + fp > 0:
        p = cp(tp, tp + fp)
        s += f" | precision {tp/(tp+fp):.3f} CI[{p[0]:.3f},{p[1]:.3f}]"
    print(s)
    lead = (L["event_k"] - L[f"{name}_k"])[pos & al].to_numpy()
    avail = (L["event_k"] - 1)[pos].to_numpy()
    if len(lead):
        rng = np.random.default_rng(SEED)
        meds = [np.median(rng.choice(lead, len(lead))) for _ in range(B_CI)]
        lo, hi = np.percentile(meds, [2.5, 97.5])
        print(f"      lead median {np.median(lead):.1f} thang CI[{lo:.1f},{hi:.1f}] "
              f"(chi tren khoan duoc phat hien) | lead toi da kha dung (median, moi khoan duong) {np.median(avail):.1f}")


def added_value(L):
    pos = L["pos"].map({True: "duong", False: "am"})
    r = L["rule_k"].notna().map({True: "luat_canh_bao", False: "luat_khong"})
    m = L["model_k"].notna().map({True: "model_canh_bao", False: "model_khong"})
    print(pd.crosstab([pos, r], m).to_string())


def row_auc_boot(te):
    te = te.reset_index(drop=True)
    y, s = te["y"].to_numpy(), te["score"].to_numpy()
    groups = [g.index.to_numpy() for _, g in te.groupby("loan_id")]
    auc = roc_auc_score(y, s)
    rng = np.random.default_rng(SEED)
    vals = []
    for _ in range(B_CI):
        idx = np.concatenate([groups[i] for i in rng.integers(0, len(groups), len(groups))])
        if 0 < y[idx].sum() < len(idx):
            vals.append(roc_auc_score(y[idx], s[idx]))
    return auc, *np.percentile(vals, [2.5, 97.5])


def coef_boot(tr, C, full_coef):
    tr = tr.reset_index(drop=True)
    X, y = tr[FEATURES].to_numpy(), tr["y"].to_numpy()
    groups = [g.index.to_numpy() for _, g in tr.groupby("loan_id")]
    rng = np.random.default_rng(SEED)
    out = []
    for _ in range(B_COEF):
        idx = np.concatenate([groups[i] for i in rng.integers(0, len(groups), len(groups))])
        if y[idx].sum() == 0:
            continue
        out.append(fit_lr(X[idx], y[idx], C)[1].coef_[0])
    out = np.array(out)
    lo, hi = np.percentile(out, [2.5, 97.5], axis=0)
    same = (np.sign(out) == np.sign(full_coef)).mean(axis=0)
    return pd.DataFrame({"feature": FEATURES, "coef_std": full_coef, "CI_lo": lo, "CI_hi": hi, "same_sign": same})


def run_fold(tag, train_years, test_year):
    print("\n" + "=" * 72)
    print(f"{tag}: train {train_years[0]}-{train_years[-1]} -> test {test_year}")
    C_star, tab, vs, val_years = select_C(train_years)
    print(f"Chon L2 tren validation {val_years} (forward-chaining, log-loss, 1-SE):")
    print(tab.to_string(index=False, float_format=lambda x: f"{x:.5g}"))
    t, n_neg_val, allowed = pick_threshold(vs)
    print(f"C chon = {C_star:g} | nguong canh bao t = {t:.4f} "
          f"({n_neg_val} khoan am o validation, cho phep {allowed} bao nham)")
    tr = D[D["loan_year"].isin(train_years)]
    te = D[D["loan_year"] == test_year].copy()
    sc, m = fit_lr(tr[FEATURES].to_numpy(), tr["y"].to_numpy(), C_star)
    te["score"] = predict(sc, m, te[FEATURES].to_numpy()); SCORES.append(te[["loan_id", "loan_year", "loan_age_k", "event_k", "y", "ever_neg", "hist_bal_min", "score"]].copy())
    auc, lo, hi = row_auc_boot(te)
    print(f"AUC cap dong (test): {auc:.3f} CI bootstrap theo khoan [{lo:.3f},{hi:.3f}]")
    print("He so chuan hoa (bootstrap huan luyen lai theo khoan vay):")
    print(coef_boot(tr, C_star, m.coef_[0]).to_string(index=False, float_format=lambda x: f"{x:.3f}"))

    g = te.groupby("loan_id")
    L = g.agg(year=("loan_year", "first"), event_k=("event_k", "first")).reset_index()
    for name, mask in [("model", te["score"] > t), ("rule", te["hist_bal_min"] < 0)]:
        L[f"{name}_k"] = L["loan_id"].map(te[mask].groupby("loan_id")["loan_age_k"].min())
    L["pos"] = L["event_k"].notna()
    print(f"\nCap khoan vay (test {test_year}):")
    summarize(L, "model", "model")
    summarize(L, "rule", "luat ")
    print("Doi chieu luat vs model:")
    added_value(L)
    return L


L1 = run_fold("FOLD 1", [1993, 1994, 1995], 1996)
L2 = run_fold("FOLD 2", [1993, 1994, 1995, 1996], 1997)
Lp = pd.concat([L1, L2], ignore_index=True)
print("\n" + "=" * 72)
print(f"GOP test 1996+1997: {len(Lp)} khoan")
summarize(Lp, "model", "model")
summarize(Lp, "rule", "luat ")
print("Doi chieu luat vs model:")
added_value(Lp)

pd.concat(SCORES).to_csv("data/processed/test_scores_" + ("demo" if USE_DEMO else "core") + ".csv", index=False)
