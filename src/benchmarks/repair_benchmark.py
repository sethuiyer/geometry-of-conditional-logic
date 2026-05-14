#!/usr/bin/env python3
"""
Incremental Repair Benchmark
==============================
Core claim: repair is faster than restart because CRT jumps preserve
commitments and localize disturbance.

Tests:
  1. Solve a puzzle from scratch (baseline)
  2. Perturb the solved state (change k cells)
  3. Repair by re-running solver with remaining cells locked
  4. Measure: repair time, repair radius, v_R, backtracks

The framework's thesis is that repair time << solve time for small
perturbations, because the CRT shield preserves most of the state.
"""

import sys
import time
import random
from copy import deepcopy

sys.path.insert(0, "src")
from src.domains.sudoku.hierarchical import (
    ConstraintGroup, create_groups, try_place, solve, print_board, get_box_id
)


# ─────────────────────────────────────────────
# Solve a puzzle and return the groups + empty list
# ─────────────────────────────────────────────

def solve_puzzle(puzzle):
    """Returns (groups, empty_cells) or None."""
    groups = create_groups()
    empty = []
    for r in range(9):
        for c in range(9):
            if puzzle[r][c] != 0:
                if not try_place(r, c, puzzle[r][c], groups):
                    return None
            else:
                empty.append((r, c))
    if solve(groups, empty):
        return groups, empty
    return None


def board_from_groups(groups):
    return [[groups["row"][r].get_value(c) for c in range(9)] for r in range(9)]


# ─────────────────────────────────────────────
# Repair benchmark
# ─────────────────────────────────────────────

def repair_after_perturbation(groups, empty_cells, perturbations):
    """
    Apply perturbations and re-solve.  The solver naturally tries
    committed cells first (they go into the empty list in priority
    order).  The CRT shield preserves whatever doesn't need to change.

    Returns:
      success, repair_time, repair_radius, preserved_count, backtracks
    """
    original_board = board_from_groups(groups)

    # Build the perturbed board
    perturbed = [row[:] for row in original_board]
    for r, c, new_val in perturbations:
        perturbed[r][c] = new_val

    # Identify committed cells: unperturbed cells with non-zero values
    perturbed_set = set((r, c) for r, c, _ in perturbations)
    committed_order = []
    for r in range(9):
        for c in range(9):
            v = original_board[r][c]
            if (r, c) not in perturbed_set and v != 0:
                committed_order.append((r, c, v))

    # Build fresh groups and place committed cells.
    # If a committed cell conflicts due to perturbation, it goes to empty.
    new_groups = create_groups()
    still_committed = set()
    for r, c, v in committed_order:
        if try_place(r, c, v, new_groups):
            still_committed.add((r, c))

    # Build empty list: first, any cell not yet placed
    new_empty = []
    for r in range(9):
        for c in range(9):
            v = perturbed[r][c]
            if (r, c) in still_committed:
                continue
            # Try to place the perturbed value
            if v != 0:
                if not try_place(r, c, v, new_groups):
                    new_empty.append((r, c))
            else:
                new_empty.append((r, c))

    # Monkey-patch solve to count calls
    import src.domains.sudoku.hierarchical as mod
    original_solve = mod.solve
    call_count = [0]

    def solve_with_count(grps, empty):
        call_count[0] += 1
        return src.domains.sudoku.hierarchical.solve(grps, empty)

    t_start = time.time()
    success = solve(new_groups, new_empty)
    t_repair = time.time() - t_start

    if not success:
        return False, t_repair, None, None, call_count[0]

    repaired_board = board_from_groups(new_groups)
    repair_radius = sum(
        1 for r in range(9) for c in range(9)
        if original_board[r][c] != repaired_board[r][c]
    )
    preserved = 81 - repair_radius

    return success, t_repair, repair_radius, preserved, call_count[0]


# ─────────────────────────────────────────────
# Main benchmark
# ─────────────────────────────────────────────

def run_benchmark(puzzle, name):
    print(f"\n{'='*65}")
    print(f"  Repair Benchmark: {name}")
    print(f"{'='*65}")

    # Solve from scratch
    t0 = time.time()
    result = solve_puzzle(puzzle)
    t_solve = time.time() - t0
    if result is None:
        print("  ✗ Could not solve from scratch")
        return

    groups, empty_cells = result
    solved_board = board_from_groups(groups)

    print(f"  Solve from scratch: {t_solve:.4f}s, {len(empty_cells)} empty cells")
    print(f"  Clues: {81 - len(empty_cells)}")

    # Test perturbations of increasing size
    for k in [1, 2, 3, 5, 10, 20]:
        # Pick k random cells that were empty (not clues)
        cells = random.sample(empty_cells, min(k, len(empty_cells)))
        perturbations = []
        for r, c in cells:
            # Change to a different valid value
            old_val = solved_board[r][c]
            new_val = ((old_val) % 9) + 1  # guaranteed different
            perturbations.append((r, c, new_val))

        success, t_repair, radius, v_R, bt_count = repair_after_perturbation(
            groups, empty_cells, perturbations
        )

        if success:
            speedup = t_solve / t_repair if t_repair > 0 else float('inf')
            preserved_pct = (81 - radius) / 81 * 100 if radius is not None else 0
            print(f"  k={k:2d} perturb  repair={t_repair:.4f}s  "
                  f"speedup={speedup:.1f}x  radius={radius}  "
                  f"preserved={preserved_pct:.0f}%  backtracks={bt_count}")
        else:
            print(f"  k={k:2d} perturb  ✗ repair failed")


if __name__ == "__main__":
    random.seed(42)

    # AI Escargot
    escargot = [
        [1, 0, 0, 0, 0, 7, 0, 9, 0],
        [0, 3, 0, 0, 2, 0, 0, 0, 8],
        [0, 0, 9, 6, 0, 0, 5, 0, 0],
        [0, 0, 5, 3, 0, 0, 9, 0, 0],
        [0, 1, 0, 0, 8, 0, 0, 0, 2],
        [6, 0, 0, 0, 0, 4, 0, 0, 0],
        [3, 0, 0, 0, 0, 0, 0, 1, 0],
        [0, 4, 0, 0, 0, 0, 0, 0, 7],
        [0, 0, 7, 0, 0, 0, 3, 0, 0],
    ]

    # Easy puzzle
    easy = [
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

    run_benchmark(escargot, "AI Escargot (hardest)")
    run_benchmark(easy, "Easy puzzle")
