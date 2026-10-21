"""Usage: python -m app.sandbox.verify_manifest experiment.json"""
import argparse
import json
from pathlib import Path
from pydantic import ValidationError
from .manifest import verify_manifest
from .engine import parse_json
from .models import ExperimentManifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('manifest', type=Path)
    args = parser.parse_args()
    try:
        if args.manifest.stat().st_size > 2_000_000:
            raise ValueError('manifest exceeds 2 MB')
        manifest = ExperimentManifest.model_validate(parse_json(args.manifest.read_bytes()))
        result = verify_manifest(manifest).model_dump()
    except (OSError, ValueError, ValidationError, RecursionError) as error:
        result = {'verified': False, 'component': 'schema_or_version', 'error': type(error).__name__}
    print(json.dumps(result, sort_keys=True))
    return 0 if result['verified'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
