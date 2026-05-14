"""
Experimental check of p-adic repair geometry claims from PADIC.md.

Tests:
  1. CRT jumps preserve locked residues (stay inside p-adic ball)
  2. Repair valuation v_R(z, z') matches disturbed-layer count
  3. Ultrametric inequality d_R(z, z'') <= max(d_R(z, z'), d_R(z', z''))
  4. Nested ball structure (deeper lock => smaller ball)
"""

import random
import itertools
import math

PRIMES = [2, 3, 5, 7, 11, 13, 17, 19]


def crt(residues, moduli):
    """Garner reconstruction: residues[i] modulo moduli[i], pairwise coprime."""
    n = len(moduli)
    v = [0] * n
    v[0] = residues[0]
    for i in range(1, n):
        t = residues[i]
        for j in range(i):
            t -= v[j] * math.prod(moduli[:j])
        inv = pow(math.prod(moduli[:i]), -1, moduli[i])
        v[i] = t * inv % moduli[i]
    z = 0
    for i in range(n):
        z += v[i] * math.prod(moduli[:i])
    return z


def decode(z, moduli):
    """Return residues of z modulo each modulus."""
    return [z % m for m in moduli]


def crt_jump(z, target_residue, target_idx, shield_modulus, moduli):
    """z' = z + k*M where M = shield_modulus, preserving all mod M residues."""
    M = shield_modulus
    pt = moduli[target_idx]
    inv = pow(M % pt, -1, pt)
    k = ((target_residue - z) * inv) % pt
    return z + k * M


def repair_valuation(z1, z2, moduli):
    """v_R = number of leading moduli where residues match (preserved layers)."""
    r1 = decode(z1, moduli)
    r2 = decode(z2, moduli)
    v = 0
    for a, b in zip(r1, r2):
        if a == b:
            v += 1
        else:
            break
    return v


def repair_distance(z1, z2, moduli, alpha=2):
    """d_R = alpha^{-v_R}"""
    return alpha ** (-repair_valuation(z1, z2, moduli))


def ultrametric_triple(z1, z2, z3, moduli, alpha=2):
    """Return True if ultrametric inequality holds."""
    d12 = repair_distance(z1, z2, moduli, alpha)
    d23 = repair_distance(z2, z3, moduli, alpha)
    d13 = repair_distance(z1, z3, moduli, alpha)
    ok = d13 <= max(d12, d23)
    return ok, (d12, d23, d13)


# --- Test 1: CRT jump preserves locked residues ---

print("=== Test 1: CRT jump preserves locked residues ===")
moduli = PRIMES[:5]  # [2,3,5,7,11], P=2310
state = [1, 0, 1, 2, 3]
z = crt(state, moduli)
print(f"  z = {z}, residues = {decode(z, moduli)}")

# Lock first 3 moduli (depth = 3, shield M = 2*3*5 = 30)
shield_M = math.prod(moduli[:3])
z2 = crt_jump(z, target_residue=4, target_idx=3, shield_modulus=shield_M, moduli=moduli)

r_old = decode(z, moduli)
r_new = decode(z2, moduli)
preserved = all(r_old[i] == r_new[i] for i in range(3))
print(f"  Shield M = {shield_M}")
print(f"  z' = {z2}, residues = {r_new}")
print(f"  First 3 residues preserved? {preserved}")
assert preserved, "FAIL: locked residues changed!"
print("  PASS")

# --- Test 2: Repair valuation matches disturbed layers ---

print("\n=== Test 2: Repair valuation ===")
v = repair_valuation(z, z2, moduli)
print(f"  v_R(z, z') = {v} (preserved {v} layers, disturbed {len(moduli)-v})")
assert v == 3, f"Expected v=3, got {v}"
d = repair_distance(z, z2, moduli)
print(f"  d_R(z, z') = 2^-{v} = {d}")
print("  PASS")

# --- Test 3: Ultrametric inequality on random triples ---

print("\n=== Test 3: Ultrametric inequality ===")
moduli6 = PRIMES[:6]
P = math.prod(moduli6)
failures = 0
trials = 2000
for _ in range(trials):
    z1 = random.randrange(0, P)
    z2 = random.randrange(0, P)
    z3 = random.randrange(0, P)
    ok, ds = ultrametric_triple(z1, z2, z3, moduli6)
    if not ok:
        failures += 1
print(f"  {trials} random triples: {failures} ultrametric violations")
if failures == 0:
    print("  PASS: all triples satisfy d_R(z,z'') <= max(d_R(z,z'), d_R(z',z''))")
else:
    print(f"  VIOLATIONS: {failures}/{trials}")

# --- Test 4: Nested ball containment ---

print("\n=== Test 4: Nested ball containment ===")
# The p-adic ball of radius 1/M around z0 is {z : z ≡ z0 (mod M)}.
# A larger shield M means a smaller ball (more residues locked).
# Since M_large is a multiple of M_small, B(M_large) ⊆ B(M_small).
M_small = math.prod(moduli[:2])   # 6
M_large = math.prod(moduli[:4])   # 210
P = math.prod(moduli[:5])         # 2310
z0 = crt([0] * 5, moduli)

# Enumerate all states in each ball (small space since P=2310)
ball_small = {z for z in range(P) if z % M_small == z0 % M_small}
ball_large = {z for z in range(P) if z % M_large == z0 % M_large}

subset = ball_large.issubset(ball_small)
print(f"  |B(M210)| = {len(ball_large)}, |B(M6)| = {len(ball_small)}")
print(f"  |B(M210)|/|B(M6)| = {len(ball_large)}/{len(ball_small)} = {len(ball_large)/len(ball_small):.3f}")
print(f"  B(M210) ⊆ B(M6)? {subset}")
assert subset, "FAIL: deeper lock ball not subset of shallower!"
# Also verify: ratio should be ~ 1/(5*7) = 1/35 since moduli[2:4] = [5,7] add 35× constraint
expected_ratio = 1.0 / math.prod(moduli[2:4])
actual_ratio = len(ball_large) / len(ball_small)
assert abs(actual_ratio - expected_ratio) < 1e-9, f"Ratio mismatch: {actual_ratio} vs {expected_ratio}"
print(f"  Ratio = 1/∏p_[2:4] = 1/{math.prod(moduli[2:4])} ✓")
print("  PASS: deeper commitments => smaller consistency ball")

# --- Test 5: Verify v_R corresponds to first-differing coordinate ---

print("\n=== Test 5: Valuation = first differing coordinate ===")
z_a = crt([0, 0, 0, 0, 0], moduli)
z_b = crt([0, 0, 1, 2, 3], moduli)
z_c = crt([0, 1, 1, 2, 3], moduli)
z_d = crt([1, 1, 1, 2, 3], moduli)

for label, zb in [("b", z_b), ("c", z_c), ("d", z_d)]:
    v = repair_valuation(z_a, zb, moduli)
    print(f"  v_R(z_a, z_{label}) = {v}  (first diff at idx {v})")
    assert v == next(i for i, (a, b) in enumerate(zip(decode(z_a, moduli), decode(zb, moduli))) if a != b)
print("  PASS")

print("\n=== All checks pass ===")
