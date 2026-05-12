"""
Regular Expression Matching as Manifold Navigation

Problem: Does pattern p match string s?
Pattern supports: '.' (any char), '*' (zero or more of preceding)

Framework interpretation:
- The DP table itself becomes a manifold
- Branches = different sheet transitions
- Epsilon transitions = monodromy jumps (preserving state without consuming chars)
- Admissible paths = valid match trajectories
- The "collapsed manifold" = acceptance basin (where all constraints satisfied)

Example: "a*b*c.*d"
- Each component creates sheet structure
- '*' creates multivalued transitions (zero, one, many)
- The final 'd' is the attractor state
- Multiple valid paths = multiple geodesics to acceptance

In our language:
> "the regex manifold collapsed into an admissible acceptance basin."

This is the MOST poetic fit because regex NFAs ARE topology disguised as automata.
"""

from functools import lru_cache
from typing import Tuple


def is_match(s: str, p: str) -> bool:
    """
    Classic regex matching with DP.

    In prime topology language:
    - dp[i][j] = coordinate on the manifold
    - Horizontal transitions = sheet navigation (consuming pattern chars)
    - Vertical transitions = epsilon transitions (state changes without consuming s)
    - '*' creates branching sheets (zero/many paths)
    - Acceptance = reaching a valley floor where all constraints satisfied
    """

    m, n = len(s), len(p)

    # dp[i][j] = does s[i:] match p[j:]?
    dp = [[False] * (n + 1) for _ in range(m + 1)]

    # Base case: empty string matches empty pattern
    dp[m][n] = True

    # Base case: empty string vs pattern
    for j in range(n - 1, -1, -1):
        if j + 1 < n and p[j] == '*':
            # zero occurrences: dp[m][j+2] if j+2 <= n, else dp[m][n] (empty pattern)
            dp[m][j] = dp[m][j + 2] if j + 2 <= n else dp[m][n]
        else:
            dp[m][j] = False

    # Fill the table
    for i in range(m - 1, -1, -1):
        for j in range(n - 1, -1, -1):
            if p[j] == '*':
                # Two paths: zero occurrences or one+ occurrences
                # In manifold terms: two sheets of the topology
                dp[i][j] = dp[i][j + 2] if j + 2 <= n else dp[i][n]  # zero
                if j + 1 < n:
                    # one+ — check if current char matches preceding
                    if p[j + 1] == '.' or p[j + 1] == s[i]:
                        dp[i][j] = dp[i][j] or dp[i + 1][j]
            elif p[j] == '.' or p[j] == s[i]:
                # Direct match — move diagonally on manifold
                dp[i][j] = dp[i + 1][j + 1]
            else:
                dp[i][j] = False

    return dp[0][0]


# =============================================================================
# PRIME TOPOLOGY INTERPRETATION
# =============================================================================

def analyze_regex_manifold(p: str) -> dict:
    """
    Analyze the topological structure of a regex pattern.

    Key metrics:
    - Number of sheets (distinct matching modes)
    - Branching complexity ('*' creates exponential sheets)
    - Epsilon transition density
    - Acceptance basin characteristics
    """

    analysis = {
        "pattern": p,
        "length": len(p),
        "sheets": 0,  # estimated branching factor
        "epsilon_density": 0,
        "star_count": 0,
        "dot_count": 0,
    }

    i = 0
    sheets = 1  # start with one sheet
    epsilon_count = 0

    while i < len(p):
        c = p[i]
        if c == '*':
            # '*' creates branching — each '*' doubles sheet count roughly
            sheets *= 2
            analysis["star_count"] += 1
            epsilon_count += 1  # zero-occurrence path
        elif c == '.':
            analysis["dot_count"] += 1
        i += 1

    analysis["sheets"] = sheets
    analysis["epsilon_density"] = epsilon_count / len(p) if len(p) > 0 else 0

    return analysis


def trace_match_path(s: str, p: str) -> list:
    """
    Trace all paths through the regex manifold.
    Returns list of paths showing the navigation steps.
    """
    m, n = len(s), len(p)
    paths = []

    def dfs(i: int, j: int, path: list):
        # Success: consumed both string and pattern
        if i == m and j == n:
            paths.append(path.copy())
            return

        # Dead end: pattern consumed but chars remain, or out of bounds
        if j >= n or i > m:
            return

        # '*' quantifier — lookahead at j+1
        if j + 1 < n and p[j + 1] == '*':
            # Zero occurrences: skip "X*"
            dfs(i, j + 2, path + [f"zero('{p[j]}*')"])
            # One or more: consume if match
            if i < m and (p[j] == '.' or p[j] == s[i]):
                dfs(i + 1, j, path + [f"consume('{s[i]}')"])
        # '.' wildcard
        elif p[j] == '.':
            if i < m:
                dfs(i + 1, j + 1, path + [f"dot('{s[i]}')"])
        # Direct character match
        elif i < m and s[i] == p[j]:
            dfs(i + 1, j + 1, path + [f"match('{s[i]}')"])

    dfs(0, 0, [])
    return paths


def is_match_v2(s: str, p: str) -> bool:
    """Simpler regex matching for testing."""
    if not p:
        return not s

    # Build character classes
    i, j = 0, 0
    while i < len(s) and j < len(p):
        if j + 1 < len(p) and p[j + 1] == '*':
            # Star quantifier
            if p[j] == '.' or p[j] == s[i]:
                i += 1  # consume one, stay at star
            else:
                j += 2  # skip star pattern, zero occurrences
        elif p[j] == '.':
            i += 1
            j += 1
        elif p[j] == s[i]:
            i += 1
            j += 1
        else:
            return False

    # Handle trailing star patterns
    while j + 1 < len(p) and p[j + 1] == '*':
        j += 2

    return i == len(s) and j == len(p)


# =============================================================================
# DEMONSTRATION
# =============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("REGEX MATCHING AS MANIFOLD NAVIGATION")
    print("=" * 60)

    test_cases = [
        ("aa", "a*", "Multiple 'a' transitions"),
        ("aab", "c*a*b", "c* can match zero 'c'"),
        ("", "a*", "Zero-length match via star"),
        ("mississippi", "mis*is*p*.", "Complex branching"),
        ("aaa", "a*a", "a* matches 'aa' then 'a'"),
        ("", "", "Empty matches empty"),
        ("abc", "a.c", "Dot wildcard"),
        ("aaaa", "a.*d", "Greedy star explosion"),
    ]

    print("\nmanifold analysis:")
    for s, p, desc in test_cases:
        analysis = analyze_regex_manifold(p)
        result = is_match(s, p)
        print(f"\n  Pattern: '{p}'")
        print(f"    sheets estimate: {analysis['sheets']}")
        print(f"    stars: {analysis['star_count']}, dots: {analysis['dot_count']}")
        print(f"    epsilon density: {analysis['epsilon_density']:.2f}")

    print("\n" + "=" * 60)
    print("PATH TRACING EXAMPLES")
    print("=" * 60)

    print("\nExample: 'aa' vs 'a*'")
    print("Expected: True (a* matches 'aa')")
    print("Manifold paths:")
    paths = trace_match_path("aa", "a*")
    print(f"  Found {len(paths)} paths through the manifold")
    for i, path in enumerate(paths):
        print(f"  Path {i + 1}: {path}")

    print("\nExample: 'aab' vs 'c*a*b'")
    print("Expected: True (c* matches zero, a* matches 'aa', b matches)")
    paths = trace_match_path("aab", "c*a*b")
    print(f"  Found {len(paths)} paths through the manifold")
    for i, path in enumerate(paths):
        print(f"  Path {i + 1}: {path}")

    print("\n" + "=" * 60)
    print("POETIC INTERPRETATION")
    print("=" * 60)

    print("""
In prime topology language:

> "The regex manifold collapsed into an admissible acceptance basin."

What this means:
- Pattern "a*b*c.*d" creates sheets for each component
- '*' creates branching topology (zero OR many)
- '.' creates wildcard sheets (any character fits)
- Multiple valid paths = multiple geodesics through the manifold
- All paths that reach acceptance lie in the same valley floor

The NFA interpretation is literally topology:
- States = sheets on the Riemann surface
- Transitions = winding around the central column
- '*' = multiple full rotations (0, 1, 2, ... times)
- Acceptance = landing on the correct floor

This is why regex matching is so elegantly expressible
as manifold navigation — NFAs were already doing topology.
""")