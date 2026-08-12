"""UC-003 step 6 — sinh tồn kho ban đầu theo lô hàng, kèm hạn sử dụng (BR-012)."""
from datetime import date, timedelta

import numpy as np
import pandas as pd

from src.config import CATEGORY_SHELF_LIFE_DAYS

_COVERAGE_DAYS_RANGE = (10, 20)
_RECEIVED_OFFSET_MAX_DAYS = 5


def generate_inventory_batches(stores_df: pd.DataFrame, products_df: pd.DataFrame, sales_df: pd.DataFrame,
                                as_of_date: date, rng: np.random.Generator) -> pd.DataFrame:
    avg_daily_demand = sales_df.groupby(["store_id", "product_id"])["quantity"].mean().to_dict()
    category_by_product = products_df.set_index("product_id")["category"].to_dict()
    records = []
    batch_counter = 1
    for _, store in stores_df.iterrows():
        for _, product in products_df.iterrows():
            demand = avg_daily_demand.get((store["store_id"], product["product_id"]), 1.0)
            coverage_days = rng.uniform(*_COVERAGE_DAYS_RANGE)
            quantity = max(1, int(round(demand * coverage_days)))
            received_date = as_of_date - timedelta(days=int(rng.integers(0, _RECEIVED_OFFSET_MAX_DAYS + 1)))
            shelf_life = CATEGORY_SHELF_LIFE_DAYS[category_by_product[product["product_id"]]]
            expiry_date = received_date + timedelta(days=shelf_life)
            records.append({
                "batch_id": f"B{batch_counter:06d}",
                "store_id": store["store_id"],
                "product_id": product["product_id"],
                "quantity": quantity,
                "received_date": received_date.isoformat(),
                "expiry_date": expiry_date.isoformat(),
            })
            batch_counter += 1
    return pd.DataFrame(records)
