"""BR-019 — tính KPI theo tuần (stockout rate, excess inventory, transport cost, MAPE)."""
from dataclasses import dataclass

from src.optimization.constraints import TransferLine


@dataclass
class WeeklyKPI:
    week: int
    scenario: str
    algorithm: str
    stockout_rate: float
    excess_inventory_value: float
    transport_cost: float
    mape: float


def compute_stockout_rate(demand_by_key: dict[tuple[int, int], float],
                           available_stock_by_key: dict[tuple[int, int], float]) -> float:
    if not demand_by_key:
        return 0.0
    stockout_count = sum(
        1 for key, demand in demand_by_key.items() if demand > available_stock_by_key.get(key, 0.0)
    )
    return stockout_count / len(demand_by_key)


def compute_excess_inventory_value(end_of_week_stock_by_key: dict[tuple[int, int], float],
                                    threshold_by_key: dict[tuple[int, int], float],
                                    cost_by_product: dict[int, float]) -> float:
    total = 0.0
    for (store_id, product_id), stock in end_of_week_stock_by_key.items():
        excess_units = max(0.0, stock - threshold_by_key.get((store_id, product_id), 0.0))
        total += excess_units * cost_by_product.get(product_id, 0.0)
    return total


def compute_transport_cost(transfer_lines: list[TransferLine],
                            transport_cost_matrix: dict[tuple[int, int], float]) -> float:
    routes_used = {(line.from_store_id, line.to_store_id) for line in transfer_lines}
    return sum(transport_cost_matrix.get(route, 0.0) for route in routes_used)


def compute_mape(forecast_by_key: dict[tuple[int, int], float],
                  actual_by_key: dict[tuple[int, int], float]) -> float:
    errors = []
    for key, actual in actual_by_key.items():
        if actual <= 0:
            continue
        forecast = forecast_by_key.get(key, 0.0)
        errors.append(abs(actual - forecast) / actual)
    return sum(errors) / len(errors) if errors else 0.0
