from src.inventory_policy.replenishment import compute_replenishment_order


def test_orders_up_to_target_level_when_below_threshold():
    result = compute_replenishment_order(current_stock=5.0, reorder_threshold=20.0, target_level=40.0)
    assert result == 35.0


def test_no_order_when_at_or_above_threshold():
    assert compute_replenishment_order(current_stock=20.0, reorder_threshold=20.0, target_level=40.0) == 0.0
    assert compute_replenishment_order(current_stock=25.0, reorder_threshold=20.0, target_level=40.0) == 0.0


def test_no_negative_order_when_target_below_current_stock():
    assert compute_replenishment_order(current_stock=5.0, reorder_threshold=20.0, target_level=3.0) == 0.0
