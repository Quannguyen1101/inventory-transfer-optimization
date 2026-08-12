"""Integration test: UC-003 -> UC-001 rút gọn, xác nhận toàn bộ pipeline nối đúng."""
from src.data_generator.main import run_data_generation
from src.simulation.rolling_simulator import run_simulation


def test_full_pipeline_generate_data_then_simulate(tmp_path):
    data_dir = tmp_path / "data"
    results_dir = tmp_path / "results"
    dashboard_dir = tmp_path / "dashboard"

    run_data_generation(output_dir=data_dir, seed=1, num_weeks=3 + 2)  # 3 tuần lịch sử + 2 tuần simulation

    kpi_df = run_simulation(data_dir=data_dir, n_weeks=2, history_weeks=3, algorithm="rule_based",
                             seed=1, results_dir=results_dir, dashboard_dir=dashboard_dir)

    assert len(kpi_df) == 2 * 2  # 2 tuần x 2 kịch bản
    assert (results_dir / "kpi_timeseries.csv").exists()
    assert (dashboard_dir / "dashboard.html").exists()
    assert not kpi_df["stockout_rate"].isna().any()
    assert not kpi_df["mape"].isna().any()
