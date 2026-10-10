"""Synthetic data generator: daily covers and per-dish sales, with hidden latent demand
and stockout censoring.

Determinism: everything draws from one ``numpy.random.Generator(cfg.seed)``; same seed ->
byte-identical CSVs (tested in test_generator.py).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from prepcast.calendar import build_calendar
from prepcast.config import DEFAULT_CONFIG, PrepCastConfig
from prepcast.menu import MENU, MenuItem


def _covers_multiplier_row(row: pd.Series, cfg: PrepCastConfig, day_index: int, n_days: int) -> float:
    s = cfg.seasonal
    mult = cfg.restaurant.dow_index[row["dow"]]

    if row["is_ramadan"]:
        # Daily covers during Ramadan: lunch collapses, dinner/iftar spikes, plus suhoor.
        # Net effect on *daily total covers* (lunch+dinner+late combined) - lunch ~40% of
        # a normal day's covers, dinner ~45%, late ~15% (see daypart split below).
        lunch_component = 0.40 * s.ramadan_lunch_mult
        dinner_component = 0.45 * s.ramadan_dinner_mult
        late_component = 0.15 * (1 + s.ramadan_suhoor_covers_frac)
        mult *= lunch_component + dinner_component + late_component
    if row["is_eid_fitr"] or row["is_eid_adha"]:
        n = row["eid_day_n"] or 1
        idx = min(int(n) - 1, len(s.eid_day_mult) - 1)
        mult *= s.eid_day_mult[idx]
    if row["is_national_day"] or row["is_founding_day"]:
        mult *= s.national_founding_day_mult
    if row["is_summer"]:
        mult *= s.summer_mult
    if row["is_riyadh_season"] and row["is_weekend"]:
        mult *= s.riyadh_season_weekend_mult
    if row["is_payday_window"]:
        mult *= s.payday_boost_mult
    if row["is_pre_payday_dip"]:
        mult *= s.pre_payday_dip_mult
    if row["is_local_event"]:
        # magnitude resolved per-row by the caller using a seeded draw; placeholder here
        pass

    trend = (1 + s.annual_trend_pct) ** (day_index / 365.25)
    mult *= trend
    return mult


def _post_eid_dip_mask(calendar_df: pd.DataFrame, fitr_or_adha_col: str, cfg: PrepCastConfig) -> np.ndarray:
    """3 days after each Eid window end get a travel-dip multiplier."""
    mask = np.zeros(len(calendar_df), dtype=bool)
    is_eid = calendar_df[fitr_or_adha_col].values
    eid_end_positions = []
    in_window = False
    for i, flag in enumerate(is_eid):
        if flag and not in_window:
            in_window = True
        elif not flag and in_window:
            eid_end_positions.append(i - 1)
            in_window = False
    for end_pos in eid_end_positions:
        for k in range(1, cfg.seasonal.post_eid_dip_days + 1):
            pos = end_pos + k
            if pos < len(mask):
                mask[pos] = True
    return mask


def generate_covers(calendar_df: pd.DataFrame, cfg: PrepCastConfig = DEFAULT_CONFIG) -> pd.DataFrame:
    rng = np.random.default_rng(cfg.seed)
    n_days = len(calendar_df)
    s = cfg.seasonal

    multipliers = np.array(
        [
            _covers_multiplier_row(row, cfg, i, n_days)
            for i, (_, row) in enumerate(calendar_df.iterrows())
        ]
    )

    # Local event magnitude: seeded draw per event day.
    event_mult = rng.uniform(s.local_event_mult_range[0], s.local_event_mult_range[1], size=n_days)
    multipliers = np.where(calendar_df["is_local_event"].values, multipliers * event_mult, multipliers)

    # Post-Eid travel dip.
    post_fitr_dip = _post_eid_dip_mask(calendar_df, "is_eid_fitr", cfg)
    post_adha_dip = _post_eid_dip_mask(calendar_df, "is_eid_adha", cfg)
    post_eid_dip = post_fitr_dip | post_adha_dip
    multipliers = np.where(post_eid_dip, multipliers * s.post_eid_dip_mult, multipliers)

    mean_covers = cfg.restaurant.baseline_covers * multipliers

    # Overdispersed, non-negative integer noise via negative binomial.
    r = cfg.noise.covers_r
    p = r / (r + mean_covers)
    p = np.clip(p, 1e-6, 1 - 1e-6)
    covers = rng.negative_binomial(r, p)

    out = calendar_df[["date"]].copy()
    out["covers"] = covers
    out["mean_covers_latent_param"] = mean_covers  # kept for diagnostics only, dropped before export
    return out


def _dish_active_mask(item: MenuItem, dates: pd.Series) -> np.ndarray:
    mask = np.ones(len(dates), dtype=bool)
    if item.launch_date:
        mask &= dates >= pd.Timestamp(item.launch_date)
    if item.retire_date:
        mask &= dates <= pd.Timestamp(item.retire_date)
    return mask


def _launch_ramp(item: MenuItem, dates: pd.Series) -> np.ndarray:
    """Linear ramp-up over 21 days post-launch, plus a 1.15x novelty bump decaying over 45 days."""
    mult = np.ones(len(dates))
    if not item.launch_date:
        return mult
    launch = pd.Timestamp(item.launch_date)
    days_since = (dates - launch).dt.days.values
    ramp = np.clip(days_since / 21.0, 0.0, 1.0)
    ramp = np.where(days_since < 0, 0.0, ramp)
    novelty = np.where(
        (days_since >= 0) & (days_since < 45),
        1.0 + 0.15 * (1 - days_since / 45.0),
        1.0,
    )
    mult = ramp * novelty
    return mult


def generate_dish_sales(
    calendar_df: pd.DataFrame, covers_df: pd.DataFrame, cfg: PrepCastConfig = DEFAULT_CONFIG
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Returns (observed_sales_df, truth_latent_demand_df). The latent frame must never be
    used as a model input - enforced by test_features_leakage.py.
    """
    rng = np.random.default_rng(cfg.seed + 2)
    dates = calendar_df["date"]
    covers = covers_df["covers"].values.astype(float)

    records_latent = []

    for item in MENU:
        active = _dish_active_mask(item, dates)
        ramp = _launch_ramp(item, dates)
        ramadan_mult = np.where(calendar_df["is_ramadan"].values, item.ramadan_multiplier, 1.0)
        if item.is_ramadan_only:
            ramadan_mult = np.where(calendar_df["is_ramadan"].values, item.ramadan_multiplier, 0.0)

        base_units = covers * item.mix_share * ramadan_mult
        base_units = base_units * np.where(item.launch_date is not None, ramp, 1.0)
        base_units = np.where(active, base_units, 0.0)

        r = cfg.noise.dish_r
        mean_u = np.clip(base_units, 1e-9, None)
        p = r / (r + mean_u)
        p = np.clip(p, 1e-6, 1 - 1e-6)
        latent = rng.negative_binomial(r, p)
        latent = np.where(active, latent, 0)

        records_latent.append(
            pd.DataFrame({"date": dates.values, "dish_id": item.dish_id, "latent_demand": latent})
        )

    latent_df = pd.concat(records_latent, ignore_index=True)

    # Stockout censoring: ~2-3% of dish-days get capped below latent demand, more likely
    # on unexpectedly high days (we approximate "unexpected" with weekend/ramadan/event days).
    is_peak = (
        calendar_df["is_weekend"].values
        | calendar_df["is_ramadan"].values
        | calendar_df["is_local_event"].values
        | calendar_df["is_eid_fitr"].values
        | calendar_df["is_eid_adha"].values
    )
    peak_by_date = dict(zip(dates.values, is_peak))

    latent_df["_is_peak"] = latent_df["date"].map(peak_by_date)
    base_rate = cfg.censoring.target_censoring_rate
    peak_mult = cfg.censoring.peak_day_censoring_multiplier
    censor_prob = np.where(latent_df["_is_peak"], base_rate * peak_mult, base_rate * 0.6)
    censor_draw = rng.uniform(0, 1, size=len(latent_df)) < censor_prob
    cap_fraction = rng.uniform(0.5, 0.9, size=len(latent_df))
    units_sold = np.where(
        censor_draw,
        np.floor(latent_df["latent_demand"].values * cap_fraction),
        latent_df["latent_demand"].values,
    ).astype(int)
    units_sold = np.minimum(units_sold, latent_df["latent_demand"].values)

    observed_df = latent_df[["date", "dish_id"]].copy()
    observed_df["units_sold"] = units_sold
    observed_df["stockout_flag"] = censor_draw & (units_sold < latent_df["latent_demand"].values)

    latent_df = latent_df.drop(columns=["_is_peak"])
    return observed_df, latent_df


def generate_all(cfg: PrepCastConfig = DEFAULT_CONFIG):
    calendar_df = build_calendar(cfg)
    covers_df = generate_covers(calendar_df, cfg)
    sales_df, latent_df = generate_dish_sales(calendar_df, covers_df, cfg)
    covers_export = covers_df[["date", "covers"]]
    return {
        "calendar": calendar_df,
        "covers": covers_export,
        "sales": sales_df,
        "latent_demand": latent_df,
    }
