"""BR-002 — dự báo Holt-Winters (statsmodels), fallback NaiveForecaster khi thiếu dữ liệu/lỗi (OQ-009)."""
import pandas as pd
from statsmodels.tsa.holtwinters import ExponentialSmoothing

from src.forecasting.base import Forecaster
from src.forecasting.naive_forecaster import NaiveForecaster


class HoltWintersForecaster(Forecaster):
    def __init__(self, seasonal_periods: int = 7):
        self.seasonal_periods = seasonal_periods
        self._model = None
        self._fallback = NaiveForecaster()

    def fit(self, history: pd.Series) -> None:
        if len(history) < 2 * self.seasonal_periods:
            self._model = None
            self._fallback.fit(history)
            return
        try:
            self._model = ExponentialSmoothing(
                history, trend="add", seasonal="add", seasonal_periods=self.seasonal_periods,
            ).fit()
        except Exception:
            self._model = None
            self._fallback.fit(history)

    def predict(self, horizon: int) -> pd.Series:
        if self._model is None:
            return self._fallback.predict(horizon)
        forecast = self._model.forecast(horizon)
        return forecast.clip(lower=0).reset_index(drop=True)
