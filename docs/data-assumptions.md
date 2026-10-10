# Data assumptions

Every numeric driver in the synthetic generator, labelled **SOURCED** (grounded in a public
fact) or **ASSUMPTION** (a reasonable guess made for this portfolio project — real client data
would replace these). This is not real restaurant data; it is built to exercise the forecasting
and prep-optimization method honestly, including its failure modes.

## Restaurant profile

| Item | Value | Label |
|---|---|---|
| Seats | 120 | ASSUMPTION |
| Baseline weekday covers | 260 | ASSUMPTION |
| Cuisine / city | Casual dining, Riyadh | ASSUMPTION (scenario choice) |
| Weekend days | Friday, Saturday | **SOURCED** — 2013 Saudi Royal decree moved the weekend to Fri-Sat |

## Day-of-week index

Sun 0.85, Mon 0.85, Tue 0.90, Wed 0.95, Thu 1.25, Fri 1.30, Sat 1.10 — ASSUMPTION, shaped to put
the peak on Thu dinner / Fri, which is the commonly reported pattern for KSA casual dining.

## Ramadan & Eid

| Item | Value | Label |
|---|---|---|
| Ramadan month | Hijri month 9, dates via Umm al-Qura (`hijridate` package) | **SOURCED** — matches the
  published Umm al-Qura calendar (verified: 1446 AH Ramadan start = 2025-03-01, 1447 AH =
  2026-02-18) |
| Ramadan lunch effect | ~-85% (mult 0.15) | ASSUMPTION |
| Ramadan dinner/iftar effect | +20% | ASSUMPTION |
| Suhoor late-daypart boost | +18% of a normal day's late-daypart covers | ASSUMPTION |
| Eid al-Fitr | 1-3 Shawwal | **SOURCED** (date), size (+35/+35/+25%) ASSUMPTION |
| Eid al-Adha | 10-12 Dhu al-Hijjah | **SOURCED** (date), size ASSUMPTION |
| Post-Eid travel dip | 3 days, -10% | ASSUMPTION |

Umm al-Qura dates can differ by +/-1 day from local moon-sighting announcements — noted as a
known limitation, not corrected for.

## Public holidays

| Item | Value | Label |
|---|---|---|
| National Day | 23 September | **SOURCED** |
| Founding Day | 22 February | **SOURCED** |
| Size of effect (+30%) | ASSUMPTION |

## Other seasonal effects (all ASSUMPTION)

- Summer (Jun-Aug): -12% (heat + travel)
- Riyadh Season (Oct-Mar): +6% on weekends; season window **SOURCED** from past editions, size
  is ASSUMPTION
- Payday: 27th of the month, +8% for day 27 through the end of a 4-day span — **the exact payday
  date (27th) is flagged "to verify" and was not independently confirmed**; treat as a placeholder
  assumption, not a sourced fact
- Pre-payday dip: days 15-26, -3%
- Local events: ~8/year, seeded random dates, +25-40% that evening — modeled as *known in
  advance* (on the restaurant's own events calendar), which makes them a legal forecast feature
- Annual trend: +4%/year

## Menu

25 prepped dishes across 6 categories (mezze, salads, grills, mains, burgers, desserts).
Beverages are excluded — made to order, no prep needed. Food-cost ratio 25-35% of price is an
ASSUMPTION within the commonly cited casual-dining band. Shelf life (1-3 days) and portion
weights are ASSUMPTION, picked per-dish to be directionally realistic (salads/grills = 1 day,
sauces/desserts = 2-3 days).

Lifecycle: `grl_shrimp` and `mn_biryani` launch mid-period (2025-06-01, 2025-09-15);
`sal_quinoa` and `mez_soup` retire (2026-03-31, 2026-01-31); `dsrt_dates_platter` and
`dsrt_fresh_juice` are Ramadan-only.

## Noise & censoring (ASSUMPTION, chosen for realism rather than measured)

- Daily counts: negative-binomial (`r=8`), overdispersed, non-negative, integer
- Stockout censoring: ~2-3% of dish-days capped below latent demand, weighted toward
  weekends/Ramadan/events/Eid ("peak" days), capturing 50-90% of true demand when it happens
- The true (uncensored) `latent_demand` is written to a separate file and is never used as a
  model input — enforced by `tests/test_features_leakage.py`

## Reproducibility

Every random draw comes from `numpy.random.default_rng(seed)` with offsets per generator stage
(`seed`, `seed+1`, `seed+2`). The same seed produces byte-identical CSVs — tested in
`tests/test_generator.py::test_reproducible_with_same_seed`.
