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
    assert {asset["name"] for asset in results} == {"field", "ball", "player-marker", "field-v2", "stadium-v2", "ball-v2", "player-marker-v2"}
    assert sum(asset["bytes"] for asset in results if not asset['name'].endswith('-v2')) < 100_000
    assert sum(asset["bytes"] for asset in results if asset['name'].endswith('-v2')) < 1_500_000
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


@pytest.mark.parametrize('mutation', ['empty', 'duplicate', 'materials'])
def test_release_manifest_cannot_omit_duplicate_or_misdescribe_assets(asset_copy, mutation):
    root, manifest = asset_copy
    if mutation == 'empty':
        manifest['assets'] = []
    elif mutation == 'duplicate':
        manifest['assets'].append(manifest['assets'][0])
    else:
        manifest['assets'][0]['materials'] = ['InventedMaterial']
    (root / 'assets/manifest.json').write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match='inventory|materials'):
        contract.validate_manifest(root)


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


def test_opaque_triangle_order_is_canonical_without_changing_geometry(tmp_path, monkeypatch):
    monkeypatch.syspath_prepend(str(ROOT / 'scripts'))
    from glb_indices import canonicalize_indices
    source = ROOT / 'frontend/src/features/observer/assets/v2/player-marker.glb'
    output = tmp_path / 'reordered.glb'
    output.write_bytes(source.read_bytes())
    canonicalize_indices(output)
    expected = output.read_bytes()
    document = contract.read_glb(output)['document']
    data = bytearray(expected)
    base = 28 + struct.unpack_from('<I', data, 12)[0]
    accessor = document['accessors'][document['meshes'][0]['primitives'][0]['indices']]
    view = document['bufferViews'][accessor['bufferView']]
    offset = base + view.get('byteOffset', 0) + accessor.get('byteOffset', 0)
    component = {5121:'B',5123:'H',5125:'I'}[accessor['componentType']]
    fmt = '<' + str(accessor['count']) + component
    values = struct.unpack_from(fmt, data, offset)
    triangles = [values[i:i+3] for i in range(0, len(values), 3)]
    reordered = [index for a,b,c in reversed(triangles) for index in (b,c,a)]
    struct.pack_into(fmt, data, offset, *reordered)
    output.write_bytes(data)
    canonicalize_indices(output)
    assert output.read_bytes() == expected
    canonicalize_indices(output)
    assert output.read_bytes() == expected
