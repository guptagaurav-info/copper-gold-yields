"""Load ETF closes (DBB, CPER, GLD, TLT, SPY) and US Treasury par yields from the defeatbeta mirror."""
import pandas as pd
import pyarrow.parquet as pq

SYMS = ["DBB", "CPER", "GLD", "TLT", "SPY"]


def load(raw="data/raw/"):
    t = pq.read_table(raw + "stock_prices.parquet", columns=["symbol", "report_date", "close"], filters=[("symbol", "in", SYMS)]).to_pandas()
    t["close"] = t.close.astype(float); t["d"] = pd.to_datetime(t.report_date)
    px = t.pivot_table(index="d", columns="symbol", values="close").sort_index()
    y = pd.read_parquet(raw + "daily_treasury_yield.parquet"); y.index = pd.to_datetime(y.report_date)
    y = y[["bc_3month", "bc_2year", "bc_10year"]].astype(float).sort_index()  # decimals (0.0494 = 4.94%)
    return px, y
