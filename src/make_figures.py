"""Tao 2 bieu do cho README Swallow (matplotlib, khong can mang).

Chay tu thu muc goc repo:  python src\\make_figures.py
Dau ra: docs\\img\\fig_recall.png, docs\\img\\fig_monthly.png

Nguon so lieu:
  - fig_monthly: doc truc tiep reports/replay_log.jsonl (lan chay that moi nhat cua tung thang).
  - fig_recall : cac so dem 22/34, 23/34, 0/270 duoc CHEP TAY tu ket qua da do (results.md,
    gop test 1996+1997). Khoang tin cay Clopper-Pearson 95% do code tinh, khong chep tay.
    Neu chay lai model va so dem doi, phai sua hang so COUNTS ben duoi.
"""
import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy.stats import beta

ROOT = Path(__file__).resolve().parent.parent
LOG = ROOT / "reports" / "replay_log.jsonl"
OUT = ROOT / "docs" / "img"
OUT.mkdir(parents=True, exist_ok=True)

# Palette da qua validate_palette.js (light, be mat #fcfcfb): xanh = slot 1, cam = slot 2
SURFACE, INK, INK2, MUTED, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#8a8985", "#e6e5e1"
BLUE, ORANGE = "#2a78d6", "#eb6834"

plt.rcParams.update({
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
    "text.color": INK, "axes.labelcolor": INK2, "xtick.color": INK2, "ytick.color": INK2,
    "axes.edgecolor": GRID, "font.size": 10, "axes.spines.top": False, "axes.spines.right": False,
})


def cp_interval(k, n, alpha=0.05):
    """Khoang tin cay Clopper-Pearson chinh xac cho ty le k/n."""
    lo = 0.0 if k == 0 else beta.ppf(alpha / 2, k, n - k + 1)
    hi = 1.0 if k == n else beta.ppf(1 - alpha / 2, k + 1, n - k)
    return lo, hi


# ---------------- Hinh 1: recall va bao nham (test gop 1996+1997) ----------------
COUNTS = {
    "Rule: balance ever negative": dict(hit=22, pos=34, fa=0, neg=270, color=ORANGE),
    "L2 logistic regression": dict(hit=23, pos=34, fa=0, neg=270, color=BLUE),
}


def fig_recall():
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(9.6, 3.0), gridspec_kw={"width_ratios": [1.6, 1]})
    names = list(COUNTS)
    for i, name in enumerate(names):
        c = COUNTS[name]
        y = len(names) - 1 - i
        p = c["hit"] / c["pos"]
        lo, hi = cp_interval(c["hit"], c["pos"])
        a1.hlines(y, lo * 100, hi * 100, color=c["color"], lw=2)
        a1.plot(p * 100, y, "o", ms=8, color=c["color"], mec=SURFACE, mew=2)
        a1.text(hi * 100 + 2, y, f"{c['hit']}/{c['pos']} = {p*100:.0f}%  [{lo*100:.0f}; {hi*100:.0f}]",
                va="center", fontsize=9, color=INK)
        flo, fhi = cp_interval(c["fa"], c["neg"])
        a2.hlines(y, flo * 100, fhi * 100, color=c["color"], lw=2)
        a2.plot(c["fa"] / c["neg"] * 100, y, "o", ms=8, color=c["color"], mec=SURFACE, mew=2)
        a2.text(fhi * 100 + 0.15, y, f"{c['fa']}/{c['neg']}, upper {fhi*100:.1f}%", va="center",
                fontsize=9, color=INK)
    for ax in (a1, a2):
        ax.set_ylim(-0.6, len(names) - 0.4)
        ax.grid(axis="x", color=GRID, lw=0.8)
        ax.set_axisbelow(True)
        ax.spines["left"].set_visible(False)
        ax.spines["bottom"].set_color(GRID)
        ax.tick_params(axis="y", length=0)
    a1.set_yticks(range(len(names)))
    a1.set_yticklabels(names[::-1])
    a2.set_yticks([])
    a1.set_xlim(-2, 118)
    a1.set_xticks([0, 20, 40, 60, 80, 100])
    a1.set_xlabel("Recall, % of 34 defaulting loans caught (95% exact CI)")
    a2.set_xlim(-0.12, 4.2)
    a2.set_xticks([0, 1, 2, 3, 4])
    a2.set_xlabel("False alarms, % of 270 good loans\n(95% upper bound)")
    fig.suptitle("A one-line rule is almost as good as the model (test 1996+1997 pooled)",
                 x=0.01, ha="left", fontsize=11.5, fontweight="bold", color=INK)
    fig.text(0.01, 0.01, "Replay of simulated Berka data. 34 positives: intervals are wide; 22 vs 23 is not a meaningful difference.",
             fontsize=8.5, color=INK2, ha="left")
    fig.tight_layout(rect=(0, 0.05, 1, 0.93))
    fig.savefig(OUT / "fig_recall.png", dpi=170)
    plt.close(fig)


# ---------------- Hinh 2: so khoan cham diem va so canh bao theo thang ----------------
def load_months():
    last = {}
    with LOG.open(encoding=("utf-16" if LOG.read_bytes()[:2] in (b"\xff\xfe", b"\xfe\xff") else "utf-8-sig")) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            r = json.loads(line)
            if r.get("dry_run"):
                continue
            last[r["replay_month"]] = r  # dong sau ghi de dong truoc: lay lan chay that moi nhat
    return [last[m] for m in sorted(last)]


def fig_monthly():
    rows = load_months()
    months = [r["replay_month"] for r in rows]
    x = list(range(len(rows)))
    scored = [r["n_scored"] for r in rows]
    alerts = [r["n_alerts"] for r in rows]
    fig, (a1, a2) = plt.subplots(2, 1, figsize=(9.6, 5.0), sharex=True)
    a1.bar(x, scored, width=0.68, color=BLUE)
    a2.bar(x, alerts, width=0.68, color=ORANGE)
    for ax, title in ((a1, "Loans scored per month"), (a2, "Alerts per month (score above threshold)")):
        ax.set_title(title, loc="left", fontsize=10, color=INK2)
        ax.grid(axis="y", color=GRID, lw=0.8)
        ax.set_axisbelow(True)
        ax.spines["left"].set_visible(False)
        ax.spines["bottom"].set_color(GRID)
        ax.tick_params(axis="y", length=0)
    # danh dau thang DQ fail (khong co dong nao de cham diem)
    for i, r in enumerate(rows):
        if not r.get("dq_ok"):
            a1.annotate("data-quality check\nfailed: run stops", (i, 0), xytext=(i + 0.8, max(scored) * 0.55),
                        fontsize=8.5, color=INK2, arrowprops=dict(arrowstyle="-", color=MUTED, lw=0.8))
    # nhan gia tri o dinh cot cuoi cung cua moi bang cho ro (chon loc, khong ghi moi cot)
    imax = max(range(len(alerts)), key=lambda i: alerts[i])
    a2.text(imax, alerts[imax] + 0.3, str(alerts[imax]), ha="center", fontsize=9, color=INK)
    jmax = max(range(len(scored)), key=lambda i: scored[i])
    a1.text(jmax, scored[jmax] + 3, str(scored[jmax]), ha="center", fontsize=9, color=INK)
    a2.set_xticks(x)
    a2.set_xticklabels(months, rotation=60, ha="right", fontsize=8)
    fig.suptitle("Monthly replay: 1997-01 to 1998-12", x=0.01, ha="left", fontsize=11.5,
                 fontweight="bold", color=INK)
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    fig.savefig(OUT / "fig_monthly.png", dpi=170)
    plt.close(fig)


if __name__ == "__main__":
    if not LOG.exists():
        sys.exit(f"Khong thay {LOG}")
    fig_recall()
    fig_monthly()
    print("Da tao:", OUT / "fig_recall.png", "va", OUT / "fig_monthly.png")
