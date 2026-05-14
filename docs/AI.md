# Ultrametric Repair Calculus for Structured Reasoning

## The Core Distinction

Current ML models similarity. Neural embeddings map inputs to a latent space where
"closeness" means statistical co-occurrence — smooth semantic proximity.

This framework models **survivability of structure under change**. Ultrametric distance
measures how many layers of symbolic commitment survive a substitution or repair.

These are different spaces.

| | Neural embeddings | Ultrametric repair |
|---|---|---|
| Measures | smooth semantic proximity | preserved symbolic hierarchy |
| Geometry | Euclidean / cosine manifold | ultrametric tree |
| Behavior | small perturbation = small vector change | small distance = deep shared structure |
| Scope | interpolation, pattern recognition | rollback, consistency, bounded repair |

The mature position: not "replace deep learning," but **add a missing notion of
hierarchical consistency-preserving structure** that neural methods alone don't
capture.

---

## Why This Matters

### 1. Reasoning Systems

LLM reasoning often rewrites large context windows, loses earlier commitments, and
drifts inconsistently. The ultrametric repair calculus asks a different question:

> What is the minimal repair that restores consistency?

This is a fundamentally different operation from "regenerate everything." It matters
for theorem proving, planning, multi-step reasoning, and agent memory consistency.

### 2. Memory Systems

Vector retrieval is based on semantic similarity. But human memory retrieval is
hierarchical — organized by preserved structure, dependency chains, and relevance
depth. Ultrametric retrieval naturally supports:

- Layered memory neighborhoods (shallow recall vs deep structural recall)
- Rollbackable memory edits (undo without recomputation)
- Stable world-model updates (preserve core facts, revise periphery)

### 3. World Models / Agents

Agents constantly face the problem:

```
new observation → update beliefs without breaking stable commitments
```

That is literally local repair. Most agents handle this heuristically. The framework
provides explicit repair geometry, disturbance metrics, and invariant preservation
semantics.

### 4. Neuro-Symbolic Systems

The hard problem in neuro-symbolic AI is: how do learned representations interact
with exact symbolic constraints? The architecture cleanly separates:

| Layer | Responsibility |
|---|---|
| Neural net | propose updates, learn priorities |
| Repair calculus | enforce consistency, preserve invariants |

### 5. Attention / Routing

Transformers exhibit clustered activation structure and layered abstraction.
Ultrametric metrics may help with hierarchical token routing, memory pruning,
tree-structured reasoning, and retrieval organization.

---

## The Stack

```
┌─────────────────────────────────────────────┐
│ Neural embeddings (propose, prioritize)      │
├─────────────────────────────────────────────┤
│ Matching / flow (compute minimal repair)     │
├─────────────────────────────────────────────┤
│ CRT (exact invariant-preserving jump)        │
├─────────────────────────────────────────────┤
│ p-adic metric (hierarchical locality)        │
├─────────────────────────────────────────────┤
│ Actors (distributed execution)               │
└─────────────────────────────────────────────┘
```

---

## Ultrametric Retrieval Architecture

A concrete design for retrieval that uses ultrametric distance instead of cosine.

### Core Idea

Documents / memories are indexed not by embedding vectors alone, but by their
**commitment structure** — a hierarchy of features at increasing depth.

A query `Q` and a document `D` share depth `v` if they agree on the first `v`
levels of feature hierarchy. The ultrametric distance is:

```
d_R(Q, D) = base^{-v_R(Q, D)}
```

Retrieval returns documents with smallest `d_R` — i.e., those sharing the deepest
feature structure with the query.

### Feature Hierarchy

Levels are ordered by stability (deepest = most invariant):

| Level | Feature type | Example |
|---|---|---|
| 0 (deepest) | Domain ontology | mathematical, biological, legal |
| 1 | Relational roles | subject/object/agent structure |
| 2 | Entity categories | animate/inanimate, concrete/abstract |
| 3 | Attribute predicates | color, size, material |
| 4 (shallowest) | Surface form | specific words, formatting |

Each level maps to a prime modulus. A document is encoded as a CRT coordinate `z`
where residue at prime `p_i` = the feature value at level `i`.

### Index Structure

```
document (raw text)
    ↓ feature extraction (NN classifier)
feature vector [f_0, f_1, ..., f_k]
    ↓ CRT encoding
z = crt_encode(features, primes)
    ↓ store
key: doc_id → value: (z, raw_text, metadata)
```

### Query Processing

```
query Q
    ↓ feature extraction
query_features [q_0, q_1, ..., q_k]
    ↓ CRT encoding
z_q = crt_encode(query_features, primes)
    ↓ ultrametric scan
for each document (z_d, ...):
    v = repair_valuation(z_q, z_d, primes)
    d = base^{-v}
    if d < threshold: include
    ↓ sort by d (ascending = deepest shared structure)
return ranked results
```

### Properties

1. **Hierarchical**: A document matching at level 2 (distance = 0.25) is closer
   than one matching only at level 0 (distance = 1.0), regardless of surface form.

2. **Quantized**: Distances take discrete values `base^{-v}`. There is no "slightly
   closer" — either a level matches or it doesn't. This matches how symbolic systems
   actually behave.

3. **Incremental**: Adding levels doesn't change existing distances — it just adds
   deeper balls. Compatible with the p-adic valuation property.

4. **Rollbackable**: If a document's features are updated, the old `z` can be
   preserved for comparison. CRT jumps enable atomic feature edits.

### Hybrid with Cosine

In practice, the best system uses both:

```
query Q
    ↓
cosine pre-filter: get top 100 semantic neighbors
    ↓
ultrametric re-rank: sort by d_R(Q, D)
```

The neural embedding provides a fast recall set. The ultrametric metric provides
a precision ranking that respects hierarchical structure.

### Implementation Sketch

```python
class UltrametricIndex:
    def __init__(self, primes, hierarchy_levels):
        self.primes = primes          # one prime per hierarchy level
        self.hierarchy = hierarchy_levels  # feature extractor functions
        self.docs = {}                # doc_id → (z, metadata)

    def add_document(self, doc_id, text):
        features = [level(text) for level in self.hierarchy]
        z = crt_encode(features, self.primes)
        self.docs[doc_id] = (z, text)

    def search(self, query, base=2, top_k=10):
        q_features = [level(query) for level in self.hierarchy]
        z_q = crt_encode(q_features, self.primes)
        results = []
        for doc_id, (z_d, text) in self.docs.items():
            v = repair_valuation(z_q, z_d, self.primes)
            d = base ** (-v)
            results.append((d, v, doc_id, text))
        results.sort(key=lambda x: x[0])
        return results[:top_k]
```

### Open Questions

1. **Feature extraction.** How do you learn the hierarchy levels? NN classifiers
   could predict each level. The hierarchy itself could be learned or hand-defined
   per domain.

2. **Indexing at scale.** A full scan over all documents works for small indices.
   For large scale, the tree structure of ultrametric spaces enables efficient
   indexing — organize documents by their feature prefix (v-adic tree).

3. **Hybrid weighting.** When to trust cosine vs ultrametric? A learned gating
   mechanism could weight each based on the query type.

4. **Dynamic hierarchy.** If the hierarchy levels change (new categories added),
   the CRT encoding is monotonic — add new primes for new levels, old distances
   remain valid.

---

## Relationship to Existing Work

- **Hyperbolic embeddings** (Nickel & Kiela, 2017): Learn tree-like geometry for
  hierarchical data. Our approach is symbolic rather than learned — hierarchy is
  explicit, not latent.

- **p-adic NLP** (Benedetto et al., 2021): p-adic metrics for text classification.
  Our contribution is the operational repair calculus, not just the metric.

- **Memory retrieval in transformers** (RETRO, RAG): Retrieve from external memory
  by semantic similarity. Ultrametric retrieval adds structure-awareness.

- **Neuro-symbolic AI** (Garnelo & Shanahan, 2019): Reconciling neural learning
  with symbolic reasoning. Our framework provides an explicit consistency layer.

---

## Defensible Claim

> Hierarchical local repair may be an important missing primitive for structured
> reasoning systems, complementing neural methods with exact consistency
> preservation, bounded disturbance, and ultrametric locality.

Not "p-adics solve intelligence." Not "replace deep learning."

The claim is that:

- neural nets excel at fuzzy semantic proximity,
- ultrametric repair excels at hierarchical consistency preservation,
- and systems that need both (reasoning, memory, agents, planning) benefit from
  combining them explicitly.

---

## Files

- `nn_ultrametric.py` — Word2Vec cosine vs ultrametric comparison (verified overlap)
- `padic_check.py` — ultrametric inequality verification (2000 triples, 0 violations)
- `padic_problem.py` — patch-vs-violate DP with ultrametric cost
- `padic_sudoku.py` — flagship solver with per-move valuation tracking
- `NEURAL.md` — neural + ultrametric bridge
- `PADIC.md` — formal p-adic repair calculus
