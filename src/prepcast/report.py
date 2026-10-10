"""Builds the human-readable backtest report and saves the raw prediction tables."""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from prepcast import metrics
from prepcast.backtest import run_backtest
from prepcast.features import (
    COVERS_FEATURES,
    DISH_FEATURES,
    build_covers_panel,
    build_dish_panel,
    calendar_features,
)

METHODS = {"PrepCast (LightGBM)": "yhat", "Last week same day": "base_lastweek",
           "4-wk same-weekday avg": "base_4wk", "Flat 28-day mean": "base_flat28"}


def _fmt(df: pd.DataFrame) -> str:
    d = df.copy()
    for c in ("WAPE", "bias", "MAPE_nonzero", "cov80"):
        if c in d:
            d[c] = d[c].map(lambda v: "" if pd.isna(v) else f"{v * 100:5.1f}%")
    return d.to_string(index=False)


def _scored(preds: pd.DataFrame, calendar: pd.DataFrame) -> pd.DataFrame:
    s = preds[~preds["is_warmup"] & preds["is_active"].astype(bool)].copy()
    cal = calendar_features(calendar)
    s = s.merge(cal, on="date", how="left")
    s["segment"] = metrics.segment_of(s)
    return s


def backtest_report(calendar, covers, sales, n_folds: int = 52, compare_censoring: bool = True,
                    out_dir: Path | None = None) -> str:
    lines = []
    dp = build_dish_panel(sales, calendar)
    cp = build_covers_panel(covers, calendar)

    dish = run_backtest(dp, DISH_FEATURES, censor_mode="downweight", n_folds=n_folds)
    cov = run_backtest(cp, COVERS_FEATURES, censor_mode="none", n_folds=n_folds)
    if out_dir is not None:
        dish.to_csv(Path(out_dir) / "backtest_dishes.csv", index=False)
        cov.to_csv(Path(out_dir) / "backtest_covers.csv", index=False)

    ds, cs = _scored(dish, calendar), _scored(cov, calendar)
    lines.append(f"BACKTEST: {n_folds} weekly origins, "
                 f"{ds['date'].min().date()} -> {ds['date'].max().date()}, horizon 1-7 days")
    lines.append(f"Dish-days scored: {len(ds):,} (active dishes only)\n")

    lines.append("== DAILY COVERS ==")
    lines.append(_fmt(metrics.summary_table(cs, METHODS)))
    lines.append("\n== DISH UNITS, ALL DAYS ==")
    lines.append(_fmt(metrics.summary_table(ds, METHODS)))
    lines.append("\n== DISH UNITS BY DAY TYPE (WAPE) ==")
    seg = metrics.summary_table(ds, METHODS, by="segment")
    piv = seg.pivot(index="segment", columns="method", values="WAPE")[list(METHODS)]
    n = seg.groupby("segment")["n"].first()
    piv.insert(0, "n", n)
    lines.append(_fmt_pivot(piv))

    lines.append("\n== PER DISH (WAPE), model vs best baseline ==")
    rows = []
    for sid, g in ds.groupby("series_id"):
        m = metrics.wape(g["y"], g["yhat"])
        b = min(metrics.wape(g["y"], g["base_lastweek"]), metrics.wape(g["y"], g["base_4wk"]))
        rows.append({"dish": sid, "avg/day": g["y"].mean(), "model": m, "best_base": b,
                     "winner": "model" if m < b else "BASELINE"})
    pdish = pd.DataFrame(rows).sort_values("avg/day", ascending=False)
    lines.append(pdish.to_string(index=False, formatters={
        "avg/day": "{:.1f}".format, "model": lambda v: f"{v*100:.1f}%",
        "best_base": lambda v: f"{v*100:.1f}%"}))
    lines.append(f"Model wins on {(pdish['winner'] == 'model').sum()}/{len(pdish)} dishes.")

    h = ds.groupby("horizon").apply(lambda g: metrics.wape(g["y"], g["yhat"]), include_groups=False)
    lines.append("\n== MODEL WAPE BY HORIZON (days ahead) ==")
    lines.append("  ".join(f"h{k}:{v*100:.1f}%" for k, v in h.items()))

    if compare_censoring:
        alt = _scored(run_backtest(dp, DISH_FEATURES, censor_mode="drop", n_folds=n_folds), calendar)
        lines.append("\n== CENSORED-ROW HANDLING (dish WAPE / bias) ==")
        for name, d in (("down-weight 0.3", ds), ("drop censored rows", alt)):
            lines.append(f"  {name:<20} WAPE {metrics.wape(d['y'], d['yhat'])*100:.1f}%  "
                         f"bias {metrics.bias(d['y'], d['yhat'])*100:+.1f}%")
    return "\n".join(lines)


def _fmt_pivot(piv: pd.DataFrame) -> str:
    d = piv.copy()
    for c in d.columns:
        if c != "n":
            d[c] = d[c].map(lambda v: f"{v * 100:.1f}%")
    return d.to_string()


def savings_report(preds: pd.DataFrame, latent: pd.DataFrame, out_dir: Path | None = None) -> str:
    from prepcast.simulate import simulate_all

    scored = preds[~preds["is_warmup"]].copy()
    summary, frames = simulate_all(scored, latent)
    if out_dir is not None:
        summary.to_csv(Path(out_dir) / "sim_summary.csv", index=False)
        frames["PrepCast"].to_csv(Path(out_dir) / "sim_prepcast_daily.csv", index=False)
        frames["Usual (+10%)"].to_csv(Path(out_dir) / "sim_usual_daily.csv", index=False)

    s = summary.set_index("method")
    main_rows = ["Usual (+10%)", "4-wk avg (+10%)", "PrepCast"]
    lines = [(f"SIMULATION: {scored['date'].min().date()} -> {scored['date'].max().date()}, "
             f"{scored['series_id'].nunique()} dishes, replayed against hidden true demand."),
             ("All money figures annualised to 52 weeks, SAR. Waste valued at food cost; "
             "stockouts valued at lost gross margin.\n")]

    def table(rows):
        cols = ["waste_kg", "waste_sar", "stockout_portions", "lost_margin_sar", "net_cost_sar",
                "fill_rate", "waste_rate"]
        t = s.loc[rows, cols].copy()
        fm = {"waste_kg": "{:,.0f}".format, "waste_sar": "{:,.0f}".format,
              "stockout_portions": "{:,.0f}".format, "lost_margin_sar": "{:,.0f}".format,
              "net_cost_sar": "{:,.0f}".format, "fill_rate": lambda v: f"{v*100:.1f}%",
              "waste_rate": lambda v: f"{v*100:.1f}%"}
        return t.to_string(formatters=fm)

    lines.append("== HEADLINE ==")
    lines.append(table(main_rows))
    u, p = s.loc["Usual (+10%)"], s.loc["PrepCast"]
    lines.append(
        f"\nPrepCast vs usual method: waste {u.waste_sar - p.waste_sar:+,.0f} SAR saved "
        f"({u.waste_kg - p.waste_kg:,.0f} kg less binned), stockout portions "
        f"{u.stockout_portions - p.stockout_portions:+,.0f} avoided, "
        f"net {u.net_cost_sar - p.net_cost_sar:+,.0f} SAR/year better.")

    lines.append("\n== SENSITIVITY: usual-method buffer ==")
    lines.append(table([r for r in s.index if r.startswith(("Usual", "4-wk"))]))

    lines.append("\n== BUFFER SLIDER (one service level for every dish) ==")
    lines.append(table([r for r in s.index if r.startswith("slider_")]))

    pc, us = frames["PrepCast"], frames["Usual (+10%)"]
    by = pd.DataFrame({
        "net_prepcast": pc.groupby("series_id")[["waste_sar", "lost_margin_sar"]].sum().sum(axis=1),
        "net_usual": us.groupby("series_id")[["waste_sar", "lost_margin_sar"]].sum().sum(axis=1),
    })
    by["winner"] = (by["net_prepcast"] < by["net_usual"]).map({True: "PrepCast", False: "USUAL"})
    lines.append(f"\nPer-dish net cost: PrepCast better on {(by['winner'] == 'PrepCast').sum()}"
                 f"/{len(by)} dishes. Usual method wins on: "
                 f"{', '.join(by.index[by['winner'] == 'USUAL']) or 'none'}")
    return "\n".join(lines)
