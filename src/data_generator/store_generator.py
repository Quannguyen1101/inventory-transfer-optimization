"""UC-003 step 3 — sinh danh mục cửa hàng."""
import numpy as np
import pandas as pd

_COORD_JITTER = 0.05


def generate_stores(num_stores: int, cities: list[str],
                     city_coordinates: dict[str, tuple[float, float]],
                     rng: np.random.Generator) -> pd.DataFrame:
    records = []
    for store_id in range(1, num_stores + 1):
        city = cities[(store_id - 1) % len(cities)]
        center_lat, center_lon = city_coordinates[city]
        records.append({
            "store_id": store_id,
            "store_name": f"Store {store_id:02d} - {city}",
            "city": city,
            "latitude": round(center_lat + rng.uniform(-_COORD_JITTER, _COORD_JITTER), 6),
            "longitude": round(center_lon + rng.uniform(-_COORD_JITTER, _COORD_JITTER), 6),
        })
    return pd.DataFrame(records)
