"""Copper/gold ratio vs the 10-year Treasury yield: co-movement, regime breaks, out-of-sample prediction, a duration rule."""
import numpy as np
import pandas as pd


def weekly_panel(px, yields, copper, start):
    w = px.resample("W-FRI").last(); yw = yields.resample("W-FRI").last()
    d = pd.concat([np.log(w[copper] / w["GLD"]).rename("ratio"), (yw["bc_10year"] * 100).rename("y10"),
                   (yw["bc_3month"] * 100).rename("y3m"), w["TLT"].rename("tlt"), w["SPY"].rename("spy")], axis=1, sort=True)
    return d.loc[start:].dropna()


def period_corr(d, periods):
    return {k: float(d.loc[a:b, ["ratio", "y10"]].corr().iloc[0, 1]) for k, (a, b) in periods.items()}


def change_beta(d, h=4):
    """10-year yield change (bp) per 10% change in the ratio, over h-week changes."""
    x = d["ratio"].diff(h); yv = d["y10"].diff(h) * 100
    z = pd.concat([x, yv], axis=1).dropna().iloc[::h]
    b = np.polyfit(z.iloc[:, 0], z.iloc[:, 1], 1)[0]
    return float(b * 0.10), float(z.corr().iloc[0, 1]), len(z)


def fair_value(d, fit_end):
    f = d.loc[:fit_end]; b = np.polyfit(f["ratio"], f["y10"], 1)
    return pd.Series(np.polyval(b, d["ratio"]), index=d.index), b


def oos_prediction(d, h=4, min_train=52):
    """Predict the next h-week 10-year yield change from the past h-week ratio change; expanding OLS, non-overlapping.
    Benchmark: no change (random walk). Returns OOS R2, hit rate, n and the forecasts."""
    z = pd.concat([d["ratio"].diff(h).rename("x"), (d["y10"].shift(-h) - d["y10"]).rename("fy")], axis=1).dropna().iloc[::h]
    p, idx = [], []
    for i in range(min_train, len(z)):
        tr = z.iloc[:i]; b = np.polyfit(tr["x"], tr["fy"], 1); p.append(np.polyval(b, z["x"].iloc[i])); idx.append(z.index[i])
    P = pd.Series(p, idx); A = z["fy"].loc[idx]
    return {"oos_r2": float(1 - ((A - P) ** 2).sum() / (A ** 2).sum()), "hit": float((np.sign(P) == np.sign(A)).mean()), "n": len(P),
            "first": str(idx[0].date())}, P, A


def duration_rule(d, h=4):
    """Hold T-bills when the ratio rose over the past h weeks (yields expected up), else hold TLT. Decided at the prior close."""
    rt = d["tlt"].pct_change(); rb = d["y3m"].shift(1) / 100 / 52
    sig = (d["ratio"].diff(h) > 0).shift(1).fillna(False).astype(bool)
    return pd.Series(np.where(sig, rb, rt), index=d.index).iloc[h + 1:], rt.iloc[h + 1:], sig


def stats(x, periods=52):
    x = x.dropna(); ann = x.mean() * periods; vol = x.std() * np.sqrt(periods); w = (1 + x).cumprod()
    return {"ann_ret": float(ann), "ann_vol": float(vol), "sharpe": float(ann / vol), "max_dd": float((w / w.cummax() - 1).min()), "n": int(len(x))}
