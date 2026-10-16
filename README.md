# PrepCast

**Stop guessing how much to prep. Forecast it, and know what it saves you.**

---

## For restaurant & hotel owners

Every kitchen prepares food before it knows exactly how many guests are coming. Prep too much
and you throw food away. Prep too little and you run out mid-service, lose the sale, and
disappoint a guest. Most kitchens solve this with a habit — "do what we did last week, plus a
bit extra" — which is really just a guess with a safety margin.

**PrepCast replaces that guess with a demand forecast**, built per dish, and converts it into a
daily prep list — how many portions of each item to prepare tomorrow, with a buffer sized to
that dish's actual shelf life and cost of running out.

### What it actually does

1. Forecasts covers (guest count) and per-dish demand for the next 7 days, using a model trained
   on sales history, day of week, local calendar effects (Ramadan, Eid, paydays, events), and
   each dish's own sales pattern.
2. Converts that forecast into a prep list: portions per dish, with a safety buffer sized to
   that dish's cost of running out vs. its cost of being thrown away.
3. Simulates what would have actually happened — day by day, dish by dish — comparing PrepCast's
   prep decisions against the "usual method" (last week + a buffer habit), using real held-out
   data the model never trained on.

### The headline result

Tested on a full year of held-out data (52 weeks, never seen during training) for a 120-seat
casual-dining restaurant in Riyadh:

| | Usual method (last week +10%) | PrepCast |
|---|---|---|
| Food wasted (binned) | 5,952 kg/year | 5,704 kg/year |
| Stockouts (ran out) | 15,216 portions/year | 6,946 portions/year |
| **Net cost** (waste + lost sales) | 615,696 SAR/year | **411,046 SAR/year** |

**PrepCast saved an estimated 204,651 SAR/year** on this test restaurant — mostly by cutting
stockouts by more than half, while slightly reducing waste too. PrepCast beat the usual method
on **every single one of the 25 menu items tested**, not just on average.

> **Important honesty note:** this is a synthetic test restaurant built to exercise the method
> realistically (see [Data & limitations](#data--limitations) below) — not a real client's
> books. It demonstrates how the approach performs, not a guaranteed result for any specific
> restaurant. A real deployment needs your actual sales history to produce real numbers.

### Try the demo

The `web/` folder is a self-contained demo (open `web/index.html` after running the pipeline
locally — see [Running it](#running-it-locally) below). It has four views:

- **Forecast** — next 7 days of covers, with a confidence band, and a toggle between a normal
  week, Ramadan week, an event day, and Eid week — each pulled from a real held-out test week
  so you can see where the forecast was right and where it missed.
- **Dishes** — every menu item's forecast, recommended prep, and how that compares to the old
  "last week" method.
- **Prep list** — a printable kitchen sheet, grouped by station (grill, mezze, dessert, etc.),
  the kind you'd actually hand to a chef.
- **Savings** — the waste/stockout/cost comparison above, plus a slider that shows the
  trade-off: prep more as a safety margin and waste goes up but stockouts go down, and vice
  versa.

---

## Technical section

### Architecture

A Python pipeline (`src/prepcast/`) does all the modelling and writes precomputed JSON; the
`web/` demo is plain HTML/CSS/JS that reads that JSON — **no framework, no build step, no
server, no computation in the browser.** This keeps the live demo honest: every number it shows
came out of the backtest, not a browser-side approximation.

```
generate (synthetic data) → backtest (leakage-safe, rolling-origin) → simulate (prep + waste)
→ export (precomputed JSON) → web/ (static demo)
```

Run end-to-end with `prepcast run`, or step by step with `prepcast generate|backtest|simulate|export`.

### Data

Two years of daily, per-dish synthetic sales for a 25-item menu, generated with documented
calendar effects (Hijri-accurate Ramadan/Eid dates via the `hijridate` package, Saudi weekend,
public holidays, paydays, local events, summer dip, menu items launching/retiring mid-period),
negative-binomial noise, and realistic stockout censoring (the model never sees true demand on
censored days — only what was actually sold). Every assumption is labelled **sourced** or
**assumption** in [`docs/data-assumptions.md`](docs/data-assumptions.md).

### Model & backtest

- **Model:** a single global LightGBM model (dish as a categorical feature, M5-style) plus
  split-conformal quantiles for uncertainty, and a separate covers model.
- **Leakage policy:** every feature for forecast horizon T+1..T+7 uses only data through T-7
  (lags ≥ 7 days), so one model is valid across the whole 7-day horizon. Enforced by an
  automated leakage test that perturbs all post-origin data and checks the forecast doesn't
  change.
- **Backtest:** rolling-origin, 52 weekly folds across a full year (Oct 2025 – Sep 2026),
  refitting at each origin on data up to that point only. That year includes a Ramadan, with
  only one earlier Ramadan available in training — a deliberately hard, realistic test.

**Results (dish-level units, WAPE, lower is better):**

| Method | WAPE | 80% interval coverage |
|---|---|---|
| Flat 28-day mean | 36.7% | — |
| Last week, same day | 45.1% | — |
| 4-week same-weekday average | 37.0% | — |
| **PrepCast (LightGBM)** | **33.0%** | 77.1% |

PrepCast's model beat every baseline on 25 of 25 dishes. It does worse in Ramadan (37.0% WAPE)
than in normal weeks (32.7%) — expected, given how little Ramadan training data exists, and
reported here rather than hidden.

### Prep logic

Each dish's prep target is a forecast quantile chosen by a **newsvendor critical ratio**:
`cost of running out / (cost of running out + cost of over-prepping)`. A same-day salad (cheap
to over-prep, costly to run out of relative to shelf life) gets a different buffer than a
3-day sauce. Carryover is tracked FIFO and expires at shelf life — full method in
[`docs/methodology.md`](docs/methodology.md).

### Tech stack

Python 3.11, `uv`, pandas, numpy, LightGBM, `hijridate` (Umm al-Qura Hijri calendar), pytest,
ruff. Demo: hand-rolled SVG charts in vanilla JS, no CDN, no framework.

### Running it locally

```bash
uv sync --extra dev
uv run prepcast run          # generate -> backtest -> simulate -> export (full pipeline)
uv run pytest                # 51 tests: generator, leakage, prep math, simulation, export
```

Then open `web/index.html` via a local static server (not `file://`, since the browser blocks
JSON fetches from the filesystem — e.g. `python -m http.server` from inside `web/`).

### Data & limitations

- **All data is synthetic**, generated to exercise the method honestly (including its failure
  modes — censoring, a hard Ramadan test, menu lifecycle changes) rather than to make the model
  look artificially good. See [`docs/data-assumptions.md`](docs/data-assumptions.md) for every
  assumption.
- The model is noticeably weaker on low-volume dishes and during Ramadan — both reported
  directly in the backtest rather than averaged away.
- This is a portfolio demonstration of method, not a production system with a real restaurant's
  historical data behind it. A real deployment would be retrained on that restaurant's actual
  sales and recalibrated.

---

## Portfolio card (copy-paste)

**Title:** PrepCast — Demand & Prep Forecaster for Restaurants

**Tags:** `Python / LightGBM` · `Time-Series Forecasting` · `Operations`

**Description:** Built a leakage-safe demand forecasting pipeline that beat baseline methods on
25/25 menu items (33% vs 37-45% WAPE) and, in a year-long backtest against a synthetic Riyadh
restaurant, cut net waste-and-stockout cost by an estimated 204,651 SAR/year — primarily by
halving stockouts while holding waste flat.
