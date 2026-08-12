import numpy as np
from datetime import date
from src.data_generator.store_generator import generate_stores
from src.data_generator.product_generator import generate_products
from src.data_generator.generator_config import SalesGenConfig
from src.data_generator.sales_generator import generate_sales_data
from src import config


def _sample_data(rng):
    stores = generate_stores(4, config.CITIES, config.CITY_COORDINATES, rng)
    products = generate_products(3, config.CATEGORIES, rng)
    return stores, products


def test_generates_one_row_per_store_product_day():
    rng = np.random.default_rng(42)
    stores, products = _sample_data(rng)
    df = generate_sales_data(stores, products, num_weeks=4, gen_config=SalesGenConfig(),
                              rng=rng, start_date=date(2026, 1, 5))
    assert len(df) == len(stores) * len(products) * 28
    assert list(df.columns) == ["date", "store_id", "product_id", "quantity", "revenue", "cost", "is_promotion"]
    assert (df["quantity"] >= 0).all()


def test_weekend_demand_higher_than_weekday_on_average():
    rng = np.random.default_rng(42)
    stores, products = _sample_data(rng)
    cfg = SalesGenConfig(trend_weekly_growth=0.0, promotion_frequency_per_year=0, noise_std_ratio=0.0)
    df = generate_sales_data(stores, products, num_weeks=8, gen_config=cfg, rng=rng, start_date=date(2026, 1, 5))
    df["weekday"] = df["date"].apply(lambda d: date.fromisoformat(d).weekday())
    weekend_avg = df[df["weekday"].isin([5, 6])]["quantity"].mean()
    weekday_avg = df[~df["weekday"].isin([5, 6])]["quantity"].mean()
    assert weekend_avg > weekday_avg


def test_later_weeks_have_higher_average_demand_with_trend():
    rng = np.random.default_rng(42)
    stores, products = _sample_data(rng)
    cfg = SalesGenConfig(seasonality_amplitude=0.0, promotion_frequency_per_year=0, noise_std_ratio=0.0,
                          trend_weekly_growth=0.05)
    df = generate_sales_data(stores, products, num_weeks=10, gen_config=cfg, rng=rng, start_date=date(2026, 1, 5))
    df["day_index"] = df["date"].apply(lambda d: (date.fromisoformat(d) - date(2026, 1, 5)).days)
    first_half = df[df["day_index"] < 35]["quantity"].mean()
    second_half = df[df["day_index"] >= 35]["quantity"].mean()
    assert second_half > first_half


def test_some_days_are_flagged_as_promotion():
    rng = np.random.default_rng(42)
    stores, products = _sample_data(rng)
    cfg = SalesGenConfig(promotion_frequency_per_year=52)  # tần suất cao để chắc chắn có promo trong 4 tuần mẫu
    df = generate_sales_data(stores, products, num_weeks=4, gen_config=cfg, rng=rng, start_date=date(2026, 1, 5))
    assert df["is_promotion"].sum() > 0
