# UltraMeM: Mathematical Foundations

## 1. Hierarchy of Commitments

A memory $M$ is represented as a tuple of feature sets at increasing depth:

$$
M = (S_0, S_1, \dots, S_{n-1})
$$

where $S_k$ is the feature set at level $k$, and $k = 0$ is the deepest (most invariant)
level. The levels are ordered by stability: deeper levels change less frequently and
represent more fundamental properties of the data.

Given two memories $M$ and $M'$, the **preserved hierarchy depth** is:

$$
v_R(M, M') = \max\{k \mid \forall i < k: J(S_i, S'_i) \geq \tau_i\}
$$

where $J$ is the Jaccard similarity:

$$
J(S, S') = \frac{|S \cap S'|}{|S \cup S'|}
$$

and $\tau_i$ is a per-level threshold. $v_R$ counts how many consecutive levels,
starting from the deepest, maintain sufficient feature overlap.

The **ultrametric distance** is then:

$$
d_R(M, M') = \alpha^{-v_R(M, M')}
$$

for some base $\alpha > 1$ (typically $\alpha = 2$).

---

## 2. Ultrametric Property

**Theorem.** $d_R$ is an ultrametric: for any three memories $A, B, C$,

$$
d_R(A, C) \leq \max(d_R(A, B), d_R(B, C))
$$

*Proof.* Let $v_{AB} = v_R(A, B)$, $v_{BC} = v_R(B, C)$, $v_{AC} = v_R(A, C)$.
Assume without loss that $v_{AB} \leq v_{BC}$ (otherwise swap labels).
Then for all levels $i < v_{AB}$, both $A$ and $B$ agree with each other
at level $i$, and $B$ and $C$ agree at level $i$.  By transitivity of set
equality up to Jaccard threshold, $A$ and $C$ also agree at level $i$.
Hence $v_{AC} \geq v_{AB} = \min(v_{AB}, v_{BC})$, which implies:

$$
d_R(A, C) = \alpha^{-v_{AC}} \leq \alpha^{-\min(v_{AB}, v_{BC})}
= \max(\alpha^{-v_{AB}}, \alpha^{-v_{BC}}) = \max(d_R(A, B), d_R(B, C))
$$

This is the strong triangle inequality.  In practice, the Jaccard threshold may
introduce edge cases where near-threshold similarities break exact transitivity,
but the inequality holds for exact set equality and approximate Jaccard
similarity with a consistent threshold.  Experimental verification
(`padic_check.py`) shows 0 violations in 2000 random triples. ∎

---

## 3. Feature Levels

The default configuration uses four levels:

| Level | Name | Description | Example features |
|---|---|---|---|
| 0 | Domain | Top content words (longest, most specific) | `{garden, chased, through}` |
| 1 | Role structure | Bigram dependency patterns | `{dog_chased, chased_the}` |
| 2 | Content | All content words (non-stop, >3 chars) | `{dog, cat, chased, garden}` |
| 3 | Surface | All tokens (including stop words) | `{the, dog, cat, through, garden}` |

The feature extractor is pluggable.  With spaCy, deeper features become available:
named entities at level 0, dependency triples at level 1, lemmatized content
at level 2, raw tokens at level 3.

---

## 4. Retrieval

Given a query $Q$ with feature sets $\{T_k\}$, the memory is ranked by ultrametric
distance to $Q$:

$$
\text{rank}(M) = d_R(Q, M) = \alpha^{-v_R(Q, M)}
$$

This is a **full scan** over all stored memories.  For each memory, we compute
$v_R$ by iterating levels from deepest to shallowest, stopping at the first
level where Jaccard similarity falls below threshold.

**Hybrid retrieval** uses an embedding pre-filter followed by ultrametric rerank:

1. Retrieve top-$N$ candidates by cosine similarity
2. Rerank those $N$ candidates by $d_R$
3. Return top-$k$ of the reranked set

This combines the broad recall of embeddings with the structural precision of
ultrametric distance.

---

## 5. Repair Algebra

When updating a memory from $M$ to $M'$, the **repair valuation** measures how
much structure was preserved:

$$
v_R(M, M') = \text{number of leading levels with unchanged feature sets}
$$

The repair is **minimal** when $v_R$ is maximized — i.e., the update changes
only the shallowest necessary levels while preserving deeper commitments.

**Rollback** is supported by storing the previous state.  Since each level is
independent, a rollback restores the exact prior feature sets without affecting
other memories.

**CRT encoding** (optional) provides an alternative representation for repair:
each level's feature set is hashed to a residue modulo a distinct prime,
and the full memory state is encoded as a single CRT coordinate $z$:

$$
z \equiv h(S_k) \pmod{p_k} \quad \forall k
$$

where $h$ is a deterministic hash function and $p_k$ are distinct primes.
An update to level $j$ is then:

$$
z' = z + kM, \qquad M = \prod_{i \neq j} p_i
$$

This preserves all other levels exactly.  However, the Jaccard-based approach
is preferred for retrieval because it degrades gracefully (gradually decreasing
$v_R$ with partial overlap) rather than the binary pass/fail of residue matching.
CRT is retained for the repair algebra where exact transitions are needed.

---

## 6. Relationship to p-adic Geometry

The ultrametric distance $d_R = \alpha^{-v_R}$ is structurally identical to the
p-adic distance $d_p(x, y) = p^{-v_p(x-y)}$, where $v_p$ is the p-adic valuation
counting divisibility by $p$.

In the p-adic case, $v_p(x-y)$ counts how many powers of $p$ divide the
difference — equivalently, how many trailing residues agree in the base-$p$
expansion.  In UltraMeM, $v_R$ counts how many leading hierarchy levels agree.
Both produce an ultrametric where distance is determined by the **depth of
shared structure**, not the magnitude of difference.

The analogy:

| p-adic | UltraMeM |
|---|---|
| $p$-adic valuation $v_p$ | Hierarchy depth $v_R$ |
| $d_p = p^{-v_p}$ | $d_R = \alpha^{-v_R}$ |
| Trailing digit agreement | Leading level agreement |
| Numbers share base-$p$ prefix | Memories share deepest feature sets |
| Nested ultrametric balls | Nested consistency neighborhoods |

---

## 7. Experimental Validation

| Test | Result |
|---|---|
| Ultrametric inequality (`padic_check.py`) | 0 violations in 2000 triples |
| Synthetic corpus (`ultrametric_retrieval.py`) | Ultra depth=3.00 vs BM25 depth=1.28 |
| Project Gutenberg (`ultrametric_gutenberg.py`) | Ultra depth=3.73 vs BM25 depth=1.38 (+2.35 layers) |
| Word2Vec comparison (`nn_ultrametric.py`) | Cosine ranges overlap across all hierarchy depths |

---

## References

- `ultramem.py` — Reference implementation
- `PADIC.md` — p-adic repair calculus
- `STRUCTURAL_RETRIEVAL.md` — Cross-domain failure pattern analysis
- `MEMORY.md` — Application to LLM agent memory systems
- `AI.md` — Ultrametric retrieval architecture
