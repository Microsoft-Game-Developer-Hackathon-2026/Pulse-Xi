"""Deterministic fictional match generator with possession and spatial continuity."""
import random
from datetime import datetime, timedelta, timezone

from .models import EventType, Match, MatchEvent, Player, Point, Team

KICKOFF = datetime(2026, 10, 14, 12, tzinfo=timezone.utc)
FIXTURES = {
    "comeback": (1107, "Harbour City comeback", [(1000, "away"), (3400, "away"), (3900, "home"), (4700, "home"), (5240, "home")]),
    "high-press": (2209, "Northbank high press", [(1820, "home"), (2960, "home"), (4240, "away")]),
    "late-winner": (3319, "Last-minute winner", [(2100, "away"), (3520, "home"), (5330, "home")]),
}


def make_team(team_id: str, name: str, color: str) -> Team:
    roles = ["GK", "RB", "CB", "CB", "LB", "DM", "CM", "AM", "RW", "ST", "LW"]
    first = ["Ari", "Bela", "Cato", "Dara", "Eli", "Faye", "Gio", "Hana", "Ivo", "Juno", "Kian"]
    return Team(team_id=team_id, name=name, color=color,
                players=[Player(player_id=f"{team_id}-{i+1:02}", name=f"{first[i]} {name.split()[0]}",
                                role=role, shirt_number=i + 1) for i, role in enumerate(roles)])


def generate(fixture: str = "comeback", seed: int | None = None) -> tuple[Match, list[MatchEvent]]:
    if fixture not in FIXTURES and fixture != "custom":
        raise ValueError("unknown fixture")
    base_seed, title, goals = FIXTURES.get(fixture, (seed or 4411, "Custom synthetic match", []))
    chosen_seed = seed if seed is not None else base_seed
    rng = random.Random(chosen_seed)
    match_id = f"{fixture}-{chosen_seed}"
    home = make_team("harbour", "Harbour City", "#27d5df")
    away = make_team("northbank", "Northbank United", "#ff7869")
    match = Match(match_id=match_id, title=title, seed=chosen_seed, home=home, away=away)
    events: list[MatchEvent] = []
    possession = "home"
    possession_number = 1
    position = Point(x=50, y=50)

    def emit(second: int, kind: EventType, side: str | None = None, actor: int | None = None,
             start: Point | None = None, end: Point | None = None, outcome: str | None = None,
             recipient: int | None = None, qualifiers: dict | None = None) -> None:
        team = home if side == "home" else away if side == "away" else None
        sequence = len(events) + 1
        events.append(MatchEvent(event_id=f"{match_id}-e{sequence:04}", match_id=match_id,
                                 sequence=sequence, match_second=second, period=1 if second <= 2700 else 2,
                                 team_id=team.team_id if team else None,
                                 actor_id=team.players[actor].player_id if team and actor is not None else None,
                                 recipient_id=team.players[recipient].player_id if team and recipient is not None else None,
                                 type=kind, outcome=outcome, start=start, end=end,
                                 possession_id=f"{match_id}-p{possession_number:04}" if team else None,
                                 qualifiers=qualifiers or {}, generated_at_utc=KICKOFF + timedelta(seconds=second)))

    emit(0, EventType.kickoff, possession, 7, position, position, "started")
    second = 0
    pending_goals = list(goals)
    while second < 5380:
        second = min(second + rng.randint(12, 25), 5380)
        if events[-1].match_second < 2700 <= second:
            emit(2700, EventType.halftime, outcome="break")
            second = 2701
            possession = "away"
            possession_number += 1
            position = Point(x=50, y=50)
            emit(second, EventType.kickoff, possession, 7, position, position, "started")
        if pending_goals and second >= pending_goals[0][0]:
            goal_second, scoring_side = pending_goals.pop(0)
            possession = scoring_side
            possession_number += 1
            position = Point(x=83, y=rng.randint(36, 64))
            shooter = rng.choice([7, 8, 9, 10])
            target = Point(x=100, y=50)
            emit(goal_second, EventType.shot, possession, shooter, position, target, "goal",
                 qualifiers={"shot_quality_proxy": round(max(0.05, 0.45 - abs(position.y - 50) / 100), 2)})
            emit(goal_second, EventType.goal, possession, shooter, position, target, "scored",
                 qualifiers={"assisted_shot_event_id": events[-1].event_id})
            possession = "away" if possession == "home" else "home"
            possession_number += 1
            position = Point(x=50, y=50)
            emit(min(goal_second + 1, 5399), EventType.kickoff, possession, 7, position, position, "restarted")
            second = max(second, goal_second + 1)
            continue

        actor = rng.choice([5, 6, 7, 8, 9, 10])
        roll = rng.random()
        if position.x > 73 and roll < 0.24:
            target = Point(x=100, y=rng.uniform(35, 65))
            emit(second, EventType.shot, possession, actor, position, target,
                 "saved" if rng.random() < 0.42 else "off_target",
                 qualifiers={"shot_quality_proxy": round(max(0.02, (position.x - 65) / 100 - abs(position.y - 50) / 180), 2)})
            possession = "away" if possession == "home" else "home"
            possession_number += 1
            position = Point(x=rng.uniform(18, 35), y=rng.uniform(25, 75))
            emit(min(second + 1, 5399), EventType.recovery, possession, rng.choice([1, 2, 3, 5]), position, position, "won")
        elif roll < 0.12:
            emit(second, EventType.pressure, "away" if possession == "home" else "home", actor,
                 position, position, "applied")
        elif roll < 0.23:
            emit(second, EventType.turnover, possession, actor, position, position, "lost")
            possession = "away" if possession == "home" else "home"
            possession_number += 1
            position = Point(x=max(5, 100 - position.x), y=position.y)
            emit(min(second + 1, 5399), EventType.recovery, possession, rng.choice([2, 5, 6]), position, position, "won")
        else:
            end = Point(x=min(94, max(5, position.x + rng.uniform(-9, 21))),
                        y=min(95, max(5, position.y + rng.uniform(-19, 19))))
            if roll < 0.72:
                recipient = rng.choice([5, 6, 7, 8, 9, 10])
                complete = rng.random() < (0.87 if position.x < 70 else 0.73)
                emit(second, EventType.pass_, possession, actor, position, end,
                     "complete" if complete else "incomplete", recipient if complete else None)
                if not complete:
                    possession = "away" if possession == "home" else "home"
                    possession_number += 1
                    position = Point(x=100 - end.x, y=end.y)
                    emit(min(second + 1, 5399), EventType.recovery, possession, rng.choice([2, 5, 6]), position, position, "won")
                    continue
            else:
                emit(second, EventType.carry, possession, actor, position, end, "complete")
            position = end
    emit(5400, EventType.fulltime, outcome="ended")
    return match, events
