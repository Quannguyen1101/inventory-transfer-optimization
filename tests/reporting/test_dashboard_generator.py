from pathlib import Path
import pandas as pd
from src.simulation.kpi_tracker import WeeklyKPI
from src.reporting.dashboard_generator import generate_dashboard


def _sample_kpi_df() -> pd.DataFrame:
    rows = []
    for week in range(1, 4):
        rows.append(WeeklyKPI(week, "baseline", "none", 0.3, 100_000.0, 0.0, 0.25).__dict__)
        rows.append(WeeklyKPI(week, "optimized", "rule_based", 0.1, 50_000.0, 80_000.0, 0.15).__dict__)
    return pd.DataFrame(rows)


def test_writes_html_file(tmp_path):
    output_path = tmp_path / "dashboard.html"
    generate_dashboard(_sample_kpi_df(), output_path)
    assert output_path.exists()
    assert output_path.stat().st_size > 1000


def test_dashboard_is_self_contained_no_cdn(tmp_path):
    # Không kiểm tra "cdn.plot.ly" như một substring thô: file plotly.js minified nhúng sẵn
    # (include_plotlyjs=True) tự nó chứa chuỗi đó ở một chỗ nội bộ không liên quan đến việc
    # tải script từ ngoài. Cái thực sự cần kiểm tra là không có <script src="..."> trỏ ra CDN.
    output_path = tmp_path / "dashboard.html"
    generate_dashboard(_sample_kpi_df(), output_path)
    content = output_path.read_text(encoding="utf-8")
    assert '<script src="https://cdn' not in content
    assert "<script" in content
