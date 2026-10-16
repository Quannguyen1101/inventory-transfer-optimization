"""UC-003 step 7 — sinh ma trận khoảng cách/chi phí và lịch giao hàng cố định (Mục 7A.2)."""
import math

import numpy as np
import pandas as pd

_WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return r * 2 * math.asin(math.sqrt(a))


def generate_distance_matrix(stores_df: pd.DataFrame) -> pd.DataFrame:
    records = []
    for _, a in stores_df.iterrows():
        for _, b in stores_df.iterrows():
            if a["store_id"] == b["store_id"]:
                continue
            records.append({
                "from_store_id": a["store_id"],
                "to_store_id": b["store_id"],
                "distance_km": round(_haversine_km(a["latitude"], a["longitude"], b["latitude"], b["longitude"]), 3),
            })
    return pd.DataFrame(records)


def generate_transport_cost_matrix(distance_df: pd.DataFrame, cost_per_km: float,
                                   fixed_cost_per_trip: float = 0.0) -> pd.DataFrame:
    """Phí 1 chuyến = phí cố định (tài xế, bốc xếp, tối thiểu mỗi chuyến) + phí theo km."""
    df = distance_df.copy()
    df["transport_cost"] = fixed_cost_per_trip + df["distance_km"] * cost_per_km
    return df[["from_store_id", "to_store_id", "transport_cost"]]


def generate_delivery_schedule(stores_df: pd.DataFrame, days_per_week: int, rng: np.random.Generator,
                               same_city_only: bool = False) -> pd.DataFrame:
    """same_city_only=True: chỉ có tuyến nội thành (kịch bản regional) — tuyến liên tỉnh tốn hàng triệu
    VNĐ/chuyến nên không lên lịch chuyển hàng ngang giữa các thành phố."""
    records = []
    for _, a in stores_df.iterrows():
        for _, b in stores_df.iterrows():
            if a["store_id"] == b["store_id"]:
                continue
            if same_city_only and a["city"] != b["city"]:
                continue
            days = sorted(rng.choice(_WEEKDAYS, size=days_per_week, replace=False),
                          key=_WEEKDAYS.index)
            records.append({
                "from_store_id": a["store_id"],
                "to_store_id": b["store_id"],
                "allowed_days": ",".join(days),
            })
    return pd.DataFrame(records)
