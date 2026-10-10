"""Central configuration for the PrepCast synthetic data pipeline.

All "magic numbers" that affect the generator, model, and simulation live here or in
``menu.py``, and are documented in ``docs/data-assumptions.md`` as SOURCED or ASSUMPTION.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = REPO_ROOT / "data"
WEB_DATA_DIR = REPO_ROOT / "web" / "data"


@dataclass(frozen=True)
class DateRangeConfig:
    start: str = "2024-10-01"
    end: str = "2026-09-30"  # inclusive; "today" in the fictional timeline is 2026-10-01
    demo_horizon_start: str = "2026-10-01"
    demo_horizon_days: int = 7


@dataclass(frozen=True)
class RestaurantConfig:
    """Baseline covers and day-of-week pattern. SOURCED: KSA weekend is Fri-Sat
    (2013 Royal decree). The index values themselves are ASSUMPTION, tuned to a
    casual-dining pattern with Thu/Fri peaks.
    """

    seats: int = 120
    baseline_covers: float = 260.0
    dow_index: dict = field(
        default_factory=lambda: {
            6: 0.85,  # Sunday (Python Monday=0 .. Sunday=6; see calendar.py for mapping)
            0: 0.85,  # Monday
            1: 0.90,  # Tuesday
            2: 0.95,  # Wednesday
            3: 1.25,  # Thursday
            4: 1.30,  # Friday
            5: 1.10,  # Saturday
        }
    )


@dataclass(frozen=True)
class SeasonalConfig:
    """ASSUMPTION unless noted. Multiplicative effects applied on top of dow_index."""

    ramadan_lunch_mult: float = 0.15       # -85%
    ramadan_dinner_mult: float = 1.20      # +20% (iftar)
    ramadan_suhoor_covers_frac: float = 0.18  # extra late daypart as frac of normal daily covers
    eid_day_mult: tuple = (1.35, 1.35, 1.25)   # Eid days 1-3
    post_eid_dip_days: int = 3
    post_eid_dip_mult: float = 0.90
    national_founding_day_mult: float = 1.30   # SOURCED dates, ASSUMPTION size
    summer_months: tuple = (6, 7, 8)
    summer_mult: float = 0.88
    riyadh_season_months: tuple = (10, 11, 12, 1, 2, 3)
    riyadh_season_weekend_mult: float = 1.06
    payday_day_of_month: int = 27             # to verify; ASSUMPTION mark in docs
    payday_boost_mult: float = 1.08
    payday_boost_span_days: int = 4           # 27th through end-of-span
    pre_payday_dip_mult: float = 0.97
    pre_payday_dip_days: tuple = (15, 26)
    annual_trend_pct: float = 0.04
    n_local_events_per_year: int = 8
    local_event_mult_range: tuple = (1.25, 1.40)


@dataclass(frozen=True)
class CensoringConfig:
    """Stockout mechanics: observed sales are capped by what was prepped."""

    target_censoring_rate: float = 0.025  # ~2-3% of dish-days
    peak_day_censoring_multiplier: float = 2.5


@dataclass(frozen=True)
class NoiseConfig:
    """Negative-binomial dispersion (overdispersed, integer, >=0). Lower r => more noise.

    covers_r=60 gives ~14% day-to-day CV on ~270 covers after all known effects - in the
    10-15% band typical of an established casual-dining venue (ASSUMPTION). dish_r=20 adds
    menu-mix noise on top of the Poisson-like count noise of a 5-20 units/day item.
    v0 used r=8 for both, which made even a perfect oracle score 27% WAPE on covers.
    """

    covers_r: float = 60.0
    dish_r: float = 20.0


@dataclass(frozen=True)
class PrepCastConfig:
    seed: int = 20261009
    dates: DateRangeConfig = field(default_factory=DateRangeConfig)
    restaurant: RestaurantConfig = field(default_factory=RestaurantConfig)
    seasonal: SeasonalConfig = field(default_factory=SeasonalConfig)
    censoring: CensoringConfig = field(default_factory=CensoringConfig)
    noise: NoiseConfig = field(default_factory=NoiseConfig)


DEFAULT_CONFIG = PrepCastConfig()
