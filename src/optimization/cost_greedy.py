"""Greedy có tính chi phí — baseline công bằng để so sánh với GA.

Dùng đúng thông tin GA dùng (phí tuyến, chi phí thiếu hàng/đơn vị) nhưng quyết định từng thiếu hụt một,
theo thứ tự giá trị thiếu hàng giảm dần. Với mỗi thiếu hụt, thử các nguồn theo chi phí biên tăng dần (tuyến
đã mở trong kế hoạch = 0, chưa mở = phí tuyến) và chỉ mở chuyến mới khi số đơn vị bù được x chi phí thiếu
hàng/đơn vị >= phí tuyến. Vì xét riêng lẻ, greedy không thấy lợi ích của việc gộp nhiều thiếu hụt nhỏ lên
cùng một chuyến — phần mà GA có thể làm thêm.
"""
import math
from datetime import date

from src.inventory_policy.classifier import StockPosition
from src.optimization.constraints import (
    CAPACITY_EPS, Batch, TransferConstraints, TransferLine, filter_eligible_batches,
)


def plan_transfers_cost_greedy(
    deficits: list[StockPosition],
    surpluses: list[StockPosition],
    batches_by_store_product: dict[tuple[int, int], list[Batch]],
    transport_cost: dict[tuple[int, int], float],
    product_attrs: dict[int, tuple[float, float]],
    constraints: TransferConstraints,
    current_date: date,
    shortage_cost_per_unit: dict[int, float],
) -> list[TransferLine]:
    """Trừ số lượng đã chuyển khỏi Batch.quantity và StockPosition.current_stock của nguồn (giống
    rule_based) — caller phải truyền bản sao riêng cho mỗi tuần."""
    plan: list[TransferLine] = []
    route_left: dict[tuple[int, int], list[float]] = {}  # tuyến đã mở -> [kg, lít] còn trống

    def need_of(d: StockPosition) -> int:
        return math.ceil(max(0.0, d.reorder_point - d.current_stock))

    for deficit in sorted(deficits, key=lambda d: need_of(d) * shortage_cost_per_unit[d.product_id], reverse=True):
        need = need_of(deficit)
        unit_value = shortage_cost_per_unit[deficit.product_id]
        weight, volume = product_attrs[deficit.product_id]

        def marginal_cost(s: StockPosition) -> float:
            route = (s.store_id, deficit.store_id)
            return 0.0 if route in route_left else transport_cost.get(route, 0.0)

        sources = [s for s in surpluses if s.product_id == deficit.product_id
                   and (s.store_id, deficit.store_id) in constraints.delivery_schedule]
        for surplus in sorted(sources, key=marginal_cost):
            if need <= 0:
                break
            route = (surplus.store_id, deficit.store_id)
            kg_left, l_left = route_left.get(route, (constraints.vehicle_capacity_kg, constraints.vehicle_capacity_l))
            batches = filter_eligible_batches(batches_by_store_product.get((surplus.store_id, deficit.product_id), []),
                                              current_date, constraints.min_shelf_life_days)
            room = min(kg_left / weight if weight > 0 else math.inf, l_left / volume if volume > 0 else math.inf)
            available = min(surplus.current_stock - surplus.reorder_point,
                            sum(math.floor(b.quantity) for b in batches), room)
            quantity = min(need, math.floor(available + CAPACITY_EPS))
            if quantity <= 0 or quantity * unit_value < marginal_cost(surplus):
                continue

            remaining = quantity
            for batch in batches:  # FEFO
                take = min(remaining, math.floor(batch.quantity))
                if take <= 0:
                    continue
                plan.append(TransferLine(surplus.store_id, deficit.store_id, deficit.product_id, batch.batch_id,
                                         quantity=take, weight_kg=take * weight, volume_l=take * volume))
                batch.quantity -= take
                remaining -= take
                if remaining <= 0:
                    break
            surplus.current_stock -= quantity
            route_left[route] = [kg_left - quantity * weight, l_left - quantity * volume]
            need -= quantity
    return plan
