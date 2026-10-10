"""Naive baselines the model must beat. All are leakage-safe for horizons 1-7.

1. last_week_same_day:   yhat(t) = y(t-7)
2. same_weekday_4wk_avg: yhat(t) = mean(y(t-7), y(t-14), y(t-21), y(t-28))
3. flat_28d_mean (footnote): yhat(t) = mean of y over the 28 days ending at the origin T
"""
from __future__ import annotations

import pandas as pd


def last_week_same_day(panel: pd.DataFrame) -> pd.Series:
    return panel["lag7"].fillna(0.0)


def same_weekday_4wk_avg(panel: pd.DataFrame) -> pd.Series:
    return panel["dow_mean4"].fillna(0.0)


def flat_28d_mean(history: pd.DataFrame, origin: pd.Timestamp) -> pd.Series:
    """Per-series mean of y over [origin-27, origin]. Returns a Series indexed by series_id."""
    window = history[(history["date"] > origin - pd.Timedelta(days=28)) & (history["date"] <= origin)]
    return window.groupby("series_id", observed=True)["y"].mean()
