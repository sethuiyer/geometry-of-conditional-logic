%% @doc crt_group - A lightweight Erlang gen_server representing one
%% constraint group (one prime modulus) in the distributed CRT scheduler.
%%
%% Each group manages local residues for positions assigned to its domain.
%% It enforces locking and reports deltas to the topology coordinator,
%% which owns the global CRT coordinate z and computes cross-group jumps.
%%
%% Design: the group knows ONLY its own prime. The topology coordinator
%% computes inter-group CRT jumps using Garner's algorithm, since only
%% the coordinator sees all primes simultaneously.

-module(crt_group).
-behaviour(gen_server).

%% ------------------------------------------------------------------
%% API
%% ------------------------------------------------------------------
-export([
    start_link/2,
    transition/3,
    rollback/2,
    lock/2,
    unlock/2,
    get_state/1,
    get_prime/1,
    get_residue/2
]).

%% ------------------------------------------------------------------
%% gen_server callbacks
%% ------------------------------------------------------------------
-export([
    init/1,
    handle_call/3,
    handle_cast/2,
    handle_info/2,
    terminate/2,
    code_change/3
]).

%% ------------------------------------------------------------------
%% Types
%% ------------------------------------------------------------------
-type position()  :: non_neg_integer().
-type residue()   :: non_neg_integer().
-type z_value()   :: integer().

-record(hist_entry, {
    pos   :: position(),
    old   :: residue() | undefined,
    old_z :: z_value()
}).

-record(state, {
    name     :: atom(),
    prime    :: pos_integer(),
    residues = #{}              :: #{position() => residue()},
    locked   = sets:new()       :: sets:set(position()),
    history  = []               :: [#hist_entry{}],
    z        = 0                :: z_value()
}).

-opaque state() :: #state{}.

%% ============================================================================
%% API
%% ============================================================================

%% @doc Start a constraint group with Name and prime modulus Prime.
-spec start_link(atom(), pos_integer()) -> {ok, pid()} | {error, term()}.
start_link(Name, Prime) when is_atom(Name), is_integer(Prime), Prime > 1 ->
    gen_server:start_link(?MODULE, {Name, Prime}, []).

%% @doc Request a position→value transition in this group.
%% Returns {ok, {OldResidue, NewResidue}} so the coordinator can
%% compute the global CRT jump.  Returns {error, locked_conflict} if
%% the position is locked to a different value.
-spec transition(pid(), position(), residue()) ->
    {ok, {residue() | undefined, residue()}} | {error, locked_conflict}.
transition(Pid, Pos, Value) ->
    gen_server:call(Pid, {transition, Pos, Value}).

%% @doc Roll back the last N transitions (immutable event stream).
-spec rollback(pid(), non_neg_integer()) -> ok.
rollback(Pid, Count) ->
    gen_server:call(Pid, {rollback, Count}).

%% @doc Lock a specific position so it cannot be overwritten.
-spec lock(pid(), position()) -> ok.
lock(Pid, Pos) ->
    gen_server:call(Pid, {lock, Pos}).

%% @doc Unlock a specific position.
-spec unlock(pid(), position()) -> ok.
unlock(Pid, Pos) ->
    gen_server:call(Pid, {unlock, Pos}).

%% @doc Get the full internal state (for debugging/introspection).
-spec get_state(pid()) -> state().
get_state(Pid) ->
    gen_server:call(Pid, get_state).

%% @doc Get this group's prime modulus.
-spec get_prime(pid()) -> pos_integer().
get_prime(Pid) ->
    gen_server:call(Pid, get_prime).

%% @doc Get the current residue for a position.
-spec get_residue(pid(), position()) -> residue() | undefined.
get_residue(Pid, Pos) ->
    gen_server:call(Pid, {get_residue, Pos}).

%% ============================================================================
%% gen_server callbacks
%% ============================================================================

init({Name, Prime}) ->
    {ok, #state{name = Name, prime = Prime}}.

handle_call(get_state, _From, State) ->
    {reply, State, State};

handle_call(get_prime, _From, State) ->
    {reply, State#state.prime, State};

handle_call({get_residue, Pos}, _From, State) ->
    Res = maps:get(Pos, State#state.residues, undefined),
    {reply, Res, State};

handle_call({transition, Pos, Value}, _From, State) ->
    handle_transition(Pos, Value, State);

handle_call({rollback, Count}, _From, State) ->
    NewState = rollback_n(Count, State),
    {reply, ok, NewState};

handle_call({lock, Pos}, _From, State) ->
    NewLocked = sets:add_element(Pos, State#state.locked),
    {reply, ok, State#state{locked = NewLocked}};

handle_call({unlock, Pos}, _From, State) ->
    NewLocked = sets:del_element(Pos, State#state.locked),
    {reply, ok, State#state{locked = NewLocked}}.

handle_cast(_Msg, State) ->
    {noreply, State}.

handle_info(_Msg, State) ->
    {noreply, State}.

terminate(_Reason, _State) ->
    ok.

code_change(_OldVsn, State, _Extra) ->
    {ok, State}.

%% ============================================================================
%% Internal: Transition
%% ============================================================================

handle_transition(Pos, Value, State) ->
    Residues = State#state.residues,
    Locked   = State#state.locked,
    Prime    = State#state.prime,

    OldValue = maps:get(Pos, Residues, undefined),

    %% Enforce lock constraint
    case sets:is_element(Pos, Locked) andalso OldValue =/= Value of
        true ->
            {reply, {error, locked_conflict}, State};
        false ->
            NewResidue = Value rem Prime,
            HistEntry = #hist_entry{
                pos   = Pos,
                old   = OldValue,
                old_z = State#state.z
            },
            NewState = State#state{
                residues = maps:put(Pos, NewResidue, Residues),
                z        = NewResidue,
                history  = [HistEntry | State#state.history]
            },
            %% Return the delta so the coordinator can compute global jump
            {reply, {ok, {OldValue, NewResidue}}, NewState}
    end.

%% ============================================================================
%% Internal: Rollback (immutable history → O(N) undo)
%% ============================================================================

rollback_n(0, State) ->
    State;
rollback_n(_, #state{history = []} = State) ->
    State;
rollback_n(N, #state{
    history   = [#hist_entry{pos = Pos, old = OldVal, old_z = OldZ} | Rest],
    residues  = Residues,
    locked    = Locked
} = State) ->
    NewResidues = case OldVal of
        undefined -> maps:remove(Pos, Residues);
        _         -> maps:put(Pos, OldVal, Residues)
    end,
    NewLocked = case OldVal of
        undefined -> sets:del_element(Pos, Locked);
        _         -> Locked
    end,
    rollback_n(N - 1, State#state{
        residues = NewResidues,
        locked   = NewLocked,
        z        = OldZ,
        history  = Rest
    }).

%% ============================================================================
%% CRT Jump (pure function — for coordinator use)
%% ============================================================================

%% @doc Exact CRT jump: z' = z + K * M
%% where K satisfies (z + K*M) ≡ TargetResidue (mod Prime).
%% M is precomputed by the coordinator as the product of all locked
%% group primes EXCEPT this group's prime.
-spec crt_jump(z_value(), residue(), pos_integer(), pos_integer()) -> z_value().
crt_jump(CurrentZ, TargetResidue, Prime, M) ->
    Diff = ((TargetResidue - CurrentZ) rem Prime + Prime) rem Prime,
    Inv  = mod_inverse(M rem Prime, Prime),
    K    = (Diff * Inv) rem Prime,
    CurrentZ + K * M.

%% ============================================================================
%% Extended Euclidean Algorithm (for modular inverse)
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