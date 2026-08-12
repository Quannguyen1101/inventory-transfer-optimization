import numpy as np
import pandas as pd
from src.forecasting.holt_winters_forecaster import HoltWintersForecaster


def _synthetic_series(num_days: int = 70) -> pd.Series:
    rng = np.random.default_rng(1)
    base = 20
    weekday_pattern = [0.9, 0.9, 0.95, 1.0, 1.1, 1.3, 1.2]
    values = [base * weekday_pattern[i % 7] + rng.normal(0, 0.5) for i in range(num_days)]
    return pd.Series(values)


def test_predicts_requested_horizon_with_enough_history():
    forecaster = HoltWintersForecaster(seasonal_periods=7)
    forecaster.fit(_synthetic_series(70))
    forecast = forecaster.predict(horizon=7)
    assert len(forecast) == 7
    assert (forecast >= 0).all()


def test_falls_back_to_naive_when_history_too_short():
    forecaster = HoltWintersForecaster(seasonal_periods=7)
    short_history = pd.Series([10, 12, 11])  # < 2 * seasonal_periods
    forecaster.fit(short_history)
    forecast = forecaster.predict(horizon=3)
    assert len(forecast) == 3
    expected_avg = short_history.mean()
    assert all(abs(v - expected_avg) < 1e-9 for v in forecast)
