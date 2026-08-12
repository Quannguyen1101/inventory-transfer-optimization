from datetime import date
from src.inventory_policy.classifier import StockPosition
from src.optimization.constraints import Batch, TransferConstraints
from src.optimization.genetic_algorithm import plan_transfers_ga


def _base_constraints():
    return TransferConstraints(vehicle_capacity_kg=1000.0, vehicle_capacity_m3=1000.0,
                                delivery_schedule={(2, 1): ["Mon"]}, min_shelf_life_days=7)


def test_covers_deficit_within_reasonable_tolerance():
    deficit = StockPosition(store_id=1, product_id=10, current_stock=5, reorder_point=25, safety_stock=10)
    surplus = StockPosition(store_id=2, product_id=10, current_stock=100, reorder_point=20, safety_stock=10)
    batches = {(2, 10): [Batch("B1", 2, 10, quantity=50, expiry_date=date(2026, 3, 1))]}
    plan = plan_transfers_ga(
        deficits=[deficit], surpluses=[surplus], batches_by_store_product=batches,
        transport_cost={(2, 1): 50_000.0}, product_attrs={10: (1.0, 1.0)},
        constraints=_base_constraints(), current_date=date(2026, 1, 5),
        population_size=20, generations=30, seed=1,
    )
    total_transferred = sum(l.quantity for l in plan)
    assert 20 <= total_transferred <= 30  # phải >= nhu cầu (25-5=20); GA cho phép dư nhẹ do bản chất heuristic


def test_returns_empty_plan_when_no_candidates():
    deficit = StockPosition(store_id=1, product_id=10, current_stock=5, reorder_point=25, safety_stock=10)
    plan = plan_transfers_ga(
        deficits=[deficit], surpluses=[], batches_by_store_product={},
        transport_cost={}, product_attrs={10: (1.0, 1.0)},
        constraints=_base_constraints(), current_date=date(2026, 1, 5),
        population_size=10, generations=5, seed=1,
    )
    assert plan == []


def test_never_exceeds_vehicle_capacity():
    deficit = StockPosition(store_id=1, product_id=10, current_stock=0, reorder_point=100, safety_stock=10)
    surplus = StockPosition(store_id=2, product_id=10, current_stock=300, reorder_point=10, safety_stock=10)
    batches = {(2, 10): [Batch("B1", 2, 10, quantity=200, expiry_date=date(2026, 3, 1))]}
    constraints = TransferConstraints(vehicle_capacity_kg=50.0, vehicle_capacity_m3=1000.0,
                                       delivery_schedule={(2, 1): ["Mon"]}, min_shelf_life_days=7)
    plan = plan_transfers_ga(
        deficits=[deficit], surpluses=[surplus], batches_by_store_product=batches,
        transport_cost={(2, 1): 50_000.0}, product_attrs={10: (2.0, 0.5)},
        constraints=constraints, current_date=date(2026, 1, 5),
        population_size=20, generations=30, seed=1,
    )
    assert sum(l.weight_kg for l in plan) <= 50.0 + 1e-6


def test_is_reproducible_with_same_seed():
    deficit = StockPosition(store_id=1, product_id=10, current_stock=5, reorder_point=25, safety_stock=10)
    surplus = StockPosition(store_id=2, product_id=10, current_stock=100, reorder_point=20, safety_stock=10)
    kwargs = dict(deficits=[deficit], surpluses=[surplus], transport_cost={(2, 1): 50_000.0},
                  product_attrs={10: (1.0, 1.0)}, constraints=_base_constraints(),
                  current_date=date(2026, 1, 5), population_size=20, generations=30, seed=99)
    batches_a = {(2, 10): [Batch("B1", 2, 10, quantity=50, expiry_date=date(2026, 3, 1))]}
    batches_b = {(2, 10): [Batch("B1", 2, 10, quantity=50, expiry_date=date(2026, 3, 1))]}
    plan_a = plan_transfers_ga(batches_by_store_product=batches_a, **kwargs)
    plan_b = plan_transfers_ga(batches_by_store_product=batches_b, **kwargs)
    key = lambda plan: [(l.from_store_id, l.to_store_id, l.quantity) for l in plan]
    assert key(plan_a) == key(plan_b)
