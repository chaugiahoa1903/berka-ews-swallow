"""Kiem tra do nhay: nhan/mo c/ tap mau khac nhau. Chay lai toan bo quy trinh cho tung bien the.
Chay: python src\sensitivity.py
"""
import os
import warnings
import numpy as np
import pandas as pd
import pyodbc
from scipy.stats import beta
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

warnings.filterwarnings("ignore")
FEATURES = ["ever_neg", "hist_bal_avg", "hist_neg_share", "hist_penalty_cnt",
            "lm_credit_ratio", "lm_debit_ratio", "loan_burden",
            "loan_amount", "loan_duration", "loan_age_k"]
CS = np.logspace(-4, 2, 13)
FA_BUDGET = 0.01

# ---------- nap du lieu ----------
conn = pyodbc.connect(
    f"DRIVER={{ODBC Driver 18 for SQL Server}};SERVER={os.environ.get('SWALLOW_SQL_SERVER', 'localhost')};"
    "DATABASE=Swallow;Trusted_Connection=yes;TrustServerCertificate=yes;")
pay = pd.read_sql("SELECT loan_id, k, paid_cum FROM clean.loan_month_payment", conn)
st = pd.read_sql("SELECT loan_id, status FROM clean.loan", conn)
conn.close()

short = pay["k"] - pay["paid_cum"]
ev2 = pay[short >= 2].groupby("loan_id")["k"].min()
ev1 = pay[short >= 1].groupby("loan_id")["k"].min()

df = pd.read_csv("data/processed/model_rows.csv")
df["lm_debit_ratio"] = df["lm_debit_ratio"].fillna(1.0)
df["ever_neg"] = (df["hist_bal_min"] < 0).astype(int)
df["as_of_date"] = pd.to_datetime(df["as_of_date"])
df = df.merge(st, on="loan_id", how="left")

# kiem chung toan ven: moc >= 2 tinh lai phai khop event_k da dung
a = df.groupby("loan_id")["event_k"].first()
b = ev2.reindex(a.index)
assert (a.fillna(-1) == b.fillna(-1)).all(), "event_k KHONG khop voi tinh lai tu loan_month_payment"
print("Kiem chung: event_k (>=2) khop tinh lai tu loan_month_payment: OK")

df["event_k1"] = df["loan_id"].map(ev1)
ed = df[df["loan_age_k"] == df["event_k"]].set_index("loan_id")["as_of_date"]
df["event_date"] = df["loan_id"].map(ed)
n_lost = df.loc[(df["event_k1"] == 1) & (df["loan_year"] <= 1997), "loan_id"].nunique()
print(f"V1: {n_lost} khoan (<=1997) co moc 'thieu>=1' ngay k=1 -> khong con dong truoc moc, khong the canh bao")


# ---------- ham ----------
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
    L = len(s)
    return m, np.sqrt(L / (L - 1) * (resid ** 2).sum()) / N


def cp(x, n, a=0.05):
    lo = 0.0 if x == 0 else beta.ppf(a / 2, x, n - x + 1)
    hi = 1.0 if x == n else beta.ppf(1 - a / 2, x + 1, n - x)
    return lo, hi


def cut_for(year):
    return pd.Timestamp(year=year, month=12, day=31)


def build(ev_col, keep=None):
    d = df.copy()
    ev = d[ev_col]
    amb = (d["is_bad"] == 1) & ev.isna()               # khoan xau khong co moc
    pre = ev.isna() | (d["loan_age_k"] < ev)           # khong co moc, hoac dong truoc moc
    m = (d["loan_year"] <= 1997) & (~amb) & pre
    if keep is not None:
        m &= keep(d)
    D = d[m].reset_index(drop=True)
    D["ev"] = D[ev_col]
    D["y"] = D["ev"].notna().astype(int)
    return D


def train_rows(tr, mode, cut):
    return tr[tr["as_of_date"] <= cut] if mode == "strict" else tr


def train_labels(tr, mode, H, cut):
    if mode == "primary":
        return tr["y"].to_numpy()
    if mode == "H":
        return (tr["ev"].notna() & ((tr["ev"] - tr["loan_age_k"]) <= H)).astype(int).to_numpy()
    if mode == "strict":                                # chi biet mốc da xay ra den ngay cat
        return (tr["ev"].notna() & (tr["event_date"] <= cut)).astype(int).to_numpy()


def select_C(D, train_years, mode, H):
    val_years = [y for y in train_years if y >= 1995]

    def val_scores(C):
        parts = []
        for vy in val_years:
            va = D[D["loan_year"] == vy]
            if va.empty:
                continue
            cut = cut_for(vy - 1)
            tr = train_rows(D[D["loan_year"] < vy], mode, cut)
            ytr = train_labels(tr, mode, H, cut)
            if len(np.unique(ytr)) < 2:
                p = np.full(len(va), ytr.mean() if len(ytr) else 0.0)
            else:
                sc, m = fit_lr(tr[FEATURES].to_numpy(), ytr, C)
                p = predict(sc, m, va[FEATURES].to_numpy())
            parts.append(pd.DataFrame({"loan_id": va["loan_id"].to_numpy(), "y": va["y"].to_numpy(), "score": p}))
        return pd.concat(parts, ignore_index=True)

    rows = []
    for C in CS:
        v = val_scores(C)
        m, se = cluster_mean_se(row_loss(v["y"].to_numpy(), v["score"].to_numpy()), v["loan_id"].to_numpy())
        rows.append((C, m, se))
    tab = pd.DataFrame(rows, columns=["C", "m", "se"])
    best = tab["m"].idxmin()
    limit = tab.loc[best, "m"] + tab.loc[best, "se"]
    C_star = tab.loc[tab["m"] <= limit, "C"].min()      # 1-SE
    return C_star, val_scores(C_star)


def pick_threshold(v):
    mx = v.groupby("loan_id").agg(y=("y", "max"), s=("score", "max"))
    neg = np.sort(mx.loc[mx["y"] == 0, "s"].to_numpy())[::-1]
    allowed = int(np.floor(FA_BUDGET * len(neg)))
    return neg[allowed]


def run_variant(ev_col="event_k", keep=None, mode="primary", H=None):
    D = build(ev_col, keep)
    Ls, Cs = [], []
    for train_years, test_year in [([1993, 1994, 1995], 1996), ([1993, 1994, 1995, 1996], 1997)]:
        C_star, vs = select_C(D, train_years, mode, H)
        t = pick_threshold(vs)
        cut = cut_for(train_years[-1])
        tr = train_rows(D[D["loan_year"].isin(train_years)], mode, cut)
        ytr = train_labels(tr, mode, H, cut)
        te = D[D["loan_year"] == test_year].copy()
        if len(np.unique(ytr)) < 2:
            te["score"] = ytr.mean()
        else:
            sc, m = fit_lr(tr[FEATURES].to_numpy(), ytr, C_star)
            te["score"] = predict(sc, m, te[FEATURES].to_numpy())
        L = te.groupby("loan_id").agg(ev=("ev", "first")).reset_index()
        for nm, mask in [("model", te["score"] > t), ("rule", te["hist_bal_min"] < 0)]:
            L[nm + "_k"] = L["loan_id"].map(te[mask].groupby("loan_id")["loan_age_k"].min())
        L["pos"] = L["ev"].notna()
        Ls.append(L)
        Cs.append(C_star)
    return pd.concat(Ls, ignore_index=True), Cs, D


def fmt(tp, P):
    lo, hi = cp(tp, P)
    return f"{tp:2d}/{P:2d} [{lo:.2f},{hi:.2f}]"


variants = [
    ("V0 chinh (tai hien)",       dict()),
    ("V1 moc thieu>=1",           dict(ev_col="event_k1")),
    ("V2 chi A/B (ket thuc)",     dict(keep=lambda d: d["status"].isin(["A", "B"]))),
    ("V3 loai chu <18 tuoi",      dict(keep=lambda d: d["age_at_loan_y"] >= 18)),
    ("V4 nhan train H=2",         dict(mode="H", H=2)),
    ("V5 nhan train H=6",         dict(mode="H", H=6)),
    ("V6 nhan train H=13",        dict(mode="H", H=13)),
    ("V7 nhan train nghiem ngat", dict(mode="strict")),
]

print("\nTest gop 1996+1997. Recall [CI95 chinh xac] | bao nham / so am | lead median (thang) | C moi fold")
print(f"{'bien the':27s} {'n_pos':>5s} {'n_neg':>5s} | {'LUAT recall':20s} {'bn':>8s} | {'MODEL recall':20s} {'bn':>8s} | lead luat/model | C")
for name, kw in variants:
    L, Cs, D = run_variant(**kw)
    P, N = int(L["pos"].sum()), int((~L["pos"]).sum())
    out = {}
    for nm in ("rule", "model"):
        al = L[nm + "_k"].notna()
        tp, fp = int((al & L["pos"]).sum()), int((al & ~L["pos"]).sum())
        lead = (L["ev"] - L[nm + "_k"])[L["pos"] & al]
        out[nm] = (tp, fp, np.median(lead) if len(lead) else float("nan"))
    print(f"{name:27s} {P:5d} {N:5d} | {fmt(out['rule'][0], P):20s} {out['rule'][1]:3d}/{N:<4d} | "
          f"{fmt(out['model'][0], P):20s} {out['model'][1]:3d}/{N:<4d} | "
          f"{out['rule'][2]:.1f} / {out['model'][2]:.1f}    | {Cs[0]:g}, {Cs[1]:g}")
