# Math Audit of `ifelse`

This document reconstructs the actual mathematics implemented in this folder. It is intentionally code-first: when the prose in `README.md` or `docs/` overstates something, this file follows the source in `src/`.

## 1. Common Mathematical Core

Most of the repository is built around one scalar coordinate `z` and a list of moduli `p_1, ..., p_n`, usually primes.

For each constraint dimension `i`, the decoded state is the residue

\[
r_i(z) = z \bmod p_i.
\]

When the moduli are pairwise coprime, the Chinese Remainder Theorem gives a bijection

\[
z \pmod P \longleftrightarrow (r_1,\dots,r_n), \qquad P = \prod_{i=1}^n p_i.
\]

So one integer `z` can encode one full discrete state vector.

### 1.1 CRT Reconstruction

The code repeatedly uses a mixed-radix Garner reconstruction. For target residues

\[
a_i \in \{0,\dots,p_i-1\},
\]

it constructs coefficients `v_i` such that

\[
z = v_1 + v_2 p_1 + v_3 p_1p_2 + \cdots + v_n \prod_{j=1}^{n-1} p_j.
\]

In the implementation pattern used in `src/garner_navigation.py`, `src/traffic_controller.py`, `src/prime_mastermind.py`, and `src/prime_sat_landscape.py`,

\[
v_1 = a_1,
\]

and for `i > 1`,

\[
v_i \equiv
\left(
a_i - \sum_{j=1}^{i-1} v_j \prod_{k=1}^{j-1} p_k
\right)
 \left(\prod_{k=1}^{i-1} p_k\right)^{-1}
\pmod{p_i}.
\]

This yields the unique `z` modulo `P` with

\[
z \equiv a_i \pmod{p_i} \quad \text{for all } i.
\]

### 1.2 Example Used Across the Repo

For

\[
(p_1,p_2,p_3) = (2,3,5), \qquad (a_1,a_2,a_3) = (1,0,1),
\]

the unique solution modulo `30` is

\[
z = 21,
\]

because

\[
21 \bmod 2 = 1,\qquad
21 \bmod 3 = 0,\qquad
21 \bmod 5 = 1.
\]

That is the target state in `src/prime_logic_nn.py`.

## 2. Smooth Residue Loss

The main differentiable surrogate is the cosine penalty

\[
L_i(z) = 1 - \cos\!\left(\frac{2\pi}{p_i}(z-a_i)\right),
\]

with total loss

\[
L(z) = \sum_{i=1}^n L_i(z).
\]

This appears in `src/prime_logic_nn.py`, `src/hard_prime_maze.py`, and `src/traffic_controller.py`.

The derivative used in the code is

\[
\frac{dL_i}{dz}
=
\frac{2\pi}{p_i}
\sin\!\left(\frac{2\pi}{p_i}(z-a_i)\right),
\]

so

\[
\frac{dL}{dz}
=
\sum_{i=1}^n
\frac{2\pi}{p_i}
\sin\!\left(\frac{2\pi}{p_i}(z-a_i)\right).
\]

The minima occur whenever `z` lands on the target residue for every modulus:

\[
z \equiv a_i \pmod{p_i}\ \forall i.
\]

Because each term is periodic, the global minima repeat every

\[
P = \prod_i p_i
\]

when the moduli are pairwise coprime.

## 3. Monodromy / Safe-Corridor Jump Used in Search Solvers

The combinatorial solvers for N-Queens and timetabling use a more exact update than gradient descent.

Suppose some previously solved moduli are preserved by the product

\[
M = \prod_{p \in S} p.
\]

We want to change `z` so that

\[
z' \equiv c \pmod{p_t}
\]

for a new target modulus `p_t`, while preserving all already solved residues. The code sets

\[
z' = z + \Delta,\qquad \Delta = kM,
\]

and chooses

\[
k \equiv (c-z) M^{-1} \pmod{p_t}.
\]

Then:

\[
z' \equiv z \pmod p \quad \text{for every } p \in S
\]

because `M` is divisible by all solved moduli, and

\[
z' \equiv z + kM \equiv c \pmod{p_t}.
\]

This is the exact arithmetic behind `garners_jump` in:

- `src/prime_n_queens.py`
- `src/prime_timetable.py`

Mathematically, this is just an incremental CRT update.

## 4. File-by-File Mathematics

### 4.1 `src/prime_logic_nn.py`

This is the cleanest minimal example.

- State space: residues modulo `(2,3,5)`.
- Target logic: `(1,0,1)`.
- Objective:

\[
L(z)=\sum_{p\in\{2,3,5\}}\left(1-\cos\left(\frac{2\pi}{p}(z-a_p)\right)\right).
\]

- Optimization: a small ReLU MLP outputs one scalar `z`; manual backprop applies the chain rule through `z`.

The actual mathematical content is not “logic learning” in a general sense. It is scalar regression onto a periodic multi-well objective whose exact minima correspond to one CRT residue pattern.

### 4.2 `src/hard_prime_maze.py`

Same loss, larger modulus set:

\[
(p_i) = (2,3,5,7,11),\qquad P = 2310.
\]

The target logic is `(1,0,1,0,1)`.

The only substantive change is optimization difficulty. Superposition of more cosine terms increases the number of local basins and shallow interference regions. The cyclic learning rate is a heuristic for escaping poor local minima; there is no proof in the code that it reaches the correct CRT coordinate.

### 4.3 `src/garner_navigation.py`

This file switches from periodic loss to direct coordinate regression.

First, it computes the exact CRT target

\[
z^\star = \operatorname{Garner}(a_1,\dots,a_n).
\]

Then the network minimizes the quadratic loss

\[
L(z) = \frac12 (z-z^\star)^2,
\qquad
\frac{dL}{dz} = z-z^\star.
\]

So mathematically this is plain supervised regression toward an exact CRT-constructed target. The “safe corridor” interpretation corresponds to using explicit arithmetic structure to avoid wandering in the periodic landscape.

### 4.4 `src/traffic_controller.py`

This file combines symbolic filtering and scalar optimization.

The four control bits are:

\[
(\text{NS},\text{EW},\text{LT},\text{PED}),
\]

encoded with moduli `(2,3,5,7)`.

The hard admissibility rules are:

\[
\neg(\text{NS}=1 \land \text{EW}=1),
\]

\[
\text{PED}=1 \implies \text{NS}=\text{EW}=\text{LT}=0.
\]

This reduces the `2^4=16` binary states to 7 safe states:

\[
(0,0,0,0),\ (0,0,0,1),\ (0,0,1,0),\ (0,1,0,0),\ (0,1,1,0),\ (1,0,0,0),\ (1,0,1,0).
\]

Each safe state has a unique CRT coordinate modulo

\[
2\cdot3\cdot5\cdot7 = 210.
\]

Examples from the actual encoding:

\[
(1,0,1,0) \mapsto 21,\qquad
(1,0,0,0) \mapsto 105,\qquad
(0,0,0,1) \mapsto 120.
\]

For a chosen scenario, the solver blends:

\[
L_{\text{MSE}}(z)=\frac12(z-z^\star)^2,
\]

with the periodic residue force

\[
\nabla L_{\text{wave}}(z)
=
\sum_i \frac{2\pi}{p_i}\sin\!\left(\frac{2\pi}{p_i}(z-a_i)\right).
\]

The code uses only a blended gradient:

\[
g_{\text{total}}
=
\alpha\,\mathrm{clip}(z-z^\star,-50,50)

+ (1-\alpha)\,\nabla L_{\text{wave}}(z),
\]

with `\alpha` decreasing linearly over training. So the implemented method is a heuristic annealing from exact coordinate regression toward local residue snapping.

### 4.5 `src/prime_n_queens.py`

This is not gradient descent. It is backtracking with CRT-preserving jumps.

- Variables: one column value per row.
- Moduli: `(11,13,17,19,23,29,31,37)`.
- Decoding:

\[
c_i = z \bmod p_i.
\]

Only values `0,...,7` are considered during construction, so each residue is interpreted as a valid chessboard column.

The conflict conditions for rows `i < j` are:

\[
c_i = c_j \quad \text{(same column)},
\]

or

\[
|c_i-c_j| = |i-j| \quad \text{(same diagonal)}.
\]

When a non-conflicting column is found for row `j`, the code performs the incremental CRT jump from Section 3 so the new residue is fixed without disturbing previous rows.

So the real algorithm is:

1. depth-first search over row assignments;
2. exact CRT update after each accepted assignment.

### 4.6 `src/prime_timetable.py`

This has the same structure as N-Queens.

Each class `i` gets modulus `p_i` from `(11,13,17,19,23)`. A residue `v` is decoded as

\[
\text{slot}(v)=v\bmod 4,\qquad
\text{room}(v)=\left\lfloor \frac{v}{4}\right\rfloor.
\]

Only residues `0,...,7` are explored, so the state space per class is exactly the `4\times 2=8` valid `(slot, room)` pairs.

Conflict predicates are:

\[
(\text{slot}_i,\text{room}_i) = (\text{slot}_j,\text{room}_j)
\]

for room collisions, and

\[
\text{slot}_i=\text{slot}_j \land \text{teacher}_i=\text{teacher}_j
\]

for teacher collisions.

Again, the accepted residue is installed by the CRT jump

\[
z \leftarrow z + kM.
\]

### 4.7 `src/prime_mastermind.py`

This file uses CRT only as a coordinate labeling of ordinary Mastermind states.

- Four peg positions use moduli `(7,11,13,17)`.
- A code `c=(c_1,c_2,c_3,c_4)` with each `c_i \in \{0,\dots,5\}` is encoded as one CRT coordinate.

The game logic itself is standard:

\[
\text{bulls} = \sum_i \mathbf 1[c_i = g_i],
\]

and cows are computed by color histogram overlap after removing bulls:

\[
\text{cows}
=
\sum_{d=0}^{5}\min\{n_d^{\text{secret}}, n_d^{\text{guess}}\}.
\]

Candidate elimination is exact set filtering:

\[
\mathcal C_{t+1}
=
\{c \in \mathcal C_t : \operatorname{score}(c,g_t)=\text{feedback}_t\}.
\]

The “best guess” heuristic is minimax on the largest remaining feedback bucket. The prime machinery is representational, not algorithmically necessary.

### 4.8 `src/prime_sat_landscape.py`

This file defines a smooth clause-violation landscape for 3-SAT-style clauses over residues modulo `(2,3,5,7)`.

For a clause with literals `(l_1,l_2,l_3)`, the code builds a multiplicative penalty

\[
E_{\text{clause}}(z)
=
\prod_{j=1}^3
\left(
\frac12 + \frac12 \cos\left(\frac{2\pi}{p_{i_j}}(z-t_{i_j})\right)
\right),
\]

where `t_{i_j}` is the residue that makes the literal false:

- positive literal `x_i`: false residue `0`
- negated literal `\neg x_i`: false residue `1`

Total energy is the sum over clauses:

\[
E(z) = \sum_{\text{clauses } C} E_C(z).
\]

This is a visualization heuristic, not an exact SAT indicator. Running `src/final_sat_verification.py` shows that a threshold on this energy matches the Boolean checker for only `102 / 210` coordinates, or about `48.6%`.

So:

- the energy has interpretable local structure;
- it does not encode SAT truth exactly in this implementation.

### 4.9 `src/extract_sat_solutions.py`, `src/verify_sat.py`, `src/final_sat_verification.py`

These files define the Boolean interpretation used for brute-force SAT checking:

- positive literal `x_i` is true iff `z % p_i == 1`;
- negative literal `\neg x_i` is true iff `z % p_i != 1`.

That means the Boolean predicate is many-to-one:

\[
z \bmod p_i \in \{0,2,3,\dots,p_i-1\}
\]

all count as Boolean false for positive literals.

This “ghost residue” convention is mathematically important: it enlarges the state space far beyond binary assignments. The SAT scripts are therefore working over a multivalued residue system projected onto booleans, not over pure `{0,1}^n`.

### 4.10 `src/prime_pigeonhole.py`

This is an energy model for an unsatisfiable CSP with 3 pigeons and 2 holes. There are 6 variables:

\[
x_{p,h}, \qquad p\in\{0,1,2\},\ h\in\{0,1\},
\]

encoded by moduli `(2,3,5,7,11,13)`.

The energy adds two families of penalties:

1. Missing-pigeon penalty. For each pigeon `p`, the clause

\[
x_{p,0}\lor x_{p,1}
\]

is violated only when both residues hit `0`, implemented by a product of cosine peaks.

2. Collision penalty. For each hole `h` and pair of pigeons `p_1 < p_2`, the constraint

\[
\neg(x_{p_1,h}\land x_{p_2,h})
\]

is violated when both residues hit `1`, again as a product of cosine peaks.

The reported phenomenon is that the minimum energy over all `z` stays positive, so there is no zero-energy state.

### 4.11 `src/prime_pigeonhole_strict.py`

This file turns the previous heuristic into a stricter discrete energy:

\[
E(z)=E_{\text{binary}}(z)+E_{\text{constraints}}(z).
\]

Binary gravity penalty:

\[
E_{\text{binary}}(z)
=
5 \cdot \#\{i : z \bmod p_i > 1\}.
\]

Constraint penalties:

- `+10` if some pigeon occupies no hole;
- `+10` if two pigeons occupy the same hole.

Brute-force scan over the full modulus product reports minimum energy `5.0`, not `0`, which is consistent with unsatisfiability under the repo's binary interpretation.

### 4.12 `src/prime_word_ladder.py`

Despite the naming, this file is standard graph search.

- Words are nodes.
- Two words are adjacent iff their Hamming distance is `1`.
- `word_ladder_prime` is breadth-first enumeration of all shortest paths.
- `analyze_landscape` computes graph metrics such as frontier size and dead-end ratio.

No CRT, periodic loss, or residue algebra is used here. The mathematical object is an unweighted graph

\[
G=(V,E),
\]

and the shortest ladders are geodesics in graph distance.

### 4.13 `src/prime_alien_dict.py`

This is also a standard discrete algorithm.

- Characters are vertices.
- An edge `u \to v` means `u` must precede `v`.
- `alien_order` runs Kahn's topological sort.
- `find_all_valid_orderings` enumerates all linear extensions by backtracking.

The core math is partial orders and DAGs, not CRT.

### 4.14 `src/prime_regex_manifold.py`

This file is dynamic programming for regex matching with `.` and `*`.

The main recurrence is over

\[
dp[i][j] = \text{whether } s[i:] \text{ matches } p[j:].
\]

The standard recurrence intended by regex matching is:

\[
dp[i][j]
=
\begin{cases}
dp[i][j+2] \lor (\text{first\_match} \land dp[i+1][j]) & \text{if } p[j+1]=* \\
\text{first\_match} \land dp[i+1][j+1] & \text{otherwise.}
\end{cases}
\]

However, the implementation checks `p[j] == '*'` instead of looking ahead for `p[j+1] == '*'` in the main DP loop, so the actual code is not the canonical regex DP recurrence. This file is best read as an exploratory metaphor layer rather than a validated mathematical extension of the prime-coordinate framework.

### 4.15 `src/prime_sudoku.py`

This file aims to use one modulus per cell, but the implementation breaks the CRT assumptions.

Intended model:

- one modulus per cell;
- decode cell `i` by `z mod p_i`;
- reduce modulo `9` to get a digit class;
- penalize duplicates in rows, columns, and `3\times 3` boxes.

Actual issues:

1. `_generate_primes` does not generate primes from 11 upward. Because it never checks divisibility by `3,5,7`, it produces odd numbers such as

\[
11, 13, 15, 17, 19, 21, 23, 25, \dots
\]

so the moduli are not pairwise coprime.

2. Without pairwise coprimeness, the one-to-one CRT coordinate interpretation fails.

3. The search is random sampling over an astronomically large period; there is no constructive solver comparable to the N-Queens or timetable files.

So mathematically this file is a loose residue-based scoring function, not a valid CRT embedding.

## 5. What Is Exact vs Heuristic in This Repo

### Exact arithmetic pieces

- CRT reconstruction with pairwise coprime moduli.
- Incremental CRT jump `z <- z + kM`.
- Direct residue decoding `z % p_i`.
- Set filtering in Mastermind.
- BFS / topological sort / DP in the non-CRT files.

### Heuristic pieces

- Cosine wave optimization as a differentiable surrogate for residue matching.
- SAT landscape energy as a proxy for logical satisfiability.
- Pigeonhole smooth energy as a frustration visualization.
- Traffic controller's blended MSE-plus-wave training.

### Purely metaphorical extensions

- Much of the “manifold / Riemann / topology” language in Word Ladder, Alien Dictionary, and Regex. Those files mostly implement standard classical algorithms with interpretive framing rather than new arithmetic machinery.

## 6. Bottom Line

The mathematically solid core of this folder is:

1. encode structured discrete states as residues of one scalar `z`;
2. reconstruct exact coordinates with CRT / Garner;
3. preserve solved residues with incremental CRT jumps;
4. optionally use cosine penalties as a smooth but non-exact training surrogate.

The strongest implementations are:

- `src/prime_logic_nn.py`
- `src/hard_prime_maze.py`
- `src/garner_navigation.py`
- `src/traffic_controller.py`
- `src/prime_n_queens.py`
- `src/prime_timetable.py`
- `src/prime_mastermind.py`
- `src/prime_pigeonhole_strict.py`

The weakest mathematical claims relative to the code are:

- SAT landscape exactness;
- Regex manifold correctness;
- Sudoku's use of “primes”.

That is the actual math of the folder.
