"""BR-021 — dashboard HTML tĩnh, tự chứa, so sánh KPI baseline vs tối ưu theo tuần."""
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

_KPI_COLUMNS = ["stockout_rate", "excess_inventory_value", "transport_cost", "mape"]
_KPI_TITLES = {
    "stockout_rate": "Stockout Rate",
    "excess_inventory_value": "Excess Inventory Value (VND)",
    "transport_cost": "Transport Cost (VND)",
    "mape": "Forecast MAPE",
}
_POSITIONS = [(1, 1), (1, 2), (2, 1), (2, 2)]


def generate_dashboard(kpi_df: pd.DataFrame, output_path: Path) -> None:
    output_path = Path(output_path)
    fig = make_subplots(rows=2, cols=2, subplot_titles=[_KPI_TITLES[c] for c in _KPI_COLUMNS])

    # Mỗi thuật toán của kịch bản tối ưu là một đường riêng để so sánh rule-based vs GA. Baseline không
    # dùng thuật toán chuyển hàng nên chỉ có một đường (các lần chạy baseline lặp lại cho mỗi thuật toán
    # cho kết quả giống hệt nhau, lấy trung bình không đổi giá trị).
    labels = kpi_df["scenario"].where(kpi_df["algorithm"] == "none",
                                      kpi_df["scenario"] + " (" + kpi_df["algorithm"] + ")")
    for kpi_col, (row, col) in zip(_KPI_COLUMNS, _POSITIONS):
        for label in sorted(labels.unique()):
            subset = kpi_df[labels == label].groupby("week", as_index=False)[kpi_col].mean()
            fig.add_trace(
                go.Scatter(x=subset["week"], y=subset[kpi_col], mode="lines+markers", name=label,
                           legendgroup=label, showlegend=(row, col) == (1, 1)),
                row=row, col=col,
            )

    fig.update_layout(title="Inventory Transfer Optimization — Weekly KPI (Baseline vs Rule-Based vs GA)",
                       height=700, width=1000)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.write_html(str(output_path), include_plotlyjs=True, full_html=True)
