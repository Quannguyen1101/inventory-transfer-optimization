import numpy as np
from src.data_generator.store_generator import generate_stores


def test_generates_requested_number_of_stores():
    rng = np.random.default_rng(42)
    df = generate_stores(20, ["Hanoi", "Ho Chi Minh City", "Da Nang"],
                          {"Hanoi": (21.0, 105.8), "Ho Chi Minh City": (10.7, 106.7), "Da Nang": (16.0, 108.2)}, rng)
    assert len(df) == 20
    assert list(df.columns) == ["store_id", "store_name", "city", "latitude", "longitude"]
    assert df["store_id"].is_unique
    assert set(df["city"]) <= {"Hanoi", "Ho Chi Minh City", "Da Nang"}


def test_coordinates_stay_close_to_city_center():
    rng = np.random.default_rng(42)
    coords = {"Hanoi": (21.0, 105.8), "Ho Chi Minh City": (10.7, 106.7), "Da Nang": (16.0, 108.2)}
    df = generate_stores(20, ["Hanoi", "Ho Chi Minh City", "Da Nang"], coords, rng)
    for _, row in df.iterrows():
        center_lat, center_lon = coords[row["city"]]
        assert abs(row["latitude"] - center_lat) < 0.2
        assert abs(row["longitude"] - center_lon) < 0.2
