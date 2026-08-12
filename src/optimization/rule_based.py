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
