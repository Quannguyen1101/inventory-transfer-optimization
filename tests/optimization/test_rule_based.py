from datetime import date
from src.inventory_policy.classifier import StockPosition
from src.optimization.constraints import Batch, TransferConstraints
from src.optimization.rule_based import plan_transfers_rule_based


def _base_constraints():
    return TransferConstraints(vehicle_capacity_kg=1000.0, vehicle_capacity_m3=1000.0,
                                delivery_schedule={(2, 1): ["Mon"]}, min_shelf_life_days=7)


def test_transfers_from_eligible_surplus_to_deficit():
    deficit = StockPosition(store_id=1, product_id=10, current_stock=5, reorder_point=25, safety_stock=10)
    surplus = StockPosition(store_id=2, product_id=10, current_stock=100, reorder_point=20, safety_stock=10)
    batches = {(2, 10): [Batch("B1", 2, 10, quantity=50, expiry_date=date(2026, 3, 1))]}
    plan = plan_transfers_rule_based(
        deficits=[deficit], surpluses=[surplus], batches_by_store_product=batches,
        distance_km={(2, 1): 10.0}, product_attrs={10: (1.0, 1.0)},
        constraints=_base_constraints(), current_date=date(2026, 1, 5),
    )
    assert len(plan) == 1
    assert plan[0].from_store_id == 2 and plan[0].to_store_id == 1
    assert plan[0].quantity == 20  # reorder_point(25) - current_stock(5)


def test_skips_route_without_delivery_schedule():
    deficit = StockPosition(store_id=1, product_id=10, current_stock=5, reorder_point=25, safety_stock=10)
    surplus = StockPosition(store_id=3, product_id=10, current_stock=100, reorder_point=20, safety_stock=10)
    batches = {(3, 10): [Batch("B1", 3, 10, quantity=50, expiry_date=date(2026, 3, 1))]}
    plan = plan_transfers_rule_based(
        deficits=[deficit], surpluses=[surplus], batches_by_store_product=batches,
        distance_km={(3, 1): 10.0}, product_attrs={10: (1.0, 1.0)},
        constraints=_base_constraints(), current_date=date(2026, 1, 5),  # schedule chỉ có (2,1)
    )
    assert plan == []


def test_caps_quantity_to_stay_within_vehicle_capacity():
    deficit = StockPosition(store_id=1, product_id=10, current_stock=0, reorder_point=100, safety_stock=10)
    surplus = StockPosition(store_id=2, product_id=10, current_stock=200, reorder_point=10, safety_stock=10)
    batches = {(2, 10): [Batch("B1", 2, 10, quantity=100, expiry_date=date(2026, 3, 1))]}
    constraints = TransferConstraints(vehicle_capacity_kg=50.0, vehicle_capacity_m3=1000.0,
                                       delivery_schedule={(2, 1): ["Mon"]}, min_shelf_life_days=7)
    plan = plan_transfers_rule_based(
        deficits=[deficit], surpluses=[surplus], batches_by_store_product=batches,
        distance_km={(2, 1): 10.0}, product_attrs={10: (2.0, 0.5)},  # 2kg/unit -> capped at 25 units
        constraints=constraints, current_date=date(2026, 1, 5),
    )
    assert sum(l.weight_kg for l in plan) <= 50.0
    assert plan[0].quantity == 25


def test_caps_quantity_by_volume_in_liters():
    deficit = StockPosition(store_id=1, product_id=10, current_stock=0, reorder_point=100, safety_stock=10)
    surplus = StockPosition(store_id=2, product_id=10, current_stock=300, reorder_point=10, safety_stock=10)
    batches = {(2, 10): [Batch("B1", 2, 10, quantity=200, expiry_date=date(2026, 3, 1))]}
    constraints = TransferConstraints(vehicle_capacity_kg=1000.0, vehicle_capacity_m3=2.0,
                                       delivery_schedule={(2, 1): ["Mon"]}, min_shelf_life_days=7)
    plan = plan_transfers_rule_based(
        deficits=[deficit], surpluses=[surplus], batches_by_store_product=batches,
        distance_km={(2, 1): 10.0}, product_attrs={10: (0.1, 25.0)},  # 25 lít/đv -> 2000 lít chở được 80 đv
        constraints=constraints, current_date=date(2026, 1, 5),
    )
    assert sum(l.quantity for l in plan) == 80


def test_transfers_whole_units_covering_fractional_need():
    deficit = StockPosition(store_id=1, product_id=10, current_stock=5, reorder_point=25.4, safety_stock=10)
    surplus = StockPosition(store_id=2, product_id=10, current_stock=100, reorder_point=20, safety_stock=10)
    batches = {(2, 10): [Batch("B1", 2, 10, quantity=50, expiry_date=date(2026, 3, 1))]}
    plan = plan_transfers_rule_based(
        deficits=[deficit], surpluses=[surplus], batches_by_store_product=batches,
        distance_km={(2, 1): 10.0}, product_attrs={10: (1.0, 1.0)},
        constraints=_base_constraints(), current_date=date(2026, 1, 5),
    )
    assert plan[0].quantity == 21  # nhu cầu 20.4 -> chuyển 21 đơn vị nguyên


def test_excludes_near_expiry_batches():
    deficit = StockPosition(store_id=1, product_id=10, current_stock=5, reorder_point=25, safety_stock=10)
    surplus = StockPosition(store_id=2, product_id=10, current_stock=100, reorder_point=20, safety_stock=10)
    batches = {(2, 10): [Batch("B1", 2, 10, quantity=50, expiry_date=date(2026, 1, 8))]}  # còn 3 ngày < 7
    plan = plan_transfers_rule_based(
        deficits=[deficit], surpluses=[surplus], batches_by_store_product=batches,
        distance_km={(2, 1): 10.0}, product_attrs={10: (1.0, 1.0)},
        constraints=_base_constraints(), current_date=date(2026, 1, 5),
    )
    assert plan == []
