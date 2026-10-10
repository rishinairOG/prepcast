"""Rolling-origin backtest.

Weekly origins T over the final N_FOLDS weeks. At each T the model is refit on rows with
date <= T only, then predicts T+1..T+7. WARMUP_FOLDS extra origins run before the scored window
purely to build out-of-sample residuals for conformal calibration; they are flagged and excluded
from the reported metrics.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from prepcast import baselines, model

N_FOLDS = 52
WARMUP_FOLDS = 8
CALIB_FOLDS = 8
HORIZON = 7
BURN_IN_DAYS = 35          # first rows lack lag28 + 7-day roll history
CENSORED_WEIGHT = 0.3      # ASSUMPTION; compared against dropping censored rows


def make_origins(last_date: pd.Timestamp, n_folds: int = N_FOLDS,
                 warmup: int = WARMUP_FOLDS) -> list[pd.Timestamp]:
    last_origin = pd.Timestamp(last_date) - pd.Timedelta(days=HORIZON)
    return [last_origin - pd.Timedelta(weeks=k) for k in range(n_folds + warmup - 1, -1, -1)]


def training_rows(panel: pd.DataFrame, origin: pd.Timestamp) -> pd.DataFrame:
    """Rows a model fitted at `origin` may see. Never anything after the origin."""
    start = panel["date"].min() + pd.Timedelta(days=BURN_IN_DAYS)
    m = (panel["date"] <= origin) & (panel["date"] >= start) & panel["is_active"].astype(bool)
    return panel[m]


def _weights(train: pd.DataFrame, censor_mode: str) -> tuple[pd.DataFrame, np.ndarray | None]:
    flag = train["stockout_flag"].astype(bool)
    if censor_mode == "drop":
        return train[~flag], None
    if censor_mode == "downweight":
        return train, np.where(flag, CENSORED_WEIGHT, 1.0)
    if censor_mode == "none":
        return train, None
    raise ValueError(censor_mode)


def run_backtest(panel: pd.DataFrame, features: list[str], censor_mode: str = "downweight",
                 n_folds: int = N_FOLDS, warmup: int = WARMUP_FOLDS,
                 num_rounds: int = model.NUM_ROUNDS, verbose: bool = False) -> pd.DataFrame:
    origins = make_origins(panel["date"].max(), n_folds, warmup)
    results: list[pd.DataFrame] = []
    for i, origin in enumerate(origins):
        train, w = _weights(training_rows(panel, origin), censor_mode)
        assert train["date"].max() <= origin
        booster = model.fit(train, features, weight=w, num_rounds=num_rounds)

        test_mask = (panel["date"] > origin) & (panel["date"] <= origin + pd.Timedelta(days=HORIZON))
        test = panel[test_mask].copy()
        active = test["is_active"].astype(bool).values
        yhat = np.zeros(len(test))
        if active.any():
            yhat[active] = model.predict(booster, test[active], features)
        test["yhat"] = yhat
        test["base_lastweek"] = np.where(active, baselines.last_week_same_day(test), 0.0)
        test["base_4wk"] = np.where(active, baselines.same_weekday_4wk_avg(test), 0.0)
        flat = baselines.flat_28d_mean(panel[panel["date"] <= origin], origin)
        test["base_flat28"] = np.where(active, test["series_id"].map(flat).fillna(0.0), 0.0)

        prior = [r for r in results[-CALIB_FOLDS:]]
        hist = pd.concat(prior)[["series_id", "y", "yhat", "is_active"]] if prior else pd.DataFrame()
        if not hist.empty:
            hist = hist[hist["is_active"].astype(bool)]
        calib = model.calibrate(hist)
        qs = model.apply_quantiles(test["series_id"].values, yhat, calib)
        qs[~active] = 0.0
        for j, p in enumerate(model.QUANTILE_LEVELS):
            test[model.qcol(p)] = qs[:, j]

        test["origin"] = origin
        test["horizon"] = (test["date"] - origin).dt.days
        test["fold"] = i - warmup
        test["is_warmup"] = i < warmup
        results.append(test)
        if verbose:
            print(f"  fold {i - warmup:>3} origin {origin.date()} train_rows={len(train)}", flush=True)

    keep = ["date", "series_id", "origin", "horizon", "fold", "is_warmup", "is_active", "y",
            "stockout_flag", "yhat", "base_lastweek", "base_4wk", "base_flat28",
            *[model.qcol(p) for p in model.QUANTILE_LEVELS]]
    return pd.concat(results, ignore_index=True)[keep]
