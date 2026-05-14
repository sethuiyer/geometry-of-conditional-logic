%% @doc scheduler_topology - The overlap-graph coordinator for CRT-based
%% scheduling.
%%
%% This module owns the GLOBAL CRT coordinate z and orchestrates LOCAL
%% repairs across constraint-group actors. It implements the key insight:
%%
%%   Preemption is a CRT jump, not a restart.
%%
%% Architecture:
%%   - One crt_group actor per constraint domain (core, cache, NUMA, deadline, etc.)
%%   - This module is the coordinator that:
%%     1. Computes M (cache-affinity shield) = product of locked group primes
%%     2. Computes global CRT jumps using Garner's algorithm
%%     3. Dispatches local transitions to groups
%%     4. Maintains the transition log (immutable event stream)
%%
%% The "geometric ELSE branch":
%%   IF position is locked → residue preserved, prime enters M
%%   ELSE → CRT jump z' = z + kM finds exact new placement
%%          displacing only what must move

-module(scheduler_topology).

-export([
    start/0,
    start/1,
    add_group/3,
    lock_group/2,
    add_process/4,
    preempt/2,
    local_repair/3,
    get_schedule/1,
    get_global_z/1,
    transition_log/1
]).

%% ============================================================================
%% Internal records
%% ============================================================================

-record(group_ref, {
    name  :: atom(),
    pid   :: pid(),
    prime :: pos_integer()
}).

-record(proc_assign, {
    proc_id  :: term(),
    group    :: atom(),
    position :: non_neg_integer()
}).

-record(tlog_entry, {
    id             :: non_neg_integer(),
    proc_id        :: term(),
    old_group      :: atom(),
    new_group      :: atom(),
    old_residue    :: integer() | undefined,
    new_residue    :: integer(),
    delta_z        :: integer(),
    preserved      :: [atom()],
    checkpoint     :: z_value()
}).

-record(topology, {
    groups       = #{}            :: #{atom() => #group_ref{}},
    assigns      = #{}            :: #{term() => #proc_assign{}},
    locked_groups = sets:new()    :: sets:set(atom()),
    z            = 0              :: integer(),
    tlog         = []             :: [#tlog_entry{}],
    next_tid     = 1              :: non_neg_integer()
}).

-opaque topology() :: #topology{}.

%% ============================================================================
%% API
%% ============================================================================

%% @doc Create an empty topology.
-spec start() -> topology().
start() -> #topology{}.

%% @doc Create a topology with predefined constraint groups.
%% Each group is {Name, Prime}. Example:
%%   start([{core0, 7}, {core1, 11}, {numa0, 13}, {deadline, 17}])
-spec start([{atom(), pos_integer()}]) -> topology().
start(GroupDefs) ->
    lists:foldl(
        fun({Name, Prime}, T) -> add_group(T, Name, Prime) end,
        start(),
        GroupDefs
    ).

%% @doc Add a constraint group (spawns a crt_group actor).
-spec add_group(topology(), atom(), pos_integer()) -> topology().
add_group(Topology, Name, Prime) ->
    {ok, Pid} = crt_group:start_link(Name, Prime),
    Groups = maps:put(Name, #group_ref{name = Name, pid = Pid, prime = Prime},
                      Topology#topology.groups),
    Topology#topology{groups = Groups}.

%% @doc Lock an entire group — all its residues become immutable.
%% The group's prime enters the cache-affinity shield M.
-spec lock_group(topology(), atom()) -> topology().
lock_group(Topology, GroupName) ->
    Locked = sets:add_element(GroupName, Topology#topology.locked_groups),
    Topology#topology{locked_groups = Locked}.

%% @doc Assign a process to a group at a given position.
%% Returns {ok, NewZ} or {error, Reason}.
-spec add_process(topology(), term(), atom(), non_neg_integer()) ->
    {ok, integer()} | {error, term()}.
add_process(Topology, ProcId, GroupName, Position) ->
    case maps:get(GroupName, Topology#topology.groups, undefined) of
        undefined ->
            {error, unknown_group};
        #group_ref{pid = GroupPid} ->
            case crt_group:transition(GroupPid, Position, ProcId) of
                {ok, {_Old, NewRes}} ->
                    Z = Topology#topology.z,
                    Prime = (maps:get(GroupName, Topology#topology.groups))#group_ref.prime,
                    NewZ = Z * Prime + NewRes,
                    Assigns = maps:put(ProcId, #proc_assign{
                        proc_id  = ProcId,
                        group    = GroupName,
                        position = Position
                    }, Topology#topology.assigns),
                    {ok, Topology#topology{z = NewZ, assigns = Assigns}};
                Error ->
                    Error
            end
    end.

%% @doc Preempt a process: the "geometric ELSE branch."
%% Identifies affected groups, computes the cache-affinity shield,
%% and performs a minimal local CRT-repair jump.
-spec preempt(topology(), term()) ->
    {ok, topology(), integer()} | {error, term()}.
preempt(Topology, ProcId) ->
    case maps:get(ProcId, Topology#topology.assigns, undefined) of
        undefined ->
            {error, unknown_process};
        #proc_assign{group = OldGroup, position = OldPos} ->
            #group_ref{pid = OldPid, prime = OldPrime} =
                maps:get(OldGroup, Topology#topology.groups),

            %% Step 1: get the old residue from the group
            OldResidue = crt_group:get_residue(OldPid, OldPos),

            %% Step 2: compute M — product of ALL locked group primes
            %% This is the cache-affinity shield
            M = compute_locked_product(Topology),

            %% Step 3: find an available position in the same or target group
            NewPos = find_available_slot(Topology, OldGroup),

            %% Step 4: get the target residue
            TargetResidue = NewPos,

            %% Step 5: compute global CRT jump
            NewZ = crt_jump(Topology#topology.z, TargetResidue, OldPrime, M),

            %% Step 6: perform the local transition in the group
            case crt_group:transition(OldPid, NewPos, ProcId) of
                {ok, {_, NewRes}} ->
                    %% Step 7: log the transition (immutable event)
                    Entry = #tlog_entry{
                        id          = Topology#topology.next_tid,
                        proc_id     = ProcId,
                        old_group   = OldGroup,
                        new_group   = OldGroup,
                        old_residue = OldResidue,
                        new_residue = NewRes,
                        delta_z     = NewZ - Topology#topology.z,
                        preserved   = sets:to_list(Topology#topology.locked_groups),
                        checkpoint  = NewZ
                    },
                    NewAssigns = maps:put(ProcId, #proc_assign{
                        proc_id  = ProcId,
                        group    = OldGroup,
                        position = NewPos
                    }, Topology#topology.assigns),
                    NewTlog = [Entry | Topology#topology.tlog],
                    NewTopology = Topology#topology{
                        assigns  = NewAssigns,
                        z        = NewZ,
                        tlog     = NewTlog,
                        next_tid = Topology#topology.next_tid + 1
                    },
                    {ok, NewTopology, NewZ};
                Error ->
                    Error
            end
    end.

%% @doc Repair a process by moving it to a different group.
%% Cross-group CRT jump that preserves all locked group residues.
-spec local_repair(topology(), term(), atom()) ->
    {ok, topology(), integer()} | {error, term()}.
local_repair(Topology, ProcId, TargetGroup) ->
    case maps:get(ProcId, Topology#topology.assigns, undefined) of
        undefined ->
            {error, unknown_process};
        #proc_assign{group = OldGroup} when OldGroup =:= TargetGroup ->
            {error, same_group};
        #proc_assign{group = OldGroup, position = _OldPos} ->
            #group_ref{prime = OldPrime} =
                maps:get(OldGroup, Topology#topology.groups),
            #group_ref{pid = TargetPid, prime = TargetPrime} =
                maps:get(TargetGroup, Topology#topology.groups),

            %% Compute M from locked groups excluding BOTH old and target
            M = compute_locked_product_excluding(Topology, OldGroup, TargetGroup),

            %% Find available slot in target group
            NewPos = find_available_slot(Topology, TargetGroup),
            TargetResidue = NewPos,

            %% Global CRT jump: z' = z + k * M
            %% This preserves all locked group residues
            NewZ = crt_jump(Topology#topology.z, TargetResidue, TargetPrime, M),

            %% Perform local transitions in both groups
            OldState = crt_group:get_state(
                maps:get(OldGroup, Topology#topology.groups)#group_ref.pid
            ),
            OldResidue = maps:get(_OldPos, OldState#state.residues, undefined),

            case crt_group:transition(TargetPid, NewPos, ProcId) of
                {ok, {_, NewRes}} ->
                    Entry = #tlog_entry{
                        id          = Topology#topology.next_tid,
                        proc_id     = ProcId,
                        old_group   = OldGroup,
                        new_group   = TargetGroup,
                        old_residue = OldResidue,
                        new_residue = NewRes,
                        delta_z     = NewZ - Topology#topology.z,
                        preserved   = sets:to_list(Topology#topology.locked_groups),
                        checkpoint  = NewZ
                    },
                    NewAssigns = maps:put(ProcId, #proc_assign{
                        proc_id  = ProcId,
                        group    = TargetGroup,
                        position = NewPos
                    }, Topology#topology.assigns),
                    NewTlog = [Entry | Topology#topology.tlog],
                    NewTopology = Topology#topology{
                        assigns  = NewAssigns,
                        z        = NewZ,
                        tlog     = NewTlog,
                        next_tid = Topology#topology.next_tid + 1
                    },
                    {ok, NewTopology, NewZ};
                Error ->
                    Error
            end
    end.

%% @doc Return a snapshot of the current schedule across all groups.
-spec get_schedule(topology()) -> #{atom() => #{non_neg_integer() => term()}}.
get_schedule(Topology) ->
    maps:fold(
        fun(Name, #group_ref{pid = Pid}, Acc ->
            State = crt_group:get_state(Pid),
            maps:put(Name, State#state.residues, Acc)
        end,
        #{},
        Topology#topology.groups
    ).

%% @doc Get the current global CRT coordinate.
-spec get_global_z(topology()) -> integer().
get_global_z(Topology) ->
    Topology#topology.z.

%% @doc Return the transition log (immutable event stream, most recent first).
-spec transition_log(topology()) -> [#tlog_entry{}].
transition_log(Topology) ->
    lists:reverse(Topology#topology.tlog).

%% ============================================================================
%% Internal
%% ============================================================================

%% @doc Product of all locked group primes.
-spec compute_locked_product(topology()) -> pos_integer().
compute_locked_product(Topology) ->
    maps:fold(
        fun(Name, #group_ref{prime = Prime}, Acc ->
            case sets:is_element(Name, Topology#topology.locked_groups) of
                true  -> Acc * Prime;
                false -> Acc
            end
        end,
        1,
        Topology#topology.groups
    ).

%% @doc Product of locked group primes, excluding two named groups.
-spec compute_locked_product_excluding(topology(), atom(), atom()) -> pos_integer().
compute_locked_product_excluding(Topology, Exclude1, Exclude2) ->
    maps:fold(
        fun(Name, #group_ref{prime = Prime}, Acc ->
            case sets:is_element(Name, Topology#topology.locked_groups)
                 andalso Name =/= Exclude1
                 andalso Name =/= Exclude2 of
                true  -> Acc * Prime;
                false -> Acc
            end
        end,
        1,
        Topology#topology.groups
    ).

%% @doc Find the first unoccupied position in a group.
-spec find_available_slot(topology(), atom()) -> non_neg_integer().
find_available_slot(Topology, GroupName) ->
    #group_ref{prime = Prime, pid = GroupPid} =
        maps:get(GroupName, Topology#topology.groups),
    State = crt_group:get_state(GroupPid),
    Occupied = maps:keys(State#state.residues),
    find_slot(0, Prime, Occupied).

-spec find_slot(non_neg_integer(), pos_integer(), [non_neg_integer()]) -> non_neg_integer().
find_slot(N, Limit, Occupied) when N >= Limit ->
    N;
find_slot(N, _Limit, Occupied) ->
    case lists:member(N, Occupied) of
        true  -> find_slot(N + 1, _Limit, Occupied);
        false -> N
    end.

%% ============================================================================
%% CRT Jump — Garner-based exact global coordinate update
%% ============================================================================

%% z' = z + K * M  where K = ((target - z) * M_inv) mod Prime
-spec crt_jump(integer(), residue(), pos_integer(), pos_integer()) -> integer().
crt_jump(CurrentZ, TargetResidue, Prime, M) ->
    Diff = ((TargetResidue - CurrentZ) rem Prime + Prime) rem Prime,
    Inv  = mod_inverse(M rem Prime, Prime),
    K    = (Diff * Inv) rem Prime,
    CurrentZ + K * M.

%% ============================================================================
%% Extended Euclidean Algorithm
%% ============================================================================

-spec mod_inverse(integer(), pos_integer()) -> integer() | no_inverse.
mod_inverse(A, M) ->
    {G, X, _Y} = egcd(A, M),
    case G of
        1 -> ((X rem M) + M) rem M;
        _ -> no_inverse
    end.

-spec egcd(integer(), integer()) -> {integer(), integer(), integer()}.
egcd(A, 0) ->
    {A, 1, 0};
egcd(A, B) ->
    {G, X1, Y1} = egcd(B, A rem B),
    {G, Y1, X1 - (A div B) * Y1}.