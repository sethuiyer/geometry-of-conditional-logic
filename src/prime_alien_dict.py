"""
Alien Dictionary — Topological Ordering + Contradiction Geometry

Problem: Given a list of dictionary words sorted by alien alphabet,
derive the character ordering. Detect cycles (impossible ordering).

Framework interpretation:
- Each character = variable on the manifold
- Valid ordering = topological sort (partial order)
- Cycle = irreducible frustration (like pigeonhole)
- UNSAT cycles become "irreducible manifold frustration"
- Every valid solution = valley floor in the ordering space

Why it fits:
- Topological ordering is inherently a manifold problem
- Dependencies create constraint structure
- Multiple valid orderings = multiple valleys
- Cycle detection = frustration floor (impossible to satisfy all)
"""

from collections import defaultdict, deque
from typing import List, Optional, Tuple


def alien_order(words: List[str]) -> str:
    """
    Derive alien dictionary ordering from sorted words.

    Returns empty string if impossible (cycle detected).
    """

    # Build graph: character -> set of characters that must follow it
    graph = defaultdict(set)
    in_degree = {}

    # Initialize all characters
    for word in words:
        for c in word:
            in_degree[c] = 0

    # Build edges from word comparisons
    for i in range(len(words) - 1):
        w1, w2 = words[i], words[i + 1]

        # Find first differing character
        j = 0
        while j < min(len(w1), len(w2)) and w1[j] == w2[j]:
            j += 1

        if j < min(len(w1), len(w2)):
            # w1[j] must come before w2[j]
            after = w2[j]
            before = w1[j]
            if after not in graph[before]:
                graph[before].add(after)
                in_degree[after] += 1
        elif len(w1) > len(w2):
            # w1 is longer but w2 is a prefix of w1 — INVALID
            return ""  # Cycle-like UNSAT (impossible ordering)

    # Kahn's algorithm for topological sort
    queue = deque()
    for c, d in in_degree.items():
        if d == 0:
            queue.append(c)

    result = []
    while queue:
        c = queue.popleft()
        result.append(c)

        for neighbor in graph[c]:
            in_degree[neighbor] -= 1
            if in_degree[neighbor] == 0:
                queue.append(neighbor)

    # Check for cycle (not all nodes processed)
    if len(result) != len(in_degree):
        return ""  # Cycle detected

    return "".join(result)


# =============================================================================
# PRIME TOPOLOGY INTERPRETATION
# =============================================================================

def analyze_ordering_space(words: List[str]) -> dict:
    """
    Analyze the "manifold structure" of an alien dictionary problem.

    Key metrics:
    - Total unique characters (manifold dimensions)
    - Edge density (constraint complexity)
    - Cycle presence (irreducible frustration)
    - Solution count (valley multiplicity)
    """

    chars = set()
    for word in words:
        chars.update(word)

    # Build adjacency info
    graph = defaultdict(set)
    in_degree = {c: 0 for c in chars}

    for i in range(len(words) - 1):
        w1, w2 = words[i], words[i + 1]
        j = 0
        while j < min(len(w1), len(w2)) and w1[j] == w2[j]:
            j += 1
        if j < min(len(w1), len(w2)):
            before, after = w1[j], w2[j]
            if after not in graph[before]:
                graph[before].add(after)
                in_degree[after] += 1

    # Detect cycle using DFS
    def has_cycle(node, visited, rec_stack):
        visited.add(node)
        rec_stack.add(node)

        for neighbor in graph[node]:
            if neighbor not in visited:
                if has_cycle(neighbor, visited, rec_stack):
                    return True
            elif neighbor in rec_stack:
                return True

        rec_stack.remove(node)
        return False

    visited = set()
    has_cycle_result = False
    for c in chars:
        if c not in visited:
            if has_cycle(c, visited, set()):
                has_cycle_result = True
                break

    # Count independent components (potential solution multiplicity)
    visited_again = set()
    components = 0

    for c in chars:
        if c not in visited_again:
            stack = [c]
            while stack:
                node = stack.pop()
                if node in visited_again:
                    continue
                visited_again.add(node)
                for neighbor in graph[node]:
                    if neighbor not in visited_again:
                        stack.append(neighbor)
            components += 1

    return {
        "unique_chars": len(chars),
        "total_edges": sum(len(v) for v in graph.values()),
        "has_cycle": has_cycle_result,
        "connected_components": components,
        "edge_density": sum(len(v) for v in graph.values()) / len(chars) if chars else 0,
    }


def find_all_valid_orderings(words: List[str]) -> List[str]:
    """
    Find ALL possible valid orderings (all valleys).

    This shows the multiplicity of solutions in the manifold.
    """

    chars = set()
    for word in words:
        chars.update(word)

    graph = defaultdict(set)
    in_degree = {c: 0 for c in chars}

    for i in range(len(words) - 1):
        w1, w2 = words[i], words[i + 1]
        j = 0
        while j < min(len(w1), len(w2)) and w1[j] == w2[j]:
            j += 1
        if j < min(len(w1), len(w2)):
            before, after = w1[j], w2[j]
            if after not in graph[before]:
                graph[before].add(after)
                in_degree[after] += 1

    results = []

    def backtrack(path: List[str], remaining: dict):
        if not remaining:
            results.append("".join(path))
            return

        # Find all chars with in_degree 0
        zero_degree = [c for c in remaining if remaining[c] == 0]

        for c in zero_degree:
            # Choose this character
            new_remaining = dict(remaining)
            del new_remaining[c]

            for neighbor in graph[c]:
                if neighbor in new_remaining:
                    new_remaining[neighbor] -= 1

            backtrack(path + [c], new_remaining)

    backtrack([], in_degree)
    return results


# =============================================================================
# DEMONSTRATION
# =============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("ALIEN DICTIONARY — TOPOLOGICAL ORDERING GEOMETRY")
    print("=" * 60)

    test_cases = [
        (["wrt", "wrf", "er", "ett", "rftt"], "wertf"),
        (["z", "x"], "zx"),
        (["z", "z"], "z"),  # duplicate words
        (["ab", "abc"], "abc"),  # single constraint
        (["abc", "ab"], ""),  # impossible - prefix case
        (["caa", "cbb", "bba"], "cab"),  # multiple constraints
    ]

    for words, expected in test_cases:
        print(f"\n{'=' * 40}")
        print(f"Words: {words}")
        print(f"Expected: {expected}")

        result = alien_order(words)
        status = "✓" if result == expected else "✗"
        print(f"Got: {result if result else '(cycle)'} {status}")

        analysis = analyze_ordering_space(words)
        print(f"\nManifold analysis:")
        print(f"  Unique chars: {analysis['unique_chars']}")
        print(f"  Total edges: {analysis['total_edges']}")
        print(f"  Edge density: {analysis['edge_density']:.2f}")
        print(f"  Has cycle: {analysis['has_cycle']}")
        print(f"  Components: {analysis['connected_components']}")

        if not analysis['has_cycle'] and analysis['unique_chars'] <= 8:
            all_orderings = find_all_valid_orderings(words)
            print(f"\nAll valid orderings ({len(all_orderings)}):")
            for o in all_orderings:
                print(f"  {o}")

    print("\n" + "=" * 60)
    print("CYCLE DETECTION AS FRUSTRATION GEOMETRY")
    print("=" * 60)

    print("""
In prime topology language:

> "UNSAT cycles become irreducible manifold frustration."

A cycle in the ordering graph means:
- You can't satisfy all constraints simultaneously
- No matter how you arrange the characters, one dependency breaks
- The "frustration floor" is nonzero

Example: ["ab", "ba"]
- 'a' before 'b' from first pair
- 'b' before 'a' from second pair
- Cycle: a->b and b->a
- Irreducible frustration: impossible to resolve

This is exactly like the pigeonhole problem:
- 2 holes (positions), 2 items both requiring position 1
- The geometry makes violations unavoidable

The manifold correctly identifies UNSAT by never
reaching a zero-energy state.
""")