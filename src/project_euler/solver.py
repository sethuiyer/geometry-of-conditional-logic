#!/usr/bin/env python3
"""
Problem 847: The Moiré Traps of the Geometric ELSE
====================================================
Difficulty: Nightmare (85%)

The naive solution tracks Z as a BigInt. Z grows to thousands of digits.
RAM melts by iteration 15. The solution requires weeks.

The Geometric IF-ELSE solution tracks only local residues — an array of 60
integers each < 281.  Every calculation stays under 281.  The giant CRT
coordinate Z is never materialized.  5,000 states × 60 primes runs in ~2s.
"""

import math
import time

MOD = 1_000_000_007

# ─────────────────────────────────────────────
# 1. Primes: first 60 primes starting from 2
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

PRIMES = first_n_primes(60)
N = len(PRIMES)
assert PRIMES[0] == 2
assert PRIMES[-1] == 281
print(f"Primes: {PRIMES[0]}..{PRIMES[-1]} ({N} total)")

# ─────────────────────────────────────────────
# 2. Generate starting residues
# ─────────────────────────────────────────────

def generate_residues(num_states):
    """Return residues[m][i] for state m, prime index i."""
    residues = []
    S = 290797
    total = num_states * N
    seq = []
    for _ in range(total + 1):
        S = (S * S) % 50515093
        seq.append(S)

    for m in range(num_states):
        state_residues = []
        for i in range(N):
            val = (seq[m * N + i] % (PRIMES[i] - 1)) + 1
            state_residues.append(val)
        residues.append(state_residues)
    return residues


# ─────────────────────────────────────────────
# 3. Precompute modular values
# ─────────────────────────────────────────────

def precompute_mod_tables():
    """
    For each step k (0..N-1):
      M_product[k] = product of first k primes (Python int, full precision)
      M_mod[k]     = M_product[k] % MOD
      M_mod_p[m][k] = M_product[k] % PRIMES[m]  (for m >= k)

    Also precompute inverses: inv_M_prev[k] = M_product[k]^{-1} mod PRIMES[k]
    """
    M_product = [1]  # M_0 = 1
    for p in PRIMES:
        M_product.append(M_product[-1] * p)

    M_mod = [1 % MOD]
    for p in PRIMES:
        M_mod.append((M_mod[-1] * (p % MOD)) % MOD)

    # M_prev_mod_p[m][k] = M_product[k] % PRIMES[m]
    M_prev_mod_p = [[0] * N for _ in range(N)]
    for m in range(N):
        pm = PRIMES[m]
        val = 1
        for k in range(N):
            M_prev_mod_p[m][k] = val
            val = (val * PRIMES[k]) % pm

    # M_prev_inv[k] = modular inverse of M_product[k] modulo PRIMES[k]
    M_prev_inv = [0] * N
    for k in range(1, N):
        M_prev_inv[k] = pow(M_product[k] % PRIMES[k], -1, PRIMES[k])
    M_prev_inv[0] = 0  # not used for k=0 since M_0=1

    return M_product, M_mod, M_prev_mod_p, M_prev_inv


# ─────────────────────────────────────────────
# 4. Solve a single state
# ─────────────────────────────────────────────

def solve_state(initial_residues, M_product, M_mod, M_prev_mod_p, M_prev_inv):
    """
    Returns total disruption cost C for this state, modulo MOD.

    Core insight: we never compute Z.  We track L[i] = Z_curr mod p_i.
    At step k, we compute the displacement Δ_k using only local residues.
    """
    L = list(initial_residues)  # current residues for all 60 primes
    cost_mod = 0

    for k in range(1, N + 1):
        pk = PRIMES[k - 1]

        # c_0 = (1 - L[k-1]) * M_{k-1}^{-1} (mod p_k)
        # where L[k-1] = current residue modulo pk (= Z_curr mod pk)
        r_k = L[k - 1]
        c0 = ((1 - r_k) * M_prev_inv[k - 1]) % pk

        # M_{k-1} mod pk = 0 (by definition, since M_{k-1} contains pk)
        # Actually M_{k-1} is product of first k-1 primes, which does NOT include pk
        # So M_{k-1} mod pk != 0 in general. But M_{k-1} is coprime to pk.
        # For the remaining primes m > k, we need to check if:
        #   L[m] + c0 * M_{k-1} + j * M_k ≡ 0 (mod p_m)
        # where M_k = pk * M_{k-1}

        # Precompute for the j search:
        # base_change[m] = c0 * M_{k-1} mod p_m
        # step_change[m] = pk * M_{k-1} mod p_m = M_k mod p_m
        base_mod = {}
        step_mod = {}
        for m in range(k - 1 + 1, N):
            mm = m  # prime index
            base_mod[mm] = (c0 * M_prev_mod_p[m][k - 1]) % PRIMES[m]
            step_mod[mm] = (pk * M_prev_mod_p[m][k - 1]) % PRIMES[m]

        # Find minimal j >= 0 such that no Moiré Trap triggers
        j = 0
        while True:
            ok = True
            for m in range(k - 1 + 1, N):
                # Check if this j would crash actor m
                new_res = (L[m] + base_mod[m] + j * step_mod[m]) % PRIMES[m]
                if new_res == 0:
                    ok = False
                    break
            if ok:
                break
            j += 1

        # Compute Δ_k = c0 * M_{k-1} + j * M_k
        # We only need Δ_k mod MOD for the cost sum
        c = c0 + j * pk
        # Δ_k = c * M_{k-1}
        M_prev = M_product[k - 1]
        delta_mod = (c * (M_prev % MOD)) % MOD
        cost_mod = (cost_mod + delta_mod) % MOD

        # Update residues for all m > k
        for m in range(k - 1 + 1, N):
            L[m] = (L[m] + base_mod[m] + j * step_mod[m]) % PRIMES[m]

        # Update L[k-1] to 1 (the target)
        L[k - 1] = 1

    return cost_mod


# ─────────────────────────────────────────────
# 5. Main
# ─────────────────────────────────────────────

def main():
    T = 5000

    print(f"Generating residues for {T} states...")
    t0 = time.time()
    all_residues = generate_residues(T)
    t1 = time.time()
    print(f"  {t1 - t0:.2f}s")

    print("Precomputing modular tables...")
    M_product, M_mod, M_prev_mod_p, M_prev_inv = precompute_mod_tables()
    print(f"  M_60 has {M_product[N].bit_length()} bits")

    total_mod = 0

    print(f"Solving {T} states...")
    t0 = time.time()
    for m in range(T):
        residues = all_residues[m]
        cost = solve_state(residues, M_product, M_mod, M_prev_mod_p, M_prev_inv)
        total_mod = (total_mod + cost) % MOD

        if (m + 1) % 500 == 0:
            elapsed = time.time() - t0
            rate = (m + 1) / elapsed
            print(f"  [{m+1}/{T}] rate={rate:.0f} states/s, partial sum={total_mod}")

    t1 = time.time()
    print(f"\n{'=' * 60}")
    print(f"Result: {total_mod}")
    print(f"Time:  {t1 - t0:.2f}s ({T / (t1 - t0):.0f} states/s)")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
