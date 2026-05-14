#!/usr/bin/env python3
"""
Hierarchical CRT Latin Squares Solver
=======================================
n×n grid.  Each row and column contains every symbol 1..n exactly once.

Constraint groups: n rows + n columns = 2n groups.
Each group is a CRT microspace with n positions.
A cell at (r,c) lives in two groups: row[r] and col[c].
Placement is a double synchronized jump: both groups must agree.
"""

from copy import deepcopy

PRIMES = [11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47, 53, 59, 61, 67, 71]

def mod_inverse(a, m):
    return pow(a, -1, m)

class ConstraintGroup:
    def __init__(self, name, n):
        self.name = name
        self.primes = PRIMES[:n]
        self.z = 0
        self.residues = [0] * n
        self.locked = set()

    def jump(self, pos, val):
        if pos in self.locked:
            return self.z if self.residues[pos] == val else None
        p_target = self.primes[pos]
        M = 1
        for p in self.locked:
            M *= self.primes[p]
        if M == 1:
            new_z = val
        else:
            diff = (val - self.z) % p_target
            k = (diff * mod_inverse(M, p_target)) % p_target
            new_z = self.z + k * M
        self.z = new_z
        self.residues[pos] = val
        self.locked.add(pos)
        return new_z

    def is_valid(self):
        n = len(self.primes)
        seen = {}
        for i in range(n):
            v = self.residues[i]
            if v == 0:
                continue
            if v < 1 or v > n:
                return False
            if v in seen:
                return False
            seen[v] = i
        return True

    def get_value(self, pos):
        return self.residues[pos]

    def reset_to(self, other):
        self.z = other.z
        self.residues = other.residues[:]
        self.locked = other.locked.copy()


def create_groups(n):
    rows = [ConstraintGroup(f"row{r}", n) for r in range(n)]
    cols = [ConstraintGroup(f"col{c}", n) for c in range(n)]
    return {"row": rows, "col": cols}


def try_place(r, c, v, groups, n):
    row_g = groups["row"][r]
    col_g = groups["col"][c]
    snap_r = deepcopy(row_g)
    snap_c = deepcopy(col_g)

    if row_g.jump(c, v) is None or not row_g.is_valid():
        row_g.reset_to(snap_r)
        return False
    if col_g.jump(r, v) is None or not col_g.is_valid():
        row_g.reset_to(snap_r)
        col_g.reset_to(snap_c)
        return False
    return True


def print_grid(groups, n):
    for r in range(n):
        row = [str(groups["row"][r].get_value(c) or ".") for c in range(n)]
        print(" ".join(row))
    print()


def solve(groups, empty_cells, n):
    if not empty_cells:
        return True
    r, c = empty_cells[0]
    rest = empty_cells[1:]
    for v in range(1, n + 1):
        snap_r = deepcopy(groups["row"][r])
        snap_c = deepcopy(groups["col"][c])
        if try_place(r, c, v, groups, n):
            if solve(groups, rest, n):
                return True
            groups["row"][r].reset_to(snap_r)
            groups["col"][c].reset_to(snap_c)
    return False


def solve_latin_square(puzzle):
    n = len(puzzle)
    groups = create_groups(n)
    empty = []
    for r in range(n):
        for c in range(n):
            if puzzle[r][c] != 0:
                if not try_place(r, c, puzzle[r][c], groups, n):
                    print(f"Conflict at ({r},{c})")
                    return None
            else:
                empty.append((r, c))
    print("Initial:")
    print_grid(groups, n)
    if solve(groups, empty, n):
        print("Solved:")
        print_grid(groups, n)
        return groups
    print("No solution")
    return None


if __name__ == "__main__":
    n = 4
    puzzle = [
        [0, 0, 0, 0],
        [0, 0, 0, 0],
        [0, 0, 0, 0],
        [0, 0, 0, 0],
    ]
    solve_latin_square(puzzle)
