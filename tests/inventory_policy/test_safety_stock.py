import math
from src.inventory_policy.safety_stock import compute_safety_stock


def test_matches_manual_formula():
    result = compute_safety_stock(demand_std=5.0, z_score=1.65, lead_time_days=4.0)
    expected = 1.65 * 5.0 * math.sqrt(4.0)
    assert abs(result - expected) < 1e-9


def test_zero_variance_gives_zero_safety_stock():
    assert compute_safety_stock(demand_std=0.0, z_score=2.05, lead_time_days=7.0) == 0.0
