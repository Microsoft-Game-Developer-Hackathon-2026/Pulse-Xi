"""Canonical opaque triangle draw order for our original static GLB exports.

Blender may permute opaque triangles between processes. Sorting cyclically
equivalent index triplets preserves winding, vertices, materials and geometry.
This deliberately rejects transparent primitives and is not a general optimizer.
"""
import struct
from pathlib import Path

from asset_contract import read_glb


def canonicalize_indices(path: Path) -> None:
    document = read_glb(path)['document']
    data = bytearray(path.read_bytes())
    binary_base = 28 + struct.unpack_from('<I', data, 12)[0]
    for mesh in document['meshes']:
        for primitive in mesh['primitives']:
            material = document.get('materials', [])[primitive['material']]
            if primitive.get('mode', 4) != 4 or material.get('alphaMode', 'OPAQUE') != 'OPAQUE':
                raise ValueError('Canonical ordering requires opaque triangle primitives')
            accessor = document['accessors'][primitive['indices']]
            view = document['bufferViews'][accessor['bufferView']]
            if 'sparse' in accessor or 'byteStride' in view:
                raise ValueError('Unsupported index layout')
            component = {5121:'B', 5123:'H', 5125:'I'}[accessor['componentType']]
            offset = binary_base + view.get('byteOffset', 0) + accessor.get('byteOffset', 0)
            count = accessor['count']
            if count % 3:
                raise ValueError('Incomplete triangle')
            indices = struct.unpack_from('<' + str(count) + component, data, offset)
            triangles = []
            for i in range(0, count, 3):
                a,b,c = indices[i:i+3]
                triangles.append(min((a,b,c),(b,c,a),(c,a,b)))
            flattened = [index for triangle in sorted(triangles) for index in triangle]
            struct.pack_into('<' + str(count) + component, data, offset, *flattened)
    path.write_bytes(data)
