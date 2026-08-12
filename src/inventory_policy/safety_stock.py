"""BR-006 — safety stock = Z(service level) x sigma(demand) x sqrt(lead time)."""
import math


def compute_safety_stock(demand_std: float, z_score: float, lead_time_days: float) -> float:
    return z_score * demand_std * math.sqrt(lead_time_days)
