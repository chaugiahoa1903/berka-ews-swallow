"""Huan luyen model cuoi (bo core, train 1993-96) va luu ra models\.
Chay: python src\train_final.py
"""
import os
import datetime
import numpy as np
import pandas as pd
import joblib
import lr_lib as L

TRAIN_YEARS = [1993, 1994, 1995, 1996]
df = L.prepare(pd.read_csv("data/processed/model_rows.csv"))
elig = (df["loan_year"] <= 1997) & (df["label_ambiguous"].astype(int) == 0) & (df["is_pre_event"] == 1)
D = df[elig].reset_index(drop=True)
D["y"] = D["event_k"].notna().astype(int)

C_star, vs = L.select_C(D, TRAIN_YEARS)
t = L.pick_threshold(vs)
print(f"C = {C_star:g} (ky vong 0.001) | t = {t:.4f} (ky vong 0.1841)")
assert np.isclose(C_star, 0.001) and abs(t - 0.1841) < 6e-5, "khong khop lan chay truoc"

tr = D[D["loan_year"].isin(TRAIN_YEARS)]
sc, m = L.fit_lr(tr[L.FEATURES].to_numpy(), tr["y"].to_numpy(), C_star)
print("\nHe so chuan hoa (model cuoi):")
print(pd.DataFrame({"feature": L.FEATURES, "coef_std": m.coef_[0]}).to_string(index=False, float_format=lambda x: f"{x:.3f}"))

# Kiem tra tai hien: cham lai test 1997 phai ra 15/18 duong, 0/170 am bi bao nham
te = D[D["loan_year"] == 1997].copy()
te["score"] = L.predict(sc, m, te[L.FEATURES].to_numpy())
al = te[te["score"] > t].groupby("loan_id").size().index
per = te.groupby("loan_id")["event_k"].first().notna()
tp, fp = int(per[per.index.isin(al)].sum()), int((~per[per.index.isin(al)]).sum())
print(f"\nTai hien test 1997: bat {tp}/{int(per.sum())} duong, bao nham {fp}/{int((~per).sum())} am (ky vong 15/18 va 0/170)")
assert (tp, fp) == (15, 0), "khong tai hien duoc ket qua test 1997"

os.makedirs("models", exist_ok=True)
path = "models/lr_core_train1993_96.joblib"
joblib.dump({"features": L.FEATURES, "scaler": sc, "model": m, "threshold": float(t), "C": float(C_star),
             "train_years": TRAIN_YEARS, "fa_budget": L.FA_BUDGET,
             "trained_at": datetime.datetime.now().isoformat(timespec="seconds"),
             "note": "Replay du lieu Berka mo phong; khong phai he thong chay that. Nhan: dong truoc moc 'thieu>=2 ky tra' = 1."},
            path)
print("\nDa luu:", path)
