from datetime import date
from src.inventory_policy.classifier import StockPosition
from src.optimization.constraints import Batch, TransferConstraints
from src.optimization.cost_greedy import plan_transfers_cost_greedy


def _constraints(schedule=None, capacity_m3=1000.0):
    return TransferConstraints(vehicle_capacity_kg=1000.0, vehicle_capacity_m3=capacity_m3,
                               delivery_schedule=schedule or {(2, 1): ["Mon"]}, min_shelf_life_days=7)


def _batches(store_id=2, quantity=50):
    return {(store_id, 10): [Batch(f"B{store_id}", store_id, 10, quantity=quantity, expiry_date=date(2026, 3, 1))]}


def test_transfers_whole_units_when_lost_margin_exceeds_route_cost():
    deficit = StockPosition(store_id=1, product_id=10, current_stock=5, reorder_point=25.4, safety_stock=10)
    surplus = StockPosition(store_id=2, product_id=10, current_stock=100, reorder_point=20, safety_stock=10)
    plan = plan_transfers_cost_greedy(
        deficits=[deficit], surpluses=[surplus], batches_by_store_product=_batches(),
        transport_cost={(2, 1): 50_000.0}, product_attrs={10: (1.0, 1.0)}, constraints=_constraints(),
        current_date=date(2026, 1, 5), shortage_cost_per_unit={10: 10_000.0},
    )
    assert sum(l.quantity for l in plan) == 21  # nhu cầu 20.4 -> 21 đv; 21 x 10.000 > 50.000


def test_skips_trip_whose_route_cost_exceeds_lost_margin():
    deficit = StockPosition(store_id=1, product_id=10, current_stock=23, reorder_point=25, safety_stock=10)
    surplus = StockPosition(store_id=2, product_id=10, current_stock=100, reorder_point=20, safety_stock=10)
    plan = plan_transfers_cost_greedy(
        deficits=[deficit], surpluses=[surplus], batches_by_store_product=_batches(),
        transport_cost={(2, 1): 50_000.0}, product_attrs={10: (1.0, 1.0)}, constraints=_constraints(),
        current_date=date(2026, 1, 5), shortage_cost_per_unit={10: 10_000.0},
    )
    assert plan == []  # 2 đv x 10.000 = 20.000 < phí tuyến 50.000


def test_prefers_cheaper_route_over_nearer_one():
    deficit = StockPosition(store_id=1, product_id=10, current_stock=0, reorder_point=20, safety_stock=5)
    near_expensive = StockPosition(store_id=2, product_id=10, current_stock=100, reorder_point=20, safety_stock=5)
    far_cheap = StockPosition(store_id=3, product_id=10, current_stock=100, reorder_point=20, safety_stock=5)
    plan = plan_transfers_cost_greedy(
        deficits=[deficit], surpluses=[near_expensive, far_cheap],
        batches_by_store_product={**_batches(2), **_batches(3)},
        transport_cost={(2, 1): 90_000.0, (3, 1): 30_000.0}, product_attrs={10: (1.0, 1.0)},
        constraints=_constraints({(2, 1): ["Mon"], (3, 1): ["Mon"]}),
        current_date=date(2026, 1, 5), shortage_cost_per_unit={10: 10_000.0},
    )
    assert {l.from_store_id for l in plan} == {3}


def test_caps_by_vehicle_volume_and_deducts_sources():
    deficit = StockPosition(store_id=1, product_id=10, current_stock=0, reorder_point=100, safety_stock=10)
    surplus = StockPosition(store_id=2, product_id=10, current_stock=300, reorder_point=10, safety_stock=10)
    batches = _batches(quantity=200)
    plan = plan_transfers_cost_greedy(
        deficits=[deficit], surpluses=[surplus], batches_by_store_product=batches,
        transport_cost={(2, 1): 50_000.0}, product_attrs={10: (0.1, 25.0)},  # 2000 lít / 25 = 80 đv
        constraints=_constraints(capacity_m3=2.0), current_date=date(2026, 1, 5),
        shortage_cost_per_unit={10: 10_000.0},
    )
    assert sum(l.quantity for l in plan) == 80
    assert batches[(2, 10)][0].quantity == 120
    assert surplus.current_stock == 220


def test_cannot_consolidate_small_shortfalls_onto_one_trip():
    # Giới hạn có chủ đích của greedy: xét từng thiếu hụt riêng lẻ, mỗi cái 3 đv x 10.000 = 30.000 < phí
    # tuyến 50.000 nên bị bỏ, dù gộp 2 mặt hàng trên cùng 1 chuyến (60.000 > 50.000) mới là có lời.
    deficits = [StockPosition(store_id=1, product_id=p, current_stock=0, reorder_point=3, safety_stock=1)
                for p in (10, 11)]
    surpluses = [StockPosition(store_id=2, product_id=p, current_stock=100, reorder_point=20, safety_stock=5)
                 for p in (10, 11)]
    batches = {(2, p): [Batch(f"B{p}", 2, p, quantity=50, expiry_date=date(2026, 3, 1))] for p in (10, 11)}
    plan = plan_transfers_cost_greedy(
        deficits=deficits, surpluses=surpluses, batches_by_store_product=batches,
        transport_cost={(2, 1): 50_000.0}, product_attrs={10: (1.0, 1.0), 11: (1.0, 1.0)},
        constraints=_constraints(), current_date=date(2026, 1, 5),
        shortage_cost_per_unit={10: 10_000.0, 11: 10_000.0},
    )
    assert plan == []
