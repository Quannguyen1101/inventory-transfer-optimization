from src.optimization.constraints import TransferLine
from src.simulation.kpi_tracker import (
    compute_stockout_rate, compute_excess_inventory_value, compute_transport_cost, compute_mape,
)


def test_stockout_rate_counts_keys_where_demand_exceeds_stock():
    demand = {(1, 10): 20.0, (1, 11): 5.0}
    available = {(1, 10): 15.0, (1, 11): 10.0}
    assert compute_stockout_rate(demand, available) == 0.5


def test_stockout_rate_zero_when_no_demand():
    assert compute_stockout_rate({}, {}) == 0.0


def test_excess_inventory_value_sums_only_positive_excess():
    stock = {(1, 10): 50.0, (1, 11): 5.0}
    threshold = {(1, 10): 20.0, (1, 11): 20.0}
    cost = {10: 1000.0, 11: 1000.0}
    assert compute_excess_inventory_value(stock, threshold, cost) == 30.0 * 1000.0


def test_transport_cost_sums_unique_routes_once():
    lines = [
        TransferLine(1, 2, 10, "B1", quantity=5, weight_kg=5.0, volume_l=5.0),
        TransferLine(1, 2, 11, "B2", quantity=3, weight_kg=3.0, volume_l=3.0),  # same route
        TransferLine(1, 3, 10, "B3", quantity=2, weight_kg=2.0, volume_l=2.0),
    ]
    cost_matrix = {(1, 2): 50_000.0, (1, 3): 30_000.0}
    assert compute_transport_cost(lines, cost_matrix) == 80_000.0


def test_mape_ignores_zero_actual_demand():
    forecast = {(1, 10): 12.0, (1, 11): 8.0}
    actual = {(1, 10): 10.0, (1, 11): 0.0}
    assert abs(compute_mape(forecast, actual) - 0.2) < 1e-9
