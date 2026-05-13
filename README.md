# Geometric IF-ELSE: Continuous Prime-Topology Logic

> **Every `if/else` statement you've ever typed is a flat shadow of a magnificent continuous manifold.**

**A [Shunyabar Labs](https://shunyabar.foo) project.**

This project explores what happens when you force neural networks to navigate discrete Boolean logic through continuous prime-number Riemann surfaces — and what the terrain itself teaches you about constraint satisfaction, UNSAT geometry, and why some problems are literally impossible to collapse.

## Math Audit

Current code-first math rating: **61/100**.

- The CRT / Garner core is the strongest part and holds up well.
- The incremental residue-preserving jump used in the search solvers is valid and useful.
- The cosine wave loss is a real smooth surrogate, but not an exact logical encoding.
- Several extensions over-claim relative to the implementation.

See the root-level [MATH.md](MATH.md) for the full audit, including exact derivations and implementation gaps.

## Research Summary

Current verdict: **good research direction, weak breakthrough claim**.

- The strongest part of the repo is the exact CRT / Garner machinery and the residue-preserving jump updates.
- That mechanism works well as a **lock-and-repair assignment primitive** on structured small-alphabet problems.
- The weaker part is the broader claim that the framework outperforms standard combinatorial optimization in general.

### Benchmark Takeaway

We ran direct benchmarks against **OR-Tools CP-SAT** on the same synthetic timetabling and inventory-allocation instances.

- On planted-feasible timetabling instances, the CRT search was competitive and often faster at the tested small-to-medium sizes.
- On inventory allocation, **CP-SAT was decisively better** on runtime and sometimes on objective quality once CRT search hit its node budget.
- The honest conclusion is that this framework is best understood as a **specialized exact repair/search idea**, not a replacement for mature exact solvers.

See:

- [MATH.md](MATH.md) for the mathematical audit
- [MONEY.md](MONEY.md) for commercial positioning
- `src/large_scale_benchmark.py` for internal scaling tests
- `src/benchmark_vs_cpsat.py` for the direct CP-SAT comparison

---

## The Core Insight

Standard neural networks struggle with `if/else` logic because the Heaviside step function has zero gradients everywhere except at the boundary (where gradients are infinite). It's a mathematical singularity — gradient descent is a blindfolded hiker, and step functions leave it standing on a flat plane.

**What if conditional logic has an inherent continuous geometry?**

It does. And it involves prime numbers.

### The Prime Wave Loss

Assign each Boolean condition a distinct prime $p_i$. Map the modulo operator to a smooth cosine wave:

```
L_i(z) = 1 - cos(2π/p_i * (z - a_i))
```

The total loss is the superposition of all prime waves:

```
L_total = Σ [1 - cos(2π/p_i * (z - a_i))]
```

**Why this works:** The gradient is never zero unless $z$ is exactly at the bottom of the valley. The blindfolded hiker always feels the slope.

### Chinese Remainder Theorem Encoding

For pairwise coprime primes $\{p_1, \ldots, p_N\}$, there exists a unique **Master Coordinate** $X \in [0, \prod p_i)$ satisfying all residues simultaneously:

```
X ≡ a_1 (mod p_1)
X ≡ a_2 (mod p_2)
X ≡ a_3 (mod p_3)
```

A single continuous number encodes the entire truth table.

**Example:** Target logic `[1, 0, 1]` with primes `[2, 3, 5]` yields Master Coordinate $X = 21$.

```
21 mod 2 = 1  (True)
21 mod 3 = 0  (False)
21 mod 5 = 1  (True)
```

### Garner's Algorithm (1958): The Teleporter

Garner's algorithm computes the exact Master Coordinate without brute force:

```
X = v1 + v2*p1 + v3*p1*p2 + ...
```

Where $v_i$ are calculated using modular multiplicative inverses. This is **fully differentiable** — and acts as a "safe corridor" that fixes broken constraints without disturbing solved ones.

---

## The Experiments

| Experiment | What We Tried | What Happened | What We Learned |
|------------|---------------|---------------|-----------------|
| Basic Prime Logic NN | Train NN to learn symbolic constraints using cosine prime-wave loss | Converged to $z \approx 21$, decoded exact logic `[1,0,1]` | Discrete Boolean states can be embedded into a smooth differentiable landscape |
| Hard Prime Maze (5D/7D) | Scale to many simultaneous prime constraints | Network got trapped in local minima; partial constraint satisfaction only | Superposed prime manifolds create real frustration geometry and interference traps |
| Garner Navigation | Use Garner's Algorithm as constructive guidance | Training stopped wandering and moved toward exact targets | Constructive arithmetic acts like a "global coordinate system" for navigation |
| Gradient Explosion Test | Push NN toward huge CRT coordinates | Gradients exploded to absurd magnitudes | Large symbolic coordinate spaces require stabilization/scaling |
| Traffic Controller | Encode safe traffic-light states as admissible manifolds | 7/7 safety scenarios passed; forbidden unsafe states avoided | Constraint manifolds can enforce safety-critical admissibility |
| Dual-Loss Architecture | Combine MSE-to-Garner with wave snapping | Massive convergence improvement | "Highway + snap" worked better than wave loss alone |
| N-Queens | Encode queen positions with primes and CRT decoding | Solved full 8-Queens with exact coordinate extraction | Constraint satisfaction can be navigated geometrically with structured jumps |
| Timetable Scheduling | Assign classes to rooms/times under conflicts | Produced valid non-overlapping schedule | Resource allocation naturally fits manifold-style constraint encoding |
| Hypergraph Timetabling | Solve an NP-hard course-placement problem with room/instructor/student conflicts | Exact valid timetable found via CRT-preserving jumps and backtracking | The framework is strongest on small-alphabet NP-hard assignment problems where solved decisions must be preserved exactly |
| Inventory Allocation | Allocate e-commerce orders to fulfillment plans under stock and lane constraints | Valid low-cost plan found, then repaired under disruption while preserving locked promises | Non-scheduling order promising is a strong commercial fit for exact lock-and-repair |
| Mastermind Solver | Use residues to represent code states and deductions | 100/100 games solved, ~4.47 average turns | Constraint elimination behaves like manifold collapse |
| SAT Landscape | Turn SAT clauses into penalty-wave geometry | Produced visible valleys/mountains and satisfying basins | SAT problems can literally be visualized as frustration terrains |
| SAT Assignment Extraction | Decode truth assignments from coordinates | Successfully recovered Boolean assignments | CRT decoding is interpretable and reversible |
| SAT Verification | Compare manifold valleys against actual SAT truth | Found "stable" solutions vs weaker/ghost solutions | Geometry encodes stability, not just satisfiability |
| Pigeonhole Principle | Try impossible 3 pigeons / 2 holes CSP | No zero-energy solution existed | UNSAT appears as irreducible geometric frustration |
| Binary Gravity Constraint | Force strict Boolean-only states | Energy floor stayed nonzero | Impossible systems cannot collapse into admissible valleys |
| "Void Residue" Behavior | Allow non-binary residues during UNSAT search | System invented higher-sheet escape states | Emergent "ghost dimensions" appear when constraints are impossible |

## Extended Problem Analysis

The framework's fit varies by problem type:

| Problem | Fit Quality | Why |
|---------|-------------|-----|
| Word Ladder II | ★★★★☆ | Multiple shortest paths naturally map to equal-energy valleys |
| Alien Dictionary | ★★★★★ | Topological ordering + cycle detection = frustration geometry |
| Regex Matching | ★★★★★ | NFAs ARE topology — branches are sheets, stars are epsilon transitions |
| Sudoku | ★★☆☆☆ | 81 interdependent constraints explode the period; requires monodromy extensions |

## The Moiré Trap

When superimposing waves of different prime frequencies, you get **moiré interference patterns** — chaotic terrain with false valleys everywhere. Standard optimization gets trapped at coordinates where exactly 2 out of 3 prime constraints are satisfied. The system builds an unscalable wall around itself.

**The theorem:** Garner's discrete algorithm for CRT is **fundamentally identical** to continuous monodromy transport through a multidimensional manifold. Any jump by $M$ (product of satisfied primes) preserves all satisfied constraints:

```
z_new = z_old + n * M  (safe corridor for all n ∈ ℤ)
```

---

## The Meta-Patterns

Across all experiments, the same phenomena kept appearing:

| Repeated Phenomenon | Meaning |
|---------------------|---------|
| Local minima | Constraint interference is real |
| Structured valleys | Satisfying assignments form basins |
| Gradient explosions | Coordinate scaling matters |
| Forbidden regions | Unsafe states become unreachable |
| Constructive jumps outperform wandering | Algebraic structure helps optimization |
| Ghost residues | Relaxed manifolds invent escape dimensions |
| UNSAT → nonzero floor | Contradictions become geometric frustration |
| Exact decoding | State space remained interpretable |

---

## The Moiré Trap

When superimposing waves of different prime frequencies, you get **moiré interference patterns** — chaotic terrain with false valleys everywhere. Standard optimization gets trapped at coordinates where exactly 2 out of 3 prime constraints are satisfied. The system builds an unscalable wall around itself.

**The theorem:** Garner's discrete algorithm for CRT is **fundamentally identical** to continuous monodromy transport through a multidimensional manifold. Any jump by $M$ (product of satisfied primes) preserves all satisfied constraints:

```
z_new = z_old + n * M  (safe corridor for all n ∈ ℤ)
```

---

## Project Structure

```
src/
├── prime_logic_nn.py          # Basic 3-prime NN learning [1,0,1] logic
├── hard_prime_maze.py          # 5-prime stress test with local minima traps
├── garner_navigation.py        # Garner's algorithm as "teleporter" for 7 primes
├── traffic_controller.py      # Safety-critical 4-way intersection (7/7 passed)
├── prime_n_queens.py          # 8-Queens solver using monodromy jumps
├── prime_timetable.py         # University class scheduler
├── prime_hypergraph_timetabling.py # NP-hard timetabling via CRT-preserving jumps
├── prime_inventory_allocation.py # Flipkart-style order promising with disruption repair
├── large_scale_benchmark.py    # Synthetic scaling tests for timetabling and inventory
├── benchmark_vs_cpsat.py       # Direct benchmark against OR-Tools CP-SAT
├── prime_mastermind.py         # Mastermind codebreaker (100/100 solved)
├── prime_sat_landscape.py      # 3-SAT visualization as frustration geometry
├── extract_sat_solutions.py    # Extract Boolean assignments from coordinates
├── verify_sat.py               # Cross-check manifold valleys against Boolean SAT
├── prime_pigeonhole.py         # Pigeonhole principle demonstration (UNSAT proof)
├── prime_pigeonhole_strict.py  # Strict binary version (proved UNSAT)
├── prime_word_ladder.py        # Word Ladder II — multiple equal-energy valleys
├── prime_alien_dict.py         # Topological ordering with cycle detection
├── prime_regex_manifold.py     # NFA as multi-sheet manifold navigation
└── prime_sudoku.py             # Full 9x9 Sudoku (81-cell constraint manifold)

docs/
├── MATH.md                    # Mathematical formulation and PyTorch implementation
├── MATH2.md                   # Deep dive: Lambert W failure, Riemann surfaces, CRT
├── podcast.md                 # Development narrative
└── codingsession.md          # Additional conversation logs

index.html                    # Visual showcase with KaTeX math rendering
sat_landscape.png             # SAT frustration geometry visualization
pigeonhole_frustration.png   # UNSAT as irreducible geometric frustration
CRITIC.md                    # Response to Hacker News critique
```

---

## Key Results

- **Traffic Controller:** 7/7 safety scenarios passed, zero violations — unsafe states are geometrically unreachable
- **8-Queens:** Solved with coordinate $z = 2,372,774,783$, extracting exact queen positions
- **Mastermind:** 100/100 games solved, average 4.47 turns (near theoretical efficiency)
- **SAT Landscape:** Visualized as physical energy terrain — valleys = satisfying assignments, mountains = frustration
- **Pigeonhole (UNSAT):** Energy floor stayed nonzero — impossible constraints manifest as irreducible geometric frustration
- **Word Ladder II:** Found multiple shortest paths as equal-energy valleys
- **Alien Dictionary:** Cycle detection correctly identifies UNSAT (prefix invalid cases)
- **Regex Matching:** Path tracing through multi-sheet manifold — NFAs are literally topology

---

## What This Is NOT

- **Not a universal optimizer.** Standard neural networks don't naturally organize weights into prime Riemann surfaces. The teleportation only works if you explicitly encode constraints as prime manifolds.
- **Not a P=NP claim.** Garner's Algorithm navigates the trap because the prime structure is known in advance. For arbitrary NP-hard problems, the algebraic map is unknown.

---

## What IS Proven

Congruence invariance in discrete arithmetic is **exactly equivalent** to monodromy invariance in continuous topology. The paralyzing frustrations in gradient descent are not merely random noise — they are literal physical topographies of constraint violations mapped from NP-hard combinatorial space onto continuous loss landscapes.

---

## The Question This Opened

> What other ancient discrete algorithms are actually just the flat collapsed shadows of magnificent continuous multi-dimensional geometries waiting to be discovered?
