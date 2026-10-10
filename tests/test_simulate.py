from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from prepcast.simulate import simulate_dish, summarize


def test_same_day_item_bins_all_leftovers():
    r = simulate_dish(targets=[10, 10], demand=[7, 12], shelf_life=1)
    assert r["prep"].tolist() == [10, 10]
    assert r["sold"].tolist() == [7, 10]
    assert r["waste"].tolist() == [3, 0]
    assert r["stockout"].tolist() == [0, 2]
    assert r["carry_out"].tolist() == [0, 0]


def test_carryover_reduces_next_prep_and_expires():
    # shelf life 2: day-0 leftovers sell on day 1, then expire at day-1 close.
    r = simulate_dish(targets=[10, 10, 10], demand=[6, 3, 0], shelf_life=2)
    # day1: 4 carried -> top up 6. Sells 3 of the OLD 4 (FIFO); the last old one expires.
    # day2: 6 carried -> top up 4. Nothing sells; the 6 from day1 expire, the 4 new carry on.
    assert r["prep"].tolist() == [10, 6, 4]
    assert r["sold"].tolist() == [6, 3, 0]
    assert r["waste"].tolist() == [0, 1, 6]
    assert r["carry_out"].tolist() == [4, 6, 4]


def test_fifo_sells_oldest_first():
    r = simulate_dish(targets=[5, 10], demand=[0, 5], shelf_life=2)
    # day0 prep 5, carry 5; day1 prep 5, sells the 5 old ones -> they don't expire.
    assert r["waste"].tolist() == [0, 0]
    assert r["carry_out"].tolist() == [5, 5]


@pytest.mark.parametrize("shelf_life", [1, 2, 3])
def test_conservation_random(shelf_life):
    rng = np.random.default_rng(shelf_life)
    targets = rng.uniform(0, 30, 200)
    demand = rng.poisson(12, 200)
    r = simulate_dish(targets, demand, shelf_life, min_batch=4)
    lhs = r["prep"] + r["carry_in"]
    rhs = r["sold"] + r["waste"] + r["carry_out"]
    assert (lhs == rhs).all()
    assert (r["sold"] + r["stockout"] == demand).all()
    assert (r["carry_out"][:-1] == r["carry_in"][1:]).all()
    assert min(v.min() for v in r.values()) >= 0


def test_summarize_annualises_and_nets():
    df = pd.DataFrame({
        "date": pd.date_range("2026-01-01", periods=7), "latent_demand": 10, "sold": 9,
        "waste": 1, "stockout": 1, "prep": 10, "waste_kg": 0.5, "waste_sar": 2.0,
        "lost_revenue_sar": 20.0, "lost_margin_sar": 14.0,
    })
    s = summarize(df)
    assert s["waste_sar"] == pytest.approx(2.0 * 7 * 52)
    assert s["net_cost_sar"] == pytest.approx((2.0 + 14.0) * 7 * 52)
    assert s["fill_rate"] == pytest.approx(0.9)
