from __future__ import annotations

import pandas as pd

from prepcast.config import DEFAULT_CONFIG
from prepcast.generator import generate_all
from prepcast.menu import MENU


def test_reproducible_with_same_seed():
    out1 = generate_all(DEFAULT_CONFIG)
    out2 = generate_all(DEFAULT_CONFIG)
    pd.testing.assert_frame_equal(out1["sales"], out2["sales"])
    pd.testing.assert_frame_equal(out1["covers"], out2["covers"])
    pd.testing.assert_frame_equal(out1["latent_demand"], out2["latent_demand"])


def test_row_counts():
    out = generate_all(DEFAULT_CONFIG)
    n_days = len(out["calendar"])
    assert len(out["covers"]) == n_days
    assert len(out["sales"]) == n_days * len(MENU)
    assert len(out["latent_demand"]) == n_days * len(MENU)


def test_no_negative_values():
    out = generate_all(DEFAULT_CONFIG)
    assert (out["covers"]["covers"] >= 0).all()
    assert (out["sales"]["units_sold"] >= 0).all()
    assert (out["latent_demand"]["latent_demand"] >= 0).all()


def test_dow_pattern_thu_fri_peak():
    out = generate_all(DEFAULT_CONFIG)
    merged = out["covers"].merge(out["calendar"][["date", "dow"]], on="date")
    means = merged.groupby("dow")["covers"].mean()
    assert means[3] > means[6]  # Thu > Sun
    assert means[4] > means[6]  # Fri > Sun
    assert means[4] > means[0]  # Fri > Mon


def test_ramadan_lunch_drop_present():
    out = generate_all(DEFAULT_CONFIG)
    cal = out["calendar"]
    merged = out["covers"].merge(cal[["date", "is_ramadan"]], on="date")
    ramadan_mean = merged.loc[merged["is_ramadan"], "covers"].mean()
    non_ramadan_mean = merged.loc[~merged["is_ramadan"], "covers"].mean()
    # Net daily covers during Ramadan should be lower than normal (lunch collapse dominates).
    assert ramadan_mean < non_ramadan_mean


def test_launch_and_retire_respected():
    out = generate_all(DEFAULT_CONFIG)
    sales = out["sales"]
    launched = [m for m in MENU if m.launch_date]
    retired = [m for m in MENU if m.retire_date]
    assert launched and retired
    for item in launched:
        before = sales[(sales.dish_id == item.dish_id) & (sales.date < pd.Timestamp(item.launch_date))]
        assert (before["units_sold"] == 0).all()
        after = sales[(sales.dish_id == item.dish_id) & (sales.date >= pd.Timestamp(item.launch_date))]
        assert after["units_sold"].sum() > 0
    for item in retired:
        after = sales[(sales.dish_id == item.dish_id) & (sales.date > pd.Timestamp(item.retire_date))]
        assert (after["units_sold"] == 0).all()


def test_ramadan_only_items_sell_only_in_ramadan():
    out = generate_all(DEFAULT_CONFIG)
    cal = out["calendar"]
    sales = out["sales"].merge(cal[["date", "is_ramadan"]], on="date")
    for item in MENU:
        if item.is_ramadan_only:
            non_ramadan_sales = sales[(sales.dish_id == item.dish_id) & (~sales.is_ramadan)]
            assert (non_ramadan_sales["units_sold"] == 0).all()


def test_censoring_rate_in_expected_range():
    out = generate_all(DEFAULT_CONFIG)
    rate = out["sales"]["stockout_flag"].mean()
    assert 0.01 <= rate <= 0.06


def test_latent_never_below_sold():
    out = generate_all(DEFAULT_CONFIG)
    merged = out["sales"].merge(out["latent_demand"], on=["date", "dish_id"])
    assert (merged["units_sold"] <= merged["latent_demand"]).all()
