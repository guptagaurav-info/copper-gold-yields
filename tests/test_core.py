import sys; sys.path.insert(0, "src")
import numpy as np, pandas as pd
from cgy import analysis as A


def panel(n=300, seed=0):
    rng = np.random.default_rng(seed); idx = pd.date_range("2010-01-01", periods=n, freq="W-FRI")
    r = np.cumsum(rng.normal(0, 0.02, n)); y = 2 + 2.5 * r + rng.normal(0, 0.01, n)
    return pd.DataFrame({"ratio": r, "y10": y, "y3m": 1.0, "tlt": 100 * np.exp(np.cumsum(rng.normal(0, 0.01, n))), "spy": 1.0}, index=idx)


def test_fair_value_recovers_slope():
    d = panel(); _, b = A.fair_value(d, "2014-12-31")
    assert abs(b[0] - 2.5) < 0.1


def test_rule_uses_prior_signal():
    d = panel(); s, t, sig = A.duration_rule(d, 4)
    i = 20; dt = s.index[i]
    raw = (d["ratio"].diff(4) > 0).shift(1).loc[dt]
    assert bool(sig.loc[dt]) == bool(raw)
    assert np.isclose(s.loc[dt], 1.0 / 100 / 52) if raw else np.isclose(s.loc[dt], t.loc[dt])


def test_oos_uses_only_past():
    d = panel(); o, P, Y = A.oos_prediction(d, 4, 30)
    assert o["n"] == len(P) and P.index.min() > d.index[4 * 30 - 1]


def test_change_beta_sign():
    b, c, n = A.change_beta(panel(), 4)
    assert b > 0 and c > 0.5
