"""Forecast accuracy metrics."""
from __future__ import annotations

import numpy as np
import pandas as pd


def wape(y, yhat) -> float:
    y, yhat = np.asarray(y, float), np.asarray(yhat, float)
    denom = np.abs(y).sum()
    return float(np.abs(y - yhat).sum() / denom) if denom > 0 else float("nan")


def mape_nonzero(y, yhat) -> float:
    """MAPE over days with y > 0 only. Unstable for low-volume items - reported with that caveat."""
    y, yhat = np.asarray(y, float), np.asarray(yhat, float)
    m = y > 0
    return float(np.mean(np.abs(y[m] - yhat[m]) / y[m])) if m.any() else float("nan")


def bias(y, yhat) -> float:
    """Signed total error as a share of actuals. Positive = over-forecasting."""
    y, yhat = np.asarray(y, float), np.asarray(yhat, float)
    denom = y.sum()
    return float((yhat - y).sum() / denom) if denom > 0 else float("nan")


def coverage(y, lo, hi) -> float:
    y, lo, hi = (np.asarray(a, float) for a in (y, lo, hi))
    return float(np.mean((y >= lo) & (y <= hi)))


def segment_of(row_cal: pd.DataFrame) -> pd.Series:
    """Day type used to break down metrics: eid > ramadan > event > normal."""
    seg = pd.Series("normal", index=row_cal.index)
    event = (row_cal["is_local_event"] == 1) | (row_cal["is_public_holiday"] == 1)
    seg[event] = "event/holiday"
    seg[row_cal["is_ramadan"] == 1] = "ramadan"
    seg[(row_cal["is_eid_fitr"] == 1) | (row_cal["is_eid_adha"] == 1)] = "eid"
    return seg


def summary_table(preds: pd.DataFrame, methods: dict[str, str], by: str | None = None,
                  y_col: str = "y") -> pd.DataFrame:
    """methods: display name -> prediction column. Coverage uses q10/q90 when present."""
    groups = [("all", preds)] if by is None else list(preds.groupby(by, observed=True))
    rows = []
    for key, g in groups:
        for name, col in methods.items():
            row = {"segment": key, "method": name, "n": len(g),
                   "WAPE": wape(g[y_col], g[col]), "bias": bias(g[y_col], g[col]),
                   "MAPE_nonzero": mape_nonzero(g[y_col], g[col])}
            if col == "yhat" and {"q10", "q90"} <= set(g.columns):
                row["cov80"] = coverage(g[y_col], g["q10"], g["q90"])
            rows.append(row)
    return pd.DataFrame(rows)
