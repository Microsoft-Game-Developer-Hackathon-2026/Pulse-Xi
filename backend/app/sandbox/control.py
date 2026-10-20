"""Durable bounded server drivers and paired experiments; safe to run in multiple workers.

Job progress uses compare-and-swap; each engine command has a stable retry ID.
Crash between an engine commit and a progress commit replays the receipt, not the tick.
"""
import asyncio
import json
from typing import Literal

from pydantic import Field, model_validator
from starlette.concurrency import run_in_threadpool

from . import storage
from .engine import EngineError, canonical, digest
from .models import Command, Identifier, Model, Tactics, Digest
from typing import Annotated

RuntimeId = Annotated[str, Field(pattern=r'^runtime-[0-9a-f]{64}$')]


class RunRequest(Model):
    operation_id: Identifier
    expected_revision: int = Field(ge=0, le=2048)
    target_tick: int = Field(ge=1, le=5400)
    ticks_per_step: int = Field(default=5, ge=1, le=60)


class Change(Model):
    team_id: Identifier
    field: Literal['formation', 'pressing', 'compactness', 'directness', 'tempo', 'risk']
    value: int | str

    @model_validator(mode='after')
    def valid(self):
        Tactics.model_validate({self.field: self.value})
        return self


class ExperimentRequest(Model):
    operation_id: Identifier
    checkpoint_id: str = Field(pattern=r'^checkpoint-[0-9a-f]{64}$')
    expected_revision: int = Field(ge=1, le=2048)
    trials: int = Field(default=3, ge=1, le=5)
    horizon: int = Field(default=300, ge=1, le=600)
    baseline: list[Change] = Field(default_factory=list, max_length=6)
    variation: list[Change] = Field(default_factory=list, max_length=6)

    @model_validator(mode='after')
    def distinct(self):
        for arm in (self.baseline, self.variation):
            if len({(c.team_id, c.field) for c in arm}) != len(arm):
                raise ValueError('each tactical field may be changed only once per arm')
        return self


class Run(Model):
    run_id: str = Field(pattern=r'^run-[0-9a-f]{64}$')
    session_id: RuntimeId
    request: RunRequest
    status: Literal['queued', 'running', 'completed', 'paused', 'cancelled', 'error'] = 'queued'
    tick: int = Field(ge=0, le=5400)
    revision: int = Field(ge=0, le=2048)
    event_cursor: int = Field(ge=1, le=20000)
    step_index: int = Field(default=0, ge=0, le=5400)
    error: str | None = None


class Experiment(Model):
    experiment_id: str = Field(pattern=r'^experiment-[0-9a-f]{64}$')
    request: ExperimentRequest
    parent_session_id: RuntimeId
    parent_state_hash: Digest
    start_tick: int = Field(ge=0, le=5400)
    status: Literal['queued', 'running', 'completed', 'cancelled', 'error'] = 'queued'
    branches: list[RuntimeId] = Field(default_factory=list, max_length=10)
    branch_index: int = Field(default=0, ge=0, le=10)
    command_index: int = Field(default=0, ge=0, le=9)
    session_id: RuntimeId
    tick: int = Field(ge=0, le=5400)
    revision: int = Field(ge=0, le=2048)
    event_cursor: int = Field(ge=1, le=20000)
    error: str | None = None


def operation_id(*parts):
    return 'job-' + digest(list(parts))


def read(table, owner, identity):
    assert table in ('runs', 'experiments')
    with storage.connect() as db:
        row = db.execute(f'SELECT generation,payload FROM {table} WHERE id=? AND owner=?', (identity, owner)).fetchone()
        if row is None:
            raise EngineError('not_found', 404)
        model = Run if table == 'runs' else Experiment
        return row[0], model.model_validate_json(row[1])


def list_runs(owner, session_id):
    with storage.connect() as db:
        storage.load(db, owner, session_id)
        return [Run.model_validate_json(r[0]) for r in db.execute(
            'SELECT payload FROM runs WHERE owner=? AND session_id=? ORDER BY rowid DESC', (owner, session_id))]


def list_experiments(owner):
    with storage.connect() as db:
        return [Experiment.model_validate_json(r[0]) for r in db.execute(
            'SELECT payload FROM experiments WHERE owner=? ORDER BY rowid DESC', (owner,))]


def save(table, owner, identity, generation, value):
    assert table in ('runs', 'experiments')
    with storage.connect() as db:
        db.execute('UPDATE ' + table + ' SET payload=?,generation=generation+1 WHERE id=? AND owner=? AND generation=?',
                   (canonical(value), identity, owner, generation))


def create_run(owner, session_id, request: RunRequest) -> Run:
    identity = 'run-' + digest([owner, request.operation_id])
    fingerprint = digest([session_id, request])
    with storage.connect() as db:
        db.execute('BEGIN IMMEDIATE')
        row = db.execute('SELECT fingerprint,payload FROM runs WHERE id=? AND owner=?', (identity, owner)).fetchone()
        if row:
            if row[0] != fingerprint:
                raise EngineError('idempotency_conflict')
            return Run.model_validate_json(row[1])
        state, _, _ = storage.load(db, owner, session_id)
        if state.revision != request.expected_revision:
            raise EngineError('stale_revision')
        if state.lifecycle not in ('paused', 'running') or not state.tick < request.target_tick <= state.scenario.config.duration_seconds:
            raise EngineError('invalid_run_boundary', 422)
        required = 1 + (request.target_tick - state.tick + request.ticks_per_step - 1) // request.ticks_per_step
        required += int(request.target_tick < state.scenario.config.duration_seconds)
        if state.revision + required > 2048:
            raise EngineError('run_exceeds_command_budget', 422)
        if db.execute('SELECT COUNT(*) FROM runs').fetchone()[0] >= 100:
            raise EngineError('run_limit', 429)
        if db.execute("SELECT 1 FROM runs WHERE session_id=? AND json_extract(payload,'$.status') IN ('queued','running')", (session_id,)).fetchone():
            raise EngineError('run_already_active')
        run = Run(run_id=identity, session_id=session_id, request=request,
                  tick=state.tick, revision=state.revision, event_cursor=state.event_cursor)
        db.execute('INSERT INTO runs VALUES (?,?,?,?,?,?)', (identity, owner, fingerprint, session_id, 0, canonical(run)))
        return run


def tick_run(owner, identity):
    generation, run = read('runs', owner, identity)
    if run.status not in ('queued', 'running'):
        return
    try:
        if run.status == 'queued':
            receipt = storage.mutate(owner, run.session_id, Command(operation_id=operation_id(identity, 'resume'),
                expected_revision=run.revision, kind='resume'))
            run.status = 'running'
        else:
            receipt = storage.mutate(owner, run.session_id, Command(operation_id=operation_id(identity, run.step_index),
                expected_revision=run.revision, kind='advance', ticks=min(run.request.ticks_per_step, run.request.target_tick - run.tick)))
            if receipt.tick >= run.request.target_tick:
                if receipt.lifecycle != 'completed':
                    receipt = storage.mutate(owner, run.session_id, Command(operation_id=operation_id(identity, 'stop'),
                        expected_revision=receipt.revision, kind='pause'))
                run.status = 'completed'
            run.step_index += 1
        run.tick, run.revision, run.event_cursor = receipt.tick, receipt.revision, receipt.event_cursor
    except EngineError as error:
        current = storage.get_runtime(owner, run.session_id)
        run.tick, run.revision, run.event_cursor = current.tick, current.revision, current.event_cursor
        run.status = 'paused' if current.state.lifecycle == 'paused' else 'error'
        run.error = error.code
    save('runs', owner, identity, generation, run)


def stop_session(owner, session_id, identity, kind):
    for attempt in range(3):
        view = storage.get_runtime(owner, session_id)
        if view.state.lifecycle in ('completed', 'cancelled') or kind == 'pause' and view.state.lifecycle == 'paused':
            return view
        try:
            storage.mutate(owner, session_id, Command(operation_id=operation_id(identity, kind, view.revision),
                           expected_revision=view.revision, kind=kind))
            return storage.get_runtime(owner, session_id)
        except EngineError as error:
            if error.code != 'stale_revision':
                raise
    raise EngineError('stale_revision')


def cancel_run(owner, identity) -> Run:
    with storage.connect() as db:
        db.execute('BEGIN IMMEDIATE')
        row = db.execute('SELECT payload FROM runs WHERE id=? AND owner=?', (identity, owner)).fetchone()
        if row is None:
            raise EngineError('not_found', 404)
        run = Run.model_validate_json(row[0])
        if run.status == 'completed':
            return run
        run.status = 'cancelled'
        db.execute('UPDATE runs SET generation=generation+1,payload=? WHERE id=?', (canonical(run), identity))
    current = stop_session(owner, run.session_id, identity, 'pause')
    generation, run = read('runs', owner, identity)
    run.tick, run.revision, run.event_cursor = current.tick, current.revision, current.event_cursor
    save('runs', owner, identity, generation, run)
    return run


def create_experiment(owner, request: ExperimentRequest) -> Experiment:
    identity = 'experiment-' + digest([owner, request.operation_id])
    checkpoint = storage.get_checkpoint(owner, request.checkpoint_id)
    if checkpoint.revision != request.expected_revision:
        raise EngineError('stale_revision')
    s = checkpoint.snapshot.state
    if s.lifecycle != 'paused' or s.tick + request.horizon > s.scenario.config.duration_seconds:
        raise EngineError('invalid_experiment_boundary', 422)
    required = 1 + max(len(request.baseline), len(request.variation)) + (request.horizon + 299) // 300
    if s.revision + required > 2048:
        raise EngineError('experiment_exceeds_command_budget', 422)
    for change in request.baseline + request.variation:
        if change.team_id not in s.tactics:
            raise EngineError('unknown_team', 422)
        if any(q.kind == 'tactic' and q.team_id == change.team_id and q.field == change.field for q in s.pending):
            raise EngineError('field_already_pending')
    with storage.connect() as db:
        db.execute('BEGIN IMMEDIATE')
        row = db.execute('SELECT fingerprint,payload FROM experiments WHERE id=? AND owner=?', (identity, owner)).fetchone()
        if row:
            if row[0] != digest(request):
                raise EngineError('idempotency_conflict')
            return Experiment.model_validate_json(row[1])
        if db.execute('SELECT COUNT(*) FROM experiments').fetchone()[0] >= 10:
            raise EngineError('experiment_limit', 429)
        if db.execute('SELECT COUNT(*) FROM sessions').fetchone()[0] + 2 * request.trials > 100:
            raise EngineError('session_limit', 429)
        result = Experiment(experiment_id=identity, request=request, parent_session_id=checkpoint.session_id,
            parent_state_hash=checkpoint.snapshot.state_hash, start_tick=checkpoint.tick, session_id=checkpoint.session_id,
            tick=checkpoint.tick, revision=checkpoint.revision, event_cursor=checkpoint.event_cursor)
        db.execute('INSERT INTO experiments VALUES (?,?,?,?,?)', (identity, owner, digest(request), 0, canonical(result)))
        return result


def trial_commands(experiment, branch_index):
    request = experiment.request
    trial = branch_index // 2
    changes = request.baseline if branch_index % 2 == 0 else request.variation
    values = [dict(kind='trial', trial_index=trial)]
    values.extend(dict(kind='intervene', team_id=c.team_id, field=c.field, value=c.value,
                       requested_tick=experiment.start_tick) for c in changes)
    left = request.horizon
    while left:
        count = min(300, left)
        values.append(dict(kind='step', ticks=count))
        left -= count
    return [Command(operation_id=operation_id(experiment.experiment_id, branch_index, i),
                    expected_revision=request.expected_revision + i, **value) for i, value in enumerate(values)]


def tick_experiment(owner, identity):
    generation, experiment = read('experiments', owner, identity)
    if experiment.status not in ('queued', 'running'):
        return
    experiment.status = 'running'
    try:
        index = experiment.branch_index
        if index >= 2 * experiment.request.trials:
            experiment.status = 'completed'
        elif len(experiment.branches) <= index:
            receipt = storage.create_session(owner, operation_id(identity, 'branch', index),
                checkpoint_id=experiment.request.checkpoint_id, expected_revision=experiment.request.expected_revision)
            experiment.branches.append(receipt.session_id)
        else:
            commands = trial_commands(experiment, index)
            if experiment.command_index == len(commands):
                experiment.branch_index += 1
                experiment.command_index = 0
            else:
                receipt = storage.mutate(owner, experiment.branches[index], commands[experiment.command_index])
                experiment.command_index += 1
                experiment.session_id = receipt.session_id
                experiment.tick, experiment.revision, experiment.event_cursor = receipt.tick, receipt.revision, receipt.event_cursor
    except EngineError as error:
        experiment.status, experiment.error = 'error', error.code
    save('experiments', owner, identity, generation, experiment)


def cancel_experiment(owner, identity) -> Experiment:
    with storage.connect() as db:
        db.execute('BEGIN IMMEDIATE')
        row = db.execute('SELECT payload FROM experiments WHERE id=? AND owner=?', (identity, owner)).fetchone()
        if row is None:
            raise EngineError('not_found', 404)
        experiment = Experiment.model_validate_json(row[0])
        if experiment.status == 'completed':
            return experiment
        experiment.status = 'cancelled'
        db.execute('UPDATE experiments SET generation=generation+1,payload=? WHERE id=?', (canonical(experiment), identity))
    latest = None
    for sid in experiment.branches:
        latest = stop_session(owner, sid, identity, 'cancel')
    generation, experiment = read('experiments', owner, identity)
    if latest:
        experiment.session_id = latest.session_id
        experiment.tick, experiment.revision, experiment.event_cursor = latest.tick, latest.revision, latest.event_cursor
        save('experiments', owner, identity, generation, experiment)
    return experiment


def drive_once():
    # Each pass is bounded; SQL limits stop one client occupying every worker.
    with storage.connect() as db:
        runs = db.execute("SELECT owner,id FROM runs WHERE json_extract(payload,'$.status') IN ('queued','running') ORDER BY generation,rowid LIMIT 4").fetchall()
        experiments = db.execute("SELECT owner,id FROM experiments WHERE json_extract(payload,'$.status') IN ('queued','running') ORDER BY generation,rowid LIMIT 2").fetchall()
    for owner, identity in runs:
        tick_run(owner, identity)
    for owner, identity in experiments:
        tick_experiment(owner, identity)


async def driver(stop: asyncio.Event):
    while not stop.is_set():
        try:
            await run_in_threadpool(drive_once)
        except Exception:
            # Retain queued work and retry after transient storage faults. Log
            # only a fixed message; credentials/payloads never enter logs.
            import logging
            logging.getLogger(__name__).exception('sandbox driver pass failed')
        try:
            await asyncio.wait_for(stop.wait(), timeout=0.25)
        except TimeoutError:
            pass
