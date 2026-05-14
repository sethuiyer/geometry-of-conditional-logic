# A Local Repair Calculus for Structured Discrete State Systems

**Shunyabar Labs Research**
*Draft — 2025*

---

## Abstract

Modern computation is dominated by systems that evolve under continual local disruption. Operating systems reschedule tasks after interrupts, distributed databases reconcile partial failures, multiplayer games maintain synchronized world state under latency, and industrial controllers adapt to fluctuating constraints without halting execution. In nearly all of these domains, the central problem is not discovering a globally optimal state from scratch, but preserving an already coherent system while repairing only the affected region.

This paper explores a computational framework for that setting: a **local repair calculus for structured discrete state systems**. The framework combines three ingredients: overlapping constraint topologies, exact invariant-preserving state transitions derived from modular arithmetic, and localized rollback semantics inspired by distributed systems and actor-based runtimes.

The goal is not to replace optimization theory, SAT solving, or strategic search. Instead, we make a narrower claim: some discrete systems can be modeled as overlapping local consistency domains connected by exact repair operators that preserve already-valid commitments during incremental updates. We present the mathematical core of the framework, demonstrate its application across several domains including CPU scheduling and game state maintenance, and offer an honest assessment of where the approach provides genuine value and where it does not.

---

## 1. Introduction

Much of theoretical computer science emphasizes global search, optimization, and asymptotic complexity. Yet many practical systems operate in a different regime: they maintain large structured states that are mostly correct most of the time. The computational challenge is therefore incremental repair under partial commitment preservation — not finding the optimal solution from scratch, but performing the smallest valid update that preserves what already works.

Consider a CPU scheduler managing thousands of runnable processes. When a process blocks on I/O, the scheduler does not restart from empty — it has already made commitments to hundreds of other processes that should remain undisturbed. The ideal update preserves hot-cache assignments, maintains NUMA locality, and repairs only the affected scheduling slot. This is fundamentally a local repair problem, not a global optimization problem.

Or consider a multiplayer game synchronized across distributed nodes. When one unit moves, the system does not resynchronize the entire world — it propagates a local update through overlapping consistency domains (region boundaries, ownership groups, collision groups) while preserving unaffected state. Again: local repair, not global recomputation.

The framework proposed in this paper addresses exactly this regime.

---

## 2. The Arithmetic of Local Repair

### 2.1 State as Residue Vector

Let $V = \{v_1, v_2, \dots, v_n\}$ be a set of discrete variables. Assign to each variable $v_i$ a prime modulus $p_i$, chosen pairwise coprime across the system. A system state is then represented as an integer $z$ satisfying:

$$z \equiv a_i \pmod{p_i}$$

for each variable $v_i$ with current assignment $a_i \in \{0, 1, \dots, p_i - 1\}$.

The Chinese Remainder Theorem (CRT) guarantees a unique solution $z \in \mathbb{Z}_{P}$ where $P = \prod_{i=1}^{n} p_i$, giving a single integer representation of the complete system state as a coordinate on a high-dimensional CRT manifold.

### 2.2 The Commitment Shield

Suppose a subset $S \subseteq V$ of variables have been assigned and should be preserved — these are "locked" or "committed" variables representing warm-cache processes, already-allocated resources, or stable structural commitments.

Define the **commitment shield**:

$$M_S = \prod_{v_j \in S} p_j$$

$M_S$ is the product of all primes associated with protected variables.

### 2.3 The Repair Operator

To modify an unlocked variable $v_t$ from its current residue $a_t$ to a new residue $a_t'$, we compute a repair transition using:

$$z' = z + kM_S$$

where $k$ is chosen such that:

$$z' \equiv a_t' \pmod{p_t}$$

By CRT construction, for every $v_j \in S$:

$$M_S \equiv 0 \pmod{p_j}$$

Therefore:

$$z' \equiv z \pmod{p_j}$$

for all protected variables. The repair preserves all locked commitments exactly — no approximation.

### 2.4 Computing the Jump

The scalar $k$ is computed by reducing the repair equation modulo $p_t$:

$$z + kM_S \equiv a_t' \pmod{p_t}$$

Since $M_S$ and $p_t$ are coprime (all primes are distinct), $M_S$ has a modular inverse modulo $p_t$, denoted $M_S^{-1}$. Thus:

$$k \equiv (a_t' - z) \cdot M_S^{-1} \pmod{p_t}$$

The smallest non-negative solution for $k$ yields the minimal repair displacement.

### 2.5 Repair Radius

We define **repair radius** as a measure of disturbed coordinates:

$$R(z, z') = |\{v_i \in V : x_i \neq x_i'\}|$$

In a CPU scheduler, $R$ corresponds to context switches and cache migrations. In a distributed simulation, $R$ corresponds to the number of affected world regions. In all cases, $R$ measures the scope of perturbation — and the goal of local repair is to minimize $R$ while satisfying all constraints.

---

## 3. The Topology of Local Consistency

### 3.1 Beyond the Single Integer

The single-integer CRT representation is elegant but does not scale to large systems with complex overlap structure. The mature framework replaces the monolithic integer with a **topology of local constraint groups**.

Define a family of overlapping constraint groups:

$$\mathcal{G} = \{G_1, G_2, \dots, G_m\}$$

where each $G_i \subseteq V$ is a subset of variables that share a local consistency requirement. Each group has a validator:

$$\phi_i : D^{|G_i|} \to \{0, 1\}$$

The global system must satisfy:

$$\forall i, \quad \phi_i(x|_{G_i}) = 1$$

where $x$ is the global state and $x|_{G_i}$ is its restriction to group $G_i$.

### 3.2 The Overlap Hypergraph

Variables participate simultaneously in multiple groups — this is the overlap structure. Represented as a hypergraph:

- **Nodes**: variables $V$
- **Hyperedges**: groups $\mathcal{G}$
- **Propagation**: repair signals traverse overlap edges

A Sudoku puzzle is a natural example: each cell belongs to three overlapping groups (row, column, box). A CPU scheduler has groups for cores, cache domains, NUMA nodes, and deadline bands. Multiplayer simulations contain region groups, ownership groups, and synchronization boundaries.

### 3.3 Local CRT Microspaces

Each group $G_i$ can maintain its own local CRT microspace — a sub-coordinate tracking only the variables in that group. A repair operation requires all affected groups to agree simultaneously. This is the **triple synchronized jump** — for Sudoku, row, column, and box groups must all accept a cell value before the placement commits.

The entire system becomes a network of overlapping local consistency domains, each maintaining its own CRT sub-coordinate, with repairs propagating through the overlap topology.

---

## 4. Relationship to Existing Methods

### 4.1 Global Optimizers

CP-SAT solvers, mixed-integer programming, and heuristic schedulers remain superior for many large-scale optimization problems. In inventory allocation experiments, standard CP-SAT substantially outperforms CRT-based search on large objective-heavy instances. The framework does not circumvent NP-hardness and provides no asymptotic improvement over mature exact solvers.

### 4.2 Actor-Based Distributed Systems

The framework aligns naturally with distributed actor runtimes. In Elixir and Erlang implementations, each constraint group is an independent process with local state, rollback history, and exact transition semantics. A repair operation becomes a coordinated transaction across overlapping actors. Constraint propagation occurs through message-passing rather than centralized recomputation.

This architecture mirrors the actual structure of many real systems: distributed applications are collections of partially independent subsystems maintaining local consistency under continual perturbation.

### 4.3 Rollback Netcode

Fighting game rollback systems use similar principles: when an input arrives late, the receiver rolls back to a previous state and re-simulates forward. The CRT repair framework provides an algebraic interpretation — a repair jump is a specific, minimal displacement to a new consistent state, not an arbitrary rollback to a checkpoint.

---

## 5. Applications

### 5.1 CPU Scheduling

CPU scheduling is the canonical application. Each core is a constraint group with a prime modulus. Hot-cache processes are locked — their primes enter the commitment shield $M$. When a process blocks, the scheduler computes the minimal CRT repair jump preserving all locked cores, migrating only the affected process to a new core.

**Traditional scheduler:**
```
process blocked → reconsider queues → migrate many tasks → recompute globally
```

**CRT repair scheduler:**
```
process blocked → compute exact local displacement → preserve warm-cache assignments → modify only affected coordinate
```

The repair radius measures how many cores are disturbed. Preemption becomes a CRT jump — not a restart.

### 5.2 Game State Maintenance

Games provide an instructive domain. Strategy engines (minimax, MCTS) operate at the level of long-horizon planning. Beneath them lies a different problem: maintaining coherent world state under local change.

When a unit moves, the system propagates updates through overlapping consistency domains:
- Position groups: updated
- Collision groups: checked and repaired
- Pathfinding groups: locally updated
- Ownership groups: synchronized

The CRT repair framework does not replace strategic reasoning. It provides a structured substrate for maintaining coherent simulation state under perturbation — local repair, bounded disturbance, preserved commitments.

### 5.3 Multiplayer Netcode

Distributed simulation synchronization is a strong fit. World state distributed across shards requires local rollback netcode when desyncs occur. The CRT framework naturally supports:
- Local rollback: repair jumps from $z$ to $z'$
- Preserved unaffected regions: locked variables stay locked
- Bounded repair radius: only nearby coordinates change
- Transactional synchronization: multi-group commits via staged transactions

This aligns with fighting game rollback, MMO region consistency, and distributed simulation maintenance.

### 5.4 Logistics and Assignment

Staff rostering, field-service dispatch, and order promising are strong commercial wedges. These domains have:
- High cost of mistakes (commitments are binding)
- Incremental disruption (one callout, one cancellation)
- Local repair preference (don't reshuffle entire rosters)

The CRT repair framework handles exactly this: preserve existing commitments, repair only the affected slot, bounded disturbance radius.

---

## 6. Limitations and Honest Assessment

### 6.1 What This Framework Is Not

The framework is not:
- A universal optimizer
- A replacement for CP-SAT on general allocation
- A strategic planning mechanism (minimax, MCTS, deep search)
- A continuous optimization method
- A theory of everything

### 6.2 Where It Does Not Apply

The approach is not well suited to:
- Continuous domains (real-valued variables)
- Fuzzy utility landscapes
- Deep strategic planning horizons
- Large-scale global optimization
- Problems where global recomputation is genuinely preferable to local repair

### 6.3 The Honest Assessment

The framework's strength is narrow: it excels at **local consistency maintenance** in structured discrete systems where preserving stable commitments is more valuable than discovering new global optima.

The 61/100 math audit rating reflects this honestly: the CRT core is solid, but some extensions overclaim. Benchmarks show CP-SAT wins on general optimization. The framework should be understood as a **specialized exact repair primitive**, not a competitive general solver.

This is not a weakness — it is a precise characterization of the problem regime where the approach provides genuine value.

---

## 7. Conclusion

Many computational systems can be viewed not merely as symbolic programs or optimization targets, but as structured discrete worlds maintained through local repair. In such systems, preserving stable commitments is often more valuable than recomputing globally optimal states.

The Chinese Remainder Theorem provides one exact algebraic mechanism for expressing these repair transitions: the repair jump $z' = z + kM$, preserving all locked residues exactly while modifying only the necessary coordinates. The overlap topology provides the structural map; the repair radius provides the disturbance metric.

Whether this develops into a practical runtime model for distributed scheduling and simulation systems remains an open engineering question. Significant work remains in scalability, propagation semantics, conflict resolution, transactional coordination, and benchmark evaluation against existing systems.

Yet the core insight appears stable: some discrete systems are best understood not as repeated global searches, but as local consistency geometries navigated through exact commitment-preserving repair operations.

The ELSE branch of computation may indeed possess geometric content.

---

**References**

- Chinese Remainder Theorem — standard number theory
- Garner's Algorithm (1958) — mixed-radix CRT reconstruction
- CRT-based coordinate systems — distributed constraint satisfaction
- Overlap topology / hypergraph formulations — constraint satisfaction literature
- Repair radius — metric for bounded-disturbance repair

---

*Shunyabar Labs · 2025*
*Source code and benchmarks: `/src/`*
*Math audit: `MATH.md`*
*Commercial notes: `MONEY.md`*