# Technical Design — Inventory Transfer Optimization v2

## 0. Document Control

| Trường | Giá trị |
|---|---|
| Tên dự án | Inventory Transfer Optimization System v2 |
| Phiên bản | 1.0 |
| Ngày tạo | 2026-08-11 |
| Tác giả | Chủ dự án (Portfolio Owner) |
| Trạng thái | Approved |
| Nguồn yêu cầu | `../requirements/BRD.md`, `UC-001-rolling-simulation-dashboard.md`, `rolling-simulation-weekly-cycle-use-case.md`, `synthetic-data-generation-use-case.md` |

## 1. Kiến trúc module

```
inventory-transfer-optimization/
├── data/                          # output của UC-003 (CSV)
├── src/
│   ├── config.py                  # tham số Mục 7A của BRD (quy mô, ràng buộc, service level, tech)
│   ├── data_generator/            # UC-003
│   │   ├── generator_config.py    #   tham số tunable (OQ-012): seasonality, trend, promo, noise
│   │   ├── store_generator.py
│   │   ├── product_generator.py
│   │   ├── sales_generator.py
│   │   ├── inventory_generator.py
│   │   ├── logistics_generator.py
│   │   └── main.py
│   ├── forecasting/               # BR-002, BR-003 (pluggable)
│   │   ├── base.py                #   abstract Forecaster (strategy pattern)
│   │   ├── holt_winters_forecaster.py   # kịch bản tối ưu
│   │   └── naive_forecaster.py    #   kịch bản baseline + fallback OQ-009
│   ├── inventory_policy/          # BR-004–008
│   │   ├── safety_stock.py
│   │   ├── reorder_point.py
│   │   └── classifier.py
│   ├── optimization/              # BR-009–016
│   │   ├── constraints.py         #   dùng chung cho cả 2 thuật toán (BR-015, BR-016)
│   │   ├── rule_based.py
│   │   └── genetic_algorithm.py
│   ├── simulation/                # UC-001, UC-002
│   │   ├── weekly_cycle.py        #   UC-002
│   │   ├── rolling_simulator.py   #   UC-001
│   │   └── kpi_tracker.py         #   BR-019
│   ├── reporting/
│   │   └── dashboard_generator.py # BR-021, Plotly
│   └── main.py                    # CLI entrypoint
├── tests/
├── results/                       # KPI time series xuất ra
├── dashboard/                     # file HTML output
└── docs/
    ├── requirements/              # BRD + UC (đã có)
    └── architecture/              # tài liệu này
```

**Nguyên tắc:** mỗi thư mục = 1 năng lực nghiệp vụ (BR-023). `optimization/constraints.py` dùng chung giữa `rule_based.py` và `genetic_algorithm.py` để đảm bảo hai thuật toán không lệch logic ràng buộc (BR-015/BR-016 phải nhất quán).

## 2. Data schema (CSV — giải quyết OQ-011)

| File | Cột |
|---|---|
| `stores.csv` | store_id, store_name, city, latitude, longitude *(như v1)* |
| `products.csv` | product_id, name, category, price, cost, lead_time_days, service_level, z_score, weight_kg, volume_l |
| `sales_data.csv` | date, store_id, product_id, quantity, revenue, cost, is_promotion |
| `inventory_batches.csv` | batch_id, store_id, product_id, quantity, received_date, expiry_date *(thay `inventory_data.csv` của v1)* |
| `distance_matrix.csv`, `transport_cost_matrix.csv` | *(giữ như v1)* |
| `delivery_schedule.csv` **(mới)** | from_store_id, to_store_id, allowed_days |

Sức chứa xe (500kg / 2m³, Mục 7A.2 của BRD) là hằng số toàn cục → đặt trong `config.py`, không tách CSV riêng.

## 3. Interface cốt lõi

```python
# forecasting/base.py — BR-003 pluggable (strategy pattern)
class Forecaster(ABC):
    def fit(self, history: pd.Series) -> None: ...
    def predict(self, horizon: int) -> pd.Series: ...
# → HoltWintersForecaster (kịch bản tối ưu), NaiveForecaster (baseline + fallback lỗi dự báo, OQ-009)

# inventory_policy/ — BR-006, BR-007
def compute_safety_stock(demand_std, z_score, lead_time_days) -> float
def compute_reorder_point(avg_demand, lead_time_days, safety_stock) -> float

# optimization/constraints.py — dùng chung cho cả 2 thuật toán
@dataclass
class TransferConstraints:
    vehicle_capacity_kg: float
    vehicle_capacity_m3: float
    delivery_schedule: dict[tuple[int, int], list[str]]
    min_shelf_life_days: int

def filter_eligible_batches(batches, min_shelf_life_days, current_date) -> list  # FEFO + loại cận hạn (BR-013, BR-014)
def is_feasible(transfer_plan, constraints) -> bool                              # sức chứa xe + lịch giao hàng (BR-010, BR-011)

# simulation/weekly_cycle.py — UC-002
def run_week(state: WeekState, scenario: Literal["baseline", "optimized"], algorithm: str) -> WeekResult

# simulation/rolling_simulator.py — UC-001
def run_simulation(n_weeks: int = 12, algorithm: str = "both", seed: int = 42) -> SimulationResult
```

Rule-based dùng `filter_eligible_batches`/`is_feasible` để lọc trước khi ghép (greedy). Genetic algorithm nhận cùng `TransferConstraints`, tính penalty trong hàm fitness khi vi phạm.

## 4. CLI (kế thừa phong cách v1)

```
python src/main.py --generate-data                          # UC-003
python src/main.py --simulate --weeks 12 --algorithm both    # UC-001, mặc định
python src/main.py --simulate --algorithm rule_based         # AF-2 của UC-001: chỉ 1 thuật toán
python src/main.py --dashboard-only                          # dựng lại dashboard từ results/ đã có
```

## 5. Xử lý lỗi (bám theo Exception Flows đã đặc tả trong use case)

| Tình huống | Xử lý |
|---|---|
| Thiếu/sai file dữ liệu đầu vào (EF-1 UC-001) | Dừng, log lỗi cụ thể, không tạo dashboard nửa vời |
| Không tìm được kế hoạch chuyển hợp lệ (EF-1 UC-002 / EF-2 UC-001) | Ghi "không chuyển hàng tuần t", tiếp tục các bước còn lại |
| Forecast lỗi/thiếu data cho 1 SKU (EF-2 UC-002) | Fallback `NaiveForecaster` cho riêng SKU/tuần đó, log warning, tiếp tục |
| Lỗi dựng dashboard (EF-3 UC-001) | Giữ nguyên KPI thô đã tính, báo lỗi riêng ở bước xuất dashboard, không mất kết quả simulation |
| Lỗi ghi file khi sinh data (EF-1 UC-003) | Dừng, không để lại dữ liệu ghi dở (partial write) |

Dashboard xuất bằng Plotly với `include_plotlyjs=True` (nhúng thẳng plotly.js vào HTML) để đúng nghĩa "tự chứa" (BR-021) — mở được offline, không phụ thuộc CDN.

## 6. Testing

`pytest` — unit test cho từng module thuần túy:
- `inventory_policy`: safety stock/reorder point đúng công thức với input biết trước.
- `optimization.constraints`: filter đúng/sai theo hạn sử dụng, sức chứa, lịch giao hàng.
- `optimization.rule_based`, `optimization.genetic_algorithm`: đúng trên fixture nhỏ, tôn trọng ràng buộc.
- `forecasting`: Holt-Winters chạy được trên chuỗi có seasonality rõ, NaiveForecaster dùng làm fallback đúng khi được gọi.

Cộng thêm 1 test tích hợp: chạy `run_simulation` rút gọn (2 tuần, bộ data nhỏ qua AF-2/AF-3 của UC-003) để bắt lỗi nối module — không chạy full 12 tuần trong test (chậm, không cần thiết cho unit/integration test).

## 7. Truy xuất yêu cầu (Traceability)

Toàn bộ 24 BR trong BRD đều có nơi triển khai tương ứng:
- BR-001, 004, 005, 009, 012 → `data_generator/` (UC-003)
- BR-002, 003 → `forecasting/`
- BR-006, 007, 008 → `inventory_policy/`
- BR-009–016 → `optimization/`
- BR-017–021 → `simulation/`, `reporting/`
- BR-022, 023, 024 → toàn bộ kiến trúc (viết lại hoàn toàn, module hóa, không tích hợp hệ thống thật)

Không còn open question nào chưa giải quyết (xem Mục 13 của BRD và của từng use case).
