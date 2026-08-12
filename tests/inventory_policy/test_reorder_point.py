from src.inventory_policy.reorder_point import compute_reorder_point


def test_matches_manual_formula():
    result = compute_reorder_point(avg_daily_demand=10.0, lead_time_days=3.0, safety_stock=8.0)
    assert result == 10.0 * 3.0 + 8.0
