from __future__ import annotations

import numpy as np
import pytest

from prepcast.menu import MENU, menu_by_id
from prepcast.model import QUANTILE_LEVELS
from prepcast.prep import critical_ratio, prep_quantity, quantile_at, waste_probability


def test_critical_ratio_hand_computed():
    # Hummus: price 18, food cost 0.28*18 = 5.04, margin 12.96, shelf life 3 -> P(waste)=1/3
    # Co = 5.04/3 = 1.68 ; CR = 12.96 / (12.96 + 1.68) = 0.88525
    assert critical_ratio(menu_by_id()["mez_hummus"]) == pytest.approx(12.96 / 14.64)
    # Fattoush: price 24, fc 7.68, margin 16.32, same-day -> CR = 16.32/24 = 0.68
    assert critical_ratio(menu_by_id()["mez_fattoush"]) == pytest.approx(0.68)


def test_same_day_items_get_lower_ratio_than_long_life_at_equal_cost_ratio():
    assert waste_probability(1) == 1.0
    assert waste_probability(3) == pytest.approx(1 / 3)
    for m in MENU:
        assert 0.5 < critical_ratio(m) < 1.0


def test_quantile_interp_and_clip():
    q = np.array([QUANTILE_LEVELS]) * 100  # quantile value == level*100
    assert quantile_at(q, 0.5)[0] == pytest.approx(50)
    assert quantile_at(q, 0.525)[0] == pytest.approx(52.5)
    assert quantile_at(q, 0.99)[0] == pytest.approx(95)  # clipped to P95


@pytest.mark.parametrize("target,carry,batch,expected", [
    (10.2, 0, 0, 11), (10.0, 0, 0, 10), (5, 8, 0, 0), (5, 3, 0, 2), (5, 3, 6, 6), (0, 0, 6, 0),
])
def test_prep_quantity(target, carry, batch, expected):
    assert prep_quantity(target, carry, batch) == expected


def test_prep_never_negative():
    rng = np.random.default_rng(0)
    for _ in range(500):
        assert prep_quantity(rng.uniform(-5, 50), rng.uniform(0, 60), int(rng.integers(0, 5))) >= 0
