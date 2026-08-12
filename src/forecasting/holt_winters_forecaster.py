"""BR-002 — dự báo Holt-Winters (statsmodels), fallback NaiveForecaster khi thiếu dữ liệu/lỗi (OQ-009)."""
import pandas as pd
from statsmodels.tsa.holtwinters import ExponentialSmoothing

from src.forecasting.base import Forecaster
from src.forecasting.naive_forecaster import NaiveForecaster


class HoltWintersForecaster(Forecaster):
    """Dùng tham số smoothing cố định (không để statsmodels tự tối ưu bằng scipy) — nhanh hơn
    ~24 lần (đo thực tế: 0.148s -> 0.006s/lần fit) so với optimized=True mặc định. Bắt buộc phải
    làm vậy để 600 cặp store/product x nhiều tuần simulation nằm trong ngân sách 15 phút của
    UC-001 (NFR, BRD Mục 12) — đánh đổi lấy tốc độ, chấp nhận forecast kém tối ưu hơn một chút."""

    def __init__(self, seasonal_periods: int = 7, smoothing_level: float = 0.3,
                 smoothing_trend: float = 0.1, smoothing_seasonal: float = 0.1):
        self.seasonal_periods = seasonal_periods
        self.smoothing_level = smoothing_level
        self.smoothing_trend = smoothing_trend
        self.smoothing_seasonal = smoothing_seasonal
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
                initialization_method="heuristic",
            ).fit(smoothing_level=self.smoothing_level, smoothing_trend=self.smoothing_trend,
                  smoothing_seasonal=self.smoothing_seasonal, optimized=False)
        except Exception:
            self._model = None
            self._fallback.fit(history)

    def predict(self, horizon: int) -> pd.Series:
        if self._model is None:
            return self._fallback.predict(horizon)
        forecast = self._model.forecast(horizon)
        return forecast.clip(lower=0).reset_index(drop=True)
