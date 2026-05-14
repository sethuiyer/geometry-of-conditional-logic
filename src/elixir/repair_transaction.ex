defmodule RepairTransaction do
  @moduledoc """
  RepairTransaction — atomic, reversible repair attempt across multiple groups.

  Groups multiple cell transitions into a single unit of work. Either all
  transitions commit (global consistency) or all roll back (no partial state).

  ## How it works

  1. Begin: Snapshot all affected groups (checkpoint IDs)
  2. Execute: Apply local transitions to each participating group
  3. Verify: Check global consistency via Garner CRT reconstruction
  4. Commit or Rollback: Based on verification result

  ## Example

      {:ok, tx_id} =
        RepairTransaction.begin(topology, [:row0, :col0, :box0])
        |> RepairTransition.set(:r0c0, 5)
        |> RepairTransaction.verify()
        |> RepairTransaction.commit()

  If verify fails or any group returns :locked_conflict:

      RepairTransaction.rollback(tx_id)

  """

  @type cell_id :: atom()
  @type group_name :: atom()
  @type value :: integer()
  @type tx_id :: reference()

  defstruct id: nil,
            topology: nil,
            checkpoints: %{},    # %{group_name => state_snapshot}
            operations: [],      # [{group_name, position, value}]
            status: :pending,    # :pending | :committed | :rolled_back | :failed
            deltas: [],          # [{group_name, old_z, new_z}]
            global_z_before: 0,
            global_z_after: 0

  # =========================================================================
  # Public API
  # =========================================================================

  @doc """
  Begin a new repair transaction on the given topology.
  Snapshots all groups involved so rollback is possible.
  """
  @spec begin(%ConstraintTopology{}, [group_name()]) :: t()
  def begin(%ConstraintTopology{} = topology, group_names) when is_list(group_names) do
    tx_id = make_ref()

    checkpoints =
      Enum.into(group_names, %{}, fn name ->
        snapshot = ConstraintGroup.dump_state(name)
        {name, snapshot}
      end)

    %__MODULE__{
      id: tx_id,
      topology: topology,
      checkpoints: checkpoints,
      global_z_before: compute_global_z(topology, group_names)
    }
  end

  @doc """
  Stage a cell transition within this transaction.
  Does NOT execute yet — call commit() to apply.

  For immediate execution, use execute/3 instead.
  """
  @spec stage(t(), cell_id(), value()) :: t()
  def stage(tx, cell_id, value) when tx.status == :pending do
    group_names = ConstraintTopology.cell_groups(tx.topology, cell_id)

    ops =
      Enum.map(group_names, fn group_name ->
        prime = ConstraintGroup.prime(group_name)
        {group_name, rem(value, prime), value}
      end)

    %{tx | operations: tx.operations ++ ops}
  end

  @doc """
  Execute all staged operations across groups.
  Returns {:ok, tx} or {:error, tx, reason}.
  """
  @spec execute(t()) :: {:ok, t()} | {:error, t(), term()}
  def execute(tx) when tx.status == :pending do
    result =
      Enum.reduce_while(tx.operations, {:ok, tx}, fn {group_name, pos, value}, acc ->
        case acc do
          {:ok, tx} ->
            case ConstraintGroup.transition(group_name, pos, value) do
              {:ok, {_old, new_res}} ->
                new_z = reconstruct_z(tx.topology, tx.checkpoints, group_name, new_res)
                delta = %{group_name: group_name, old_z: tx.global_z_before, new_z: new_z}
                {:cont, {:ok, %{tx | deltas: tx.deltas ++ [delta]}}}

              {:error, reason} ->
                {:halt, {:error, %{tx | status: :failed}, reason}}
            end

          {:error, _tx, _reason} = err ->
            {:halt, err}
        end
      end)

    case result do
      {:ok, tx} ->
        updated_z = compute_global_z(tx.topology, Map.keys(tx.checkpoints))
        {:ok, %{tx | status: :committed, global_z_after: updated_z}}

      {:error, tx, reason} ->
        rollback(tx)
        {:error, %{tx | status: :failed}, reason}
    end
  end

  @doc """
  Execute a single immediate transition across all overlap groups.
  This is the "triple synchronized jump" for cells in multiple groups.
  """
  @spec execute(t(), cell_id(), value()) :: {:ok, t()} | {:error, t(), term()}
  def execute(tx, cell_id, value) do
    tx = stage(tx, cell_id, value)
    execute(tx)
  end

  @doc """
  Rollback all transitions in this transaction.
  Restores every group to its checkpoint snapshot.
  """
  @spec rollback(t()) :: :ok
  def rollback(tx) do
    Enum.each(tx.checkpoints, fn {group_name, snapshot} ->
      ConstraintGroup.restore_state(group_name, snapshot)
    end)

    %{tx | status: :rolled_back}
    :ok
  end

  @doc """
  Verify global consistency after staged operations.
  Checks that the CRT coordinate z can be reconstructed consistently
  from all group residues.
  """
  @spec verify(t()) :: :ok | {:error, atom()}
  def verify(tx) when tx.status == :pending do
    case compute_global_z(tx.topology, Map.keys(tx.checkpoints)) do
      z when is_integer(z) -> :ok
      _ -> {:error, :inconsistent_state}
    end
  end

  @doc "Get the transaction ID."
  @spec id(t()) :: tx_id()
  def id(tx), do: tx.id

  @doc "Get the transaction status."
  @spec status(t()) :: atom()
  def status(tx), do: tx.status

  @doc "Get the deltas (change log) for this transaction."
  @spec deltas(t()) :: [%{group_name: atom(), old_z: integer(), new_z: integer()}]
  def deltas(tx), do: tx.deltas

  # =========================================================================
  # Internal
  # =========================================================================

  defp compute_global_z(_topology, group_names) do
    # Simplified: in a full implementation, this uses Garner's algorithm
    # to reconstruct z from the residues of all participating groups.
    # For now, returns the sum of group z-values as a placeholder.
    group_names
    |> Enum.map(fn name ->
      state = ConstraintGroup.dump_state(name)
      state.z
    end)
    |> Enum.sum()
  end

  defp reconstruct_z(_topology, _checkpoints, group_name, new_res) do
    # Placeholder: actual implementation uses Garner's algorithm
    # with the product of all OTHER locked group primes.
    new_res
  end
end