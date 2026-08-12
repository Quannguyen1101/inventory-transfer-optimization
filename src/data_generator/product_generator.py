"""UC-003 step 4 — sinh danh mục sản phẩm và thuộc tính theo danh mục (BR-004, BR-005, BR-009)."""
import numpy as np
import pandas as pd

from src import config

_WEIGHT_RANGE_KG = {
    "Essentials": (0.2, 2.0), "Beverages": (0.3, 2.0), "Dry Goods": (0.1, 5.0),
    "Frozen": (0.2, 3.0), "Household": (0.5, 10.0),
}
_VOLUME_RANGE_L = {
    "Essentials": (0.2, 2.0), "Beverages": (0.3, 2.0), "Dry Goods": (0.1, 5.0),
    "Frozen": (0.2, 3.0), "Household": (0.5, 15.0),
}
_COST_RANGE_VND = (10_000, 300_000)
_MARGIN_RANGE = (1.2, 1.8)  # price = cost * margin


def generate_products(num_products: int, categories: list[str], rng: np.random.Generator) -> pd.DataFrame:
    records = []
    for product_id in range(1, num_products + 1):
        category = categories[(product_id - 1) % len(categories)]
        service_level = config.SERVICE_LEVEL_BY_CATEGORY[category]
        cost = rng.uniform(*_COST_RANGE_VND)
        price = cost * rng.uniform(*_MARGIN_RANGE)
        w_lo, w_hi = _WEIGHT_RANGE_KG[category]
        v_lo, v_hi = _VOLUME_RANGE_L[category]
        records.append({
            "product_id": product_id,
            "name": f"Product {product_id:02d} - {category}",
            "category": category,
            "price": round(price, 2),
            "cost": round(cost, 2),
            "lead_time_days": config.CATEGORY_LEAD_TIME_DAYS[category],
            "service_level": service_level,
            "z_score": config.Z_SCORE_BY_SERVICE_LEVEL[service_level],
            "weight_kg": round(rng.uniform(w_lo, w_hi), 3),
            "volume_l": round(rng.uniform(v_lo, v_hi), 3),
        })
    return pd.DataFrame(records)
