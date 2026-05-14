"""
Word Ladder II — Prime Topology Interpretation

Problem: Find ALL shortest transformation sequences from start to end,
where each step changes exactly one letter and intermediate words must
exist in the word list.

Framework interpretation:
- Each word = coordinate in a modular constraint space
- Valid 1-letter mutations = connected sheets in the manifold
- Shortest paths = geodesics across equal-energy basins
- Multiple solutions = multiple equal-depth valleys

The "safe corridor" analogy:
- Already-valid prefix transforms = satisfied prime constraints
- Monodromy jumps = structured leaps to new mutation frontier
- Dead ends = frustration spikes where no valid mutations exist
"""

from collections import defaultdict, deque
from typing import List, Set, Tuple


def build_adjacency(word_list: Set[str]) -> dict:
    """
    Build adjacency map: word -> all valid 1-letter mutations.
    In our framework, this is the "sheet connectivity" of the manifold.
    """
    adjacency = {}
    words = list(word_list)

    for word in words:
        adjacency[word] = set()
        for other in words:
            if word == other:
                continue
            # Count differing characters
            diff = sum(c1 != c2 for c1, c2 in zip(word, other))
            if diff == 1:
                adjacency[word].add(other)

    return adjacency


def word_ladder_prime(start: str, end: str, word_list: List[str]) -> List[List[str]]:
    """
    Find ALL shortest transformation sequences using prime topology approach.

    The key insight for our framework:
    - Each word state is a "residue" on the manifold
    - Valid mutations are transitions between connected sheets
    - All shortest paths have equal "manifold depth"
    - Multiple solutions = multiple equal-energy valleys
    """
    word_set = set(word_list)
    if end not in word_set:
        return []

    # Build the adjacency graph (sheet connectivity)
    adjacency = build_adjacency(word_set)

    # BFS to find shortest path length AND all nodes at each level
    # This is like finding the "energy contour" of the landscape
    level_words = {start: [[start]]}  # word -> all paths reaching it

    visited = {start}
    found_paths = []

    while level_words:
        next_level = defaultdict(list)

        for word, paths in level_words.items():
            if word == end:
                # We've reached a valley floor — collect all paths of this depth
                found_paths.extend(paths)
                continue

            for next_word in adjacency[word]:
                if next_word not in visited:
                    for path in paths:
                        next_level[next_word].append(path + [next_word])

        if found_paths:
            # Found end — all paths collected are shortest (same BFS depth)
            return found_paths

        visited.update(next_level.keys())
        level_words = next_level

    return []  # No path exists


def word_ladder_classic(start: str, end: str, word_list: List[str]) -> List[List[str]]:
    """
    Standard BFS approach with parent tracking for comparison.
    """
    word_set = set(word_list)
    if end not in word_set:
        return []

    adjacency = build_adjacency(word_set)

    # BFS to find level of each word
    level = {start: 0}
    parents = defaultdict(set)
    queue = deque([start])
    found_level = None

    while queue:
        word = queue.popleft()
        curr_level = level[word]

        if found_level is not None and curr_level >= found_level:
            continue

        for next_word in adjacency[word]:
            if next_word not in level:
                level[next_word] = curr_level + 1
                queue.append(next_word)
            if level[next_word] == curr_level + 1:
                parents[next_word].add(word)

        if word == end:
            found_level = curr_level

    if found_level is None:
        return []

    # Reconstruct all paths from parents
    def dfs(word, path):
        if word == start:
            result.append(path[::-1])
            return
        for parent in parents[word]:
            dfs(parent, path + [word])

    result = []
    dfs(end, [])
    return result


# =============================================================================
# PRIME TOPOLOGY ANALYSIS
# =============================================================================

def analyze_landscape(start: str, end: str, word_list: List[str]):
    """
    Analyze the "manifold structure" of a word ladder problem.

    Key metrics:
    - Total nodes / edges (manifold size)
    - Branching factor at each level (topological complexity)
    - Number of solutions (valley multiplicity)
    - Dead end density (frustration spikes)
    """
    word_set = set(word_list)
    if end not in word_set:
        return {"error": "end not in word list"}

    adjacency = build_adjacency(word_set)

    # BFS to analyze structure
    level_data = [{start: 0}]
    visited = {start: 0}
    queue = deque([start])
    found_level = None
    solution_count = 0

    while queue:
        word = queue.popleft()
        level = visited[word]

        if found_level is not None and level > found_level:
            break

        for next_word in adjacency[word]:
            if next_word not in visited:
                visited[next_word] = level + 1
                queue.append(next_word)
            elif visited[next_word] == level + 1:
                pass  # Multiple parents at same level

        if word == end:
            found_level = level

    # Analyze branching at each level
    level_branching = {}
    for word, lvl in visited.items():
        if lvl not in level_branching:
            level_branching[lvl] = {"nodes": 0, "total_neighbors": 0}
        level_branching[lvl]["nodes"] += 1
        level_branching[lvl]["total_neighbors"] += len(adjacency[word])

    # Count dead ends (nodes with no path to end)
    reachable_from_start = set(visited.keys())

    # Get nodes that can reach end (reverse BFS from end)
    reverse_visited = set()
    queue = deque([end])
    while queue:
        word = queue.popleft()
        if word in reverse_visited:
            continue
        reverse_visited.add(word)
        for prev in adjacency.get(word, []):
            if prev not in reverse_visited:
                queue.append(prev)

    dead_ends = reachable_from_start - reverse_visited
    dead_end_ratio = len(dead_ends) / len(reachable_from_start) if reachable_from_start else 0

    return {
        "manifold_size": len(visited),
        "shortest_length": found_level,
        "total_edges": sum(len(adjacency[w]) for w in visited),
        "dead_end_ratio": dead_end_ratio,
        "level_branching": level_branching,
    }


# =============================================================================
# DEMONSTRATION
# =============================================================================

if __name__ == "__main__":
    # Example 1: "hit" -> "cog"
    # Classic hard case with multiple solutions
    words1 = ["hot", "dot", "dog", "lot", "log", "cog", "hit", "hot"]

    print("=" * 60)
    print("WORD LADDER II — PRIME TOPOLOGY ANALYSIS")
    print("=" * 60)

    print("\nExample 1: hit -> cog")
    print("-" * 40)
    result = word_ladder_prime("hit", "cog", words1)
    print(f"Solutions found: {len(result)}")
    for path in result:
        print(f"  {' -> '.join(path)}")

    analysis = analyze_landscape("hit", "cog", words1)
    print(f"\nManifold analysis:")
    print(f"  Nodes: {analysis['manifold_size']}")
    print(f"  Shortest length: {analysis['shortest_length']}")
    print(f"  Total edges: {analysis['total_edges']}")
    print(f"  Dead end ratio: {analysis['dead_end_ratio']:.2%}")

    # Example 2: Custom harder case
    print("\n" + "=" * 60)
    print("Example 2: more complex landscape")
    print("-" * 40)

    words2 = [
        "aaaaa", "aaaab", "aaaac", "aaaad", "aaaae",
        "aabbb", "aabcc", "aabdd", "aabee",
        "abbbb", "abccc", "abddd", "abeee",
        "acccc", "acddd", "aceee",
        "adddd", "adeee",
        "eeeee"
    ]

    # This would be a longer path with branching
    result2 = word_ladder_prime("aaaaa", "eeeee", words2)
    print(f"Solutions found: {len(result2)}")

    # Show branching structure
    print("\nExpected behavior in prime topology framework:")
    print("- Multiple solution valleys = equal-energy attractors")
    print("- Dead ends = frustration spikes where no valid mutations exist")
    print("- Shortest path = geodesic through minimum-depth basins")
    print("- Each word state = residue on modular manifold")