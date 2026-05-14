"""
LARGE-SCALE BENCHMARK
=====================

Stress-tests the two commercially relevant exact-search demos:

1. Prime hypergraph timetabling
2. Prime inventory allocation / order promising

The benchmark is intentionally honest:
- fixed search budgets via node limits
- repeated randomized trials
- success rate, node count, and runtime summaries

This does not prove the framework scales generally. It measures how far the
current CRT-preserving search machinery goes before combinatorics dominate.
"""

from __future__ import annotations

from dataclasses import dataclass
from statistics import median
import random
import time
from typing import Dict, List, Optional, Tuple

from prime_hypergraph_timetabling import Course, Placement, PrimeHypergraphTimetabler
from prime_inventory_allocation import FulfillmentPlan, Order, PrimeInventoryAllocator


@dataclass
class TrialResult:
    solved: bool
    nodes: int
    runtime_ms: float
    objective: Optional[int] = None


def summarize(results: List[TrialResult]) -> str:
    solved = [r for r in results if r.solved]
    success_rate = 100.0 * len(solved) / len(results) if results else 0.0
    median_nodes = median(r.nodes for r in results) if results else 0
    median_runtime = median(r.runtime_ms for r in results) if results else 0.0
    solved_runtime = median(r.runtime_ms for r in solved) if solved else 0.0
    solved_nodes = median(r.nodes for r in solved) if solved else 0
    solved_objectives = [r.objective for r in solved if r.objective is not None]
    solved_obj = median(solved_objectives) if solved_objectives else None

    parts = [
        f"success={len(solved)}/{len(results)} ({success_rate:.1f}%)",
        f"median_nodes={median_nodes}",
        f"median_runtime_ms={median_runtime:.1f}",
    ]
    if solved:
        parts.append(f"solved_median_nodes={solved_nodes}")
        parts.append(f"solved_median_runtime_ms={solved_runtime:.1f}")
    if solved_obj is not None:
        parts.append(f"solved_median_objective={solved_obj}")
    return " | ".join(parts)


def random_prime_timetable_instance(
    rng: random.Random,
    num_courses: int,
    options_per_course: int,
    num_slots: int,
    num_rooms: int,
    num_instructors: int,
    num_groups: int,
) -> List[Course]:
    slots = [f"S{i}" for i in range(num_slots)]
    rooms = [f"R{i}" for i in range(num_rooms)]
    instructors = [f"I{i}" for i in range(num_instructors)]
    groups = [f"G{i}" for i in range(num_groups)]

    used_slot_room = set()
    used_slot_instructor = set()
    used_slot_group = set()
    courses: List[Course] = []
    for i in range(num_courses):
        instructor = rng.choice(instructors)
        course_groups = tuple(sorted(rng.sample(groups, k=rng.randint(1, min(3, num_groups)))))
        hidden: Optional[Placement] = None
        for _ in range(500):
            candidate = Placement(
                slot=rng.choice(slots),
                room=rng.choice(rooms),
                instructor=instructor,
                groups=course_groups,
            )
            sr = (candidate.slot, candidate.room)
            si = (candidate.slot, candidate.instructor)
            sg = {(candidate.slot, group) for group in candidate.groups}
            if sr in used_slot_room or si in used_slot_instructor or any(x in used_slot_group for x in sg):
                continue
            hidden = candidate
            used_slot_room.add(sr)
            used_slot_instructor.add(si)
            used_slot_group.update(sg)
            break

        if hidden is None:
            raise RuntimeError("failed to plant feasible timetable option")

        course_options = [hidden]
        seen = set()
        seen.add((hidden.slot, hidden.room))

        while len(course_options) < options_per_course:
            placement = Placement(
                slot=rng.choice(slots),
                room=rng.choice(rooms),
                instructor=instructor,
                groups=course_groups,
            )
            key = (placement.slot, placement.room)
            if key in seen:
                continue
            seen.add(key)
            course_options.append(placement)

        courses.append(Course(name=f"C{i:03d}", options=tuple(course_options)))

    return courses


def run_timetable_trials(
    seed: int,
    sizes: List[Tuple[int, int]],
    trials_per_size: int,
    node_limit: int,
) -> List[str]:
    lines = []
    for num_courses, options_per_course in sizes:
        results: List[TrialResult] = []
        for trial in range(trials_per_size):
            rng = random.Random(seed + 1000 * num_courses + trial)
            courses = None
            for resource_bump in range(4):
                try:
                    courses = random_prime_timetable_instance(
                        rng=rng,
                        num_courses=num_courses,
                        options_per_course=options_per_course,
                        num_slots=max(6, num_courses // 3 + resource_bump),
                        num_rooms=max(5, num_courses // 4 + resource_bump),
                        num_instructors=max(5, num_courses // 5 + resource_bump),
                        num_groups=max(8, num_courses // 2 + resource_bump),
                    )
                    break
                except RuntimeError:
                    continue
            if courses is None:
                results.append(TrialResult(solved=False, nodes=0, runtime_ms=0.0))
                continue
            solver = PrimeHypergraphTimetabler(courses)
            start = time.perf_counter()
            z, assignment, nodes = solver.solve(node_limit=node_limit)
            runtime_ms = (time.perf_counter() - start) * 1000.0
            results.append(
                TrialResult(
                    solved=assignment is not None and z is not None,
                    nodes=nodes,
                    runtime_ms=runtime_ms,
                )
            )
        lines.append(
            f"timetable courses={num_courses} options={options_per_course} node_limit={node_limit} | {summarize(results)}"
        )
    return lines


def random_inventory_instance(
    rng: random.Random,
    num_orders: int,
    options_per_order: int,
    num_warehouses: int,
    num_zones: int,
    num_skus: int,
) -> Tuple[List[Order], Dict[Tuple[str, str], int], Dict[Tuple[str, str, int], int]]:
    warehouses = [f"W{i}" for i in range(num_warehouses)]
    zones = [f"Z{i}" for i in range(num_zones)]
    skus = [f"SKU{i}" for i in range(num_skus)]
    shipping_methods = ["same-day", "air", "surface"]

    stock_capacity: Dict[Tuple[str, str], int] = {}
    lane_capacity: Dict[Tuple[str, str, int], int] = {}
    orders: List[Order] = []

    hidden_stock_use: Dict[Tuple[str, str], int] = {}
    hidden_lane_use: Dict[Tuple[str, str, int], int] = {}

    for i in range(num_orders):
        sku = rng.choice(skus)
        zone = rng.choice(zones)
        max_days = rng.choice([1, 2, 2, 3])
        priority = rng.randint(1, 10)
        plans = []
        hidden_warehouse = rng.choice(warehouses)
        hidden_days = rng.choice([d for d in (1, 2, 3) if d <= max_days])
        hidden_method = shipping_methods[hidden_days - 1]
        hidden_cost = {"same-day": 170, "air": 120, "surface": 80}[hidden_method] + rng.randint(0, 15)
        hidden_plan = FulfillmentPlan(
            warehouse=hidden_warehouse,
            ship_method=hidden_method,
            promise_days=hidden_days,
            unit_cost=hidden_cost,
            stock_key=(hidden_warehouse, sku),
            lane_key=(hidden_warehouse, zone, hidden_days),
        )
        plans.append(hidden_plan)
        hidden_stock_use[hidden_plan.stock_key] = hidden_stock_use.get(hidden_plan.stock_key, 0) + 1
        hidden_lane_use[hidden_plan.lane_key] = hidden_lane_use.get(hidden_plan.lane_key, 0) + 1
        seen = set()
        seen.add((hidden_plan.warehouse, zone, hidden_days))

        while len(plans) < options_per_order:
            warehouse = rng.choice(warehouses)
            promise_days = rng.choice([1, 2, 3])
            method = shipping_methods[promise_days - 1]
            key = (warehouse, zone, promise_days)
            if key in seen:
                continue
            seen.add(key)
            base_cost = {"same-day": 170, "air": 120, "surface": 80}[method]
            distance_penalty = warehouses.index(warehouse) * 8 + zones.index(zone) * 3
            cost = base_cost + distance_penalty + rng.randint(0, 15)
            plans.append(
                FulfillmentPlan(
                    warehouse=warehouse,
                    ship_method=method,
                    promise_days=promise_days,
                    unit_cost=cost,
                    stock_key=(warehouse, sku),
                    lane_key=(warehouse, zone, promise_days),
                )
            )

        orders.append(
            Order(
                order_id=f"O{i:04d}",
                sku=sku,
                zone=zone,
                max_days=max_days,
                priority=priority,
                plans=tuple(plans),
            )
        )

    # Set capacities after hidden feasible plans are known.
    for warehouse in warehouses:
        for sku in skus:
            base = hidden_stock_use.get((warehouse, sku), 0)
            stock_capacity[(warehouse, sku)] = base + rng.randint(0, 2)

    for warehouse in warehouses:
        for zone in zones:
            for days in (1, 2, 3):
                base = hidden_lane_use.get((warehouse, zone, days), 0)
                lane_capacity[(warehouse, zone, days)] = base + rng.randint(0, 2)

    return orders, stock_capacity, lane_capacity


def build_locked_assignments(
    rng: random.Random,
    assignment: Dict[int, int],
    lock_fraction: float,
) -> Dict[int, int]:
    keys = list(assignment.keys())
    rng.shuffle(keys)
    cutoff = int(len(keys) * lock_fraction)
    return {k: assignment[k] for k in keys[:cutoff]}


def run_inventory_trials(
    seed: int,
    sizes: List[Tuple[int, int]],
    trials_per_size: int,
    node_limit: int,
    repair_node_limit: int,
    lock_fraction: float,
) -> List[str]:
    lines = []
    for num_orders, options_per_order in sizes:
        base_results: List[TrialResult] = []
        repair_results: List[TrialResult] = []

        for trial in range(trials_per_size):
            rng = random.Random(seed + 5000 * num_orders + trial)
            orders, stock_capacity, lane_capacity = random_inventory_instance(
                rng=rng,
                num_orders=num_orders,
                options_per_order=options_per_order,
                num_warehouses=max(3, num_orders // 8),
                num_zones=max(3, num_orders // 10),
                num_skus=max(4, num_orders // 6),
            )

            solver = PrimeInventoryAllocator(orders, stock_capacity, lane_capacity)
            start = time.perf_counter()
            z, assignment, nodes, cost = solver.solve(node_limit=node_limit)
            runtime_ms = (time.perf_counter() - start) * 1000.0
            solved = assignment is not None and z is not None and cost is not None
            base_results.append(TrialResult(solved=solved, nodes=nodes, runtime_ms=runtime_ms, objective=cost))

            if not solved:
                repair_results.append(TrialResult(solved=False, nodes=0, runtime_ms=0.0, objective=None))
                continue

            locked = build_locked_assignments(rng, assignment, lock_fraction=lock_fraction)

            disrupted_stock = dict(stock_capacity)
            disrupted_lane = dict(lane_capacity)
            stock_keys = list(disrupted_stock.keys())
            lane_keys = list(disrupted_lane.keys())
            # Mild but meaningful disruption.
            for key in rng.sample(stock_keys, k=min(2, len(stock_keys))):
                disrupted_stock[key] = max(0, disrupted_stock[key] - 1)
            for key in rng.sample(lane_keys, k=min(2, len(lane_keys))):
                disrupted_lane[key] = max(0, disrupted_lane[key] - 1)

            repair_solver = PrimeInventoryAllocator(orders, disrupted_stock, disrupted_lane)
            start = time.perf_counter()
            rz, rassignment, rnodes, rcost = repair_solver.solve(
                locked_assignments=locked,
                node_limit=repair_node_limit,
            )
            runtime_ms = (time.perf_counter() - start) * 1000.0
            repair_results.append(
                TrialResult(
                    solved=rassignment is not None and rz is not None and rcost is not None,
                    nodes=rnodes,
                    runtime_ms=runtime_ms,
                    objective=rcost,
                )
            )

        lines.append(
            f"inventory-base orders={num_orders} options={options_per_order} node_limit={node_limit} | {summarize(base_results)}"
        )
        lines.append(
            f"inventory-repair orders={num_orders} options={options_per_order} node_limit={repair_node_limit} lock_fraction={lock_fraction:.2f} | {summarize(repair_results)}"
        )
    return lines


def main() -> None:
    seed = 42
    print("=" * 88)
    print("LARGE-SCALE CRT SEARCH BENCHMARK")
    print("=" * 88)
    print(f"seed={seed}")
    print("")

    print("Timetabling:")
    for line in run_timetable_trials(
        seed=seed,
        sizes=[(12, 4), (18, 4), (24, 5)],
        trials_per_size=5,
        node_limit=50000,
    ):
        print(f"  {line}")

    print("")
    print("Inventory Allocation:")
    for line in run_inventory_trials(
        seed=seed,
        sizes=[(20, 3), (35, 4), (50, 4)],
        trials_per_size=5,
        node_limit=60000,
        repair_node_limit=40000,
        lock_fraction=0.25,
    ):
        print(f"  {line}")


if __name__ == "__main__":
    main()
