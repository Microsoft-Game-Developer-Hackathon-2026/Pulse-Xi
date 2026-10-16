import importlib.util
import json
import shutil
import struct
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("asset_contract", ROOT / "scripts/asset_contract.py")
contract = importlib.util.module_from_spec(spec)
spec.loader.exec_module(contract)


def test_original_asset_hashes_budgets_and_self_contained_glb():
    results = contract.validate_manifest(ROOT)
    assert {asset["name"] for asset in results} == {"field", "ball", "player-marker"}
    assert sum(asset["bytes"] for asset in results) < 100_000
    assert all(asset["triangles"] > 0 for asset in results)


@pytest.fixture
def asset_copy(tmp_path):
    manifest = json.loads((ROOT / "assets/manifest.json").read_text())
    for asset in manifest["assets"]:
        for key in ("source", "output"):
            target = tmp_path / asset[key]
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / asset[key], target)
    (tmp_path / "assets/manifest.json").write_text(json.dumps(manifest))
    return tmp_path, manifest


def test_corrupted_asset_is_rejected(asset_copy):
    root, manifest = asset_copy
    output = root / manifest["assets"][0]["output"]
    data = bytearray(output.read_bytes())
    data[-1] ^= 1
    output.write_bytes(data)
    with pytest.raises(ValueError, match="hash mismatch"):
        contract.validate_manifest(root)


def test_escaped_paths_and_exceeded_budgets_are_rejected(asset_copy):
    root, manifest = asset_copy
    manifest["assets"][0]["budget_bytes"] = 1
    (root / "assets/manifest.json").write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="budget exceeded"):
        contract.validate_manifest(root)
    manifest["assets"][0]["output"] = "../outside.glb"
    (root / "assets/manifest.json").write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="escapes repository"):
        contract.validate_manifest(root)


def test_truncated_glb_is_rejected(tmp_path):
    path = tmp_path / "broken.glb"
    path.write_bytes(b"glTF")
    with pytest.raises(ValueError, match="truncated"):
        contract.read_glb(path)


def test_binary_chunk_length_corruption_is_rejected(tmp_path):
    output = ROOT / "frontend/src/features/observer/assets/field.glb"
    data = bytearray(output.read_bytes())
    json_size = struct.unpack_from('<I', data, 12)[0]
    struct.pack_into('<I', data, 20 + json_size, 0)
    path = tmp_path / 'bad-binary.glb'
    path.write_bytes(data)
    with pytest.raises(ValueError, match='BIN chunk'):
        contract.read_glb(path)


@pytest.mark.parametrize('field', ['source_bytes', 'draw_primitives'])
def test_manifest_measured_metadata_must_match(asset_copy, field):
    root, manifest = asset_copy
    manifest['assets'][0][field] += 1
    (root / 'assets/manifest.json').write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match='metadata mismatch'):
        contract.validate_manifest(root)
