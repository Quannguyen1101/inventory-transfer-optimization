import sys
from unittest.mock import patch

import pandas as pd

from src import config, main as main_module


def _sample_kpi_df() -> pd.DataFrame:
    return pd.DataFrame({"week": [1], "scenario": ["baseline"], "algorithm": ["none"],
                          "stockout_rate": [0.0], "excess_inventory_value": [0.0],
                          "transport_cost": [0.0], "mape": [0.0]})


def test_generate_data_flag_calls_run_data_generation(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["main.py", "--generate-data"])
    with patch("src.main.run_data_generation") as mock_generate:
        main_module.main()
        mock_generate.assert_called_once()


def test_simulate_flag_calls_run_simulation_with_parsed_args(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["main.py", "--simulate", "--weeks", "4", "--algorithm", "rule_based"])
    with patch("src.main.run_simulation") as mock_simulate:
        mock_simulate.return_value = _sample_kpi_df()
        main_module.main()
        mock_simulate.assert_called_once_with(n_weeks=4, algorithm="rule_based", seed=config.RANDOM_SEED)


def test_dashboard_only_flag_calls_generate_dashboard(monkeypatch, tmp_path):
    kpi_csv = tmp_path / "kpi_timeseries.csv"
    _sample_kpi_df().to_csv(kpi_csv, index=False)
    monkeypatch.setattr(config, "RESULTS_DIR", tmp_path)
    monkeypatch.setattr(sys, "argv", ["main.py", "--dashboard-only"])
    with patch("src.main.generate_dashboard") as mock_dashboard:
        main_module.main()
        mock_dashboard.assert_called_once()
