"""Trusted local administration only. Never run against arbitrary uploaded databases."""
import argparse
import json
import sys
import sqlite3
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1] / 'backend'))
from app.database_backup import copy_database
from app.storage import database_path


def main():
    parser = argparse.ArgumentParser(description='Copy verified Pulse-Xi SQLite backups to NEW files; never overwrite live data.')
    parser.add_argument('operation',choices=['backup','restore'])
    parser.add_argument('--source',type=Path,help='Defaults to PULSE_DB_PATH; use an absolute override for a server started in another directory')
    parser.add_argument('--destination',type=Path,required=True)
    parser.add_argument('--sha256',help='Required for restore: the SHA-256 reported by the original backup command')
    args = parser.parse_args()
    if args.operation == 'restore' and (not args.sha256 or len(args.sha256) != 64):
        parser.error('restore requires the recorded --sha256 digest')
    source=args.source or database_path()
    if args.source is None and not source.is_absolute():
        parser.error('relative PULSE_DB_PATH is ambiguous across server/CLI directories; supply --source explicitly')
    try:
        print(json.dumps(copy_database(source,args.destination,args.sha256 if args.operation == 'restore' else None)))
    except (ValueError,OSError,sqlite3.Error) as error:
        # This is an operator CLI, not a public HTTP response. Preserve failure status.
        parser.exit(1, f'Backup/recovery failed: {error}\n')


if __name__ == '__main__':
    main()
