import numpy as np
from src.data_generator.product_generator import generate_products
from src import config


def test_generates_requested_number_of_products():
    rng = np.random.default_rng(42)
    df = generate_products(30, config.CATEGORIES, rng)
    assert len(df) == 30
    assert df["product_id"].is_unique
    assert set(df["category"]) == set(config.CATEGORIES)


def test_attributes_match_category_config():
    rng = np.random.default_rng(42)
    df = generate_products(30, config.CATEGORIES, rng)
    for _, row in df.iterrows():
        assert row["service_level"] == config.SERVICE_LEVEL_BY_CATEGORY[row["category"]]
        assert row["z_score"] == config.Z_SCORE_BY_SERVICE_LEVEL[row["service_level"]]
        assert row["lead_time_days"] == config.CATEGORY_LEAD_TIME_DAYS[row["category"]]
        assert row["price"] > row["cost"] > 0
        assert row["weight_kg"] > 0
        assert row["volume_l"] > 0
