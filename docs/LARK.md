# Geometric Code Repair: Lark + CRT Runtime

## The Insight

An AST is a ConstraintTopology. A grammar is a set of constraint groups — each production rule
is a group, each node is a variable, each child relationship is an overlap edge. A broken AST
(a syntax error, a type mismatch, a violated lint rule) is a **perturbation** in the repair
runtime sense.

Lark generates the topology. The CRT runtime executes the repair.

## Why This Works

| CRT concept | AST concept |
|---|---|
| Constraint group | Grammar production rule |
| Variable | AST node |
| Overlap edge | Parent-child / sibling relation |
| Locked residue | Valid subtree |
| Shield M = ∏ locked primes | Set of correctly parsed subtrees |
| CRT jump z' = z + kM | Minimal edit to fix the broken node |
| Rollback | Undo the edit if it breaks other rules |

An AST is not merely analogous to a Sudoku board. Both are **structured discrete state systems
with nested commitments**. Sudoku has row/col/box constraints. An AST has grammar production
constraints. The repair algebra is identical.

## Applications

### 1. Structure-Aware Code Search (UltraMeM for Code)

Standard code search retrieves by token overlap or embedding similarity. AST-based retrieval
retrieves by **structural pattern**.

Search for "async retry with exponential backoff":
- Token search finds: any file with those keywords in any context
- AST search finds: code with the same **control flow topology** — try-catch nesting depth,
  retry loop position, fallback chain structure, error propagation pattern

UltraMeM hierarchy for code:

| Level | Feature | Extraction |
|---|---|---|
| 0 | Control flow topology | Loop nesting, try/catch depth, branching structure |
| 1 | Call graph dependencies | Which functions call which, import topology |
| 2 | Type signature | Parameter types, return types, generic constraints |
| 3 | Surface tokens | Variable names, comments, formatting |

A query AST is compared against stored ASTs using the ultrametric distance `d_R = 2^{-v_R}`,
where `v_R` counts consecutive matching levels. Two code snippets can have different variable
names (different surface tokens) but identical control flow and call graph — ultrametric
distance treats them as structurally close.

### 2. Auto-Healing DSLs for LLM Agents

LLMs generate structured DSLs (configs, workflows, business rules). They frequently produce
near-valid output — 95% correct, with a single syntax or constraint violation.

Current approach: parser throws `SyntaxError`, LLM regenerates from scratch.

Repair approach:
1. Lark parses the LLM output — finds the error location (the perturbation)
2. CRT runtime locks the valid 95% of the AST (the shield M)
3. Computes the minimal edit to fix the broken node
4. Returns the nearest valid AST, preserving the LLM's reasoning

This is the **patch-vs-violate DP** from `src/core/metrics.py` applied to grammar constraints:
- Patching individual tokens costs `patch_cost * number_of_tokens`
- Violating a production rule and replacing the subtree costs `2^{-depth}`
- The solver chooses whichever is cheaper

### 3. Lock-Preserving Incremental Refactoring

Change a function signature across a large codebase:
1. Lark parses all files into ASTs
2. The signature change is a perturbation to the function's production rule
3. CRT runtime computes the minimal repair cascade:
   - Lock all unaffected function bodies
   - Follow overlap edges to caller sites
   - Update call arguments at each caller
   - Lock updated callers
   - Continue until no more edges need repair

The result: a refactoring tool that touches only the AST nodes forced to change by the
perturbation — mathematically guaranteed minimal disturbance.

### 4. Live-Coding Constraint Engine

During typing, the AST is temporarily invalid. Each keystroke is a perturbation.
The CRT runtime computes the minimal displacement to restore validity, providing:

- Syntax-aware autocomplete (the repair engine knows which tokens are legal next)
- Error recovery that preserves surrounding structure (lock the valid outer scope,
  repair only the broken inner node)
- Refactoring suggestions that respect the program's constraint topology

## Quick Prototype

```python
from lark import Lark, Tree, Token
from src.core.local_crt import LocalCRTGroup
from src.core.topology import ConstraintTopology

# 1. Define a DSL grammar
grammar = """
    start: command+
    command: "deploy" service "to" env
    service: NAME
    env: "staging" | "production"
    NAME: /[a-z_]+/
    %ignore " "
"""

parser = Lark(grammar)

# 2. Parse user input (possibly broken)
try:
    tree = parser.parse("deploy my_service to staging")
except LarkError as e:
    # 3. Repair: lock the valid prefix, find the CRT jump for the broken token
    #    (Conceptual — implementation uses the repair runtime)
    repair = compute_minimal_edit(e, grammar)
    tree = repair.apply()

# 4. The tree is now the nearest valid AST, with maximum preserved structure
```

The actual implementation uses the same `ConstraintGroup` / `try_place` / `rollback`
primitives that solved AI Escargot in 6.98s. The grammar nodes are the constraint groups.
The AST paths are the overlap edges. The repair engine is already written.

## Files

- `src/core/local_crt.py` — LocalCRTGroup (the repair primitive)
- `src/core/topology.py` — ConstraintTopology (the constraint graph)
- `src/core/engine.py` — RepairEngine (generic backtracking solver)
- `src/core/metrics.py` — patch-vs-violate DP (ultrametric cost model)
- `docs/AI.md` — ultrametric retrieval architecture
- `docs/MEMORY.md` — ultrametric memory for LLM agents
