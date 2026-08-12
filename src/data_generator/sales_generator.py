"""UC-003 step 5 — sinh lịch sử bán hàng có seasonality/trend/promotion (BR-001)."""
from datetime import date, timedelta

import numpy as np
import pandas as pd

from src.data_generator.generator_config import SalesGenConfig

_WEEKDAY_MULTIPLIER = {0: 0.9, 1: 0.9, 2: 0.95, 3: 1.0, 4: 1.1, 5: 1.3, 6: 1.2}  # Mon=0..Sun=6


def _pick_promotion_days(num_days: int, gen_config: SalesGenConfig, rng: np.random.Generator) -> set[int]:
    num_promos = int(round(gen_config.promotion_frequency_per_year * (num_days / 365)))
    promo_days: set[int] = set()
    attempts = 0
    max_start = max(1, num_days - gen_config.promotion_duration_days)
    while len(promo_days) < num_promos * gen_config.promotion_duration_days and attempts < 100:
        start = int(rng.integers(0, max_start))
        promo_days.update(range(start, start + gen_config.promotion_duration_days))
        attempts += 1
    return promo_days


def generate_sales_data(stores_df: pd.DataFrame, products_df: pd.DataFrame, num_weeks: int,
                         gen_config: SalesGenConfig, rng: np.random.Generator,
                         start_date: date | None = None) -> pd.DataFrame:
    if start_date is None:
        start_date = date.today() - timedelta(days=num_weeks * 7)
    num_days = num_weeks * 7
    records = []
    for _, product in products_df.iterrows():
        base_demand = rng.uniform(*gen_config.base_demand_range)
        promo_days = _pick_promotion_days(num_days, gen_config, rng)
        for _, store in stores_df.iterrows():
            store_multiplier = rng.uniform(0.7, 1.3)
            for day_offset in range(num_days):
                current_date = start_date + timedelta(days=day_offset)
                weekday_mult = 1 + gen_config.seasonality_amplitude * (
                    _WEEKDAY_MULTIPLIER[current_date.weekday()] - 1
                )
                trend_mult = (1 + gen_config.trend_weekly_growth) ** (day_offset // 7)
                is_promo = day_offset in promo_days
                promo_mult = (1 + gen_config.promotion_uplift) if is_promo else 1.0
                noise = max(rng.normal(1.0, gen_config.noise_std_ratio), 0.0)
                expected = base_demand * store_multiplier * weekday_mult * trend_mult * promo_mult * noise
                quantity = max(0, int(round(expected)))
                records.append({
                    "date": current_date.isoformat(),
                    "store_id": store["store_id"],
                    "product_id": product["product_id"],
                    "quantity": quantity,
                    "revenue": round(quantity * product["price"], 2),
                    "cost": round(quantity * product["cost"], 2),
                    "is_promotion": int(is_promo),
                })
    return pd.DataFrame(records)
