# Event contract v1.0

The authoritative schema is `backend/app/models.py`; FastAPI serves machine-readable OpenAPI at `/openapi.json`. Every event has a stable `event_id`, a `match_id`, a delivery `sequence`, a logical `match_second`, `period`, `source_type`, `schema_version`, and a UTC generation timestamp. Coordinates are normalized to 0–100 from the attacking team's point of view. Team/player references must belong to the fixture.

`POST /api/matches/ingest` accepts a synthetic match and up to 1,000 versioned events. It validates identities, deduplicates identical event IDs, rejects conflicting IDs, sorts out-of-order events by match clock and ID, then assigns contiguous delivery sequence numbers. Ingested matches live in process memory in this milestone; restart loses imported data. The built-in fixtures regenerate exactly from their seeds.

`GET /api/matches/{id}/state?at_second=N` and `/metrics?at_second=N` derive values only from events up to N. Goals are counted from `goal` events. Pass completion is completed pass events divided by all pass events. Final-third entry counts completed passes or carries crossing x=66.7. Pressure counts explicit `pressure` events; it is not tracking-derived intensity. Shot quality is a toy geometry proxy stored per shot and is **not** calibrated xG. No player speed or shot speed is measured.

The WebSocket sends a snapshot then ordered event messages with sequence IDs, allowing clients to deduplicate or resume with `?cursor=N`. It streams a fast deterministic replay for local demonstration; the browser controls the visible replay clock.
