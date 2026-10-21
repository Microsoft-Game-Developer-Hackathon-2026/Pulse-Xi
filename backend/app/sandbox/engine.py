"""Pure bounded transitions. No I/O, global RNG, wall clock, or session registry."""
import hashlib
import json
from pathlib import Path
from datetime import datetime, timedelta, timezone

from pydantic import BaseModel, ValidationError

from .models import (ActorState, Command, EngineEvent, EngineState, Intervention, PendingAction,
                     RngState, Scenario, ScenarioConfig, Snapshot, STREAMS, Tactics, ENGINE_VERSION)


class EngineError(Exception):
    def __init__(self, code: str, status: int = 409):
        self.code, self.status = code, status
        super().__init__(code)


def canonical(value) -> str:
    def encode(item):
        if isinstance(item, BaseModel):
            return item.model_dump(mode='json')
        raise TypeError('canonical serialization requires JSON values or versioned models')
    return json.dumps(value, default=encode, sort_keys=True, separators=(',', ':'), ensure_ascii=True, allow_nan=False)


def digest(value) -> str:
    return hashlib.sha256(canonical(value).encode('ascii')).hexdigest()


def implementation_hash() -> str:
    """Hash source with universal newlines, independent of checkout line endings."""
    root = Path(__file__).parent
    return digest({name: (root / name).read_text(encoding='utf-8')
                   for name in ('models.py', 'engine.py', 'manifest.py')})


def parse_json(data: str | bytes):
    """Unambiguous JSON at offline verification boundaries."""
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError('duplicate JSON object key')
            result[key] = value
        return result

    def invalid(value):
        raise ValueError('nonfinite JSON value')
    return json.loads(data, object_pairs_hook=unique, parse_constant=invalid)


def build_scenario(config: ScenarioConfig) -> Scenario:
    config = ScenarioConfig.model_validate(config.model_dump())
    hashed = digest(config)
    return Scenario(scenario_id=f'scenario-{hashed}', config_hash=hashed, config=config)


def presets() -> dict[str, ScenarioConfig]:
    result = {}
    for name in ('balanced', 'high-press', 'late-comeback', 'stalemate'):
        config = ScenarioConfig(preset=name)
        if name == 'high-press':
            config.home.tactics = Tactics(pressing=90, tempo=80, risk=65)
        elif name == 'late-comeback':
            # An aggressive strategy preset, never a pre-scripted score.
            config.home.tactics = Tactics(formation='3-5-2', directness=85, risk=90, tempo=90)
        elif name == 'stalemate':
            config.home.tactics = Tactics(compactness=90, tempo=20, risk=10)
            config.away.tactics = config.home.tactics.model_copy(deep=True)
        result[name] = config
    return result


def roles(formation: str) -> list[str]:
    defenders, midfielders, forwards = map(int, formation.split('-'))
    return ['GK'] + ['DF'] * defenders + ['MF'] * midfielders + ['FW'] * forwards


def initial_state(scenario: Scenario) -> EngineState:
    config = scenario.config
    state = EngineState(
        scenario=scenario.model_copy(deep=True), tick=0, revision=0, period=1, lifecycle='paused',
        score={config.home.team_id: 0, config.away.team_id: 0},
        possession_team_id=config.home.team_id, possession_actor_id=config.home.players[-1].player_id,
        possession_id=1, ball_x=50, ball_y=50,
        actors=[ActorState(player_id=p.player_id, team_id=t.team_id, role=r, stamina=10000, last_action_tick=0)
                for t in (config.home, config.away) for p, r in zip(t.players, roles(t.tactics.formation))],
        tactics={t.team_id: t.tactics.model_copy(deep=True) for t in (config.home, config.away)},
        policy_revision=0,
        rng={name: RngState(key=hashlib.sha256(f'{ENGINE_VERSION}:{config.seed}:{name}'.encode()).hexdigest(), counter=0)
             for name in STREAMS},
        pending=[], next_queue_order=1, next_decision_tick=1, event_cursor=1,
        events=[EngineEvent(sequence=1, tick=0, period=1, type='kickoff', team_id=config.home.team_id,
                            actor_id=config.home.players[-1].player_id, x=50, y=50, end_x=50, end_y=50,
                            possession_id=1, policy_revision=0)], interventions=[])
    validate_state(state)
    return state


def draw(state: EngineState, stream: str, bound: int = 100) -> int:
    rng = state.rng[stream]
    if rng.counter >= 100000:
        raise EngineError('rng_limit', 429)
    value = int.from_bytes(hashlib.sha256(f'{rng.key}:{rng.counter}'.encode('ascii')).digest(), 'big')
    rng.counter += 1
    # Modulo reduction is specified; these are synthetic policy draws, not cryptographic sampling.
    return value % bound


def emit(state: EngineState, kind: str, team_id=None, actor_id=None, recipient_id=None,
         outcome=None, end_x=None, end_y=None):
    state.event_cursor += 1
    state.events.append(EngineEvent(sequence=state.event_cursor, tick=state.tick, period=state.period,
        type=kind, team_id=team_id, actor_id=actor_id, recipient_id=recipient_id, outcome=outcome,
        x=state.ball_x, y=state.ball_y, end_x=state.ball_x if end_x is None else end_x,
        end_y=state.ball_y if end_y is None else end_y, possession_id=state.possession_id,
        policy_revision=state.policy_revision))


def other(state: EngineState, team_id: str) -> str:
    c = state.scenario.config
    return c.away.team_id if team_id == c.home.team_id else c.home.team_id


def pick_actor(state: EngineState, team_id: str, preferred: str, exclude=None) -> str:
    candidates = [a for a in state.actors if a.team_id == team_id and a.role != 'GK' and a.player_id != exclude]
    weighted = [a.player_id for a in candidates for _ in range(3 if a.role == preferred else 1)]
    return weighted[draw(state, 'actor', len(weighted))]


def take_possession(state: EngineState, team_id: str, actor_id: str):
    state.possession_id += 1
    state.possession_team_id = team_id
    state.possession_actor_id = actor_id


def queue(state: EngineState, kind: str, team_id: str, **kwargs):
    state.pending.append(PendingAction(tick=state.tick + 1, order=state.next_queue_order,
                                       kind=kind, team_id=team_id, **kwargs))
    state.next_queue_order += 1


def restart(state: EngineState, team_id: str):
    take_possession(state, team_id, pick_actor(state, team_id, 'FW'))
    state.ball_x = state.ball_y = 50
    emit(state, 'kickoff', team_id, state.possession_actor_id, outcome='restart')
    state.next_decision_tick = state.tick + 1


def decision(state: EngineState):
    attack, actor_id = state.possession_team_id, state.possession_actor_id
    defend = other(state, attack)
    policy, opposition = state.tactics[attack], state.tactics[defend]
    actor = next(a for a in state.actors if a.player_id == actor_id)
    actor.stamina = max(0, actor.stamina - 2 - policy.tempo // 20)
    actor.last_action_tick = state.tick
    config_team = next(t for t in (state.scenario.config.home, state.scenario.config.away) if t.team_id == attack)
    attributes = next(p for p in config_team.players if p.player_id == actor_id)
    defender = pick_actor(state, defend, 'DF')
    pressure_roll = draw(state, 'duel')
    duel_roll = draw(state, 'duel')
    action_roll = draw(state, 'decision')
    success_roll = draw(state, 'decision')
    direction = 1 if attack == state.scenario.config.home.team_id else -1
    progress = state.ball_x if direction == 1 else 100 - state.ball_x
    state.next_decision_tick = state.tick + 10 - policy.tempo // 15
    if pressure_roll < opposition.pressing:
        defender_state = next(a for a in state.actors if a.player_id == defender)
        defender_state.stamina = max(0, defender_state.stamina - 2 - opposition.pressing // 20)
        defender_state.last_action_tick = state.tick
        defending_team = next(t for t in (state.scenario.config.home, state.scenario.config.away) if t.team_id == defend)
        defending_skill = next(p.defending for p in defending_team.players if p.player_id == defender)
        emit(state, 'pressure', defend, defender, outcome='attempt')
        if duel_roll < 2 + defending_skill // 10 + opposition.compactness // 10 + policy.risk // 8 + (10000 - actor.stamina) // 1000 - (10000 - defender_state.stamina) // 2000:
            emit(state, 'turnover', attack, actor_id, outcome='dispossessed')
            take_possession(state, defend, defender)
            emit(state, 'tackle', defend, defender, outcome='won')
            emit(state, 'recovery', defend, defender, outcome='controlled')
            return
    if progress >= 65 and action_roll < 15 + policy.risk // 3 + (12 if actor.role == 'FW' else 0):
        emit(state, 'shot', attack, actor_id, outcome='on_target')
        if draw(state, 'finish') < 2 + attributes.finishing // 20 + max(0, progress - 80) // 10:
            state.score[attack] += 1
            emit(state, 'goal', attack, actor_id, outcome='scored')
            queue(state, 'restart', defend)
            state.next_decision_tick = state.tick + 2
        else:
            keeper = next(a.player_id for a in state.actors if a.team_id == defend and a.role == 'GK')
            emit(state, 'save', defend, keeper, outcome='held')
            take_possession(state, defend, keeper)
            state.ball_x = 5 if direction == -1 else 95
            emit(state, 'recovery', defend, keeper, outcome='controlled')
        return
    gain = 3 + policy.directness // 10 + (5 if actor.role == 'FW' else 0)
    target_x = max(2, min(98, state.ball_x + direction * gain))
    target_y = 20 + draw(state, 'decision', 61)
    if action_roll < 70 or actor.role == 'GK':
        recipient = pick_actor(state, attack, 'FW' if progress > 55 else 'MF', exclude=actor_id)
        complete = success_roll < min(97, 55 + attributes.passing // 2 - policy.risk // 5 - opposition.compactness // 10)
        emit(state, 'pass', attack, actor_id, recipient, 'complete' if complete else 'incomplete', target_x, target_y)
        state.ball_x, state.ball_y = target_x, target_y
        if complete:
            state.possession_actor_id = recipient
        else:
            emit(state, 'turnover', attack, actor_id, outcome='lost_pass')
            take_possession(state, defend, defender)
            emit(state, 'interception', defend, defender, outcome='won')
            emit(state, 'recovery', defend, defender, outcome='controlled')
    else:
        emit(state, 'carry', attack, actor_id, outcome='complete', end_x=target_x, end_y=target_y)
        state.ball_x, state.ball_y = target_x, target_y


def advance(state: EngineState, ticks: int):
    duration = state.scenario.config.duration_seconds
    for _ in range(ticks):
        if state.tick == duration:
            break
        state.tick += 1
        due = sorted((q for q in state.pending if q.tick == state.tick), key=lambda q: q.order)
        state.pending = [q for q in state.pending if q.tick != state.tick]
        # Scheduled tactics precede restart, period boundary, and decisions at this tick.
        for q in sorted(due, key=lambda q: (q.kind != 'tactic', q.order)):
            if q.kind == 'tactic':
                setattr(state.tactics[q.team_id], q.field, q.value)
                state.policy_revision += 1
                for intervention in state.interventions:
                    if intervention.operation_id == q.operation_id:
                        intervention.result = 'applied'
                for a, role in zip([a for a in state.actors if a.team_id == q.team_id], roles(state.tactics[q.team_id].formation)):
                    a.role = role
            elif state.tick not in (duration // 2, duration):
                restart(state, q.team_id)
        if state.tick == duration:
            emit(state, 'fulltime')
            state.pending = []
            state.lifecycle = 'completed'
            break
        if state.tick == duration // 2:
            emit(state, 'halftime')
            state.period = 2
            restart(state, state.scenario.config.away.team_id)
            continue
        if state.tick >= state.next_decision_tick:
            decision(state)


def apply_command(original: EngineState, command: Command) -> EngineState:
    """Copy-on-write: rejection cannot partially mutate the supplied state."""
    if command.expected_revision != original.revision:
        raise EngineError('stale_revision')
    if original.revision >= 2048:
        raise EngineError('operation_limit', 429)
    state = original.model_copy(deep=True)
    if command.kind != 'checkpoint' and state.lifecycle in ('completed', 'cancelled'):
        raise EngineError('terminal_session')
    if command.kind == 'step':
        if state.lifecycle != 'paused':
            raise EngineError('step_requires_pause')
        advance(state, command.ticks)
    elif command.kind == 'advance':
        if state.lifecycle != 'running':
            raise EngineError('advance_requires_resume')
        advance(state, command.ticks)
    elif command.kind == 'pause':
        state.lifecycle = 'paused'
    elif command.kind == 'resume':
        state.lifecycle = 'running'
    elif command.kind == 'cancel':
        state.lifecycle = 'cancelled'
    elif command.kind == 'trial':
        if state.lifecycle != 'paused' or any(i.operation_id == command.operation_id for i in state.interventions):
            raise EngineError('trial_requires_pause')
        # Explicit, replayable common-random-number blocks for bounded paired
        # trials. The checkpoint itself is untouched; both arms skip equally.
        if any(r.counter + command.trial_index * 4096 > 100000 for r in state.rng.values()):
            raise EngineError('rng_limit', 429)
        for rng in state.rng.values():
            rng.counter += command.trial_index * 4096
    elif command.kind == 'intervene':
        if command.requested_tick != state.tick:
            raise EngineError('stale_tick')
        if len(state.pending) >= 128 or len(state.interventions) >= 1024:
            raise EngineError('intervention_limit', 429)
        if command.team_id not in state.tactics:
            raise EngineError('unknown_team', 422)
        if any(q.kind == 'tactic' and q.team_id == command.team_id and q.field == command.field for q in state.pending):
            raise EngineError('field_already_pending')
        old = getattr(state.tactics[command.team_id], command.field)
        state.interventions.append(Intervention(operation_id=command.operation_id, expected_revision=command.expected_revision,
            requested_tick=state.tick, effective_tick=state.tick + 1, team_id=command.team_id,
            field=command.field, previous_value=old, new_value=command.value, result='accepted'))
        queue(state, 'tactic', command.team_id, field=command.field, value=command.value, operation_id=command.operation_id)
    state.revision += 1
    validate_state(state)
    return state


def validate_state(state: EngineState):
    """Validate structural and continuation invariants, including required RNG/queue data."""
    c = state.scenario.config
    expected = build_scenario(c)
    if expected != state.scenario:
        raise EngineError('corrupt_snapshot', 422)
    teams = {c.home.team_id, c.away.team_id}
    players = {p.player_id: t.team_id for t in (c.home, c.away) for p in t.players}
    if (set(state.rng) != set(STREAMS) or set(state.score) != teams or set(state.tactics) != teams
            or any(type(v) is not int or v < 0 for v in state.score.values())
            or state.possession_team_id not in teams
            or players.get(state.possession_actor_id) != state.possession_team_id
            or {a.player_id for a in state.actors} != set(players)
            or any(players[a.player_id] != a.team_id or a.last_action_tick > state.tick for a in state.actors)
            or state.tick > c.duration_seconds
            or state.period != (1 if state.tick < c.duration_seconds // 2 else 2)
            or (state.lifecycle == 'completed') != (state.tick == c.duration_seconds)
            or state.event_cursor != len(state.events)):
        raise EngineError('corrupt_snapshot', 422)
    previous = -1
    goals = dict.fromkeys(teams, 0)
    for i, e in enumerate(state.events, 1):
        if (e.sequence != i or e.tick < previous or e.tick > state.tick
                or e.team_id is not None and e.team_id not in teams
                or e.actor_id is not None and players.get(e.actor_id) != e.team_id
                or e.recipient_id is not None and players.get(e.recipient_id) != e.team_id):
            raise EngineError('corrupt_snapshot', 422)
        if e.type == 'goal':
            if e.team_id is None:
                raise EngineError('corrupt_snapshot', 422)
            goals[e.team_id] += 1
        previous = e.tick
    if goals != state.score:
        raise EngineError('corrupt_snapshot', 422)
    for name, rng in state.rng.items():
        expected_key = hashlib.sha256(f'{ENGINE_VERSION}:{c.seed}:{name}'.encode()).hexdigest()
        if rng.key != expected_key:
            raise EngineError('corrupt_snapshot', 422)
    for t in (c.home, c.away):
        if [a.role for a in state.actors if a.team_id == t.team_id] != roles(state.tactics[t.team_id].formation):
            raise EngineError('corrupt_snapshot', 422)
    orders = [q.order for q in state.pending]
    if len(set(orders)) != len(orders) or any(q.tick <= state.tick or q.tick > c.duration_seconds
            or q.team_id not in teams or q.order >= state.next_queue_order for q in state.pending):
        raise EngineError('corrupt_snapshot', 422)
    accepted = {i.operation_id: i for i in state.interventions if i.result == 'accepted'}
    if set(accepted) != {q.operation_id for q in state.pending if q.kind == 'tactic'}:
        raise EngineError('corrupt_snapshot', 422)
    for q in state.pending:
        if q.kind == 'tactic':
            try:
                Tactics.model_validate({q.field: q.value})
            except (ValidationError, TypeError):
                raise EngineError('corrupt_snapshot', 422) from None
            i = accepted[q.operation_id]
            if (i.effective_tick, i.team_id, i.field, i.new_value) != (q.tick, q.team_id, q.field, q.value):
                raise EngineError('corrupt_snapshot', 422)


def capture_state(state: EngineState) -> Snapshot:
    validate_state(state)
    return Snapshot(state=state.model_copy(deep=True), state_hash=digest(state))


def restore_state(snapshot: Snapshot | dict) -> EngineState:
    if isinstance(snapshot, Snapshot):
        snapshot = snapshot.model_dump(mode='json')
    if not isinstance(snapshot, dict):
        raise EngineError('corrupt_snapshot', 422)
    if snapshot.get('engine_version') != ENGINE_VERSION or snapshot.get('schema_version') != 'sandbox/1':
        raise EngineError('incompatible_version')
    if isinstance(snapshot.get('state'), dict) and (snapshot['state'].get('engine_version') != ENGINE_VERSION
            or snapshot['state'].get('schema_version') != 'sandbox/1'):
        raise EngineError('incompatible_version')
    try:
        parsed = Snapshot.model_validate(snapshot)
    except ValidationError:
        raise EngineError('corrupt_snapshot', 422) from None
    if digest(parsed.state) != parsed.state_hash:
        raise EngineError('corrupt_snapshot', 422)
    validate_state(parsed.state)
    return parsed.state.model_copy(deep=True)


def match_record(state: EngineState, session_id: str):
    """Project fictional roster metadata for existing v1 consumers."""
    from ..models import Match, Team, Player
    config = state.scenario.config
    if config.duration_seconds != 5400:
        raise EngineError('v1_requires_90_minutes', 422)
    teams = [Team(team_id=t.team_id, name=t.name, color=t.color,
                  players=[Player(player_id=p.player_id, name=p.name, role=a.role, shirt_number=i)
                           for i, (p, a) in enumerate(zip(t.players, [a for a in state.actors if a.team_id == t.team_id]), 1)])
             for t in (config.home, config.away)]
    return Match(match_id=session_id, title=f'{config.home.name} vs {config.away.name}', seed=config.seed,
                 home=teams[0], away=teams[1])


def match_events(state: EngineState, session_id: str):
    """Compatibility adapter for the existing v1 90-minute replay consumers."""
    from ..models import MatchEvent, Point
    if state.scenario.config.duration_seconds != 5400:
        raise EngineError('v1_requires_90_minutes', 422)
    return [MatchEvent(event_id=f'{session_id}-{e.sequence}', match_id=session_id, sequence=e.sequence,
        match_second=e.tick, period=e.period, team_id=e.team_id, actor_id=e.actor_id,
        recipient_id=e.recipient_id, type=e.type, outcome=e.outcome,
        start=Point(x=100 - e.x if e.team_id == state.scenario.config.away.team_id else e.x, y=e.y),
        end=Point(x=100 - e.end_x if e.team_id == state.scenario.config.away.team_id else e.end_x, y=e.end_y),
        possession_id=str(e.possession_id),
        qualifiers={'engine_version': ENGINE_VERSION, 'scenario_id': state.scenario.scenario_id,
                    'session_id': session_id, 'policy_revision': e.policy_revision},
        generated_at_utc=datetime(2000, 1, 1, tzinfo=timezone.utc) + timedelta(seconds=e.tick)) for e in state.events]
