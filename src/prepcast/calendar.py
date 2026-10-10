"""Calendar features: KSA weekend, Hijri calendar (Ramadan/Eid via Umm al-Qura, through
``hijridate``), fixed-date public holidays, paydays, and seeded local events.

SOURCED: KSA weekend Fri-Sat (2013 Royal decree); National Day 23 Sep; Founding Day 22 Feb;
Eid al-Fitr starts 1 Shawwal; Eid al-Adha starts 10 Dhu al-Hijjah. Ramadan = Hijri month 9.
Umm al-Qura dates can differ by +/-1 day from local moon-sighting announcements (documented).
"""
from __future__ import annotations

from datetime import date, timedelta

import numpy as np
import pandas as pd
from hijridate import Hijri

from prepcast.config import DEFAULT_CONFIG, PrepCastConfig

KSA_WEEKEND = {4, 5}  # Python weekday(): Friday=4, Saturday=5


def _hijri_year_range(start: date, end: date) -> range:
    from hijridate import Gregorian

    start_hy = Gregorian(start.year, start.month, start.day).to_hijri().year
    end_hy = Gregorian(end.year, end.month, end.day).to_hijri().year
    return range(start_hy - 1, end_hy + 2)


def ramadan_windows(start: date, end: date) -> list[tuple[date, date]]:
    """Returns [(ramadan_start, ramadan_end_inclusive), ...] overlapping [start, end]."""
    windows = []
    for hy in _hijri_year_range(start, end):
        try:
            r_start = Hijri(hy, 9, 1).to_gregorian()
            r_end = Hijri(hy, 9, 29).to_gregorian()  # 29 or 30; next month's day 1 - 1 is safer
            shawwal_1 = Hijri(hy, 10, 1).to_gregorian()
            r_end = shawwal_1 - timedelta(days=1)
        except ValueError:
            continue
        r_start_g = date(r_start.year, r_start.month, r_start.day)
        r_end_g = date(r_end.year, r_end.month, r_end.day)
        if r_end_g >= start and r_start_g <= end:
            windows.append((r_start_g, r_end_g))
    return sorted(set(windows))


def eid_fitr_windows(start: date, end: date) -> list[tuple[date, date]]:
    """3-day Eid al-Fitr windows (1-3 Shawwal)."""
    windows = []
    for hy in _hijri_year_range(start, end):
        try:
            d1 = Hijri(hy, 10, 1).to_gregorian()
        except ValueError:
            continue
        d1g = date(d1.year, d1.month, d1.day)
        d3g = d1g + timedelta(days=2)
        if d3g >= start and d1g <= end:
            windows.append((d1g, d3g))
    return sorted(set(windows))


def eid_adha_windows(start: date, end: date) -> list[tuple[date, date]]:
    """3-day Eid al-Adha windows (10-12 Dhu al-Hijjah)."""
    windows = []
    for hy in _hijri_year_range(start, end):
        try:
            d1 = Hijri(hy, 12, 10).to_gregorian()
        except ValueError:
            continue
        d1g = date(d1.year, d1.month, d1.day)
        d3g = d1g + timedelta(days=2)
        if d3g >= start and d1g <= end:
            windows.append((d1g, d3g))
    return sorted(set(windows))


def _in_any_window(d: date, windows: list[tuple[date, date]]) -> bool:
    return any(w0 <= d <= w1 for w0, w1 in windows)


def build_calendar(cfg: PrepCastConfig = DEFAULT_CONFIG) -> pd.DataFrame:
    """One row per date in [cfg.dates.start, cfg.dates.end] with every calendar feature
    needed by the generator and, later, the leakage-safe feature builder. Everything here
    is known arbitrarily far in advance, so it's always a legal model feature.
    """
    start = date.fromisoformat(cfg.dates.start)
    end = date.fromisoformat(cfg.dates.end)
    dates = pd.date_range(start, end, freq="D")

    ramadan_w = ramadan_windows(start, end)
    fitr_w = eid_fitr_windows(start, end)
    adha_w = eid_adha_windows(start, end)

    rng = np.random.default_rng(cfg.seed + 1)
    n_years = (end - start).days / 365.25
    n_events = max(1, round(cfg.seasonal.n_local_events_per_year * n_years))
    event_offsets = rng.choice((end - start).days + 1, size=n_events, replace=False)
    event_dates = {start + timedelta(days=int(o)) for o in event_offsets}

    rows = []
    for ts in dates:
        d = ts.date()
        from hijridate import Gregorian

        hijri = Gregorian(d.year, d.month, d.day).to_hijri()

        is_ramadan = _in_any_window(d, ramadan_w)
        ramadan_day_n = None
        days_until_ramadan = None
        if is_ramadan:
            for w0, _w1 in ramadan_w:
                if w0 <= d:
                    candidate = (d - w0).days + 1
            ramadan_day_n = candidate
        else:
            future_starts = [w0 for w0, _ in ramadan_w if w0 > d]
            if future_starts:
                days_until_ramadan = (min(future_starts) - d).days

        is_eid_fitr = _in_any_window(d, fitr_w)
        is_eid_adha = _in_any_window(d, adha_w)
        eid_day_n = None
        if is_eid_fitr:
            for w0, _ in fitr_w:
                if w0 <= d <= w0 + timedelta(days=2):
                    eid_day_n = (d - w0).days + 1
        elif is_eid_adha:
            for w0, _ in adha_w:
                if w0 <= d <= w0 + timedelta(days=2):
                    eid_day_n = (d - w0).days + 1

        is_national_day = d.month == 9 and d.day == 23
        is_founding_day = d.month == 2 and d.day == 22
        is_weekend = d.weekday() in KSA_WEEKEND
        is_summer = d.month in cfg.seasonal.summer_months
        is_riyadh_season = d.month in cfg.seasonal.riyadh_season_months
        is_payday_window = cfg.seasonal.payday_day_of_month <= d.day <= min(
            31, cfg.seasonal.payday_day_of_month + cfg.seasonal.payday_boost_span_days
        )
        lo, hi = cfg.seasonal.pre_payday_dip_days
        is_pre_payday_dip = lo <= d.day <= hi
        is_local_event = d in event_dates

        rows.append(
            {
                "date": d,
                "dow": d.weekday(),
                "is_weekend": is_weekend,
                "month": d.month,
                "day_of_month": d.day,
                "hijri_year": hijri.year,
                "hijri_month": hijri.month,
                "hijri_day": hijri.day,
                "is_ramadan": is_ramadan,
                "ramadan_day_n": ramadan_day_n,
                "days_until_ramadan": days_until_ramadan,
                "is_eid_fitr": is_eid_fitr,
                "is_eid_adha": is_eid_adha,
                "eid_day_n": eid_day_n,
                "is_national_day": is_national_day,
                "is_founding_day": is_founding_day,
                "is_summer": is_summer,
                "is_riyadh_season": is_riyadh_season,
                "is_payday_window": is_payday_window,
                "is_pre_payday_dip": is_pre_payday_dip,
                "is_local_event": is_local_event,
            }
        )

    df = pd.DataFrame(rows)
    df["date"] = pd.to_datetime(df["date"])
    return df
