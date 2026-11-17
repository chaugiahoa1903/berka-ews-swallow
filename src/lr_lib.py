"""Thu vien dung chung: logistic L2 bo 'core' (huan luyen + cham diem)."""
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

FEATURES = ["ever_neg", "hist_bal_avg", "hist_neg_share", "hist_penalty_cnt",
            "lm_credit_ratio", "lm_debit_ratio", "loan_burden",
            "loan_amount", "loan_duration", "loan_age_k"]
CS = np.logspace(-4, 2, 13)     # luoi log 1e-4..1e2, buoc nua bac
FA_BUDGET = 0.01                # gia dinh chi phi: toi da 1% khoan am bi bao nham (o validation)


def prepare(df):
    df = df.copy()
    df["lm_debit_ratio"] = df["lm_debit_ratio"].fillna(1.0)       # 0/0 -> khong lech
    df["ever_neg"] = (df["hist_bal_min"] < 0).astype(int)
    return df


def fit_lr(X, y, C):
    sc = StandardScaler().fit(X)
    return sc, LogisticRegression(C=C, max_iter=5000).fit(sc.transform(X), y)


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
    n = len(s)
    return m, np.sqrt(n / (n - 1) * (resid ** 2).sum()) / N


def val_scores(D, val_years, C):
    parts = []
    for vy in val_years:
        tr, va = D[D["loan_year"] < vy], D[D["loan_year"] == vy]
        sc, m = fit_lr(tr[FEATURES].to_numpy(), tr["y"].to_numpy(), C)
        parts.append(pd.DataFrame({"loan_id": va["loan_id"].to_numpy(), "y": va["y"].to_numpy(),
                                   "score": predict(sc, m, va[FEATURES].to_numpy())}))
    return pd.concat(parts, ignore_index=True)


def select_C(D, train_years):
    """Forward-chaining tren cac nam train (validation tu 1995), log-loss, quy tac 1-SE."""
    val_years = [y for y in train_years if y >= 1995]
    rows = []
    for C in CS:
        v = val_scores(D, val_years, C)
        m, se = cluster_mean_se(row_loss(v["y"].to_numpy(), v["score"].to_numpy()), v["loan_id"].to_numpy())
        rows.append((C, m, se))
    tab = pd.DataFrame(rows, columns=["C", "m", "se"])
    best = tab["m"].idxmin()
    limit = tab.loc[best, "m"] + tab.loc[best, "se"]
    C_star = tab.loc[tab["m"] <= limit, "C"].min()
    return C_star, val_scores(D, val_years, C_star)


def pick_threshold(v):
    """Canh bao khi score > t; t lay tu validation sao cho toi da FA_BUDGET khoan am bi bao nham."""
    mx = v.groupby("loan_id").agg(y=("y", "max"), s=("score", "max"))
    neg = np.sort(mx.loc[mx["y"] == 0, "s"].to_numpy())[::-1]
    return neg[int(np.floor(FA_BUDGET * len(neg)))]
