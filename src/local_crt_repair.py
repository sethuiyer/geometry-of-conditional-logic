#!/usr/bin/env python3
"""
Local CRT Repair Engine
General-purpose residue-preserving local state transitions.

Core idea:
- Each group = one local constraint manifold (row, col, box, lane, machine, etc.)
- transition(pos, val) = exact jump that sets one residue while preserving all locked ones
- undo() = O(1) reversible delta (mutation stack)
- z = lazy arithmetic witness / commitment certificate (not the operational state)

This is the distilled primitive that survived the entire research arc.
"""

from typing import List, Optional, Callable


def default_primes(n: int) -> List[int]:
    """Small primes > max expected value (adjust as needed)"""
    base = [11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47, 53, 59, 61, 67, 71, 73, 79, 83, 89]
    if n > len(base):
        raise ValueError("Need more primes — extend the list or generate dynamically")
    return base[:n]


class LocalCRTGroup:
    """
    One local constraint group with exact residue-preserving transitions.

    Operational layer: residues + locks + reversible history
    Witness layer: lazy z (CRT coordinate) as algebraic certificate
    """

    def __init__(self, name: str, size: int, primes: Optional[List[int]] = None):
        self.name = name
        self.size = size
        self.primes = primes or default_primes(size)
        self.residues: List[int] = [0] * size
        self.locked: set = set()
        self.z: int = 0
        self.history: List[tuple] = []   # (pos, old_val, old_z)
        self.dirty: bool = False         # z needs recompute?

    # ===================== CORE PRIMITIVE =====================
    def transition(self, pos: int, val: int) -> Optional[int]:
        """
        Residue-preserving local state transition.
        Sets residues[pos] = val while exactly preserving all previously locked residues.
        Returns new z on success, None on conflict.
        """
        if pos < 0 or pos >= self.size:
            return None
        if pos in self.locked and self.residues[pos] != val:
            return None

        old_val = self.residues[pos]
        old_z = self.z

        p_target = self.primes[pos]
        solved = [self.primes[p] for p in self.locked]

        if not solved:
            new_z = val
        else:
            M = 1
            for p in solved:
                M *= p
            diff = (val - self.z) % p_target
            k = (diff * pow(M, -1, p_target)) % p_target
            new_z = self.z + k * M

        # apply
        self.residues[pos] = val
        self.z = new_z
        if pos not in self.locked:
            self.locked.add(pos)
        self.history.append((pos, old_val, old_z))
        self.dirty = True
        return new_z

    def undo(self) -> bool:
        """O(1) reversible rollback. Returns True if something was undone."""
        if not self.history:
            return False
        pos, old_val, old_z = self.history.pop()
        self.residues[pos] = old_val
        self.z = old_z
        if old_val == 0:
            self.locked.discard(pos)
        self.dirty = True
        return True

    # ===================== VALIDITY & WITNESS =====================
    def is_valid(self, validity_fn: Optional[Callable] = None) -> bool:
        """
        Check local validity.
        Default: no duplicate non-zero values (Sudoku-style).
        Pass custom validity_fn for other domains.
        """
        if validity_fn:
            return validity_fn(self.residues, self.locked)

        # default: unique non-zero values
        seen = {}
        for i in range(self.size):
            v = self.residues[i]
            if v == 0:
                continue
            if v in seen:
                return False
            seen[v] = i
        return True

    def get_witness(self, force_recompute: bool = False) -> int:
        """
        Return the current CRT coordinate (algebraic witness).
        Lazy by default — only recomputes when dirty.
        """
        if not self.dirty and not force_recompute:
            return self.z

        # Recompute z from current residues (for safety / export)
        z = 0
        M = 1
        for i in range(self.size):
            if self.residues[i] == 0:
                continue
            p = self.primes[i]
            diff = (self.residues[i] - z) % p
            k = (diff * pow(M, -1, p)) % p
            z += k * M
            M *= p
        self.z = z
        self.dirty = False
        return z

    # ===================== UTILITIES =====================
    def __repr__(self):
        return f"LocalCRTGroup({self.name}, size={self.size}, locked={len(self.locked)})"

    def snapshot(self) -> int:
        """Return a cheap checkpoint id (current history length)"""
        return len(self.history)

    def rollback_to(self, checkpoint: int):
        """Rollback to a previous checkpoint id"""
        while len(self.history) > checkpoint:
            self.undo()


# ===================== EXAMPLE: SUDOKU ON TOP =====================
def sudoku_validity(residues, locked):
    """Sudoku-style: unique non-zero values"""
    seen = {}
    for v in residues:
        if v == 0:
            continue
        if v in seen:
            return False
        seen[v] = True
    return True


def solve_sudoku_with_engine():
    """Demo: build 27 groups and solve using the general engine"""
    print("=== Local CRT Repair Engine — Sudoku Demo ===\n")

    # Create 27 groups
    groups = {
        "row": [LocalCRTGroup(f"row{r}", 9) for r in range(9)],
        "col": [LocalCRTGroup(f"col{c}", 9) for c in range(9)],
        "box": [LocalCRTGroup(f"box{b}", 9) for b in range(9)],
    }

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

    empty = []
    for r in range(9):
        for c in range(9):
            if puzzle[r][c] != 0:
                v = puzzle[r][c]
                row_g = groups["row"][r]
                col_g = groups["col"][c]
                box_g = groups["box"][(r // 3) * 3 + (c // 3)]

                if (row_g.transition(c, v) is None or
                    col_g.transition(r, v) is None or
                    box_g.transition((r % 3) * 3 + (c % 3), v) is None):
                    print(f"Conflict in initial puzzle at ({r},{c})")
                    return
            else:
                empty.append((r, c))

    print("Initial givens locked. Starting search...\n")

    def search(cells):
        if not cells:
            return True
        r, c = cells[0]
        rest = cells[1:]

        row_g = groups["row"][r]
        col_g = groups["col"][c]
        box_g = groups["box"][(r // 3) * 3 + (c // 3)]
        row_pos = c
        col_pos = r
        box_pos = (r % 3) * 3 + (c % 3)

        for v in range(1, 10):
            cp_row = row_g.snapshot()
            cp_col = col_g.snapshot()
            cp_box = box_g.snapshot()

            if (row_g.transition(row_pos, v) and
                col_g.transition(col_pos, v) and
                box_g.transition(box_pos, v) and
                row_g.is_valid(sudoku_validity) and
                col_g.is_valid(sudoku_validity) and
                box_g.is_valid(sudoku_validity)):

                if search(rest):
                    return True

            # rollback
            row_g.rollback_to(cp_row)
            col_g.rollback_to(cp_col)
            box_g.rollback_to(cp_box)

        return False

    if search(empty):
        print("Solved!\n")
        # print solution from row groups
        for r in range(9):
            row = [groups["row"][r].residues[c] for c in range(9)]
            print(" ".join(map(str, row)))
    else:
        print("No solution")


if __name__ == "__main__":
    solve_sudoku_with_engine()


# ===================== LATIN SQUARE =====================
def latin_validity(residues, locked):
    """Latin Square style: unique non-zero values"""
    seen = {}
    for v in residues:
        if v == 0:
            continue
        if v in seen:
            return False
        seen[v] = True
    return True


def solve_latin_square(order: int = 4, givens: list = None):
    """
    Solve an order×order Latin Square:
    each row and column must contain 1..order exactly once.

    groups = rows + columns only (no boxes — simpler than Sudoku)
    """
    print(f"=== Latin Square — order {order} ===\n")

    groups = {
        "row": [LocalCRTGroup(f"row{r}", order) for r in range(order)],
        "col": [LocalCRTGroup(f"col{c}", order) for c in range(order)],
    }

    if givens is None:
        givens = []

    empty = []
    for r in range(order):
        for c in range(order):
            if givens and r < len(givens) and c < len(givens[r]) and givens[r][c] != 0:
                v = givens[r][c]
                if (groups["row"][r].transition(c, v) is None or
                    groups["col"][c].transition(r, v) is None):
                    print(f"Conflict in givens at ({r},{c})")
                    return
            else:
                empty.append((r, c))

    print(f"Givens locked. {len(empty)} empty cells. Starting search...\n")

    def search(cells):
        if not cells:
            return True
        r, c = cells[0]
        rest = cells[1:]

        row_g = groups["row"][r]
        col_g = groups["col"][c]

        for v in range(1, order + 1):
            cp_row = row_g.snapshot()
            cp_col = col_g.snapshot()

            if (row_g.transition(c, v) and
                col_g.transition(r, v) and
                row_g.is_valid(latin_validity) and
                col_g.is_valid(latin_validity)):

                if search(rest):
                    return True

            row_g.rollback_to(cp_row)
            col_g.rollback_to(cp_col)

        return False

    if search(empty):
        print("Latin Square found!\n")
        for r in range(order):
            row = [groups["row"][r].residues[c] for c in range(order)]
            print(" ".join(map(str, row)))
    else:
        print("No solution")


if __name__ == "__main__":
    print("\n" + "=" * 50)
    print("LATIN SQUARE — 4×4")
    print("=" * 50)
    solve_latin_square(4)

    print("\n" + "=" * 50)
    print("LATIN SQUARE — 5×5")
    print("=" * 50)
    solve_latin_square(5)