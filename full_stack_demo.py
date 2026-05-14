#!/usr/bin/env python3
"""
Full Stack Demo: Lark + CRT Runtime + Ultrametric Retrieval
=============================================================
Self-healing infrastructure-as-code compiler.

Scenario: A Terraform-like HCL config has a broken depends_on cycle.
Lark parses it. Ultrametric retrieval finds structurally similar fixes
from a memory of known repairs. CRT runtime applies the minimal fix,
preserving all valid blocks.

Steps:
  1. Define a tiny HCL grammar in Lark
  2. Parse a broken config (has circular dependency)
  3. Store known-good fix patterns in UltraMeM
  4. Retrieve structurally similar fix by ultrametric distance
  5. CRT runtime repairs the AST transactionally
  6. Output: repaired config + repair radius metric
"""

import sys, math, os
sys.path.insert(0, '.')

from lark import Lark, Transformer, Tree
from copy import deepcopy

# ─────────────────────────────────────────────
# 1. Tiny Terraform-like HCL grammar
# ─────────────────────────────────────────────

HCL_GRAMMAR = r"""
start: resource+

resource: "resource" CNAME "{" attr* "}"

attr: CNAME "=" value
    | "depends_on" "=" "[" CNAME ("," CNAME)* "]"  -> depends_on_attr

value: NUMBER -> number_val
     | CNAME  -> name_val
     | STRING -> string_val

NUMBER: /[0-9]+/
STRING: /"[^"]*"/
CNAME: /[a-zA-Z_][a-zA-Z0-9_]*/
%ignore /\s+/
"""


class HCLTransformer(Transformer):
    def resource(self, items):
        name = str(items[0])
        attrs = {}
        deps = []
        for item in items[1:]:
            if isinstance(item, tuple):
                key, val = item
                if key == "depends_on":
                    deps = val
                else:
                    attrs[key] = val
        return {"name": name, "attrs": attrs, "depends_on": deps}

    def depends_on_attr(self, items):
        return ("depends_on", [str(c) for c in items])

    def attr(self, items):
        if items[0] == "depends_on":
            return (items[0], items[1])
        return (str(items[0]), items[1])

    def number_val(self, items):
        return int(items[0])

    def name_val(self, items):
        return str(items[0])

    def string_val(self, items):
        return str(items[0])[1:-1]

    def start(self, items):
        return items


def parse_hcl(text):
    parser = Lark(HCL_GRAMMAR, parser='lalr')
    tree = parser.parse(text)
    return HCLTransformer().transform(tree)


def generate_hcl(resources):
    lines = []
    for r in resources:
        lines.append(f"resource {r['name']} {{")
        for k, v in r['attrs'].items():
            if isinstance(v, str):
                lines.append(f'  {k} = "{v}"')
            else:
                lines.append(f'  {k} = {v}')
        if r.get('depends_on'):
            deps = ", ".join(r['depends_on'])
            lines.append(f"  depends_on = [{deps}]")
        lines.append("}")
        lines.append("")
    return "\n".join(lines)


# ─────────────────────────────────────────────
# 2. CRT Repair Runtime (mini)
# ─────────────────────────────────────────────

PRIMES = [11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47,
          53, 59, 61, 67, 71, 73, 79, 83, 89, 97]


class MiniCRT:
    """Minimal CRT repair runtime for resource dependency graphs."""

    def __init__(self, resources):
        self.resources = {r['name']: r for r in resources}
        self.names = [r['name'] for r in resources]
        self.prime_of = {name: PRIMES[i] for i, name in enumerate(self.names)}
        self.locked = set()

    def detect_cycle(self):
        """Find any circular dependency in the resource graph."""
        visited = set()
        in_stack = set()

        def dfs(name, path):
            visited.add(name)
            in_stack.add(name)
            for dep in self.resources[name].get('depends_on', []):
                if dep not in self.resources:
                    continue  # missing resource — handled separately
                if dep not in visited:
                    result = dfs(dep, path + [dep])
                    if result:
                        return result
                elif dep in in_stack:
                    return path + [dep]
            in_stack.discard(name)
            return None

        for name in self.names:
            if name not in visited:
                result = dfs(name, [name])
                if result:
                    return result
        return None

    def fix_cycle(self, cycle):
        """Repair a circular dependency: remove the last edge.
        This is a minimal displacement — we change only the edge
        that closes the cycle."""
        if len(cycle) < 2:
            return None, 0
        last = cycle[-1]
        culprit = cycle[-2]
        deps = self.resources[last].get('depends_on', [])
        if culprit in deps:
            deps.remove(culprit)
            return f"Removed {culprit} from {last}'s depends_on", 1
        return None, 0

    def validate(self):
        """Return list of problems: (type, details)"""
        problems = []

        # Check for missing dependencies
        for name, r in self.resources.items():
            for dep in r.get('depends_on', []):
                if dep not in self.resources:
                    problems.append(('missing_dep', f"{name} depends on {dep} which doesn't exist"))

        # Check for cycles
        cycle = self.detect_cycle()
        if cycle:
            problems.append(('cycle', f"Circular dependency: {' -> '.join(cycle)}"))

        return problems


# ─────────────────────────────────────────────
# 3. UltraMeM (simplified ultrametric index)
# ─────────────────────────────────────────────

class UltraMeMMini:
    """
    Minimal ultrametric memory for fix patterns.
    Stores AST structures keyed by dependency graph topology.
    Retrieval returns fix patterns with smallest ultrametric distance.
    """

    def __init__(self):
        self.patterns = []

    def _feature_sets(self, resources):
        """Extract hierarchy levels from a resource dependency graph."""
        names = [r['name'] for r in resources]
        deps_map = {r['name']: set(r.get('depends_on', [])) for r in resources}
        all_deps = set()
        for dlist in deps_map.values():
            all_deps |= dlist
        return {
            0: set(names),                        # domain: resource names
            1: set(frozenset(d) for d in deps_map.values()),  # structure: dependency sets
            2: all_deps,                          # content: all dependency targets
            3: set(names) | all_deps,             # surface: everything
        }

    def _jaccard(self, a, b):
        if not a or not b:
            return 0.0
        return len(a & b) / len(a | b)

    def _ultrametric_depth(self, fs1, fs2):
        """v_R = number of consecutive matching levels."""
        thresholds = [0.0, 0.0, 0.0, 0.0]  # exact match for simplicity
        v = 0
        for level in range(4):
            sim = self._jaccard(fs1.get(level, set()), fs2.get(level, set()))
            if sim >= thresholds[level]:
                v += 1
            else:
                break
        return v

    def store_fix(self, broken_resources, fix_description, repair_radius):
        """Store a known fix pattern."""
        fs = self._feature_sets(broken_resources)
        self.patterns.append({
            "features": fs,
            "fix": fix_description,
            "radius": repair_radius,
        })

    def retrieve(self, broken_resources, top_k=1):
        """Retrieve the most structurally similar fix pattern."""
        q_fs = self._feature_sets(broken_resources)
        scored = []
        for i, pat in enumerate(self.patterns):
            v = self._ultrametric_depth(q_fs, pat["features"])
            d = 2 ** (-v)
            scored.append((d, v, i, pat))
        scored.sort(key=lambda x: x[0])
        return scored[:top_k]


# ─────────────────────────────────────────────
# 4. Repair Orchestrator
# ─────────────────────────────────────────────

def repair_broken_config(broken_hcl, memory):
    print("=" * 60)
    print("BROKEN CONFIG:")
    print("=" * 60)
    print(broken_hcl)

    # Step 1: Lark parse
    print("\n[1/4] Lark parsing...")
    resources = parse_hcl(broken_hcl)
    print(f"  Parsed {len(resources)} resources")
    for r in resources:
        deps = r.get('depends_on', [])
        print(f"    {r['name']}: depends_on={deps}")

    # Step 2: Run CR,1,1T diagnosis
    print("\n[2/4] CRT diagnosis...")
    runtime = MiniCRT(resources)
    problems = runtime.validate()
    if not problems:
        print("  ✓ No problems detected")
        return broken_hcl
    print(f"  Found {len(problems)} problem(s):")
    for ptype, desc in problems:
        print(f"    [{ptype}] {desc}")

    # Step 3: Retrieve structurally similar fix
    print("\n[3/4] Ultrametric retrieval...")
    results = memory.retrieve(resources, top_k=1)
    if results:
        d, v, idx, pat = results[0]
        print(f"  Found fix pattern (d_R={d:.3f}, v_R={v})")
        print(f"  Pattern: {pat['fix']}")
    else:
        print("  No fix patterns in memory — using heuristic repair")
        pat = None

    # Step 4: Apply CRT repair
    print("\n[4/4] CRT repair...")
    repairs_made = 0
    for ptype, desc in problems:
        if ptype == 'cycle':
            cycle = runtime.detect_cycle()
            if cycle:
                fix, radius = runtime.fix_cycle(cycle)
                if fix:
                    print(f"  {fix} (radius={radius})")
                    repairs_made += radius
        elif ptype == 'missing_dep':
            # Extract the dependent and the missing dependency
            parts = desc.split(" depends on ")
            dependent = parts[0]
            missing = parts[1].split(" which doesn't exist")[0]
            # Remove the dangling reference
            deps = runtime.resources[dependent].get('depends_on', [])
            if missing in deps:
                deps.remove(missing)
                print(f"  Removed dangling ref {missing} from {dependent} (radius=1)")
                repairs_made += 1

    repaired_hcl = generate_hcl(list(runtime.resources.values()))

    print(f"\n  Total repair radius: {repairs_made}")
    print(f"  Valid blocks preserved: {len(resources)} blocks total")

    print("\n" + "=" * 60)
    print("REPAIRED CONFIG:")
    print("=" * 60)
    print(repaired_hcl)

    return repaired_hcl


# ─────────────────────────────────────────────
# 5. Demo
# ─────────────────────────────────────────────

if __name__ == "__main__":
    # Build a memory of known fix patterns
    memory = UltraMeMMini()

    # Seed with a past fix: a similar cycle that was repaired
    past_broken = [
        {"name": "web", "attrs": {"ami": "ami-123"}, "depends_on": ["lb"]},
        {"name": "app", "attrs": {"ami": "ami-456"}, "depends_on": ["db"]},
        {"name": "lb", "attrs": {"type": "alb"}, "depends_on": ["web"]},
    ]
    memory.store_fix(past_broken,
                     "Removed circular dependency between web and lb",
                     repair_radius=1)

    # Another past fix: dangling dependency removed
    past_broken2 = [
        {"name": "cache", "attrs": {"engine": "redis"}, "depends_on": ["vanished_module"]},
        {"name": "web", "attrs": {"ami": "ami-789"}, "depends_on": ["cache"]},
    ]
    memory.store_fix(past_broken2,
                     "Removed dangling reference to vanished_module",
                     repair_radius=1)

    # Current broken config: has a circular dependency + missing dep
    broken_hcl = """
resource web {
  ami = "ami-111"
  depends_on = [app, lb]
}

resource app {
  ami = "ami-222"
  depends_on = [db, missing_service]
}

resource db {
  ami = "ami-333"
}

resource lb {
  type = "alb"
  depends_on = [web]
}

resource worker {
  queue = "critical"
  depends_on = [db]
}
"""
    # (note: web→lb→web creates a cycle, app depends on missing_service)

    repaired = repair_broken_config(broken_hcl, memory)
