import numpy as np
from src.data_generator.store_generator import generate_stores
from src.data_generator.logistics_generator import (
    generate_distance_matrix, generate_transport_cost_matrix, generate_delivery_schedule,
)
from src import config


def _stores():
    rng = np.random.default_rng(42)
    return generate_stores(4, config.CITIES, config.CITY_COORDINATES, rng)


def test_distance_matrix_covers_all_ordered_pairs_excluding_self():
    stores = _stores()
    df = generate_distance_matrix(stores)
    assert len(df) == len(stores) * (len(stores) - 1)
    assert (df["from_store_id"] != df["to_store_id"]).all()
    assert (df["distance_km"] > 0).all()


def test_transport_cost_scales_with_distance():
    stores = _stores()
    distance_df = generate_distance_matrix(stores)
    cost_df = generate_transport_cost_matrix(distance_df, cost_per_km=5000.0)
    merged = distance_df.merge(cost_df, on=["from_store_id", "to_store_id"])
    assert (merged["transport_cost"] == merged["distance_km"] * 5000.0).all()


def test_delivery_schedule_has_fixed_days_per_route():
    stores = _stores()
    rng = np.random.default_rng(42)
    df = generate_delivery_schedule(stores, days_per_week=2, rng=rng)
    assert len(df) == len(stores) * (len(stores) - 1)
    for _, row in df.iterrows():
        assert len(row["allowed_days"].split(",")) == 2


def test_delivery_schedule_same_city_only_drops_cross_city_routes():
    rng_stores = np.random.default_rng(42)
    stores = generate_stores(6, config.CITIES, config.CITY_COORDINATES, rng_stores)  # 2 cửa hàng/thành phố
    df = generate_delivery_schedule(stores, days_per_week=2, rng=np.random.default_rng(42), same_city_only=True)
    city = stores.set_index("store_id")["city"]
    assert len(df) == 3 * 2  # mỗi thành phố 2 cửa hàng -> 2 tuyến có hướng
    assert (df["from_store_id"].map(city) == df["to_store_id"].map(city)).all()
