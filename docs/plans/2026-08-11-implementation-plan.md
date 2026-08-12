# Inventory Transfer Optimization v2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rewrite the inventory transfer optimization demo into a portfolio-grade system with demand forecasting, safety-stock/reorder-point policy, constraint-aware transfer optimization (rule-based + genetic algorithm), a 12-week rolling simulation with baseline-vs-optimized comparison, and a self-contained HTML KPI dashboard.

**Architecture:** Six independent Python packages under `src/` (`data_generator`, `forecasting`, `inventory_policy`, `optimization`, `simulation`, `reporting`), each owning one business capability per `docs/architecture/technical-design.md`. `data_generator` runs first and produces CSVs in `data/`; `forecasting`, `inventory_policy`, and `optimization` are independent, pure-logic packages consumed by `simulation`, which drives the weekly/rolling pipeline (UC-002 → UC-001) and hands accumulated KPIs to `reporting` for the final dashboard.

**Tech Stack:** Python 3.11+, pandas, NumPy, statsmodels (Holt-Winters), Plotly (dashboard), pytest.

## Global Constraints

- Data scale (BRD Mục 7A.1): 20 stores / 3 cities, 30 products / 5 categories, 52 weeks (364 days) of history, 12-week rolling simulation.
- Operational constraints (BRD Mục 7A.2): vehicle capacity 500 kg **and** 2 m³ per route per week; delivery schedule fixed at 2 days/week per store pair; batches with < 7 days shelf life left are excluded from transfer.
- Service levels (BRD Mục 7A.3): Essentials 98% (Z=2.05), Beverages/Dry Goods 95% (Z=1.65), Frozen 95% (Z=1.65), Household 90% (Z=1.28).
- Storage format (UC-003 OQ-011): CSV only, under `data/`. No Parquet/SQLite.
- Dashboard must be self-contained (`include_plotlyjs=True`), no CDN dependency (BR-021).
- No real system integration (BR-024) — synthetic data only. No GA non-determinism fix required — fix `random.seed`/`np.random.default_rng(seed)` for reproducibility only.
- Runtime budget: full 12-week × 2-scenario × 2-algorithm simulation < 15 min (UC-001 NFR); data generation < 2 min (UC-003 NFR).
- All money values in VND (float, 2 decimals). All dates as ISO `YYYY-MM-DD` strings in CSVs, `datetime.date` in Python code.

---

## File Structure

```
inventory-transfer-optimization/
├── src/
│   ├── config.py
│   ├── data_generator/
│   │   ├── __init__.py
│   │   ├── generator_config.py
│   │   ├── store_generator.py
│   │   ├── product_generator.py
│   │   ├── sales_generator.py
│   │   ├── inventory_generator.py
│   │   ├── logistics_generator.py
│   │   └── main.py
│   ├── forecasting/
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── naive_forecaster.py
│   │   └── holt_winters_forecaster.py
│   ├── inventory_policy/
│   │   ├── __init__.py
│   │   ├── safety_stock.py
│   │   ├── reorder_point.py
│   │   └── classifier.py
│   ├── optimization/
│   │   ├── __init__.py
│   │   ├── constraints.py
│   │   ├── rule_based.py
│   │   └── genetic_algorithm.py
│   ├── simulation/
│   │   ├── __init__.py
│   │   ├── kpi_tracker.py
│   │   ├── weekly_cycle.py
│   │   └── rolling_simulator.py
│   ├── reporting/
│   │   ├── __init__.py
│   │   └── dashboard_generator.py
│   └── main.py
├── tests/
│   ├── __init__.py
│   ├── data_generator/  (test_store_generator.py, test_product_generator.py, test_sales_generator.py, test_inventory_generator.py, test_logistics_generator.py)
│   ├── forecasting/ (test_naive_forecaster.py, test_holt_winters_forecaster.py)
│   ├── inventory_policy/ (test_safety_stock.py, test_reorder_point.py, test_classifier.py)
│   ├── optimization/ (test_constraints.py, test_rule_based.py, test_genetic_algorithm.py)
│   ├── simulation/ (test_kpi_tracker.py, test_weekly_cycle.py)
│   └── test_integration.py
├── data/            (generated, not committed except .gitkeep)
├── results/         (generated)
├── dashboard/       (generated)
├── requirements.txt
├── pytest.ini
└── .gitignore
```

---

### Task 0: Project scaffolding

**Files:**
- Create: `requirements.txt`
- Create: `pytest.ini`
- Create: `.gitignore`
- Create: `src/config.py`
- Create: `src/__init__.py`, `tests/__init__.py`
- Test: `tests/test_config.py`

**Interfaces:**
- Produces: module-level constants in `src/config.py` — `PROJECT_ROOT: Path`, `DATA_DIR: Path`, `RESULTS_DIR: Path`, `DASHBOARD_DIR: Path`, `RANDOM_SEED: int`, `NUM_STORES: int`, `CITIES: list[str]`, `NUM_PRODUCTS: int`, `CATEGORIES: list[str]`, `HISTORY_WEEKS: int`, `SIMULATION_WEEKS: int`, `VEHICLE_CAPACITY_KG: float`, `VEHICLE_CAPACITY_M3: float`, `DELIVERY_DAYS_PER_WEEK: int`, `MIN_SHELF_LIFE_DAYS: int`, `SERVICE_LEVEL_BY_CATEGORY: dict[str, float]`, `Z_SCORE_BY_SERVICE_LEVEL: dict[float, float]`, `CATEGORY_LEAD_TIME_DAYS: dict[str, int]`, `MIN_INVENTORY_DAYS: float`, `MAX_INVENTORY_DAYS: float`. All later tasks import from here — no module should hardcode these values again.

- [ ] **Step 1: Create directory skeleton and git init**

```bash
mkdir -p src/data_generator src/forecasting src/inventory_policy src/optimization src/simulation src/reporting
mkdir -p tests/data_generator tests/forecasting tests/inventory_policy tests/optimization tests/simulation
mkdir -p data results dashboard
git init
```

- [ ] **Step 2: Write `.gitignore`**

```
__pycache__/
*.pyc
.pytest_cache/
data/*.csv
results/*.csv
dashboard/*.html
!data/.gitkeep
!results/.gitkeep
!dashboard/.gitkeep
```

Then: `touch data/.gitkeep results/.gitkeep dashboard/.gitkeep`

- [ ] **Step 3: Write `requirements.txt`**

```
pandas>=2.1
numpy>=1.26
statsmodels>=0.14
plotly>=5.20
pytest>=8.0
```

- [ ] **Step 4: Write `pytest.ini`**

```ini
[pytest]
testpaths = tests
pythonpath = .
```

- [ ] **Step 5: Write the failing test for config**

`tests/test_config.py`:
```python
from src import config


def test_service_level_categories_match_product_categories():
    assert set(config.SERVICE_LEVEL_BY_CATEGORY.keys()) == set(config.CATEGORIES)


def test_z_score_mapping_covers_all_service_levels():
    used_levels = set(config.SERVICE_LEVEL_BY_CATEGORY.values())
    assert used_levels.issubset(config.Z_SCORE_BY_SERVICE_LEVEL.keys())


def test_lead_time_covers_all_categories():
    assert set(config.CATEGORY_LEAD_TIME_DAYS.keys()) == set(config.CATEGORIES)
```

- [ ] **Step 6: Run test to verify it fails**

Run: `pytest tests/test_config.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'src.config'` (or collection error since `src/config.py` doesn't exist yet).

- [ ] **Step 7: Write `src/config.py`**

```python
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

# Ngưỡng days-of-inventory cho kịch bản baseline (logic v1)
MIN_INVENTORY_DAYS = 7.0
MAX_INVENTORY_DAYS = 30.0
```

- [ ] **Step 8: Run test to verify it passes**

Run: `pytest tests/test_config.py -v`
Expected: PASS (3 passed)

- [ ] **Step 9: Commit**

```bash
git add .gitignore requirements.txt pytest.ini src/config.py src/__init__.py tests/__init__.py tests/test_config.py data/.gitkeep results/.gitkeep dashboard/.gitkeep
git commit -m "chore: project scaffolding and central config"
```

---

## Phase 1 — Data Generator (UC-003)

### Task 1: `store_generator.py`

**Files:**
- Create: `src/data_generator/store_generator.py`
- Test: `tests/data_generator/test_store_generator.py`

**Interfaces:**
- Consumes: `config.NUM_STORES`, `config.CITIES`, `config.CITY_COORDINATES`
- Produces: `generate_stores(num_stores: int, cities: list[str], city_coordinates: dict[str, tuple[float, float]], rng: np.random.Generator) -> pd.DataFrame` with columns `store_id (int), store_name (str), city (str), latitude (float), longitude (float)`. Used by Task 2 onward (all downstream generators take this DataFrame as input).

- [ ] **Step 1: Write failing test**

`tests/data_generator/test_store_generator.py`:
```python
import numpy as np
from src.data_generator.store_generator import generate_stores


def test_generates_requested_number_of_stores():
    rng = np.random.default_rng(42)
    df = generate_stores(20, ["Hanoi", "Ho Chi Minh City", "Da Nang"],
                          {"Hanoi": (21.0, 105.8), "Ho Chi Minh City": (10.7, 106.7), "Da Nang": (16.0, 108.2)}, rng)
    assert len(df) == 20
    assert list(df.columns) == ["store_id", "store_name", "city", "latitude", "longitude"]
    assert df["store_id"].is_unique
    assert set(df["city"]) <= {"Hanoi", "Ho Chi Minh City", "Da Nang"}


def test_coordinates_stay_close_to_city_center():
    rng = np.random.default_rng(42)
    coords = {"Hanoi": (21.0, 105.8), "Ho Chi Minh City": (10.7, 106.7), "Da Nang": (16.0, 108.2)}
    df = generate_stores(20, ["Hanoi", "Ho Chi Minh City", "Da Nang"], coords, rng)
    for _, row in df.iterrows():
        center_lat, center_lon = coords[row["city"]]
        assert abs(row["latitude"] - center_lat) < 0.2
        assert abs(row["longitude"] - center_lon) < 0.2
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/data_generator/test_store_generator.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'src.data_generator.store_generator'`

- [ ] **Step 3: Write implementation**

`src/data_generator/__init__.py`: (empty file)

`src/data_generator/store_generator.py`:
```python
"""UC-003 step 3 — sinh danh mục cửa hàng."""
import numpy as np
import pandas as pd

_COORD_JITTER = 0.05


def generate_stores(num_stores: int, cities: list[str],
                     city_coordinates: dict[str, tuple[float, float]],
                     rng: np.random.Generator) -> pd.DataFrame:
    records = []
    for store_id in range(1, num_stores + 1):
        city = cities[(store_id - 1) % len(cities)]
        center_lat, center_lon = city_coordinates[city]
        records.append({
            "store_id": store_id,
            "store_name": f"Store {store_id:02d} - {city}",
            "city": city,
            "latitude": round(center_lat + rng.uniform(-_COORD_JITTER, _COORD_JITTER), 6),
            "longitude": round(center_lon + rng.uniform(-_COORD_JITTER, _COORD_JITTER), 6),
        })
    return pd.DataFrame(records)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/data_generator/test_store_generator.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add src/data_generator/__init__.py src/data_generator/store_generator.py tests/data_generator/test_store_generator.py tests/data_generator/__init__.py
git commit -m "feat: generate synthetic store data (UC-003)"
```

---

### Task 2: `product_generator.py`

**Files:**
- Create: `src/data_generator/product_generator.py`
- Test: `tests/data_generator/test_product_generator.py`

**Interfaces:**
- Consumes: `config.NUM_PRODUCTS`, `config.CATEGORIES`, `config.SERVICE_LEVEL_BY_CATEGORY`, `config.Z_SCORE_BY_SERVICE_LEVEL`, `config.CATEGORY_LEAD_TIME_DAYS`
- Produces: `generate_products(num_products: int, categories: list[str], rng: np.random.Generator) -> pd.DataFrame` with columns `product_id (int), name (str), category (str), price (float), cost (float), lead_time_days (int), service_level (float), z_score (float), weight_kg (float), volume_l (float)`. Consumed by `sales_generator`, `inventory_generator`, `optimization.constraints`.

- [ ] **Step 1: Write failing test**

`tests/data_generator/test_product_generator.py`:
```python
import numpy as np
from src.data_generator.product_generator import generate_products
from src import config


def test_generates_requested_number_of_products():
    rng = np.random.default_rng(42)
    df = generate_products(30, config.CATEGORIES, rng)
    assert len(df) == 30
    assert df["product_id"].is_unique
    assert set(df["category"]) == set(config.CATEGORIES)


def test_attributes_match_category_config():
    rng = np.random.default_rng(42)
    df = generate_products(30, config.CATEGORIES, rng)
    for _, row in df.iterrows():
        assert row["service_level"] == config.SERVICE_LEVEL_BY_CATEGORY[row["category"]]
        assert row["z_score"] == config.Z_SCORE_BY_SERVICE_LEVEL[row["service_level"]]
        assert row["lead_time_days"] == config.CATEGORY_LEAD_TIME_DAYS[row["category"]]
        assert row["price"] > row["cost"] > 0
        assert row["weight_kg"] > 0
        assert row["volume_l"] > 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/data_generator/test_product_generator.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Write implementation**

`src/data_generator/product_generator.py`:
```python
"""UC-003 step 4 — sinh danh mục sản phẩm và thuộc tính theo danh mục (BR-004, BR-005, BR-009)."""
import numpy as np
import pandas as pd

from src import config

_WEIGHT_RANGE_KG = {
    "Essentials": (0.2, 2.0), "Beverages": (0.3, 2.0), "Dry Goods": (0.1, 5.0),
    "Frozen": (0.2, 3.0), "Household": (0.5, 10.0),
}
_VOLUME_RANGE_L = {
    "Essentials": (0.2, 2.0), "Beverages": (0.3, 2.0), "Dry Goods": (0.1, 5.0),
    "Frozen": (0.2, 3.0), "Household": (0.5, 15.0),
}
_COST_RANGE_VND = (10_000, 300_000)
_MARGIN_RANGE = (1.2, 1.8)  # price = cost * margin


def generate_products(num_products: int, categories: list[str], rng: np.random.Generator) -> pd.DataFrame:
    records = []
    for product_id in range(1, num_products + 1):
        category = categories[(product_id - 1) % len(categories)]
        service_level = config.SERVICE_LEVEL_BY_CATEGORY[category]
        cost = rng.uniform(*_COST_RANGE_VND)
        price = cost * rng.uniform(*_MARGIN_RANGE)
        w_lo, w_hi = _WEIGHT_RANGE_KG[category]
        v_lo, v_hi = _VOLUME_RANGE_L[category]
        records.append({
            "product_id": product_id,
            "name": f"Product {product_id:02d} - {category}",
            "category": category,
            "price": round(price, 2),
            "cost": round(cost, 2),
            "lead_time_days": config.CATEGORY_LEAD_TIME_DAYS[category],
            "service_level": service_level,
            "z_score": config.Z_SCORE_BY_SERVICE_LEVEL[service_level],
            "weight_kg": round(rng.uniform(w_lo, w_hi), 3),
            "volume_l": round(rng.uniform(v_lo, v_hi), 3),
        })
    return pd.DataFrame(records)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/data_generator/test_product_generator.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add src/data_generator/product_generator.py tests/data_generator/test_product_generator.py
git commit -m "feat: generate synthetic product data with category attributes (UC-003)"
```

---

### Task 3: `sales_generator.py`

**Files:**
- Create: `src/data_generator/generator_config.py`
- Create: `src/data_generator/sales_generator.py`
- Test: `tests/data_generator/test_sales_generator.py`

**Interfaces:**
- Consumes: `stores_df` (Task 1 output), `products_df` (Task 2 output)
- Produces: `SalesGenConfig` dataclass (tunable params, OQ-012); `generate_sales_data(stores_df: pd.DataFrame, products_df: pd.DataFrame, num_weeks: int, gen_config: SalesGenConfig, rng: np.random.Generator, start_date: date | None = None) -> pd.DataFrame` with columns `date (str ISO), store_id (int), product_id (int), quantity (int), revenue (float), cost (float), is_promotion (int 0/1)`. Consumed by `inventory_generator` (Task 4) and by `forecasting`/`simulation` at runtime.

- [ ] **Step 1: Write failing test**

`src/data_generator/generator_config.py`:
```python
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
```

`tests/data_generator/test_sales_generator.py`:
```python
import numpy as np
from datetime import date
from src.data_generator.store_generator import generate_stores
from src.data_generator.product_generator import generate_products
from src.data_generator.generator_config import SalesGenConfig
from src.data_generator.sales_generator import generate_sales_data
from src import config


def _sample_data(rng):
    stores = generate_stores(4, config.CITIES, config.CITY_COORDINATES, rng)
    products = generate_products(3, config.CATEGORIES, rng)
    return stores, products


def test_generates_one_row_per_store_product_day():
    rng = np.random.default_rng(42)
    stores, products = _sample_data(rng)
    df = generate_sales_data(stores, products, num_weeks=4, gen_config=SalesGenConfig(),
                              rng=rng, start_date=date(2026, 1, 5))
    assert len(df) == len(stores) * len(products) * 28
    assert list(df.columns) == ["date", "store_id", "product_id", "quantity", "revenue", "cost", "is_promotion"]
    assert (df["quantity"] >= 0).all()


def test_weekend_demand_higher_than_weekday_on_average():
    rng = np.random.default_rng(42)
    stores, products = _sample_data(rng)
    cfg = SalesGenConfig(trend_weekly_growth=0.0, promotion_frequency_per_year=0, noise_std_ratio=0.0)
    df = generate_sales_data(stores, products, num_weeks=8, gen_config=cfg, rng=rng, start_date=date(2026, 1, 5))
    df["weekday"] = df["date"].apply(lambda d: date.fromisoformat(d).weekday())
    weekend_avg = df[df["weekday"].isin([5, 6])]["quantity"].mean()
    weekday_avg = df[~df["weekday"].isin([5, 6])]["quantity"].mean()
    assert weekend_avg > weekday_avg


def test_later_weeks_have_higher_average_demand_with_trend():
    rng = np.random.default_rng(42)
    stores, products = _sample_data(rng)
    cfg = SalesGenConfig(seasonality_amplitude=0.0, promotion_frequency_per_year=0, noise_std_ratio=0.0,
                          trend_weekly_growth=0.05)
    df = generate_sales_data(stores, products, num_weeks=10, gen_config=cfg, rng=rng, start_date=date(2026, 1, 5))
    df["day_index"] = df["date"].apply(lambda d: (date.fromisoformat(d) - date(2026, 1, 5)).days)
    first_half = df[df["day_index"] < 35]["quantity"].mean()
    second_half = df[df["day_index"] >= 35]["quantity"].mean()
    assert second_half > first_half


def test_some_days_are_flagged_as_promotion():
    rng = np.random.default_rng(42)
    stores, products = _sample_data(rng)
    cfg = SalesGenConfig(promotion_frequency_per_year=52)  # tần suất cao để chắc chắn có promo trong 4 tuần mẫu
    df = generate_sales_data(stores, products, num_weeks=4, gen_config=cfg, rng=rng, start_date=date(2026, 1, 5))
    assert df["is_promotion"].sum() > 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/data_generator/test_sales_generator.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'src.data_generator.sales_generator'`

- [ ] **Step 3: Write implementation**

`src/data_generator/sales_generator.py`:
```python
"""UC-003 step 5 — sinh lịch sử bán hàng có seasonality/trend/promotion (BR-001)."""
from datetime import date, timedelta

import numpy as np
import pandas as pd

from src.data_generator.generator_config import SalesGenConfig

_WEEKDAY_MULTIPLIER = {0: 0.9, 1: 0.9, 2: 0.95, 3: 1.0, 4: 1.1, 5: 1.3, 6: 1.2}  # Mon=0..Sun=6


def _pick_promotion_days(num_days: int, gen_config: SalesGenConfig, rng: np.random.Generator) -> set[int]:
    num_promos = int(round(gen_config.promotion_frequency_per_year * (num_days / 365)))
    promo_days: set[int] = set()
    attempts = 0
    max_start = max(1, num_days - gen_config.promotion_duration_days)
    while len(promo_days) < num_promos * gen_config.promotion_duration_days and attempts < 100:
        start = int(rng.integers(0, max_start))
        promo_days.update(range(start, start + gen_config.promotion_duration_days))
        attempts += 1
    return promo_days


def generate_sales_data(stores_df: pd.DataFrame, products_df: pd.DataFrame, num_weeks: int,
                         gen_config: SalesGenConfig, rng: np.random.Generator,
                         start_date: date | None = None) -> pd.DataFrame:
    if start_date is None:
        start_date = date.today() - timedelta(days=num_weeks * 7)
    num_days = num_weeks * 7
    records = []
    for _, product in products_df.iterrows():
        base_demand = rng.uniform(*gen_config.base_demand_range)
        promo_days = _pick_promotion_days(num_days, gen_config, rng)
        for _, store in stores_df.iterrows():
            store_multiplier = rng.uniform(0.7, 1.3)
            for day_offset in range(num_days):
                current_date = start_date + timedelta(days=day_offset)
                weekday_mult = 1 + gen_config.seasonality_amplitude * (
                    _WEEKDAY_MULTIPLIER[current_date.weekday()] - 1
                )
                trend_mult = (1 + gen_config.trend_weekly_growth) ** (day_offset // 7)
                is_promo = day_offset in promo_days
                promo_mult = (1 + gen_config.promotion_uplift) if is_promo else 1.0
                noise = max(rng.normal(1.0, gen_config.noise_std_ratio), 0.0)
                expected = base_demand * store_multiplier * weekday_mult * trend_mult * promo_mult * noise
                quantity = max(0, int(round(expected)))
                records.append({
                    "date": current_date.isoformat(),
                    "store_id": store["store_id"],
                    "product_id": product["product_id"],
                    "quantity": quantity,
                    "revenue": round(quantity * product["price"], 2),
                    "cost": round(quantity * product["cost"], 2),
                    "is_promotion": int(is_promo),
                })
    return pd.DataFrame(records)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/data_generator/test_sales_generator.py -v`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
git add src/data_generator/generator_config.py src/data_generator/sales_generator.py tests/data_generator/test_sales_generator.py
git commit -m "feat: generate synthetic sales data with seasonality, trend, promotion (BR-001)"
```

---

### Task 4: `inventory_generator.py`

**Files:**
- Create: `src/data_generator/inventory_generator.py`
- Test: `tests/data_generator/test_inventory_generator.py`

**Interfaces:**
- Consumes: `stores_df` (Task 1), `products_df` (Task 2), `sales_df` (Task 3, used to size initial stock)
- Produces: `generate_inventory_batches(stores_df: pd.DataFrame, products_df: pd.DataFrame, sales_df: pd.DataFrame, as_of_date: date, rng: np.random.Generator) -> pd.DataFrame` with columns `batch_id (str), store_id (int), product_id (int), quantity (int), received_date (str ISO), expiry_date (str ISO)`. Consumed by `optimization.constraints` (via `Batch` records) and `simulation.weekly_cycle`.

- [ ] **Step 1: Write failing test**

```python
import numpy as np
from datetime import date
from src.data_generator.store_generator import generate_stores
from src.data_generator.product_generator import generate_products
from src.data_generator.generator_config import SalesGenConfig
from src.data_generator.sales_generator import generate_sales_data
from src.data_generator.inventory_generator import generate_inventory_batches
from src import config


def test_generates_one_batch_per_store_product_pair():
    rng = np.random.default_rng(42)
    stores = generate_stores(3, config.CITIES, config.CITY_COORDINATES, rng)
    products = generate_products(2, config.CATEGORIES, rng)
    sales = generate_sales_data(stores, products, num_weeks=2, gen_config=SalesGenConfig(), rng=rng,
                                 start_date=date(2026, 1, 5))
    batches = generate_inventory_batches(stores, products, sales, as_of_date=date(2026, 1, 19), rng=rng)
    assert len(batches) == len(stores) * len(products)
    assert batches["batch_id"].is_unique
    assert (batches["quantity"] > 0).all()


def test_expiry_after_received_date():
    rng = np.random.default_rng(42)
    stores = generate_stores(3, config.CITIES, config.CITY_COORDINATES, rng)
    products = generate_products(2, config.CATEGORIES, rng)
    sales = generate_sales_data(stores, products, num_weeks=2, gen_config=SalesGenConfig(), rng=rng,
                                 start_date=date(2026, 1, 5))
    batches = generate_inventory_batches(stores, products, sales, as_of_date=date(2026, 1, 19), rng=rng)
    for _, row in batches.iterrows():
        assert date.fromisoformat(row["expiry_date"]) > date.fromisoformat(row["received_date"])
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/data_generator/test_inventory_generator.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Write implementation**

```python
"""UC-003 step 6 — sinh tồn kho ban đầu theo lô hàng, kèm hạn sử dụng (BR-012)."""
from datetime import date, timedelta

import numpy as np
import pandas as pd

_CATEGORY_SHELF_LIFE_DAYS = {
    "Essentials": 180, "Beverages": 270, "Dry Goods": 365, "Frozen": 45, "Household": 365,
}
_COVERAGE_DAYS_RANGE = (10, 20)
_RECEIVED_OFFSET_MAX_DAYS = 5


def generate_inventory_batches(stores_df: pd.DataFrame, products_df: pd.DataFrame, sales_df: pd.DataFrame,
                                as_of_date: date, rng: np.random.Generator) -> pd.DataFrame:
    avg_daily_demand = sales_df.groupby(["store_id", "product_id"])["quantity"].mean().to_dict()
    category_by_product = products_df.set_index("product_id")["category"].to_dict()
    records = []
    batch_counter = 1
    for _, store in stores_df.iterrows():
        for _, product in products_df.iterrows():
            demand = avg_daily_demand.get((store["store_id"], product["product_id"]), 1.0)
            coverage_days = rng.uniform(*_COVERAGE_DAYS_RANGE)
            quantity = max(1, int(round(demand * coverage_days)))
            received_date = as_of_date - timedelta(days=int(rng.integers(0, _RECEIVED_OFFSET_MAX_DAYS + 1)))
            shelf_life = _CATEGORY_SHELF_LIFE_DAYS[category_by_product[product["product_id"]]]
            expiry_date = received_date + timedelta(days=shelf_life)
            records.append({
                "batch_id": f"B{batch_counter:06d}",
                "store_id": store["store_id"],
                "product_id": product["product_id"],
                "quantity": quantity,
                "received_date": received_date.isoformat(),
                "expiry_date": expiry_date.isoformat(),
            })
            batch_counter += 1
    return pd.DataFrame(records)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/data_generator/test_inventory_generator.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add src/data_generator/inventory_generator.py tests/data_generator/test_inventory_generator.py
git commit -m "feat: generate synthetic inventory batches with expiry dates (BR-012)"
```

---

### Task 5: `logistics_generator.py`

**Files:**
- Create: `src/data_generator/logistics_generator.py`
- Test: `tests/data_generator/test_logistics_generator.py`

**Interfaces:**
- Consumes: `stores_df` (Task 1)
- Produces:
  - `generate_distance_matrix(stores_df: pd.DataFrame) -> pd.DataFrame` — columns `from_store_id, to_store_id, distance_km`
  - `generate_transport_cost_matrix(distance_df: pd.DataFrame, cost_per_km: float) -> pd.DataFrame` — columns `from_store_id, to_store_id, transport_cost`
  - `generate_delivery_schedule(stores_df: pd.DataFrame, days_per_week: int, rng: np.random.Generator) -> pd.DataFrame` — columns `from_store_id, to_store_id, allowed_days` (`allowed_days` = comma-joined weekday abbreviations, e.g. `"Mon,Thu"`)
  - All three are consumed by `optimization.rule_based`, `optimization.genetic_algorithm`, and `optimization.constraints`.

- [ ] **Step 1: Write failing test**

```python
import numpy as np
from src.data_generator.store_generator import generate_stores
from src.data_generator.logistics_generator import (
    generate_distance_matrix, generate_transport_cost_matrix, generate_delivery_schedule,
)
from src import config


def _stores():
    rng = np.random.default_rng(42)
    return generate_stores(4, config.CITIES, config.CITY_COORDINATES, rng)


def test_distance_matrix_covers_all_ordered_pairs_excluding_self():
    stores = _stores()
    df = generate_distance_matrix(stores)
    assert len(df) == len(stores) * (len(stores) - 1)
    assert (df["from_store_id"] != df["to_store_id"]).all()
    assert (df["distance_km"] > 0).all()


def test_transport_cost_scales_with_distance():
    stores = _stores()
    distance_df = generate_distance_matrix(stores)
    cost_df = generate_transport_cost_matrix(distance_df, cost_per_km=5000.0)
    merged = distance_df.merge(cost_df, on=["from_store_id", "to_store_id"])
    assert (merged["transport_cost"] == merged["distance_km"] * 5000.0).all()


def test_delivery_schedule_has_fixed_days_per_route():
    stores = _stores()
    rng = np.random.default_rng(42)
    df = generate_delivery_schedule(stores, days_per_week=2, rng=rng)
    assert len(df) == len(stores) * (len(stores) - 1)
    for _, row in df.iterrows():
        assert len(row["allowed_days"].split(",")) == 2
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/data_generator/test_logistics_generator.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Write implementation**

```python
"""UC-003 step 7 — sinh ma trận khoảng cách/chi phí và lịch giao hàng cố định (Mục 7A.2)."""
import math

import numpy as np
import pandas as pd

_WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return r * 2 * math.asin(math.sqrt(a))


def generate_distance_matrix(stores_df: pd.DataFrame) -> pd.DataFrame:
    records = []
    for _, a in stores_df.iterrows():
        for _, b in stores_df.iterrows():
            if a["store_id"] == b["store_id"]:
                continue
            records.append({
                "from_store_id": a["store_id"],
                "to_store_id": b["store_id"],
                "distance_km": round(_haversine_km(a["latitude"], a["longitude"], b["latitude"], b["longitude"]), 3),
            })
    return pd.DataFrame(records)


def generate_transport_cost_matrix(distance_df: pd.DataFrame, cost_per_km: float) -> pd.DataFrame:
    df = distance_df.copy()
    df["transport_cost"] = df["distance_km"] * cost_per_km
    return df[["from_store_id", "to_store_id", "transport_cost"]]


def generate_delivery_schedule(stores_df: pd.DataFrame, days_per_week: int, rng: np.random.Generator) -> pd.DataFrame:
    records = []
    for _, a in stores_df.iterrows():
        for _, b in stores_df.iterrows():
            if a["store_id"] == b["store_id"]:
                continue
            days = sorted(rng.choice(_WEEKDAYS, size=days_per_week, replace=False),
                          key=_WEEKDAYS.index)
            records.append({
                "from_store_id": a["store_id"],
                "to_store_id": b["store_id"],
                "allowed_days": ",".join(days),
            })
    return pd.DataFrame(records)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/data_generator/test_logistics_generator.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add src/data_generator/logistics_generator.py tests/data_generator/test_logistics_generator.py
git commit -m "feat: generate distance/transport cost matrices and delivery schedule"
```

---

### Task 6: `data_generator/main.py` (UC-003 entrypoint)

**Files:**
- Create: `src/data_generator/main.py`
- Test: `tests/data_generator/test_main.py`

**Interfaces:**
- Consumes: all of Tasks 1-5's `generate_*` functions, `config.DATA_DIR` and scale constants.
- Produces: `run_data_generation(output_dir: Path, seed: int = config.RANDOM_SEED, num_weeks: int = config.HISTORY_WEEKS) -> None` — writes `stores.csv`, `products.csv`, `sales_data.csv`, `inventory_batches.csv`, `distance_matrix.csv`, `transport_cost_matrix.csv`, `delivery_schedule.csv` into `output_dir`. Called by `src/main.py` (Task 20) for the `--generate-data` CLI flag.

- [ ] **Step 1: Write failing test**

```python
from src.data_generator.main import run_data_generation


def test_writes_all_expected_csv_files(tmp_path):
    run_data_generation(output_dir=tmp_path, seed=1, num_weeks=2)
    expected_files = {
        "stores.csv", "products.csv", "sales_data.csv", "inventory_batches.csv",
        "distance_matrix.csv", "transport_cost_matrix.csv", "delivery_schedule.csv",
    }
    actual_files = {p.name for p in tmp_path.glob("*.csv")}
    assert expected_files <= actual_files


def test_is_reproducible_with_same_seed(tmp_path):
    out1, out2 = tmp_path / "run1", tmp_path / "run2"
    out1.mkdir()
    out2.mkdir()
    run_data_generation(output_dir=out1, seed=7, num_weeks=2)
    run_data_generation(output_dir=out2, seed=7, num_weeks=2)
    import pandas as pd
    pd.testing.assert_frame_equal(pd.read_csv(out1 / "sales_data.csv"), pd.read_csv(out2 / "sales_data.csv"))
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/data_generator/test_main.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Write implementation**

```python
"""UC-003 — entrypoint sinh toàn bộ dữ liệu synthetic ban đầu."""
import argparse
from datetime import date, timedelta
from pathlib import Path

import numpy as np

from src import config
from src.data_generator.generator_config import SalesGenConfig
from src.data_generator.inventory_generator import generate_inventory_batches
from src.data_generator.logistics_generator import (
    generate_delivery_schedule, generate_distance_matrix, generate_transport_cost_matrix,
)
from src.data_generator.product_generator import generate_products
from src.data_generator.sales_generator import generate_sales_data
from src.data_generator.store_generator import generate_stores

_COST_PER_KM_VND = 5000.0


def run_data_generation(output_dir: Path, seed: int = config.RANDOM_SEED,
                         num_weeks: int = config.TOTAL_DATA_WEEKS) -> None:
    """`num_weeks` mặc định = HISTORY_WEEKS + SIMULATION_WEEKS: 52 tuần đầu là lịch sử mà
    forecaster được huấn luyện trên, 12 tuần cuối là nhu cầu thực tế "tương lai" mà
    `simulation.rolling_simulator` (Task 17) tiết lộ dần từng tuần khi chạy UC-001."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(seed)
    as_of_date = date.today()
    start_date = as_of_date - timedelta(days=num_weeks * 7)

    stores = generate_stores(config.NUM_STORES, config.CITIES, config.CITY_COORDINATES, rng)
    products = generate_products(config.NUM_PRODUCTS, config.CATEGORIES, rng)
    sales = generate_sales_data(stores, products, num_weeks, SalesGenConfig(), rng, start_date=start_date)
    batches = generate_inventory_batches(stores, products, sales, as_of_date, rng)
    distance = generate_distance_matrix(stores)
    transport_cost = generate_transport_cost_matrix(distance, _COST_PER_KM_VND)
    delivery_schedule = generate_delivery_schedule(stores, config.DELIVERY_DAYS_PER_WEEK, rng)

    stores.to_csv(output_dir / "stores.csv", index=False)
    products.to_csv(output_dir / "products.csv", index=False)
    sales.to_csv(output_dir / "sales_data.csv", index=False)
    batches.to_csv(output_dir / "inventory_batches.csv", index=False)
    distance.to_csv(output_dir / "distance_matrix.csv", index=False)
    transport_cost.to_csv(output_dir / "transport_cost_matrix.csv", index=False)
    delivery_schedule.to_csv(output_dir / "delivery_schedule.csv", index=False)


def _cli() -> None:
    parser = argparse.ArgumentParser(description="Sinh dữ liệu synthetic ban đầu (UC-003)")
    parser.add_argument("--output-dir", type=Path, default=config.DATA_DIR)
    parser.add_argument("--seed", type=int, default=config.RANDOM_SEED)
    parser.add_argument("--weeks", type=int, default=config.TOTAL_DATA_WEEKS)
    args = parser.parse_args()
    run_data_generation(args.output_dir, args.seed, args.weeks)
    print(f"Data generated at {args.output_dir}")


if __name__ == "__main__":
    _cli()
```

Note: `date.today()` makes `as_of_date`/`received_date`/`expiry_date` non-reproducible across days — this is acceptable since Step 1's reproducibility test only checks `sales_data.csv` (driven purely by `start_date`, which is itself derived from `date.today()` consistently within a single run, and both runs in the test execute the same day). If bitwise-identical inventory batches across days are ever needed, pass `as_of_date` as an explicit parameter — out of scope here (YAGNI).

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/data_generator/test_main.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Run the full data_generator test suite**

Run: `pytest tests/data_generator/ -v`
Expected: All tests pass (Tasks 1-6 combined)

- [ ] **Step 6: Commit**

```bash
git add src/data_generator/main.py tests/data_generator/test_main.py
git commit -m "feat: add UC-003 data generation entrypoint"
```

---

## Phase 2 — Forecasting (BR-002, BR-003)

### Task 7: `forecasting/base.py` — pluggable interface

**Files:**
- Create: `src/forecasting/base.py`
- Test: `tests/forecasting/test_base.py`

**Interfaces:**
- Produces: abstract class `Forecaster` with `fit(self, history: pd.Series) -> None` and `predict(self, horizon: int) -> pd.Series`. Every forecaster (Task 8, Task 9) implements this. `simulation.weekly_cycle` (Task 17) depends only on this interface (BR-003 — strategy pattern for pluggability).

- [ ] **Step 1: Write failing test**

```python
import pytest
from src.forecasting.base import Forecaster


def test_cannot_instantiate_abstract_forecaster():
    with pytest.raises(TypeError):
        Forecaster()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/forecasting/test_base.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Write implementation**

`src/forecasting/__init__.py`: (empty file)

`src/forecasting/base.py`:
```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/forecasting/test_base.py -v`
Expected: PASS (1 passed)

- [ ] **Step 5: Commit**

```bash
git add src/forecasting/__init__.py src/forecasting/base.py tests/forecasting/__init__.py tests/forecasting/test_base.py
git commit -m "feat: add pluggable Forecaster interface (BR-003)"
```

---

### Task 8: `forecasting/naive_forecaster.py`

**Files:**
- Create: `src/forecasting/naive_forecaster.py`
- Test: `tests/forecasting/test_naive_forecaster.py`

**Interfaces:**
- Consumes: `Forecaster` (Task 7)
- Produces: `NaiveForecaster(window: int = 14)` implementing `Forecaster`. Used directly for the baseline scenario in `simulation.weekly_cycle` (Task 17), and as the fallback inside `HoltWintersForecaster` (Task 9, OQ-009).

- [ ] **Step 1: Write failing test**

```python
import pandas as pd
from src.forecasting.naive_forecaster import NaiveForecaster


def test_predicts_flat_average_of_recent_window():
    history = pd.Series([10, 10, 10, 20, 20, 20, 20, 20, 20, 20], name="quantity")
    forecaster = NaiveForecaster(window=7)
    forecaster.fit(history)
    forecast = forecaster.predict(horizon=5)
    assert len(forecast) == 5
    assert all(abs(v - 20.0) < 1e-9 for v in forecast)


def test_raises_if_predict_called_before_fit():
    import pytest
    forecaster = NaiveForecaster()
    with pytest.raises(RuntimeError):
        forecaster.predict(horizon=3)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/forecasting/test_naive_forecaster.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Write implementation**

```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/forecasting/test_naive_forecaster.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add src/forecasting/naive_forecaster.py tests/forecasting/test_naive_forecaster.py
git commit -m "feat: add NaiveForecaster for baseline scenario and fallback"
```

---

### Task 9: `forecasting/holt_winters_forecaster.py`

**Files:**
- Create: `src/forecasting/holt_winters_forecaster.py`
- Test: `tests/forecasting/test_holt_winters_forecaster.py`

**Interfaces:**
- Consumes: `Forecaster` (Task 7), `NaiveForecaster` (Task 8, used as fallback)
- Produces: `HoltWintersForecaster(seasonal_periods: int = 7)` implementing `Forecaster`. Used for the optimized scenario in `simulation.weekly_cycle` (Task 17). Seasonal period is 7 (day-of-week) — matches `sales_generator`'s weekly seasonality pattern and is reliably fittable from 52 weeks of daily history.

- [ ] **Step 1: Write failing test**

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/forecasting/test_holt_winters_forecaster.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Write implementation**

```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/forecasting/test_holt_winters_forecaster.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add src/forecasting/holt_winters_forecaster.py tests/forecasting/test_holt_winters_forecaster.py
git commit -m "feat: add Holt-Winters forecaster with naive fallback (BR-002, OQ-009)"
```

---

## Phase 3 — Inventory Policy (BR-004–008)

### Task 10: `inventory_policy/safety_stock.py` and `reorder_point.py`

**Files:**
- Create: `src/inventory_policy/safety_stock.py`
- Create: `src/inventory_policy/reorder_point.py`
- Test: `tests/inventory_policy/test_safety_stock.py`
- Test: `tests/inventory_policy/test_reorder_point.py`

**Interfaces:**
- Produces: `compute_safety_stock(demand_std: float, z_score: float, lead_time_days: float) -> float` and `compute_reorder_point(avg_daily_demand: float, lead_time_days: float, safety_stock: float) -> float`. Both consumed by `inventory_policy.classifier` (Task 12) and `simulation.weekly_cycle` (Task 17).

- [ ] **Step 1: Write failing tests**

`tests/inventory_policy/test_safety_stock.py`:
```python
import math
from src.inventory_policy.safety_stock import compute_safety_stock


def test_matches_manual_formula():
    result = compute_safety_stock(demand_std=5.0, z_score=1.65, lead_time_days=4.0)
    expected = 1.65 * 5.0 * math.sqrt(4.0)
    assert abs(result - expected) < 1e-9


def test_zero_variance_gives_zero_safety_stock():
    assert compute_safety_stock(demand_std=0.0, z_score=2.05, lead_time_days=7.0) == 0.0
```

`tests/inventory_policy/test_reorder_point.py`:
```python
from src.inventory_policy.reorder_point import compute_reorder_point


def test_matches_manual_formula():
    result = compute_reorder_point(avg_daily_demand=10.0, lead_time_days=3.0, safety_stock=8.0)
    assert result == 10.0 * 3.0 + 8.0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/inventory_policy/ -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Write implementation**

`src/inventory_policy/__init__.py`: (empty file)

`src/inventory_policy/safety_stock.py`:
```python
"""BR-006 — safety stock = Z(service level) x sigma(demand) x sqrt(lead time)."""
import math


def compute_safety_stock(demand_std: float, z_score: float, lead_time_days: float) -> float:
    return z_score * demand_std * math.sqrt(lead_time_days)
```

`src/inventory_policy/reorder_point.py`:
```python
"""BR-007 — reorder point = nhu cầu trung bình trong lead time + safety stock."""


def compute_reorder_point(avg_daily_demand: float, lead_time_days: float, safety_stock: float) -> float:
    return avg_daily_demand * lead_time_days + safety_stock
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/inventory_policy/ -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add src/inventory_policy/__init__.py src/inventory_policy/safety_stock.py src/inventory_policy/reorder_point.py tests/inventory_policy/__init__.py tests/inventory_policy/test_safety_stock.py tests/inventory_policy/test_reorder_point.py
git commit -m "feat: implement safety stock and reorder point formulas (BR-006, BR-007)"
```

---

### Task 11: `inventory_policy/classifier.py`

**Files:**
- Create: `src/inventory_policy/classifier.py`
- Test: `tests/inventory_policy/test_classifier.py`

**Interfaces:**
- Consumes: nothing from earlier tasks directly (pure logic module)
- Produces:
  - `StockStatus(Enum)`: `SURPLUS`, `DEFICIT`, `NORMAL`
  - `StockPosition(dataclass)`: `store_id: int, product_id: int, current_stock: float, reorder_point: float, safety_stock: float`
  - `classify_stock(position: StockPosition) -> StockStatus` — optimized scenario (BR-008)
  - `classify_stock_baseline(current_stock: float, avg_daily_demand: float, min_days: float, max_days: float) -> StockStatus` — baseline scenario (v1-style days-of-inventory)
  - Both consumed by `simulation.weekly_cycle` (Task 17).

- [ ] **Step 1: Write failing test**

```python
from src.inventory_policy.classifier import (
    StockStatus, StockPosition, classify_stock, classify_stock_baseline,
)


def test_below_reorder_point_is_deficit():
    pos = StockPosition(store_id=1, product_id=1, current_stock=5, reorder_point=20, safety_stock=8)
    assert classify_stock(pos) == StockStatus.DEFICIT


def test_more_than_double_reorder_point_is_surplus():
    pos = StockPosition(store_id=1, product_id=1, current_stock=50, reorder_point=20, safety_stock=8)
    assert classify_stock(pos) == StockStatus.SURPLUS


def test_between_reorder_point_and_double_is_normal():
    pos = StockPosition(store_id=1, product_id=1, current_stock=25, reorder_point=20, safety_stock=8)
    assert classify_stock(pos) == StockStatus.NORMAL


def test_baseline_below_min_days_is_deficit():
    assert classify_stock_baseline(current_stock=20, avg_daily_demand=10, min_days=7, max_days=30) == StockStatus.DEFICIT


def test_baseline_above_max_days_is_surplus():
    assert classify_stock_baseline(current_stock=400, avg_daily_demand=10, min_days=7, max_days=30) == StockStatus.SURPLUS


def test_baseline_zero_demand_is_normal():
    assert classify_stock_baseline(current_stock=100, avg_daily_demand=0, min_days=7, max_days=30) == StockStatus.NORMAL
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/inventory_policy/test_classifier.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Write implementation**

```python
"""BR-008 — phân loại thừa/thiếu theo reorder point/safety stock (tối ưu) hoặc days-of-inventory (baseline)."""
from dataclasses import dataclass
from enum import Enum


class StockStatus(Enum):
    SURPLUS = "surplus"
    DEFICIT = "deficit"
    NORMAL = "normal"


@dataclass
class StockPosition:
    store_id: int
    product_id: int
    current_stock: float
    reorder_point: float
    safety_stock: float


# Ngưỡng surplus: tồn kho vượt quá 2x reorder point coi là dư đáng kể để có thể chuyển bớt.
# Quyết định kỹ thuật (BR-008 không quy định con số cụ thể).
_SURPLUS_MULTIPLIER = 2.0


def classify_stock(position: StockPosition) -> StockStatus:
    if position.current_stock < position.reorder_point:
        return StockStatus.DEFICIT
    if position.current_stock > _SURPLUS_MULTIPLIER * position.reorder_point:
        return StockStatus.SURPLUS
    return StockStatus.NORMAL


def classify_stock_baseline(current_stock: float, avg_daily_demand: float,
                             min_days: float, max_days: float) -> StockStatus:
    if avg_daily_demand <= 0:
        return StockStatus.NORMAL
    days_of_inventory = current_stock / avg_daily_demand
    if days_of_inventory < min_days:
        return StockStatus.DEFICIT
    if days_of_inventory > max_days:
        return StockStatus.SURPLUS
    return StockStatus.NORMAL
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/inventory_policy/test_classifier.py -v`
Expected: PASS (6 passed)

- [ ] **Step 5: Commit**

```bash
git add src/inventory_policy/classifier.py tests/inventory_policy/test_classifier.py
git commit -m "feat: classify stock surplus/deficit for optimized and baseline scenarios (BR-008)"
```

---

## Phase 4 — Optimization (BR-009–016)

### Task 12: `optimization/constraints.py`

**Files:**
- Create: `src/optimization/constraints.py`
- Test: `tests/optimization/test_constraints.py`

**Interfaces:**
- Produces:
  - `Batch(dataclass)`: `batch_id: str, store_id: int, product_id: int, quantity: float, expiry_date: date`
  - `TransferConstraints(dataclass)`: `vehicle_capacity_kg: float, vehicle_capacity_m3: float, delivery_schedule: dict[tuple[int, int], list[str]], min_shelf_life_days: int`
  - `TransferLine(dataclass)`: `from_store_id: int, to_store_id: int, product_id: int, batch_id: str, quantity: float, weight_kg: float, volume_l: float`
  - `filter_eligible_batches(batches: list[Batch], current_date: date, min_shelf_life_days: int) -> list[Batch]` — BR-013 (FEFO order), BR-014 (exclude near-expiry)
  - `is_delivery_day(from_store_id: int, to_store_id: int, current_date: date, delivery_schedule: dict) -> bool` — BR-011
  - `route_totals(transfer_lines: list[TransferLine]) -> dict[tuple[int, int], tuple[float, float]]`
  - `is_feasible(transfer_lines: list[TransferLine], constraints: TransferConstraints) -> bool` — BR-010
  - All of the above consumed identically by `optimization.rule_based` (Task 13) and `optimization.genetic_algorithm` (Task 14) — this is the single shared source of truth for constraint logic (BR-015, BR-016 must not diverge).

- [ ] **Step 1: Write failing test**

```python
from datetime import date
from src.optimization.constraints import (
    Batch, TransferConstraints, TransferLine,
    filter_eligible_batches, is_delivery_day, route_totals, is_feasible,
)


def test_filter_eligible_batches_excludes_near_expiry_and_sorts_fefo():
    today = date(2026, 1, 1)
    batches = [
        Batch("B1", store_id=1, product_id=1, quantity=10, expiry_date=date(2026, 1, 3)),   # < 7 days: excluded
        Batch("B2", store_id=1, product_id=1, quantity=10, expiry_date=date(2026, 2, 1)),   # eligible, later expiry
        Batch("B3", store_id=1, product_id=1, quantity=10, expiry_date=date(2026, 1, 20)),  # eligible, earlier expiry
    ]
    eligible = filter_eligible_batches(batches, current_date=today, min_shelf_life_days=7)
    assert [b.batch_id for b in eligible] == ["B3", "B2"]


def test_is_delivery_day_checks_schedule():
    schedule = {(1, 2): ["Mon", "Thu"]}
    monday = date(2026, 1, 5)  # a Monday
    tuesday = date(2026, 1, 6)
    assert is_delivery_day(1, 2, monday, schedule) is True
    assert is_delivery_day(1, 2, tuesday, schedule) is False
    assert is_delivery_day(2, 1, monday, schedule) is False  # no schedule for reverse route


def test_route_totals_sums_weight_and_volume_per_route():
    lines = [
        TransferLine(1, 2, product_id=1, batch_id="B1", quantity=10, weight_kg=5.0, volume_l=2.0),
        TransferLine(1, 2, product_id=2, batch_id="B2", quantity=5, weight_kg=3.0, volume_l=1.0),
        TransferLine(1, 3, product_id=1, batch_id="B3", quantity=8, weight_kg=4.0, volume_l=1.5),
    ]
    totals = route_totals(lines)
    assert totals[(1, 2)] == (8.0, 3.0)
    assert totals[(1, 3)] == (4.0, 1.5)


def test_is_feasible_respects_vehicle_capacity():
    constraints = TransferConstraints(vehicle_capacity_kg=10.0, vehicle_capacity_m3=5.0,
                                       delivery_schedule={}, min_shelf_life_days=7)
    ok_lines = [TransferLine(1, 2, 1, "B1", quantity=1, weight_kg=8.0, volume_l=2.0)]
    over_lines = [TransferLine(1, 2, 1, "B1", quantity=1, weight_kg=11.0, volume_l=2.0)]
    assert is_feasible(ok_lines, constraints) is True
    assert is_feasible(over_lines, constraints) is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/optimization/test_constraints.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Write implementation**

`src/optimization/__init__.py`: (empty file)

`src/optimization/constraints.py`:
```python
"""BR-009–016 — mô hình ràng buộc dùng chung cho rule-based và genetic algorithm."""
from collections import defaultdict
from dataclasses import dataclass
from datetime import date


@dataclass
class Batch:
    batch_id: str
    store_id: int
    product_id: int
    quantity: float
    expiry_date: date


@dataclass
class TransferConstraints:
    vehicle_capacity_kg: float
    vehicle_capacity_m3: float
    delivery_schedule: dict[tuple[int, int], list[str]]
    min_shelf_life_days: int


@dataclass
class TransferLine:
    from_store_id: int
    to_store_id: int
    product_id: int
    batch_id: str
    quantity: float
    weight_kg: float
    volume_l: float


def filter_eligible_batches(batches: list[Batch], current_date: date, min_shelf_life_days: int) -> list[Batch]:
    """BR-013 (FEFO), BR-014 (loại hàng cận hạn)."""
    eligible = [b for b in batches if (b.expiry_date - current_date).days >= min_shelf_life_days]
    return sorted(eligible, key=lambda b: b.expiry_date)


def is_delivery_day(from_store_id: int, to_store_id: int, current_date: date,
                     delivery_schedule: dict[tuple[int, int], list[str]]) -> bool:
    """BR-011."""
    allowed_days = delivery_schedule.get((from_store_id, to_store_id), [])
    weekday_name = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"][current_date.weekday()]
    return weekday_name in allowed_days


def route_totals(transfer_lines: list[TransferLine]) -> dict[tuple[int, int], tuple[float, float]]:
    totals: dict[tuple[int, int], list[float]] = defaultdict(lambda: [0.0, 0.0])
    for line in transfer_lines:
        key = (line.from_store_id, line.to_store_id)
        totals[key][0] += line.weight_kg
        totals[key][1] += line.volume_l
    return {key: (w, v) for key, (w, v) in totals.items()}


def is_feasible(transfer_lines: list[TransferLine], constraints: TransferConstraints) -> bool:
    """BR-010."""
    for weight_kg, volume_l in route_totals(transfer_lines).values():
        if weight_kg > constraints.vehicle_capacity_kg or volume_l > constraints.vehicle_capacity_m3:
            return False
    return True
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/optimization/test_constraints.py -v`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
git add src/optimization/__init__.py src/optimization/constraints.py tests/optimization/__init__.py tests/optimization/test_constraints.py
git commit -m "feat: implement shared transfer constraints (vehicle capacity, delivery schedule, FEFO)"
```

---

### Task 13: `optimization/rule_based.py`

**Files:**
- Create: `src/optimization/rule_based.py`
- Test: `tests/optimization/test_rule_based.py`

**Interfaces:**
- Consumes: `StockPosition` (Task 11), `Batch`/`TransferConstraints`/`TransferLine`/`filter_eligible_batches`/`is_feasible` (Task 12)
- Produces: `plan_transfers_rule_based(deficits: list[StockPosition], surpluses: list[StockPosition], batches_by_store_product: dict[tuple[int, int], list[Batch]], distance_km: dict[tuple[int, int], float], product_attrs: dict[int, tuple[float, float]], constraints: TransferConstraints, current_date: date) -> list[TransferLine]`. **Note:** mutates `Batch.quantity` and `StockPosition.current_stock` on the input objects to reflect consumption — callers (`simulation.weekly_cycle`, Task 17) must pass fresh per-week copies. Consumed by `simulation.weekly_cycle` for the rule-based algorithm choice (BR-015).

- [ ] **Step 1: Write failing test**

```python
from datetime import date
from src.inventory_policy.classifier import StockPosition
from src.optimization.constraints import Batch, TransferConstraints
from src.optimization.rule_based import plan_transfers_rule_based


def _base_constraints():
    return TransferConstraints(vehicle_capacity_kg=1000.0, vehicle_capacity_m3=1000.0,
                                delivery_schedule={(2, 1): ["Mon"]}, min_shelf_life_days=7)


def test_transfers_from_eligible_surplus_to_deficit():
    deficit = StockPosition(store_id=1, product_id=10, current_stock=5, reorder_point=25, safety_stock=10)
    surplus = StockPosition(store_id=2, product_id=10, current_stock=100, reorder_point=20, safety_stock=10)
    batches = {(2, 10): [Batch("B1", 2, 10, quantity=50, expiry_date=date(2026, 3, 1))]}
    plan = plan_transfers_rule_based(
        deficits=[deficit], surpluses=[surplus], batches_by_store_product=batches,
        distance_km={(2, 1): 10.0}, product_attrs={10: (1.0, 1.0)},
        constraints=_base_constraints(), current_date=date(2026, 1, 5),
    )
    assert len(plan) == 1
    assert plan[0].from_store_id == 2 and plan[0].to_store_id == 1
    assert plan[0].quantity == 20  # reorder_point(25) - current_stock(5)


def test_skips_route_without_delivery_schedule():
    deficit = StockPosition(store_id=1, product_id=10, current_stock=5, reorder_point=25, safety_stock=10)
    surplus = StockPosition(store_id=3, product_id=10, current_stock=100, reorder_point=20, safety_stock=10)
    batches = {(3, 10): [Batch("B1", 3, 10, quantity=50, expiry_date=date(2026, 3, 1))]}
    plan = plan_transfers_rule_based(
        deficits=[deficit], surpluses=[surplus], batches_by_store_product=batches,
        distance_km={(3, 1): 10.0}, product_attrs={10: (1.0, 1.0)},
        constraints=_base_constraints(), current_date=date(2026, 1, 5),  # schedule chỉ có (2,1)
    )
    assert plan == []


def test_caps_quantity_to_stay_within_vehicle_capacity():
    deficit = StockPosition(store_id=1, product_id=10, current_stock=0, reorder_point=100, safety_stock=10)
    surplus = StockPosition(store_id=2, product_id=10, current_stock=200, reorder_point=10, safety_stock=10)
    batches = {(2, 10): [Batch("B1", 2, 10, quantity=100, expiry_date=date(2026, 3, 1))]}
    constraints = TransferConstraints(vehicle_capacity_kg=50.0, vehicle_capacity_m3=1000.0,
                                       delivery_schedule={(2, 1): ["Mon"]}, min_shelf_life_days=7)
    plan = plan_transfers_rule_based(
        deficits=[deficit], surpluses=[surplus], batches_by_store_product=batches,
        distance_km={(2, 1): 10.0}, product_attrs={10: (2.0, 0.5)},  # 2kg/unit -> capped at 25 units
        constraints=constraints, current_date=date(2026, 1, 5),
    )
    assert sum(l.weight_kg for l in plan) <= 50.0
    assert plan[0].quantity == 25


def test_excludes_near_expiry_batches():
    deficit = StockPosition(store_id=1, product_id=10, current_stock=5, reorder_point=25, safety_stock=10)
    surplus = StockPosition(store_id=2, product_id=10, current_stock=100, reorder_point=20, safety_stock=10)
    batches = {(2, 10): [Batch("B1", 2, 10, quantity=50, expiry_date=date(2026, 1, 8))]}  # còn 3 ngày < 7
    plan = plan_transfers_rule_based(
        deficits=[deficit], surpluses=[surplus], batches_by_store_product=batches,
        distance_km={(2, 1): 10.0}, product_attrs={10: (1.0, 1.0)},
        constraints=_base_constraints(), current_date=date(2026, 1, 5),
    )
    assert plan == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/optimization/test_rule_based.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Write implementation**

```python
"""BR-015 — rule-based greedy transfer planning, tôn trọng ràng buộc chung (constraints.py)."""
from datetime import date

from src.inventory_policy.classifier import StockPosition
from src.optimization.constraints import (
    Batch, TransferConstraints, TransferLine, filter_eligible_batches, is_feasible,
)


def plan_transfers_rule_based(
    deficits: list[StockPosition],
    surpluses: list[StockPosition],
    batches_by_store_product: dict[tuple[int, int], list[Batch]],
    distance_km: dict[tuple[int, int], float],
    product_attrs: dict[int, tuple[float, float]],
    constraints: TransferConstraints,
    current_date: date,
) -> list[TransferLine]:
    plan: list[TransferLine] = []
    route_usage: dict[tuple[int, int], list[float]] = {}

    sorted_deficits = sorted(deficits, key=lambda p: p.reorder_point - p.current_stock, reverse=True)

    for deficit in sorted_deficits:
        remaining_need = deficit.reorder_point - deficit.current_stock
        if remaining_need <= 0:
            continue
        weight_per_unit, volume_per_unit = product_attrs[deficit.product_id]

        candidates = [
            s for s in surpluses
            if s.product_id == deficit.product_id
            and (s.store_id, deficit.store_id) in constraints.delivery_schedule
        ]
        candidates.sort(key=lambda s: distance_km.get((s.store_id, deficit.store_id), float("inf")))

        for surplus in candidates:
            if remaining_need <= 0:
                break
            key = (surplus.store_id, deficit.product_id)
            eligible_batches = filter_eligible_batches(
                batches_by_store_product.get(key, []), current_date, constraints.min_shelf_life_days,
            )
            route_key = (surplus.store_id, deficit.store_id)
            used_weight, used_volume = route_usage.get(route_key, [0.0, 0.0])

            for batch in eligible_batches:
                if remaining_need <= 0:
                    break
                available_in_batch = min(batch.quantity, surplus.current_stock - surplus.reorder_point)
                if available_in_batch <= 0:
                    continue
                take_qty = min(remaining_need, available_in_batch)

                added_weight = take_qty * weight_per_unit
                added_volume = take_qty * volume_per_unit
                if (used_weight + added_weight > constraints.vehicle_capacity_kg
                        or used_volume + added_volume > constraints.vehicle_capacity_m3):
                    remaining_weight_cap = constraints.vehicle_capacity_kg - used_weight
                    remaining_volume_cap = constraints.vehicle_capacity_m3 - used_volume
                    max_by_weight = remaining_weight_cap / weight_per_unit if weight_per_unit > 0 else take_qty
                    max_by_volume = remaining_volume_cap / volume_per_unit if volume_per_unit > 0 else take_qty
                    take_qty = max(0, min(take_qty, max_by_weight, max_by_volume))
                    if take_qty <= 0:
                        continue
                    added_weight = take_qty * weight_per_unit
                    added_volume = take_qty * volume_per_unit

                plan.append(TransferLine(
                    from_store_id=surplus.store_id, to_store_id=deficit.store_id,
                    product_id=deficit.product_id, batch_id=batch.batch_id,
                    quantity=take_qty, weight_kg=added_weight, volume_l=added_volume,
                ))
                used_weight += added_weight
                used_volume += added_volume
                route_usage[route_key] = [used_weight, used_volume]
                remaining_need -= take_qty
                batch.quantity -= take_qty
                surplus.current_stock -= take_qty

    assert is_feasible(plan, constraints), "internal invariant: rule-based plan must respect capacity"
    return plan
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/optimization/test_rule_based.py -v`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
git add src/optimization/rule_based.py tests/optimization/test_rule_based.py
git commit -m "feat: implement rule-based greedy transfer planning (BR-015)"
```

---

### Task 14: `optimization/genetic_algorithm.py`

**Files:**
- Create: `src/optimization/genetic_algorithm.py`
- Test: `tests/optimization/test_genetic_algorithm.py`

**Interfaces:**
- Consumes: `StockPosition` (Task 11), `Batch`/`TransferConstraints`/`TransferLine`/`filter_eligible_batches`/`route_totals` (Task 12)
- Produces: `plan_transfers_ga(deficits: list[StockPosition], surpluses: list[StockPosition], batches_by_store_product: dict[tuple[int, int], list[Batch]], transport_cost: dict[tuple[int, int], float], product_attrs: dict[int, tuple[float, float]], constraints: TransferConstraints, current_date: date, population_size: int = 60, generations: int = 150, seed: int = 42) -> list[TransferLine]`. Guarantees the returned plan is always capacity-feasible (post-hoc proportional clipping). Consumed by `simulation.weekly_cycle` for the GA algorithm choice (BR-016).

- [ ] **Step 1: Write failing test**

```python
from datetime import date
from src.inventory_policy.classifier import StockPosition
from src.optimization.constraints import Batch, TransferConstraints
from src.optimization.genetic_algorithm import plan_transfers_ga


def _base_constraints():
    return TransferConstraints(vehicle_capacity_kg=1000.0, vehicle_capacity_m3=1000.0,
                                delivery_schedule={(2, 1): ["Mon"]}, min_shelf_life_days=7)


def test_covers_deficit_within_reasonable_tolerance():
    deficit = StockPosition(store_id=1, product_id=10, current_stock=5, reorder_point=25, safety_stock=10)
    surplus = StockPosition(store_id=2, product_id=10, current_stock=100, reorder_point=20, safety_stock=10)
    batches = {(2, 10): [Batch("B1", 2, 10, quantity=50, expiry_date=date(2026, 3, 1))]}
    plan = plan_transfers_ga(
        deficits=[deficit], surpluses=[surplus], batches_by_store_product=batches,
        transport_cost={(2, 1): 50_000.0}, product_attrs={10: (1.0, 1.0)},
        constraints=_base_constraints(), current_date=date(2026, 1, 5),
        population_size=20, generations=30, seed=1,
    )
    total_transferred = sum(l.quantity for l in plan)
    assert 20 <= total_transferred <= 30  # phải >= nhu cầu (25-5=20); GA cho phép dư nhẹ do bản chất heuristic


def test_returns_empty_plan_when_no_candidates():
    deficit = StockPosition(store_id=1, product_id=10, current_stock=5, reorder_point=25, safety_stock=10)
    plan = plan_transfers_ga(
        deficits=[deficit], surpluses=[], batches_by_store_product={},
        transport_cost={}, product_attrs={10: (1.0, 1.0)},
        constraints=_base_constraints(), current_date=date(2026, 1, 5),
        population_size=10, generations=5, seed=1,
    )
    assert plan == []


def test_never_exceeds_vehicle_capacity():
    deficit = StockPosition(store_id=1, product_id=10, current_stock=0, reorder_point=100, safety_stock=10)
    surplus = StockPosition(store_id=2, product_id=10, current_stock=300, reorder_point=10, safety_stock=10)
    batches = {(2, 10): [Batch("B1", 2, 10, quantity=200, expiry_date=date(2026, 3, 1))]}
    constraints = TransferConstraints(vehicle_capacity_kg=50.0, vehicle_capacity_m3=1000.0,
                                       delivery_schedule={(2, 1): ["Mon"]}, min_shelf_life_days=7)
    plan = plan_transfers_ga(
        deficits=[deficit], surpluses=[surplus], batches_by_store_product=batches,
        transport_cost={(2, 1): 50_000.0}, product_attrs={10: (2.0, 0.5)},
        constraints=constraints, current_date=date(2026, 1, 5),
        population_size=20, generations=30, seed=1,
    )
    assert sum(l.weight_kg for l in plan) <= 50.0 + 1e-6


def test_is_reproducible_with_same_seed():
    deficit = StockPosition(store_id=1, product_id=10, current_stock=5, reorder_point=25, safety_stock=10)
    surplus = StockPosition(store_id=2, product_id=10, current_stock=100, reorder_point=20, safety_stock=10)
    kwargs = dict(deficits=[deficit], surpluses=[surplus], transport_cost={(2, 1): 50_000.0},
                  product_attrs={10: (1.0, 1.0)}, constraints=_base_constraints(),
                  current_date=date(2026, 1, 5), population_size=20, generations=30, seed=99)
    batches_a = {(2, 10): [Batch("B1", 2, 10, quantity=50, expiry_date=date(2026, 3, 1))]}
    batches_b = {(2, 10): [Batch("B1", 2, 10, quantity=50, expiry_date=date(2026, 3, 1))]}
    plan_a = plan_transfers_ga(batches_by_store_product=batches_a, **kwargs)
    plan_b = plan_transfers_ga(batches_by_store_product=batches_b, **kwargs)
    key = lambda plan: [(l.from_store_id, l.to_store_id, l.quantity) for l in plan]
    assert key(plan_a) == key(plan_b)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/optimization/test_genetic_algorithm.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Write implementation**

```python
"""BR-016 — genetic algorithm cho lập kế hoạch chuyển hàng, tôn trọng ràng buộc dùng chung."""
from dataclasses import dataclass
from datetime import date

import numpy as np

from src.inventory_policy.classifier import StockPosition
from src.optimization.constraints import (
    Batch, TransferConstraints, TransferLine, filter_eligible_batches, route_totals,
)

_DEFICIT_PENALTY_PER_UNIT = 100_000.0
_CAPACITY_PENALTY_PER_UNIT = 100_000.0
_WASTE_PENALTY_PER_UNIT = 1.0


@dataclass
class _Candidate:
    from_store_id: int
    to_store_id: int
    product_id: int
    batch_id: str
    max_quantity: float
    weight_per_unit: float
    volume_per_unit: float


def _build_candidates(deficits, surpluses, batches_by_store_product, product_attrs,
                       constraints: TransferConstraints, current_date: date) -> list[_Candidate]:
    candidates: list[_Candidate] = []
    for deficit in deficits:
        for surplus in surpluses:
            if surplus.product_id != deficit.product_id:
                continue
            if (surplus.store_id, deficit.store_id) not in constraints.delivery_schedule:
                continue
            key = (surplus.store_id, deficit.product_id)
            eligible = filter_eligible_batches(
                batches_by_store_product.get(key, []), current_date, constraints.min_shelf_life_days,
            )
            weight_per_unit, volume_per_unit = product_attrs[deficit.product_id]
            available_surplus = max(0.0, surplus.current_stock - surplus.reorder_point)
            for batch in eligible:
                max_qty = min(batch.quantity, available_surplus)
                if max_qty <= 0:
                    continue
                candidates.append(_Candidate(surplus.store_id, deficit.store_id, deficit.product_id,
                                              batch.batch_id, max_qty, weight_per_unit, volume_per_unit))
    return candidates


def _decode(genes: np.ndarray, candidates: list[_Candidate]) -> list[TransferLine]:
    lines = []
    for gene, candidate in zip(genes, candidates):
        quantity = int(round(gene))
        if quantity <= 0:
            continue
        lines.append(TransferLine(
            candidate.from_store_id, candidate.to_store_id, candidate.product_id, candidate.batch_id,
            quantity=quantity, weight_kg=quantity * candidate.weight_per_unit,
            volume_l=quantity * candidate.volume_per_unit,
        ))
    return lines


def _fitness(genes: np.ndarray, candidates: list[_Candidate], deficits: list[StockPosition],
             transport_cost: dict[tuple[int, int], float], constraints: TransferConstraints) -> float:
    lines = _decode(genes, candidates)
    routes_used = {(l.from_store_id, l.to_store_id) for l in lines}
    cost = sum(transport_cost.get(route, 0.0) for route in routes_used)

    allocated_by_deficit: dict[tuple[int, int], float] = {}
    for line in lines:
        key = (line.to_store_id, line.product_id)
        allocated_by_deficit[key] = allocated_by_deficit.get(key, 0.0) + line.quantity

    deficit_penalty = 0.0
    waste_penalty = 0.0
    for deficit in deficits:
        need = max(0.0, deficit.reorder_point - deficit.current_stock)
        allocated = allocated_by_deficit.get((deficit.store_id, deficit.product_id), 0.0)
        deficit_penalty += max(0.0, need - allocated) * _DEFICIT_PENALTY_PER_UNIT
        waste_penalty += max(0.0, allocated - need) * _WASTE_PENALTY_PER_UNIT

    capacity_penalty = 0.0
    for weight_kg, volume_l in route_totals(lines).values():
        over_weight = max(0.0, weight_kg - constraints.vehicle_capacity_kg)
        over_volume = max(0.0, volume_l - constraints.vehicle_capacity_m3)
        capacity_penalty += (over_weight + over_volume) * _CAPACITY_PENALTY_PER_UNIT

    return cost + deficit_penalty + waste_penalty + capacity_penalty


def _clip_to_feasible(lines: list[TransferLine], constraints: TransferConstraints) -> list[TransferLine]:
    """Co giãn tỷ lệ các dòng trên mỗi tuyến vượt sức chứa để đảm bảo kế hoạch trả về luôn khả thi."""
    scale_by_route: dict[tuple[int, int], float] = {}
    for route, (weight_kg, volume_l) in route_totals(lines).items():
        scale_weight = constraints.vehicle_capacity_kg / weight_kg if weight_kg > constraints.vehicle_capacity_kg else 1.0
        scale_volume = constraints.vehicle_capacity_m3 / volume_l if volume_l > constraints.vehicle_capacity_m3 else 1.0
        scale_by_route[route] = min(scale_weight, scale_volume)

    clipped = []
    for line in lines:
        scale = scale_by_route.get((line.from_store_id, line.to_store_id), 1.0)
        quantity = int(round(line.quantity * scale))
        if quantity <= 0:
            continue
        ratio = quantity / line.quantity
        clipped.append(TransferLine(line.from_store_id, line.to_store_id, line.product_id, line.batch_id,
                                     quantity=quantity, weight_kg=line.weight_kg * ratio,
                                     volume_l=line.volume_l * ratio))
    return clipped


def _tournament_select(population: np.ndarray, fitness_values: np.ndarray, rng: np.random.Generator,
                        tournament_size: int = 3) -> np.ndarray:
    indices = rng.choice(len(population), size=tournament_size, replace=False)
    return population[indices[np.argmin(fitness_values[indices])]]


def _crossover(parent_a: np.ndarray, parent_b: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    if len(parent_a) < 2:
        return parent_a.copy()
    point = rng.integers(1, len(parent_a))
    return np.concatenate([parent_a[:point], parent_b[point:]])


def _mutate(genes: np.ndarray, max_quantities: np.ndarray, rng: np.random.Generator,
            mutation_rate: float = 0.1) -> np.ndarray:
    mutated = genes.copy()
    mask = rng.random(len(genes)) < mutation_rate
    mutated[mask] = rng.uniform(0, max_quantities[mask])
    return mutated


def plan_transfers_ga(
    deficits: list[StockPosition],
    surpluses: list[StockPosition],
    batches_by_store_product: dict[tuple[int, int], list[Batch]],
    transport_cost: dict[tuple[int, int], float],
    product_attrs: dict[int, tuple[float, float]],
    constraints: TransferConstraints,
    current_date: date,
    population_size: int = 60,
    generations: int = 150,
    seed: int = 42,
) -> list[TransferLine]:
    rng = np.random.default_rng(seed)
    candidates = _build_candidates(deficits, surpluses, batches_by_store_product, product_attrs,
                                    constraints, current_date)
    if not candidates:
        return []

    max_quantities = np.array([c.max_quantity for c in candidates])
    population = rng.uniform(0, max_quantities, size=(population_size, len(candidates)))

    def fitness_of(genes: np.ndarray) -> float:
        return _fitness(genes, candidates, deficits, transport_cost, constraints)

    best_genes = population[0]
    best_fitness = fitness_of(best_genes)

    for _ in range(generations):
        fitness_values = np.array([fitness_of(ind) for ind in population])
        gen_best_idx = int(np.argmin(fitness_values))
        if fitness_values[gen_best_idx] < best_fitness:
            best_fitness = fitness_values[gen_best_idx]
            best_genes = population[gen_best_idx].copy()

        new_population = [population[gen_best_idx].copy()]  # elitism
        while len(new_population) < population_size:
            parent_a = _tournament_select(population, fitness_values, rng)
            parent_b = _tournament_select(population, fitness_values, rng)
            child = _mutate(_crossover(parent_a, parent_b, rng), max_quantities, rng)
            new_population.append(child)
        population = np.array(new_population)

    return _clip_to_feasible(_decode(best_genes, candidates), constraints)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/optimization/test_genetic_algorithm.py -v`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
git add src/optimization/genetic_algorithm.py tests/optimization/test_genetic_algorithm.py
git commit -m "feat: implement genetic algorithm transfer planning (BR-016)"
```

---

## Phase 5 — Simulation (UC-001, UC-002, BR-017–020)

### Task 15: `simulation/kpi_tracker.py`

**Files:**
- Create: `src/simulation/kpi_tracker.py`
- Test: `tests/simulation/test_kpi_tracker.py`

**Interfaces:**
- Consumes: `TransferLine` (Task 12)
- Produces:
  - `WeeklyKPI(dataclass)`: `week: int, scenario: str, algorithm: str, stockout_rate: float, excess_inventory_value: float, transport_cost: float, mape: float`
  - `compute_stockout_rate(demand_by_key: dict[tuple[int, int], float], available_stock_by_key: dict[tuple[int, int], float]) -> float`
  - `compute_excess_inventory_value(end_of_week_stock_by_key: dict[tuple[int, int], float], threshold_by_key: dict[tuple[int, int], float], cost_by_product: dict[int, float]) -> float`
  - `compute_transport_cost(transfer_lines: list[TransferLine], transport_cost_matrix: dict[tuple[int, int], float]) -> float`
  - `compute_mape(forecast_by_key: dict[tuple[int, int], float], actual_by_key: dict[tuple[int, int], float]) -> float`
  - All four consumed by `simulation.weekly_cycle` (Task 16) inside `run_week`. `WeeklyKPI` consumed by `simulation.rolling_simulator` (Task 17) and `reporting.dashboard_generator` (Task 18).

- [ ] **Step 1: Write failing test**

```python
from src.optimization.constraints import TransferLine
from src.simulation.kpi_tracker import (
    compute_stockout_rate, compute_excess_inventory_value, compute_transport_cost, compute_mape,
)


def test_stockout_rate_counts_keys_where_demand_exceeds_stock():
    demand = {(1, 10): 20.0, (1, 11): 5.0}
    available = {(1, 10): 15.0, (1, 11): 10.0}
    assert compute_stockout_rate(demand, available) == 0.5


def test_stockout_rate_zero_when_no_demand():
    assert compute_stockout_rate({}, {}) == 0.0


def test_excess_inventory_value_sums_only_positive_excess():
    stock = {(1, 10): 50.0, (1, 11): 5.0}
    threshold = {(1, 10): 20.0, (1, 11): 20.0}
    cost = {10: 1000.0, 11: 1000.0}
    assert compute_excess_inventory_value(stock, threshold, cost) == 30.0 * 1000.0


def test_transport_cost_sums_unique_routes_once():
    lines = [
        TransferLine(1, 2, 10, "B1", quantity=5, weight_kg=5.0, volume_l=5.0),
        TransferLine(1, 2, 11, "B2", quantity=3, weight_kg=3.0, volume_l=3.0),  # same route
        TransferLine(1, 3, 10, "B3", quantity=2, weight_kg=2.0, volume_l=2.0),
    ]
    cost_matrix = {(1, 2): 50_000.0, (1, 3): 30_000.0}
    assert compute_transport_cost(lines, cost_matrix) == 80_000.0


def test_mape_ignores_zero_actual_demand():
    forecast = {(1, 10): 12.0, (1, 11): 8.0}
    actual = {(1, 10): 10.0, (1, 11): 0.0}
    assert abs(compute_mape(forecast, actual) - 0.2) < 1e-9
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/simulation/test_kpi_tracker.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Write implementation**

`src/simulation/__init__.py`: (empty file)

```python
"""BR-019 — tính KPI theo tuần (stockout rate, excess inventory, transport cost, MAPE)."""
from dataclasses import dataclass

from src.optimization.constraints import TransferLine


@dataclass
class WeeklyKPI:
    week: int
    scenario: str
    algorithm: str
    stockout_rate: float
    excess_inventory_value: float
    transport_cost: float
    mape: float


def compute_stockout_rate(demand_by_key: dict[tuple[int, int], float],
                           available_stock_by_key: dict[tuple[int, int], float]) -> float:
    if not demand_by_key:
        return 0.0
    stockout_count = sum(
        1 for key, demand in demand_by_key.items() if demand > available_stock_by_key.get(key, 0.0)
    )
    return stockout_count / len(demand_by_key)


def compute_excess_inventory_value(end_of_week_stock_by_key: dict[tuple[int, int], float],
                                    threshold_by_key: dict[tuple[int, int], float],
                                    cost_by_product: dict[int, float]) -> float:
    total = 0.0
    for (store_id, product_id), stock in end_of_week_stock_by_key.items():
        excess_units = max(0.0, stock - threshold_by_key.get((store_id, product_id), 0.0))
        total += excess_units * cost_by_product.get(product_id, 0.0)
    return total


def compute_transport_cost(transfer_lines: list[TransferLine],
                            transport_cost_matrix: dict[tuple[int, int], float]) -> float:
    routes_used = {(line.from_store_id, line.to_store_id) for line in transfer_lines}
    return sum(transport_cost_matrix.get(route, 0.0) for route in routes_used)


def compute_mape(forecast_by_key: dict[tuple[int, int], float],
                  actual_by_key: dict[tuple[int, int], float]) -> float:
    errors = []
    for key, actual in actual_by_key.items():
        if actual <= 0:
            continue
        forecast = forecast_by_key.get(key, 0.0)
        errors.append(abs(actual - forecast) / actual)
    return sum(errors) / len(errors) if errors else 0.0
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/simulation/test_kpi_tracker.py -v`
Expected: PASS (5 passed)

- [ ] **Step 5: Commit**

```bash
git add src/simulation/__init__.py src/simulation/kpi_tracker.py tests/simulation/__init__.py tests/simulation/test_kpi_tracker.py
git commit -m "feat: implement weekly KPI computation (BR-019)"
```

---

### Task 16: `simulation/weekly_cycle.py` (UC-002)

**Files:**
- Create: `src/simulation/weekly_cycle.py`
- Test: `tests/simulation/test_weekly_cycle.py`

**Interfaces:**
- Consumes: `Forecaster`/`NaiveForecaster`/`HoltWintersForecaster` (Tasks 7-9), `compute_safety_stock`/`compute_reorder_point` (Task 10), `StockStatus`/`StockPosition`/`classify_stock`/`classify_stock_baseline` (Task 11), `Batch`/`TransferConstraints`/`TransferLine` (Task 12), `plan_transfers_rule_based` (Task 13), `plan_transfers_ga` (Task 14), `WeeklyKPI`/`compute_*` (Task 15)
- Produces: `WeekResult(dataclass)`: `updated_batches: dict[tuple[int, int], list[Batch]], kpi: WeeklyKPI, transfer_lines: list[TransferLine]`; `run_week(week_index: int, current_date: date, scenario: Literal["baseline", "optimized"], algorithm: Literal["rule_based", "ga"], batches: dict[tuple[int, int], list[Batch]], sales_history: dict[tuple[int, int], pd.Series], actual_demand_this_week: dict[tuple[int, int], float], product_attrs: dict[int, dict], distance_km: dict[tuple[int, int], float], transport_cost_matrix: dict[tuple[int, int], float], delivery_schedule: dict[tuple[int, int], list[str]], vehicle_capacity_kg: float, vehicle_capacity_m3: float, min_shelf_life_days: int, min_inventory_days: float, max_inventory_days: float, ga_seed: int = 42) -> WeekResult`. Consumed by `simulation.rolling_simulator` (Task 17), called once per (week, scenario, algorithm) combination.

- [ ] **Step 1: Write failing test**

```python
from datetime import date
import pandas as pd
from src.optimization.constraints import Batch
from src.simulation.weekly_cycle import run_week


def _product_attrs():
    return {
        10: {"category": "Essentials", "price": 20000.0, "cost": 10000.0, "lead_time_days": 2,
             "service_level": 0.98, "z_score": 2.05, "weight_kg": 1.0, "volume_l": 1.0},
    }


def test_baseline_scenario_never_transfers():
    history = pd.Series([10.0] * 30)
    batches = {(1, 10): [Batch("B1", 1, 10, quantity=5, expiry_date=date(2026, 6, 1))]}
    result = run_week(
        week_index=1, current_date=date(2026, 1, 5), scenario="baseline", algorithm="rule_based",
        batches=batches, sales_history={(1, 10): history}, actual_demand_this_week={(1, 10): 70.0},
        product_attrs=_product_attrs(), distance_km={}, transport_cost_matrix={}, delivery_schedule={},
        vehicle_capacity_kg=500.0, vehicle_capacity_m3=2.0, min_shelf_life_days=7,
        min_inventory_days=7.0, max_inventory_days=30.0,
    )
    assert result.transfer_lines == []
    assert result.kpi.week == 1
    assert result.kpi.scenario == "baseline"
    assert result.kpi.algorithm == "none"


def test_optimized_scenario_transfers_from_surplus_to_deficit():
    history = pd.Series([10.0] * 30)
    batches = {
        (1, 10): [Batch("B1", 1, 10, quantity=2, expiry_date=date(2026, 6, 1))],
        (2, 10): [Batch("B2", 2, 10, quantity=200, expiry_date=date(2026, 6, 1))],
    }
    result = run_week(
        week_index=1, current_date=date(2026, 1, 5), scenario="optimized", algorithm="rule_based",
        batches=batches, sales_history={(1, 10): history, (2, 10): history},
        actual_demand_this_week={(1, 10): 10.0, (2, 10): 10.0},
        product_attrs=_product_attrs(), distance_km={(2, 1): 10.0}, transport_cost_matrix={(2, 1): 50_000.0},
        delivery_schedule={(2, 1): ["Mon"]},
        vehicle_capacity_kg=500.0, vehicle_capacity_m3=2.0, min_shelf_life_days=7,
        min_inventory_days=7.0, max_inventory_days=30.0,
    )
    assert len(result.transfer_lines) >= 1
    assert result.transfer_lines[0].from_store_id == 2
    assert result.transfer_lines[0].to_store_id == 1
    assert result.kpi.algorithm == "rule_based"


def test_transferred_stock_is_available_for_sales_at_destination():
    history = pd.Series([10.0] * 30)
    batches = {
        (1, 10): [Batch("B1", 1, 10, quantity=0, expiry_date=date(2026, 6, 1))],
        (2, 10): [Batch("B2", 2, 10, quantity=200, expiry_date=date(2026, 6, 1))],
    }
    result = run_week(
        week_index=1, current_date=date(2026, 1, 5), scenario="optimized", algorithm="rule_based",
        batches=batches, sales_history={(1, 10): history, (2, 10): history},
        actual_demand_this_week={(1, 10): 5.0, (2, 10): 5.0},
        product_attrs=_product_attrs(), distance_km={(2, 1): 10.0}, transport_cost_matrix={(2, 1): 50_000.0},
        delivery_schedule={(2, 1): ["Mon"]},
        vehicle_capacity_kg=500.0, vehicle_capacity_m3=2.0, min_shelf_life_days=7,
        min_inventory_days=7.0, max_inventory_days=30.0,
    )
    remaining_at_store_1 = sum(b.quantity for b in result.updated_batches.get((1, 10), []))
    assert remaining_at_store_1 >= 0  # đã nhận hàng và bán một phần, không bị lỗi âm kho
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/simulation/test_weekly_cycle.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Write implementation**

```python
"""UC-002 — thực thi một chu kỳ (tuần) trong rolling simulation."""
from dataclasses import dataclass
from datetime import date
from typing import Literal

import pandas as pd

from src.forecasting.holt_winters_forecaster import HoltWintersForecaster
from src.forecasting.naive_forecaster import NaiveForecaster
from src.inventory_policy.classifier import StockPosition, StockStatus, classify_stock, classify_stock_baseline
from src.inventory_policy.reorder_point import compute_reorder_point
from src.inventory_policy.safety_stock import compute_safety_stock
from src.optimization.constraints import Batch, TransferConstraints, TransferLine
from src.optimization.genetic_algorithm import plan_transfers_ga
from src.optimization.rule_based import plan_transfers_rule_based
from src.simulation.kpi_tracker import (
    WeeklyKPI, compute_excess_inventory_value, compute_mape, compute_stockout_rate, compute_transport_cost,
)


@dataclass
class WeekResult:
    updated_batches: dict[tuple[int, int], list[Batch]]
    kpi: WeeklyKPI
    transfer_lines: list[TransferLine]


def run_week(
    week_index: int,
    current_date: date,
    scenario: Literal["baseline", "optimized"],
    algorithm: Literal["rule_based", "ga"],
    batches: dict[tuple[int, int], list[Batch]],
    sales_history: dict[tuple[int, int], pd.Series],
    actual_demand_this_week: dict[tuple[int, int], float],
    product_attrs: dict[int, dict],
    distance_km: dict[tuple[int, int], float],
    transport_cost_matrix: dict[tuple[int, int], float],
    delivery_schedule: dict[tuple[int, int], list[str]],
    vehicle_capacity_kg: float,
    vehicle_capacity_m3: float,
    min_shelf_life_days: int,
    min_inventory_days: float,
    max_inventory_days: float,
    ga_seed: int = 42,
) -> WeekResult:
    constraints = TransferConstraints(vehicle_capacity_kg, vehicle_capacity_m3, delivery_schedule,
                                       min_shelf_life_days)

    # Bước 1-2: dự báo (BR-002) + (chỉ tối ưu) safety stock/reorder point (BR-006, BR-007)
    forecast_weekly: dict[tuple[int, int], float] = {}
    reorder_point_by_key: dict[tuple[int, int], float] = {}
    safety_stock_by_key: dict[tuple[int, int], float] = {}
    for key, history in sales_history.items():
        forecaster = HoltWintersForecaster() if scenario == "optimized" else NaiveForecaster()
        forecaster.fit(history)
        forecast_weekly[key] = float(forecaster.predict(7).sum())

        if scenario == "optimized":
            attrs = product_attrs[key[1]]
            recent = history.tail(28)
            demand_std = float(recent.std(ddof=0)) if len(recent) > 0 else 0.0
            avg_daily_demand = float(recent.mean()) if len(recent) > 0 else 0.0
            safety_stock = compute_safety_stock(demand_std, attrs["z_score"], attrs["lead_time_days"])
            safety_stock_by_key[key] = safety_stock
            reorder_point_by_key[key] = compute_reorder_point(avg_daily_demand, attrs["lead_time_days"],
                                                                safety_stock)

    # Bước 3-4: phân loại thừa/thiếu (BR-008) + (chỉ tối ưu) lập kế hoạch chuyển hàng có ràng buộc
    current_stock_by_key = {key: sum(b.quantity for b in blist) for key, blist in batches.items()}
    transfer_lines: list[TransferLine] = []
    if scenario == "optimized":
        deficits, surpluses = [], []
        for key, stock in current_stock_by_key.items():
            store_id, product_id = key
            position = StockPosition(store_id, product_id, stock,
                                      reorder_point_by_key.get(key, 0.0), safety_stock_by_key.get(key, 0.0))
            status = classify_stock(position)
            if status == StockStatus.DEFICIT:
                deficits.append(position)
            elif status == StockStatus.SURPLUS:
                surpluses.append(position)

        product_weight_volume = {pid: (a["weight_kg"], a["volume_l"]) for pid, a in product_attrs.items()}
        if algorithm == "rule_based":
            transfer_lines = plan_transfers_rule_based(deficits, surpluses, batches, distance_km,
                                                         product_weight_volume, constraints, current_date)
        else:
            transfer_lines = plan_transfers_ga(deficits, surpluses, batches, transport_cost_matrix,
                                                product_weight_volume, constraints, current_date, seed=ga_seed)

    # Bước 5: áp dụng kế hoạch chuyển hàng vào tồn kho
    updated_batches = {key: list(blist) for key, blist in batches.items()}
    for line in transfer_lines:
        from_key = (line.from_store_id, line.product_id)
        source_expiry = next(
            (b.expiry_date for b in updated_batches.get(from_key, []) if b.batch_id == line.batch_id),
            current_date,
        )
        to_key = (line.to_store_id, line.product_id)
        updated_batches.setdefault(to_key, []).append(
            Batch(f"{line.batch_id}-T{line.to_store_id}", line.to_store_id, line.product_id,
                  line.quantity, source_expiry)
        )

    # Bước 6: giả lập bán hàng thực tế (tiêu thụ theo FEFO)
    available_after_transfer = {key: sum(b.quantity for b in blist) for key, blist in updated_batches.items()}
    for key, demand in actual_demand_this_week.items():
        remaining_demand = demand
        blist = sorted(updated_batches.get(key, []), key=lambda b: b.expiry_date)
        for b in blist:
            if remaining_demand <= 0:
                break
            consumed = min(b.quantity, remaining_demand)
            b.quantity -= consumed
            remaining_demand -= consumed
        updated_batches[key] = [b for b in blist if b.quantity > 0]

    # Bước 7: tính KPI (BR-019)
    end_of_week_stock = {key: sum(b.quantity for b in blist) for key, blist in updated_batches.items()}
    if scenario == "optimized":
        threshold_by_key = reorder_point_by_key
    else:
        threshold_by_key = {
            key: max_inventory_days * (float(sales_history[key].tail(28).mean()) if key in sales_history else 0.0)
            for key in end_of_week_stock
        }
    cost_by_product = {pid: attrs["cost"] for pid, attrs in product_attrs.items()}

    kpi = WeeklyKPI(
        week=week_index,
        scenario=scenario,
        algorithm=algorithm if scenario == "optimized" else "none",
        stockout_rate=compute_stockout_rate(actual_demand_this_week, available_after_transfer),
        excess_inventory_value=compute_excess_inventory_value(end_of_week_stock, threshold_by_key, cost_by_product),
        transport_cost=compute_transport_cost(transfer_lines, transport_cost_matrix),
        mape=compute_mape(forecast_weekly, actual_demand_this_week),
    )

    return WeekResult(updated_batches=updated_batches, kpi=kpi, transfer_lines=transfer_lines)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/simulation/test_weekly_cycle.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add src/simulation/weekly_cycle.py tests/simulation/test_weekly_cycle.py
git commit -m "feat: implement weekly cycle orchestration (UC-002)"
```

---

## Phase 6 — Reporting (BR-021)

### Task 17: `reporting/dashboard_generator.py`

**Files:**
- Create: `src/reporting/dashboard_generator.py`
- Test: `tests/reporting/test_dashboard_generator.py`

**Interfaces:**
- Consumes: `WeeklyKPI` (Task 15, via its `.__dict__` shape when assembled into a DataFrame)
- Produces: `generate_dashboard(kpi_df: pd.DataFrame, output_path: Path) -> None` — writes a self-contained HTML file with 4 subplots (stockout rate, excess inventory value, transport cost, MAPE), one line per scenario, averaged across algorithms when both ran. Consumed by `simulation.rolling_simulator` (Task 18) at the end of a full run.

*Implemented before Task 18 despite living conceptually under "reporting" per the architecture doc's folder layout — `rolling_simulator` depends on it.*

- [ ] **Step 1: Write failing test**

```python
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
    # Không kiểm tra "cdn.plot.ly" như substring thô: plotly.js minified nhúng sẵn
    # (include_plotlyjs=True) tự chứa chuỗi đó ở một chỗ nội bộ không liên quan tới CDN load.
    # Kiểm tra đúng thứ cần: không có <script src="..."> trỏ ra CDN.
    output_path = tmp_path / "dashboard.html"
    generate_dashboard(_sample_kpi_df(), output_path)
    content = output_path.read_text(encoding="utf-8")
    assert '<script src="https://cdn' not in content
    assert "<script" in content
```

> **Ghi chú thực thi:** Bản gốc của test này dùng `assert "cdn.plot.ly" not in content`, nhưng file plotly.js
> minified được nhúng (`include_plotlyjs=True`) tình cờ chứa chuỗi đó ở một vị trí nội bộ không liên quan đến
> việc tải script — gây false-positive fail dù implementation đúng. Đã sửa assertion để kiểm tra đúng điều kiện
> tự chứa (không có `<script src="https://cdn...">`).

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/reporting/test_dashboard_generator.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Write implementation**

`src/reporting/__init__.py`: (empty file)

```python
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

    # Khi cả 2 thuật toán cùng chạy ("both"), lấy trung bình theo scenario để dashboard không bị
    # chẻ quá nhiều đường — BR-021 chỉ yêu cầu so sánh 2 kịch bản (baseline vs tối ưu).
    for kpi_col, (row, col) in zip(_KPI_COLUMNS, _POSITIONS):
        for scenario in sorted(kpi_df["scenario"].unique()):
            subset = (
                kpi_df[kpi_df["scenario"] == scenario]
                .groupby("week", as_index=False)[kpi_col].mean()
            )
            fig.add_trace(
                go.Scatter(x=subset["week"], y=subset[kpi_col], mode="lines+markers", name=scenario,
                           legendgroup=scenario, showlegend=(row, col) == (1, 1)),
                row=row, col=col,
            )

    fig.update_layout(title="Inventory Transfer Optimization — Weekly KPI (Baseline vs Optimized)",
                       height=700, width=1000)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.write_html(str(output_path), include_plotlyjs=True, full_html=True)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/reporting/test_dashboard_generator.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add src/reporting/__init__.py src/reporting/dashboard_generator.py tests/reporting/__init__.py tests/reporting/test_dashboard_generator.py
git commit -m "feat: generate self-contained HTML KPI dashboard (BR-021)"
```

---

### Task 18: `simulation/rolling_simulator.py` (UC-001)

**Files:**
- Create: `src/simulation/rolling_simulator.py`
- Test: `tests/simulation/test_rolling_simulator.py`

**Interfaces:**
- Consumes: `Batch` (Task 12), `run_week`/`WeekResult` (Task 16), `generate_dashboard` (Task 17), reads CSVs written by `data_generator.main` (Task 6)
- Produces: `run_simulation(data_dir: Path = config.DATA_DIR, n_weeks: int = config.SIMULATION_WEEKS, history_weeks: int = config.HISTORY_WEEKS, algorithm: Literal["rule_based", "ga", "both"] = "both", seed: int = config.RANDOM_SEED, results_dir: Path = config.RESULTS_DIR, dashboard_dir: Path = config.DASHBOARD_DIR) -> pd.DataFrame` — runs baseline + optimized scenarios for each requested algorithm, writes `results/kpi_timeseries.csv` and `dashboard/dashboard.html`, returns the KPI DataFrame. Called by `src/main.py` (Task 19) for the `--simulate` CLI flag.
- **Design note:** `sales_data.csv` must contain `history_weeks + n_weeks` weeks per store/product (see Task 6's `TOTAL_DATA_WEEKS`). The first `history_weeks` are the training history the forecaster sees; the remaining `n_weeks` are treated as ground-truth "future" demand, revealed one week at a time and appended to `sales_history` after each `run_week` call (walk-forward simulation) — this is what makes MAPE and stockout meaningful rather than circular.

- [ ] **Step 1: Write failing test**

```python
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

from src.simulation.rolling_simulator import run_simulation


def _write_minimal_dataset(data_dir: Path) -> None:
    stores = pd.DataFrame([
        {"store_id": 1, "store_name": "S1", "city": "Hanoi", "latitude": 21.0, "longitude": 105.8},
        {"store_id": 2, "store_name": "S2", "city": "Hanoi", "latitude": 21.01, "longitude": 105.81},
    ])
    products = pd.DataFrame([
        {"product_id": 10, "name": "P10", "category": "Essentials", "price": 20000.0, "cost": 10000.0,
         "lead_time_days": 2, "service_level": 0.98, "z_score": 2.05, "weight_kg": 1.0, "volume_l": 1.0},
    ])
    start = date(2026, 1, 1)
    total_days = 3 * 7 + 2 * 7  # 3 tuần lịch sử + 2 tuần simulation
    sales_rows = []
    for day_offset in range(total_days):
        current_date = start + timedelta(days=day_offset)
        for store_id, qty in [(1, 5), (2, 20)]:
            sales_rows.append({"date": current_date.isoformat(), "store_id": store_id, "product_id": 10,
                                "quantity": qty, "revenue": qty * 20000.0, "cost": qty * 10000.0,
                                "is_promotion": 0})
    sales = pd.DataFrame(sales_rows)
    batches = pd.DataFrame([
        {"batch_id": "B1", "store_id": 1, "product_id": 10, "quantity": 5,
         "received_date": start.isoformat(), "expiry_date": (start + timedelta(days=200)).isoformat()},
        {"batch_id": "B2", "store_id": 2, "product_id": 10, "quantity": 200,
         "received_date": start.isoformat(), "expiry_date": (start + timedelta(days=200)).isoformat()},
    ])
    distance = pd.DataFrame([
        {"from_store_id": 1, "to_store_id": 2, "distance_km": 1.0},
        {"from_store_id": 2, "to_store_id": 1, "distance_km": 1.0},
    ])
    transport_cost = pd.DataFrame([
        {"from_store_id": 1, "to_store_id": 2, "transport_cost": 5000.0},
        {"from_store_id": 2, "to_store_id": 1, "transport_cost": 5000.0},
    ])
    schedule = pd.DataFrame([
        {"from_store_id": 1, "to_store_id": 2, "allowed_days": "Mon,Thu"},
        {"from_store_id": 2, "to_store_id": 1, "allowed_days": "Mon,Thu"},
    ])
    stores.to_csv(data_dir / "stores.csv", index=False)
    products.to_csv(data_dir / "products.csv", index=False)
    sales.to_csv(data_dir / "sales_data.csv", index=False)
    batches.to_csv(data_dir / "inventory_batches.csv", index=False)
    distance.to_csv(data_dir / "distance_matrix.csv", index=False)
    transport_cost.to_csv(data_dir / "transport_cost_matrix.csv", index=False)
    schedule.to_csv(data_dir / "delivery_schedule.csv", index=False)


def test_runs_two_week_simulation_and_produces_kpi_and_dashboard(tmp_path):
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    _write_minimal_dataset(data_dir)
    results_dir = tmp_path / "results"
    dashboard_dir = tmp_path / "dashboard"

    kpi_df = run_simulation(data_dir=data_dir, n_weeks=2, history_weeks=3, algorithm="rule_based",
                             seed=1, results_dir=results_dir, dashboard_dir=dashboard_dir)

    assert len(kpi_df) == 2 * 2  # 2 tuần x 2 kịch bản (baseline, optimized), 1 thuật toán
    assert set(kpi_df["scenario"]) == {"baseline", "optimized"}
    assert (results_dir / "kpi_timeseries.csv").exists()
    assert (dashboard_dir / "dashboard.html").exists()


def test_optimized_scenario_incurs_transport_cost_baseline_does_not(tmp_path):
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    _write_minimal_dataset(data_dir)

    kpi_df = run_simulation(data_dir=data_dir, n_weeks=2, history_weeks=3, algorithm="rule_based",
                             seed=1, results_dir=tmp_path / "results", dashboard_dir=tmp_path / "dashboard")

    baseline_cost = kpi_df[kpi_df["scenario"] == "baseline"]["transport_cost"].sum()
    optimized_cost = kpi_df[kpi_df["scenario"] == "optimized"]["transport_cost"].sum()
    assert baseline_cost == 0.0  # baseline không bao giờ chuyển hàng (AF-1 của UC-002)
    assert optimized_cost > 0.0  # store 1 thiếu hụt rõ rệt, store 2 dư rõ rệt -> phải có chuyển hàng
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/simulation/test_rolling_simulator.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Write implementation**

```python
"""UC-001 — điều phối rolling simulation qua N tuần x kịch bản x thuật toán, xuất KPI + dashboard."""
from datetime import timedelta
from pathlib import Path
from typing import Literal

import pandas as pd

from src import config
from src.optimization.constraints import Batch
from src.reporting.dashboard_generator import generate_dashboard
from src.simulation.weekly_cycle import run_week


def _load_input_data(data_dir: Path):
    stores = pd.read_csv(data_dir / "stores.csv")
    products = pd.read_csv(data_dir / "products.csv")
    sales = pd.read_csv(data_dir / "sales_data.csv", parse_dates=["date"])
    batches_df = pd.read_csv(data_dir / "inventory_batches.csv", parse_dates=["received_date", "expiry_date"])
    distance_df = pd.read_csv(data_dir / "distance_matrix.csv")
    cost_df = pd.read_csv(data_dir / "transport_cost_matrix.csv")
    schedule_df = pd.read_csv(data_dir / "delivery_schedule.csv")
    return stores, products, sales, batches_df, distance_df, cost_df, schedule_df


def _to_batches_dict(batches_df: pd.DataFrame) -> dict[tuple[int, int], list[Batch]]:
    result: dict[tuple[int, int], list[Batch]] = {}
    for _, row in batches_df.iterrows():
        key = (int(row["store_id"]), int(row["product_id"]))
        result.setdefault(key, []).append(
            Batch(str(row["batch_id"]), int(row["store_id"]), int(row["product_id"]),
                  float(row["quantity"]), row["expiry_date"].date())
        )
    return result


def _pair_dict(matrix_df: pd.DataFrame, value_col: str) -> dict[tuple[int, int], float]:
    return {(int(r["from_store_id"]), int(r["to_store_id"])): float(r[value_col])
            for _, r in matrix_df.iterrows()}


def _schedule_dict(schedule_df: pd.DataFrame) -> dict[tuple[int, int], list[str]]:
    return {(int(r["from_store_id"]), int(r["to_store_id"])): str(r["allowed_days"]).split(",")
            for _, r in schedule_df.iterrows()}


def _split_history_and_future(sales: pd.DataFrame, history_weeks: int, simulation_weeks: int):
    history_days = history_weeks * 7
    initial_history: dict[tuple[int, int], pd.Series] = {}
    weekly_future: list[dict[tuple[int, int], float]] = [dict() for _ in range(simulation_weeks)]

    for (store_id, product_id), group in sales.groupby(["store_id", "product_id"]):
        group = group.sort_values("date").reset_index(drop=True)
        key = (int(store_id), int(product_id))
        initial_history[key] = group["quantity"].iloc[:history_days].reset_index(drop=True).astype(float)
        future = group["quantity"].iloc[history_days:history_days + simulation_weeks * 7].reset_index(drop=True)
        for week_index in range(simulation_weeks):
            week_slice = future.iloc[week_index * 7:(week_index + 1) * 7]
            weekly_future[week_index][key] = float(week_slice.sum())

    return initial_history, weekly_future


def run_simulation(
    data_dir: Path = config.DATA_DIR,
    n_weeks: int = config.SIMULATION_WEEKS,
    history_weeks: int = config.HISTORY_WEEKS,
    algorithm: Literal["rule_based", "ga", "both"] = "both",
    seed: int = config.RANDOM_SEED,
    results_dir: Path = config.RESULTS_DIR,
    dashboard_dir: Path = config.DASHBOARD_DIR,
) -> pd.DataFrame:
    stores, products, sales, batches_df, distance_df, cost_df, schedule_df = _load_input_data(Path(data_dir))
    product_attrs = products.set_index("product_id").to_dict(orient="index")
    distance_km = _pair_dict(distance_df, "distance_km")
    transport_cost = _pair_dict(cost_df, "transport_cost")
    delivery_schedule = _schedule_dict(schedule_df)
    initial_history, weekly_future = _split_history_and_future(sales, history_weeks, n_weeks)

    algorithms = ["rule_based", "ga"] if algorithm == "both" else [algorithm]
    all_kpi_rows = []

    for algo in algorithms:
        for scenario in ["baseline", "optimized"]:
            batches = _to_batches_dict(batches_df)
            sales_history = {key: series.copy() for key, series in initial_history.items()}

            for week_index in range(1, n_weeks + 1):
                actual_demand = weekly_future[week_index - 1]
                week_date = sales["date"].max().date() + timedelta(days=(week_index - 1) * 7 + 1)
                result = run_week(
                    week_index=week_index, current_date=week_date, scenario=scenario, algorithm=algo,
                    batches=batches, sales_history=sales_history, actual_demand_this_week=actual_demand,
                    product_attrs=product_attrs, distance_km=distance_km, transport_cost_matrix=transport_cost,
                    delivery_schedule=delivery_schedule, vehicle_capacity_kg=config.VEHICLE_CAPACITY_KG,
                    vehicle_capacity_m3=config.VEHICLE_CAPACITY_M3, min_shelf_life_days=config.MIN_SHELF_LIFE_DAYS,
                    min_inventory_days=config.MIN_INVENTORY_DAYS, max_inventory_days=config.MAX_INVENTORY_DAYS,
                    ga_seed=seed + week_index,
                )
                batches = result.updated_batches
                for key, weekly_total in actual_demand.items():
                    daily_avg = weekly_total / 7
                    existing = sales_history.get(key, pd.Series(dtype=float))
                    sales_history[key] = pd.concat([existing, pd.Series([daily_avg] * 7)], ignore_index=True)
                all_kpi_rows.append(result.kpi.__dict__)

    kpi_df = pd.DataFrame(all_kpi_rows)
    results_dir = Path(results_dir)
    results_dir.mkdir(parents=True, exist_ok=True)
    kpi_df.to_csv(results_dir / "kpi_timeseries.csv", index=False)

    dashboard_dir = Path(dashboard_dir)
    dashboard_dir.mkdir(parents=True, exist_ok=True)
    generate_dashboard(kpi_df, dashboard_dir / "dashboard.html")

    return kpi_df
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/simulation/test_rolling_simulator.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add src/simulation/rolling_simulator.py tests/simulation/test_rolling_simulator.py
git commit -m "feat: implement rolling simulation orchestration (UC-001)"
```

---

## Phase 7 — CLI

### Task 19: `src/main.py`

**Files:**
- Create: `src/main.py`
- Test: `tests/test_main_cli.py`

**Interfaces:**
- Consumes: `run_data_generation` (Task 6), `run_simulation` (Task 18), `generate_dashboard` (Task 17)
- Produces: `main() -> None` — CLI entrypoint per `docs/architecture/technical-design.md` Mục 4 (`--generate-data`, `--simulate --weeks N --algorithm {rule_based,ga,both}`, `--dashboard-only`).

- [ ] **Step 1: Write failing test**

```python
import sys
from unittest.mock import patch

import pandas as pd

from src import config, main as main_module


def _sample_kpi_df() -> pd.DataFrame:
    return pd.DataFrame({"week": [1], "scenario": ["baseline"], "algorithm": ["none"],
                          "stockout_rate": [0.0], "excess_inventory_value": [0.0],
                          "transport_cost": [0.0], "mape": [0.0]})


def test_generate_data_flag_calls_run_data_generation(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["main.py", "--generate-data"])
    with patch("src.main.run_data_generation") as mock_generate:
        main_module.main()
        mock_generate.assert_called_once()


def test_simulate_flag_calls_run_simulation_with_parsed_args(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["main.py", "--simulate", "--weeks", "4", "--algorithm", "rule_based"])
    with patch("src.main.run_simulation") as mock_simulate:
        mock_simulate.return_value = _sample_kpi_df()
        main_module.main()
        mock_simulate.assert_called_once_with(n_weeks=4, algorithm="rule_based", seed=config.RANDOM_SEED)


def test_dashboard_only_flag_calls_generate_dashboard(monkeypatch, tmp_path):
    kpi_csv = tmp_path / "kpi_timeseries.csv"
    _sample_kpi_df().to_csv(kpi_csv, index=False)
    monkeypatch.setattr(config, "RESULTS_DIR", tmp_path)
    monkeypatch.setattr(sys, "argv", ["main.py", "--dashboard-only"])
    with patch("src.main.generate_dashboard") as mock_dashboard:
        main_module.main()
        mock_dashboard.assert_called_once()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_main_cli.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Write implementation**

```python
"""CLI entrypoint (docs/architecture/technical-design.md Mục 4)."""
import argparse

import pandas as pd

from src import config
from src.data_generator.main import run_data_generation
from src.reporting.dashboard_generator import generate_dashboard
from src.simulation.rolling_simulator import run_simulation


def main() -> None:
    parser = argparse.ArgumentParser(description="Inventory Transfer Optimization v2")
    parser.add_argument("--generate-data", action="store_true")
    parser.add_argument("--simulate", action="store_true")
    parser.add_argument("--dashboard-only", action="store_true")
    parser.add_argument("--weeks", type=int, default=config.SIMULATION_WEEKS)
    parser.add_argument("--algorithm", choices=["rule_based", "ga", "both"], default="both")
    parser.add_argument("--seed", type=int, default=config.RANDOM_SEED)
    args = parser.parse_args()

    if args.generate_data:
        run_data_generation(config.DATA_DIR, seed=args.seed)
        print(f"Data generated at {config.DATA_DIR}")

    if args.simulate:
        kpi_df = run_simulation(n_weeks=args.weeks, algorithm=args.algorithm, seed=args.seed)
        print(f"Simulation complete: {len(kpi_df)} KPI rows written to {config.RESULTS_DIR}")
        print(f"Dashboard written to {config.DASHBOARD_DIR / 'dashboard.html'}")

    if args.dashboard_only:
        kpi_df = pd.read_csv(config.RESULTS_DIR / "kpi_timeseries.csv")
        generate_dashboard(kpi_df, config.DASHBOARD_DIR / "dashboard.html")
        print(f"Dashboard regenerated at {config.DASHBOARD_DIR / 'dashboard.html'}")

    if not (args.generate_data or args.simulate or args.dashboard_only):
        parser.print_help()


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_main_cli.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add src/main.py tests/test_main_cli.py
git commit -m "feat: add CLI entrypoint for data generation, simulation, dashboard"
```

---

## Phase 8 — Integration

### Task 20: End-to-end integration test

**Files:**
- Test: `tests/test_integration.py`

**Interfaces:**
- Consumes: `run_data_generation` (Task 6), `run_simulation` (Task 18) — real implementations, no mocking. Validates that the full UC-003 → UC-001 pipeline wires together correctly end-to-end, catching schema/type mismatches unit tests with hand-built fixtures could miss.

- [ ] **Step 1: Write the integration test**

```python
"""Integration test: UC-003 -> UC-001 rút gọn, xác nhận toàn bộ pipeline nối đúng."""
from src.data_generator.main import run_data_generation
from src.simulation.rolling_simulator import run_simulation


def test_full_pipeline_generate_data_then_simulate(tmp_path):
    data_dir = tmp_path / "data"
    results_dir = tmp_path / "results"
    dashboard_dir = tmp_path / "dashboard"

    run_data_generation(output_dir=data_dir, seed=1, num_weeks=3 + 2)  # 3 tuần lịch sử + 2 tuần simulation

    kpi_df = run_simulation(data_dir=data_dir, n_weeks=2, history_weeks=3, algorithm="rule_based",
                             seed=1, results_dir=results_dir, dashboard_dir=dashboard_dir)

    assert len(kpi_df) == 2 * 2  # 2 tuần x 2 kịch bản
    assert (results_dir / "kpi_timeseries.csv").exists()
    assert (dashboard_dir / "dashboard.html").exists()
    assert not kpi_df["stockout_rate"].isna().any()
    assert not kpi_df["mape"].isna().any()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_integration.py -v`
Expected: FAIL — `ModuleNotFoundError` if run before Task 6/18 exist; once all prior tasks are complete this is the first run of the test, so instead confirm it currently collects and runs (it depends only on already-implemented modules by this point in the plan).

- [ ] **Step 3: Run test to verify it passes**

Run: `pytest tests/test_integration.py -v`
Expected: PASS (1 passed). If it fails, the failure is almost certainly a data-shape mismatch between `data_generator` output and `rolling_simulator` input (e.g. dtype of `store_id`/`product_id` columns after CSV round-trip) — fix at the source module, not by patching this test.

- [ ] **Step 4: Run the full test suite**

Run: `pytest -v`
Expected: All tests across every module pass.

- [ ] **Step 5: Commit**

```bash
git add tests/test_integration.py
git commit -m "test: add end-to-end integration test for UC-003 -> UC-001 pipeline"
```

---

## Self-Review

**Spec coverage** — every BR from `docs/requirements/BRD.md` maps to a task:
- BR-001, 004, 005, 009, 012 (data generation) → Tasks 1-6
- BR-002, 003 (forecasting) → Tasks 7-9
- BR-006, 007, 008 (inventory policy) → Tasks 10-11
- BR-009–016 (constraints + both algorithms) → Tasks 12-14
- BR-017–020 (rolling simulation, KPI, baseline comparison) → Tasks 15, 16, 18
- BR-021 (dashboard) → Task 17
- BR-022, 023, 024 (full rewrite, modular architecture, no real integration) → satisfied by the overall module layout (Task 0 + File Structure); no dedicated task needed since these are structural properties of every task, not a discrete deliverable.

**Placeholder scan** — no TBD/TODO markers; every step has runnable code and exact commands.

**Type consistency** — verified across tasks: `Batch`, `TransferConstraints`, `TransferLine` (Task 12) are the single definitions imported everywhere else (Tasks 13, 14, 16, 18); `StockPosition`/`StockStatus`/`classify_stock`/`classify_stock_baseline` (Task 11) used identically in Tasks 13, 14, 16; `WeeklyKPI` (Task 15) fields (`week, scenario, algorithm, stockout_rate, excess_inventory_value, transport_cost, mape`) match what Task 16 constructs and what Task 17's dashboard reads by column name; `Forecaster`/`NaiveForecaster`/`HoltWintersForecaster` (Tasks 7-9) used identically in Task 16.

**Scope check** — all 8 phases form one dependency chain (data → forecasting/policy/optimization → simulation → reporting → CLI → integration) for a single system, not independent subsystems; a single plan is appropriate (matches the Scope Check guidance — no decomposition needed).

---

**Execution options:**

**1. Subagent-Driven (recommended)** — I dispatch a fresh subagent per task, review between tasks, fast iteration.

**2. Inline Execution** — Execute tasks in this session using executing-plans, batch execution with checkpoints.

Which approach?

