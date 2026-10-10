"""Leakage-safe feature building.

Policy: the forecast origin is day T and we predict T+1..T+7. Every sales-derived feature for
target day t uses data from day t-7 or earlier (MIN_LAG = 7), so for any t <= T+7 it only touches
data <= T. One model is therefore valid for all horizons 1-7. Calendar/Hijri/holiday/event/menu
features are known in advance and always allowed.

Never used as inputs: units_sold / covers on the target day, stockout_flag on the target day,
latent_demand (hidden truth). Enforced by tests/test_features_leakage.py.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from prepcast.menu import MENU

MIN_LAG = 7
LAGS = (7, 14, 21, 28)

CAL_FEATURES = [
    "dow", "is_weekend", "month", "day_of_month", "hijri_month", "hijri_day",
    "is_ramadan", "ramadan_day_n", "days_until_ramadan", "eid_day_n",
    "is_eid_fitr", "is_eid_adha", "is_public_holiday", "is_local_event",
    "is_summer", "is_riyadh_season", "is_payday_window", "is_pre_payday_dip",
]
LAG_FEATURES = [f"lag{lag}" for lag in LAGS] + [
    "roll7_mean", "roll28_mean", "roll28_std", "dow_mean4",
]
DISH_FEATURES = CAL_FEATURES + LAG_FEATURES + [
    "dish_share28", "days_since_launch", "dish_id", "category",
]
COVERS_FEATURES = CAL_FEATURES + LAG_FEATURES

FORBIDDEN = {"units_sold", "covers", "stockout_flag", "latent_demand", "y"}

DISH_IDS = [m.dish_id for m in MENU]
CATEGORIES = sorted({m.category for m in MENU})


def calendar_features(calendar: pd.DataFrame) -> pd.DataFrame:
    df = calendar.copy()
    df["is_public_holiday"] = df["is_national_day"] | df["is_founding_day"]
    for col in ("ramadan_day_n", "days_until_ramadan", "eid_day_n"):
        df[col] = pd.to_numeric(df[col], errors="coerce").astype(float)
    for col in CAL_FEATURES:
        if df[col].dtype == bool:
            df[col] = df[col].astype(int)
    return df[["date", *CAL_FEATURES]]


def _lag_block(y: pd.Series) -> pd.DataFrame:
    """y must be a contiguous daily series sorted by date."""
    out = pd.DataFrame(index=y.index)
    for lag in LAGS:
        out[f"lag{lag}"] = y.shift(lag)
    base = y.shift(MIN_LAG)
    out["roll7_mean"] = base.rolling(7, min_periods=1).mean()
    out["roll28_mean"] = base.rolling(28, min_periods=1).mean()
    out["roll28_std"] = base.rolling(28, min_periods=2).std()
    out["dow_mean4"] = out[[f"lag{lag}" for lag in LAGS]].mean(axis=1)
    return out


def _check_contiguous(dates: pd.Series) -> None:
    d = pd.to_datetime(dates).sort_values()
    if len(d) > 1 and not (d.diff().dropna() == pd.Timedelta(days=1)).all():
        raise ValueError("Series must be contiguous daily data (no gaps) for shift-based lags")


def dish_activity(calendar: pd.DataFrame) -> pd.DataFrame:
    """Known-in-advance menu availability per (date, dish)."""
    rows = []
    dates = pd.to_datetime(calendar["date"])
    ramadan = calendar["is_ramadan"].astype(bool).values
    for m in MENU:
        active = np.ones(len(dates), dtype=bool)
        if m.launch_date:
            active &= (dates >= pd.Timestamp(m.launch_date)).values
        if m.retire_date:
            active &= (dates <= pd.Timestamp(m.retire_date)).values
        if m.is_ramadan_only:
            active &= ramadan
        if m.launch_date:
            since = (dates - pd.Timestamp(m.launch_date)).dt.days.astype(float).values
        else:
            since = np.full(len(dates), np.nan)
        rows.append(pd.DataFrame({
            "date": dates.values, "dish_id": m.dish_id,
            "is_active": active, "days_since_launch": since,
        }))
    return pd.concat(rows, ignore_index=True)


def build_dish_panel(sales: pd.DataFrame, calendar: pd.DataFrame) -> pd.DataFrame:
    """One row per (date, dish): target `y` (observed units_sold), `stockout_flag` (training
    weight only), `is_active`, and DISH_FEATURES. latent_demand is never read here.
    """
    s = sales[["date", "dish_id", "units_sold", "stockout_flag"]].copy()
    s["date"] = pd.to_datetime(s["date"])
    s = s.sort_values(["dish_id", "date"]).reset_index(drop=True)

    parts = []
    for _dish, d in s.groupby("dish_id", sort=True):
        _check_contiguous(d["date"])
        parts.append(pd.concat([d, _lag_block(d["units_sold"].astype(float))], axis=1))
    panel = pd.concat(parts, ignore_index=True)

    # Dish share of total sales over the 28 days ending t-7.
    total = s.groupby("date")["units_sold"].sum().sort_index().astype(float)
    total_roll = total.shift(MIN_LAG).rolling(28, min_periods=1).sum()
    panel["_total_roll28"] = panel["date"].map(total_roll)
    panel["dish_share28"] = (panel["roll28_mean"] * 28 / panel["_total_roll28"]).where(
        panel["_total_roll28"] > 0
    )
    panel = panel.drop(columns=["_total_roll28"])

    panel = panel.merge(calendar_features(calendar), on="date", how="left")
    panel = panel.merge(dish_activity(calendar), on=["date", "dish_id"], how="left")
    cat_map = {m.dish_id: m.category for m in MENU}
    panel["category"] = pd.Categorical(panel["dish_id"].map(cat_map), categories=CATEGORIES)
    panel["dish_id"] = pd.Categorical(panel["dish_id"], categories=DISH_IDS)
    panel = panel.rename(columns={"units_sold": "y"})
    panel["series_id"] = panel["dish_id"].astype(str)
    return panel.sort_values(["date", "series_id"]).reset_index(drop=True)


def build_covers_panel(covers: pd.DataFrame, calendar: pd.DataFrame) -> pd.DataFrame:
    c = covers[["date", "covers"]].copy()
    c["date"] = pd.to_datetime(c["date"])
    c = c.sort_values("date").reset_index(drop=True)
    _check_contiguous(c["date"])
    panel = pd.concat([c, _lag_block(c["covers"].astype(float))], axis=1)
    panel = panel.merge(calendar_features(calendar), on="date", how="left")
    panel = panel.rename(columns={"covers": "y"})
    panel["series_id"] = "covers"
    panel["is_active"] = True
    panel["stockout_flag"] = False
    return panel
