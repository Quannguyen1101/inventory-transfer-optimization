"""Tham số tunable cho sinh dữ liệu bán hàng (UC-003 OQ-012)."""
from dataclasses import dataclass


@dataclass
class SalesGenConfig:
    base_demand_range: tuple[float, float] = (5.0, 50.0)
    seasonality_amplitude: float = 0.3
    trend_weekly_growth: float = 0.01
    promotion_frequency_per_year: int = 6
    promotion_uplift: float = 0.5
    promotion_duration_days: int = 7
    noise_std_ratio: float = 0.15
