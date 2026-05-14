# Neural + Ultrametric: Empirical Bridge

## The Core Distinction

Word embeddings (Word2Vec, GloVe, etc.) learn **smooth semantic proximity** — cosine similarity between vectors. Two words are "close" if they co-occur in similar contexts.

Ultrametric repair distance measures **preserved symbolic hierarchy** — how much structured commitment survives a substitution. Two words are "close" if replacing one with the other preserves deep layers of semantic classification.

These are fundamentally different geometries.

## Experiment

`nn_ultrametric.py` compares both metrics on 30 word pairs across three hierarchy depths:

| Hierarchy depth | Example | Cosine range | Ultrametric d |
|---|---|---|---|
| v=3 (same fine) | dog→wolf, cat→tiger | 0.36 – 0.76 | 0.125 |
| v=2 (same mid) | ran→walked, dog→bird | 0.00 – 0.72 | 0.25 |
| v=1 (same coarse) | dog→car, ran→ate | -0.11 – 0.75 | 0.5 |
| v=0 (diff coarse) | dog→democracy, car→love | -0.14 – 0.34 | 1.0 |

**Result:** Cosine ranges overlap heavily between adjacent hierarchy levels. "dog→wolf" (v=3, cos=0.76) and "dog→bird" (v=1, cos=0.75) are indistinguishable by cosine. The metric cannot tell a fine-grained substitution from a coarse category break.

Ultrametric distance, by construction, quantizes to `2^{-v}` — it measures preserved commitment depth, not continuous proximity.

## The Distinction

| | Cosine / Euclidean | Ultrametric |
|---|---|---|
| Measures | smooth semantic proximity | preserved symbolic hierarchy |
| Geometry | continuous latent space | discrete ultrametric tree |
| Behavior | small perturbation ≠ shallow change | distance = depth of shared structure |
| Gradient | differentiable everywhere | quantized (2^{-v}) |
| Captures | statistical co-occurrence | structural compatibility |

## Hybrid Architecture

The mature framing is not "replace embeddings with CRT." It is a clean systems split:

| Layer | Role |
|---|---|
| Neural nets | learn semantic priors, repair policies, topology embeddings |
| Matching / flow | compute minimal repair path |
| CRT | exact invariant-preserving displacement |
| p-adic metric | hierarchical locality geometry |
| Actors | distributed execution |

The neural net handles fuzzy pattern recognition. The ultrametric repair layer enforces exact symbolic consistency. This is differentiable symbolic repair — a plausible bridge between continuous learning and structured discrete reasoning.

## Open Questions

1. **Can ultrametric embeddings be learned?** Is there a training objective that yields latent spaces where distance = preserved hierarchy depth, not co-occurrence frequency?

2. **Does language have latent ultrametric structure?** Attention graphs in transformers form hierarchical clusters. Do reasoning traces naturally satisfy ultrametric inequality?

3. **Repair policy learning.** Can a neural net learn when to patch individual elements vs violate a deep consistency level (the DP from `padic_problem.py`)?

4. **Differentiable p-adic valuation.** Can `v_R(z, z')` be softened into a differentiable surrogate for end-to-end learning?

## Files

- `nn_ultrametric.py` — Word2Vec vs ultrametric distance experiment (gensim, 30 word pairs, hierarchy tree)
- `padic_check.py` — ultrametric inequality verification (2000 random triples, zero violations)
- `padic_problem.py` — patch-vs-violate DP with ultrametric cost structure
- `padic_sudoku.py` — flagship p-adic Sudoku solver with per-move valuation tracking
- `PADIC.md` — formal development of the p-adic repair calculus
