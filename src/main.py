"""CLI entrypoint (docs/architecture/technical-design.md Mục 4)."""
import argparse

import pandas as pd

from src import config
from src.data_generator.main import run_data_generation
from src.reporting.dashboard_generator import generate_dashboard
from src.simulation.rolling_simulator import run_simulation


def main() -> None:
    parser = argparse.ArgumentParser(description="Inventory Transfer Optimization v2")
    parser.add_argument("--generate-data", action="store_true")
    parser.add_argument("--simulate", action="store_true")
    parser.add_argument("--dashboard-only", action="store_true")
    parser.add_argument("--weeks", type=int, default=config.SIMULATION_WEEKS)
    parser.add_argument("--algorithm", choices=["rule_based", "ga", "both"], default="both")
    parser.add_argument("--seed", type=int, default=config.RANDOM_SEED)
    args = parser.parse_args()

    if args.generate_data:
        run_data_generation(config.DATA_DIR, seed=args.seed)
        print(f"Data generated at {config.DATA_DIR}")

    if args.simulate:
        kpi_df = run_simulation(n_weeks=args.weeks, algorithm=args.algorithm, seed=args.seed)
        print(f"Simulation complete: {len(kpi_df)} KPI rows written to {config.RESULTS_DIR}")
        print(f"Dashboard written to {config.DASHBOARD_DIR / 'dashboard.html'}")

    if args.dashboard_only:
        kpi_df = pd.read_csv(config.RESULTS_DIR / "kpi_timeseries.csv")
        generate_dashboard(kpi_df, config.DASHBOARD_DIR / "dashboard.html")
        print(f"Dashboard regenerated at {config.DASHBOARD_DIR / 'dashboard.html'}")

    if not (args.generate_data or args.simulate or args.dashboard_only):
        parser.print_help()


if __name__ == "__main__":
    main()
