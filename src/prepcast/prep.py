"""Forecast -> prep portions.

Newsvendor with shelf-life carryover:
  Cu (cost of one portion short)  = lost gross margin = price - food cost
  Co (cost of one portion extra)  = food cost x P(the leftover portion is eventually binned)
  critical ratio CR = Cu / (Cu + Co); prep target = forecast quantile at CR.

P(binned) is approximated as 1 / shelf_life_days (ASSUMPTION): a same-day item's leftover is
always binned; a 3-day sauce's leftover usually gets sold on a later day. So same-day salads and
grills get a lower critical ratio than dips and desserts.

Prep today = max(0, ceil(target - usable carryover)), raised to min_batch if non-zero.
"""
from __future__ import annotations

import math

import numpy as np

from prepcast.menu import MenuItem
from prepcast.model import QUANTILE_LEVELS

CR_MIN, CR_MAX = QUANTILE_LEVELS[0], QUANTILE_LEVELS[-1]


def waste_probability(shelf_life_days: int) -> float:
    return 1.0 / max(1, int(shelf_life_days))


def critical_ratio(item: MenuItem) -> float:
    cu = item.price_sar - item.food_cost_sar
    co = item.food_cost_sar * waste_probability(item.shelf_life_days)
    return cu / (cu + co)


def quantile_at(qmat: np.ndarray, p: float | np.ndarray) -> np.ndarray:
    """Linear interpolation across QUANTILE_LEVELS. qmat: (n, len(QUANTILE_LEVELS)).
    p is clipped to the modelled range [P05, P95] - we never extrapolate the tails."""
    qmat = np.atleast_2d(np.asarray(qmat, float))
    p = np.broadcast_to(np.clip(np.asarray(p, float), CR_MIN, CR_MAX), (qmat.shape[0],))
    levels = np.asarray(QUANTILE_LEVELS)
    return np.array([np.interp(p[i], levels, qmat[i]) for i in range(qmat.shape[0])])


def prep_quantity(target: float, carryover: float, min_batch: int = 0) -> int:
    need = math.ceil(round(float(target) - float(carryover), 9))
    if need <= 0:
        return 0
    return max(need, int(min_batch))
