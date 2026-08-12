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
