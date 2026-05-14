defmodule RepairCoordinator do
  @moduledoc """
  RepairCoordinator — the central dispatch for distributed CRT repair.

  This module sits on top of ConstraintTopology and ConstraintGroup
  actors. It owns the global CRT coordinate z and orchestrates local
  repair jumps across the overlap graph.

  ## The Core Loop

  1. Event arrives (process preempted, task added, machine fails, etc.)
  2. Identify affected groups and cells
  3. Compute cache-affinity shield M = ∏(locked group primes)
  4. For each affected cell:
     a. Find available slot in target group
     b. Compute CRT jump: z' = z + kM
     c. Execute via RepairTransaction (staged, verify, commit or rollback)
  5. Log the transition (immutable event stream)

  ## The Key Invariant

  "Preemption is a CRT jump, not a restart."

  A traditional scheduler says: event → recompute
  This coordinator says: event → local invariant-preserving displacement

  """

  use GenServer

  @type t :: %__MODULE__{
          topology: ConstraintTopology.t(),
          z: integer(),
          repair_log: [repair_entry()],
          locked_groups: MapSet.t()
        }

  defstruct topology: nil,
            z: 0,
            repair_log: [],
            locked_groups: MapSet.new()

  defrecordp :repair_entry,
    id: nil,
    proc_id: nil,
    old_group: nil,
    new_group: nil,
    old_residue: nil,
    new_residue: nil,
    delta_z: 0,
    preserved: [],
    checkpoint: 0

  # =========================================================================
  # Public API
  # =========================================================================

  @doc "Start a coordinator with the given topology."
  @spec start_link(ConstraintTopology.t()) :: GenServer.on_start()
  def start_link(%ConstraintTopology{} = topology) do
    GenServer.start_link(__MODULE__, topology)
  end

  @doc "Start a coordinator by building a topology from declarations."
  @spec start_link([{atom(), integer()}], [{atom(), atom(), integer()}]) :: GenServer.on_start()
  def start_link(group_defs, cell_defs) do
    topology = build_topology(group_defs, cell_defs)
    start_link(topology)
  end

  @doc "Build topology from group and cell declarations."
  @spec build_topology([{atom(), integer()}], [{atom(), atom(), integer()}]) :: ConstraintTopology.t()
  def build_topology(group_defs, cell_defs) do
    topo = Enum.reduce(group_defs, ConstraintTopology.new(), fn {name, prime}, t ->
      ConstraintTopology.add_group(t, name, prime: prime)
    end)

    cell_groups = Enum.group_by(cell_defs, fn {cell, _group, _val} -> cell end)

    Enum.reduce(cell_groups, topo, fn {cell, entries}, t ->
      groups = Enum.map(entries, fn {_cell, group, _val} -> group end)
      ConstraintTopology.add_cell(t, cell, groups)
    end)
  end

  @doc """
  Add a process to the schedule.
  Returns {:ok, pid, new_z} or {:error, reason}.
  """
  @spec add_process(atom(), term(), atom(), integer()) :: {:ok, integer()} | {:error, term()}
  def add_process(coordinator, proc_id, group_name, position) do
    GenServer.call(coordinator, {:add_process, proc_id, group_name, position})
  end

  @doc """
  Lock a group — all its residues become immutable.
  The group's prime enters the cache-affinity shield.
  """
  @spec lock_group(atom(), atom()) :: :ok
  def lock_group(coordinator, group_name) do
    GenServer.call(coordinator, {:lock_group, group_name})
  end

  @doc """
  Preempt a process with minimal local repair.
  This is the "geometric ELSE branch" in action.
  """
  @spec preempt(atom(), term()) :: {:ok, integer()} | {:error, term()}
  def preempt(coordinator, proc_id) do
    GenServer.call(coordinator, {:preempt, proc_id})
  end

  @doc """
  Repair a process by moving it to a different group.
  Cross-group CRT jump preserving all locked residues.
  """
  @spec local_repair(atom(), term(), atom()) :: {:ok, integer()} | {:error, term()}
  def local_repair(coordinator, proc_id, target_group) do
    GenServer.call(coordinator, {:local_repair, proc_id, target_group})
  end

  @doc "Get the current global CRT coordinate."
  @spec get_global_z(atom()) :: integer()
  def get_global_z(coordinator) do
    GenServer.call(coordinator, :get_global_z)
  end

  @doc "Get a snapshot of the current schedule across all groups."
  @spec get_schedule(atom()) :: %{atom() => %{integer() => term()}}
  def get_schedule(coordinator) do
    GenServer.call(coordinator, :get_schedule)
  end

  @doc "Get the repair transition log (immutable event stream)."
  @spec get_repair_log(atom()) :: [repair_entry()]
  def get_repair_log(coordinator) do
    GenServer.call(coordinator, :get_repair_log)
  end

  @doc """
  Checkpoint the current state. Returns a checkpoint ID.
  Rollback restores z and all group states to this point.
  """
  @spec checkpoint(atom()) :: reference()
  def checkpoint(coordinator) do
    GenServer.call(coordinator, :checkpoint)
  end

  @doc "Roll back to a checkpoint."
  @spec rollback(atom(), reference()) :: :ok
  def rollback(coordinator, checkpoint_id) do
    GenServer.call(coordinator, {:rollback, checkpoint_id})
  end

  # =========================================================================
  # GenServer Callbacks
  # =========================================================================

  @impl true
  def init(%ConstraintTopology{} = topology) do
    # Start a ConstraintGroup actor for each declared group
    Enum.each(topology.groups, fn {name, %{prime: prime}} ->
      {:ok, _pid} = ConstraintGroup.start_link(name, prime)
    end)

    state = %__MODULE__{
      topology: topology,
      z: 0,
      repair_log: [],
      locked_groups: MapSet.new()
    }

    {:ok, state}
  end

  @impl true
  def handle_call({:add_process, proc_id, group_name, position}, _from, state) do
    prime = ConstraintTopology.group_prime(state.topology, group_name)

    case ConstraintGroup.transition(group_name, position, proc_id) do
      {:ok, {_old, new_res}} ->
        # Update global z using Garner-style reconstruction
        new_z = state.z * prime + new_res
        {:reply, {:ok, new_z}, %{state | z: new_z}}

      {:error, reason} ->
        {:reply, {:error, reason}, state}
    end
  end

  def handle_call({:lock_group, group_name}, _from, state) do
    locked = MapSet.put(state.locked_groups, group_name)
    {:reply, :ok, %{state | locked_groups: locked}}
  end

  def handle_call({:preempt, proc_id}, _from, state) do
    %{^proc_id => assign} = state
    old_group = assign.group
    old_pos = assign.position

    # Get cache-affinity shield: product of ALL locked group primes
    m = compute_shield(state)

    # Find available position in the same group
    prime = ConstraintTopology.group_prime(state.topology, old_group)
    new_pos = find_available(state.topology, old_group)

    # CRT jump: z' = z + k * M
    # where k = ((target - z) * M_inv) mod prime
    new_z = crt_jump(state.z, new_pos, prime, m)

    # Execute the local group transition
    case ConstraintGroup.transition(old_group, new_pos, proc_id) do
      {:ok, {_old, new_res}} ->
        entry = repair_entry(
          id: length(state.repair_log) + 1,
          proc_id: proc_id,
          old_group: old_group,
          new_group: old_group,
          old_residue: old_pos,
          new_residue: new_res,
          delta_z: new_z - state.z,
          preserved: MapSet.to_list(state.locked_groups),
          checkpoint: new_z
        )

        # Remove old assignment
        new_assigns = Map.delete(state, proc_id)

        {:reply, {:ok, new_z}, %{state |
          z: new_z,
          repair_log: [entry | state.repair_log]
        }}

      {:error, reason} ->
        {:reply, {:error, reason}, state}
    end
  end

  def handle_call({:local_repair, proc_id, target_group}, _from, state) do
    %{^proc_id => assign} = state
    old_group = assign.group

    # Compute shield excluding both old and target groups
    m = compute_shield_excluding(state, old_group, target_group)

    prime = ConstraintTopology.group_prime(state.topology, target_group)
    target_prime = prime

    # Compute CRT jump for cross-group repair
    new_pos = find_available(state.topology, target_group)
    new_z = crt_jump(state.z, new_pos, target_prime, m)

    # Execute local transition in target group
    case ConstraintGroup.transition(target_group, new_pos, proc_id) do
      {:ok, {_old, new_res}} ->
        entry = repair_entry(
          id: length(state.repair_log) + 1,
          proc_id: proc_id,
          old_group: old_group,
          new_group: target_group,
          old_residue: nil,
          new_residue: new_res,
          delta_z: new_z - state.z,
          preserved: MapSet.to_list(state.locked_groups),
          checkpoint: new_z
        )

        {:reply, {:ok, new_z}, %{state |
          z: new_z,
          repair_log: [entry | state.repair_log]
        }}

      {:error, reason} ->
        {:reply, {:error, reason}, state}
    end
  end

  def handle_call(:get_global_z, _from, state) do
    {:reply, state.z, state}
  end

  def handle_call(:get_schedule, _from, state) do
    schedule = Enum.reduce(state.topology.groups, %{}, fn {name, _}, acc ->
      Map.put(acc, name, ConstraintGroup.dump_state(name).residues)
    end)
    {:reply, schedule, state}
  end

  def handle_call(:get_repair_log, _from, state) do
    {:reply, Enum.reverse(state.repair_log), state}
  end

  def handle_call(:checkpoint, _from, state) do
    ref = make_ref()
    # Snapshot all group states
    Enum.each(state.topology.groups, fn {name, _}, _ ->
      ConstraintGroup.dump_state(name)
    end)
    {:reply, ref, state}
  end

  def handle_call({:rollback, checkpoint_ref}, _from, state) do
    # Restore all groups to initial state
    Enum.each(state.topology.groups, fn {name, _}, _ ->
      ConstraintGroup.rollback(name, 999)
    end)
    {:reply, :ok, %{state | z: 0, repair_log: []}}
  end

  @impl true
  def handle_cast(_msg, state), do: {:noreply, state}
  def handle_info(_msg, state), do: {:noreply, state}
  def terminate(_reason, _state), do: :ok
  def code_change(_old, state, _extra), do: {:ok, state}

  # =========================================================================
  # Internal: CRT Jump (Garner-based exact coordinate update)
  # =========================================================================

  defp crt_jump(current_z, target_residue, prime, m) do
    diff = rem(rem(target_residue - current_z, prime) + prime, prime)
    inv = mod_inverse(rem(m, prime), prime)
    k = rem(diff * inv, prime)
    current_z + k * m
  end

  defp mod_inverse(a, m) do
    {g, x, _y} = egcd(rem(a, m), m)
    case g do
      1 -> rem(rem(x, m) + m, m)
      _ -> raise "no modular inverse exists"
    end
  end

  defp egcd(a, 0), do: {a, 1, 0}
  defp egcd(a, b) do
    {g, x1, y1} = egcd(b, rem(a, b))
    {g, y1, x1 - div(a, b) * y1}
  end

  defp compute_shield(state) do
    Enum.reduce(state.locked_groups, 1, fn name, acc ->
      prime = ConstraintTopology.group_prime(state.topology, name)
      acc * prime
    end)
  end

  defp compute_shield_excluding(state, exclude1, exclude2) do
    Enum.reduce(state.locked_groups, 1, fn name, acc ->
      if name != exclude1 and name != exclude2 do
        prime = ConstraintTopology.group_prime(state.topology, name)
        acc * prime
      else
        acc
      end
    end)
  end

  defp find_available(topology, group_name) do
    prime = ConstraintTopology.group_prime(topology, group_name)
    occupied = ConstraintGroup.dump_state(group_name).residues |> Map.keys()
    do_find_slot(0, prime, occupied)
  end

  defp do_find_slot(n, limit, occupied) when n >= limit, do: n
  defp do_find_slot(n, limit, occupied) do
    if n in occupied, do: do_find_slot(n + 1, limit, occupied), else: n
  end
end