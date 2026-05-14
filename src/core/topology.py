#!/usr/bin/env python3
"""
Constraint Topology — Detailed, explicit layer for overlap-driven constraint systems

This is the "as detailed as possible" version while staying readable and non-magical.

Core philosophy:
- Topology = pure declarative structure (groups + variables + overlaps)
- No hidden state, no auto-compilation, no DSL
- Clear separation from the execution engine (LocalCRTGroup)
- Designed for dynamic repair scenarios (the real killer app)

Author: Grok + Sethu collaboration, May 2026
"""

from typing import List, Dict, Set, Optional, Callable, Any
from dataclasses import dataclass, field
from src.core.local_crt import LocalCRTGroup


@dataclass
class Variable:
    """A variable in the system (cell, job, order, nurse shift, etc.)"""
    name: str
    domain_size: int = 9
    groups: List[str] = field(default_factory=list)
    positions: Dict[str, int] = field(default_factory=dict)
    initial_value: Optional[int] = None   # for pre-filled / committed values


class ConstraintTopology:
    """
    Detailed explicit representation of overlap topology.

    You build it by declaring:
    - Groups (with optional per-group validators)
    - Variables
    - Connections (which variables live in which groups at which positions)

    Then you can:
    - Query the structure
    - Validate consistency
    - Materialize into executable LocalCRTGroup instances
    - Export for visualization or persistence
    """

    def __init__(self, name: str = "default"):
        self.name: str = name
        self.groups: Dict[str, Dict[str, Any]] = {}        # group_name -> metadata
        self.variables: Dict[str, Variable] = {}
        self.group_instances: Dict[str, LocalCRTGroup] = {}
        self._materialized: bool = False

    # ===================== CORE DECLARATION =====================
    def add_group(self, name: str, size: int, 
                  validator: Optional[Callable[[List[int], Set[int]], bool]] = None,
                  metadata: Optional[Dict] = None):
        """Declare a constraint group (row, column, box, machine, time slot, etc.)"""
        if name in self.groups:
            raise ValueError(f"Group '{name}' already exists")
        self.groups[name] = {
            "size": size,
            "validator": validator,
            "metadata": metadata or {}
        }

    def add_variable(self, name: str, domain_size: int = 9, initial_value: Optional[int] = None):
        """Declare a variable that can participate in multiple groups"""
        if name in self.variables:
            raise ValueError(f"Variable '{name}' already exists")
        self.variables[name] = Variable(name, domain_size, initial_value=initial_value)

    def connect(self, var_name: str, group_name: str, position: int):
        """
        Declare that this variable lives in this group at this position.
        This is the heart of the overlap topology.
        """
        if var_name not in self.variables:
            raise ValueError(f"Unknown variable: {var_name}")
        if group_name not in self.groups:
            raise ValueError(f"Unknown group: {group_name}")
        if position < 0 or position >= self.groups[group_name]["size"]:
            raise ValueError(f"Position {position} out of range for group {group_name}")

        var = self.variables[var_name]
        if group_name in var.groups:
            raise ValueError(f"Variable {var_name} already connected to {group_name}")

        var.groups.append(group_name)
        var.positions[group_name] = position

    # ===================== QUERIES (very detailed) =====================
    def get_variables_in_group(self, group_name: str) -> List[str]:
        """Return all variable names that belong to this group"""
        return [v.name for v in self.variables.values() if group_name in v.groups]

    def get_groups_for_variable(self, var_name: str) -> List[str]:
        return self.variables[var_name].groups if var_name in self.variables else []

    def get_position(self, var_name: str, group_name: str) -> int:
        return self.variables[var_name].positions[group_name]

    def get_group_size(self, group_name: str) -> int:
        return self.groups[group_name]["size"]

    def get_all_group_names(self) -> List[str]:
        return list(self.groups.keys())

    def get_all_variable_names(self) -> List[str]:
        return list(self.variables.keys())

    def get_overlap_degree(self, var_name: str) -> int:
        """How many groups does this variable participate in? (degree in the hypergraph)"""
        return len(self.get_groups_for_variable(var_name))

    def find_potential_conflicts(self, var_name: str, value: int) -> List[str]:
        """
        Which groups would be affected if we set this variable to this value?
        Useful for repair planning.
        """
        affected = []
        for gname in self.get_groups_for_variable(var_name):
            # This is a lightweight check — real conflict detection happens in the engine
            affected.append(gname)
        return affected

    # ===================== VALIDATION =====================
    def validate_topology(self) -> List[str]:
        """Check for structural problems (duplicate positions, orphan groups, etc.)"""
        errors = []
        for gname, ginfo in self.groups.items():
            positions_used = set()
            for v in self.variables.values():
                if gname in v.positions:
                    pos = v.positions[gname]
                    if pos in positions_used:
                        errors.append(f"Position {pos} in group '{gname}' used more than once")
                    positions_used.add(pos)
            if len(positions_used) != ginfo["size"]:
                errors.append(f"Group '{gname}' has {len(positions_used)} variables but size {ginfo['size']}")
        return errors

    # ===================== MATERIALIZATION =====================
    def materialize(self, reset: bool = True) -> Dict[str, LocalCRTGroup]:
        """Create executable LocalCRTGroup instances from the declared topology"""
        if reset:
            self.group_instances = {}

        for gname, ginfo in self.groups.items():
            grp = LocalCRTGroup(name=gname, size=ginfo["size"])
            if ginfo["validator"]:
                grp._custom_validator = ginfo["validator"]
            self.group_instances[gname] = grp

        self._materialized = True
        return self.group_instances

    def get_group_instance(self, group_name: str) -> Optional[LocalCRTGroup]:
        return self.group_instances.get(group_name)

    # ===================== INITIAL ASSIGNMENTS (for repair scenarios) =====================
    def set_initial_value(self, var_name: str, value: int):
        """Mark a variable as pre-committed (useful for dynamic repair)"""
        if var_name not in self.variables:
            raise ValueError(f"Unknown variable: {var_name}")
        self.variables[var_name].initial_value = value

    def apply_initial_assignments(self):
        """Push all initial values into the materialized groups (call after materialize)"""
        if not self._materialized:
            self.materialize()

        for var_name, var in self.variables.items():
            if var.initial_value is not None:
                for gname in var.groups:
                    pos = var.positions[gname]
                    grp = self.group_instances[gname]
                    grp.transition(pos, var.initial_value)

    # ===================== EXPORT / SERIALIZATION =====================
    def to_dict(self) -> Dict[str, Any]:
        """Export the topology in a clean, serializable format"""
        return {
            "name": self.name,
            "groups": {k: {"size": v["size"], "metadata": v.get("metadata", {})} 
                       for k, v in self.groups.items()},
            "variables": {
                name: {
                    "domain_size": v.domain_size,
                    "groups": v.groups,
                    "positions": v.positions,
                    "initial_value": v.initial_value
                } for name, v in self.variables.items()
            }
        }

    def summary(self) -> str:
        return (f"ConstraintTopology '{self.name}': "
                f"{len(self.groups)} groups, {len(self.variables)} variables, "
                f"avg overlap = {sum(len(v.groups) for v in self.variables.values()) / max(1, len(self.variables)):.2f}")

    # ===================== BUILT-IN HELPERS =====================
    @classmethod
    def sudoku_9x9(cls) -> "ConstraintTopology":
        """Factory for classic Sudoku topology"""
        topo = cls("sudoku_9x9")
        for i in range(9):
            topo.add_group(f"row{i}", 9)
            topo.add_group(f"col{i}", 9)
            topo.add_group(f"box{i}", 9)

        for r in range(9):
            for c in range(9):
                var = f"r{r}c{c}"
                topo.add_variable(var)
                box = (r // 3) * 3 + (c // 3)
                box_pos = (r % 3) * 3 + (c % 3)
                topo.connect(var, f"row{r}", c)
                topo.connect(var, f"col{c}", r)
                topo.connect(var, f"box{box}", box_pos)
        return topo

    @classmethod
    def latin_square(cls, order: int = 4) -> "ConstraintTopology":
        """Factory for Latin Square of given order"""
        topo = cls(f"latin_square_{order}x{order}")
        for i in range(order):
            topo.add_group(f"row{i}", order)
            topo.add_group(f"col{i}", order)

        for r in range(order):
            for c in range(order):
                var = f"r{r}c{c}"
                topo.add_variable(var, domain_size=order)
                topo.connect(var, f"row{r}", c)
                topo.connect(var, f"col{c}", r)
        return topo

    @classmethod
    def nqueens(cls, n: int = 8) -> "ConstraintTopology":
        """Factory for N-Queens (rows + two diagonal groups)"""
        topo = cls(f"nqueens_{n}")
        for i in range(n):
            topo.add_group(f"row{i}", n)

        # Diagonals: main (r+c) and anti (r-c + offset)
        for d in range(2 * n - 1):
            topo.add_group(f"diag_main_{d}", n)
            topo.add_group(f"diag_anti_{d}", n)

        for r in range(n):
            for c in range(n):
                var = f"r{r}c{c}"
                topo.add_variable(var, domain_size=n)
                topo.connect(var, f"row{r}", c)
                topo.connect(var, f"diag_main_{r + c}", c)
                topo.connect(var, f"diag_anti_{r - c + n - 1}", c)
        return topo


if __name__ == "__main__":
    print("=== Detailed Constraint Topology Demo ===\n")

    # Sudoku example
    sudoku = ConstraintTopology.sudoku_9x9()
    print(sudoku.summary())
    print("Validation errors:", sudoku.validate_topology())
    print(f"cell r0c0 belongs to: {sudoku.get_groups_for_variable('r0c0')}")
    print(f"Position in row0: {sudoku.get_position('r0c0', 'row0')}")

    # Latin Square example
    latin = ConstraintTopology.latin_square(4)
    print("\n" + latin.summary())

    # N-Queens example
    queens = ConstraintTopology.nqueens(8)
    print(queens.summary())

    print("\nTopology layer is now very detailed and ready for use.")