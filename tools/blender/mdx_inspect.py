#!/usr/bin/env python3
"""Read a Warcraft III .mdx, print its geometry stats and optionally export OBJ.

    python3 tools/blender/mdx_inspect.py <model.mdx> [out.obj]

Reads the chunked MDX container (MDLX): GEOS for geometry, TEXS for texture paths,
MTLS for material/layer counts, BONE for the skeleton, SEQS for animation names.
No game install and no Blender needed.
"""
import pathlib
import struct
import sys


def chunks(data):
    pos, end = 4, len(data)
    while pos + 8 <= end:
        cid = data[pos:pos + 4].decode("ascii", "replace")
        size = struct.unpack_from("<I", data, pos + 4)[0]
        yield cid, data[pos + 8:pos + 8 + size]
        pos += 8 + size


SUB_SIZE = {"VRTX": 12, "NRMS": 12, "PTYP": 4, "PCNT": 4, "PVTX": 2, "GNDX": 1,
            "MTGC": 4, "MATS": 4, "UVBS": 8}


def parse_geos(payload):
    """v800 GEOS chunk: a run of geosets, each `u32 inclusive size` + tagged sub-chunks
    (VRTX NRMS PTYP PCNT PVTX GNDX MTGC MATS, then material id, bounds, anim extents, UVAS/UVBS).
    Older files use one flat block; the tag check picks the layout. Returns one dict per geoset
    with vertices (x, y, z, nx, ny, nz, u, v), faces (flat index list), material, bounds."""
    if payload[4:8] != b"VRTX":
        return parse_geos_flat(payload)
    out, pos = [], 0
    while pos + 8 <= len(payload):
        size = struct.unpack_from("<I", payload, pos)[0]
        out.append(parse_geoset(payload[pos + 4:pos + size]))
        pos += size
    return out


def parse_geoset(g):
    """One v800 geoset body (after its size word) -> geoset dict. Tags are walked in file order."""
    at = 0
    blocks = {}
    for tag, stride in (("VRTX", 12), ("NRMS", 12), ("PTYP", 4), ("PCNT", 4), ("PVTX", 2),
                        ("GNDX", 1), ("MTGC", 4), ("MATS", 4)):
        assert g[at:at + 4] == tag.encode(), (tag, g[at:at + 4])
        n = struct.unpack_from("<I", g, at + 4)[0]
        blocks[tag] = (at + 8, n)
        at += 8 + n * stride
    material, _sel, _flags = struct.unpack_from("<3I", g, at)
    radius = struct.unpack_from("<f", g, at + 12)[0]
    lo = struct.unpack_from("<3f", g, at + 16)
    hi = struct.unpack_from("<3f", g, at + 28)
    at += 40
    at += 4 + 28 * struct.unpack_from("<I", g, at)[0]        # per-sequence extents
    uv_at = g.find(b"UVBS", at)                                # first texture-coord set
    uvn = struct.unpack_from("<I", g, uv_at + 4)[0] if uv_at >= 0 else 0
    uvs = struct.unpack_from(f"<{uvn * 2}f", g, uv_at + 8) if uv_at >= 0 else ()
    vp, vn = blocks["VRTX"]
    npos = blocks["NRMS"][0]
    pos3 = struct.unpack_from(f"<{vn * 3}f", g, vp)
    nor3 = struct.unpack_from(f"<{vn * 3}f", g, npos)
    verts = [(*pos3[i * 3:i * 3 + 3], *nor3[i * 3:i * 3 + 3],
              *(uvs[i * 2:i * 2 + 2] if i * 2 + 1 < len(uvs) else (0.0, 0.0))) for i in range(vn)]
    ip, inum = blocks["PVTX"]
    faces = list(struct.unpack_from(f"<{inum}H", g, ip))
    return {"vertices": verts, "faces": faces, "material": material, "bounds_radius": radius,
            "min": lo, "max": hi}


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


def parse_mtls(payload):
    """MTLS (v800): per material `u32 size, priority, flags, 'LAYS', n`, then n layers of
    `u32 size, filter, shading, texture id, texanim id, coord id, alpha` (+ animation tracks).
    Returns [[{filter, texture, alpha}, ...], ...] (layers per material)."""
    mats, pos = [], 0
    while pos + 20 <= len(payload):
        size = struct.unpack_from("<I", payload, pos)[0]
        count = struct.unpack_from("<I", payload, pos + 16)[0]
        lay, layers = pos + 20, []
        for _ in range(count):
            lsize, filt, _sh, tex, _anim, _coord, alpha = struct.unpack_from("<6If", payload, lay)
            layers.append({"filter": filt, "texture": tex, "alpha": alpha})
            lay += lsize
        mats.append(layers)
        pos += size
    return mats


def parse_nodes(payload, extra=0):
    """Names of the nodes of a BONE/HELP chunk (each node starts with its inclusive size; a
    BONE entry has `extra`=8 more bytes, geoset id and geoset animation id, after the node)."""
    out, pos = [], 0
    while pos + 4 <= len(payload):
        size = struct.unpack_from("<I", payload, pos)[0]
        out.append(payload[pos + 4:pos + 84].split(b"\0")[0].decode("latin-1"))
        pos += size + extra
    return out


def hidden_geosets(payload, start=0, end=0):
    """Geoset ids a GEOA entry hides in the first sequence [start, end] (the static alpha under 0.5, or the alpha track's
    last key at the sequence start under 0.5; a track with no key in the sequence leaves the static alpha): upgrade, decay and glow parts the game does not show when the unit stands."""
    out, pos = set(), 0
    while pos + 28 <= len(payload):
        size = struct.unpack_from("<I", payload, pos)[0]
        alpha, _flags, *_col, gid = struct.unpack_from("<fI3fI", payload, pos + 4)
        if payload[pos + 28:pos + 32] == b"KGAO":
            n, interp = struct.unpack_from("<2I", payload, pos + 32)
            step = 8 if interp == 0 else 20                      # time + value (+ in/out tangents)
            keys = [struct.unpack_from("<if", payload, pos + 44 + step * i) for i in range(n)]
            alpha = next((v for t, v in keys if start <= t <= end), alpha)
        if alpha < 0.5:
            out.add(gid)
        pos += size
    return out


def parse_texs(payload):
    """[(replaceable id, path)] of a TEXS chunk (268 bytes per texture)."""
    return [(struct.unpack_from("<I", payload, i)[0], payload[i + 4:i + 264].split(b"\0")[0].decode("latin-1"))
            for i in range(0, len(payload) - 267, 268)]


def parse_seqs(payload):
    """[(name, start, end)] of a SEQS chunk (132 bytes per sequence)."""
    return [(payload[i:i + 80].split(b"\0")[0].decode("latin-1"), *struct.unpack_from("<2I", payload, i + 80))
            for i in range(0, len(payload) - 131, 132)]


# chunk id -> (key of the result, parser); BONE and HELP both feed "bones" (the joints of the skeleton)
CHUNK_PARSERS = {"GEOS": ("geosets", parse_geos), "MTLS": ("materials", parse_mtls), "TEXS": ("textures", parse_texs),
                 "SEQS": ("sequences", parse_seqs), "GEOA": ("_geoa", bytes),
                 "BONE": ("bones", lambda p: parse_nodes(p, 8)), "HELP": ("bones", parse_nodes)}


def read_mdx(path):
    """Parsed MDX (v800): geosets (list of dicts, each with `visible`), materials (layers),
    textures [(replaceable id, path)], bones [names of the BONE and HELP nodes: the joints], sequences [(name, start, end)]."""
    data = pathlib.Path(path).read_bytes()
    if data[:4] != b"MDLX":
        raise ValueError(f"{path}: not an MDX file")
    mdx = {"bytes": len(data), "chunks": {}, "geosets": [], "materials": [], "textures": [],
           "bones": [], "sequences": [], "_geoa": b""}
    for cid, payload in chunks(data):
        mdx["chunks"][cid] = mdx["chunks"].get(cid, 0) + 1
        if cid in CHUNK_PARSERS:
            key, parse = CHUNK_PARSERS[cid]
            got = parse(payload)
            mdx[key] = mdx[key] + got if key == "bones" else got
    first = mdx["sequences"][0][1:] if mdx["sequences"] else (0, 0)
    mdx["hidden"] = hidden_geosets(mdx.pop("_geoa"), *first)
    for n, g in enumerate(mdx["geosets"]):
        g["visible"] = n not in mdx["hidden"]
    return mdx


def main():
    path = sys.argv[1]
    out_obj = sys.argv[2] if len(sys.argv) > 2 else None
    mdx = read_mdx(path)
    flat = mdx["geosets"]
    textures = [p or f"<replaceable {r}>" for r, p in mdx["textures"]]
    verts = sum(len(g["vertices"]) for g in flat)
    tris = sum(len(g["faces"]) // 3 for g in flat)
    print(f"{path}: {mdx['bytes']} bytes")
    print(f"  chunks: {', '.join(f'{k}x{v}' if v > 1 else k for k, v in mdx['chunks'].items())}")
    print(f"  geosets {len(flat)} ({len(mdx['hidden'])} hidden) | vertices {verts} | triangles {tris}")
    for n, g in enumerate(flat):
        lo, hi = g["min"], g["max"]
        size = tuple(round(hi[i] - lo[i], 2) for i in range(3))
        print(f"    geoset {n}: {len(g['vertices'])} v, {len(g['faces']) // 3} tris, "
              f"extent {size}, material {g['material']}{'' if g['visible'] else ' (hidden)'}")
    print(f"  materials {len(mdx['materials'])} | textures: {textures or 'none'}")
    print(f"  bones: {len(mdx['bones'])} | sequences: {[s[0] for s in mdx['sequences']][:8]}")

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
