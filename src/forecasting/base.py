"""BR-003 — interface trừu tượng cho module dự báo (strategy pattern)."""
from abc import ABC, abstractmethod

import pandas as pd


class Forecaster(ABC):
    @abstractmethod
    def fit(self, history: pd.Series) -> None:
        """Huấn luyện forecaster trên chuỗi lịch sử (index = ngày, value = demand)."""

    @abstractmethod
    def predict(self, horizon: int) -> pd.Series:
        """Trả về dự báo demand cho `horizon` ngày tiếp theo."""
