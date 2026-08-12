from src.inventory_policy.classifier import (
    StockStatus, StockPosition, classify_stock, classify_stock_baseline,
)


def test_below_reorder_point_is_deficit():
    pos = StockPosition(store_id=1, product_id=1, current_stock=5, reorder_point=20, safety_stock=8)
    assert classify_stock(pos) == StockStatus.DEFICIT


def test_more_than_double_reorder_point_is_surplus():
    pos = StockPosition(store_id=1, product_id=1, current_stock=50, reorder_point=20, safety_stock=8)
    assert classify_stock(pos) == StockStatus.SURPLUS


def test_between_reorder_point_and_double_is_normal():
    pos = StockPosition(store_id=1, product_id=1, current_stock=25, reorder_point=20, safety_stock=8)
    assert classify_stock(pos) == StockStatus.NORMAL


def test_baseline_below_min_days_is_deficit():
    assert classify_stock_baseline(current_stock=20, avg_daily_demand=10, min_days=7, max_days=30) == StockStatus.DEFICIT


def test_baseline_above_max_days_is_surplus():
    assert classify_stock_baseline(current_stock=400, avg_daily_demand=10, min_days=7, max_days=30) == StockStatus.SURPLUS


def test_baseline_zero_demand_is_normal():
    assert classify_stock_baseline(current_stock=100, avg_daily_demand=0, min_days=7, max_days=30) == StockStatus.NORMAL
