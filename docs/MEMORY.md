# Ultrametric Memory for LLM Agents

## The Problem

Current LLM memory systems use **semantic similarity** — vector embeddings, cosine distance, BM25. These are great for topical relevance but systematically weak at:

- Long-term consistency (new facts contradict old commitments)
- Role preservation (agent context is scrambled across sessions)
- Symbolic continuity (plan state, dependency chains, workflow position)
- Structured reasoning memory (proof state, constraint topology)

The root cause: **semantic similarity does not measure structural compatibility.**

Your system can retrieve "Thai food" and "Tokyo restaurants" for a vegetarian user with peanut allergy, but it won't retrieve the **constraint topology** — dietary restrictions × travel context × prior commitments — that actually determines what's relevant.

## A Second Retrieval Geometry

| Retrieval type | Measures | Best for |
|---|---|---|
| Embeddings (cosine) | Semantic proximity | Topical relevance, paraphrases |
| BM25 | Token overlap | Keyword search |
| **Ultrametric** | **Preserved commitment hierarchy** | **Structural continuity, role preservation** |
| Graph | Dependency traversal | Causal chains, entity relations |

Ultrametric retrieval answers a different question from cosine:

> **Which memories preserve the deepest hierarchy relevant to the current state?**

Not "which memories are semantically nearby."

## How It Works for an Agent

The agent's memory is organized by **commitment layers**:

| Level | Feature | Example |
|---|---|---|
| 0 (deepest) | User identity & invariants | "vegetarian", "peanut allergy" |
| 1 | Active context domain | "travel planning", "Tokyo trip" |
| 2 | Interaction role | "restaurant recommendation" |
| 3 | Prior commitments | "already booked Ramen shop Tuesday" |
| 4 | Surface tokens | "Thai food", "Tokyo restaurants" |

A new query enters. Instead of a single vector lookup, the system computes:

```
v_R(query, memory) = how many consecutive levels share structure
d_R = 2^{-v_R}
```

A memory about "Ramen reservation on Tuesday" shares levels 0-2 with a query about "dinner suggestions in Shinjuku" — same user, same trip, same restaurant domain. It gets promoted even if surface tokens don't overlap.

A memory about "Thai food in Bangkok from last year" shares only level 0 — different trip, different city. It gets deprioritized despite high cosine similarity.

## Memory Repair vs Memory Overwrite

Current systems handle contradictions by overwriting:

```
new fact: "user likes Thai food"
embedding update → old food preferences displaced
```

Ultrametric memory supports **minimal repair**:

```
new fact: "user now prefers Japanese food"
↓
1. Lock levels 0-1 (user identity, travel context)
2. Update level 3 (cuisine preference)
3. Preserve all other commitments
4. d_R( old_state, new_state ) = 2^{-2} = 0.25 (shallow repair)
```

The depth of the repair measures how much of the memory structure survived. A preference change is shallow. A user identity change is deep.

This is memory with **rollback semantics** — you can undo to any previous commitment depth without recomputing from scratch.

## Concrete Agent Architecture

```
Query
  ↓
[Feature extractor]  →  levels 0..4
  ↓
[Ultrametric index]  →  rank by d_R
  ↓
[CRT jump]           →  if updating memory, preserve locked levels
  ↓
[Top-k memories]     →  passed to LLM context
  ↓
[LLM]                →  generate response
  ↓
[Repair engine]      →  if response changes state, compute minimal repair
```

The LLM does what it's best at — language generation, semantic interpolation. The ultrametric layer does what it's best at — structural continuity, commitment preservation.

## Where This Matters

### Persistent agents
Agents need stable world models with bounded updates. Ultrametric memory naturally enforces: "core facts don't change without deep repair."

### Planning memory
Retrieve structurally compatible plans, not semantically nearby text. A plan failure in domain X should retrieve structurally similar failures from domain Y — same dependency topology, different surface details.

### Code assistants
Retrieve code by architectural role and dependency topology, not by API name overlap. Same error-handling structure, different function names.

### Long-term user modeling
Memory organized by preserved commitments — stable dietary restrictions, travel patterns, interaction roles — not by recency-biased vector embeddings.

### Theorem proving / reasoning
Retrieve proofs by implication structure and dependency depth, not by symbol overlap. Same forward-chaining topology, different domain vocabulary.

## Relationship to Existing Work

- **RAG / vector retrieval**: semantic similarity. Ultrametric is complementary — a second retrieval pass that re-ranks by structural preservation.
- **Graph memory / knowledge graphs**: explicit relations. Ultrametric provides a distance metric over the graph structure.
- **Hyperbolic memory**: tree-like embeddings. Ultrametric is symbolic rather than learned — the hierarchy levels are explicit features, not latent dimensions.
- **MemWalker / MemGPT**: long-term memory for LLMs. Ultrametric adds structure-sensitive retrieval — what survives, not what's nearby.

## Claim

> Semantic similarity is not sufficient for memory in structured reasoning systems. Ultrametric distance over feature hierarchies provides a complementary retrieval geometry that respects preserved commitments, role continuity, and structural compatibility.

This is not hypothetical. The Gutenberg experiment proved the retrieval gap empirically — BM25 depth=1.38 vs ultrametric depth=3.73 across 750 real documents. The same hierarchy applies to agent memory, code retrieval, and planning recall.

## Files

- `ultrametric_gutenberg.py` — empirical proof on real text (+2.35 depth layers vs BM25)
- `ultrametric_retrieval.py` — synthetic corpus verification
- `STRUCTURAL_RETRIEVAL.md` — cross-domain failure pattern analysis
- `AI.md` — general architecture for ultrametric retrieval systems
