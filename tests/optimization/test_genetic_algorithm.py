from datetime import date
from src.inventory_policy.classifier import StockPosition
from src.optimization.constraints import Batch, TransferConstraints, TransferLine
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


def test_never_draws_more_than_surplus_available_across_deficits():
    d1 = StockPosition(store_id=1, product_id=10, current_stock=0, reorder_point=25, safety_stock=5)
    d3 = StockPosition(store_id=3, product_id=10, current_stock=0, reorder_point=25, safety_stock=5)
    surplus = StockPosition(store_id=2, product_id=10, current_stock=50, reorder_point=20, safety_stock=5)  # dư 30
    batches = {(2, 10): [Batch("B1", 2, 10, quantity=50, expiry_date=date(2026, 3, 1))]}
    constraints = TransferConstraints(vehicle_capacity_kg=1000.0, vehicle_capacity_m3=1000.0,
                                       delivery_schedule={(2, 1): ["Mon"], (2, 3): ["Mon"]}, min_shelf_life_days=7)
    plan = plan_transfers_ga(
        deficits=[d1, d3], surpluses=[surplus], batches_by_store_product=batches,
        transport_cost={(2, 1): 1_000.0, (2, 3): 1_000.0}, product_attrs={10: (1.0, 1.0)},
        constraints=constraints, current_date=date(2026, 1, 5),
        population_size=20, generations=30, seed=1,
    )
    assert sum(l.quantity for l in plan) <= 30


def test_deducts_transferred_quantity_from_source_like_rule_based():
    deficit = StockPosition(store_id=1, product_id=10, current_stock=5, reorder_point=25, safety_stock=10)
    surplus = StockPosition(store_id=2, product_id=10, current_stock=100, reorder_point=20, safety_stock=10)
    batches = {(2, 10): [Batch("B1", 2, 10, quantity=50, expiry_date=date(2026, 3, 1))]}
    plan = plan_transfers_ga(
        deficits=[deficit], surpluses=[surplus], batches_by_store_product=batches,
        transport_cost={(2, 1): 50_000.0}, product_attrs={10: (1.0, 1.0)},
        constraints=_base_constraints(), current_date=date(2026, 1, 5),
        population_size=20, generations=30, seed=1,
    )
    transferred = sum(l.quantity for l in plan)
    assert transferred > 0
    assert batches[(2, 10)][0].quantity == 50 - transferred
    assert surplus.current_stock == 100 - transferred


def test_caps_quantity_by_volume_in_liters():
    deficit = StockPosition(store_id=1, product_id=10, current_stock=0, reorder_point=100, safety_stock=10)
    surplus = StockPosition(store_id=2, product_id=10, current_stock=300, reorder_point=10, safety_stock=10)
    batches = {(2, 10): [Batch("B1", 2, 10, quantity=200, expiry_date=date(2026, 3, 1))]}
    constraints = TransferConstraints(vehicle_capacity_kg=1000.0, vehicle_capacity_m3=2.0,
                                       delivery_schedule={(2, 1): ["Mon"]}, min_shelf_life_days=7)
    plan = plan_transfers_ga(
        deficits=[deficit], surpluses=[surplus], batches_by_store_product=batches,
        transport_cost={(2, 1): 50_000.0}, product_attrs={10: (0.1, 25.0)},  # 2000 lít / 25 = 80 đv
        constraints=constraints, current_date=date(2026, 1, 5),
        population_size=20, generations=30, seed=1,
    )
    assert sum(l.quantity for l in plan) == 80


def _total_cost(plan, deficits, transport_cost, shortage_cost):
    import math
    routes = {(l.from_store_id, l.to_store_id) for l in plan}
    delivered = {}
    for l in plan:
        delivered[(l.to_store_id, l.product_id)] = delivered.get((l.to_store_id, l.product_id), 0) + l.quantity
    shortage = sum((math.ceil(d.reorder_point - d.current_stock) - delivered.get((d.store_id, d.product_id), 0))
                   * shortage_cost[d.product_id] for d in deficits)
    return sum(transport_cost[r] for r in routes) + shortage


def test_skips_transfer_whose_route_costs_more_than_the_shortage_it_fixes():
    # thiếu 2 đv, biên lợi nhuận 1.000đ/đv -> thiệt hại 2.000đ < phí tuyến 50.000đ: không nên chạy xe
    deficit = StockPosition(store_id=1, product_id=10, current_stock=23, reorder_point=25, safety_stock=10)
    surplus = StockPosition(store_id=2, product_id=10, current_stock=100, reorder_point=20, safety_stock=10)
    batches = {(2, 10): [Batch("B1", 2, 10, quantity=50, expiry_date=date(2026, 3, 1))]}
    plan = plan_transfers_ga(
        deficits=[deficit], surpluses=[surplus], batches_by_store_product=batches,
        transport_cost={(2, 1): 50_000.0}, product_attrs={10: (1.0, 1.0)},
        constraints=_base_constraints(), current_date=date(2026, 1, 5),
        population_size=20, generations=30, seed=1, shortage_cost_per_unit={10: 1_000.0},
    )
    assert plan == []


def test_seeded_ga_is_never_worse_than_its_seed_plan():
    deficits = [StockPosition(store_id=s, product_id=10, current_stock=0, reorder_point=r, safety_stock=5)
                for s, r in [(1, 30), (3, 4), (4, 25)]]
    surpluses = [StockPosition(store_id=2, product_id=10, current_stock=100, reorder_point=20, safety_stock=5),
                 StockPosition(store_id=5, product_id=10, current_stock=60, reorder_point=20, safety_stock=5)]
    schedule = {(src, dst): ["Mon"] for src in (2, 5) for dst in (1, 3, 4)}
    cost = {(2, 1): 30_000.0, (2, 3): 90_000.0, (2, 4): 20_000.0, (5, 1): 10_000.0, (5, 3): 40_000.0,
            (5, 4): 70_000.0}
    shortage_cost = {10: 5_000.0}
    constraints = TransferConstraints(vehicle_capacity_kg=1000.0, vehicle_capacity_m3=1000.0,
                                       delivery_schedule=schedule, min_shelf_life_days=7)

    def fresh_batches():
        return {(2, 10): [Batch("B2", 2, 10, quantity=100, expiry_date=date(2026, 3, 1))],
                (5, 10): [Batch("B5", 5, 10, quantity=60, expiry_date=date(2026, 3, 1))]}

    seed_plan = [TransferLine(2, 1, 10, "B2", 30, 30.0, 30.0), TransferLine(2, 3, 10, "B2", 4, 4.0, 4.0),
                 TransferLine(5, 4, 10, "B5", 25, 25.0, 25.0)]
    import copy
    plan = plan_transfers_ga(
        deficits=copy.deepcopy(deficits), surpluses=copy.deepcopy(surpluses), batches_by_store_product=fresh_batches(),
        transport_cost=cost, product_attrs={10: (1.0, 1.0)}, constraints=constraints, current_date=date(2026, 1, 5),
        population_size=20, generations=30, seed=1, seed_plan=seed_plan, shortage_cost_per_unit=shortage_cost,
    )
    assert _total_cost(plan, deficits, cost, shortage_cost) <= _total_cost(seed_plan, deficits, cost, shortage_cost)


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
