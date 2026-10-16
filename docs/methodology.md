# Methodology

Detail behind the headline numbers in `README.md`. Read `docs/data-assumptions.md` first for
what the synthetic data represents.

## 1. Forecasting targets

Two models:
- **Covers** (total guests/day) — single time series.
- **Dish units** — one global LightGBM model across all 25 dishes, with dish ID as a categorical
  feature (the "M5 competition" pattern: one model learns shared seasonal/calendar structure
  across items, rather than fitting 25 separate small models on sparse per-dish data).

## 2. Features and the leakage policy

**The rule:** a forecast made at origin day T for day T+h (h = 1..7) may only use information
that would genuinely have been available at T.

To make this simple and provably correct for every horizon from 1 to 7 in one model, every lag
and rolling feature is built from data **at least 7 days old relative to the forecast origin**
(lag7, lag14, lag21, lag28; rolling mean/std over 7 and 28 days, ending 7 days before the
origin). The trade-off: the model never sees the most recent 1-6 days of actuals, even when
forecasting day T+1 where that data would technically be available. This is a deliberate
simplicity-over-marginal-accuracy choice, documented rather than hidden.

Calendar/Hijri/holiday/payday/event features are genuinely knowable in advance (they're
calendar facts or on the restaurant's own events calendar), so using them for any horizon is not
leakage.

**Enforced by test:** `tests/test_features_leakage.py` perturbs every value in the dataset after
origin T and asserts the computed features for forecasting T+1..T+7 are byte-identical to the
unperturbed run. If any feature secretly depended on post-origin data, this test fails.

**Full feature list:** day of week, month, day of month, payday window flag, Hijri month/day,
Ramadan flag + days into/until Ramadan, Eid day number, public holiday flag, local event flag,
summer flag, Riyadh Season flag, lag7/14/21/28, rolling mean/std (7d, 28d) ending at t-7, dish
category, days since menu launch, and the dish's trailing 28-day share of total unit sales.

## 3. Handling censored (stockout) days

On roughly 2-3% of dish-days, the generator caps recorded sales below true demand (a stockout).
The *true* latent demand is written to a separate file and is **never used as a model input or
training target** — `tests/test_features_leakage.py` also checks this file is absent from every
feature set.

Two approaches were compared on the actual training data:
- Down-weight censored rows (weight 0.3) and still include them: **33.0% WAPE, -0.9% bias**
- Drop censored rows entirely: **33.1% WAPE, -0.4% bias**

Nearly identical; down-weighting was kept since it uses more data without materially hurting
accuracy, but both are reported rather than silently picking the better-looking number.

## 4. Backtest design

**Rolling origin, weekly, 52 folds, Oct 2025 → Sep 2026** (the final year of the 2-year synthetic
dataset). At each fold the model is **refit from scratch using only data up to that origin**,
then scored on the real 7-day forecast that follows. This means 52 independently-trained models,
each tested on genuinely unseen future data — not a single train/test split, which would hide
how performance drifts as the forecast origin moves through the calendar (including through a
Ramadan the model has only seen once before in training).

**Metrics:** WAPE (weighted absolute percentage error, the headline — robust to low-volume
dishes dominating a simple average), bias (systematic over/under-forecasting), MAPE on non-zero
days (reported but caveated — unstable on sparse dishes), and empirical 80% interval coverage
(if the interval claims 80% coverage, we report what it actually achieved — 77-78% here, not a
perfect 80%, stated plainly).

## 5. Baselines

Two real competing methods, not strawmen:
1. **Last week, same day** — forecast(T+h) = actual sales on the same weekday, 7 days prior.
2. **4-week same-weekday average** — average of the same weekday across the last 4 weeks. This
   is a meaningfully stronger baseline than a flat historical mean (it already captures
   day-of-week seasonality), and PrepCast's model still beats it on every dish.

A third, weaker baseline (flat 28-day mean, no day-of-week adjustment) is also reported as a
floor/sanity-check, not as the main comparison.

## 6. Prep logic — newsvendor with shelf-life carryover

**Critical ratio per dish:** `Cu / (Cu + Co)`, where:
- `Cu` (cost of under-prepping / running out) = lost gross margin on that dish = price − food
  cost.
- `Co` (cost of over-prepping) = food cost × probability that portion goes unused and expires
  before its shelf life ends.

A same-day salad has a low critical ratio (over-prepping is pure waste almost immediately);
a 3-day marinated protein or sauce has a higher one (more time to sell through surplus), so the
model naturally preps a thinner margin on fragile items and a fatter one on shelf-stable items —
without being told to do so explicitly; it falls out of the ratio.

**Prep target** = the forecast quantile at that critical ratio (using the conformal quantiles
from the model). **Prep today** = `max(0, target − usable carryover)`. Carryover is consumed
FIFO and anything past its shelf life is discarded (counted as waste) rather than carried
forward indefinitely.

Rounded to whole portions, with a configurable minimum batch size per dish.

## 7. Simulation methodology

All three methods (usual, 4-week-average, PrepCast) are replayed **day by day, dish by dish**,
against the exact same hidden latent demand (the same 52 backtest weeks), so the comparison
isn't contaminated by different random seeds or different weeks being easier/harder for one
method. For each day: `available = carryover + today's prep`, `sold = min(latent demand,
available)`, `waste = portions that expire before being sold`, `stockout = latent demand - sold`.

Reported in both kg and SAR: waste valued at food cost, stockouts valued at lost gross margin
(price − food cost, i.e. what was actually foregone, not full retail price). Net cost = waste
cost + lost margin from stockouts.

**Sensitivity check:** the "usual method"'s buffer habit (assumed +10% over last week) was also
tested at 0% and +20% to confirm PrepCast's advantage isn't an artifact of picking an
unfavorable buffer for the comparison method — PrepCast's net cost is lower than the usual
method at every tested buffer level.

## 8. Known limitations

- Dish-level WAPE (33.0% overall) is meaningfully worse than covers-level WAPE (13.0%) — demand
  for an individual dish is inherently noisier than total guest count, and low-volume dishes
  (e.g. `dsrt_dates_platter`, ~4.4 units/day average) show WAPE above 49%. This is reported
  per-dish in `data/backtest_report.txt`, not averaged away.
- Ramadan performance (37.0% WAPE) is worse than normal weeks (32.7%) because the synthetic
  dataset only contains one full prior Ramadan for the model to learn from before the test
  Ramadan arrives — a realistic cold-start problem a real restaurant would also face in its
  first year or two of using this kind of system.
- The 80% prediction interval's actual empirical coverage is 77-78%, not a clean 80% — stated as
  measured, not adjusted to look better.
- All of the above comes from **synthetic data** built to be directionally realistic
  (see `docs/data-assumptions.md`), not a real restaurant's books. Real deployment requires
  retraining on that restaurant's actual history.
