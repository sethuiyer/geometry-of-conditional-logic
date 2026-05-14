defmodule ConstraintGroup do
  @moduledoc """
  ConstraintGroup — an Elixir GenServer representing a single constraint domain.

  Each group owns:
    - A prime modulus (its coordinate space)
    - Local residue assignments for cells in its domain
    - An immutable event log (for rollback)
    - A lock set (for warm-cache / committed values)

  This is the Elixir equivalent of the Erlang `crt_group.erl` actor,
  using GenServer semantics with Elixir's cleaner syntax.

  ## Design

  The group is intentionally local. It does NOT know about other groups.
  The RepairCoordinator handles cross-group CRT jumps and Garner's algorithm.
  """

  use GenServer

  @type position :: non_neg_integer()
  @type residue :: non_neg_integer()
  @type t :: %__MODULE__{
          name: atom(),
          prime: pos_integer(),
          residues: %{position() => residue()},
          locked: MapSet.t(),
          history: [hist_entry()],
          z: integer()
        }

  defstruct name: nil,
            prime: 0,
            residues: %{},
            locked: MapSet.new(),
            history: [],
            z: 0

  defrecordp :hist_entry, pos: nil, old: nil, old_z: nil

  # =========================================================================
  # Public API
  # =========================================================================

  @doc "Start a constraint group with name and prime modulus."
  @spec start_link(atom(), pos_integer()) :: GenServer.on_start()
  def start_link(name, prime) when is_atom(name) and is_integer(prime) and prime > 1 do
    GenServer.start_link(__MODULE__, {name, prime}, name: __MODULE__.name(name))
  end

  @doc "Get the process name registry key."
  @spec name(atom()) :: atom()
  def name(group_name), do: :"constraint_group_#{group_name}"

  @doc "Transition a cell to a new value. Returns {old_residue, new_residue}."
  @spec transition(atom(), position(), residue()) ::
          {:ok, {residue() | nil, residue()}} | {:error, :locked_conflict}
  def transition(group_name, pos, value) do
    GenServer.call(name(group_name), {:transition, pos, value})
  end

  @doc "Lock a position — prevents future changes to this cell."
  @spec lock(atom(), position()) :: :ok
  def lock(group_name, pos) do
    GenServer.call(name(group_name), {:lock, pos})
  end

  @doc "Unlock a previously locked position."
  @spec unlock(atom(), position()) :: :ok
  def unlock(group_name, pos) do
    GenServer.call(name(group_name), {:unlock, pos})
  end

  @doc "Roll back the last N transitions."
  @spec rollback(atom(), non_neg_integer()) :: :ok
  def rollback(group_name, count) do
    GenServer.call(name(group_name), {:rollback, count})
  end

  @doc "Get the current residue for a position."
  @spec get_residue(atom(), position()) :: residue() | nil
  def get_residue(group_name, pos) do
    GenServer.call(name(group_name), {:get_residue, pos})
  end

  @doc "Get the full group state (for debugging / checkpointing)."
  @spec dump_state(atom()) :: t()
  def dump_state(group_name) do
    GenServer.call(name(group_name), :dump_state)
  end

  @doc "Restore group state from a checkpoint."
  @spec restore_state(atom(), t()) :: :ok
  def restore_state(group_name, state) do
    GenServer.call(name(group_name), {:restore_state, state})
  end

  @doc "Get the group's prime modulus."
  @spec prime(atom()) :: pos_integer()
  def prime(group_name) do
    GenServer.call(name(group_name), :prime)
  end

  # =========================================================================
  # GenServer Callbacks
  # =========================================================================

  @impl true
  def init({name, prime}) do
    {:ok, %__MODULE__{name: name, prime: prime}}
  end

  @impl true
  def handle_call({:transition, pos, value}, _from, state) do
    locked? = MapSet.member?(state.locked, pos)
    old_val = Map.get(state.residues, pos)

    if locked? and old_val != value do
      {:reply, {:error, :locked_conflict}, state}
    else
      new_res = rem(value, state.prime)
      entry = hist_entry(pos: pos, old: old_val, old_z: state.z)

      new_state = %{state |
        residues: Map.put(state.residues, pos, new_res),
        z: new_res,
        history: [entry | state.history]
      }

      {:reply, {:ok, {old_val, new_res}}, new_state}
    end
  end

  def handle_call({:lock, pos}, _from, state) do
    new_locked = MapSet.put(state.locked, pos)
    {:reply, :ok, %{state | locked: new_locked}}
  end

  def handle_call({:unlock, pos}, _from, state) do
    new_locked = MapSet.delete(state.locked, pos)
    {:reply, :ok, %{state | locked: new_locked}}
  end

  def handle_call({:rollback, count}, _from, state) do
    {:reply, :ok, rollback_n(count, state)}
  end

  def handle_call({:get_residue, pos}, _from, state) do
    {:reply, Map.get(state.residues, pos), state}
  end

  def handle_call(:dump_state, _from, state) do
    {:reply, state, state}
  end

  def handle_call({:restore_state, snapshot}, _from, _state) do
    {:reply, :ok, snapshot}
  end

  def handle_call(:prime, _from, state) do
    {:reply, state.prime, state}
  end

  @impl true
  def handle_cast(_msg, state), do: {:noreply, state}
  def handle_info(_msg, state), do: {:noreply, state}
  def terminate(_reason, _state), do: :ok
  def code_change(_old, state, _extra), do: {:ok, state}

  # =========================================================================
  # Internal
  # =========================================================================

  defp rollback_n(0, state), do: state
  defp rollback_n(_, %{history: []} = state), do: state

  defp rollback_n(n, %{
    history: [entry | rest],
    residues: residues,
    locked: locked
  } = state) do
    residues = case entry.old do
      nil -> Map.delete(residues, entry.pos)
      v   -> Map.put(residues, entry.pos, v)
    end

    locked = case entry.old do
      nil -> MapSet.delete(locked, entry.pos)
      _   -> locked
    end

    rollback_n(n - 1, %{state |
      residues: residues,
      locked: locked,
      z: entry.old_z,
      history: rest
    })
  end
end