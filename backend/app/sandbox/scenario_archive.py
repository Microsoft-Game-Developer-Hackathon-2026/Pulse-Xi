"""Portable scenario records, deliberately outside hashed simulation state."""
from datetime import datetime, timezone
from typing import Literal

from pydantic import Field, field_validator

from .engine import EngineError, build_scenario
from .models import Digest, Model, Scenario, RNG_ALGORITHM, STREAMS


class ScenarioArchive(Model):
    archive_version: Literal['scenario-archive/1'] = 'scenario-archive/1'
    scenario: Scenario
    rng_algorithm: Literal['sha256-counter/1'] = RNG_ALGORITHM
    rng_derivation: Literal['sha256(engine_version:seed:stream); sha256(key:counter)'] = 'sha256(engine_version:seed:stream); sha256(key:counter)'
    rng_streams: list[str] = Field(default_factory=lambda: list(STREAMS), max_length=4)
    # NULL means the original timestamp was not recorded (pre-schema-3 data).
    created_at_utc: str | None = Field(max_length=40, pattern=r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?Z$')

    @field_validator('created_at_utc')
    @classmethod
    def utc_timestamp(cls, value):
        if value is not None:
            parsed = datetime.fromisoformat(value)
            if not value.endswith('Z') or parsed.utcoffset() != timezone.utc.utcoffset(parsed):
                raise ValueError('creation timestamp must use UTC with a Z suffix')
        return value

    @field_validator('rng_streams')
    @classmethod
    def supported_streams(cls, value):
        if value != list(STREAMS):
            raise ValueError('unsupported RNG streams or ordering')
        return value


class ScenarioSummary(Model):
    scenario_id: str
    config_hash: Digest
    seed: int
    preset: str
    created_at_utc: str | None


def validate_identity(archive: ScenarioArchive) -> Scenario:
    resolved = build_scenario(archive.scenario.config)
    if resolved != archive.scenario:
        raise EngineError('scenario_hash_mismatch', 409)
    return resolved


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec='microseconds').replace('+00:00', 'Z')
