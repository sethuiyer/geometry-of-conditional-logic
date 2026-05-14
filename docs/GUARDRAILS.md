# The Brain and the Spinal Cord

## The Architecture

An LLM proposes. The Geometric IF-ELSE runtime disposes.

The LLM is the **creative brain** — it generates ideas, suggests changes, hypothesizes refactors, proposes configurations. It's fuzzy, probabilistic, creative, and occasionally wrong.

The repair runtime is the **spinal cord** — it enforces the physics of the code. When the LLM proposes moving a service from zone 2 to zone 1, the runtime computes the exact cascade of dependency repairs required. It locks what doesn't need to change. It rolls back what can't be satisfied. It returns the nearest valid state.

The LLM never writes code directly. It writes **perturbations**.

```
┌─────────────────────────────────────────────────┐
│  LLM (Creative Brain)                           │
│  "What if we move the DB to zone 3?"            │
│  "What if we rename this function?"             │
│  "What if we extract this into a microservice?" │
└──────────────────────┬──────────────────────────┘
                       │ perturbation
                       ▼
┌─────────────────────────────────────────────────┐
│  Geometric IF-ELSE (Spinal Cord)                │
│  1. Lark parses current state → AST topology    │
│  2. Perturbation applied to target node         │
│  3. Lock shield M = all unaffected nodes        │
│  4. Cascade unlock through overlap edges        │
│  5. CRT jump computes minimal valid repair      │
│  6. Rollback if no valid state exists           │
│  7. Return repaired AST topology                │
└──────────────────────┬──────────────────────────┘
                       │ valid state
                       ▼
┌─────────────────────────────────────────────────┐
│  Output: code/DSL/config that satisfies         │
│  all constraints with minimal disturbance       │
└─────────────────────────────────────────────────┘
```

## What This Solves

LLM code generation has a fundamental problem: **fluency without fidelity**. The model produces plausible code that often violates constraints — type errors, broken imports, inconsistent naming, violated business rules, unsafe configurations.

Existing approaches handle this by:
- Generating multiple candidates and filtering
- Asking the LLM to self-correct
- Throwing parser errors and retrying

All of these discard the valid structure the LLM got right and regenerate from scratch.

The geometric approach handles it by:
- Treating the LLM output as a **perturbation** to the current valid state
- **Locking** everything the LLM got right
- **Repairing** only what it broke
- Returning the **nearest valid state**

This is mathematically guaranteed to preserve the maximum amount of valid structure. The LLM never needs to regenerate what it already got right.

## Mathematical Guardrails

The key property: **the runtime refuses to produce invalid states**.

When the LLM proposes a change that makes the constraint system unsatisfiable, the runtime rolls back and reports the impossibility. This is not a soft heuristic — it's an algebraic guarantee. The LLM can't hallucinate a state that violates the grammar, the type system, or the business rules, because the runtime won't execute the jump.

This is the same property that gave the traffic controller 7/7 safety scenarios passed. Unsafe states are geometrically unreachable.

## What Changes

| Without guardrails | With geometric guardrails |
|---|---|
| LLM generates code, may be invalid | LLM generates perturbations, runtime validates |
| Error → regenerate from scratch | Error → rollback to last valid state |
| Every generation is independent | Every generation is a repair of the last |
| No notion of minimal change | Change cost measured as repair radius |
| Parser is a gate (pass/fail) | Parser is a topology (nested commitments) |

## Demo

`auto_healing_ast.py` demonstrates this with a 50-line DSL: Lark parses the AST, a perturbation forces `backend` from zone 2 to zone 1, the runtime locks `database` (unaffected), cascades `frontend` and `cache` (affected by overlap edges), and returns the repaired DSL with all constraints satisfied. No regeneration. No error. Just a bounded repair cascade with measured radius.

## Files

- `auto_healing_ast.py` — Lark + CRT repair runtime demo
- `docs/LARK.md` — AST repair vision and applications
- `src/core/local_crt.py` — LocalCRTGroup (the repair primitive)
- `src/core/topology.py` — ConstraintTopology (the constraint graph)
- `src/core/engine.py` — RepairEngine (generic backtracking solver)
- `src/benchmarks/repair_benchmark.py` — 847-12,495x speedup proof
