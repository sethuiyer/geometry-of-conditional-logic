"""
LeetCode Nightmare: Minimum Disturbance to Reach Target
=======================================================

You have source array S[0..n-1] and target array T[0..n-1].
Indices are partitioned into k zones by boundaries b_1 < ... < b_k = n
(b_0 = 0).  Zone j = indices [b_{j-1}, b_j).

Two operations:

  1. PATCH(i): set S[i] = T[i].  Cost = patch_cost (constant, e.g. 1).

  2. VIOLATE(j): unlock zones j..k for free modification.
     Cost = base^{-(k-j+1)} (e.g. 2^{-(k-j+1)}).
     Violating zone j also unlocks all deeper zones (> j).

Goal:  minimum total cost to turn S into T.

------------------------------------------------------------------------------
p-adic insight:

  v_R(S,T) = number of leading zones that already match perfectly.
  d_R(S,T) = base^{-v_R(S,T)}  = cost of violating the first mismatching zone.

  This is ultrametric: once you violate zone j, you get all deeper zones
  for free.  There's no "partial" violation — you pay for the deepest
  zone you touch, and that covers everything below it.

  The optimal strategy is a DP over zones:
    - Zone j matches perfectly  →  cost = cost(j+1..k)
    - Zone j has mismatches     →  either patch all mismatches individually,
                                    or violate zone j and fix everything below.

  The p-adic valuation tells you the crossover point where violating
  becomes cheaper than per-element patching.
------------------------------------------------------------------------------
"""

import random
import math


def min_cost(S, T, boundaries, patch_cost=1.0, base=2):
    """
    DP over zones from right to left.

    Returns (cost, ops) where ops describes the strategy.
    """
    n = len(S)
    k = len(boundaries)
    b = [0] + boundaries

    # Precompute: does zone j match perfectly?
    zone_matches = []
    for j in range(1, k + 1):
        start, end = b[j - 1], b[j]
        zone_matches.append(all(S[i] == T[i] for i in range(start, end)))

    # Precompute: number of mismatches in each zone
    zone_mismatches = []
    for j in range(1, k + 1):
        start, end = b[j - 1], b[j]
        zone_mismatches.append(sum(1 for i in range(start, end) if S[i] != T[i]))

    # DP from right (deepest zone) to left (shallowest)
    # dp[j] = min cost to fix zones j..k (1-indexed)

    # Sentinel: dp[k+1] = 0 (nothing to fix)
    dp = [0.0] * (k + 2)  # 1-indexed, dp[k+1] = 0
    choice = [None] * (k + 2)  # "patch", "violate", or "skip"

    # Work backwards
    for j in range(k, 0, -1):
        mm = zone_mismatches[j - 1]
        rest = dp[j + 1]

        if zone_matches[j - 1]:
            # Zone already matches.  Either skip (carry on below)
            # or violate here (cheap shallow violation that covers all deeper).
            violate_cost_val = base ** (-(k - j + 1))
            if rest <= violate_cost_val:
                dp[j] = rest
                choice[j] = "skip"
            else:
                dp[j] = violate_cost_val
                choice[j] = "violate"
        else:
            # Option A: patch all mismatches in this zone individually
            patch_all = mm * patch_cost + rest

            # Option B: violate this zone (covers all deeper zones too)
            violate_cost_val = base ** (-(k - j + 1))
            # When we violate, we fix zone j AND everything below for free
            violate_all = violate_cost_val  # no dp[j+1], all deeper zones included

            if patch_all <= violate_all:
                dp[j] = patch_all
                choice[j] = "patch"
            else:
                dp[j] = violate_all
                choice[j] = "violate"

    # Reconstruct strategy
    ops = []
    j = 1
    while j <= k:
        if choice[j] == "skip":
            ops.append(f"  zone {j}: skip (already matches)")
            j += 1
        elif choice[j] == "patch":
            ops.append(f"  zone {j}: patch {zone_mismatches[j-1]} mismatch(es) "
                       f"at {zone_mismatches[j-1] * patch_cost}")
            j += 1
        elif choice[j] == "violate":
            ops.append(f"  zone {j}: VIOLATE at cost "
                       f"{base}^-({k-j+1}) = {base ** (-(k-j+1))}, "
                       f"fix zones {j}..{k} freely")
            break  # everything below is handled

    return dp[1], ops


def brute_force_min_cost(S, T, boundaries, patch_cost=1.0, base=2):
    """
    Enumerate all possible strategies to verify optimality.

    For each subset of zones to patch, and for each possible violation level,
    check if S can reach T and compute cost.
    """
    n = len(S)
    k = len(boundaries)
    b = [0] + boundaries

    best = float("inf")
    # Try all violation levels (0 = no violation, 1..k = violate at level j)
    for violate_level in range(0, k + 1):
        # For zones before violate_level, we can only patch individual elements.
        # We must patch ALL mismatches in those zones.
        must_patch_zones = list(range(1, violate_level)) if violate_level > 0 else list(range(1, k + 1))
        can_free_zones = list(range(violate_level, k + 1)) if violate_level > 0 else []

        # Check if patching is sufficient for must_patch_zones
        possible = True
        cost = 0.0
        for j in must_patch_zones:
            start, end = b[j - 1], b[j]
            mm = sum(1 for i in range(start, end) if S[i] != T[i])
            cost += mm * patch_cost
        if violate_level > 0:
            cost += base ** (-(k - violate_level + 1))

        # Verify that for free zones, we can reach T (always yes since we can set freely)
        if possible:
            best = min(best, cost)

    # Also try: violate none, patch everything
    cost_patch_all = 0.0
    for j in range(1, k + 1):
        start, end = b[j - 1], b[j]
        mm = sum(1 for i in range(start, end) if S[i] != T[i])
        cost_patch_all += mm * patch_cost
    best = min(best, cost_patch_all)

    return best


# ---------------------------------------------------------------------------
# Examples
# ---------------------------------------------------------------------------

print("=" * 68)
print("Example 1: Shallow mismatch — cheaper to patch than violate")
S = [1, 2, 3, 4, 5]
T = [1, 9, 3, 4, 5]
boundaries = [2, 4, 5]  # zones: [0,2) [2,4) [4,5)
cost, ops = min_cost(S, T, boundaries, patch_cost=1.0)
bf = brute_force_min_cost(S, T, boundaries, patch_cost=1.0)
print(f"  S = {S}")
print(f"  T = {T}")
print(f"  zones: [0,2) [2,4) [4,5),  patch_cost=1")
print(f"  DP cost = {cost},  brute force = {bf}")
for o in ops:
    print(o)
assert abs(cost - bf) < 1e-9
print("  ✓")

print()
print("=" * 68)
print("Example 2: Deep mismatch — cheaper to violate than patch many")
S = [1, 2, 3, 4, 5]
T = [9, 8, 7, 6, 5]
cost, ops = min_cost(S, T, boundaries, patch_cost=1.0)
bf = brute_force_min_cost(S, T, boundaries, patch_cost=1.0)
print(f"  S = {S}")
print(f"  T = {T}")
print(f"  zones: [0,2) [2,4) [4,5),  patch_cost=1")
print(f"  DP cost = {cost},  brute force = {bf}")
for o in ops:
    print(o)
assert abs(cost - bf) < 1e-9
print("  ✓")

print()
print("=" * 68)
print("Example 3: All match — zero cost")
S = [1, 2, 3, 4, 5]
T = [1, 2, 3, 4, 5]
cost, ops = min_cost(S, T, boundaries)
bf = brute_force_min_cost(S, T, boundaries)
print(f"  S = {S}")
print(f"  T = {T}")
print(f"  Cost = {cost}, brute = {bf}")
for o in ops:
    print(o)
assert abs(cost - bf) < 1e-9
print("  ✓")

print()
print("=" * 68)
print("Example 4: Many patches in one zone — violate is cheaper")
S = [1, 2, 3, 4, 5]
T = [1, 9, 8, 7, 6]
cost, ops = min_cost(S, T, boundaries, patch_cost=1.0)
bf = brute_force_min_cost(S, T, boundaries, patch_cost=1.0)
print(f"  S = {S}")
print(f"  T = {T}")
print(f"  zones: [0,2) [2,4) [4,5),  patch_cost=1")
print(f"  DP cost = {cost},  brute force = {bf}")
for o in ops:
    print(o)
# zone 2 has 2 mismatches (indices 2,3) → patch cost = 2, violate = 0.25
# zone 3 has 1 mismatch → patch cost = 1
# zone 2: patch(2) vs violate = 0.25 → violate is cheaper!
# zone 3 is then free
assert abs(cost - bf) < 1e-9
print("  ✓")

print()
print("=" * 68)
print("Example 5: High patch cost — violate always wins early")
S = [1, 2, 3, 4, 5]
T = [9, 8, 7, 6, 5]
boundaries2 = [1, 2, 3, 4, 5]  # each element is its own zone
cost, ops = min_cost(S, T, boundaries2, patch_cost=100.0)
bf = brute_force_min_cost(S, T, boundaries2, patch_cost=100.0)
print(f"  S = {S}")
print(f"  T = {T}")
print(f"  each index = own zone,  patch_cost=100")
print(f"  DP cost = {cost},  brute force = {bf}")
for o in ops:
    print(o)
assert abs(cost - bf) < 1e-9
print("  ✓")

print()
print("=" * 68)
print("Random stress test")
for trial in range(200):
    n = random.randint(3, 10)
    k = random.randint(2, n)
    candidates = sorted(random.sample(range(1, n), k - 1))
    boundaries_r = candidates + [n]
    S = [random.randint(0, 5) for _ in range(n)]
    T = [random.randint(0, 5) for _ in range(n)]
    pc = random.choice([0.5, 1.0, 2.0, 5.0])
    cost, _ = min_cost(S, T, boundaries_r, patch_cost=pc)
    bf = brute_force_min_cost(S, T, boundaries_r, patch_cost=pc)
    assert abs(cost - bf) < 1e-9, f"FAIL trial {trial}: DP={cost} BF={bf}"
print(f"  200/200 random tests pass")
print()

# ---------------------------------------------------------------------------
# The p-adic structure
# ---------------------------------------------------------------------------
print("=" * 68)
print("The p-adic structure: violation costs are ultrametric")
print()

# Show that the minimum cost to repair S→T equals the cost of violating
# at the "deepest zone worth violating" — which is the p-adic valuation
# of the difference, but measured in zones rather than residues.
def repair_valuation(z1, z2, moduli):
    v = 0
    for m in moduli:
        if (z1 - z2) % m == 0:
            v += 1
        else:
            break
    return v

# Use CRT encoding to show the p-adic valuation tracks preserved layers
moduli = [2, 3, 5, 7]


def encode(arr, moduli):
    residues = [v % m for v, m in zip(arr, moduli)]
    z = 0
    for i, (r, m) in enumerate(zip(residues, moduli)):
        M = math.prod(moduli[:i])
        inv = pow(M % m, -1, m)
        z += ((r - z) * inv) % m * M
    return z


cases = [
    ([1, 2, 3, 4], [1, 2, 3, 4]),
    ([1, 2, 3, 4], [1, 2, 9, 4]),
    ([1, 2, 3, 4], [1, 9, 9, 4]),
    ([1, 2, 3, 4], [9, 9, 9, 9]),
]
for S, T in cases:
    z_s = encode(S, moduli[:4])
    z_t = encode(T, moduli[:4])
    v = repair_valuation(z_s, z_t, moduli[:4])
    dR = 2 ** (-v)
    print(f"  S={S}  T={T}")
    print(f"    v_R = {v} preserved residues")
    print(f"    d_R = 2^-{v} = {dR}  (p-adic distance)")
    print()
