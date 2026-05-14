#!/usr/bin/env python3
"""
Hierarchical CRT Killer Sudoku Solver
========================================
Standard 9×9 Sudoku (rows/cols/boxes) PLUS sum cages.
Each cage is a set of cells whose values must sum to a given target.

Constraint groups:
  - 9 rows (CRT microspaces, permutation)
  - 9 cols (CRT microspaces, permutation)
  - 9 boxes (CRT microspaces, permutation)
  - k cages (validator: sum of values == target)

A cell lives in 4 groups: row + col + box + (one) cage.
Placement is validated against all four.
"""

from copy import deepcopy

PRIMES = [11, 13, 17, 19, 23, 29, 31, 37, 41]

def mod_inverse(a, m):
    return pow(a, -1, m)


class ConstraintGroup:
    def __init__(self, name, primes):
        self.name = name
        self.primes = primes[:]
        self.n = len(primes)
        self.z = 0
        self.residues = [0] * self.n
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
        seen = {}
        for i in range(self.n):
            v = self.residues[i]
            if v == 0:
                continue
            if v < 1 or v > 9:
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


# ─────────────────────────────────────────────
# Cage validation
# ─────────────────────────────────────────────

class CageGroup:
    """A sum cage: set of (r,c) cells whose values must sum to target."""
    def __init__(self, name, cells, target):
        self.name = name
        self.cells = cells      # list of (r,c) tuples
        self.target = target

    def is_satisfied(self, groups):
        """Check if all cells in the cage are filled and sum to target."""
        total = 0
        for r, c in self.cells:
            v = groups["row"][r].get_value(c)
            if v == 0:
                return True  # not all filled yet — skip check
            total += v
        return total == self.target


def get_box_id(r, c):
    return (r // 3) * 3 + (c // 3)


def create_groups():
    rows = [ConstraintGroup(f"row{r}", PRIMES) for r in range(9)]
    cols = [ConstraintGroup(f"col{c}", PRIMES) for c in range(9)]
    boxes = [ConstraintGroup(f"box{b}", PRIMES) for b in range(9)]
    return {"row": rows, "col": cols, "box": boxes}


def try_place(r, c, v, groups, cages):
    row_g = groups["row"][r]
    col_g = groups["col"][c]
    box_g = groups["box"][get_box_id(r, c)]
    snap_r = deepcopy(row_g)
    snap_c = deepcopy(col_g)
    snap_b = deepcopy(box_g)

    if row_g.jump(c, v) is None or not row_g.is_valid():
        row_g.reset_to(snap_r)
        return False
    if col_g.jump(r, v) is None or not col_g.is_valid():
        row_g.reset_to(snap_r)
        col_g.reset_to(snap_c)
        return False
    if box_g.jump((r % 3) * 3 + (c % 3), v) is None or not box_g.is_valid():
        row_g.reset_to(snap_r)
        col_g.reset_to(snap_c)
        box_g.reset_to(snap_b)
        return False
    # Check cage constraints
    for cage in cages:
        if not cage.is_satisfied(groups):
            row_g.reset_to(snap_r)
            col_g.reset_to(snap_c)
            box_g.reset_to(snap_b)
            return False
    return True


def print_board(groups):
    print("+-------+-------+-------+")
    for r in range(9):
        row = "| "
        for c in range(9):
            v = groups["row"][r].get_value(c)
            row += str(v) + " "
            if c % 3 == 2:
                row += "| "
        print(row)
        if r % 3 == 2:
            print("+-------+-------+-------+")
    print()


def solve(groups, empty_cells, cages):
    if not empty_cells:
        return True
    r, c = empty_cells[0]
    rest = empty_cells[1:]
    for v in range(1, 10):
        snap_r = deepcopy(groups["row"][r])
        snap_c = deepcopy(groups["col"][c])
        snap_b = deepcopy(groups["box"][get_box_id(r, c)])
        if try_place(r, c, v, groups, cages):
            if solve(groups, rest, cages):
                return True
            groups["row"][r].reset_to(snap_r)
            groups["col"][c].reset_to(snap_c)
            groups["box"][get_box_id(r, c)].reset_to(snap_b)
    return False


def solve_killer_sudoku(puzzle, cages):
    groups = create_groups()
    empty = []
    for r in range(9):
        for c in range(9):
            if puzzle[r][c] != 0:
                if not try_place(r, c, puzzle[r][c], groups, cages):
                    print(f"Conflict at ({r},{c})")
                    return None
            else:
                empty.append((r, c))
    print("Initial:")
    print_board(groups)
    if solve(groups, empty, cages):
        print("Solved:")
        print_board(groups)
        return groups
    print("No solution")
    return None


if __name__ == "__main__":
    # Standard Sudoku puzzle with 28 clues
    puzzle = [
        [0, 0, 0, 0, 0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0, 3, 0, 8, 5],
        [0, 0, 1, 0, 2, 0, 0, 0, 0],
        [0, 0, 0, 5, 0, 7, 0, 0, 0],
        [0, 0, 4, 0, 0, 0, 1, 0, 0],
        [0, 9, 0, 0, 0, 0, 0, 0, 0],
        [5, 0, 0, 0, 0, 0, 0, 7, 3],
        [0, 0, 2, 0, 1, 0, 0, 0, 0],
        [0, 0, 0, 0, 4, 0, 0, 0, 9],
    ]
    # Killer cages: (cells, target_sum)
    cages = [
        CageGroup("cage1", [(0,0), (0,1)], 8),   # top-left 2 cells sum to 8
        CageGroup("cage2", [(0,3), (1,3)], 12),
        CageGroup("cage3", [(7,0), (8,0), (8,1)], 15),
    ]
    solve_killer_sudoku(puzzle, cages)
