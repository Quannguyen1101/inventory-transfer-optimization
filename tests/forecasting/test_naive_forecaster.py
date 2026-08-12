import pandas as pd
from src.forecasting.naive_forecaster import NaiveForecaster


def test_predicts_flat_average_of_recent_window():
    history = pd.Series([10, 10, 10, 20, 20, 20, 20, 20, 20, 20], name="quantity")
    forecaster = NaiveForecaster(window=7)
    forecaster.fit(history)
    forecast = forecaster.predict(horizon=5)
    assert len(forecast) == 5
    assert all(abs(v - 20.0) < 1e-9 for v in forecast)


def test_raises_if_predict_called_before_fit():
    import pytest
    forecaster = NaiveForecaster()
    with pytest.raises(RuntimeError):
        forecaster.predict(horizon=3)
