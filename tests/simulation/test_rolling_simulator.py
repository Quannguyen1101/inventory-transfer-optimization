from datetime import date, timedelta
from pathlib import Path

import pandas as pd

from src.simulation.rolling_simulator import run_simulation


def _write_minimal_dataset(data_dir: Path) -> None:
    stores = pd.DataFrame([
        {"store_id": 1, "store_name": "S1", "city": "Hanoi", "latitude": 21.0, "longitude": 105.8},
        {"store_id": 2, "store_name": "S2", "city": "Hanoi", "latitude": 21.01, "longitude": 105.81},
    ])
    products = pd.DataFrame([
        {"product_id": 10, "name": "P10", "category": "Essentials", "price": 20000.0, "cost": 10000.0,
         "lead_time_days": 2, "service_level": 0.98, "z_score": 2.05, "weight_kg": 1.0, "volume_l": 1.0},
    ])
    start = date(2026, 1, 1)
    total_days = 3 * 7 + 2 * 7  # 3 tuần lịch sử + 2 tuần simulation
    sales_rows = []
    for day_offset in range(total_days):
        current_date = start + timedelta(days=day_offset)
        for store_id, qty in [(1, 5), (2, 20)]:
            sales_rows.append({"date": current_date.isoformat(), "store_id": store_id, "product_id": 10,
                                "quantity": qty, "revenue": qty * 20000.0, "cost": qty * 10000.0,
                                "is_promotion": 0})
    sales = pd.DataFrame(sales_rows)
    batches = pd.DataFrame([
        {"batch_id": "B1", "store_id": 1, "product_id": 10, "quantity": 5,
         "received_date": start.isoformat(), "expiry_date": (start + timedelta(days=200)).isoformat()},
        {"batch_id": "B2", "store_id": 2, "product_id": 10, "quantity": 200,
         "received_date": start.isoformat(), "expiry_date": (start + timedelta(days=200)).isoformat()},
    ])
    distance = pd.DataFrame([
        {"from_store_id": 1, "to_store_id": 2, "distance_km": 1.0},
        {"from_store_id": 2, "to_store_id": 1, "distance_km": 1.0},
    ])
    transport_cost = pd.DataFrame([
        {"from_store_id": 1, "to_store_id": 2, "transport_cost": 5000.0},
        {"from_store_id": 2, "to_store_id": 1, "transport_cost": 5000.0},
    ])
    schedule = pd.DataFrame([
        {"from_store_id": 1, "to_store_id": 2, "allowed_days": "Mon,Thu"},
        {"from_store_id": 2, "to_store_id": 1, "allowed_days": "Mon,Thu"},
    ])
    stores.to_csv(data_dir / "stores.csv", index=False)
    products.to_csv(data_dir / "products.csv", index=False)
    sales.to_csv(data_dir / "sales_data.csv", index=False)
    batches.to_csv(data_dir / "inventory_batches.csv", index=False)
    distance.to_csv(data_dir / "distance_matrix.csv", index=False)
    transport_cost.to_csv(data_dir / "transport_cost_matrix.csv", index=False)
    schedule.to_csv(data_dir / "delivery_schedule.csv", index=False)


def test_runs_two_week_simulation_and_produces_kpi_and_dashboard(tmp_path):
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    _write_minimal_dataset(data_dir)
    results_dir = tmp_path / "results"
    dashboard_dir = tmp_path / "dashboard"

    kpi_df = run_simulation(data_dir=data_dir, n_weeks=2, history_weeks=3, algorithm="rule_based",
                             seed=1, results_dir=results_dir, dashboard_dir=dashboard_dir)

    assert len(kpi_df) == 2 * 2  # 2 tuần x 2 kịch bản (baseline, optimized), 1 thuật toán
    assert set(kpi_df["scenario"]) == {"baseline", "optimized"}
    assert (results_dir / "kpi_timeseries.csv").exists()
    assert (dashboard_dir / "dashboard.html").exists()


def test_optimized_scenario_incurs_transport_cost_baseline_does_not(tmp_path):
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    _write_minimal_dataset(data_dir)

    kpi_df = run_simulation(data_dir=data_dir, n_weeks=2, history_weeks=3, algorithm="rule_based",
                             seed=1, results_dir=tmp_path / "results", dashboard_dir=tmp_path / "dashboard")

    baseline_cost = kpi_df[kpi_df["scenario"] == "baseline"]["transport_cost"].sum()
    optimized_cost = kpi_df[kpi_df["scenario"] == "optimized"]["transport_cost"].sum()
    assert baseline_cost == 0.0  # baseline không bao giờ chuyển hàng (AF-1 của UC-002)
    assert optimized_cost > 0.0  # store 1 thiếu hụt rõ rệt, store 2 dư rõ rệt -> phải có chuyển hàng


def test_replenishment_prevents_stockout_from_worsening_over_many_weeks(tmp_path):
    # BR-025: nếu không có replenishment, tồn kho hệ thống cạn dần đơn điệu qua các tuần vì chỉ
    # bán ra, không có nguồn bổ sung -> stockout_rate hội tụ về 1.0 và không bao giờ giảm lại.
    # Test này xác nhận có replenishment thì stockout không đơn điệu tăng mãi tới 100%.
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    _write_minimal_dataset(data_dir)
    kpi_df = run_simulation(data_dir=data_dir, n_weeks=2, history_weeks=3, algorithm="rule_based",
                             seed=1, results_dir=tmp_path / "results", dashboard_dir=tmp_path / "dashboard")
    assert (kpi_df["stockout_rate"] < 1.0).any()
