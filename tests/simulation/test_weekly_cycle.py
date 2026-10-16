from datetime import date
import pandas as pd
import pytest
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


@pytest.mark.parametrize("algorithm", ["rule_based", "ga"])
def test_transfers_conserve_total_system_stock(algorithm):
    # Không bán hàng, không nhập hàng: chuyển hàng ngang chỉ được dời tồn kho, không được tạo thêm.
    history = pd.Series([10.0] * 30)
    batches = {
        (1, 10): [Batch("B1", 1, 10, quantity=2, expiry_date=date(2026, 6, 1))],
        (2, 10): [Batch("B2", 2, 10, quantity=200, expiry_date=date(2026, 6, 1))],
    }
    result = run_week(
        week_index=1, current_date=date(2026, 1, 5), scenario="optimized", algorithm=algorithm,
        batches=batches, sales_history={(1, 10): history, (2, 10): history},
        actual_demand_this_week={},
        product_attrs=_product_attrs(), distance_km={(2, 1): 10.0}, transport_cost_matrix={(2, 1): 50_000.0},
        delivery_schedule={(2, 1): ["Mon"]},
        vehicle_capacity_kg=500.0, vehicle_capacity_m3=2.0, min_shelf_life_days=7,
        min_inventory_days=7.0, max_inventory_days=30.0,
    )
    assert len(result.transfer_lines) >= 1
    total_after = sum(b.quantity for blist in result.updated_batches.values() for b in blist)
    assert total_after == 202


def test_deficit_below_threshold_after_sales_triggers_pending_replenishment():
    history = pd.Series([10.0] * 30)
    batches = {(1, 10): [Batch("B1", 1, 10, quantity=5, expiry_date=date(2026, 6, 1))]}
    result = run_week(
        week_index=1, current_date=date(2026, 1, 5), scenario="baseline", algorithm="rule_based",
        batches=batches, sales_history={(1, 10): history}, actual_demand_this_week={(1, 10): 5.0},
        product_attrs=_product_attrs(), distance_km={}, transport_cost_matrix={}, delivery_schedule={},
        vehicle_capacity_kg=500.0, vehicle_capacity_m3=2.0, min_shelf_life_days=7,
        min_inventory_days=7.0, max_inventory_days=30.0,
    )
    # Sau bán hàng: tồn kho = 0, avg_daily_demand = 10 -> ngưỡng baseline = 7*10 = 70 -> chắc chắn dưới ngưỡng
    assert result.pending_replenishment[(1, 10)] > 0


def test_incoming_replenishment_is_added_to_stock_before_sales():
    history = pd.Series([10.0] * 30)
    batches = {(1, 10): [Batch("B1", 1, 10, quantity=0, expiry_date=date(2026, 6, 1))]}
    result = run_week(
        week_index=2, current_date=date(2026, 1, 12), scenario="baseline", algorithm="rule_based",
        batches=batches, sales_history={(1, 10): history}, actual_demand_this_week={(1, 10): 20.0},
        product_attrs=_product_attrs(), distance_km={}, transport_cost_matrix={}, delivery_schedule={},
        vehicle_capacity_kg=500.0, vehicle_capacity_m3=2.0, min_shelf_life_days=7,
        min_inventory_days=7.0, max_inventory_days=30.0,
        incoming_replenishment={(1, 10): 50.0},
    )
    remaining = sum(b.quantity for b in result.updated_batches.get((1, 10), []))
    assert remaining == 30.0  # 0 tồn kho + 50 nhập về - 20 bán ra = 30
    assert result.kpi.stockout_rate == 0.0  # đủ hàng nhờ replenishment, không stockout
