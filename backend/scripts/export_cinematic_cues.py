"""Write a deterministic synthetic fixture cue manifest to stdout or a file.

Example from the repository root:
  python backend/scripts/export_cinematic_cues.py --fixture comeback --output cues.json
"""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.cinematic_cues import export_goal_cues
from app.simulator import FIXTURES


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", choices=sorted(FIXTURES), default="comeback")
    parser.add_argument("--output", type=Path, help="output path; stdout when omitted")
    args = parser.parse_args()
    serialized = json.dumps(export_goal_cues(args.fixture), ensure_ascii=True,
                            allow_nan=False, sort_keys=True, indent=2) + "\n"
    if args.output:
        args.output.write_text(serialized, encoding="utf-8")
    else:
        sys.stdout.write(serialized)


if __name__ == "__main__":
    main()
