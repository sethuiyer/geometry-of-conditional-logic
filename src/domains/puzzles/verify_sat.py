import numpy as np

# 1. SETUP
PRIMES = [2, 3, 5, 7] # x1, x2, x3, x4
N_VARS = 4

# Clauses from our SAT instance
# (var_idx, is_positive)
CLAUSES = [
    [(0, True),  (1, False), (2, True)],  # (x1 OR NOT x2 OR x3)
    [(0, False), (3, True),  (1, True)],  # (NOT x1 OR x4 OR x2)
    [(2, False), (1, False), (3, False)], # (NOT x3 OR NOT x2 OR NOT x4)
    [(0, True),  (2, False), (3, True)],  # (x1 OR NOT x3 OR x4)
    [(1, True),  (2, True),  (0, False)], # (x2 OR x3 OR NOT x1)
]

def is_satisfied(z):
    # Extract residues
    residues = [z % p for p in PRIMES]
    
    # We define a literal (x) as satisfied if its residue is 1.
    # We define a literal (NOT x) as satisfied if its residue is NOT 1 (0, 2, 3...).
    # This matches our "Penalty Wave" mountain at target=0/1.
    
    for clause in CLAUSES:
        clause_met = False
        for var_idx, is_pos in clause:
            res = residues[var_idx]
            if is_pos:
                if res == 1: # Literal (x) satisfied if res is 1
                    clause_met = True; break
            else:
                if res != 1: # Literal (NOT x) satisfied if res is NOT 1
                    clause_met = True; break
        
        if not clause_met:
            return False
    return True

# 2. BRUTE FORCE VERIFICATION
print(f"Verifying all {np.prod(PRIMES)} coordinates in the 4-prime manifold...")
satisfied_coords = []
for z in range(np.prod(PRIMES)):
    if is_satisfied(z):
        satisfied_coords.append(z)

print(f"\nFOUND {len(satisfied_coords)} SATISFYING COORDINATES:")
print(satisfied_coords)

# 3. ANALYSIS OF PURE BINARY SOLUTIONS
print("\nScanning for Pure Binary Solutions (all residues are 0 or 1):")
pure_binary = []
for z in satisfied_coords:
    res = [z % p for p in PRIMES]
    if all(r <= 1 for r in res):
        pure_binary.append((z, res))

if pure_binary:
    for z, res in pure_binary:
        print(f"  z = {z:<3} | Assignments: x1={res[0]}, x2={res[1]}, x3={res[2]}, x4={res[3]}")
else:
    print("  None. All solutions exist in the 'Ghost Sheets' of the manifold.")

# 4. CROSS-CHECK WITH OUR LANDSCAPE
# Our landscape found 17 coordinates with loss < 0.1
manifold_valleys = [17, 18, 32, 38, 53, 67, 68, 73, 102, 108, 128, 137, 138, 143, 158, 193, 198]
print(f"\nLandscape Cross-Check:")
missing = [c for c in satisfied_coords if c not in manifold_valleys]
extra = [c for c in manifold_valleys if c not in satisfied_coords]
print(f"  Missing from Manifold: {missing}")
print(f"  Extra in Manifold:   {extra}")
if not missing and not extra:
    print("  ✅ PERFECT ALIGNMENT: Manifold valleys = Logical Truth.")
