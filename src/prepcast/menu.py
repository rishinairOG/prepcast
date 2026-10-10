"""The 25-item prepped menu for the synthetic restaurant.

Beverages are excluded: they are made to order and need no advance prep (documented in
docs/data-assumptions.md). food_cost_ratio of 25-35% is typical for KSA casual dining
(ASSUMPTION, within a commonly-cited industry band).
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MenuItem:
    dish_id: str
    name: str
    category: str
    price_sar: float
    food_cost_ratio: float
    portion_kg: float
    shelf_life_days: int  # 1 = same-day only
    mix_share: float      # share of total dish-units on an average normal day
    daypart_profile: dict  # fraction of this dish's daily units by daypart
    ramadan_multiplier: float = 1.0
    is_ramadan_only: bool = False
    launch_date: str | None = None   # None = available from day 1
    retire_date: str | None = None   # None = available through the end

    @property
    def food_cost_sar(self) -> float:
        return round(self.price_sar * self.food_cost_ratio, 2)

    @property
    def margin_sar(self) -> float:
        return round(self.price_sar - self.food_cost_sar, 2)


_LUNCH_DINNER_LATE = {"lunch": 0.40, "dinner": 0.50, "late": 0.10}
_DINNER_HEAVY = {"lunch": 0.20, "dinner": 0.65, "late": 0.15}
_LUNCH_HEAVY = {"lunch": 0.60, "dinner": 0.35, "late": 0.05}
_LATE_HEAVY = {"lunch": 0.10, "dinner": 0.40, "late": 0.50}

MENU: list[MenuItem] = [
    # --- Mezze / starters (5) ---
    MenuItem("mez_hummus", "Hummus", "mezze", 18, 0.28, 0.20, 3, 0.055, _LUNCH_DINNER_LATE),
    MenuItem("mez_moutabal", "Moutabal", "mezze", 20, 0.30, 0.20, 3, 0.045, _LUNCH_DINNER_LATE),
    MenuItem("mez_fattoush", "Fattoush", "mezze", 24, 0.32, 0.25, 1, 0.045, _LUNCH_DINNER_LATE),
    MenuItem("mez_sambousek", "Sambousek (6pc)", "mezze", 22, 0.30, 0.18, 2, 0.040,
             _DINNER_HEAVY, ramadan_multiplier=1.6),
    MenuItem("mez_soup", "Lentil Soup", "mezze", 16, 0.25, 0.30, 1, 0.035,
             _LUNCH_DINNER_LATE, ramadan_multiplier=2.2),
    # --- Salads (3) ---
    MenuItem("sal_caesar", "Chicken Caesar Salad", "salads", 32, 0.33, 0.35, 1, 0.050, _LUNCH_HEAVY),
    MenuItem("sal_quinoa", "Quinoa & Pomegranate Salad", "salads", 30, 0.30, 0.30, 1, 0.030, _LUNCH_HEAVY),
    MenuItem("sal_greek", "Greek Salad", "salads", 26, 0.28, 0.30, 1, 0.030, _LUNCH_HEAVY),
    # --- Grills (6) ---
    MenuItem("grl_chicken_shish", "Chicken Shish Tawook", "grills", 42, 0.32, 0.30, 1, 0.060,
             _DINNER_HEAVY, ramadan_multiplier=0.7),
    MenuItem("grl_lamb_chops", "Lamb Chops", "grills", 68, 0.35, 0.30, 1, 0.035,
             _DINNER_HEAVY, ramadan_multiplier=0.7),
    MenuItem("grl_mixed_grill", "Mixed Grill Platter", "grills", 85, 0.33, 0.45, 1, 0.045,
             _DINNER_HEAVY, ramadan_multiplier=0.8),
    MenuItem("grl_kofta", "Beef Kofta Skewers", "grills", 38, 0.32, 0.28, 1, 0.040,
             _DINNER_HEAVY, ramadan_multiplier=0.7),
    MenuItem("grl_fish", "Grilled Hammour", "grills", 58, 0.34, 0.30, 1, 0.025, _DINNER_HEAVY),
    MenuItem("grl_shrimp", "Grilled Shrimp Skewers", "grills", 52, 0.33, 0.25, 1, 0.025, _DINNER_HEAVY),
    # --- Mains / pasta (4) ---
    MenuItem("mn_chicken_alfredo", "Chicken Alfredo", "mains", 40, 0.30, 0.38, 2, 0.040, _LUNCH_DINNER_LATE),
    MenuItem("mn_beef_lasagna", "Beef Lasagna", "mains", 38, 0.30, 0.40, 2, 0.035, _LUNCH_DINNER_LATE),
    MenuItem("mn_kabsa", "Chicken Kabsa", "mains", 36, 0.28, 0.45, 1, 0.045, _LUNCH_HEAVY),
    MenuItem("mn_biryani", "Lamb Biryani", "mains", 44, 0.30, 0.42, 1, 0.030, _LUNCH_HEAVY),
    # --- Burgers / sandwiches (4) ---
    MenuItem("brg_classic", "Classic Beef Burger", "burgers", 34, 0.30, 0.25, 1, 0.050, _LATE_HEAVY),
    MenuItem("brg_chicken", "Grilled Chicken Burger", "burgers", 32, 0.30, 0.24, 1, 0.040, _LATE_HEAVY),
    MenuItem("brg_shawarma_wrap", "Chicken Shawarma Wrap", "burgers", 24, 0.28, 0.22, 1, 0.055, _LUNCH_DINNER_LATE),
    MenuItem("brg_falafel_wrap", "Falafel Wrap", "burgers", 20, 0.27, 0.20, 1, 0.030, _LUNCH_DINNER_LATE),
    # --- Desserts (3, incl. 2 lifecycle items) ---
    MenuItem("dsrt_kunafa", "Kunafa", "desserts", 22, 0.25, 0.15, 2, 0.035,
             _LATE_HEAVY, ramadan_multiplier=1.8),
    MenuItem("dsrt_dates_platter", "Ramadan Dates Platter", "desserts", 16, 0.26, 0.15, 3, 0.020,
             _DINNER_HEAVY, is_ramadan_only=True),
    MenuItem("dsrt_fresh_juice", "Fresh Juice Trio", "desserts", 20, 0.30, 0.20, 1, 0.025,
             _LUNCH_DINNER_LATE, ramadan_multiplier=1.6, is_ramadan_only=True),
]

# Lifecycle overrides applied after the base list (keeps the table above readable):
# 2 items launch mid-period, 2 items retire, 2 are Ramadan-only (already flagged above).
_LAUNCH_RETIRE = {
    "grl_shrimp": {"launch_date": "2025-06-01"},        # launches mid-period
    "mn_biryani": {"launch_date": "2025-09-15"},        # launches mid-period
    "sal_quinoa": {"retire_date": "2026-03-31"},        # retired
    "mez_soup": {"retire_date": "2026-01-31"},          # retired (soup stays available for most of Ramadan 2025 history)
}


def _apply_lifecycle(items: list[MenuItem]) -> list[MenuItem]:
    out = []
    for item in items:
        overrides = _LAUNCH_RETIRE.get(item.dish_id)
        if overrides:
            out.append(
                MenuItem(
                    **{**item.__dict__, **overrides}
                )
            )
        else:
            out.append(item)
    return out


MENU = _apply_lifecycle(MENU)

assert len(MENU) == 25, f"Expected 25 menu items, got {len(MENU)}"
assert abs(sum(m.mix_share for m in MENU) - 1.0) < 0.05, "mix_share should sum to ~1.0"


def menu_by_id() -> dict[str, MenuItem]:
    return {m.dish_id: m for m in MENU}
