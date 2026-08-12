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
