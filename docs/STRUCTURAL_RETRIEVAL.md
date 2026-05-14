# Structural Retrieval: Why Ultrametric > BM25

## The Failure Pattern

BM25 and cosine retrieval fail in the same way across every domain:
they match **surface tokens** and miss **structural incompatibility**.

| Domain | Lexical hit | Structural miss |
|---|---|---|
| Code search | Same APIs, same function names | Wrong architecture pattern |
| Theorem proving | Same symbols, same keywords | Wrong proof structure |
| Planning | Same action names | Wrong causal topology |
| Workflows | Same step labels | Wrong dependency graph |
| Debugging | Same error text | Wrong failure mode |
| Literature | Same words ("drink", "talk") | Wrong book, wrong voice, wrong entities |

The Gutenberg experiment quantified this: BM25 retrieves Moby Dick paragraphs
for an Austen query because "drink" and "rather" co-occur. Ultrametric distance
checks the entire structural fingerprint — book source → entity types →
dependency patterns → content words → surface — and never makes that mistake.

## What Ultrametric Checks That BM25 Doesn't

| Level | Feature | What it catches |
|---|---|---|
| Book source | Which document/domain | Cross-domain pollution |
| Named entities | PERSON, ORG, GPE, DATE | Wrong characters, wrong setting |
| Dependency patterns | (nsubj, VERB) signatures | Wrong interaction structure |
| Content words | Nouns, verbs, adjectives | Wrong topical vocabulary |
| Surface tokens | All words (last resort) | Token overlap (what BM25 uses) |

Ultrametric distance requires agreement at the deepest levels first.
Surface token overlap alone can never promote a structurally irrelevant result.

## Where This Matters

### Code search
Query: "async retry with exponential backoff and circuit breaker"
- BM25 finds: any code mentioning "async" + "retry" + "backoff"
- Ultrametric finds: code with the same **error-handling architecture** —
  retry topology, state machine structure, fallback chain depth

### Theorem proving
Query: "compactness implies uniform continuity on metric spaces"
- BM25 finds: any text with "compactness" + "uniform continuity" + "metric"
- Ultrametric finds: proofs preserving the same **implication structure** —
  forward chaining depth, lemma dependency order, quantifier scope

### Planning
Query: "deploy canary → monitor → rollback on failure"
- BM25 finds: any workflow with "deploy" + "monitor" + "rollback"
- Ultrametric finds: plans with the same **causal topology** —
  branching structure, guard conditions, rollback propagation radius

### Debugging
Query: "segfault in malloc after double free"
- BM25 finds: any ticket mentioning "segfault" + "malloc" + "double free"
- Ultrametric finds: bugs with the same **memory error pattern** —
  allocation lifetime, free chain depth, dangling pointer topology

## The Claim

> Surface token overlap is a weak proxy for relevance in structured domains.
> Ultrametric distance over hierarchical feature levels provides a principled
> alternative that respects domain structure.

This is not hypothetical. The Gutenberg experiment proves it on real text.
The same hierarchy applies to any domain with decomposable structure.

## Files

- `ultrametric_gutenberg.py` — 750 docs, 5 books, BM25 depth=1.38 vs Ultra depth=3.73
- `ultrametric_retrieval.py` — synthetic corpus, BM25 depth=1.28 vs Ultra depth=3.00
- `AI.md` — architecture for ultrametric retrieval in general systems
