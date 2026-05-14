#!/usr/bin/env python3
"""
CRT Sokoban Solver — Stress Test for Ultrametric Planning
===========================================================

Sokoban is fundamentally different from Sudoku:
  - Sequential planning, not constraint assignment
  - Irreversible traps (boxes in corners)
  - Dependency chains (box A before box B)
  - Spatial constraints, not permutation constraints

CRT is used here for STATE ENCODING, not constraint satisfaction.
Each cell in the warehouse gets a prime.  Residue = what occupies it.
A player move is a CRT jump that changes 2-3 residues (player movement,
optionally box push).  The shield preserves everything unchanged.

The ultrametric valuation v_R measures how much of the layout is
preserved by a move — moves that change fewer cells are "closer."

This tests whether ultrametric locality has any value for planning.

Expected result: CRT encoding works but adds overhead vs standard BFS.
The ultrametric heuristic does not help Sokoban's core difficulty
(dependency chains, deadlocks).  A useful negative result.
"""

import math
import sys
from collections import deque

# ─────────────────────────────────────────────
# Primes for cell encoding
# ─────────────────────────────────────────────

def first_n_primes(n):
    primes = []
    cand = 2
    while len(primes) < n:
        is_prime = True
        for p in primes:
            if p * p > cand:
                break
            if cand % p == 0:
                is_prime = False
                break
        if is_prime:
            primes.append(cand)
        cand += 1 if cand == 2 else 2
    return primes

# Residue encoding for cell contents
EMPTY = 0
WALL = 1
PLAYER = 2
BOX = 3
TARGET = 4
BOX_ON_TARGET = 5
PLAYER_ON_TARGET = 6


# ─────────────────────────────────────────────
# CRT helpers
# ─────────────────────────────────────────────

def crt_encode(values, moduli):
    n = len(moduli)
    v = [0] * n
    v[0] = values[0] % moduli[0]
    for i in range(1, n):
        t = values[i] % moduli[i]
        for j in range(i):
            t -= v[j] * math.prod(moduli[:j])
        inv = pow(math.prod(moduli[:i]), -1, moduli[i])
        v[i] = t * inv % moduli[i]
    z = 0
    for i in range(n):
        z += v[i] * math.prod(moduli[:i])
    return z


def crt_decode(z, moduli):
    return [z % m for m in moduli]


def crt_jump(z, changes, moduli):
    """
    Apply multiple cell changes atomically.
    changes: list of (cell_idx, new_value)
    All other cells are shielded (their residues preserved).
    """
    # Compute shield M = product of all moduli EXCEPT changed ones
    changed_indices = set(idx for idx, _ in changes)
    shielded = [i for i in range(len(moduli)) if i not in changed_indices]
    z_new = z
    for cell_idx, new_val in changes:
        M = 1
        for s in shielded:
            M *= moduli[s]
        p_t = moduli[cell_idx]
        k = ((new_val - z_new) * pow(M % p_t, -1, p_t)) % p_t
        z_new = z_new + k * M
        # After this jump, cell_idx has the new value.
        # Other cells' residues are unchanged (shielded).
    return z_new


def valuation(z1, z2, moduli):
    """v_R = number of leading matching residues (in cell order)."""
    r1 = crt_decode(z1, moduli)
    r2 = crt_decode(z2, moduli)
    v = 0
    for a, b in zip(r1, r2):
        if a == b:
            v += 1
        else:
            break
    return v


# ─────────────────────────────────────────────
# Sokoban board
# ─────────────────────────────────────────────

class Sokoban:
    """Tiny Sokoban puzzle with CRT state encoding."""

    def __init__(self, grid):
        """
        grid: list of strings.  Characters:
          ' ' = empty, '#' = wall, '@' = player, '$' = box,
          '.' = target, '*' = box on target, '+' = player on target
        """
        self.grid = [list(row) for row in grid]
        self.h = len(self.grid)
        self.w = len(self.grid[0])
        self.n_cells = self.h * self.w
        self.primes = first_n_primes(self.n_cells)

        # Parse initial state
        self.initial_residues = [EMPTY] * self.n_cells
        self.target_cells = set()
        self.box_count = 0

        for r in range(self.h):
            for c in range(self.w):
                idx = r * self.w + c
                ch = self.grid[r][c]
                if ch == '#':
                    self.initial_residues[idx] = WALL
                elif ch == '@':
                    self.initial_residues[idx] = PLAYER
                    self.player_start = (r, c)
                elif ch == '$':
                    self.initial_residues[idx] = BOX
                    self.box_count += 1
                elif ch == '.':
                    self.initial_residues[idx] = TARGET
                    self.target_cells.add(idx)
                elif ch == '*':
                    self.initial_residues[idx] = BOX_ON_TARGET
                    self.target_cells.add(idx)
                    self.box_count += 1
                elif ch == '+':
                    self.initial_residues[idx] = PLAYER_ON_TARGET
                    self.target_cells.add(idx)
                # else: empty, already 0

        self.initial_z = crt_encode(self.initial_residues, self.primes)

    def decode(self, z):
        return crt_decode(z, self.primes)

    def get_positions(self, z):
        """Return (player_pos, box_positions_set, boxes_on_target)."""
        residues = self.decode(z)
        player = None
        boxes = set()
        for idx, val in enumerate(residues):
            if val in (PLAYER, PLAYER_ON_TARGET):
                player = (idx // self.w, idx % self.w)
            if val in (BOX, BOX_ON_TARGET):
                boxes.add((idx // self.w, idx % self.w))
        return player, boxes

    def is_won(self, z):
        residues = self.decode(z)
        # Win: no box is off-target (every box is on a target)
        return not any(val == BOX for val in residues)

    def is_wall(self, r, c):
        if not (0 <= r < self.h and 0 <= c < self.w):
            return True
        return self.grid[r][c] == '#'

    def get_legal_moves(self, z):
        """Return list of (z_next, move_desc) for all legal player moves."""
        residues = self.decode(z)
        player, boxes = self.get_positions(z)
        if player is None:
            return []
        pr, pc = player
        moves = []

        for dr, dc, name in [(-1, 0, 'up'), (1, 0, 'down'), (0, -1, 'left'), (0, 1, 'right')]:
            nr, nc = pr + dr, pc + dc
            nidx = nr * self.w + nc
            if self.is_wall(nr, nc):
                continue

            current_val = residues[nidx]
            changes = []

            if current_val in (EMPTY, TARGET):
                # Player moves into empty/target cell
                # Old player position becomes empty (or target)
                old_val = residues[pr * self.w + pc]
                changes.append((pr * self.w + pc, TARGET if old_val == PLAYER_ON_TARGET else EMPTY))
                # New player position
                target_val = PLAYER_ON_TARGET if current_val == TARGET else PLAYER
                changes.append((nidx, target_val))
                z_next = crt_jump(z, changes, self.primes)
                moves.append((z_next, f"{name} ({pr},{pc})→({nr},{nc})"))

            elif current_val in (BOX, BOX_ON_TARGET):
                # Push box
                br, bc = nr + dr, nc + dc
                bidx = br * self.w + bc
                if self.is_wall(br, bc) or residues[bidx] in (BOX, BOX_ON_TARGET):
                    continue  # can't push
                # Player moves to box position
                p_old = pr * self.w + pc
                p_old_val = residues[p_old]
                changes.append((p_old, TARGET if p_old_val == PLAYER_ON_TARGET else EMPTY))
                # Box moves to new position
                was_on_target = current_val == BOX_ON_TARGET
                new_is_target = residues[bidx] == TARGET
                box_new = BOX_ON_TARGET if new_is_target else BOX
                changes.append((bidx, box_new))
                # Box vacates its old position (player stands there now)
                player_new = PLAYER_ON_TARGET if was_on_target else PLAYER
                changes.append((nidx, player_new))
                z_next = crt_jump(z, changes, self.primes)
                moves.append((z_next, f"push {name} ({pr},{pc})→({nr},{nc})→({br},{bc})"))

        return moves


# ─────────────────────────────────────────────
# Solvers
# ─────────────────────────────────────────────

def bfs_solve(sokoban, max_states=50000):
    """BFS over Sokoban states encoded as CRT coordinates."""
    start = sokoban.initial_z
    if sokoban.is_won(start):
        return [], 0

    visited = {start}
    q = deque([(start, [])])
    states_explored = 0

    while q and states_explored < max_states:
        z, path = q.popleft()
        states_explored += 1

        for z_next, desc in sokoban.get_legal_moves(z):
            if z_next in visited:
                continue
            visited.add(z_next)
            new_path = path + [desc]

            if sokoban.is_won(z_next):
                return new_path, states_explored

            q.append((z_next, new_path))

    return None, states_explored


def ultrametric_solve(sokoban, max_states=50000):
    """
    BFS with ultrametric heuristic: prefer moves with high v_R
    (preserve more of the board layout).  This is A*-ish:
    priority = -v_R (higher v_R = closer to previous state).
    """
    start = sokoban.initial_z
    if sokoban.is_won(start):
        return [], 0

    visited = {start}
    # (z, path, prev_z)
    q = deque([(start, [], start)])
    states_explored = 0

    while q and states_explored < max_states:
        z, path, prev_z = q.popleft()
        states_explored += 1

        moves = sokoban.get_legal_moves(z)
        # Score moves by v_R with previous state
        scored = []
        for z_next, desc in moves:
            if z_next in visited:
                continue
            v = valuation(z, z_next, sokoban.primes)
            scored.append((v, z_next, desc))

        # Sort by v_R descending (prefer moves that change little)
        scored.sort(reverse=True)

        for v, z_next, desc in scored:
            visited.add(z_next)
            new_path = path + [desc]

            if sokoban.is_won(z_next):
                return new_path, states_explored

            q.append((z_next, new_path, z))

    return None, states_explored


# ─────────────────────────────────────────────
# Visualization
# ─────────────────────────────────────────────

def print_state(sokoban, z, label=""):
    residues = sokoban.decode(z)
    symbols = {EMPTY: ' ', WALL: '#', PLAYER: '@', BOX: '$',
               TARGET: '.', BOX_ON_TARGET: '*', PLAYER_ON_TARGET: '+'}
    if label:
        print(label)
    for r in range(sokoban.h):
        row = ""
        for c in range(sokoban.w):
            val = residues[r * sokoban.w + c]
            row += symbols.get(val, '?')
        print("  " + row)
    print()


# ─────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────

def test_puzzle(grid, name):
    print(f"\n{'='*65}")
    print(f"  Sokoban: {name}")
    print(f"{'='*65}")

    s = Sokoban(grid)
    print_state(s, s.initial_z, "Initial:")

    # Standard BFS
    print("  Standard BFS...")
    result, explored = bfs_solve(s)
    if result:
        print(f"  ✓ Solved in {len(result)} moves ({explored} states explored)")
    else:
        print(f"  ✗ Not solved (explored {explored} states)")

    # Ultrametric BFS
    print("  Ultrametric BFS...")
    result2, explored2 = ultrametric_solve(s)
    if result2:
        print(f"  ✓ Solved in {len(result2)} moves ({explored2} states explored)")
    else:
        print(f"  ✗ Not solved (explored {explored2} states)")


if __name__ == "__main__":
    # Tiny puzzles

    # Puzzle 1: 1 box, 1 target, trivial
    micro = [
        "  ####",
        "##   #",
        "# $  #",
        "#  @.#",
        "######",
    ]

    # Puzzle 2: 2 boxes, 2 targets, simple dependency
    small = [
        "#######",
        "#     #",
        "# $ $ #",
        "#  @  #",
        "# . . #",
        "#######",
    ]

    # Puzzle 3: Corner trap — box can be pushed into corner
    corner = [
        "#####",
        "#   #",
        "# $ #",
        "# @ #",
        "# . #",
        "#####",
    ]

    for grid, name in [(micro, "Micro (1 box)"), (small, "Small (2 boxes)"), (corner, "Corner trap")]:
        test_puzzle(grid, name)
