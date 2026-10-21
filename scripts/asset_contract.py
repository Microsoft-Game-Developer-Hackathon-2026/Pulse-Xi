"""Standard-library glTF 2.0 container and provenance checks; no Blender needed."""
import hashlib
import json
import struct
from pathlib import Path


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_glb(path: Path) -> dict:
    data = path.read_bytes()
    if len(data) < 20:
        raise ValueError("truncated GLB")
    magic, version, size = struct.unpack_from("<4sII", data)
    if magic != b"glTF" or version != 2 or size != len(data):
        raise ValueError("invalid GLB header")
    length, kind = struct.unpack_from("<II", data, 12)
    if kind != 0x4E4F534A or length % 4 or 20 + length > len(data):
        raise ValueError("invalid JSON chunk")
    doc = json.loads(data[20:20 + length])
    # This original untextured kit requires one self-contained binary chunk.
    binary_offset = 20 + length
    if binary_offset + 8 > len(data):
        raise ValueError("missing BIN chunk")
    binary_length, binary_kind = struct.unpack_from("<II", data, binary_offset)
    if (binary_kind != 0x004E4942 or binary_length % 4 or
            binary_offset + 8 + binary_length != len(data)):
        raise ValueError("invalid BIN chunk length/type")
    buffers = doc.get("buffers", [])
    if (len(buffers) != 1 or not isinstance(buffers[0].get("byteLength"), int) or
            not 0 <= binary_length - buffers[0]["byteLength"] <= 3):
        raise ValueError("BIN chunk disagrees with buffer length")
    for view in doc.get("bufferViews", []):
        offset, size = view.get("byteOffset", 0), view.get("byteLength")
        if (view.get("buffer") != 0 or type(offset) is not int or type(size) is not int or
                offset < 0 or size < 0 or offset + size > buffers[0]["byteLength"]):
            raise ValueError("buffer view exceeds BIN chunk")
    for collection in ("buffers", "images"):
        if any("uri" in item for item in doc.get(collection, [])):
            raise ValueError("external/data URI resources are not permitted")
    triangles = 0
    primitives = 0
    for mesh in doc.get("meshes", []):
        for primitive in mesh["primitives"]:
            if primitive.get("mode", 4) != 4:
                raise ValueError("triangle primitives required")
            accessor = primitive.get("indices", primitive["attributes"]["POSITION"])
            count = doc["accessors"][accessor]["count"]
            if count % 3:
                raise ValueError("invalid triangle index count")
            triangles += count // 3
            primitives += 1
    return {"document": doc, "triangles": triangles, "primitives": primitives,
            "bytes": len(data), "textures": len(doc.get("textures", []))}


def validate_manifest(root: Path) -> list[dict]:
    manifest = json.loads((root / "assets/manifest.json").read_text(encoding="utf-8"))
    if manifest["schema_version"] != "1.0" or manifest["release_approval"] != "pending-team-review":
        raise ValueError("unexpected asset review/schema state")
    expected = {'field', 'ball', 'player-marker', 'field-v2', 'ball-v2', 'player-marker-v2', 'stadium-v2'}
    names = [asset['name'] for asset in manifest['assets']]
    if len(names) != len(expected) or set(names) != expected:
        raise ValueError('release asset inventory is incomplete or duplicated')
    results = []
    for asset in manifest["assets"]:
        output = (root / asset["output"]).resolve()
        source = (root / asset["source"]).resolve()
        if not output.is_relative_to(root.resolve()) or not source.is_relative_to(root.resolve()):
            raise ValueError("asset path escapes repository")
        if sha256(output) != asset["output_sha256"] or sha256(source) != asset["source_sha256"]:
            raise ValueError(f"asset hash mismatch: {asset['name']}")
        info = read_glb(output)
        materials = sorted(item['name'] for item in info['document'].get('materials', []))
        if sorted(asset['materials']) != materials:
            raise ValueError(f"asset materials mismatch: {asset['name']}")
        if info["bytes"] > asset["budget_bytes"] or info["triangles"] > asset["budget_triangles"]:
            raise ValueError(f"asset budget exceeded: {asset['name']}")
        if (info["triangles"] != asset["triangles"] or info["bytes"] != asset["bytes"] or info["textures"] or
                info["primitives"] != asset["draw_primitives"] or source.stat().st_size != asset["source_bytes"]):
            raise ValueError(f"asset metadata mismatch: {asset['name']}")
        if asset["license"] != "CC0-1.0" or not asset["author"]:
            raise ValueError("asset provenance is incomplete")
        results.append({"name": asset["name"], "bytes": info["bytes"], "triangles": info["triangles"],
                        "draw_primitives": info["primitives"]})
    return results


if __name__ == "__main__":
    print(json.dumps(validate_manifest(Path(__file__).resolve().parents[1]), indent=2))
