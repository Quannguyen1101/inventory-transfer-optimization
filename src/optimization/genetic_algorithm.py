"""BR-016 — genetic algorithm cho lập kế hoạch chuyển hàng, tôn trọng ràng buộc dùng chung.

Ràng buộc được xử lý bằng repair khi giải mã gen (không dùng hàm phạt): mọi bộ gen đều cho ra kế hoạch
khả thi — không rút quá lô hàng / quá phần dư của cửa hàng nguồn, không giao quá nhu cầu của cửa hàng
thiếu, không vượt sức chứa xe mỗi tuyến. Hàm mục tiêu = chi phí tuyến vận chuyển + chi phí thiếu hàng
(số đơn vị còn thiếu so với reorder point x chi phí thiếu hàng/đơn vị của sản phẩm).

Quần thể có thể được seed bằng một kế hoạch có sẵn (vd. nghiệm rule-based); nhờ elitism, kết quả không
bao giờ tệ hơn kế hoạch seed theo chính hàm mục tiêu này.
"""
import math
from collections import defaultdict
from dataclasses import dataclass
from datetime import date

import numpy as np

from src.inventory_policy.classifier import StockPosition
from src.optimization.constraints import (
    CAPACITY_EPS, Batch, TransferConstraints, TransferLine, filter_eligible_batches,
)

_DEFAULT_SHORTAGE_COST_PER_UNIT = 100_000.0


@dataclass
class _Candidate:
    from_store_id: int
    to_store_id: int
    product_id: int
    batch_id: str
    max_quantity: float
    weight_per_unit: float
    volume_per_unit: float


@dataclass
class _Limits:
    batch_qty: dict[tuple[int, int, str], float]
    surplus_qty: dict[tuple[int, int], float]
    need: dict[tuple[int, int], int]
    capacity_kg: float
    capacity_l: float


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


def _build_limits(deficits, surpluses, batches_by_store_product, constraints: TransferConstraints) -> _Limits:
    surplus_qty = {(s.store_id, s.product_id): max(0.0, s.current_stock - s.reorder_point) for s in surpluses}
    batch_qty = {(b.store_id, b.product_id, b.batch_id): b.quantity
                 for key in surplus_qty for b in batches_by_store_product.get(key, [])}
    need = {(d.store_id, d.product_id): math.ceil(max(0.0, d.reorder_point - d.current_stock)) for d in deficits}
    return _Limits(batch_qty, surplus_qty, need, constraints.vehicle_capacity_kg, constraints.vehicle_capacity_l)


def _decode(genes: np.ndarray, candidates: list[_Candidate], limits: _Limits) -> list[TransferLine]:
    """Repair: số lượng mỗi gen bị cắt theo phần còn lại của lô, của phần dư nguồn, của nhu cầu đích và
    của sức chứa xe trên tuyến — nên kế hoạch giải mã ra luôn khả thi, số đơn vị luôn nguyên."""
    batch_left = dict(limits.batch_qty)
    surplus_left = dict(limits.surplus_qty)
    need_left = dict(limits.need)
    route_left: dict[tuple[int, int], list[float]] = {}
    lines = []
    for gene, c in zip(genes, candidates):
        if gene < 1:
            continue
        batch_key = (c.from_store_id, c.product_id, c.batch_id)
        surplus_key = (c.from_store_id, c.product_id)
        need_key = (c.to_store_id, c.product_id)
        route = route_left.setdefault((c.from_store_id, c.to_store_id), [limits.capacity_kg, limits.capacity_l])
        quantity = min(gene, batch_left[batch_key], surplus_left[surplus_key], need_left[need_key])
        if c.weight_per_unit > 0:
            quantity = min(quantity, route[0] / c.weight_per_unit)
        if c.volume_per_unit > 0:
            quantity = min(quantity, route[1] / c.volume_per_unit)
        quantity = math.floor(quantity + CAPACITY_EPS)
        if quantity <= 0:
            continue
        batch_left[batch_key] -= quantity
        surplus_left[surplus_key] -= quantity
        need_left[need_key] -= quantity
        route[0] -= quantity * c.weight_per_unit
        route[1] -= quantity * c.volume_per_unit
        lines.append(TransferLine(
            c.from_store_id, c.to_store_id, c.product_id, c.batch_id,
            quantity=quantity, weight_kg=quantity * c.weight_per_unit, volume_l=quantity * c.volume_per_unit,
        ))
    return lines


def _fitness(lines: list[TransferLine], limits: _Limits, transport_cost: dict[tuple[int, int], float],
             shortage_cost_per_unit: dict[int, float]) -> float:
    routes_used = {(l.from_store_id, l.to_store_id) for l in lines}
    cost = sum(transport_cost.get(route, 0.0) for route in routes_used)

    delivered: dict[tuple[int, int], float] = defaultdict(float)
    for line in lines:
        delivered[(line.to_store_id, line.product_id)] += line.quantity
    shortage_cost = sum(
        (need - delivered[key]) * shortage_cost_per_unit.get(key[1], _DEFAULT_SHORTAGE_COST_PER_UNIT)
        for key, need in limits.need.items()
    )
    return cost + shortage_cost


def _encode(plan: list[TransferLine], candidates: list[_Candidate]) -> np.ndarray:
    index = {(c.from_store_id, c.to_store_id, c.product_id, c.batch_id): i for i, c in enumerate(candidates)}
    genes = np.zeros(len(candidates))
    for line in plan:
        genes[index[(line.from_store_id, line.to_store_id, line.product_id, line.batch_id)]] += line.quantity
    return genes


def _apply_to_sources(lines: list[TransferLine], batches_by_store_product: dict[tuple[int, int], list[Batch]],
                      surpluses: list[StockPosition]) -> None:
    """Trừ số lượng đã chuyển khỏi lô nguồn và tồn kho cửa hàng nguồn (cùng hợp đồng với rule_based)."""
    batch_by_key = {(b.store_id, b.product_id, b.batch_id): b
                    for blist in batches_by_store_product.values() for b in blist}
    surplus_by_key = {(s.store_id, s.product_id): s for s in surpluses}
    for line in lines:
        batch_by_key[(line.from_store_id, line.product_id, line.batch_id)].quantity -= line.quantity
        surplus_by_key[(line.from_store_id, line.product_id)].current_stock -= line.quantity


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
    """Gen bị đột biến: một nửa nhận số lượng ngẫu nhiên mới, một nửa về 0 — cho phép bỏ hẳn một tuyến
    (tiết kiệm phí tuyến), điều mà đột biến đồng đều trong [0, max] gần như không bao giờ làm được."""
    mutated = genes.copy()
    mask = rng.random(len(genes)) < mutation_rate
    mutated[mask] = rng.uniform(0, max_quantities[mask])
    mutated[mask & (rng.random(len(genes)) < 0.5)] = 0.0
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
    seed_plan: list[TransferLine] | None = None,
    shortage_cost_per_unit: dict[int, float] | None = None,
) -> list[TransferLine]:
    """Trừ số lượng đã chuyển khỏi Batch.quantity và StockPosition.current_stock của nguồn (giống
    rule_based) — caller phải truyền bản sao riêng cho mỗi tuần. `shortage_cost_per_unit` theo
    product_id (mặc định 100.000đ/đv); `seed_plan` phải được lập trên cùng tồn kho, chưa bị trừ."""
    rng = np.random.default_rng(seed)
    candidates = _build_candidates(deficits, surpluses, batches_by_store_product, product_attrs,
                                    constraints, current_date)
    if not candidates:
        return []
    limits = _build_limits(deficits, surpluses, batches_by_store_product, constraints)
    shortage_cost_per_unit = shortage_cost_per_unit or {}

    max_quantities = np.array([c.max_quantity for c in candidates])
    shape = (population_size, len(candidates))
    population = rng.uniform(0, max_quantities, size=shape) * (rng.random(shape) < 0.5)  # khởi tạo thưa
    if seed_plan:
        population[0] = _encode(seed_plan, candidates)

    def fitness_of(genes: np.ndarray) -> float:
        return _fitness(_decode(genes, candidates, limits), limits, transport_cost, shortage_cost_per_unit)

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

    plan = _decode(best_genes, candidates, limits)
    _apply_to_sources(plan, batches_by_store_product, surpluses)
    return plan
