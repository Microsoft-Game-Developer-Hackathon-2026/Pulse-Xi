"""Versioned contracts. Pitch x/y are normalized to 0..100."""
from datetime import datetime
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class EventType(StrEnum):
    kickoff = "kickoff"
    pass_ = "pass"
    carry = "carry"
    shot = "shot"
    goal = "goal"
    save = "save"
    tackle = "tackle"
    interception = "interception"
    pressure = "pressure"
    recovery = "recovery"
    turnover = "turnover"
    clearance = "clearance"
    foul = "foul"
    card = "card"
    substitution = "substitution"
    halftime = "halftime"
    fulltime = "fulltime"


class Point(BaseModel):
    x: float = Field(ge=0, le=100)
    y: float = Field(ge=0, le=100)


class Player(BaseModel):
    player_id: str
    name: str
    role: str
    shirt_number: int = Field(ge=1, le=99)


class Team(BaseModel):
    team_id: str
    name: str
    color: str
    players: list[Player]


class Match(BaseModel):
    match_id: str
    title: str
    seed: int
    synthetic: Literal[True] = True
    schema_version: Literal["1.0"] = "1.0"
    home: Team
    away: Team
    duration_seconds: int = 5400
    event_source: Literal["synthetic-generator"] = "synthetic-generator"


class MatchEvent(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    event_id: str
    match_id: str
    sequence: int = Field(ge=1)
    match_second: int = Field(ge=0, le=5400)
    period: Literal[1, 2]
    team_id: str | None = None
    actor_id: str | None = None
    recipient_id: str | None = None
    event_type: EventType = Field(alias="type")
    outcome: str | None = None
    start: Point | None = None
    end: Point | None = None
    possession_id: str | None = None
    qualifiers: dict[str, str | int | float | bool] = Field(default_factory=dict)
    source_type: Literal["synthetic-generator"] = "synthetic-generator"
    schema_version: Literal["1.0"] = "1.0"
    generated_at_utc: datetime

    @model_validator(mode="after")
    def check_period(self):
        if self.period == 1 and self.match_second > 2700:
            raise ValueError("first-half event after halftime")
        if self.period == 2 and self.match_second < 2700:
            raise ValueError("second-half event before halftime")
        return self


class Score(BaseModel):
    home: int = 0
    away: int = 0


class MatchState(BaseModel):
    match_id: str
    at_second: int
    score: Score
    phase: Literal["pre_match", "first_half", "halftime", "second_half", "fulltime"]
    possession_team_id: str | None
    last_event_id: str | None
    event_count: int


class TeamMetrics(BaseModel):
    team_id: str
    goals: int
    shots: int
    passes: int
    completed_passes: int
    pass_completion_pct: float
    final_third_entries: int
    recoveries: int
    turnovers: int
    pressure_events: int


class MatchMetrics(BaseModel):
    match_id: str
    at_second: int
    home: TeamMetrics
    away: TeamMetrics
    computed_from_event_count: int
