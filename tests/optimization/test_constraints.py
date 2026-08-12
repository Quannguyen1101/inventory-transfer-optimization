from datetime import date
from src.optimization.constraints import (
    Batch, TransferConstraints, TransferLine,
    filter_eligible_batches, is_delivery_day, route_totals, is_feasible,
)


def test_filter_eligible_batches_excludes_near_expiry_and_sorts_fefo():
    today = date(2026, 1, 1)
    batches = [
        Batch("B1", store_id=1, product_id=1, quantity=10, expiry_date=date(2026, 1, 3)),   # < 7 days: excluded
        Batch("B2", store_id=1, product_id=1, quantity=10, expiry_date=date(2026, 2, 1)),   # eligible, later expiry
        Batch("B3", store_id=1, product_id=1, quantity=10, expiry_date=date(2026, 1, 20)),  # eligible, earlier expiry
    ]
    eligible = filter_eligible_batches(batches, current_date=today, min_shelf_life_days=7)
    assert [b.batch_id for b in eligible] == ["B3", "B2"]


def test_is_delivery_day_checks_schedule():
    schedule = {(1, 2): ["Mon", "Thu"]}
    monday = date(2026, 1, 5)  # a Monday
    tuesday = date(2026, 1, 6)
    assert is_delivery_day(1, 2, monday, schedule) is True
    assert is_delivery_day(1, 2, tuesday, schedule) is False
    assert is_delivery_day(2, 1, monday, schedule) is False  # no schedule for reverse route


def test_route_totals_sums_weight_and_volume_per_route():
    lines = [
        TransferLine(1, 2, product_id=1, batch_id="B1", quantity=10, weight_kg=5.0, volume_l=2.0),
        TransferLine(1, 2, product_id=2, batch_id="B2", quantity=5, weight_kg=3.0, volume_l=1.0),
        TransferLine(1, 3, product_id=1, batch_id="B3", quantity=8, weight_kg=4.0, volume_l=1.5),
    ]
    totals = route_totals(lines)
    assert totals[(1, 2)] == (8.0, 3.0)
    assert totals[(1, 3)] == (4.0, 1.5)


def test_is_feasible_respects_vehicle_capacity():
    constraints = TransferConstraints(vehicle_capacity_kg=10.0, vehicle_capacity_m3=5.0,
                                       delivery_schedule={}, min_shelf_life_days=7)
    ok_lines = [TransferLine(1, 2, 1, "B1", quantity=1, weight_kg=8.0, volume_l=2.0)]
    over_lines = [TransferLine(1, 2, 1, "B1", quantity=1, weight_kg=11.0, volume_l=2.0)]
    assert is_feasible(ok_lines, constraints) is True
    assert is_feasible(over_lines, constraints) is False
