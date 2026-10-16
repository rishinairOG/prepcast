"""Writes precomputed JSON for the static web demo (web/data/).

No modelling happens in the browser: every number here is read straight out of the pipeline's
own CSV outputs (backtest predictions, the kitchen simulation, the menu). Nothing is invented or
re-derived with different logic than the CLI reports in report.py use.

Four scenario weeks are picked from the real 52-fold backtest (held-out, never trained on for
that origin): a normal week, a Ramadan week, a week containing a local event day, and an
Eid al-Adha week. "Tomorrow" for the dish table / prep list is day 1 of the normal-week scenario,
so those sections show a real forecast against a real simulated prep run, not a hypothetical.
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from prepcast.config import DATA_DIR, DEFAULT_CONFIG, WEB_DATA_DIR
from prepcast.menu import menu_by_id
from prepcast.model import QUANTILE_LEVELS, qcol
from prepcast.prep import critical_ratio, quantile_at

# Real held-out backtest origins (Monday forecast-origin -> next 7 days), chosen because the
# days that follow are dominated by the labelled day type. See docs/methodology.md.
SCENARIO_ORIGINS = {
    "normal": "2025-10-15",
    "ramadan": "2026-02-25",
    "event": "2026-06-10",
    "eid": "2026-05-20",
}
SCENARIO_LABELS = {
    "normal": "Normal week",
    "ramadan": "Ramadan week",
    "event": "Event day",
    "eid": "Eid week",
}

STATION_NAMES = {
    "mezze": "Mezze / Starters station",
    "salads": "Salad station",
    "grills": "Grill station",
    "mains": "Mains / Pasta station",
    "burgers": "Burgers / Sandwiches station",
    "desserts": "Dessert station",
}


def _week(df: pd.DataFrame, origin: str) -> pd.DataFrame:
    o = pd.Timestamp(origin)
    return df[(df["date"] > o) & (df["date"] <= o + pd.Timedelta(days=7))].copy()


def build_scenarios(covers_bt: pd.DataFrame) -> dict:
    out = {}
    for key, origin in SCENARIO_ORIGINS.items():
        wk = _week(covers_bt, origin).sort_values("date")
        if wk.empty:
            raise ValueError(f"Scenario '{key}' origin {origin} has no scored backtest rows")
        out[key] = {
            "label": SCENARIO_LABELS[key],
            "origin": origin,
            "dates": [d.strftime("%Y-%m-%d") for d in wk["date"]],
            "actual": [round(v, 1) for v in wk["y"]],
            "forecast_p50": [round(v, 1) for v in wk["yhat"]],
            "forecast_p10": [round(v, 1) for v in wk["q10"]],
            "forecast_p90": [round(v, 1) for v in wk["q90"]],
            "last_week_baseline": [round(v, 1) for v in wk["base_lastweek"]],
        }
    return out


def build_dishes(dish_bt: pd.DataFrame, tomorrow: pd.Timestamp) -> list[dict]:
    menu = menu_by_id()
    day = dish_bt[(dish_bt["date"] == tomorrow) & dish_bt["is_active"].astype(bool)].copy()
    qcols = [qcol(p) for p in QUANTILE_LEVELS]
    qmat = day[qcols].to_numpy(float)
    cr = day["series_id"].map(lambda s: critical_ratio(menu[s])).to_numpy(float)
    day["recommended_prep"] = quantile_at(qmat, cr)
    rows = []
    for _, r in day.sort_values("series_id").iterrows():
        item = menu[r["series_id"]]
        rows.append({
            "dish_id": r["series_id"],
            "name": item.name,
            "category": item.category,
            "station": STATION_NAMES[item.category],
            "forecast_p50": round(float(r["yhat"]), 1),
            "forecast_p10": round(float(r["q10"]), 1),
            "forecast_p90": round(float(r["q90"]), 1),
            "recommended_prep": round(r["recommended_prep"]),
            "last_week_method": round(float(r["base_lastweek"]), 1),
            "diff_vs_last_week": round(float(r["recommended_prep"]) - float(r["base_lastweek"]), 1),
            "portion_kg": item.portion_kg,
            "shelf_life_days": item.shelf_life_days,
        })
    return rows


def build_prep_list(sim_prepcast_daily: pd.DataFrame, tomorrow: pd.Timestamp) -> dict:
    menu = menu_by_id()
    day = sim_prepcast_daily[sim_prepcast_daily["date"] == tomorrow].copy()
    items = []
    for _, r in day.sort_values("series_id").iterrows():
        item = menu[r["series_id"]]
        items.append({
            "dish_id": r["series_id"],
            "name": item.name,
            "category": item.category,
            "station": STATION_NAMES[item.category],
            "carryover_portions": int(r["carry_in"]),
            "prep_portions": int(r["prep"]),
            "prep_kg": round(float(r["prep_kg"]), 2),
        })
    items.sort(key=lambda x: (x["station"], x["name"]))
    return {"date": tomorrow.strftime("%Y-%m-%d"), "items": items}


def build_savings(sim_summary: pd.DataFrame) -> dict:
    s = sim_summary.set_index("method")

    def row(name: str) -> dict:
        r = s.loc[name]
        return {
            "waste_kg": round(float(r["waste_kg"]), 0),
            "waste_sar": round(float(r["waste_sar"]), 0),
            "stockout_portions": round(float(r["stockout_portions"]), 0),
            "lost_margin_sar": round(float(r["lost_margin_sar"]), 0),
            "net_cost_sar": round(float(r["net_cost_sar"]), 0),
            "fill_rate": round(float(r["fill_rate"]), 4),
            "waste_rate": round(float(r["waste_rate"]), 4),
        }

    usual, prepcast = s.loc["Usual (+10%)"], s.loc["PrepCast"]
    headline = {
        "waste_sar_saved": round(float(usual["waste_sar"] - prepcast["waste_sar"]), 0),
        "waste_kg_saved": round(float(usual["waste_kg"] - prepcast["waste_kg"]), 0),
        "stockout_portions_avoided": round(
            float(usual["stockout_portions"] - prepcast["stockout_portions"]), 0
        ),
        "net_cost_sar_saved": round(float(usual["net_cost_sar"] - prepcast["net_cost_sar"]), 0),
    }
    slider = {
        f"P{p}": row(f"slider_P{p}")
        for p in [round(l * 100) for l in DEFAULT_CONFIG.sim.slider_levels]
    }
    return {
        "headline": headline,
        "usual_plus_10": row("Usual (+10%)"),
        "fourwk_plus_10": row("4-wk avg (+10%)"),
        "prepcast": row("PrepCast"),
        "buffer_slider": slider,
    }


def export_all(data_dir: Path = DATA_DIR, web_data_dir: Path = WEB_DATA_DIR) -> dict[str, Path]:
    """Reads the pipeline's CSV outputs and writes web/data/*.json. Returns the written paths."""
    web_data_dir.mkdir(parents=True, exist_ok=True)

    dish_bt = pd.read_csv(data_dir / "backtest_dishes.csv", parse_dates=["date", "origin"])
    dish_bt = dish_bt[~dish_bt["is_warmup"]]
    covers_bt = pd.read_csv(data_dir / "backtest_covers.csv", parse_dates=["date", "origin"])
    covers_bt = covers_bt[~covers_bt["is_warmup"]]
    sim_summary = pd.read_csv(data_dir / "sim_summary.csv")
    sim_prepcast_daily = pd.read_csv(data_dir / "sim_prepcast_daily.csv", parse_dates=["date"])

    tomorrow = pd.Timestamp(SCENARIO_ORIGINS["normal"]) + pd.Timedelta(days=1)

    payload = {
        "scenarios.json": build_scenarios(covers_bt),
        "dishes.json": build_dishes(dish_bt, tomorrow),
        "prep_list.json": build_prep_list(sim_prepcast_daily, tomorrow),
        "savings.json": build_savings(sim_summary),
        "meta.json": {
            "generated_from": "synthetic data (see docs/data-assumptions.md)",
            "tomorrow_date": tomorrow.strftime("%Y-%m-%d"),
            "backtest_window": "2025-10-02 to 2026-09-30, 52 weekly folds",
        },
    }
    written = {}
    for fname, obj in payload.items():
        path = web_data_dir / fname
        path.write_text(json.dumps(obj, indent=2), encoding="utf-8")
        written[fname] = path
    return written
