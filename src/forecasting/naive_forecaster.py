"""Kịch bản baseline (logic v1: trung bình ngắn hạn) + fallback khi Holt-Winters lỗi (OQ-009)."""
import pandas as pd

from src.forecasting.base import Forecaster


class NaiveForecaster(Forecaster):
    def __init__(self, window: int = 14):
        self.window = window
        self._history: pd.Series | None = None

    def fit(self, history: pd.Series) -> None:
        self._history = history

    def predict(self, horizon: int) -> pd.Series:
        if self._history is None:
            raise RuntimeError("fit() must be called before predict()")
        avg = self._history.tail(self.window).mean()
        return pd.Series([avg] * horizon)
