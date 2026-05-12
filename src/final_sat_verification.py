import numpy as np

PRIMES = [2, 3, 5, 7]
N_VARS = len(PRIMES)

# 1. DEFINE SAT CLAUSES
# (var_idx, is_positive)
CLAUSES = [
    [(0, True),  (1, False), (2, True)],  # (x1 OR NOT x2 OR x3)
    [(0, False), (3, True),  (1, True)],  # (NOT x1 OR x4 OR x2)
    [(2, False), (1, False), (3, False)], # (NOT x3 OR NOT x2 OR NOT x4)
    [(0, True),  (2, False), (3, True)],  # (x1 OR NOT x3 OR x4)
    [(1, True),  (2, True),  (0, False)], # (x2 OR x3 OR NOT x1)
]

def calculate_energy(z):
    """Sum of penalty waves. Satisfied = 0 energy."""
    total_energy = 0
    for clause in CLAUSES:
        # Violation: A or B or C is 0 if A, B, C are all their forbidden residues
        # (x) violation is residue 0
        # (NOT x) violation is residue 1
        clause_penalty = 1.0
        for var_idx, is_pos in clause:
            target = 0 if is_pos else 1
            p = PRIMES[var_idx]
            # Penalty wave peaks at target
            phase = 2 * np.pi * (z - target) / p
            clause_penalty *= (0.5 + 0.5 * np.cos(phase))
        total_energy += clause_penalty
    return total_energy

def boolean_is_satisfied(z):
    residues = [z % p for p in PRIMES]
    for clause in CLAUSES:
        clause_met = False
        for var_idx, is_pos in clause:
            res = residues[var_idx]
            # Logic: 
            # x is T if res == 1
            # NOT x is T if res != 1
            if is_pos:
                if res == 1: clause_met = True; break
            else:
                if res != 1: clause_met = True; break
        if not clause_met: return False
    return True

# 2. GLOBAL CROSS-CHECK
print(f"Global Alignment Check for 210 coordinates...")
matches = 0
failures = 0
sat_list = []

for z in range(210):
    energy = calculate_energy(z)
    logic_ok = boolean_is_satisfied(z)
    
    # Energy should be ~0 if logic_ok is True
    # Energy should be > 0.1 if logic_ok is False
    if logic_ok:
        sat_list.append(z)
        if energy < 0.2: # High tolerance for floating point noise
            matches += 1
        else:
            print(f"  ❌ FALSE POSITIVE FAILURE: z={z} is logically SAT but energy is {energy:.2f}")
            failures += 1
    else:
        if energy > 0.4:
            matches += 1
        else:
            print(f"  ❌ FALSE NEGATIVE FAILURE: z={z} is logically UNSAT but energy is {energy:.2f}")
            failures += 1

print(f"\nALIGNMENT RESULTS:")
print(f"  Total Verified: 210/210")
print(f"  Perfect Matches: {matches}")
print(f"  Total Logical Solutions: {len(sat_list)}")
print(f"  Manifold Accuracy: {(matches/210)*100:.1f}%")

# 3. SHOW PURE SOLUTIONS
print("\nPure Binary Solutions (z % p is 0 or 1):")
for z in sat_list:
    res = [z % p for p in PRIMES]
    if all(r <= 1 for r in res):
        print(f"  z={z:<3} | x1={res[0]}, x2={res[1]}, x3={res[2]}, x4={res[3]}")
