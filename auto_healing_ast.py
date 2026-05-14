#!/usr/bin/env python3
"""
Geometric IF-ELSE + Lark AST Parser
===================================
A demonstration of a Lock-Preserving Incremental Refactorer.
Lark parses a DSL into an AST constraint space. 
When a perturbation breaks the AST, the CRT runtime computes the 
exact minimal repair cascade, locking all unaffected nodes.
"""

from lark import Lark, Transformer
from copy import deepcopy

# ─────────────────────────────────────────────
# 1. Lark Grammar & Transformer (The AST)
# ─────────────────────────────────────────────

DSL_GRAMMAR = """
start: system rules
system: "system" "{" service+ "}"
service: "service" CNAME "(" "zone:" INT ")"
rules: "rules" "{" rule+ "}"
rule: CNAME "(" CNAME "," CNAME ")"

%import common.CNAME
%import common.INT
%import common.WS
%ignore WS
"""

class ASTTransformer(Transformer):
    def service(self, items):
        return str(items[0]), int(items[1])
    def system(self, items):
        return {"services": dict(items)}
    def rule(self, items):
        return {"type": str(items[0]), "vars": (str(items[1]), str(items[2]))}
    def rules(self, items):
        return {"rules": items}
    def start(self, items):
        return {"state": items[0]["services"], "rules": items[1]["rules"]}

def parse_dsl(dsl_text):
    parser = Lark(DSL_GRAMMAR, parser='lalr')
    tree = parser.parse(dsl_text)
    return ASTTransformer().transform(tree)

def generate_dsl(state, rules):
    """Reconstructs the DSL text from the repaired state."""
    out = ["system {"]
    for svc, zone in state.items():
        out.append(f"    service {svc} (zone: {zone})")
    out.append("}")
    out.append("rules {")
    for r in rules:
        out.append(f"    {r['type']}({r['vars'][0]}, {r['vars'][1]})")
    out.append("}")
    return "\n".join(out)

# ─────────────────────────────────────────────
# 2. Geometric IF-ELSE (CRT) Repair Runtime
# ─────────────────────────────────────────────

PRIMES = [11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47]

def mod_inverse(a, m):
    return pow(a, -1, m)


class ConstraintGroup:
    """An ACID CRT Microspace representing a single AST Rule."""
    def __init__(self, name, rule_type, vars_involved, var_to_prime_idx):
        self.name = name
        self.rule_type = rule_type
        self.vars = vars_involved
        self.var_to_prime_idx = var_to_prime_idx
        self.primes = PRIMES
        
        self.z = 0
        self.residues = {}
        self.locked = set()

    def jump(self, var, val):
        """The Exact Algebraic Displacement (z' = z + kM)"""
        if var in self.locked:
            return self.z if self.residues.get(var) == val else None
        
        p_target = self.primes[self.var_to_prime_idx[var]]
        M = 1
        for l_var in self.locked:
            M *= self.primes[self.var_to_prime_idx[l_var]]
            
        if M == 1:
            new_z = val
        else:
            diff = (val - self.z) % p_target
            k = (diff * mod_inverse(M, p_target)) % p_target
            new_z = self.z + k * M
            
        self.z = new_z
        self.residues[var] = val
        self.locked.add(var)
        return new_z

    def is_valid(self):
        """Evaluates the semantic rule over the current residues."""
        if len(self.residues) < len(self.vars):
            return True
            
        v1, v2 = self.residues[self.vars[0]], self.residues[self.vars[1]]
        if self.rule_type == 'affinity':
            return v1 == v2
        elif self.rule_type == 'anti_affinity':
            return v1 != v2
        return False

    def reset_to(self, snapshot):
        self.z = snapshot.z
        self.residues = snapshot.residues.copy()
        self.locked = snapshot.locked.copy()


def try_place(var, val, groups_for_var):
    """Triple Synchronized Jump across overlapping AST constraints."""
    snaps = {g.name: deepcopy(g) for g in groups_for_var}
    
    for g in groups_for_var:
        if g.jump(var, val) is None or not g.is_valid():
            for rg in groups_for_var:
                rg.reset_to(snaps[rg.name])
            return False
    return True


def crt_solve(empty_vars, var_to_groups, available_zones, final_state):
    """Backtracking solver for variables knocked out by perturbation."""
    if not empty_vars:
        return True
    
    var = empty_vars[0]
    for val in available_zones:
        snaps = {g.name: deepcopy(g) for g in var_to_groups[var]}
        if try_place(var, val, var_to_groups[var]):
            final_state[var] = val
            if crt_solve(empty_vars[1:], var_to_groups, available_zones, final_state):
                return True
        for g in var_to_groups[var]:
            g.reset_to(snaps[g.name])
            
    return False


# ─────────────────────────────────────────────
# 3. The Orchestrator (AST -> Topology -> Repair)
# ─────────────────────────────────────────────

def auto_heal_ast(dsl_text, perturbations):
    ast = parse_dsl(dsl_text)
    initial_state = ast['state']
    rules = ast['rules']
    
    print("\n[AST PARSED] Extracted topology.")
    
    services = list(initial_state.keys())
    var_to_prime_idx = {svc: i for i, svc in enumerate(services)}
    
    # Build constraint groups
    groups = []
    var_to_groups = {svc: [] for svc in services}
    for i, r in enumerate(rules):
        g = ConstraintGroup(f"rule_{i}", r['type'], r['vars'], var_to_prime_idx)
        groups.append(g)
        var_to_groups[r['vars'][0]].append(g)
        var_to_groups[r['vars'][1]].append(g)

    final_state = {}

    # Apply forced perturbations
    print(f"[DISRUPTION] {perturbations}")
    for var, new_val in perturbations.items():
        if not try_place(var, new_val, var_to_groups[var]):
            raise Exception("Perturbation makes AST invalid!")
        final_state[var] = new_val

    # Lock unperturbed nodes; cascade unlock on conflict
    empty_vars = []
    preserved_count = 0
    for var, old_val in initial_state.items():
        if var in perturbations:
            continue
            
        snaps = {g.name: deepcopy(g) for g in var_to_groups[var]}
        if try_place(var, old_val, var_to_groups[var]):
            final_state[var] = old_val
            preserved_count += 1
        else:
            for g in var_to_groups[var]:
                g.reset_to(snaps[g.name])
            empty_vars.append(var)

    print(f"[SHIELD] {preserved_count}/{len(services)} nodes locked.")
    
    if empty_vars:
        print(f"[REPAIR] Cascading: {empty_vars}")
        success = crt_solve(empty_vars, var_to_groups, [1, 2, 3], final_state)
        if not success:
            raise Exception("Cannot auto-heal AST!")

    print("[SUCCESS] AST healed.\n")
    return generate_dsl(final_state, rules)


# ─────────────────────────────────────────────
# 4. Demo
# ─────────────────────────────────────────────

if __name__ == "__main__":
    original_code = """system {
    service frontend (zone: 1)
    service backend (zone: 2)
    service database (zone: 3)
    service cache (zone: 2)
}
rules {
    anti_affinity(frontend, backend)
    anti_affinity(backend, database)
    affinity(backend, cache)
}"""

    print("=" * 50)
    print("ORIGINAL DSL:")
    print("=" * 50)
    print(original_code)

    # Zone 2 fails — backend must move to zone 1
    perturbation = {'backend': 1}
    
    repaired_code = auto_heal_ast(original_code, perturbation)

    print("=" * 50)
    print("AUTO-HEALED DSL:")
    print("=" * 50)
    print(repaired_code)
