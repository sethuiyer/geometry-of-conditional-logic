# Hensel Lifting: Depth-Sensitive Commitments

## The Upgrade

CRT gives flat parallel consistency:

```
x ≡ a₁ (mod p₁)
x ≡ a₂ (mod p₂)
x ≡ a₃ (mod p₃)
```

Each residue is a binary commitment — locked or not. There's no notion of depth.

Hensel lifting gives hierarchical refinement:

```
x ≡ a   (mod p)
x ≡ a'  (mod p²)
x ≡ a'' (mod p³)
```

Each lift strengthens the commitment. The same variable can be:

- **Weakly locked** (mod p — shallow preference)
- **Moderately locked** (mod p² — meaningful constraint)
- **Deeply locked** (mod p³ — almost immutable)

Repair radius becomes depth-sensitive. A perturbation respects deep locks
aggressively while allowing shallow movement freely.

## The Mapping

| CRT | Hensel / p-adic |
|---|---|
| Flat residues | Hierarchical refinement |
| Binary lock/unlock | Depth-graded commitment |
| Parallel consistency | Nested consistency balls |
| Shield M = ∏ p_i | Shield M = ∏ p_i^{k_i} |
| Repair radius = count | Repair radius = depth-weighted sum |

## How It Changes Repair

In CRT-only repair:

```
z' = z + kM,  M = ∏ p_i
```

Every locked prime contributes equally to the shield. Breaking any single
lock costs the same as breaking any other.

With Hensel lifting:

```
M_depth = ∏ p_i^{d_i}
```

where d_i is the commitment depth of lock i. Deeper locks have higher
exponents, making M larger and the CRT jump "farther" — meaning the
solver preferentially preserves deep locks over shallow ones.

The repair valuation becomes depth-weighted:

```
v_R(z, z') = sum of depths of preserved commitments
```

Not just count — weighted by how deep each commitment was.

## Example

In AST repair:

| Commitment | CRT depth | Hensel depth |
|---|---|---|
| Indentation style | — | 1 (mod 2) |
| Variable name | p₁ | 2 (mod 4) |
| Function signature | p₂ | 3 (mod 8) |
| Module structure | p₃ | 4 (mod 16) |

When a perturbation arrives (LLM suggests a rename), the repair engine:

1. Locks module structure at depth 4 — won't touch it unless forced
2. Analyzes function signature at depth 3 — may adjust if needed
3. Considers variable name at depth 2 — flexible
4. Ignores indentation at depth 1 — can freely reformat

The solver naturally prefers repairs that preserve deeper commitments.

## Relationship to Ultrametric Distance

The p-adic valuation v_p already measures divisibility depth. Hensel lifting
makes this operational: the depth of a commitment is the exponent of p in
the shield. The ultrametric distance between two states:

```
d(z, z') = p^{-v_p(z - z')}
```

naturally extends to:

```
d(z, z') = p^{-min(v_p(z - z'), max_depth)}
```

Two states that differ only in shallow commitments (low p-adic depth) are
close. States that differ in deep commitments (high p-adic depth) are far.

## Implementation Sketch

```python
class HenselCommitment:
    """A commitment with depth."""
    
    def __init__(self, prime, value, depth=1):
        self.p = prime          # the prime modulus
        self.value = value      # locked value
        self.depth = depth      # 1 = shallow, 3+ = deep
    
    def contribution_to_shield(self):
        """p^depth contributes more to M than p^1."""
        return self.p ** self.depth

class HenselRepairRuntime:
    def shield(self, commitments):
        M = 1
        for c in commitments:
            M *= c.contribution_to_shield()
        return M
    
    def repair(self, z, target_var, target_val, commitments):
        """CRT jump with depth-weighted shield."""
        M = self.shield(commitments)
        p_t = target_var.prime
        k = ((target_val - z) * pow(M % p_t, -1, p_t)) % p_t
        return z + k * M
```

The shield is larger for deep commitments, making the CRT jump "harder"
to accidentally disturb them. The solver naturally finds repairs that
preserve deep structure.

## Next Steps

- Build HenselCommitment into LocalCRTGroup
- Test on a 3-level AST repair (whitespace vs signature vs structure)
- Compare Hensel depth-weighted repair vs flat CRT on the repair benchmark

The algebra is clean. The motivation is clear. It matches the p-adic
ultrametric geometry already in the repo. The question is whether the
practical improvement justifies the complexity.
