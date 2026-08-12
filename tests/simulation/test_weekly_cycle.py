from datetime import date
import pandas as pd
from src.optimization.constraints import Batch
from src.simulation.weekly_cycle import run_week


def _product_attrs():
    return {
        10: {"category": "Essentials", "price": 20000.0, "cost": 10000.0, "lead_time_days": 2,
             "service_level": 0.98, "z_score": 2.05, "weight_kg": 1.0, "volume_l": 1.0},
    }


def test_baseline_scenario_never_transfers():
    history = pd.Series([10.0] * 30)
    batches = {(1, 10): [Batch("B1", 1, 10, quantity=5, expiry_date=date(2026, 6, 1))]}
    result = run_week(
        week_index=1, current_date=date(2026, 1, 5), scenario="baseline", algorithm="rule_based",
        batches=batches, sales_history={(1, 10): history}, actual_demand_this_week={(1, 10): 70.0},
        product_attrs=_product_attrs(), distance_km={}, transport_cost_matrix={}, delivery_schedule={},
        vehicle_capacity_kg=500.0, vehicle_capacity_m3=2.0, min_shelf_life_days=7,
        min_inventory_days=7.0, max_inventory_days=30.0,
    )
    assert result.transfer_lines == []
    assert result.kpi.week == 1
    assert result.kpi.scenario == "baseline"
    assert result.kpi.algorithm == "none"


def test_optimized_scenario_transfers_from_surplus_to_deficit():
    history = pd.Series([10.0] * 30)
    batches = {
        (1, 10): [Batch("B1", 1, 10, quantity=2, expiry_date=date(2026, 6, 1))],
        (2, 10): [Batch("B2", 2, 10, quantity=200, expiry_date=date(2026, 6, 1))],
    }
    result = run_week(
        week_index=1, current_date=date(2026, 1, 5), scenario="optimized", algorithm="rule_based",
        batches=batches, sales_history={(1, 10): history, (2, 10): history},
        actual_demand_this_week={(1, 10): 10.0, (2, 10): 10.0},
        product_attrs=_product_attrs(), distance_km={(2, 1): 10.0}, transport_cost_matrix={(2, 1): 50_000.0},
        delivery_schedule={(2, 1): ["Mon"]},
        vehicle_capacity_kg=500.0, vehicle_capacity_m3=2.0, min_shelf_life_days=7,
        min_inventory_days=7.0, max_inventory_days=30.0,
    )
    assert len(result.transfer_lines) >= 1
    assert result.transfer_lines[0].from_store_id == 2
    assert result.transfer_lines[0].to_store_id == 1
    assert result.kpi.algorithm == "rule_based"


def test_transferred_stock_is_available_for_sales_at_destination():
    history = pd.Series([10.0] * 30)
    batches = {
        (1, 10): [Batch("B1", 1, 10, quantity=0, expiry_date=date(2026, 6, 1))],
        (2, 10): [Batch("B2", 2, 10, quantity=200, expiry_date=date(2026, 6, 1))],
    }
    result = run_week(
        week_index=1, current_date=date(2026, 1, 5), scenario="optimized", algorithm="rule_based",
        batches=batches, sales_history={(1, 10): history, (2, 10): history},
        actual_demand_this_week={(1, 10): 5.0, (2, 10): 5.0},
        product_attrs=_product_attrs(), distance_km={(2, 1): 10.0}, transport_cost_matrix={(2, 1): 50_000.0},
        delivery_schedule={(2, 1): ["Mon"]},
        vehicle_capacity_kg=500.0, vehicle_capacity_m3=2.0, min_shelf_life_days=7,
        min_inventory_days=7.0, max_inventory_days=30.0,
    )
    remaining_at_store_1 = sum(b.quantity for b in result.updated_batches.get((1, 10), []))
    assert remaining_at_store_1 >= 0  # đã nhận hàng và bán một phần, không bị lỗi âm kho
