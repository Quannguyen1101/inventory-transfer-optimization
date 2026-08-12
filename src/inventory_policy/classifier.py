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
