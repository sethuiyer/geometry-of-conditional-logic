#!/usr/bin/env python3
"""
Hensel Lifting Demo: Graded Commitment Depth
=============================================
A single prime p at increasing powers creates nested commitment balls.
Shallow commitments (mod p) are easy to change.
Deep commitments (mod p^k) are hard to disturb.

Repair naturally preserves the deepest valid structure.
"""


def show(z, label=""):
    print(f"  {label:12s} z = {z:4d}  |  "
          f"mod 5 = {z % 5}  mod 25 = {z % 25:2d}  mod 125 = {z % 125:3d}")


def repair(z, preserve_mod):
    """
    Find the nearest z' > z that preserves z mod `preserve_mod`.
    Simple: add preserve_mod to move to the next value in the same residue class.
    """
    return z + preserve_mod


print("=" * 70)
print("HENSEL LIFTING: NESTED COMMITMENT BALLS")
print("Single prime p=5 at increasing powers")
print("=" * 70)

# Initial state: task at exact slot 58
z = 58
print("\n--- Initial State ---")
show(z, "original")
print("  Commitments:")
print("    region (mod 5):   ", z % 5, "(deepest commitment)")
print("    rack   (mod 25):  ", z % 25)
print("    slot   (mod 125): ", z % 125, "(shallowest)")

# Small perturbation: local CPU slot dies,
# Same rack + region must survive (preserve mod 25)
z1 = repair(z, preserve_mod=25)
print("\n--- Small Repair: local slot dies, same rack ---")
show(z, "before")
show(z1, "after")
print("  Preserved: region ✓  rack ✓  slot changed")
print("  Distance d_5(z, z') = 5^{-2} = 0.04")

# Medium perturbation: entire rack fails
# Same region must survive (preserve mod 5)
z2 = repair(z, preserve_mod=5)
print("\n--- Medium Repair: rack fails, same region ---")
show(z, "before")
show(z2, "after")
print("  Preserved: region ✓  rack ✗  slot ✗")
print("  Distance d_5(z, z') = 5^{-1} = 0.20")

# Large perturbation: everything changes
z3 = 42
print("\n--- Large Change: all new ---")
show(z, "before")
show(z3, "after")
print("  Preserved: nothing")
print("  Distance d_5(z, z') = 5^{-0} = 1.00")

# ─────────────────────────────────────────────
# Systematic demonstration
# ─────────────────────────────────────────────

print("\n" + "=" * 70)
print("SYSTEMATIC: 5-adic refinement ladder")
print("=" * 70)

# Start from z=0 and refine at each depth
z = 0
for depth in range(4):
    modulus = 5 ** (depth + 1)
    target_value = (3 * 25 + 8 * 5 + 2) % modulus
    # Lift to next depth: find z' with desired residue mod modulus
    # while preserving all previous residues
    z = z + ((target_value - z) % modulus)
    print(f"  depth {depth}: mod {modulus:3d} = {z % modulus:2d}  →  z = {z}")

# ─────────────────────────────────────────────
# Hierarchical search
# ─────────────────────────────────────────────

print("\n" + "=" * 70)
print("HIERARCHICAL REPAIR SEARCH")
print("=" * 70)


def hierarchical_repair(z, min_preserve_depth):
    """
    Find nearest valid z' that preserves commitments down to min_preserve_depth.
    depth 2 = preserve mod 25 (rack)
    depth 1 = preserve mod 5 (region)
    depth 0 = preserve nothing
    """
    preserve_mod = 5 ** min_preserve_depth
    if preserve_mod == 1:
        return z + 1  # any change
    # Add preserve_mod: moves to next value in the same residue class
    return z + preserve_mod


# Simulate a repair cascade
z = 58
for depth in [2, 1, 0]:
    z_new = hierarchical_repair(z, depth)
    preserved = []
    for d in [1, 2, 3]:
        mod = 5 ** d
        if z_new % mod == z % mod:
            preserved.append(f"mod {mod}")
    print(f"  preserve depth ≥ {depth}: z={z} → {z_new:4d}, preserved: {', '.join(preserved)}")
