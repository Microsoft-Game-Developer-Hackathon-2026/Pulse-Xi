"""Bounded read-only exports using existing authoritative calculations."""
import csv
from datetime import datetime, timezone
import io
import json
import os
import re
from typing import Any, Literal

from fastapi import HTTPException
from fastapi.responses import Response
from pydantic import BaseModel

from .analytics import metrics_at
from .models import Match, MatchEvent
from .pass_difficulty import score_pass, verify_pass_difficulty


class AnalysisExport(BaseModel):
    schema_version: Literal['analysis-export/1'] = 'analysis-export/1'
    match_id: str
    replay_cutoff: int
    generated_at: str
    category: Literal['events', 'pass', 'metrics']
    synthetic: Literal[True] = True
    provenance: dict[str, Any]
    data: list[dict[str, Any]]


def safe_cell(value: Any) -> Any:
    if value is None:
        return ''
    if isinstance(value, (dict, list)):
        value = json.dumps(value, ensure_ascii=False, sort_keys=True)
    if isinstance(value, str) and re.match(r'^[\s\ufeff]*[=+\-@]', value):
        return "'" + value
    if isinstance(value, str) and value.startswith(('\t', '\r', '\n')):
        return "'" + value
    return value


def analysis_export(match: Match, events: list[MatchEvent], cutoff: int, category: Literal['events', 'pass', 'metrics'],
                    format: Literal['json', 'csv'], team_id: str | None, event_type: str | None, event_id: str | None, *, runtime_provenance: dict[str, Any] | None = None) -> Response:
    if cutoff > match.duration_seconds:
        raise HTTPException(422, 'cutoff exceeds match duration')
    if team_id and team_id not in (match.home.team_id, match.away.team_id):
        raise HTTPException(422, 'unknown team')
    visible = sorted((e for e in events if e.match_id == match.match_id and e.match_second <= cutoff), key=lambda e: e.sequence)
    if len(visible) > 5000:
        raise HTTPException(413, 'export exceeds 5000 source events; narrow cutoff')
    supporting_ids = [e.event_id for e in visible]
    if category == 'events':
        selected = [e for e in visible if (not team_id or e.team_id == team_id) and (not event_type or e.event_type == event_type)]
        if len(selected) > 5000:
            raise HTTPException(413, 'export exceeds 5000 events; narrow filters or cutoff')
        data = [e.model_dump(mode='json', by_alias=True) for e in selected]
        supporting_ids = [e.event_id for e in selected]
        fields = list(MatchEvent.model_fields)
        fields = ['type' if f == 'event_type' else f for f in fields]
    elif category == 'pass':
        event = next((e for e in visible if e.event_id == event_id and e.event_type == 'pass'), None)
        if event is None:
            raise HTTPException(404, 'visible pass not found')
        try:
            packet = score_pass(match, event, cutoff)
        except ValueError as error:
            raise HTTPException(422, 'pass analysis unavailable for this source event') from error
        if not verify_pass_difficulty(packet, match, events):
            raise HTTPException(409, 'pass evidence verification failed')
        data = [packet.model_dump(mode='json')]
        supporting_ids = packet.supporting_event_ids
        fields = list(data[0])
    else:
        metrics = metrics_at(match, visible, cutoff).model_dump(mode='json')
        data = [{'team_id': team.team_id, **metrics[side], 'units': 'counts; pass_completion_pct in percent',
                 'computed_from_event_count': metrics['computed_from_event_count']} for side, team in [('home', match.home), ('away', match.away)]]
        fields = list(data[0])
    if sum(len(json.dumps(row, ensure_ascii=False).encode('utf-8')) for row in data) > 8_000_000:
        raise HTTPException(413, 'export exceeds byte budget; narrow cutoff')
    envelope = AnalysisExport(match_id=match.match_id, replay_cutoff=cutoff,
        generated_at=datetime.now(timezone.utc).isoformat(), category=category,
        provenance={'fixture_seed': match.seed, 'build_revision': os.getenv('PULSE_BUILD_REVISION') or None,
                    'fixture_generator_version': None, 'engine_manifest': None, 'source_event_ids': supporting_ids, 'event_units': 'normalized pitch coordinates, not metres',
                    'unavailable': ['fixture generator version', 'authoritative engine manifest', 'build revision unless configured']}, data=data)
    if runtime_provenance is not None:
        envelope.provenance['runtime'] = runtime_provenance
        envelope.provenance['fixture_seed'] = None
        envelope.provenance['scenario_seed'] = match.seed
        envelope.provenance['unavailable'] = ['fixture generator version', 'embedded engine manifest; download separately']
    filename = re.sub(r'[^A-Za-z0-9_-]', '_', match.match_id)[:80] + f'-{category}-{cutoff}.{format}'
    if format == 'json':
        content = envelope.model_dump_json(indent=2)
        media_type = 'application/json'
    else:
        output = io.StringIO(newline='')
        metadata = ['export_schema', 'export_match_id', 'replay_cutoff', 'generated_at', 'fixture_seed', 'build_revision', 'coordinate_units']
        writer = csv.writer(output)
        runtime_columns = list(runtime_provenance) if runtime_provenance is not None else []
        writer.writerow(metadata + ['runtime_' + key for key in runtime_columns] + fields)
        for row in data:
            writer.writerow([safe_cell(v) for v in [envelope.schema_version, match.match_id, cutoff, envelope.generated_at,
                envelope.provenance['fixture_seed'], envelope.provenance['build_revision'], envelope.provenance['event_units']] +
                ([runtime_provenance[key] for key in runtime_columns] if runtime_provenance else []) + [row.get(f) for f in fields]])
        content = '\ufeff' + output.getvalue()
        media_type = 'text/csv'
    if len(content.encode('utf-8')) > 8_000_000:
        raise HTTPException(413, 'export exceeds byte budget; narrow cutoff')
    return Response(content, media_type=media_type, headers={'Content-Disposition': f'attachment; filename="{filename}"', 'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff'})
