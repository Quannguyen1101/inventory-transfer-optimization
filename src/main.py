"""CLI entrypoint (docs/architecture/technical-design.md Mục 4)."""
import argparse
from pathlib import Path

import pandas as pd

from src import config
from src.data_generator.main import run_data_generation
from src.reporting.dashboard_generator import generate_dashboard
from src.simulation.rolling_simulator import run_simulation


def _scenario_dirs(scenario: str) -> tuple[Path, Path, Path]:
    """Kịch bản uniform giữ các thư mục gốc; kịch bản khác dùng thư mục con cùng tên."""
    if scenario == "uniform":
        return config.DATA_DIR, config.RESULTS_DIR, config.DASHBOARD_DIR
    return config.DATA_DIR / scenario, config.RESULTS_DIR / scenario, config.DASHBOARD_DIR / scenario


def main() -> None:
    parser = argparse.ArgumentParser(description="Inventory Transfer Optimization v2")
    parser.add_argument("--generate-data", action="store_true")
    parser.add_argument("--simulate", action="store_true")
    parser.add_argument("--dashboard-only", action="store_true")
    parser.add_argument("--weeks", type=int, default=config.SIMULATION_WEEKS)
    parser.add_argument("--algorithm", choices=["rule_based", "cost_greedy", "ga", "all"], default="all")
    parser.add_argument("--seed", type=int, default=config.RANDOM_SEED)
    parser.add_argument("--scenario", choices=["uniform", "regional"], default="uniform")
    args = parser.parse_args()
    data_dir, results_dir, dashboard_dir = _scenario_dirs(args.scenario)

    if args.generate_data:
        run_data_generation(data_dir, seed=args.seed, scenario=args.scenario)
        print(f"Data generated at {data_dir}")

    if args.simulate:
        kpi_df = run_simulation(n_weeks=args.weeks, algorithm=args.algorithm, seed=args.seed, data_dir=data_dir,
                                results_dir=results_dir, dashboard_dir=dashboard_dir)
        print(f"Simulation complete: {len(kpi_df)} KPI rows written to {results_dir}")
        print(f"Dashboard written to {dashboard_dir / 'dashboard.html'}")

    if args.dashboard_only:
        kpi_df = pd.read_csv(results_dir / "kpi_timeseries.csv")
        generate_dashboard(kpi_df, dashboard_dir / "dashboard.html")
        print(f"Dashboard regenerated at {dashboard_dir / 'dashboard.html'}")

    if not (args.generate_data or args.simulate or args.dashboard_only):
        parser.print_help()


if __name__ == "__main__":
    main()
