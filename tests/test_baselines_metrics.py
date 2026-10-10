from __future__ import annotations

import itertools

import numpy as np
import pandas as pd
import pytest

from prepcast import baselines, metrics, model
from prepcast.backtest import make_origins


def test_wape_known_value():
    assert metrics.wape([10, 20, 30], [12, 18, 30]) == pytest.approx(4 / 60)


def test_wape_zero_actuals_is_nan():
    assert np.isnan(metrics.wape([0, 0], [1, 2]))


def test_mape_ignores_zero_days():
    assert metrics.mape_nonzero([0, 10, 20], [5, 12, 18]) == pytest.approx((0.2 + 0.1) / 2)


def test_bias_sign():
    assert metrics.bias([10, 10], [12, 12]) == pytest.approx(0.2)
    assert metrics.bias([10, 10], [8, 8]) == pytest.approx(-0.2)


def test_coverage():
    assert metrics.coverage([1, 5, 10], [0, 6, 9], [2, 7, 11]) == pytest.approx(2 / 3)


def test_baselines_use_lag_columns():
    panel = pd.DataFrame({"lag7": [5.0, np.nan], "dow_mean4": [4.0, 6.0]})
    assert baselines.last_week_same_day(panel).tolist() == [5.0, 0.0]
    assert baselines.same_weekday_4wk_avg(panel).tolist() == [4.0, 6.0]


def test_flat_28d_mean_window():
    dates = pd.date_range("2026-01-01", periods=40, freq="D")
    hist = pd.DataFrame({"date": dates, "series_id": "a", "y": np.arange(40, dtype=float)})
    origin = dates[-1]
    assert baselines.flat_28d_mean(hist, origin)["a"] == pytest.approx(np.arange(12, 40).mean())


def test_origins_weekly_and_leave_full_horizon():
    origins = make_origins(pd.Timestamp("2026-09-30"), n_folds=52, warmup=8)
    assert len(origins) == 60
    assert origins[-1] == pd.Timestamp("2026-09-23")
    assert all((b - a) == pd.Timedelta(weeks=1) for a, b in itertools.pairwise(origins))


def test_conformal_quantiles_monotone_and_nonnegative():
    rng = np.random.default_rng(0)
    yhat = rng.uniform(0, 30, 500)
    hist = pd.DataFrame({"series_id": "a", "yhat": yhat, "y": rng.poisson(yhat)})
    calib = model.calibrate(hist)
    q = model.apply_quantiles(["a", "b"], [10.0, 0.0], calib)
    assert (np.diff(q, axis=1) >= 0).all()
    assert (q >= 0).all()


def test_conformal_coverage_roughly_nominal():
    rng = np.random.default_rng(1)
    yhat = rng.uniform(1, 40, 4000)
    y = rng.poisson(yhat)
    calib = model.calibrate(pd.DataFrame({"series_id": "a", "yhat": yhat[:2000], "y": y[:2000]}))
    q = model.apply_quantiles(["a"] * 2000, yhat[2000:], calib)
    i10 = model.QUANTILE_LEVELS.index(0.1)
    i90 = model.QUANTILE_LEVELS.index(0.9)
    cov = metrics.coverage(y[2000:], q[:, i10], q[:, i90])
    assert 0.75 <= cov <= 0.87
