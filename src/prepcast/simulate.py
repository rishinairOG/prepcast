"""Day-by-day kitchen simulation.

For each dish and day: available = carryover + prep; sold = min(true demand, available), taken
FIFO (oldest portions first); portions past their shelf life at close are binned (waste);
unmet demand is a stockout. Every method is replayed against the SAME hidden true demand
(latent_demand), which is what guests actually wanted - the forecasts never saw it.

Conservation (tested): prep + carry_in = sold + waste + carry_out, every dish-day.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from prepcast.config import DEFAULT_CONFIG, SimConfig
from prepcast.menu import MENU, menu_by_id
from prepcast.model import QUANTILE_LEVELS, qcol
from prepcast.prep import critical_ratio, prep_quantity, quantile_at

QCOLS = [qcol(p) for p in QUANTILE_LEVELS]


def simulate_dish(targets, demand, shelf_life: int, min_batch: int = 0) -> dict[str, np.ndarray]:
    targets = np.asarray(targets, float)
    demand = np.asarray(demand, int)
    n = len(targets)
    out = {k: np.zeros(n, dtype=int) for k in
           ("carry_in", "prep", "sold", "waste", "carry_out", "stockout")}
    inv: list[list[int]] = []  # [units, selling days left incl. today], oldest first
    for t in range(n):
        carry_in = sum(u for u, _ in inv)
        prep = prep_quantity(targets[t], carry_in, min_batch)
        if prep:
            inv.append([prep, int(shelf_life)])
        want = int(demand[t])
        sold = 0
        for batch in inv:
            take = min(batch[0], want - sold)
            batch[0] -= take
            sold += take
            if sold == want:
                break
        waste = 0
        kept = []
        for units, left in inv:
            if units == 0:
                continue
            if left - 1 <= 0:
                waste += units
            else:
                kept.append([units, left - 1])
        inv = kept
        out["carry_in"][t], out["prep"][t], out["sold"][t] = carry_in, prep, sold
        out["waste"][t], out["carry_out"][t] = waste, sum(u for u, _ in inv)
        out["stockout"][t] = want - sold
    return out


def method_targets(preds: pd.DataFrame, sim: SimConfig = DEFAULT_CONFIG.sim) -> dict[str, np.ndarray]:
    """Prep targets per method, aligned to `preds` rows. Inactive dishes get 0."""
    active = preds["is_active"].astype(bool).values
    qmat = preds[QCOLS].to_numpy(float)
    qmat = np.where(np.isnan(qmat), preds["yhat"].to_numpy(float)[:, None], qmat)
    menu = menu_by_id()
    cr = preds["series_id"].map(lambda s: critical_ratio(menu[s])).to_numpy(float)

    def z(x):
        return np.where(active, x, 0.0)

    t = {"PrepCast": z(quantile_at(qmat, cr))}
    for b in sim.buffer_sensitivity:
        t[f"Usual (+{b:.0%})"] = z(preds["base_lastweek"].to_numpy(float) * (1 + b))
        t[f"4-wk avg (+{b:.0%})"] = z(preds["base_4wk"].to_numpy(float) * (1 + b))
    for p in sim.slider_levels:
        t[f"slider_P{round(p * 100)}"] = z(quantile_at(qmat, p))
    return t


def run(preds: pd.DataFrame, latent: pd.DataFrame, targets: np.ndarray,
        sim: SimConfig = DEFAULT_CONFIG.sim) -> pd.DataFrame:
    """Simulate one method across all dishes. Returns one row per (date, dish)."""
    df = preds[["date", "series_id"]].copy()
    df["target"] = targets
    lat = latent.rename(columns={"dish_id": "series_id"})
    lat["date"] = pd.to_datetime(lat["date"])
    df = df.merge(lat, on=["date", "series_id"], how="left", validate="one_to_one")
    df = df.sort_values(["series_id", "date"]).reset_index(drop=True)
    menu = menu_by_id()
    parts = []
    for sid, g in df.groupby("series_id", sort=True):
        item = menu[sid]
        res = simulate_dish(g["target"], g["latent_demand"], item.shelf_life_days, sim.min_batch)
        part = g.assign(**res)
        part["waste_kg"] = part["waste"] * item.portion_kg
        part["waste_sar"] = part["waste"] * item.food_cost_sar
        part["prep_kg"] = part["prep"] * item.portion_kg
        part["lost_revenue_sar"] = part["stockout"] * item.price_sar
        part["lost_margin_sar"] = part["stockout"] * item.margin_sar
        part["food_cost_prepped_sar"] = part["prep"] * item.food_cost_sar
        parts.append(part)
    return pd.concat(parts, ignore_index=True)


def summarize(sim_df: pd.DataFrame) -> dict[str, float]:
    days = sim_df["date"].nunique()
    scale = 364.0 / days  # annualise to a 52-week year
    demand = sim_df["latent_demand"].sum()
    s = {
        "waste_portions": sim_df["waste"].sum() * scale,
        "waste_kg": sim_df["waste_kg"].sum() * scale,
        "waste_sar": sim_df["waste_sar"].sum() * scale,
        "stockout_portions": sim_df["stockout"].sum() * scale,
        "lost_revenue_sar": sim_df["lost_revenue_sar"].sum() * scale,
        "lost_margin_sar": sim_df["lost_margin_sar"].sum() * scale,
        "fill_rate": sim_df["sold"].sum() / demand if demand else float("nan"),
        "waste_rate": sim_df["waste"].sum() / max(1, sim_df["prep"].sum()),
        "stockout_days_pct": float((sim_df["stockout"] > 0).mean()),
    }
    s["net_cost_sar"] = s["waste_sar"] + s["lost_margin_sar"]
    return s


def simulate_all(preds: pd.DataFrame, latent: pd.DataFrame,
                 sim: SimConfig = DEFAULT_CONFIG.sim) -> tuple[pd.DataFrame, dict[str, pd.DataFrame]]:
    """preds: scored (non-warm-up) backtest rows for dishes. Returns (summary table, per-method
    simulation frames)."""
    preds = preds.sort_values(["date", "series_id"]).reset_index(drop=True)
    assert not preds.duplicated(["date", "series_id"]).any(), "one forecast per dish-day expected"
    frames = {name: run(preds, latent, t, sim) for name, t in method_targets(preds, sim).items()}
    rows = [{"method": k, **summarize(v)} for k, v in frames.items()]
    return pd.DataFrame(rows), frames


DISHES = [m.dish_id for m in MENU]
