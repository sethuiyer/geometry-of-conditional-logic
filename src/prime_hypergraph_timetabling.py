"""
PRIME HYPERGRAPH TIMETABLING
============================

A genuinely NP-hard timetabling problem solved with the strongest part of
this repository's framework: exact CRT-preserving incremental jumps.

Problem:
- Each course must pick exactly one legal placement.
- Placements consume resources: timeslot, room, instructor, and student groups.
- Courses conflict if any claimed resource overlaps incompatibly.

Why NP-hard:
- Graph coloring reduces directly to this problem.
- Let each course be a graph vertex and each timeslot be a color.
- Give every course one legal placement per timeslot.
- For every graph edge (u, v), declare the matching timeslot placements
  incompatible.
- A valid timetable exists iff the graph is k-colorable.

Framework fit:
- Course i gets a prime p_i > number_of_legal_options(course_i).
- z % p_i = chosen option index for course i.
- Once a course assignment is accepted, we use an exact CRT jump to preserve
  all previous assignments while setting the new residue.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Set, Tuple


@dataclass(frozen=True)
class Placement:
    slot: str
    room: str
    instructor: str
    groups: Tuple[str, ...]


@dataclass(frozen=True)
class Course:
    name: str
    options: Tuple[Placement, ...]


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


def primes_for_courses(courses: List[Course]) -> List[int]:
    primes = []
    candidate_floor = 2
    for course in courses:
        candidate_floor = max(candidate_floor, len(course.options) + 1)
        p = next_prime_at_least(candidate_floor)
        while p in primes:
            p = next_prime_at_least(p + 1)
        primes.append(p)
        candidate_floor = p + 1
    return primes


def resources_of(placement: Placement) -> Set[Tuple[str, str]]:
    resources: Set[Tuple[str, str]] = {
        ("slot-room", f"{placement.slot}|{placement.room}"),
        ("slot-instructor", f"{placement.slot}|{placement.instructor}"),
    }
    for group in placement.groups:
        resources.add(("slot-group", f"{placement.slot}|{group}"))
    return resources


def placements_conflict(a: Placement, b: Placement) -> bool:
    if a.slot != b.slot:
        return False
    if a.room == b.room:
        return True
    if a.instructor == b.instructor:
        return True
    return bool(set(a.groups) & set(b.groups))


class PrimeHypergraphTimetabler:
    def __init__(self, courses: List[Course]):
        self.courses = courses
        self.primes = primes_for_courses(courses)
        self.n = len(courses)
        self.conflicts = self._build_conflicts()

    def _build_conflicts(self) -> Dict[Tuple[int, int], Set[Tuple[int, int]]]:
        conflicts: Dict[Tuple[int, int], Set[Tuple[int, int]]] = {}
        for i, course in enumerate(self.courses):
            for oi, placement in enumerate(course.options):
                key = (i, oi)
                conflicts[key] = set()
                for j, other_course in enumerate(self.courses):
                    if i == j:
                        continue
                    for oj, other_placement in enumerate(other_course.options):
                        if placements_conflict(placement, other_placement):
                            conflicts[key].add((j, oj))
        return conflicts

    def garners_jump(self, current_z: int, target_value: int, course_idx: int, solved: List[int]) -> int:
        p_target = self.primes[course_idx]
        M = 1
        for idx in solved:
            M *= self.primes[idx]
        diff = (target_value - current_z) % p_target
        k = (diff * mod_inverse(M, p_target)) % p_target
        return k * M

    def decode(self, z: int) -> List[int]:
        return [z % p for p in self.primes]

    def verify_assignment(self, assignment: Dict[int, int]) -> Tuple[bool, str]:
        used_resources: Set[Tuple[str, str]] = set()
        for course_idx, option_idx in assignment.items():
            placement = self.courses[course_idx].options[option_idx]
            claim = resources_of(placement)
            overlap = used_resources & claim
            if overlap:
                return False, f"resource conflict at {self.courses[course_idx].name}: {sorted(overlap)}"
            used_resources |= claim
        return True, "ok"

    def candidate_options(self, course_idx: int, assignment: Dict[int, int]) -> List[int]:
        legal = []
        for option_idx, _ in enumerate(self.courses[course_idx].options):
            blocked = False
            for assigned_course, assigned_option in assignment.items():
                if (assigned_course, assigned_option) in self.conflicts[(course_idx, option_idx)]:
                    blocked = True
                    break
            if not blocked:
                legal.append(option_idx)
        return legal

    def choose_next_course(self, assignment: Dict[int, int]) -> Tuple[Optional[int], List[int]]:
        best_idx = None
        best_options: List[int] = []
        best_score = None

        for course_idx in range(self.n):
            if course_idx in assignment:
                continue
            options = self.candidate_options(course_idx, assignment)
            score = (len(options), -len(self.courses[course_idx].options))
            if best_score is None or score < best_score:
                best_score = score
                best_idx = course_idx
                best_options = options

        return best_idx, best_options

    def order_options(self, course_idx: int, options: List[int], assignment: Dict[int, int]) -> List[int]:
        scored = []
        for option_idx in options:
            future_blocked = 0
            for other_idx in range(self.n):
                if other_idx == course_idx or other_idx in assignment:
                    continue
                for other_option in range(len(self.courses[other_idx].options)):
                    if (other_idx, other_option) in self.conflicts[(course_idx, option_idx)]:
                        future_blocked += 1
            scored.append((future_blocked, option_idx))
        scored.sort()
        return [option_idx for _, option_idx in scored]

    def solve(self) -> Tuple[Optional[int], Optional[Dict[int, int]], int]:
        attempts = 0

        def backtrack(z: int, assignment: Dict[int, int], solved_order: List[int]) -> Tuple[Optional[int], Optional[Dict[int, int]]]:
            nonlocal attempts
            attempts += 1

            if len(assignment) == self.n:
                ok, _ = self.verify_assignment(assignment)
                if ok:
                    return z, dict(assignment)
                return None, None

            course_idx, options = self.choose_next_course(assignment)
            if course_idx is None or not options:
                return None, None

            for option_idx in self.order_options(course_idx, options, assignment):
                assignment[course_idx] = option_idx

                if not solved_order:
                    new_z = option_idx
                else:
                    new_z = z + self.garners_jump(z, option_idx, course_idx, solved_order)

                solved_order.append(course_idx)
                result_z, result_assignment = backtrack(new_z, assignment, solved_order)
                if result_assignment is not None:
                    return result_z, result_assignment
                solved_order.pop()
                del assignment[course_idx]

            return None, None

        final_z, final_assignment = backtrack(0, {}, [])
        return final_z, final_assignment, attempts

    def render_solution(self, z: int, assignment: Dict[int, int]) -> str:
        lines = []
        lines.append("=" * 76)
        lines.append("PRIME HYPERGRAPH TIMETABLING")
        lines.append("=" * 76)
        lines.append(f"Courses: {self.n}")
        lines.append(f"Primes:  {self.primes}")
        lines.append(f"Master Coordinate: z = {z}")
        lines.append("")
        lines.append(f"{'Course':<16} | {'Residue':<7} | {'Slot':<10} | {'Room':<8} | {'Instructor':<10} | Groups")
        lines.append("-" * 76)

        for i, course in enumerate(self.courses):
            option_idx = assignment[i]
            residue = z % self.primes[i]
            placement = course.options[option_idx]
            groups = ",".join(placement.groups)
            lines.append(
                f"{course.name:<16} | {residue:<7} | {placement.slot:<10} | {placement.room:<8} | "
                f"{placement.instructor:<10} | {groups}"
            )

        ok, reason = self.verify_assignment(assignment)
        lines.append("-" * 76)
        lines.append(f"Verification: {'PASS' if ok else 'FAIL'} ({reason})")
        return "\n".join(lines)


def build_demo_instance() -> List[Course]:
    return [
        Course(
            "Algorithms",
            (
                Placement("Mon-09", "R1", "Ada", ("CS-A", "CS-B")),
                Placement("Tue-09", "R2", "Ada", ("CS-A", "CS-B")),
                Placement("Wed-11", "R1", "Ada", ("CS-A", "CS-B")),
            ),
        ),
        Course(
            "Databases",
            (
                Placement("Mon-09", "R2", "Turing", ("CS-B",)),
                Placement("Tue-11", "R1", "Turing", ("CS-B",)),
                Placement("Wed-09", "R2", "Turing", ("CS-B",)),
            ),
        ),
        Course(
            "Compilers",
            (
                Placement("Mon-11", "R1", "Church", ("CS-A",)),
                Placement("Tue-09", "R1", "Church", ("CS-A",)),
                Placement("Wed-09", "R1", "Church", ("CS-A",)),
            ),
        ),
        Course(
            "Networks",
            (
                Placement("Mon-09", "R3", "Shannon", ("EE-A", "CS-A")),
                Placement("Tue-11", "R2", "Shannon", ("EE-A", "CS-A")),
                Placement("Wed-11", "R2", "Shannon", ("EE-A", "CS-A")),
            ),
        ),
        Course(
            "OperatingSys",
            (
                Placement("Mon-11", "R2", "Ada", ("CS-B", "EE-A")),
                Placement("Tue-09", "R3", "Knuth", ("CS-B", "EE-A")),
                Placement("Wed-09", "R3", "Knuth", ("CS-B", "EE-A")),
            ),
        ),
        Course(
            "MLSystems",
            (
                Placement("Mon-09", "R4", "Ng", ("DS-A", "CS-A")),
                Placement("Tue-11", "R3", "Ng", ("DS-A", "CS-A")),
                Placement("Wed-09", "R4", "Ng", ("DS-A", "CS-A")),
            ),
        ),
        Course(
            "Security",
            (
                Placement("Mon-11", "R3", "Turing", ("CS-A", "DS-A")),
                Placement("Tue-09", "R4", "Turing", ("CS-A", "DS-A")),
                Placement("Wed-11", "R4", "Turing", ("CS-A", "DS-A")),
            ),
        ),
    ]


if __name__ == "__main__":
    courses = build_demo_instance()
    solver = PrimeHypergraphTimetabler(courses)
    z, assignment, attempts = solver.solve()

    if assignment is None or z is None:
        print("No valid timetable found.")
    else:
        print(solver.render_solution(z, assignment))
        print(f"Search nodes explored: {attempts}")
