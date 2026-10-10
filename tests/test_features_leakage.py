"""The core honesty guarantee: a forecast made at origin T cannot see anything after T."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from prepcast import model
from prepcast.backtest import HORIZON, training_rows
from prepcast.features import (
    COVERS_FEATURES,
    DISH_FEATURES,
    FORBIDDEN,
    LAGS,
    MIN_LAG,
    build_covers_panel,
    build_dish_panel,
)
from prepcast.generator import generate_all

ORIGIN = pd.Timestamp("2026-03-10")  # inside Ramadan 2026 - hardest place for leaks to matter


@pytest.fixture(scope="module")
def data():
    return generate_all()


def _perturb_after(df: pd.DataFrame, col: str, origin: pd.Timestamp, seed: int = 0) -> pd.DataFrame:
    out = df.copy()
    out["date"] = pd.to_datetime(out["date"])
    m = out["date"] > origin
    rng = np.random.default_rng(seed)
    out.loc[m, col] = rng.integers(0, 5000, size=m.sum())
    if "stockout_flag" in out.columns:
        out.loc[m, "stockout_flag"] = rng.random(m.sum()) < 0.5
    return out


def _window(panel, origin):
    m = (panel["date"] > origin) & (panel["date"] <= origin + pd.Timedelta(days=HORIZON))
    return panel[m].reset_index(drop=True)


def test_dish_features_unchanged_when_future_perturbed(data):
    clean = build_dish_panel(data["sales"], data["calendar"])
    dirty = build_dish_panel(_perturb_after(data["sales"], "units_sold", ORIGIN), data["calendar"])
    a, b = _window(clean, ORIGIN), _window(dirty, ORIGIN)
    assert not a["y"].equals(b["y"])  # sanity: perturbation actually happened
    pd.testing.assert_frame_equal(a[DISH_FEATURES], b[DISH_FEATURES])


def test_covers_features_unchanged_when_future_perturbed(data):
    clean = build_covers_panel(data["covers"], data["calendar"])
    dirty = build_covers_panel(_perturb_after(data["covers"], "covers", ORIGIN), data["calendar"])
    a, b = _window(clean, ORIGIN), _window(dirty, ORIGIN)
    assert not a["y"].equals(b["y"])
    pd.testing.assert_frame_equal(a[COVERS_FEATURES], b[COVERS_FEATURES])


def test_model_predictions_unchanged_when_future_perturbed(data):
    clean = build_dish_panel(data["sales"], data["calendar"])
    dirty = build_dish_panel(_perturb_after(data["sales"], "units_sold", ORIGIN), data["calendar"])
    preds = []
    for panel in (clean, dirty):
        train = training_rows(panel, ORIGIN)
        assert train["date"].max() <= ORIGIN
        booster = model.fit(train, DISH_FEATURES, num_rounds=30)
        preds.append(model.predict(booster, _window(panel, ORIGIN), DISH_FEATURES))
    np.testing.assert_array_equal(preds[0], preds[1])


def test_min_lag_is_at_least_horizon():
    assert MIN_LAG >= HORIZON
    assert min(LAGS) >= MIN_LAG


def test_forbidden_columns_not_features():
    for feats in (DISH_FEATURES, COVERS_FEATURES):
        assert not FORBIDDEN & set(feats)
        assert not any("latent" in f for f in feats)


def test_latent_demand_never_reaches_panel(data):
    panel = build_dish_panel(data["sales"], data["calendar"])
    assert not any("latent" in c for c in panel.columns)
    # Panel is built from observed sales: censored days carry the lower observed value.
    merged = panel.merge(data["latent_demand"].assign(date=lambda d: pd.to_datetime(d["date"])),
                         left_on=["date", "series_id"], right_on=["date", "dish_id"])
    censored = merged[merged["stockout_flag"].astype(bool)]
    assert (censored["y"] < censored["latent_demand"]).any()
