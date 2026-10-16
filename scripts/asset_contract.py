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
    if kind != 0x4E4F534A or 20 + length > len(data):
        raise ValueError("invalid JSON chunk")
    doc = json.loads(data[20:20 + length])
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
    results = []
    for asset in manifest["assets"]:
        output = (root / asset["output"]).resolve()
        source = (root / asset["source"]).resolve()
        if not output.is_relative_to(root.resolve()) or not source.is_relative_to(root.resolve()):
            raise ValueError("asset path escapes repository")
        if sha256(output) != asset["output_sha256"] or sha256(source) != asset["source_sha256"]:
            raise ValueError(f"asset hash mismatch: {asset['name']}")
        info = read_glb(output)
        if info["bytes"] > asset["budget_bytes"] or info["triangles"] > asset["budget_triangles"]:
            raise ValueError(f"asset budget exceeded: {asset['name']}")
        if info["triangles"] != asset["triangles"] or info["bytes"] != asset["bytes"] or info["textures"]:
            raise ValueError(f"asset metadata mismatch: {asset['name']}")
        if asset["license"] != "CC0-1.0" or not asset["author"]:
            raise ValueError("asset provenance is incomplete")
        results.append({"name": asset["name"], "bytes": info["bytes"], "triangles": info["triangles"],
                        "draw_primitives": info["primitives"]})
    return results


if __name__ == "__main__":
    print(json.dumps(validate_manifest(Path(__file__).resolve().parents[1]), indent=2))
