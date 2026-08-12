from src.data_generator.main import run_data_generation


def test_writes_all_expected_csv_files(tmp_path):
    run_data_generation(output_dir=tmp_path, seed=1, num_weeks=2)
    expected_files = {
        "stores.csv", "products.csv", "sales_data.csv", "inventory_batches.csv",
        "distance_matrix.csv", "transport_cost_matrix.csv", "delivery_schedule.csv",
    }
    actual_files = {p.name for p in tmp_path.glob("*.csv")}
    assert expected_files <= actual_files


def test_is_reproducible_with_same_seed(tmp_path):
    out1, out2 = tmp_path / "run1", tmp_path / "run2"
    out1.mkdir()
    out2.mkdir()
    run_data_generation(output_dir=out1, seed=7, num_weeks=2)
    run_data_generation(output_dir=out2, seed=7, num_weeks=2)
    import pandas as pd
    pd.testing.assert_frame_equal(pd.read_csv(out1 / "sales_data.csv"), pd.read_csv(out2 / "sales_data.csv"))
