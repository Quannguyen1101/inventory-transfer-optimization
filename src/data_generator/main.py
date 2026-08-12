"""UC-003 — entrypoint sinh toàn bộ dữ liệu synthetic ban đầu."""
import argparse
from datetime import date, timedelta
from pathlib import Path

import numpy as np

from src import config
from src.data_generator.generator_config import SalesGenConfig
from src.data_generator.inventory_generator import generate_inventory_batches
from src.data_generator.logistics_generator import (
    generate_delivery_schedule, generate_distance_matrix, generate_transport_cost_matrix,
)
from src.data_generator.product_generator import generate_products
from src.data_generator.sales_generator import generate_sales_data
from src.data_generator.store_generator import generate_stores

_COST_PER_KM_VND = 5000.0


def run_data_generation(output_dir: Path, seed: int = config.RANDOM_SEED,
                         num_weeks: int = config.TOTAL_DATA_WEEKS) -> None:
    """`num_weeks` mặc định = HISTORY_WEEKS + SIMULATION_WEEKS: 52 tuần đầu là lịch sử mà
    forecaster được huấn luyện trên, 12 tuần cuối là nhu cầu thực tế "tương lai" mà
    `simulation.rolling_simulator` tiết lộ dần từng tuần khi chạy UC-001."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(seed)
    as_of_date = date.today()
    start_date = as_of_date - timedelta(days=num_weeks * 7)

    stores = generate_stores(config.NUM_STORES, config.CITIES, config.CITY_COORDINATES, rng)
    products = generate_products(config.NUM_PRODUCTS, config.CATEGORIES, rng)
    sales = generate_sales_data(stores, products, num_weeks, SalesGenConfig(), rng, start_date=start_date)
    batches = generate_inventory_batches(stores, products, sales, as_of_date, rng)
    distance = generate_distance_matrix(stores)
    transport_cost = generate_transport_cost_matrix(distance, _COST_PER_KM_VND)
    delivery_schedule = generate_delivery_schedule(stores, config.DELIVERY_DAYS_PER_WEEK, rng)

    stores.to_csv(output_dir / "stores.csv", index=False)
    products.to_csv(output_dir / "products.csv", index=False)
    sales.to_csv(output_dir / "sales_data.csv", index=False)
    batches.to_csv(output_dir / "inventory_batches.csv", index=False)
    distance.to_csv(output_dir / "distance_matrix.csv", index=False)
    transport_cost.to_csv(output_dir / "transport_cost_matrix.csv", index=False)
    delivery_schedule.to_csv(output_dir / "delivery_schedule.csv", index=False)


def _cli() -> None:
    parser = argparse.ArgumentParser(description="Sinh dữ liệu synthetic ban đầu (UC-003)")
    parser.add_argument("--output-dir", type=Path, default=config.DATA_DIR)
    parser.add_argument("--seed", type=int, default=config.RANDOM_SEED)
    parser.add_argument("--weeks", type=int, default=config.TOTAL_DATA_WEEKS)
    args = parser.parse_args()
    run_data_generation(args.output_dir, args.seed, args.weeks)
    print(f"Data generated at {args.output_dir}")


if __name__ == "__main__":
    _cli()
