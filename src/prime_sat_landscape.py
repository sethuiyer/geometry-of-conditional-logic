"""
PRIME-TOPOLOGY SAT LANDSCAPE OBSERVER
=====================================
Visualizing 3-SAT "Frustration Geometry" as a continuous wave landscape.

Each clause in a 3-SAT instance is mapped to a "Penalty Wave" peaking 
at the exact coordinate that violates that clause.

CONSTRAINTS:
  x1, x2, x3, x4 -> Primes [2, 3, 5, 7]
  Residue 0 = False, 1 = True
"""

import numpy as np
import matplotlib.pyplot as plt

# 1. SAT CONFIG
PRIMES = [2, 3, 5, 7] # 4 Variables
N_VARS = len(PRIMES)
MAX_Z = np.prod(PRIMES) # 210

def mod_inverse(a, m):
    a = a % m
    for x in range(1, m):
        if (a * x) % m == 1:
            return x
    return 1

def garners_target(a_list, p_list):
    """Find the coordinate z that satisfies all residues in a_list."""
    v = [a_list[0] % p_list[0]]
    for i in range(1, len(p_list)):
        prod = 1
        for j in range(i): prod *= p_list[j]
        inv = mod_inverse(prod, p_list[i])
        temp = a_list[i]
        for j in range(i):
            pj = 1
            for k in range(j): pj *= p_list[k]
            temp -= v[j] * pj
        v.append((temp * inv) % p_list[i])
    X, acc = v[0], 1
    for i in range(1, len(v)):
        acc *= p_list[i-1]
        X += v[i] * acc
    return X

# 2. DEFINE SAT CLAUSES
# A clause is (var_idx, is_positive)
# e.g., (0, True) means x1, (1, False) means NOT x2
CLAUSES = [
    [(0, True),  (1, False), (2, True)],  # (x1 OR NOT x2 OR x3)
    [(0, False), (3, True),  (1, True)],  # (NOT x1 OR x4 OR x2)
    [(2, False), (1, False), (3, False)], # (NOT x3 OR NOT x2 OR NOT x4)
    [(0, True),  (2, False), (3, True)],  # (x1 OR NOT x3 OR x4)
    [(1, True),  (2, True),  (0, False)], # (x2 OR x3 OR NOT x1)
]

def get_clause_violation_z(clause):
    """
    Find the Master Coordinate z that VIOLATES this clause.
    A clause (A or B or C) is violated ONLY if A=0, B=0, C=0.
    """
    target_residues = [None] * N_VARS
    for var_idx, is_pos in clause:
        # To violate (x), x must be 0 (False).
        # To violate (NOT x), x must be 1 (True).
        target_residues[var_idx] = 1 if not is_pos else 0
        
    # For variables not in the clause, we don't care, but for the 
    # visualization, we'll treat them as a "sub-manifold" mountain range.
    # We find all possible z that satisfy the clause-violating residues.
    return target_residues

def calculate_landscape(z_range):
    """Sum the penalty waves for all clauses across the coordinate space."""
    landscape = np.zeros_like(z_range)
    
    for clause in CLAUSES:
        # Find the violation target
        targets = get_clause_violation_z(clause)
        
        # Each clause violation creates a wave: 
        # A clause only constrains 3 variables. The 4th variable 
        # creates "ghost peaks" every P_missing units.
        clause_loss = np.ones_like(z_range)
        for i, target in enumerate(targets):
            if target is not None:
                p = PRIMES[i]
                # High loss when z % p == target
                phase = 2 * np.pi * (z_range - target) / p
                # Penalty wave is high at the target residue
                clause_loss *= (0.5 + 0.5 * np.cos(phase))
        
        landscape += clause_loss
        
    return landscape

# 3. GENERATE VISUALIZATION
def plot_sat_landscape():
    z = np.linspace(0, MAX_Z, 2000)
    landscape = calculate_landscape(z)
    
    plt.figure(figsize=(15, 7), facecolor='#0a0a0f')
    ax = plt.gca()
    ax.set_facecolor('#0a0a0f')
    
    # Plot the "Frustration Sea"
    plt.fill_between(z, landscape, color='#7c6ff7', alpha=0.2)
    plt.plot(z, landscape, color='#7c6ff7', lw=1.5, label='SAT Frustration Energy')
    
    # Find Satisfying Assignments (Loss near 0)
    # Since we only have 210 coordinates, we can check them all
    sat_assignments = []
    for i in range(MAX_Z):
        l = calculate_landscape(np.array([float(i)]))[0]
        if l < 0.1: # Threshold for "Satisfied"
            sat_assignments.append(i)
            plt.axvline(x=i, color='#6ff7a0', alpha=0.3, ls='--')
            plt.scatter(i, 0, color='#6ff7a0', s=50, zorder=5)

    plt.title("3-SAT Frustration Geometry: The Continuous Manifold", color='#e8e8f0', fontsize=16, pad=20)
    plt.xlabel("Master Coordinate (z)", color='#6b6b7b', fontfamily='monospace')
    plt.ylabel("Constraint Violation (Energy)", color='#6b6b7b', fontfamily='monospace')
    
    plt.grid(color='#1e1e2e', alpha=0.5)
    ax.tick_params(colors='#6b6b7b')
    for spine in ax.spines.values(): spine.set_color('#1e1e2e')
    
    # Annotate satisfying points
    if sat_assignments:
        plt.legend(facecolor='#12121a', edgecolor='#1e1e2e', labelcolor='#c9c9d9')
        print(f"Found {len(sat_assignments)} satisfying coordinates: {sat_assignments}")
    else:
        print("UNSAT: No global minima found in the manifold.")

    plt.tight_layout()
    plt.savefig('sat_landscape.png', dpi=300)
    print("Landscape saved to 'sat_landscape.png'")

if __name__ == "__main__":
    plot_sat_landscape()
