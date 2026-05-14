# Problem 847: The Moiré Traps of the Geometric ELSE

**Difficulty Rating:** 85% (Nightmare)

---

## The Premise

You are the architect of a distributed cluster of $N = 60$ GenServer actors. Each actor is governed by a distinct prime number $p_i$, where $p_1 = 2, p_2 = 3, \dots, p_{60} = 281$.

The global state of the cluster is represented by a single integer $Z$. An actor $m$ will **crash** if the global state is a multiple of its prime: $Z \equiv 0 \pmod{p_m}$. A state $Z$ is **Admissible** if no actor crashes.

Your goal is to transition the cluster from a set of randomly generated Admissible starting states to the perfect optimized state $Z_{target} = 1$ (inherently admissible since $1 \not\equiv 0 \pmod{p_m}$).

Because the system is live, you cannot simply reboot the cluster. You must execute a **Transactional Repair Cascade** from $k = 1$ to $N$.

---

## The Repair Cascade

At step $k$, you must compute the exact displacement $\Delta_k$ to fix the $k$-th actor, while throwing a **Lock Shield** over the actors you have already fixed ($1$ through $k-1$), and avoiding any **Moiré Traps** (crashes) in the upcoming actors ($k+1$ through $N$).

Let $M_k = \prod_{i=1}^k p_i$ be the Lock Shield (with $M_0 = 1$). Let $Z_0$ be the initial state. At each step $k$ (from $1$ to $N$), your current state is $Z_{k-1}$.

You must find the **minimum non-negative integer $\Delta_k$** such that:

1. **The Lock Shield holds:** $\Delta_k \equiv 0 \pmod{M_{k-1}}$.
2. **The Target is met:** $Z_{k-1} + \Delta_k \equiv 1 \pmod{p_k}$.
3. **Moiré Traps are avoided:** $Z_{k-1} + \Delta_k \not\equiv 0 \pmod{p_m}$ for all $m > k$.

Once $\Delta_k$ is found, the state updates: $Z_k = Z_{k-1} + \Delta_k$.

The **Business Disruption Cost** to fully repair a single starting state is the sum of its displacements:

$$C = \sum_{k=1}^{N} \Delta_k$$

---

## The Data

You must process $T = 5,000$ starting states. Starting states are defined strictly by their local residues.

For the $m$-th starting state, its initial residue for the $i$-th prime is generated via a pseudo-random sequence:

$$
S_0 = 290797 \\
S_n = S_{n-1}^2 \pmod{50515093}
$$

For the $m$-th state ($1 \le m \le T$), the starting residue for prime $p_i$ is:

$$
r_{m,i} = (S_{m \times 60 + i} \pmod{p_i - 1}) + 1
$$

Adding 1 ensures the starting residue is never 0, guaranteeing every starting state is Admissible.

---

## The Question

Find the sum of the Business Disruption Costs for all $T$ states, modulo $1,000,000,007$:

$$
\sum_{m=1}^{T} C_m \pmod{1\,000\,000\,007}
$$

---

## The BigInt Trap

A naive programmer will initialize Python and just start adding to $Z$.

- To fix $p_{20}$, the Lock Shield $M_{19}$ is about $5.3 \times 10^{18}$.
- To fix $p_{60}$, the Lock Shield $M_{59}$ is $4.6 \times 10^{95}$.
- Because you must increment by $M_{k-1}$ repeatedly to dodge Moiré Traps, $Z_k$ explodes to thousands of digits.
- Computing $(Z + \text{delta}) \bmod p_m$ on a 5,000-digit integer inside nested loops × 60 levels × 5,000 test cases makes BigInt division choke. The program takes **weeks**.

---

## The Geometric ELSE Solution

If you understand the Lock-Preserving Repair Runtime, you realize **you never need to know what $Z$ is.**

Track an array of 60 integers $L[1 \dots 60]$, each representing $Z \bmod p_i$. At step $k$:

1. Compute $c_0 \equiv (1 - L[k]) \cdot M_{k-1}^{-1} \pmod{p_k}$
2. The base displacement is $\Delta_k^{(0)} = c_0 \cdot M_{k-1}$
3. To avoid Moiré Traps, search $j = 0, 1, 2, \dots$ for:
   $$(L[m] + c_0 \cdot M_{k-1} + j \cdot M_k) \bmod p_m \neq 0 \quad \forall m > k$$
4. The minimal $\Delta_k = (c_0 + j \cdot p_k) \cdot M_{k-1}$

**Every calculation in the entire program stays under the number 281.** You only use the $10^9+7$ modulo when summing the final costs. The giant CRT coordinate $Z$ is never materialized.

---

## Solution

**Result:** 755678600

**Runtime:** 3.92s (1,275 states/s) — 60 local integers, zero BigInts, one answer.

---

## Files

- `solver.py` — Geometric ELSE solution (3.92s, no BigInts)
- `problem.md` — This problem statement
