"""UC-001 — điều phối rolling simulation qua N tuần x kịch bản x thuật toán, xuất KPI + dashboard."""
from datetime import timedelta
from pathlib import Path
from typing import Literal

import pandas as pd

from src import config
from src.optimization.constraints import Batch
from src.reporting.dashboard_generator import generate_dashboard
from src.simulation.weekly_cycle import run_week


def _load_input_data(data_dir: Path):
    stores = pd.read_csv(data_dir / "stores.csv")
    products = pd.read_csv(data_dir / "products.csv")
    sales = pd.read_csv(data_dir / "sales_data.csv", parse_dates=["date"])
    batches_df = pd.read_csv(data_dir / "inventory_batches.csv", parse_dates=["received_date", "expiry_date"])
    distance_df = pd.read_csv(data_dir / "distance_matrix.csv")
    cost_df = pd.read_csv(data_dir / "transport_cost_matrix.csv")
    schedule_df = pd.read_csv(data_dir / "delivery_schedule.csv")
    return stores, products, sales, batches_df, distance_df, cost_df, schedule_df


def _to_batches_dict(batches_df: pd.DataFrame) -> dict[tuple[int, int], list[Batch]]:
    result: dict[tuple[int, int], list[Batch]] = {}
    for _, row in batches_df.iterrows():
        key = (int(row["store_id"]), int(row["product_id"]))
        result.setdefault(key, []).append(
            Batch(str(row["batch_id"]), int(row["store_id"]), int(row["product_id"]),
                  float(row["quantity"]), row["expiry_date"].date())
        )
    return result


def _pair_dict(matrix_df: pd.DataFrame, value_col: str) -> dict[tuple[int, int], float]:
    return {(int(r["from_store_id"]), int(r["to_store_id"])): float(r[value_col])
            for _, r in matrix_df.iterrows()}


def _schedule_dict(schedule_df: pd.DataFrame) -> dict[tuple[int, int], list[str]]:
    return {(int(r["from_store_id"]), int(r["to_store_id"])): str(r["allowed_days"]).split(",")
            for _, r in schedule_df.iterrows()}


def _split_history_and_future(sales: pd.DataFrame, history_weeks: int, simulation_weeks: int):
    history_days = history_weeks * 7
    initial_history: dict[tuple[int, int], pd.Series] = {}
    weekly_future: list[dict[tuple[int, int], float]] = [dict() for _ in range(simulation_weeks)]

    for (store_id, product_id), group in sales.groupby(["store_id", "product_id"]):
        group = group.sort_values("date").reset_index(drop=True)
        key = (int(store_id), int(product_id))
        initial_history[key] = group["quantity"].iloc[:history_days].reset_index(drop=True).astype(float)
        future = group["quantity"].iloc[history_days:history_days + simulation_weeks * 7].reset_index(drop=True)
        for week_index in range(simulation_weeks):
            week_slice = future.iloc[week_index * 7:(week_index + 1) * 7]
            weekly_future[week_index][key] = float(week_slice.sum())

    return initial_history, weekly_future


def run_simulation(
    data_dir: Path = config.DATA_DIR,
    n_weeks: int = config.SIMULATION_WEEKS,
    history_weeks: int = config.HISTORY_WEEKS,
    algorithm: Literal["rule_based", "ga", "both"] = "both",
    seed: int = config.RANDOM_SEED,
    results_dir: Path = config.RESULTS_DIR,
    dashboard_dir: Path = config.DASHBOARD_DIR,
) -> pd.DataFrame:
    stores, products, sales, batches_df, distance_df, cost_df, schedule_df = _load_input_data(Path(data_dir))
    product_attrs = products.set_index("product_id").to_dict(orient="index")
    distance_km = _pair_dict(distance_df, "distance_km")
    transport_cost = _pair_dict(cost_df, "transport_cost")
    delivery_schedule = _schedule_dict(schedule_df)
    initial_history, weekly_future = _split_history_and_future(sales, history_weeks, n_weeks)

    algorithms = ["rule_based", "ga"] if algorithm == "both" else [algorithm]
    all_kpi_rows = []

    for algo in algorithms:
        for scenario in ["baseline", "optimized"]:
            batches = _to_batches_dict(batches_df)
            sales_history = {key: series.copy() for key, series in initial_history.items()}

            for week_index in range(1, n_weeks + 1):
                actual_demand = weekly_future[week_index - 1]
                week_date = sales["date"].max().date() + timedelta(days=(week_index - 1) * 7 + 1)
                result = run_week(
                    week_index=week_index, current_date=week_date, scenario=scenario, algorithm=algo,
                    batches=batches, sales_history=sales_history, actual_demand_this_week=actual_demand,
                    product_attrs=product_attrs, distance_km=distance_km, transport_cost_matrix=transport_cost,
                    delivery_schedule=delivery_schedule, vehicle_capacity_kg=config.VEHICLE_CAPACITY_KG,
                    vehicle_capacity_m3=config.VEHICLE_CAPACITY_M3, min_shelf_life_days=config.MIN_SHELF_LIFE_DAYS,
                    min_inventory_days=config.MIN_INVENTORY_DAYS, max_inventory_days=config.MAX_INVENTORY_DAYS,
                    ga_seed=seed + week_index,
                )
                batches = result.updated_batches
                for key, weekly_total in actual_demand.items():
                    daily_avg = weekly_total / 7
                    existing = sales_history.get(key, pd.Series(dtype=float))
                    sales_history[key] = pd.concat([existing, pd.Series([daily_avg] * 7)], ignore_index=True)
                all_kpi_rows.append(result.kpi.__dict__)

    kpi_df = pd.DataFrame(all_kpi_rows)
    results_dir = Path(results_dir)
    results_dir.mkdir(parents=True, exist_ok=True)
    kpi_df.to_csv(results_dir / "kpi_timeseries.csv", index=False)

    dashboard_dir = Path(dashboard_dir)
    dashboard_dir.mkdir(parents=True, exist_ok=True)
    generate_dashboard(kpi_df, dashboard_dir / "dashboard.html")

    return kpi_df
