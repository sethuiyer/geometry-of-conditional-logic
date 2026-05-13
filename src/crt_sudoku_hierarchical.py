#!/usr/bin/env python3
"""
Hierarchical CRT Sudoku Solver
Distributed exact commitment over overlapping row/col/box manifolds
Each group = its own small CRT microspace (9 primes)
Jumps are local, exact, and preserve locked residues inside the group
"""

from copy import deepcopy
import sys

# 9 small primes > 9 for each local group (same set reused for simplicity)
PRIMES = [11, 13, 17, 19, 23, 29, 31, 37, 41]

def mod_inverse(a, m):
    return pow(a, -1, m)

class ConstraintGroup:
    """One local CRT manifold (row, col or box)"""
    def __init__(self, name):
        self.name = name
        self.primes = PRIMES[:]
        self.z = 0
        self.residues = [0] * 9
        self.locked = set()

    def jump(self, pos, val):
        """Exact residue-preserving jump inside this group only"""
        if pos in self.locked:
            return self.z if self.residues[pos] == val else None

        p_target = self.primes[pos]
        solved_primes = [self.primes[p] for p in self.locked]
        M = 1
        for p in solved_primes:
            M *= p

        if M == 1:
            new_z = val
        else:
            diff = (val - self.z) % p_target
            k = (diff * mod_inverse(M, p_target)) % p_target
            new_z = self.z + k * M

        # commit
        self.z = new_z
        self.residues[pos] = val
        self.locked.add(pos)
        return new_z

    def is_valid(self):
        """Check no duplicate values among *placed* cells (0 = empty is allowed)"""
        seen = {}
        for i in range(9):
            v = self.residues[i]
            if v == 0:
                continue  # empty slot is fine
            if v < 1 or v > 9:
                return False
            if v in seen:
                return False
            seen[v] = i
        return True

    def get_value(self, pos):
        return self.residues[pos]

    def reset_to(self, other):
        """Rollback helper"""
        self.z = other.z
        self.residues = other.residues[:]
        self.locked = other.locked.copy()


def get_box_id(r, c):
    return (r // 3) * 3 + (c // 3)


def create_groups():
    rows = [ConstraintGroup(f"row{r}") for r in range(9)]
    cols = [ConstraintGroup(f"col{c}") for c in range(9)]
    boxes = [ConstraintGroup(f"box{b}") for b in range(9)]
    return {"row": rows, "col": cols, "box": boxes}


def try_place(r, c, v, groups):
    """Triple synchronized jump + validation. 
    On any failure, fully rolls back and returns False.
    On success, leaves all three groups updated and returns True.
    Caller should snapshot before calling for backtracking."""
    row_g = groups["row"][r]
    col_g = groups["col"][c]
    box_g = groups["box"][get_box_id(r, c)]

    row_pos = c
    col_pos = r
    box_pos = (r % 3) * 3 + (c % 3)

    snap_row = deepcopy(row_g)
    snap_col = deepcopy(col_g)
    snap_box = deepcopy(box_g)

    # Row jump
    if row_g.jump(row_pos, v) is None or not row_g.is_valid():
        row_g.reset_to(snap_row)
        return False

    # Col jump
    if col_g.jump(col_pos, v) is None or not col_g.is_valid():
        row_g.reset_to(snap_row)
        col_g.reset_to(snap_col)
        return False

    # Box jump
    if box_g.jump(box_pos, v) is None or not box_g.is_valid():
        row_g.reset_to(snap_row)
        col_g.reset_to(snap_col)
        box_g.reset_to(snap_box)
        return False

    return True


def print_board(groups):
    print("\n+-------+-------+-------+")
    for r in range(9):
        row_str = "| "
        for c in range(9):
            # Read value from row group (any group works once consistent)
            val = groups["row"][r].get_value(c)
            row_str += str(val) + " "
            if c % 3 == 2:
                row_str += "| "
        print(row_str)
        if r % 3 == 2:
            print("+-------+-------+-------+")
    print()


def solve(groups, empty_cells):
    if not empty_cells:
        return True

    r, c = empty_cells[0]
    rest = empty_cells[1:]

    for v in range(1, 10):
        # Snapshot all three groups before attempt
        row_g = groups["row"][r]
        col_g = groups["col"][c]
        box_g = groups["box"][get_box_id(r, c)]

        snap_row = deepcopy(row_g)
        snap_col = deepcopy(col_g)
        snap_box = deepcopy(box_g)

        if try_place(r, c, v, groups):
            if solve(groups, rest):
                return True
            # Backtrack: restore the three groups
            row_g.reset_to(snap_row)
            col_g.reset_to(snap_col)
            box_g.reset_to(snap_box)

    return False


def solve_sudoku(puzzle):
    groups = create_groups()

    empty_cells = []
    for r in range(9):
        for c in range(9):
            if puzzle[r][c] != 0:
                if not try_place(r, c, puzzle[r][c], groups):
                    print(f"Initial conflict at ({r},{c}) with value {puzzle[r][c]}")
                    return None
            else:
                empty_cells.append((r, c))

    print("Initial board (givens locked):")
    print_board(groups)

    if solve(groups, empty_cells):
        print("\n✅ Solved!")
        print_board(groups)
        return groups
    else:
        print("\n❌ No solution found (or search exhausted)")
        return None


# ==================== DEMO ====================
if __name__ == "__main__":
    # Classic easy Sudoku (known solvable)
    puzzle = [
        [5, 3, 0, 0, 7, 0, 0, 0, 0],
        [6, 0, 0, 1, 9, 5, 0, 0, 0],
        [0, 9, 8, 0, 0, 0, 0, 6, 0],
        [8, 0, 0, 0, 6, 0, 0, 0, 3],
        [4, 0, 0, 8, 0, 3, 0, 0, 1],
        [7, 0, 0, 0, 2, 0, 0, 0, 6],
        [0, 6, 0, 0, 0, 0, 2, 8, 0],
        [0, 0, 0, 4, 1, 9, 0, 0, 5],
        [0, 0, 0, 0, 8, 0, 0, 7, 9],
    ]

    print("=== Hierarchical CRT Sudoku Solver ===")
    print("Distributed exact jumps over row/col/box manifolds\n")

    solve_sudoku(puzzle)
