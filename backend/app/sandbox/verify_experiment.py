"""python -m app.sandbox.verify_experiment forkcast.json (no DB or network)."""
import argparse
from pathlib import Path
from .engine import canonical, parse_json
from .experiments import ExperimentBundle, verify_bundle


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('bundle', type=Path)
    args = parser.parse_args()
    try:
        if args.bundle.stat().st_size > 20_000_000:
            raise ValueError('experiment bundle exceeds 20 MB')
        result = verify_bundle(ExperimentBundle.model_validate(parse_json(args.bundle.read_bytes()))).model_dump()
    except (ValueError, OSError, RecursionError):
        result = {'verified': False, 'component': 'schema_or_version'}
    print(canonical(result))
    return 0 if result['verified'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
