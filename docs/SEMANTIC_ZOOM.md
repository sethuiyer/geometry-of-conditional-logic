# Semantic Zoom: p-adic Distance vs Cosine Similarity

## The Failure

Standard embeddings measure semantic proximity via cosine similarity.
They cannot distinguish:

| Pair | Cosine | What they share |
|---|---|---|
| dog ↔ wolf | 0.757 | mammal, canine, same species group |
| dog ↔ bird | 0.752 | animate, living thing |

To cosine, these are the same. Both are "animals." Cosine has no **resolution** —
it measures proximity, not hierarchy.

This is why LLMs hallucinate. They operate in a continuous latent space where
"dog" can drift to "bird" because the gradient is flat. There is no geometric
reason to stay inside the canine manifold.

## The Fix

Hensel encoding maps each word to a 2-adic integer where bits at increasing
depth represent increasingly specific hierarchical commitments:

```
bit 0 (mod 2):    coarse category     (animate, artifact, ...)
bit 1 (mod 4):    mid category        (mammal, vehicle, ...)
bit 2 (mod 8):    fine category       (canine, automobile, ...)
bits 3+ (mod 16): word identity       (dog, wolf, ...)
```

The 2-adic distance d_2 = 2^{-v} measures how many consecutive bits match.
"dog" and "wolf" match at bits 0, 1, 2 → v = 3 → d = 0.125.
"dog" and "bird" match only at bit 0 → v = 1 → d = 0.500.

**4× separation where cosine sees near-identity.**

## Semantic Zoom

Cosine space is flat. Moving closer reveals no new structure — the space
is uniformly continuous.

p-adic space has **zoom**: as distance decreases (v increases), you unfold
deeper logical structure. Each factor of 2^{-1} reveals a new level of
hierarchical commitment:

| d_2 | Meaning |
|---|---|
| 1.0 | Different coarse categories |
| 0.5 | Same coarse, different mid |
| 0.25 | Same coarse+mid, different fine |
| 0.125 | Same coarse+mid+fine, different word |
| <0.125 | Same word or near-identical |

Distance is quantized. There is no "slightly closer" — either a hierarchy
level is shared or it isn't. This matches how symbolic systems actually behave.

## The Correction Layer

An LLM operating with cosine embeddings can drift within a semantic neighborhood
because the metric provides no corrective force. p-adic distance provides a
**geometric stabilizer**: if the model is reasoning about dogs, the p-adic
metric penalizes jumps to birds (d moves from 0.125 to 0.500), creating an
energy barrier that cosine doesn't see.

This is the same `z' = z + kM` spinal reflex applied to meaning. The lock
shield M preserves the deep hierarchical commitments (mammal, canine) while
allowing surface movement (wolf → fox).

## Experimental Confirmation

On Gutenberg-trained Word2Vec (41 hierarchy-annotated words):

| Depth | p-adic distance | Cosine range |
|---|---|---|
| 3 (same fine) | 0.125 | 0.420 - 0.757 |
| 2 (same mid) | 0.250 | 0.705 - 0.848 |
| 1 (same coarse) | 0.500 | 0.645 - 0.752 |
| 0 (different) | 1.000 | -0.143 - 0.342 |

p-adic at depth 3 is **perfectly separated** from all lower depths.
Cosine ranges overlap at every level.

## Relationship to the Runtime

| Domain | Lock shield M | Preserves |
|---|---|---|
| CPU scheduling | Product of locked cores | Warm caches |
| AST repair | Product of valid subtrees | Syntactic structure |
| Pharmacy inventory | Product of committed SKUs | Shelf positions |
| **Meaning** | **Bits at depth ≤ v** | **Hierarchical commitments** |

The same formula. The runtime computes `z' = z + kM` to preserve commitments
in scheduling. The Hensel encoding computes `d_2 = 2^{-v}` to preserve
commitments in meaning. The algebra is identical.

## Files

- `hensel_embeddings.py` — Experiment on Gutenberg Word2Vec
- `hensel_demo.py` — Minimal Hensel lifting demo
- `docs/HENSEL.md` — Theoretical development
- `nn_ultrametric.py` — Earlier hierarchy comparison (research/)
