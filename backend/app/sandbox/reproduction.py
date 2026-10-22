"""Portable replay envelopes. Observed provenance is unsigned and never hashed as engine input."""
import platform
import re
import subprocess
from pathlib import Path
from typing import Literal

from pydantic import Field

from .engine import parse_json
from .experiments import ExperimentBundle
from .models import ExperimentManifest, Model


class ExecutionProvenance(Model):
    provenance_version: Literal['execution-provenance/1'] = 'execution-provenance/1'
    observation_scope: Literal['exporting build; original execution environment unrecorded'] = 'exporting build; original execution environment unrecorded'
    git_revision: str | None = Field(pattern=r'^(?:[0-9a-f]{40}|[0-9a-f]{64})$')
    working_tree_dirty: bool | None
    python_version: str = Field(max_length=32, pattern=r'^\d+\.\d+\.\d+$')
    operating_system: Literal['Windows', 'Linux', 'Darwin', 'other']
    simulation_dependencies: Literal['resolved-synthetic-config; no external data or presentation assets'] = 'resolved-synthetic-config; no external data or presentation assets'


class RuntimeReproduction(Model):
    archive_version: Literal['runtime-reproduction/1']
    manifest: ExperimentManifest
    provenance: ExecutionProvenance


class ForkCastReproduction(Model):
    archive_version: Literal['forkcast-reproduction/1']
    manifest: ExperimentBundle
    provenance: ExecutionProvenance


def execution_provenance() -> ExecutionProvenance:
    revision = dirty = None
    root = Path(__file__).resolve().parents[3]
    try:
        # Fixed read-only commands; no host/user names, remotes, paths or environment exports.
        identity = subprocess.run(['git', '-C', str(root), 'rev-parse', '--show-toplevel', 'HEAD'], capture_output=True,
                                  text=True, timeout=2, check=True).stdout.splitlines()
        if len(identity) != 2 or Path(identity[0]).resolve() != root:
            raise ValueError('source root is not this Git checkout')
        head = identity[1].strip()
        changes = subprocess.run(['git', '-C', str(root), 'status', '--porcelain', '--untracked-files=normal'],
                                 capture_output=True, text=True, timeout=2, check=True).stdout
        if re.fullmatch(r'(?:[0-9a-f]{40}|[0-9a-f]{64})', head):
            revision, dirty = head, bool(changes.strip())
    except (OSError, ValueError, subprocess.SubprocessError):
        pass  # A source distribution may genuinely have no Git metadata.
    system = platform.system()
    return ExecutionProvenance(git_revision=revision, working_tree_dirty=dirty,
        python_version=platform.python_version(), operating_system=system if system in ('Windows', 'Linux', 'Darwin') else 'other')


def runtime_reproduction(manifest: ExperimentManifest) -> RuntimeReproduction:
    return RuntimeReproduction(archive_version='runtime-reproduction/1', manifest=manifest, provenance=execution_provenance())


def forkcast_reproduction(manifest: ExperimentBundle) -> ForkCastReproduction:
    return ForkCastReproduction(archive_version='forkcast-reproduction/1', manifest=manifest, provenance=execution_provenance())


def read_runtime(data: bytes) -> ExperimentManifest:
    value = parse_json(data)
    if isinstance(value, dict) and 'archive_version' in value:
        return RuntimeReproduction.model_validate(value).manifest
    return ExperimentManifest.model_validate(value)


def read_forkcast(data: bytes) -> ExperimentBundle:
    value = parse_json(data)
    if isinstance(value, dict) and 'archive_version' in value:
        return ForkCastReproduction.model_validate(value).manifest
    return ExperimentBundle.model_validate(value)


def read_bounded(path: Path, limit: int) -> bytes:
    """Cap the read itself, including files that grow after a size check."""
    if not path.is_file():
        raise ValueError('manifest must be a regular file')
    with path.open('rb') as source:
        data = source.read(limit + 1)
    if len(data) > limit:
        raise ValueError('manifest exceeds byte limit')
    return data
