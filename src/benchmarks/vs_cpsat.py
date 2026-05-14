"""
BENCHMARK VS CP-SAT
===================

Compares the repo's CRT-preserving search solvers against a standard exact tool:
Google OR-Tools CP-SAT.

The comparison is fair in the narrow sense:
- same synthetic instance generators
- same constraints
- same optimization target for inventory allocation
- same number of trials per size bucket

This is the benchmark that matters. If CP-SAT dominates, we should say so.
"""

from __future__ import annotations

from dataclasses import dataclass
from statistics import median
import random
import time
from typing import Dict, List, Optional, Tuple

from ortools.sat.python import cp_model

from src.benchmarks.scaling import random_inventory_instance, random_prime_timetable_instance
from src.domains.scheduling.timetabling import Course, PrimeHypergraphTimetabler, resources_of
from src.domains.logistics.inventory import Order, PrimeInventoryAllocator


@dataclass
class SolverRun:
    solved: bool
    runtime_ms: float
    objective: Optional[int] = None
    nodes: Optional[int] = None


def summarize_runs(name: str, runs: List[SolverRun]) -> str:
    solved = [r for r in runs if r.solved]
    success = 100.0 * len(solved) / len(runs) if runs else 0.0
    median_runtime = median(r.runtime_ms for r in runs) if runs else 0.0
    solved_runtime = median(r.runtime_ms for r in solved) if solved else 0.0
    parts = [
        f"{name}: success={len(solved)}/{len(runs)} ({success:.1f}%)",
        f"median_runtime_ms={median_runtime:.1f}",
    ]
    if solved:
        parts.append(f"solved_median_runtime_ms={solved_runtime:.1f}")
    node_values = [r.nodes for r in runs if r.nodes is not None]
    if node_values:
        parts.append(f"median_nodes={median(node_values)}")
    obj_values = [r.objective for r in solved if r.objective is not None]
    if obj_values:
        parts.append(f"solved_median_objective={median(obj_values)}")
    return " | ".join(parts)


def cpsat_timetable(courses: List[Course], time_limit_s: float) -> Tuple[bool, float]:
    model = cp_model.CpModel()
    x: Dict[Tuple[int, int], cp_model.IntVar] = {}

    for i, course in enumerate(courses):
        vars_i = []
        for oi, _ in enumerate(course.options):
            var = model.NewBoolVar(f"x_{i}_{oi}")
            x[(i, oi)] = var
            vars_i.append(var)
        model.AddExactlyOne(vars_i)

    resource_to_vars: Dict[Tuple[str, str], List[cp_model.IntVar]] = {}
    for i, course in enumerate(courses):
        for oi, placement in enumerate(course.options):
            for resource in resources_of(placement):
                resource_to_vars.setdefault(resource, []).append(x[(i, oi)])

    for vars_for_resource in resource_to_vars.values():
        if len(vars_for_resource) > 1:
            model.AddAtMostOne(vars_for_resource)

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = time_limit_s
    solver.parameters.num_search_workers = 8
    status = solver.Solve(model)
    return status in (cp_model.OPTIMAL, cp_model.FEASIBLE), solver.WallTime() * 1000.0


def cpsat_inventory(
    orders: List[Order],
    stock_capacity: Dict[Tuple[str, str], int],
    lane_capacity: Dict[Tuple[str, str, int], int],
    locked_assignments: Optional[Dict[int, int]],
    time_limit_s: float,
) -> Tuple[bool, float, Optional[int]]:
    model = cp_model.CpModel()
    x: Dict[Tuple[int, int], cp_model.IntVar] = {}

    for i, order in enumerate(orders):
        vars_i = []
        for pi, plan in enumerate(order.plans):
            var = model.NewBoolVar(f"x_{i}_{pi}")
            x[(i, pi)] = var
            vars_i.append(var)
            if plan.promise_days > order.max_days:
                model.Add(var == 0)
        model.AddExactlyOne(vars_i)

    if locked_assignments:
        for i, pi in locked_assignments.items():
            for pj in range(len(orders[i].plans)):
                model.Add(x[(i, pj)] == (1 if pj == pi else 0))

    for stock_key, cap in stock_capacity.items():
        vars_for_stock = []
        for i, order in enumerate(orders):
            for pi, plan in enumerate(order.plans):
                if plan.stock_key == stock_key:
                    vars_for_stock.append(x[(i, pi)])
        if vars_for_stock:
            model.Add(sum(vars_for_stock) <= cap)

    for lane_key, cap in lane_capacity.items():
        vars_for_lane = []
        for i, order in enumerate(orders):
            for pi, plan in enumerate(order.plans):
                if plan.lane_key == lane_key:
                    vars_for_lane.append(x[(i, pi)])
        if vars_for_lane:
            model.Add(sum(vars_for_lane) <= cap)

    model.Minimize(
        sum(plan.unit_cost * x[(i, pi)] for i, order in enumerate(orders) for pi, plan in enumerate(order.plans))
    )

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = time_limit_s
    solver.parameters.num_search_workers = 8
    status = solver.Solve(model)
    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return False, solver.WallTime() * 1000.0, None
    return True, solver.WallTime() * 1000.0, int(solver.ObjectiveValue())


def benchmark_timetable() -> List[str]:
    lines = []
    seed = 42
    sizes = [(12, 4), (18, 4), (24, 5)]
    trials = 5

    for num_courses, options_per_course in sizes:
        crt_runs: List[SolverRun] = []
        cpsat_runs: List[SolverRun] = []

        for trial in range(trials):
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
                crt_runs.append(SolverRun(False, 0.0, nodes=0))
                cpsat_runs.append(SolverRun(False, 0.0))
                continue

            crt = PrimeHypergraphTimetabler(courses)
            start = time.perf_counter()
            z, assignment, nodes = crt.solve(node_limit=50000)
            crt_runs.append(
                SolverRun(
                    solved=(z is not None and assignment is not None),
                    runtime_ms=(time.perf_counter() - start) * 1000.0,
                    nodes=nodes,
                )
            )

            solved, runtime_ms = cpsat_timetable(courses, time_limit_s=5.0)
            cpsat_runs.append(SolverRun(solved=solved, runtime_ms=runtime_ms))

        lines.append(f"timetable courses={num_courses} options={options_per_course}")
        lines.append("  " + summarize_runs("crt", crt_runs))
        lines.append("  " + summarize_runs("cpsat", cpsat_runs))
    return lines


def benchmark_inventory() -> List[str]:
    lines = []
    seed = 42
    sizes = [(20, 3), (35, 4), (50, 4)]
    trials = 5
    lock_fraction = 0.25

    for num_orders, options_per_order in sizes:
        crt_base: List[SolverRun] = []
        cpsat_base: List[SolverRun] = []
        crt_repair: List[SolverRun] = []
        cpsat_repair: List[SolverRun] = []

        for trial in range(trials):
            rng = random.Random(seed + 5000 * num_orders + trial)
            orders, stock_capacity, lane_capacity = random_inventory_instance(
                rng=rng,
                num_orders=num_orders,
                options_per_order=options_per_order,
                num_warehouses=max(3, num_orders // 8),
                num_zones=max(3, num_orders // 10),
                num_skus=max(4, num_orders // 6),
            )

            crt = PrimeInventoryAllocator(orders, stock_capacity, lane_capacity)
            start = time.perf_counter()
            z, assignment, nodes, cost = crt.solve(node_limit=60000)
            crt_base.append(
                SolverRun(
                    solved=(z is not None and assignment is not None and cost is not None),
                    runtime_ms=(time.perf_counter() - start) * 1000.0,
                    objective=cost,
                    nodes=nodes,
                )
            )

            solved, runtime_ms, objective = cpsat_inventory(
                orders,
                stock_capacity,
                lane_capacity,
                locked_assignments=None,
                time_limit_s=5.0,
            )
            cpsat_base.append(SolverRun(solved=solved, runtime_ms=runtime_ms, objective=objective))

            if assignment is None:
                crt_repair.append(SolverRun(False, 0.0, nodes=0))
                cpsat_repair.append(SolverRun(False, 0.0))
                continue

            keys = list(assignment.keys())
            rng.shuffle(keys)
            cutoff = int(len(keys) * lock_fraction)
            locked = {k: assignment[k] for k in keys[:cutoff]}

            disrupted_stock = dict(stock_capacity)
            disrupted_lane = dict(lane_capacity)
            for key in rng.sample(list(disrupted_stock.keys()), k=min(2, len(disrupted_stock))):
                disrupted_stock[key] = max(0, disrupted_stock[key] - 1)
            for key in rng.sample(list(disrupted_lane.keys()), k=min(2, len(disrupted_lane))):
                disrupted_lane[key] = max(0, disrupted_lane[key] - 1)

            crt_repair_solver = PrimeInventoryAllocator(orders, disrupted_stock, disrupted_lane)
            start = time.perf_counter()
            rz, rassignment, rnodes, rcost = crt_repair_solver.solve(
                locked_assignments=locked,
                node_limit=40000,
            )
            crt_repair.append(
                SolverRun(
                    solved=(rz is not None and rassignment is not None and rcost is not None),
                    runtime_ms=(time.perf_counter() - start) * 1000.0,
                    objective=rcost,
                    nodes=rnodes,
                )
            )

            solved, runtime_ms, objective = cpsat_inventory(
                orders,
                disrupted_stock,
                disrupted_lane,
                locked_assignments=locked,
                time_limit_s=5.0,
            )
            cpsat_repair.append(SolverRun(solved=solved, runtime_ms=runtime_ms, objective=objective))

        lines.append(f"inventory-base orders={num_orders} options={options_per_order}")
        lines.append("  " + summarize_runs("crt", crt_base))
        lines.append("  " + summarize_runs("cpsat", cpsat_base))
        lines.append(f"inventory-repair orders={num_orders} options={options_per_order}")
        lines.append("  " + summarize_runs("crt", crt_repair))
        lines.append("  " + summarize_runs("cpsat", cpsat_repair))
    return lines


def main() -> None:
    print("=" * 88)
    print("CRT SEARCH VS OR-TOOLS CP-SAT")
    print("=" * 88)
    print("")
    print("Timetabling:")
    for line in benchmark_timetable():
        print(line)
    print("")
    print("Inventory Allocation:")
    for line in benchmark_inventory():
        print(line)


if __name__ == "__main__":
    main()
