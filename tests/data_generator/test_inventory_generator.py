import numpy as np
from datetime import date
from src.data_generator.store_generator import generate_stores
from src.data_generator.product_generator import generate_products
from src.data_generator.generator_config import SalesGenConfig
from src.data_generator.sales_generator import generate_sales_data
from src.data_generator.inventory_generator import generate_inventory_batches
from src import config


def test_generates_one_batch_per_store_product_pair():
    rng = np.random.default_rng(42)
    stores = generate_stores(3, config.CITIES, config.CITY_COORDINATES, rng)
    products = generate_products(2, config.CATEGORIES, rng)
    sales = generate_sales_data(stores, products, num_weeks=2, gen_config=SalesGenConfig(), rng=rng,
                                 start_date=date(2026, 1, 5))
    batches = generate_inventory_batches(stores, products, sales, as_of_date=date(2026, 1, 19), rng=rng)
    assert len(batches) == len(stores) * len(products)
    assert batches["batch_id"].is_unique
    assert (batches["quantity"] > 0).all()


def test_product_mean_allocation_ignores_store_level_demand():
    rng = np.random.default_rng(42)
    stores = generate_stores(6, config.CITIES, config.CITY_COORDINATES, rng)
    products = generate_products(2, config.CATEGORIES, rng)
    sales = generate_sales_data(stores, products, num_weeks=2, gen_config=SalesGenConfig(store_demand_sigma=0.8),
                                 rng=rng, start_date=date(2026, 1, 5))
    batches = generate_inventory_batches(stores, products, sales, as_of_date=date(2026, 1, 19), rng=rng,
                                          allocation="product_mean")
    product_mean = sales.groupby("product_id")["quantity"].mean()
    coverage_days = batches["quantity"] / batches["product_id"].map(product_mean)
    assert coverage_days.between(9.5, 20.5).all()  # 10-20 ngày theo nhu cầu TB sản phẩm, không theo cửa hàng


def test_expiry_after_received_date():
    rng = np.random.default_rng(42)
    stores = generate_stores(3, config.CITIES, config.CITY_COORDINATES, rng)
    products = generate_products(2, config.CATEGORIES, rng)
    sales = generate_sales_data(stores, products, num_weeks=2, gen_config=SalesGenConfig(), rng=rng,
                                 start_date=date(2026, 1, 5))
    batches = generate_inventory_batches(stores, products, sales, as_of_date=date(2026, 1, 19), rng=rng)
    for _, row in batches.iterrows():
        assert date.fromisoformat(row["expiry_date"]) > date.fromisoformat(row["received_date"])
