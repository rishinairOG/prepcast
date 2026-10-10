"""LightGBM global model + split-conformal quantiles.

Conformal scheme: normalized residual r = (y - yhat) / sqrt(yhat + 1) (Poisson-style scaling so
one residual distribution works across quiet and busy days). Empirical quantiles of r from the
previous CALIB_FOLDS out-of-sample weeks give any quantile: q_p = max(0, yhat + Q_p(r)*sqrt(yhat+1)).
Per series when it has enough history, otherwise pooled across all series.
"""
from __future__ import annotations

import lightgbm as lgb
import numpy as np
import pandas as pd

PARAMS = {
    "objective": "poisson",
    "learning_rate": 0.05,
    "num_leaves": 31,
    "min_data_in_leaf": 20,
    "feature_fraction": 0.9,
    "bagging_fraction": 0.9,
    "bagging_freq": 1,
    "lambda_l2": 1.0,
    "num_threads": 1,
    "deterministic": True,
    "force_row_wise": True,
    "seed": 7,
    "verbose": -1,
}
NUM_ROUNDS = 400
QUANTILE_LEVELS = [round(x, 2) for x in np.arange(0.05, 0.951, 0.05)]
MIN_CALIB_POINTS = 30


def qcol(p: float) -> str:
    return f"q{round(p * 100):02d}"


def fit(train: pd.DataFrame, features: list[str], weight: np.ndarray | None = None,
        num_rounds: int = NUM_ROUNDS) -> lgb.Booster:
    ds = lgb.Dataset(train[features], label=train["y"].astype(float), weight=weight,
                     free_raw_data=True)
    return lgb.train(PARAMS, ds, num_boost_round=num_rounds)


def predict(booster: lgb.Booster, df: pd.DataFrame, features: list[str]) -> np.ndarray:
    return np.clip(booster.predict(df[features]), 0.0, None)


def normalized_residual(y, yhat) -> np.ndarray:
    y, yhat = np.asarray(y, float), np.asarray(yhat, float)
    return (y - yhat) / np.sqrt(yhat + 1.0)


def calibrate(history: pd.DataFrame) -> dict[str, np.ndarray]:
    """history: columns series_id, y, yhat (out-of-sample only). Returns series_id -> quantile
    vector over QUANTILE_LEVELS, plus '__pooled__'."""
    out: dict[str, np.ndarray] = {}
    if history.empty:
        return out
    r_all = normalized_residual(history["y"], history["yhat"])
    out["__pooled__"] = np.quantile(r_all, QUANTILE_LEVELS)
    for sid, g in history.groupby("series_id"):
        if len(g) >= MIN_CALIB_POINTS:
            out[sid] = np.quantile(normalized_residual(g["y"], g["yhat"]), QUANTILE_LEVELS)
    return out


def apply_quantiles(series_ids, yhat, calib: dict[str, np.ndarray]) -> np.ndarray:
    """Returns array (n, len(QUANTILE_LEVELS)); NaN if no calibration exists yet."""
    yhat = np.asarray(yhat, float)
    out = np.full((len(yhat), len(QUANTILE_LEVELS)), np.nan)
    if "__pooled__" not in calib:
        return out
    scale = np.sqrt(yhat + 1.0)
    for i, sid in enumerate(series_ids):
        q = calib.get(sid, calib["__pooled__"])
        out[i] = np.clip(yhat[i] + q * scale[i], 0.0, None)
    # Enforce monotone quantiles.
    return np.maximum.accumulate(out, axis=1)
