"""Regenerate the checked-in versioned event JSON schema."""
import json
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root / "backend"))
from app.models import MatchEvent  # noqa: E402

target = root / "data" / "contracts" / "match_event_v1.schema.json"
target.parent.mkdir(parents=True, exist_ok=True)
target.write_text(json.dumps(MatchEvent.model_json_schema(), indent=2) + "\n", encoding="utf-8")
print(target)
