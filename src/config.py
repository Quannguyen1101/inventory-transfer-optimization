"""Project-wide configuration values (BRD Mục 7A)."""
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
RESULTS_DIR = PROJECT_ROOT / "results"
DASHBOARD_DIR = PROJECT_ROOT / "dashboard"

RANDOM_SEED = 42

# Mục 7A.1 — Quy mô dữ liệu
NUM_STORES = 20
CITIES = ["Hanoi", "Ho Chi Minh City", "Da Nang"]
CITY_COORDINATES = {
    "Hanoi": (21.0285, 105.8542),
    "Ho Chi Minh City": (10.7769, 106.7009),
    "Da Nang": (16.0544, 108.2022),
}
NUM_PRODUCTS = 30
CATEGORIES = ["Essentials", "Beverages", "Dry Goods", "Frozen", "Household"]
HISTORY_WEEKS = 52
SIMULATION_WEEKS = 12
# UC-003 sinh đủ HISTORY_WEEKS (dữ liệu forecaster được "thấy") + SIMULATION_WEEKS (đóng vai trò
# nhu cầu thực tế "tương lai" được UC-001 tiết lộ dần theo từng tuần trong rolling simulation).
TOTAL_DATA_WEEKS = HISTORY_WEEKS + SIMULATION_WEEKS

# Mục 7A.2 — Ràng buộc vận hành
VEHICLE_CAPACITY_KG = 500.0
VEHICLE_CAPACITY_M3 = 2.0
DELIVERY_DAYS_PER_WEEK = 2
MIN_SHELF_LIFE_DAYS = 7

# Mục 7A.3 — Service level theo danh mục
SERVICE_LEVEL_BY_CATEGORY = {
    "Essentials": 0.98,
    "Beverages": 0.95,
    "Dry Goods": 0.95,
    "Frozen": 0.95,
    "Household": 0.90,
}
Z_SCORE_BY_SERVICE_LEVEL = {
    0.98: 2.05,
    0.95: 1.65,
    0.90: 1.28,
}

# Lead time theo danh mục (ngày) — quyết định kỹ thuật, BRD chỉ yêu cầu có thuộc tính (BR-004)
CATEGORY_LEAD_TIME_DAYS = {
    "Essentials": 2,
    "Beverages": 3,
    "Dry Goods": 5,
    "Frozen": 2,
    "Household": 7,
}

# Hạn sử dụng theo danh mục (ngày) — dùng khi sinh batch ban đầu (UC-003) và khi nhận hàng
# bổ sung từ NCC trong simulation (BR-025).
CATEGORY_SHELF_LIFE_DAYS = {
    "Essentials": 180,
    "Beverages": 270,
    "Dry Goods": 365,
    "Frozen": 45,
    "Household": 365,
}

# Ngưỡng days-of-inventory cho kịch bản baseline (logic v1)
MIN_INVENTORY_DAYS = 7.0
MAX_INVENTORY_DAYS = 30.0
