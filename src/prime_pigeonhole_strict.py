"""
PRIME-TOPOLOGY PIGEONHOLE FRUSTRATION (STRICT BINARY)
====================================================
Forcing variables to 0 or 1 to prove UNSAT.
"""

import numpy as np
import matplotlib.pyplot as plt

PRIMES = [2, 3, 5, 7, 11, 13]
MAX_Z = np.prod(PRIMES)

def calculate_strict_energy(z):
    energy = 0
    
    # 1. BINARY GRAVITY: Every variable MUST be 0 or 1.
    # Penalty if residue is > 1.
    for p in PRIMES:
        res = z % p
        if res > 1:
            energy += 5.0 # Massive penalty for "imaginary" states
            
    # 2. PIGEON CONSTRAINTS (Same as before)
    # Each pigeon in at least one hole (Violation: x_p,0=0 AND x_p,1=0)
    for p in range(3):
        v1, v2 = p*2, p*2+1
        if (z % PRIMES[v1] == 0) and (z % PRIMES[v2] == 0):
            energy += 10.0
            
    # No hole more than one pigeon (Violation: x_p1,j=1 AND x_p2,j=1)
    for h in range(2):
        for p1 in range(3):
            for p2 in range(p1 + 1, 3):
                v1, v2 = p1*2 + h, p2*2 + h
                if (z % PRIMES[v1] == 1) and (z % PRIMES[v2] == 1):
                    energy += 10.0
                    
    return energy

print("Scanning with Binary Gravity...")
min_energy = float('inf')
for zi in range(MAX_Z):
    e = calculate_strict_energy(zi)
    if e < min_energy:
        min_energy = e
        
print(f"\nSTRICT RESULTS:")
print(f"  Minimum Binary Energy: {min_energy}")

if min_energy > 0:
    print("\n🏆 GEOMETRIC PROOF OF UNSAT (STRICT):")
    print(f"  The lowest energy state has a frustration of {min_energy}.")
    print("  There is NO WAY to satisfy these constraints in binary space.")
    print("  The Pigeonhole Principle is topologically enforced.")
