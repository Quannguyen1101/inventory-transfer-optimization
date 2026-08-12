"""BR-007 — reorder point = nhu cầu trung bình trong lead time + safety stock."""


def compute_reorder_point(avg_daily_demand: float, lead_time_days: float, safety_stock: float) -> float:
    return avg_daily_demand * lead_time_days + safety_stock
