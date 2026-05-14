"""
Neuro-Symbolic Sudoku: NN proposes, p-adic valuation guides, CRT validates
===========================================================================

Data generation: standard fast backtracking solver generates optimal move traces.
Each move is annotated with its p-adic valuation (v_R), measuring how many
commitment layers are preserved.

The NN learns to predict which (cell, value) the optimal solver chooses,
given the current board.  The v_R acts as an auxiliary training signal
(weighting the loss by preserved depth).

Inference: NN proposes top-k moves, CRT engine validates and executes.
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
import numpy as np
import math
import random
import time
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from src.domains.sudoku.padic import (
    CELL_PRIMES, crt_encode, crt_decode, crt_jump, repair_valuation,
    board_from_z, z_from_board, is_valid, legal_values
)

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print(f"Device: {device}")

# ─────────────────────────────────────────────
# 1. Standard fast backtracking solver
# ─────────────────────────────────────────────

def _solve_standard(board):
    """Fast standard backtracking.  Mutates board in place.  Returns True/False."""
    for r in range(9):
        for c in range(9):
            if board[r][c] == 0:
                vals = list(range(1, 10))
                random.shuffle(vals)
                for v in vals:
                    board[r][c] = v
                    if _is_valid_placement(board, r, c) and _solve_standard(board):
                        return True
                    board[r][c] = 0
                return False
    return True


def _is_valid_placement(board, r, c):
    v = board[r][c]
    for cc in range(9):
        if cc != c and board[r][cc] == v:
            return False
    for rr in range(9):
        if rr != r and board[rr][c] == v:
            return False
    br, bc = r // 3, c // 3
    for rr in range(br * 3, br * 3 + 3):
        for cc in range(bc * 3, bc * 3 + 3):
            if (rr != r or cc != c) and board[rr][cc] == v:
                return False
    return True


# ─────────────────────────────────────────────
# 2. Puzzle + trace generation
# ─────────────────────────────────────────────

def _fill_solved(board):
    """Generate a solved board."""
    for r in range(9):
        for c in range(9):
            if board[r][c] == 0:
                vals = list(range(1, 10))
                random.shuffle(vals)
                for v in vals:
                    board[r][c] = v
                    if _is_valid_placement(board, r, c) and _fill_solved(board):
                        return True
                    board[r][c] = 0
                return False
    return True


SOLVED_CACHE = []


def _get_solved():
    if not SOLVED_CACHE:
        for _ in range(10):
            b = [[0] * 9 for _ in range(9)]
            _fill_solved(b)
            SOLVED_CACHE.append([row[:] for row in b])
    return random.choice(SOLVED_CACHE)


def random_puzzle(num_clues=24):
    solved = _get_solved()
    puzzle = [row[:] for row in solved]
    cells = list(range(81))
    random.shuffle(cells)
    for i in range(81 - num_clues):
        r, c = divmod(cells[i], 9)
        puzzle[r][c] = 0
    return puzzle, solved


def generate_traces(puzzle, solved):
    """
    Generate training traces by replaying the optimal solution.
    Returns list of (board_tensor, target_729, v_R).
    """
    board = [row[:] for row in puzzle]
    clue_mask = [puzzle[r][c] != 0 for r in range(9) for c in range(9)]
    traces = []

    # Determine commitment order once (clues first, then most-constrained-first)
    commit_order = _commitment_order(puzzle)

    for depth, ci in enumerate(commit_order):
        r, c = divmod(ci, 9)
        if clue_mask[ci]:
            continue
        target_val = solved[r][c]

        # Compute v_R for this move
        locked = [i for i in range(81) if clue_mask[i] or board[i // 9][i % 9] != 0]
        z = z_from_board(board)
        z_next = crt_jump(z, ci, target_val, locked, CELL_PRIMES)
        v = repair_valuation(z, z_next, [CELL_PRIMES[i] for i in commit_order])

        # Save state before the move
        tensor = board_to_tensor(board)
        target_flat = ci * 9 + (target_val - 1)
        traces.append((tensor, target_flat, v))

        # Apply move
        board[r][c] = target_val

    return traces


def _commitment_order(puzzle):
    """Clues first, then cells sorted by legal-move count ascending."""
    clue_mask = [puzzle[r][c] != 0 for r in range(9) for c in range(9)]
    clues = [i for i in range(81) if clue_mask[i]]
    non_clues = [i for i in range(81) if not clue_mask[i]]
    board = [row[:] for row in puzzle]

    def legal_count(idx):
        r, c = divmod(idx, 9)
        return len(legal_values(board, r, c))

    non_clues.sort(key=legal_count)
    return clues + non_clues


def board_to_tensor(board):
    """9×9 board → 9×9×10 tensor (9 value channels + 1 clue mask)."""
    t = np.zeros((9, 9, 10), dtype=np.float32)
    for r in range(9):
        for c in range(9):
            v = board[r][c]
            if 1 <= v <= 9:
                t[r, c, v - 1] = 1.0
    return t


# ─────────────────────────────────────────────
# 3. Dataset
# ─────────────────────────────────────────────

class SudokuTraceDataset(Dataset):
    def __init__(self, traces):
        arr = np.array([t[0] for t in traces], dtype=np.float32)
        self.X = torch.FloatTensor(arr)
        self.y = torch.LongTensor([t[1] for t in traces])
        # Use v_R as weight (how many layers preserved), normalized
        max_v = max(t[2] for t in traces) if traces else 1
        self.weights = torch.FloatTensor([(1.0 + t[2]) / (1.0 + max_v) for t in traces])

    def __len__(self):
        return len(self.y)

    def __getitem__(self, idx):
        return self.X[idx], self.y[idx], self.weights[idx]


# ─────────────────────────────────────────────
# 4. Neural network
# ─────────────────────────────────────────────

class ResBlock(nn.Module):
    def __init__(self, channels):
        super().__init__()
        self.conv1 = nn.Conv2d(channels, channels, 3, padding=1)
        self.bn1 = nn.BatchNorm2d(channels)
        self.conv2 = nn.Conv2d(channels, channels, 3, padding=1)
        self.bn2 = nn.BatchNorm2d(channels)

    def forward(self, x):
        residual = x
        x = F.relu(self.bn1(self.conv1(x)))
        x = self.bn2(self.conv2(x))
        x = F.relu(x + residual)
        return x


class SudokuPolicyNet(nn.Module):
    """Predicts which (cell, value) to place next.  10→64→729."""

    def __init__(self, channels=64, blocks=4):
        super().__init__()
        self.entry = nn.Sequential(
            nn.Conv2d(10, channels, 3, padding=1),
            nn.BatchNorm2d(channels),
            nn.ReLU(),
        )
        self.res_blocks = nn.Sequential(*[ResBlock(channels) for _ in range(blocks)])
        self.policy_head = nn.Sequential(
            nn.Conv2d(channels, 32, 1),
            nn.BatchNorm2d(32),
            nn.ReLU(),
            nn.Flatten(),
            nn.Linear(32 * 9 * 9, 729),
        )

    def forward(self, x):
        x = self.entry(x)
        x = self.res_blocks(x)
        return self.policy_head(x)


# ─────────────────────────────────────────────
# 5. Training
# ─────────────────────────────────────────────

def generate_dataset(num_puzzles=100, traces_per=30):
    all_traces = []
    t_start = time.time()
    for i in range(num_puzzles):
        puzzle, solved = random_puzzle(random.randint(22, 27))
        traces = generate_traces(puzzle, solved)
        all_traces.extend(traces[:traces_per])
        if (i + 1) % 20 == 0:
            elapsed = time.time() - t_start
            print(f"  [{i+1}/{num_puzzles}] {len(all_traces)} traces ({elapsed:.1f}s)")
    return all_traces


def train(model, dataset, epochs=8, batch_size=64, lr=3e-3):
    loader = DataLoader(dataset, batch_size=batch_size, shuffle=True)
    optimizer = optim.Adam(model.parameters(), lr=lr)
    scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, epochs)

    for epoch in range(epochs):
        total_loss = 0.0
        total_acc = 0.0
        n = 0
        for X, y, w in loader:
            X = X.permute(0, 3, 1, 2).to(device)  # (B,10,9,9)
            y = y.to(device)
            w = w.to(device)
            logits = model(X)
            loss = F.cross_entropy(logits, y, reduction='none')
            loss = (loss * w).mean()
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()

            acc = (logits.argmax(-1) == y).float().mean()
            total_loss += loss.item()
            total_acc += acc.item()
            n += 1

        scheduler.step()
        print(f"  Epoch {epoch+1}: loss={total_loss/n:.4f}  acc={total_acc/n:.4f}")


# ─────────────────────────────────────────────
# 6. NN-guided inference
# ─────────────────────────────────────────────

class NNGuidedSolver:
    def __init__(self, model, puzzle, beam_width=5):
        self.model = model
        self.puzzle = [row[:] for row in puzzle]
        self.model.eval()
        self.beam_width = beam_width
        self.nn_calls = 0

    def solve(self, max_steps=500):
        board = [row[:] for row in self.puzzle]
        return self._backtrack(board, 0, max_steps)

    def _get_nn_candidates(self, board):
        """Return top-k (prob, cell_idx, value) proposals from NN."""
        tensor = board_to_tensor(board)
        x = torch.FloatTensor(tensor).unsqueeze(0).permute(0, 3, 1, 2).to(device)
        with torch.no_grad():
            self.nn_calls += 1
            logits = self.model(x)[0]
        probs = F.softmax(logits, dim=0)
        candidates = []
        for flat_idx in probs.argsort(descending=True):
            ci = flat_idx.item() // 9
            val = flat_idx.item() % 9 + 1
            r, c = divmod(ci, 9)
            if board[r][c] != 0:
                continue
            if val not in legal_values(board, r, c):
                continue
            candidates.append((probs[flat_idx].item(), ci, val))
            if len(candidates) >= self.beam_width:
                break
        return candidates

    def _backtrack(self, board, depth, max_steps):
        if depth > max_steps:
            return None
        if is_valid(board):
            return board

        candidates = self._get_nn_candidates(board)
        if not candidates:
            return None

        for prob, ci, val in candidates:
            r, c = divmod(ci, 9)
            board[r][c] = val
            result = self._backtrack(board, depth + 1, max_steps)
            if result is not None:
                return result
            board[r][c] = 0

        return None

# ─────────────────────────────────────────────
# 7. Main
# ─────────────────────────────────────────────

if __name__ == "__main__":
    seed = 42
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)

    # Generate data
    print("\nGenerating training data...")
    traces = generate_dataset(num_puzzles=80, traces_per=30)
    print(f"Total: {len(traces)} traces")

    dataset = SudokuTraceDataset(traces)
    print(f"Dataset size: {len(dataset)}")

    # Build model
    model = SudokuPolicyNet(channels=64, blocks=4).to(device)
    n_params = sum(p.numel() for p in model.parameters())
    print(f"Parameters: {n_params:,}")

    # Train
    print("\nTraining...")
    train(model, dataset, epochs=8, batch_size=64, lr=3e-3)

    torch.save(model.state_dict(), "/tmp/padic_sudoku_nn.pt")
    print("\nModel saved to /tmp/padic_sudoku_nn.pt")

    # Evaluate
    print("\nEvaluating on 20 test puzzles...")
    nn_wins = 0
    for i in range(20):
        puzzle, solved = random_puzzle(random.randint(22, 27))
        solver = NNGuidedSolver(model, puzzle, beam_width=3)
        result = solver.solve(max_steps=162)
        if result is not None and is_valid(result):
            nn_wins += 1
        if (i + 1) % 5 == 0:
            print(f"  {i+1}/20: {nn_wins}/{i+1} = {nn_wins/(i+1)*100:.0f}%")

    print(f"\nNN solve rate: {nn_wins}/20 = {nn_wins*5}%")
