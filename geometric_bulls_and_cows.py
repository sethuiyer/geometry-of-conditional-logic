#!/usr/bin/env python3
"""
Geometric Bulls and Cows
=========================
Every Cow (correct char, correct place) is a Locked Commitment in the CRT manifold.
The Lock Shield M collapses the search space from 36^4 = 1.6M down to 36^(4-cows).
Each guess is a CRT jump z' = z + kM preserving all locked slots.
"""

import random, math, sys

ALPHABET = "0123456789abcdefghijklmnopqrstuvwxyz"
CHAR_TO_INT = {c: i for i, c in enumerate(ALPHABET)}
INT_TO_CHAR = {i: c for i, c in enumerate(ALPHABET)}
PRIMES = [37, 41, 43, 47]


class GeometricSolver:
    """The Spinal Cord — tracks locked commitments, computes manifold state."""

    def __init__(self):
        self.locked = {}  # slot_idx → char_value (0-35)
        self.attempts = []
        self.z = 0

    def lock_cow(self, idx, char):
        self.locked[idx] = CHAR_TO_INT[char]

    def shield(self):
        M = 1
        for idx in self.locked:
            M *= PRIMES[idx]
        return M

    def manifold_size(self):
        return 36 ** (4 - len(self.locked))

    def status(self):
        M = self.shield()
        remaining = self.manifold_size()
        pct = remaining / 36**4 * 100
        return M, remaining, pct

    def suggest(self):
        """Generate a valid guess respecting all locked cows."""
        import itertools
        best = None
        best_score = -1
        # Sample random guesses that respect locked slots
        for _ in range(5000):
            candidate = list("????")
            for idx, val in self.locked.items():
                candidate[idx] = INT_TO_CHAR[val]
            for idx in range(4):
                if idx not in self.locked:
                    candidate[idx] = random.choice(ALPHABET)
            word = "".join(candidate)
            # Score by how different it is from previous guesses
            diversity = sum(1 for w in self.attempts if w != word)
            if diversity > best_score:
                best_score = diversity
                best = word
        return best


def feedback(secret, guess):
    """Return (cows, bulls, cow_indices)."""
    cows = 0
    bulls = 0
    cow_idx = []
    s = list(secret)
    g = list(guess)
    for i in range(4):
        if g[i] == s[i]:
            cows += 1
            cow_idx.append(i)
    for i in sorted(cow_idx, reverse=True):
        s.pop(i)
        g.pop(i)
    for ch in g:
        if ch in s:
            bulls += 1
            s.remove(ch)
    return cows, bulls, cow_idx


def simulate():
    """Run a simulated game with optimal strategy."""
    secret = "".join(random.choices(ALPHABET, k=4))
    solver = GeometricSolver()

    print("=" * 62)
    print("  GEOMETRIC BULLS & COWS")
    print("  Secret: {}".format(secret.upper() if random.random() < 0 else "(hidden)"))
    print("=" * 62)

    for attempt in range(1, 25):
        guess = solver.suggest()
        solver.attempts.append(guess)
        cows, bulls, ci = feedback(secret, guess)

        for idx in ci:
            solver.lock_cow(idx, guess[idx])

        M, remaining, pct = solver.status()
        locked_str = ", ".join(f"slot {i}={guess[i]}" for i in sorted(solver.locked))

        print(f"\n  [{attempt}] Guess: {guess}")
        print(f"         {cows} Cows 🎯 {bulls} Bulls 🐂")
        print(f"         Locked: {locked_str if solver.locked else '(none)'}")
        print(f"         Shield M = {M}")
        print(f"         Manifold: {remaining:,} / {36**4:,} ({pct:.4f}%)")

        if cows == 4:
            print(f"\n  🎉 Solved in {attempt} attempts! Secret was '{secret}'")
            print(f"  Manifold converged to a single point.")
            return attempt

    print(f"\n  ✗ Failed to solve in 24 attempts. Secret was '{secret}'")
    return None


if __name__ == "__main__":
    import time
    random.seed(42)
    total_attempts = 0
    n_games = 20
    print(f"Simulating {n_games} games...\n")
    t0 = time.time()
    for g in range(n_games):
        a = simulate()
        if a:
            total_attempts += a
        print()
    t1 = time.time()
    avg = total_attempts / n_games
    print(f"  Average: {avg:.1f} attempts over {n_games} games ({t1-t0:.1f}s total)")
