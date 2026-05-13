"""
PRIME INVENTORY ALLOCATION / ORDER PROMISING
============================================

A Flipkart-style allocation demo using the strongest real mechanism in this
repository: exact CRT-preserving incremental jumps inside a constrained search.

Problem:
- Each order must choose exactly one feasible fulfillment plan.
- Plans consume warehouse stock and shipping-lane capacity.
- Some orders may already be promised and therefore locked.
- When a disruption happens, the solver repairs the remaining orders while
  preserving committed ones exactly.

Why this is commercially interesting:
- The option menu per order is naturally small.
- Constraints are hard and expensive to violate.
- Preserving existing commitments matters more than "global re-optimization."
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple


@dataclass(frozen=True)
class FulfillmentPlan:
    warehouse: str
    ship_method: str
    promise_days: int
    unit_cost: int
    stock_key: Tuple[str, str]
    lane_key: Tuple[str, str, int]


@dataclass(frozen=True)
class Order:
    order_id: str
    sku: str
    zone: str
    max_days: int
    priority: int
    plans: Tuple[FulfillmentPlan, ...]


def mod_inverse(a: int, m: int) -> int:
    a %= m
    for x in range(1, m):
        if (a * x) % m == 1:
            return x
    raise ValueError(f"No modular inverse for {a} mod {m}")


def next_prime_at_least(n: int) -> int:
    candidate = max(2, n)
    while True:
        is_prime = True
        d = 2
        while d * d <= candidate:
            if candidate % d == 0:
                is_prime = False
                break
            d += 1
        if is_prime:
            return candidate
        candidate += 1


def primes_for_orders(orders: List[Order]) -> List[int]:
    primes = []
    floor = 2
    for order in orders:
        floor = max(floor, len(order.plans) + 1)
        p = next_prime_at_least(floor)
        while p in primes:
            p = next_prime_at_least(p + 1)
        primes.append(p)
        floor = p + 1
    return primes


class PrimeInventoryAllocator:
    def __init__(
        self,
        orders: List[Order],
        stock_capacity: Dict[Tuple[str, str], int],
        lane_capacity: Dict[Tuple[str, str, int], int],
    ):
        self.orders = orders
        self.stock_capacity = dict(stock_capacity)
        self.lane_capacity = dict(lane_capacity)
        self.primes = primes_for_orders(orders)
        self.n = len(orders)

    def garners_jump(self, current_z: int, target_value: int, order_idx: int, solved: List[int]) -> int:
        p_target = self.primes[order_idx]
        M = 1
        for idx in solved:
            M *= self.primes[idx]
        diff = (target_value - current_z) % p_target
        k = (diff * mod_inverse(M, p_target)) % p_target
        return k * M

    def decode(self, z: int) -> List[int]:
        return [z % p for p in self.primes]

    def candidate_options(
        self,
        order_idx: int,
        stock_remaining: Dict[Tuple[str, str], int],
        lane_remaining: Dict[Tuple[str, str, int], int],
    ) -> List[int]:
        legal = []
        order = self.orders[order_idx]
        for plan_idx, plan in enumerate(order.plans):
            if plan.promise_days > order.max_days:
                continue
            if stock_remaining.get(plan.stock_key, 0) < 1:
                continue
            if lane_remaining.get(plan.lane_key, 0) < 1:
                continue
            legal.append(plan_idx)
        return legal

    def option_penalty(self, order_idx: int, plan_idx: int) -> int:
        order = self.orders[order_idx]
        plan = order.plans[plan_idx]
        sla_slack = order.max_days - plan.promise_days
        # Lower is better: shipping cost dominates, then use some slack, and
        # prioritize important orders having good options.
        return plan.unit_cost * 10 - sla_slack * 3 - order.priority

    def choose_next_order(
        self,
        assignment: Dict[int, int],
        stock_remaining: Dict[Tuple[str, str], int],
        lane_remaining: Dict[Tuple[str, str, int], int],
    ) -> Tuple[Optional[int], List[int]]:
        best_idx = None
        best_options: List[int] = []
        best_score = None

        for order_idx in range(self.n):
            if order_idx in assignment:
                continue
            options = self.candidate_options(order_idx, stock_remaining, lane_remaining)
            order = self.orders[order_idx]
            score = (len(options), -order.priority, len(order.plans))
            if best_score is None or score < best_score:
                best_score = score
                best_idx = order_idx
                best_options = options

        return best_idx, best_options

    def order_options(self, order_idx: int, options: List[int]) -> List[int]:
        return sorted(options, key=lambda option_idx: self.option_penalty(order_idx, option_idx))

    def apply_plan(
        self,
        plan: FulfillmentPlan,
        stock_remaining: Dict[Tuple[str, str], int],
        lane_remaining: Dict[Tuple[str, str, int], int],
    ) -> None:
        stock_remaining[plan.stock_key] = stock_remaining.get(plan.stock_key, 0) - 1
        lane_remaining[plan.lane_key] = lane_remaining.get(plan.lane_key, 0) - 1

    def unapply_plan(
        self,
        plan: FulfillmentPlan,
        stock_remaining: Dict[Tuple[str, str], int],
        lane_remaining: Dict[Tuple[str, str, int], int],
    ) -> None:
        stock_remaining[plan.stock_key] = stock_remaining.get(plan.stock_key, 0) + 1
        lane_remaining[plan.lane_key] = lane_remaining.get(plan.lane_key, 0) + 1

    def verify_assignment(self, assignment: Dict[int, int]) -> Tuple[bool, str, int]:
        stock_used: Dict[Tuple[str, str], int] = {}
        lane_used: Dict[Tuple[str, str, int], int] = {}
        total_cost = 0

        for order_idx, plan_idx in assignment.items():
            order = self.orders[order_idx]
            if plan_idx < 0 or plan_idx >= len(order.plans):
                return False, f"invalid plan index for {order.order_id}", total_cost
            plan = order.plans[plan_idx]
            if plan.promise_days > order.max_days:
                return False, f"SLA violation for {order.order_id}", total_cost

            stock_used[plan.stock_key] = stock_used.get(plan.stock_key, 0) + 1
            lane_used[plan.lane_key] = lane_used.get(plan.lane_key, 0) + 1
            total_cost += plan.unit_cost

        for key, used in stock_used.items():
            if used > self.stock_capacity.get(key, 0):
                return False, f"stock exceeded at {key}: {used}>{self.stock_capacity.get(key, 0)}", total_cost

        for key, used in lane_used.items():
            if used > self.lane_capacity.get(key, 0):
                return False, f"lane exceeded at {key}: {used}>{self.lane_capacity.get(key, 0)}", total_cost

        if len(assignment) != self.n:
            return False, "not all orders assigned", total_cost

        return True, "ok", total_cost

    def solve(
        self,
        locked_assignments: Optional[Dict[int, int]] = None,
        node_limit: Optional[int] = None,
    ) -> Tuple[Optional[int], Optional[Dict[int, int]], int, Optional[int]]:
        locked_assignments = dict(locked_assignments or {})
        stock_remaining = dict(self.stock_capacity)
        lane_remaining = dict(self.lane_capacity)
        assignment: Dict[int, int] = {}
        solved_order: List[int] = []
        z = 0
        nodes = 0

        for order_idx, plan_idx in sorted(locked_assignments.items()):
            order = self.orders[order_idx]
            if plan_idx < 0 or plan_idx >= len(order.plans):
                return None, None, 0, None
            plan = order.plans[plan_idx]
            if plan.promise_days > order.max_days:
                return None, None, 0, None
            if stock_remaining.get(plan.stock_key, 0) < 1:
                return None, None, 0, None
            if lane_remaining.get(plan.lane_key, 0) < 1:
                return None, None, 0, None

            if not solved_order:
                z = plan_idx
            else:
                z = z + self.garners_jump(z, plan_idx, order_idx, solved_order)

            assignment[order_idx] = plan_idx
            solved_order.append(order_idx)
            self.apply_plan(plan, stock_remaining, lane_remaining)

        best_cost: Optional[int] = None
        best_assignment: Optional[Dict[int, int]] = None
        best_z: Optional[int] = None

        def lower_bound(current_assignment: Dict[int, int]) -> int:
            bound = 0
            for idx, plan_idx in current_assignment.items():
                bound += self.orders[idx].plans[plan_idx].unit_cost
            for idx in range(self.n):
                if idx in current_assignment:
                    continue
                bound += min(plan.unit_cost for plan in self.orders[idx].plans)
            return bound

        def backtrack(
            current_z: int,
            current_assignment: Dict[int, int],
            current_solved: List[int],
        ) -> None:
            nonlocal nodes, best_cost, best_assignment, best_z
            nodes += 1

            if node_limit is not None and nodes > node_limit:
                return

            if best_cost is not None and lower_bound(current_assignment) >= best_cost:
                return

            if len(current_assignment) == self.n:
                ok, _, total_cost = self.verify_assignment(current_assignment)
                if ok and (best_cost is None or total_cost < best_cost):
                    best_cost = total_cost
                    best_assignment = dict(current_assignment)
                    best_z = current_z
                return

            order_idx, options = self.choose_next_order(current_assignment, stock_remaining, lane_remaining)
            if order_idx is None or not options:
                return

            for plan_idx in self.order_options(order_idx, options):
                plan = self.orders[order_idx].plans[plan_idx]
                current_assignment[order_idx] = plan_idx
                self.apply_plan(plan, stock_remaining, lane_remaining)

                if not current_solved:
                    new_z = plan_idx
                else:
                    new_z = current_z + self.garners_jump(current_z, plan_idx, order_idx, current_solved)

                current_solved.append(order_idx)
                backtrack(new_z, current_assignment, current_solved)
                current_solved.pop()

                self.unapply_plan(plan, stock_remaining, lane_remaining)
                del current_assignment[order_idx]

        backtrack(z, assignment, solved_order)
        return best_z, best_assignment, nodes, best_cost

    def render_solution(
        self,
        title: str,
        z: int,
        assignment: Dict[int, int],
        locked_assignments: Optional[Dict[int, int]] = None,
    ) -> str:
        locked_assignments = locked_assignments or {}
        ok, reason, total_cost = self.verify_assignment(assignment)
        lines = []
        lines.append("=" * 104)
        lines.append(title)
        lines.append("=" * 104)
        lines.append(f"Orders: {self.n}")
        lines.append(f"Primes: {self.primes}")
        lines.append(f"Master Coordinate: z = {z}")
        lines.append(f"Verification: {'PASS' if ok else 'FAIL'} ({reason})")
        lines.append(f"Total Shipping Cost: {total_cost}")
        lines.append("")
        lines.append(
            f"{'Order':<10} | {'Locked':<6} | {'Residue':<7} | {'SKU':<12} | {'Zone':<8} | "
            f"{'Warehouse':<10} | {'Method':<9} | {'Days':<4} | {'Cost':<4}"
        )
        lines.append("-" * 104)

        for order_idx, order in enumerate(self.orders):
            plan_idx = assignment[order_idx]
            residue = z % self.primes[order_idx]
            plan = order.plans[plan_idx]
            locked = "yes" if order_idx in locked_assignments else "no"
            lines.append(
                f"{order.order_id:<10} | {locked:<6} | {residue:<7} | {order.sku:<12} | {order.zone:<8} | "
                f"{plan.warehouse:<10} | {plan.ship_method:<9} | {plan.promise_days:<4} | {plan.unit_cost:<4}"
            )

        return "\n".join(lines)


def build_flipkart_demo() -> Tuple[List[Order], Dict[Tuple[str, str], int], Dict[Tuple[str, str, int], int]]:
    stock_capacity = {
        ("BLR_FC", "iphone15"): 2,
        ("MUM_FC", "iphone15"): 1,
        ("DEL_FC", "iphone15"): 1,
        ("BLR_FC", "airpods"): 2,
        ("MUM_FC", "airpods"): 1,
        ("DEL_FC", "airpods"): 1,
        ("BLR_FC", "ps5"): 1,
        ("MUM_FC", "ps5"): 2,
        ("DEL_FC", "ps5"): 1,
        ("BLR_FC", "dyson"): 1,
        ("MUM_FC", "dyson"): 1,
        ("DEL_FC", "dyson"): 2,
    }

    lane_capacity = {
        ("BLR_FC", "South", 1): 2,
        ("BLR_FC", "West", 2): 2,
        ("BLR_FC", "North", 3): 1,
        ("MUM_FC", "West", 1): 2,
        ("MUM_FC", "South", 2): 1,
        ("MUM_FC", "North", 3): 1,
        ("DEL_FC", "North", 1): 2,
        ("DEL_FC", "West", 2): 1,
        ("DEL_FC", "South", 3): 1,
    }

    def plan(warehouse: str, zone: str, sku: str, method: str, days: int, cost: int) -> FulfillmentPlan:
        return FulfillmentPlan(
            warehouse=warehouse,
            ship_method=method,
            promise_days=days,
            unit_cost=cost,
            stock_key=(warehouse, sku),
            lane_key=(warehouse, zone, days),
        )

    orders = [
        Order(
            "FK1001",
            "iphone15",
            "South",
            2,
            10,
            (
                plan("BLR_FC", "South", "iphone15", "same-day-air", 1, 180),
                plan("MUM_FC", "South", "iphone15", "air", 2, 220),
                plan("DEL_FC", "South", "iphone15", "surface", 3, 150),
            ),
        ),
        Order(
            "FK1002",
            "iphone15",
            "West",
            2,
            9,
            (
                plan("MUM_FC", "West", "iphone15", "same-day-air", 1, 170),
                plan("BLR_FC", "West", "iphone15", "air", 2, 210),
                plan("DEL_FC", "West", "iphone15", "surface", 2, 190),
            ),
        ),
        Order(
            "FK1003",
            "airpods",
            "North",
            2,
            7,
            (
                plan("DEL_FC", "North", "airpods", "same-day-air", 1, 90),
                plan("MUM_FC", "North", "airpods", "air", 3, 110),
                plan("BLR_FC", "North", "airpods", "surface", 3, 80),
            ),
        ),
        Order(
            "FK1004",
            "ps5",
            "West",
            2,
            10,
            (
                plan("MUM_FC", "West", "ps5", "same-day-air", 1, 240),
                plan("DEL_FC", "West", "ps5", "air", 2, 260),
                plan("BLR_FC", "West", "ps5", "surface", 2, 210),
            ),
        ),
        Order(
            "FK1005",
            "dyson",
            "North",
            1,
            8,
            (
                plan("DEL_FC", "North", "dyson", "same-day-air", 1, 130),
                plan("MUM_FC", "North", "dyson", "air", 3, 120),
                plan("BLR_FC", "North", "dyson", "surface", 3, 100),
            ),
        ),
        Order(
            "FK1006",
            "airpods",
            "South",
            2,
            6,
            (
                plan("BLR_FC", "South", "airpods", "same-day-air", 1, 85),
                plan("MUM_FC", "South", "airpods", "air", 2, 95),
                plan("DEL_FC", "South", "airpods", "surface", 3, 70),
            ),
        ),
        Order(
            "FK1007",
            "ps5",
            "North",
            3,
            7,
            (
                plan("DEL_FC", "North", "ps5", "same-day-air", 1, 250),
                plan("MUM_FC", "North", "ps5", "air", 3, 180),
                plan("BLR_FC", "North", "ps5", "surface", 3, 160),
            ),
        ),
        Order(
            "FK1008",
            "dyson",
            "West",
            2,
            5,
            (
                plan("MUM_FC", "West", "dyson", "same-day-air", 1, 140),
                plan("DEL_FC", "West", "dyson", "air", 2, 150),
                plan("BLR_FC", "West", "dyson", "surface", 2, 125),
            ),
        ),
    ]

    return orders, stock_capacity, lane_capacity


def compare_assignments(before: Dict[int, int], after: Dict[int, int], orders: List[Order], locked: Dict[int, int]) -> str:
    lines = []
    lines.append("Repair Delta:")
    changes = 0
    for idx, order in enumerate(orders):
        old = before[idx]
        new = after[idx]
        if old == new:
            continue
        changes += 1
        lock_flag = "LOCKED" if idx in locked else "repaired"
        lines.append(f"  {order.order_id}: {old} -> {new} ({lock_flag})")
    if changes == 0:
        lines.append("  No plan changes.")
    return "\n".join(lines)


if __name__ == "__main__":
    orders, stock_capacity, lane_capacity = build_flipkart_demo()

    base_solver = PrimeInventoryAllocator(orders, stock_capacity, lane_capacity)
    base_z, base_assignment, base_nodes, base_cost = base_solver.solve()

    if base_assignment is None or base_z is None or base_cost is None:
        print("Base allocation failed.")
        raise SystemExit(1)

    print(base_solver.render_solution("FLIPKART BASE ALLOCATION", base_z, base_assignment))
    print(f"Search nodes explored: {base_nodes}")
    print()

    locked = {0: base_assignment[0], 1: base_assignment[1], 3: base_assignment[3]}

    disrupted_stock = dict(stock_capacity)
    disrupted_lane = dict(lane_capacity)
    # Simulate disruption:
    # - one BLR iPhone unit is lost;
    # - the BLR -> West 2-day lane tightens, forcing local repair for an
    #   unlocked order while preserving locked promises.
    disrupted_stock[("BLR_FC", "iphone15")] = 1
    disrupted_lane[("BLR_FC", "West", 2)] = 1

    repair_solver = PrimeInventoryAllocator(orders, disrupted_stock, disrupted_lane)
    repair_z, repair_assignment, repair_nodes, repair_cost = repair_solver.solve(locked_assignments=locked)

    if repair_assignment is None or repair_z is None or repair_cost is None:
        print("Repair allocation failed under disruption.")
        raise SystemExit(1)

    print(repair_solver.render_solution("FLIPKART DISRUPTION REPAIR", repair_z, repair_assignment, locked))
    print(f"Search nodes explored: {repair_nodes}")
    print(compare_assignments(base_assignment, repair_assignment, orders, locked))
