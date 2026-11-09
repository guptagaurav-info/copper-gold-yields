"""Run everything: python -m cgy.pipeline -> reports/metrics.json + reports/figures/*.png"""
import json, os
import yaml
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from . import data, analysis as A

NAVY, GREY, GOLD, RED, TEAL = "#1F3A5F", "#8A8F98", "#9A7F2E", "#B5473A", "#2A7F7F"
plt.rcParams.update({"font.size": 11, "axes.spines.top": False, "axes.spines.right": False, "figure.dpi": 150})
FIG = "reports/figures/"


def run(d, cfg):
    h = cfg["horizon_weeks"]; fv, b = A.fair_value(d, cfg["fit_end"])
    pre, post = d.loc[:cfg["fit_end"]], d.loc[str(pd.Timestamp(cfg["fit_end"]).year + 1):]
    oos, P, Y = A.oos_prediction(d, h)
    rule, tlt, sig = A.duration_rule(d, h)
    half = 0.5 * tlt + 0.5 * (d["y3m"].shift(1) / 100 / 52).reindex(tlt.index)
    sp = cfg["split"]; B = str(pd.Timestamp(sp).year + 1)
    return {
        "weeks": len(d), "first": str(d.index[0].date()), "last": str(d.index[-1].date()),
        "level_corr": A.period_corr(d, cfg["periods"]),
        "beta_pre": dict(zip(["bp_per_10pct", "corr", "n"], A.change_beta(pre, h))),
        "beta_post": dict(zip(["bp_per_10pct", "corr", "n"], A.change_beta(post, h))),
        "fair_value": {"slope_pct_per_logunit": float(b[0]), "implied_now": float(fv.iloc[-1]), "actual_now": float(d["y10"].iloc[-1]),
                       "gap_now": float(d["y10"].iloc[-1] - fv.iloc[-1]), "gap_end_fit": float((d["y10"] - fv).loc[:cfg["fit_end"]].iloc[-1])},
        "oos": oos,
        "rule": {k: {"tlt": A.stats(tlt.loc[a:z]), "rule": A.stats(rule.loc[a:z]), "half": A.stats(half.loc[a:z])}
                 for k, (a, z) in {"all": (None, None), "A": (None, sp), "B": (B, None)}.items()},
        "time_in_bills": float(sig.mean()),
    }, fv, rule, tlt, half


def main():
    cfg = yaml.safe_load(open("configs/default.yaml"))
    px, y = data.load()
    dm = A.weekly_panel(px, y, cfg["main"]["copper"], cfg["main"]["start"])
    dr = A.weekly_panel(px, y, cfg["robust"]["copper"], cfg["robust"]["start"])
    om, fv, rule, tlt, half = run(dm, cfg); orb, fvr, *_ = run(dr, cfg)
    fe = pd.Timestamp(cfg["fit_end"])
    moves = {s: float(px[s].dropna().iloc[-1] / px[s].loc[:fe].dropna().iloc[-1] - 1) for s in ["GLD", "DBB", "CPER"]}
    moves["y10_bp"] = float((y["bc_10year"].iloc[-1] - y["bc_10year"].loc[:fe].iloc[-1]) * 1e4)
    out = {"main_DBB": om, "robust_CPER": orb, "since_fit_end": moves}
    os.makedirs(FIG, exist_ok=True); json.dump(out, open("reports/metrics.json", "w"), indent=1)

    # 1. implied vs actual
    fig, ax = plt.subplots(figsize=(9, 5.2))
    ax.plot(dm["y10"], color=NAVY, lw=1.8, label="10-year Treasury yield")
    ax.plot(fv, color=GOLD, lw=1.6, label="Yield implied by the copper/gold ratio (base metals; fit 2007–2021)")
    ax.plot(fvr, color=GOLD, lw=1.0, ls="--", label="Same, copper only (fit 2011–2021)")
    ax.axvline(fe, color=GREY, lw=0.8, ls=":"); ax.text(fe, ax.get_ylim()[1] * 0.97, " fit ends", color=GREY, fontsize=9, va="top")
    ax.set_ylabel("%"); ax.legend(frameon=False, fontsize=9, loc="upper center", bbox_to_anchor=(0.5, -0.08), ncol=2)
    ax.set_title("The copper/gold ratio stopped tracking the 10-year yield in 2022", loc="left")
    fig.tight_layout(); fig.savefig(FIG + "implied.png"); plt.close(fig)

    # 2. rolling correlation (2-year window, levels and 4-week changes)
    lv = dm["ratio"].rolling(104).corr(dm["y10"]); ch = dm["ratio"].diff(4).rolling(104).corr(dm["y10"].diff(4))
    fig, ax = plt.subplots(figsize=(9, 4.2))
    ax.plot(lv, color=NAVY, lw=1.6, label="Levels"); ax.plot(ch, color=TEAL, lw=1.6, label="4-week changes")
    ax.axhline(0, color=GREY, lw=0.7); ax.set_ylim(-1, 1); ax.legend(frameon=False)
    ax.set_title("Rolling 2-year correlation: copper/gold ratio vs 10-year yield", loc="left")
    fig.tight_layout(); fig.savefig(FIG + "rolling_corr.png"); plt.close(fig)

    # 3. what moved since end-2021
    fig, ax = plt.subplots(figsize=(8, 3.8))
    lab = ["Gold (GLD)", "Copper (CPER)", "Base metals (DBB)"]; v = [moves["GLD"] * 100, moves["CPER"] * 100, moves["DBB"] * 100]
    bars = ax.barh(lab, v, color=[GOLD, RED, GREY]); ax.invert_yaxis()
    for r_, x in zip(bars, v):
        ax.text(x + 1.5, r_.get_y() + r_.get_height() / 2, f"{x:+.0f}%", va="center")
    ax.set_xlim(0, max(v) * 1.18); ax.set_xlabel("Price change, end-2021 to Oct 2026, %")
    ax.set_title(f"Gold did the moving (10-year yield: {moves['y10_bp']:+.0f} bp)", loc="left")
    fig.tight_layout(); fig.savefig(FIG + "moves.png"); plt.close(fig)

    # 4. duration rule
    fig, ax = plt.subplots(figsize=(9, 4.4))
    for s, c, l in [(tlt, RED, "Long Treasuries (TLT), buy and hold"), (half, GREY, "50% TLT, 50% T-bills"),
                    (rule, NAVY, "Rule: T-bills when the ratio rose over 4 weeks, else TLT")]:
        ax.plot((1 + s.fillna(0)).cumprod(), color=c, lw=1.6, label=l)
    ax.axvline(pd.Timestamp(cfg["split"]), color=GREY, lw=0.8, ls=":"); ax.legend(fontsize=9, loc="upper left", framealpha=0.9, edgecolor="none")
    ax.set_title("Using the ratio to time duration, weekly, 2007–2026 ($1 start)", loc="left")
    fig.tight_layout(); fig.savefig(FIG + "rule.png"); plt.close(fig)
    print(json.dumps(out, indent=1)[:3000])


if __name__ == "__main__":
    main()
