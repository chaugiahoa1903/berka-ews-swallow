"""So sanh replay_log.jsonl (goc) voi replay_log_rerun.jsonl (chay lai) theo tung thang."""
import json, sys

def read(path):
    raw = open(path, "rb").read()
    if raw[:2] in (b"\xff\xfe", b"\xfe\xff"):
        txt = raw.decode("utf-16")
    else:
        txt = raw.decode("utf-8-sig")
    rows = [json.loads(l) for l in txt.splitlines() if l.strip()]
    return rows

def month_key(r):
    for k in ("month", "replay_month", "as_of", "as_of_month"):
        if k in r:
            return k
    return None

def last_per_month(rows):
    out = {}
    for r in rows:
        if r.get("dry"):
            continue
        k = month_key(r)
        if k is None:
            continue
        out[str(r[k])] = r
    return out

a = read("reports/replay_log.jsonl")
b = read("reports/replay_log_rerun.jsonl")
print("keys goc  :", sorted(a[0].keys()))
print("keys rerun:", sorted(b[0].keys()))
A, B = last_per_month(a), last_per_month(b)
months = sorted(set(A) | set(B))
fields = ["n_scored", "n_alerts", "max_score"]
bad = 0
print("\nthang | " + " | ".join(fields) + " | ket qua")
for m in months:
    ra, rb = A.get(m), B.get(m)
    if ra is None or rb is None:
        print(m, "| chi co o", "goc" if rb is None else "rerun")
        bad += 1
        continue
    diffs = []
    for f in fields:
        va, vb = ra.get(f), rb.get(f)
        if isinstance(va, (int, float)) and isinstance(vb, (int, float)):
            same = abs(va - vb) <= 1e-9
        else:
            same = va == vb
        if not same:
            diffs.append(f"{f}: {va} vs {vb}")
    if diffs:
        bad += 1
    print(m, "|", [ra.get(f) for f in fields], "|", "KHAC " + "; ".join(diffs) if diffs else "giong")
print(f"\nTong: {len(months)} thang, {bad} thang khac/thieu")
sys.exit(1 if bad else 0)