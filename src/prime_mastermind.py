"""
PRIME-TOPOLOGY MASTERMIND CODEBREAKER
=====================================
The classic deduction game, solved via Riemann Manifold navigation.

RULES:
  - Secret code: 4 pegs, 6 colors (0-5)
  - After each guess, you get:
      Bulls (●): Right color, right position
      Cows  (○): Right color, wrong position
  - Goal: Crack the code in minimum guesses

PRIME ENCODING:
  Primes [7, 11, 13, 17] encode each peg position.
  z % 7  = Color at Position 0
  z % 11 = Color at Position 1
  z % 13 = Color at Position 2
  z % 17 = Color at Position 3

  Total manifold: 7 * 11 * 13 * 17 = 17,017 coordinates
  Valid codes:    6^4 = 1,296 (colors 0-5 only)

STRATEGY:
  After each guess, the feedback (bulls, cows) eliminates
  swathes of the manifold. The solver navigates the shrinking
  topology until only ONE coordinate remains: the secret code.
"""

import numpy as np
from itertools import product

# ─────────────────────────────────────────────
# 1. PRIME TOPOLOGY CORE
# ─────────────────────────────────────────────
PRIMES = [7, 11, 13, 17]
COLORS = 6
PEGS = 4
COLOR_SYMBOLS = ["🔴", "🟢", "🔵", "🟡", "🟣", "🟠"]
COLOR_NAMES = ["Red", "Green", "Blue", "Yellow", "Purple", "Orange"]

def mod_inverse(a, m):
    a = a % m
    for x in range(1, m):
        if (a * x) % m == 1:
            return x
    return 1

def garners_encode(code):
    """Encode a 4-color code as a single Master Coordinate via CRT."""
    # Garner's Algorithm: mixed-radix reconstruction
    a_list = list(code)
    p_list = PRIMES
    n = len(p_list)
    v = [0] * n
    v[0] = a_list[0] % p_list[0]
    
    for i in range(1, n):
        prod_prev = 1
        for j in range(i):
            prod_prev *= p_list[j]
        inv_prod = mod_inverse(prod_prev, p_list[i])
        
        temp = a_list[i]
        for j in range(i):
            p_ij = 1
            for k in range(j):
                p_ij *= p_list[k]
            temp -= v[j] * p_ij
        v[i] = (temp * inv_prod) % p_list[i]
    
    X = v[0]
    p_acc = 1
    for i in range(1, n):
        p_acc *= p_list[i-1]
        X += v[i] * p_acc
    return X

def decode_coordinate(z):
    """Extract the 4-color code from a Master Coordinate."""
    z_int = int(round(z))
    return tuple(z_int % p for p in PRIMES)

def score_guess(secret, guess):
    """
    Standard Mastermind scoring.
    Returns (bulls, cows).
    """
    bulls = sum(s == g for s, g in zip(secret, guess))
    
    # Count color frequencies for cow calculation
    s_counts = [0] * COLORS
    g_counts = [0] * COLORS
    for i in range(PEGS):
        if secret[i] != guess[i]:
            s_counts[secret[i]] += 1
            g_counts[guess[i]] += 1
    cows = sum(min(s_counts[c], g_counts[c]) for c in range(COLORS))
    
    return bulls, cows

def render_guess(guess, bulls, cows, guess_num):
    """Pretty-print a guess with feedback."""
    pegs = " ".join(COLOR_SYMBOLS[c] for c in guess)
    feedback = "●" * bulls + "○" * cows + "·" * (PEGS - bulls - cows)
    return f"  Guess {guess_num}: {pegs}  │ {feedback} │ {bulls}B {cows}C"

# ─────────────────────────────────────────────
# 2. THE MANIFOLD NAVIGATOR
# ─────────────────────────────────────────────
class PrimeManifold:
    """
    The solution space as a prime-numbered Riemann surface.
    Each feedback response eliminates entire sheets.
    """
    def __init__(self):
        # Generate ALL valid codes (colors 0-5 in each position)
        self.all_codes = list(product(range(COLORS), repeat=PEGS))
        self.candidates = list(self.all_codes)
        
        # Encode every code as a Master Coordinate
        self.coord_map = {code: garners_encode(code) for code in self.all_codes}
        
    def eliminate(self, guess, bulls, cows):
        """
        After a guess, eliminate all candidates that would NOT
        produce the same (bulls, cows) feedback.
        
        This is the topological "sheet collapse" — entire regions
        of the Riemann surface are annihilated.
        """
        before = len(self.candidates)
        self.candidates = [
            c for c in self.candidates 
            if score_guess(c, guess) == (bulls, cows)
        ]
        after = len(self.candidates)
        return before - after
    
    def best_guess(self):
        """
        Minimax strategy: Pick the guess that minimizes the 
        worst-case number of remaining candidates.
        
        This is navigating the manifold to the point of
        maximum "topological information gain."
        """
        if len(self.candidates) <= 2:
            return self.candidates[0]
        
        best_code = None
        best_worst = len(self.candidates) + 1
        
        # Sample from candidates for speed
        sample = self.candidates if len(self.candidates) <= 100 else \
                 [self.candidates[i] for i in np.random.choice(
                     len(self.candidates), min(100, len(self.candidates)), replace=False)]
        
        for guess in sample:
            # Count how many candidates fall into each feedback bucket
            buckets = {}
            for candidate in self.candidates:
                fb = score_guess(candidate, guess)
                buckets[fb] = buckets.get(fb, 0) + 1
            
            # Worst case: largest bucket
            worst = max(buckets.values())
            if worst < best_worst:
                best_worst = worst
                best_code = guess
        
        return best_code

# ─────────────────────────────────────────────
# 3. THE GAME
# ─────────────────────────────────────────────
def play_mastermind():
    # Generate a random secret code
    secret = tuple(np.random.randint(0, COLORS) for _ in range(PEGS))
    secret_z = garners_encode(secret)
    
    print("=" * 58)
    print("  PRIME-TOPOLOGY MASTERMIND CODEBREAKER")
    print("=" * 58)
    print(f"\n  Primes:     {PRIMES}")
    print(f"  Colors:     {COLORS}  ({', '.join(COLOR_NAMES)})")
    print(f"  Pegs:       {PEGS}")
    print(f"  Manifold:   {np.prod(PRIMES):,} coordinates")
    print(f"  Valid Codes: {COLORS**PEGS:,}")
    print(f"\n  Secret Code Coordinate: z = {secret_z}")
    print(f"  (Hidden: {' '.join(COLOR_SYMBOLS[c] for c in secret)})")
    
    manifold = PrimeManifold()
    
    print(f"\n{'─' * 58}")
    print(f"  {'GUESS':>8}  {'PEGS':^16}  │ {'FEEDBACK':^6} │ {'REMAINING':>10}")
    print(f"{'─' * 58}")
    
    for turn in range(1, 11):
        # Navigate the manifold to find the best guess
        guess = manifold.best_guess()
        guess_z = manifold.coord_map[guess]
        
        # Score against the secret
        bulls, cows = score_guess(secret, guess)
        
        # Eliminate inconsistent sheets
        eliminated = manifold.eliminate(guess, bulls, cows)
        remaining = len(manifold.candidates)
        
        # Render
        pegs = " ".join(COLOR_SYMBOLS[c] for c in guess)
        feedback = "●" * bulls + "○" * cows + "·" * (PEGS - bulls - cows)
        
        print(f"  {turn:>4}    {pegs}  │ {feedback}   │ {remaining:>6} left")
        
        if bulls == PEGS:
            print(f"{'─' * 58}")
            print(f"\n  🏆 CODE CRACKED in {turn} guesses!")
            print(f"  Secret:  {' '.join(COLOR_SYMBOLS[c] for c in secret)}")
            print(f"  Coordinate: z = {secret_z}")
            print(f"\n  Topological Proof:")
            print(f"    {secret_z} mod {PRIMES[0]:>2} = {secret[0]}  →  {COLOR_NAMES[secret[0]]}")
            print(f"    {secret_z} mod {PRIMES[1]:>2} = {secret[1]}  →  {COLOR_NAMES[secret[1]]}")
            print(f"    {secret_z} mod {PRIMES[2]:>2} = {secret[2]}  →  {COLOR_NAMES[secret[2]]}")
            print(f"    {secret_z} mod {PRIMES[3]:>2} = {secret[3]}  →  {COLOR_NAMES[secret[3]]}")
            print()
            return turn
    
    print(f"\n  ❌ Failed to crack in 10 guesses.")
    return -1

# ─────────────────────────────────────────────
# 4. STRESS TEST: 100 GAMES
# ─────────────────────────────────────────────
if __name__ == "__main__":
    # Single showcase game
    turns = play_mastermind()
    
    # Statistical stress test
    print("\n" + "=" * 58)
    print("  STRESS TEST: 100 Random Games")
    print("=" * 58)
    
    results = []
    for _ in range(100):
        secret = tuple(np.random.randint(0, COLORS) for _ in range(PEGS))
        manifold = PrimeManifold()
        
        for turn in range(1, 11):
            guess = manifold.best_guess()
            bulls, cows = score_guess(secret, guess)
            manifold.eliminate(guess, bulls, cows)
            if bulls == PEGS:
                results.append(turn)
                break
        else:
            results.append(-1)
    
    results = np.array(results)
    solved = results[results > 0]
    
    print(f"\n  Games Solved:  {len(solved)}/100")
    print(f"  Average Turns: {solved.mean():.2f}")
    print(f"  Worst Case:    {solved.max()} turns")
    print(f"  Best Case:     {solved.min()} turn(s)")
    print(f"\n  Distribution:")
    for t in range(1, int(solved.max()) + 1):
        count = (solved == t).sum()
        bar = "█" * count
        print(f"    {t} turns: {bar} ({count})")
    print()
