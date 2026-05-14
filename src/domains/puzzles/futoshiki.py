#!/usr/bin/env python3
"""
Hierarchical CRT Futoshiki Solver
====================================
n×n grid with row/col permutation constraints (like Latin squares)
plus inequality constraints (< or >) between adjacent cells.

Constraint groups: n rows + n columns = 2n CRT microspaces.
Inequalities: validated separately after each CRT jump.
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


def get_value(r, c, groups):
    return groups["row"][r].get_value(c)


# ─────────────────────────────────────────────
# Inequality checking
# ─────────────────────────────────────────────

def check_inequalities(groups, n, inequalities):
    """inequalities: list of (r1,c1, r2,c2, direction)
    direction: '<' means val(r1,c1) < val(r2,c2), '>' means >"""
    for r1, c1, r2, c2, direction in inequalities:
        v1 = get_value(r1, c1, groups)
        v2 = get_value(r2, c2, groups)
        if v1 == 0 or v2 == 0:
            continue
        if direction == '<' and not (v1 < v2):
            return False
        if direction == '>' and not (v1 > v2):
            return False
    return True


# ─────────────────────────────────────────────
# Placement with inequality validation
# ─────────────────────────────────────────────

def try_place(r, c, v, groups, n, inequalities):
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
    if not check_inequalities(groups, n, inequalities):
        row_g.reset_to(snap_r)
        col_g.reset_to(snap_c)
        return False
    return True


def print_grid(groups, n, inequalities=None):
    for r in range(n):
        row_str = ""
        for c in range(n):
            val = get_value(r, c, groups)
            row_str += str(val) if val != 0 else "."
            if c < n - 1:
                # Check horizontal inequality
                ineq = ""
                if inequalities:
                    for r1,c1,r2,c2,d in inequalities:
                        if (r1,c1,r2,c2) == (r,c,r,c+1):
                            ineq = " "+d+" "
                        elif (r1,c1,r2,c2) == (r,c+1,r,c):
                            ineq = " "+(">" if d == "<" else "<")+" "
                row_str += ineq or "   "
        print(row_str)
        if r < n - 1:
            # Check vertical inequalities
            vert_str = ""
            for c in range(n):
                ineq = ""
                if inequalities:
                    for r1,c1,r2,c2,d in inequalities:
                        if (r1,c1,r2,c2) == (r,c,r+1,c):
                            ineq = d
                        elif (r1,c1,r2,c2) == (r+1,c,r,c):
                            ineq = ">" if d == "<" else "<"
                vert_str += " " + ineq + "   " if ineq else "     "
            if vert_str.strip():
                print(vert_str)


def solve(groups, empty_cells, n, inequalities):
    if not empty_cells:
        return True
    r, c = empty_cells[0]
    rest = empty_cells[1:]
    for v in range(1, n + 1):
        snap_r = deepcopy(groups["row"][r])
        snap_c = deepcopy(groups["col"][c])
        if try_place(r, c, v, groups, n, inequalities):
            if solve(groups, rest, n, inequalities):
                return True
            groups["row"][r].reset_to(snap_r)
            groups["col"][c].reset_to(snap_c)
    return False


def solve_futoshiki(puzzle, inequalities):
    n = len(puzzle)
    groups = create_groups(n)
    empty = []
    for r in range(n):
        for c in range(n):
            if puzzle[r][c] != 0:
                if not try_place(r, c, puzzle[r][c], groups, n, inequalities):
                    print(f"Conflict at ({r},{c})")
                    return None
            else:
                empty.append((r, c))
    print("Initial:")
    print_grid(groups, n, inequalities)
    print()
    if solve(groups, empty, n, inequalities):
        print("Solved:")
        print_grid(groups, n, inequalities)
        return groups
    print("No solution")
    return None


if __name__ == "__main__":
    # 5×5 Futoshiki with inequalities
    n = 5
    puzzle = [
        [0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0],
    ]
    # inequalities: (r1,c1, r2,c2, direction) meaning val(r1,c1) < or > val(r2,c2)
    inequalities = [
        (0,0, 0,1, '<'),  # top-left corner: left < right
        (1,0, 1,1, '>'),  # row 1: left > right
        (3,2, 4,2, '<'),  # col 2: row 3 < row 4
        (2,3, 2,4, '>'),  # row 2: col 3 > col 4
        (0,4, 1,4, '<'),  # col 4: row 0 < row 1
    ]
    solve_futoshiki(puzzle, inequalities)
