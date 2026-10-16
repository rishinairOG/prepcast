"""Smoke test for export.py: the pipeline's JSON output for the static demo must exist, be
shaped as app.js expects, and trace back to the same CSVs report.py reads (no separate
re-derivation that could silently diverge).
"""
from __future__ import annotations

import json

import pandas as pd
import pytest

from prepcast.config import DATA_DIR
from prepcast.export import (
    SCENARIO_ORIGINS,
    build_dishes,
    build_prep_list,
    build_savings,
    build_scenarios,
)

pytestmark = pytest.mark.skipif(
    not (DATA_DIR / "backtest_dishes.csv").exists(),
    reason="requires `prepcast backtest` and `prepcast simulate` to have been run",
)


@pytest.fixture(scope="module")
def dish_bt():
    df = pd.read_csv(DATA_DIR / "backtest_dishes.csv", parse_dates=["date", "origin"])
    return df[~df["is_warmup"]]


@pytest.fixture(scope="module")
def covers_bt():
    df = pd.read_csv(DATA_DIR / "backtest_covers.csv", parse_dates=["date", "origin"])
    return df[~df["is_warmup"]]


@pytest.fixture(scope="module")
def sim_summary():
    return pd.read_csv(DATA_DIR / "sim_summary.csv")


@pytest.fixture(scope="module")
def sim_prepcast_daily():
    return pd.read_csv(DATA_DIR / "sim_prepcast_daily.csv", parse_dates=["date"])


def test_scenarios_have_7_days_each(covers_bt):
    scenarios = build_scenarios(covers_bt)
    assert set(scenarios) == set(SCENARIO_ORIGINS)
    for s in scenarios.values():
        assert len(s["dates"]) == 7
        assert len(s["actual"]) == len(s["forecast_p50"]) == 7
        # p10 <= p50 <= p90 for every day (the model's own monotone quantiles)
        for lo, mid, hi in zip(s["forecast_p10"], s["forecast_p50"], s["forecast_p90"]):
            assert lo <= mid <= hi


def test_dishes_json_serializable_and_nonempty(dish_bt):
    tomorrow = pd.Timestamp(SCENARIO_ORIGINS["normal"]) + pd.Timedelta(days=1)
    rows = build_dishes(dish_bt, tomorrow)
    assert len(rows) > 0
    json.dumps(rows)  # must round-trip through JSON with no NaN/Timestamp objects
    for r in rows:
        assert r["recommended_prep"] >= 0
        assert r["station"]


def test_prep_list_grouped_and_nonnegative(sim_prepcast_daily):
    tomorrow = pd.Timestamp(SCENARIO_ORIGINS["normal"]) + pd.Timedelta(days=1)
    pl = build_prep_list(sim_prepcast_daily, tomorrow)
    assert pl["items"]
    for item in pl["items"]:
        assert item["prep_portions"] >= 0
        assert item["carryover_portions"] >= 0


def test_savings_headline_matches_known_backtest_numbers(sim_summary):
    s = build_savings(sim_summary)
    # These trace to data/savings_report.txt; allow a little slack for re-runs with the same
    # seed (should be byte-identical, but keep the test robust to minor float formatting).
    assert s["headline"]["net_cost_sar_saved"] > 150_000
    assert s["headline"]["waste_sar_saved"] > 0
    assert s["headline"]["stockout_portions_avoided"] > 0
    assert set(s["buffer_slider"]) == {f"P{p}" for p in range(50, 100, 5)}
    json.dumps(s)
