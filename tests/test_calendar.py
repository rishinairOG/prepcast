from __future__ import annotations

import pandas as pd

from prepcast.calendar import build_calendar
from prepcast.config import DEFAULT_CONFIG


def test_calendar_shape_and_range():
    df = build_calendar(DEFAULT_CONFIG)
    assert df["date"].min() == pd.Timestamp("2024-10-01")
    assert df["date"].max() == pd.Timestamp("2026-09-30")
    assert len(df) == (pd.Timestamp("2026-09-30") - pd.Timestamp("2024-10-01")).days + 1


def test_ramadan_matches_known_umm_al_qura_dates():
    df = build_calendar(DEFAULT_CONFIG)
    ramadan_dates = df.loc[df["is_ramadan"], "date"]
    # Published Umm al-Qura starts: 1446 AH -> 2025-03-01, 1447 AH -> 2026-02-18.
    assert pd.Timestamp("2025-03-01") in ramadan_dates.values
    assert pd.Timestamp("2026-02-18") in ramadan_dates.values
    assert pd.Timestamp("2025-02-28") not in ramadan_dates.values


def test_national_and_founding_day_fixed_dates():
    df = build_calendar(DEFAULT_CONFIG)
    nd = df.loc[df["is_national_day"], "date"]
    fd = df.loc[df["is_founding_day"], "date"]
    assert all(d.month == 9 and d.day == 23 for d in nd)
    assert all(d.month == 2 and d.day == 22 for d in fd)


def test_weekend_is_friday_saturday():
    df = build_calendar(DEFAULT_CONFIG)
    weekend_dows = set(df.loc[df["is_weekend"], "dow"].unique())
    assert weekend_dows == {4, 5}


def test_eid_windows_are_three_days_and_dont_overlap_ramadan():
    df = build_calendar(DEFAULT_CONFIG)
    assert df["is_eid_fitr"].sum() % 3 == 0
    assert df["is_eid_adha"].sum() % 3 == 0
    overlap = df["is_ramadan"] & df["is_eid_fitr"]
    assert not overlap.any()
