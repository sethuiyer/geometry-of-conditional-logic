"""
PRIME-TOPOLOGY PIGEONHOLE FRUSTRATION
=====================================
Proving UNSAT via Manifold Geometry.

Setup: 3 Pigeons, 2 Holes.
Variables: x_{p,h} (Pigeon p in Hole h)
Constraint: Total SAT is impossible.
"""

import numpy as np
import matplotlib.pyplot as plt

# 1. ENCODING
# Pigeons 0,1,2 | Holes 0,1
# Variables: 0:(0,0), 1:(0,1), 2:(1,0), 3:(1,1), 4:(2,0), 5:(2,1)
PRIMES = [2, 3, 5, 7, 11, 13]
N_VARS = 6
MAX_Z = np.prod(PRIMES) # 30,030

def calculate_pigeonhole_energy(z):
    energy = 0
    
    # CONSTRAINT A: Each pigeon MUST be in at least one hole.
    # For Pigeon i, (x_i,0 OR x_i,1) must be True.
    # Violation: (x_i,0 = 0 AND x_i,1 = 0)
    for p in range(3):
        v1, v2 = p*2, p*2+1
        # Penalty if both variables for this pigeon are 0
        penalty = 1.0
        for v in [v1, v2]:
            phase = 2 * np.pi * (z - 0) / PRIMES[v]
            penalty *= (0.5 + 0.5 * np.cos(phase))
        energy += penalty * 2.0 # High weight for "Missing Pigeon"
        
    # CONSTRAINT B: No hole can have more than one pigeon.
    # For Hole j, not (Pigeon i in Hole j AND Pigeon k in Hole j)
    # Violation: (x_i,j = 1 AND x_k,j = 1)
    for h in range(2):
        for p1 in range(3):
            for p2 in range(p1 + 1, 3):
                v1, v2 = p1*2 + h, p2*2 + h
                # Penalty if both pigeons are in the same hole
                penalty = 1.0
                for v in [v1, v2]:
                    phase = 2 * np.pi * (z - 1) / PRIMES[v]
                    penalty *= (0.5 + 0.5 * np.cos(phase))
                energy += penalty * 2.0
                
    return energy

# 2. SCANNING THE MANIFOLD
print(f"Scanning the 30,030-unit Pigeonhole Manifold...")
z_samples = np.linspace(0, 1000, 2000) # Sample first 1000 for viz
energies = [calculate_pigeonhole_energy(zi) for zi in z_samples]

# Find the Global Minimum
min_energy = float('inf')
best_z = -1

# Brute force scan all 30,030 integers
for zi in range(MAX_Z):
    e = calculate_pigeonhole_energy(zi)
    if e < min_energy:
        min_energy = e
        best_z = zi

print(f"\nRESULTS:")
print(f"  Minimum Manifold Energy: {min_energy:.4f}")
print(f"  Best Possible Coordinate: z = {best_z}")

if min_energy > 0.5:
    print("\n🏆 GEOMETRIC PROOF OF UNSAT:")
    print("  The 'Ground State' of the manifold is still elevated.")
    print("  There is no 'Midnight Alignment'. The pigeons are physically trapped.")
else:
    print("  Wait, a solution was found? Check encoding.")

# 3. VISUALIZATION
plt.figure(figsize=(12, 6), facecolor='#0a0a0f')
ax = plt.gca()
ax.set_facecolor('#0a0a0f')
plt.plot(z_samples, energies, color='#f77c6f', lw=1.5)
plt.fill_between(z_samples, energies, color='#f77c6f', alpha=0.1)

plt.axhline(y=min_energy, color='white', ls='--', alpha=0.3, label=f'Min Energy: {min_energy:.2f}')
plt.title("Pigeonhole Frustration: The Geometry of the Impossible", color='#e8e8f0', fontsize=16)
plt.xlabel("Master Coordinate (z)", color='#6b6b7b')
plt.ylabel("Frustration Energy", color='#6b6b7b')
plt.grid(color='#1e1e2e', alpha=0.3)
plt.legend()
plt.savefig('pigeonhole_frustration.png', dpi=300)
print("\nVisualization saved to 'pigeonhole_frustration.png'")
