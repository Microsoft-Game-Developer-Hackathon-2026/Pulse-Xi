# Decisions

- All teams, players, and events are fictional and labeled synthetic.
- The first vertical slice keeps seeded fixtures in memory. This makes replay deterministic; durable ingest and SQLite are the next backend milestone.
- The local match clock is controlled by the browser. The WebSocket demonstrates sequenced event delivery; the replay UI uses REST snapshots so seeking is exact.
- Coordinates are normalized 0..100 in the attacking team's direction. They are generated states, not video tracking.
- Fixture goals are scripted at fixed seconds to guarantee three reliable demo story arcs. Other actions are seeded state-machine outputs. This is demonstration data, not a predictive football model.
- No LLM integration is claimed. The `/health` response reports `not_configured` until genuine Foundry integration is verified.
