#!/usr/bin/env python3
"""Read a Warcraft III .mdx, print its geometry stats and optionally export OBJ.

    python3 tools/blender/mdx_inspect.py <model.mdx> [out.obj]

Reads the chunked MDX container (MDLX): GEOS for geometry, TEXS for texture paths,
MTLS for material/layer counts, BONE for the skeleton, SEQS for animation names.
No game install and no Blender needed.
"""
import math
import struct
import sys


def chunks(data):
    pos, end = 4, len(data)
    while pos + 8 <= end:
        cid = data[pos:pos + 4].decode("ascii", "replace")
        size = struct.unpack_from("<I", data, pos + 4)[0]
        yield cid, data[pos + 8:pos + 8 + size]
        pos += 8 + size


SUB_SIZE = {"VRTX": 12, "NRMS": 12, "PTYP": 1, "PCNT": 4, "PVTX": 2, "GNDX": 1,
            "MTGC": 4, "MATS": 4, "UVBS": 8}


def parse_geos(payload):
    """Reforged-style GEOS: inclusive size, then tagged sub-chunks (VRTX, NRMS, PVTX...).
    Older files use one flat block; the tag check below picks the layout."""
    if payload[4:8] != b"VRTX":
        return parse_geos_flat(payload)
    # MDX pads some sub-chunks to 4 bytes and others not at all (PTYP is padded,
    # PVTX with an even byte count is not), so locate the tags instead of walking.
    def block(tag, stride):
        at = payload.find(tag.encode())
        if at < 0:
            return b"", 0
        count = struct.unpack_from("<I", payload, at + 4)[0]
        return payload[at + 8:at + 8 + count * stride], count

    vraw, vcount = block("VRTX", 12)
    nraw, _ = block("NRMS", 12)
    idx, icount = block("PVTX", 2)
    mat, _ = block("MATS", 4)
    verts = []
    for n in range(vcount):
        x, y, z = struct.unpack_from("<3f", vraw, n * 12)
        nx, ny, nz = struct.unpack_from("<3f", nraw, n * 12) if len(nraw) >= (n + 1) * 12 else (0, 0, 1)
        verts.append((x, y, z, nx, ny, nz, 0.0, 0.0))
    faces = list(struct.unpack_from(f"<{icount}H", idx)) if idx else []
    material_id = struct.unpack_from("<I", mat, 0)[0] if len(mat) >= 4 else 0
    xs = [v[0] for v in verts] or [0]
    ys = [v[1] for v in verts] or [0]
    zs = [v[2] for v in verts] or [0]
    bounds_radius = max(math.dist((0, 0, 0), (v[0], v[1], v[2])) for v in verts) if verts else 0
    return [{"vertices": verts, "faces": faces, "material": material_id,
             "bounds_radius": bounds_radius, "min": (min(xs), min(ys), min(zs)),
             "max": (max(xs), max(ys), max(zs))}]


def parse_geos_flat(payload):
    i = 4
    vcount = struct.unpack_from("<I", payload, i)[0]
    i += 4
    verts = []
    for _ in range(vcount):
        verts.append(struct.unpack_from("<8f", payload, i))
        i += 32
    ftype_count = struct.unpack_from("<I", payload, i)[0]
    i += 4 + 4 * ftype_count
    fgroup_count = struct.unpack_from("<I", payload, i)[0]
    i += 4 + 8 * fgroup_count
    fcount = struct.unpack_from("<I", payload, i)[0]
    i += 4
    faces = list(struct.unpack_from(f"<{fcount}H", payload, i))
    i += fcount * 2 + (fcount % 2) * 2
    vg_count = struct.unpack_from("<I", payload, i)[0]
    i += 4 + vg_count
    mg_count = struct.unpack_from("<I", payload, i)[0]
    i += 4 + 8 * mg_count
    material_id, _, _ = struct.unpack_from("<3I", payload, i)
    i += 12
    radius = struct.unpack_from("<f", payload, i)[0]
    min_ext = struct.unpack_from("<3f", payload, i + 4)
    max_ext = struct.unpack_from("<3f", payload, i + 16)
    return [{"vertices": verts, "faces": faces, "material": material_id,
             "bounds_radius": radius, "min": min_ext, "max": max_ext}]


def main():
    path = sys.argv[1]
    out_obj = sys.argv[2] if len(sys.argv) > 2 else None
    data = open(path, "rb").read()
    if data[:4] != b"MDLX":
        sys.exit("not an MDX file")

    counts = {}
    geosets, textures, bones, seqs = [], [], [], []
    for cid, payload in chunks(data):
        counts[cid] = counts.get(cid, 0) + 1
        if cid == "GEOS":
            geosets.append(parse_geos(payload))
        elif cid == "TEXS":
            i = 0
            while i + 268 <= len(payload):
                textures.append(payload[i + 4:i + 264].split(b"\0")[0].decode("latin-1"))
                i += 268
        elif cid == "BONE":
            i = 0
            while i + 96 <= len(payload):
                name = payload[i:i + 80].split(b"\0")[0].decode("latin-1")
                bones.append(name)
                i += 96
        elif cid == "SEQS":
            i = 0
            while i + 132 <= len(payload):
                name = payload[i:i + 80].split(b"\0")[0].decode("latin-1")
                start, end = struct.unpack_from("<2I", payload, i + 80)
                seqs.append((name, start, end))
                i += 132

    flat = [g for group in geosets for g in group]
    verts = sum(len(g["vertices"]) for g in flat)
    tris = sum(len(g["faces"]) // 3 for g in flat)
    print(f"{path}: {len(data)} bytes")
    print(f"  chunks: {', '.join(f'{k}x{v}' if v > 1 else k for k, v in counts.items())}")
    print(f"  geosets {len(geosets)} | vertices {verts} | triangles {tris}")
    for n, g in enumerate(flat):
        lo, hi = g["min"], g["max"]
        size = tuple(round(hi[i] - lo[i], 2) for i in range(3))
        print(f"    geoset {n}: {len(g['vertices'])} v, {len(g['faces']) // 3} tris, "
              f"extent {size}, material {g['material']}")
    print(f"  textures: {textures or 'none'}")
    print(f"  bones: {len(bones)} | sequences: {[s[0] for s in seqs][:8]}")

    if out_obj and flat:
        with open(out_obj, "w") as fh:
            offset = 1
            for g in flat:
                for x, y, z, *_ in g["vertices"]:
                    fh.write(f"v {x:.4f} {y:.4f} {z:.4f}\n")
                for i in range(0, len(g["faces"]) - 2, 3):
                    a, b, c = (g["faces"][i] + offset, g["faces"][i + 1] + offset,
                               g["faces"][i + 2] + offset)
                    fh.write(f"f {a} {b} {c}\n")
                offset += len(g["vertices"])
        print(f"  wrote {out_obj}")


if __name__ == "__main__":
    main()
