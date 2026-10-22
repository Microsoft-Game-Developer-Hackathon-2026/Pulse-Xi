"""python -m app.sandbox.verify_experiment forkcast.json (no DB or network)."""
import argparse
from pathlib import Path
from .engine import canonical
from .experiments import verify_bundle
from .reproduction import read_forkcast, read_bounded


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('bundle', type=Path)
    args = parser.parse_args()
    try:
        result = verify_bundle(read_forkcast(read_bounded(args.bundle, 20_000_000))).model_dump()
    except (ValueError, OSError, RecursionError):
        result = {'verified': False, 'component': 'schema_or_version'}
    print(canonical(result))
    return 0 if result['verified'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
