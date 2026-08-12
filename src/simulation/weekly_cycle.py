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
