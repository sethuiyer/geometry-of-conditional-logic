defmodule ConstraintTopology do
  @moduledoc """
  ConstraintTopology — declarative overlap graph for distributed CRT repair.

  This module lets you declare any structured constraint problem purely in terms of:

    - groups  (constraint domains, each with its own prime modulus)
    - cells   (shared variables that live in multiple groups)
    - primes  (one per group, pairwise coprime within local neighborhoods)

  Once declared, the topology becomes the "map" that any RepairCoordinator reads
  to execute local CRT jumps, rollbacks, and checkpoint-based recovery.

  The key insight: Sudoku, scheduling, N-Queens, inventory allocation, and Latin
  Squares all become *different topology declarations on the same repair runtime*.

  ## Architecture

      topology
      ├── groups  %{name => %{prime: p, domain: 0..(p-1)}}
      ├── cells   %{cell_id => [group_name, ...]}
      └── edges   [{group_a, group_b, shared_cells: [...]}]

  ## Example: Sudoku

      topology =
        ConstraintTopology.new()
        |> ConstraintTopology.add_group(:row0, prime: 11)
        |> ConstraintTopology.add_group(:row1, prime: 13)
        |> ConstraintTopology.add_group(:col0, prime: 7)
        |> ConstraintTopology.add_group(:box0, prime: 17)
        |> ConstraintTopology.add_cell(:r0c0, [:row0, :col0, :box0])

  ## Example: CPU Scheduling

      topology =
        ConstraintTopology.new()
        |> ConstraintTopology.add_group(:core0, prime: 5)
        |> ConstraintTopology.add_group(:core1, prime: 7)
        |> ConstraintTopology.add_group(:deadline_rt, prime: 11)
        |> ConstraintTopology.add_group(:numa_node0, prime: 13)
        |> ConstraintTopology.add_cell(:task_a, [:core0, :deadline_rt])

  """

  defstruct groups: %{}, cells: %{}, edges: [], next_prime_idx: 0

  @type t :: %__MODULE__{
          groups: %{atom() => %{prime: integer(), domain: Range.t()}},
          cells: %{atom() => [atom()]},
          edges: [{atom(), atom(), [atom()]}],
          next_prime_idx: non_neg_integer()
        }

  @default_primes [2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47]

  @doc "Create an empty topology."
  @spec new() :: t()
  def new, do: %__MODULE__{}

  @doc "Add a constraint group with an explicit prime modulus."
  @spec add_group(t(), atom(), prime: integer()) :: t()
  def add_group(topology, name, prime: prime) when is_atom(name) and is_integer(prime) do
    %{topology |
      groups: Map.put(topology.groups, name, %{
        prime: prime,
        domain: 0..(prime - 1)
      })
    }
  end

  @doc "Add a constraint group, auto-assigning the next available prime."
  @spec add_group(t(), atom()) :: t()
  def add_group(topology, name) when is_atom(name) do
    prime = Enum.at(@default_primes, topology.next_prime_idx, nil)
    if prime do
      topology
      |> add_group(name, prime: prime)
      |> put_next_prime_idx(topology.next_prime_idx + 1)
    else
      raise "ran out of default primes — pass prime: explicitly"
    end
  end

  defp put_next_prime_idx(topology, idx) do
    %{topology | next_prime_idx: idx}
  end

  @doc """
  Declare a shared cell/variable that participates in multiple groups.

  The cell becomes an overlap edge connecting all listed groups.
  """
  @spec add_cell(t(), atom(), [atom()]) :: t()
  def add_cell(topology, cell_id, group_names) when is_list(group_names) do
    topology = Map.update!(topology, :cells, &Map.put(&1, cell_id, group_names))

    # Generate pairwise edges for all group combinations sharing this cell
    pairs = for a <- group_names, b <- group_names, a < b, do: {a, b, cell_id}
    edges = Enum.reduce(pairs, topology.edges, fn {a, b, cell}, acc ->
      case Enum.find(acc, fn {ga, gb, _} -> ga == a and gb == b end) do
        nil -> [{a, b, [cell]} | acc]
        {^a, ^b, existing_cells} ->
          Enum.map(acc, fn
            {^a, ^b, ^existing_cells} -> {a, b, existing_cells ++ [cell]}
            other -> other
          end)
          |> case do
            updated ->
              # Remove old and add updated
              Enum.filter(acc, fn {ga, gb, _c} -> ga != a or gb != b end) ++
                [{a, b, existing_cells ++ [cell]}]
          end
      end
    end)

    %{topology | edges: edges}
  end

  @doc "Get the prime for a group."
  @spec group_prime(t(), atom()) :: integer()
  def group_prime(%__MODULE__{groups: groups}, name) do
    Map.fetch!(groups, name).prime
  end

  @doc "Get all groups this cell participates in."
  @spec cell_groups(t(), atom()) :: [atom()]
  def cell_groups(%__MODULE__{cells: cells}, cell_id) do
    Map.fetch!(cells, cell_id)
  end

  @doc "List all cell IDs in the topology."
  @spec all_cells(t()) :: [atom()]
  def all_cells(%__MODULE__{cells: cells}), do: Map.keys(cells)

  @doc "List all group names."
  @spec all_groups(t()) :: [atom()]
  def all_groups(%__MODULE__{groups: groups}), do: Map.keys(groups)

  @doc "Get all edges (group pairs with shared cells)."
  @spec all_edges(t()) :: [{atom(), atom(), [atom()]}]
  def all_edges(%__MODULE__{edges: edges}), do: edges

  @doc """
  Compile a problem description into topology + initial assignments.

  Takes a keyword list of cell→value assignments and returns:
  {topology, assignments_map}
  """
  @spec compile_problem([{atom(), atom(), non_neg_integer()}]) :: {t(), %{atom() => integer()}}
  def compile_problem(declarations) do
    topology = new()

    # First pass: collect all groups and auto-assign primes
    groups = Enum.map(declarations, fn {cell, group, _val} -> group end) |> Enum.uniq()
    topology = Enum.reduce(groups, topology, &add_group(&2, &1))

    # Second pass: add cells and their group memberships
    cell_groups = Enum.group_by(declarations, fn {cell, _group, _val} -> cell end)
    topology =
      Enum.reduce(cell_groups, topology, fn {cell, entries}, topo ->
        groups_for_cell = Enum.map(entries, fn {_cell, group, _val} -> group end)
        add_cell(topo, cell, groups_for_cell)
      end)

    # Third pass: build initial assignments
    assignments =
      Enum.into(declarations, %{}, fn {cell, group, value} ->
        {{cell, group}, value}
      end)

    {topology, assignments}
  end
end